import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  clearTokens,
  getAccessToken,
  getRole,
  isAuthenticated,
  login,
  logout,
  onAuthChange,
  refreshAccessToken,
  register,
  verifyTotp,
} from "./auth";

function jsonResponse(body: unknown, ok = true, status = ok ? 200 : 400): Response {
  return { ok, status, json: async () => body } as Response;
}

describe("auth", () => {
  beforeEach(() => {
    clearTokens();
    vi.restoreAllMocks();
  });

  afterEach(() => {
    clearTokens();
  });

  describe("register", () => {
    it("posts email/password to /auth/register and returns the temp token", async () => {
      const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ temp_token: "temp-1" }));
      vi.stubGlobal("fetch", fetchMock);

      const token = await register("a@b.com", "hunter22");

      expect(token).toBe("temp-1");
      expect(fetchMock).toHaveBeenCalledWith(
        "/auth/register",
        expect.objectContaining({ method: "POST", body: JSON.stringify({ email: "a@b.com", password: "hunter22" }) }),
      );
    });

    it("throws the server detail on a 409 conflict", async () => {
      vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse({ detail: "An account with this email already exists" }, false, 409)));
      await expect(register("a@b.com", "hunter22")).rejects.toThrow("already exists");
    });
  });

  describe("login", () => {
    it("returns a temp token and does not authenticate on its own", async () => {
      vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse({ temp_token: "temp-2" })));
      const token = await login("a@b.com", "hunter22");
      expect(token).toBe("temp-2");
      expect(isAuthenticated()).toBe(false);
    });

    it("throws on a 401", async () => {
      vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse({ detail: "Invalid email or password" }, false, 401)));
      await expect(login("a@b.com", "wrong")).rejects.toThrow("Invalid email or password");
    });
  });

  describe("verifyTotp", () => {
    it("sets tokens and fetches the role on success", async () => {
      const fetchMock = vi
        .fn()
        .mockResolvedValueOnce(jsonResponse({ access_token: "acc-1", refresh_token: "ref-1" }))
        .mockResolvedValueOnce(jsonResponse({ role: "member" }));
      vi.stubGlobal("fetch", fetchMock);
      const listener = vi.fn();
      const unsubscribe = onAuthChange(listener);

      await verifyTotp("temp-1", "");

      expect(getAccessToken()).toBe("acc-1");
      expect(isAuthenticated()).toBe(true);
      expect(getRole()).toBe("member");
      expect(listener).toHaveBeenCalledWith(true);
      unsubscribe();
    });

    it("accepts an empty totp_code (member with no 2FA enrolled)", async () => {
      const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ access_token: "a", refresh_token: "r" }));
      vi.stubGlobal("fetch", fetchMock);
      await verifyTotp("temp-1", "");
      const [, init] = fetchMock.mock.calls[0];
      expect(init.body).toBe(JSON.stringify({ temp_token: "temp-1", totp_code: "" }));
    });

    it("throws on an invalid code", async () => {
      vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse({ detail: "Invalid or expired code" }, false, 401)));
      await expect(verifyTotp("temp-1", "000000")).rejects.toThrow("Invalid or expired code");
      expect(isAuthenticated()).toBe(false);
    });
  });

  describe("refreshAccessToken", () => {
    it("returns null immediately with no refresh token stored", async () => {
      const fetchMock = vi.fn();
      vi.stubGlobal("fetch", fetchMock);
      expect(await refreshAccessToken()).toBeNull();
      expect(fetchMock).not.toHaveBeenCalled();
    });

    it("works again on a later call after an earlier no-refresh-token call", async () => {
      // Regression check for the exact bug found in the sibling trading-bot
      // project: a synchronously-resolving no-op call must not permanently
      // wedge the in-flight guard.
      vi.stubGlobal("fetch", vi.fn());
      await refreshAccessToken();

      const fetchMock2 = vi
        .fn()
        .mockResolvedValueOnce(jsonResponse({ access_token: "a1", refresh_token: "r1" }))
        .mockResolvedValueOnce(jsonResponse({ role: "member" }))
        .mockResolvedValueOnce(jsonResponse({ access_token: "a2" }));
      vi.stubGlobal("fetch", fetchMock2);
      await verifyTotp("temp-1", "");

      const result = await refreshAccessToken();
      expect(result).toBe("a2");
    });

    it("clears tokens and returns null when the refresh call fails", async () => {
      vi.stubGlobal(
        "fetch",
        vi
          .fn()
          .mockResolvedValueOnce(jsonResponse({ access_token: "a1", refresh_token: "r1" }))
          .mockResolvedValueOnce(jsonResponse({ role: "member" }))
          .mockResolvedValueOnce(jsonResponse({}, false, 401)),
      );
      await verifyTotp("temp-1", "");
      const result = await refreshAccessToken();
      expect(result).toBeNull();
      expect(isAuthenticated()).toBe(false);
    });
  });

  describe("logout", () => {
    it("clears tokens and role, notifies listeners with false", async () => {
      vi.stubGlobal(
        "fetch",
        vi.fn().mockResolvedValueOnce(jsonResponse({ access_token: "a", refresh_token: "r" })).mockResolvedValueOnce(jsonResponse({ role: "admin" })),
      );
      await verifyTotp("temp-1", "123456");
      const listener = vi.fn();
      const unsubscribe = onAuthChange(listener);

      logout();

      expect(isAuthenticated()).toBe(false);
      expect(getRole()).toBeNull();
      expect(listener).toHaveBeenCalledWith(false);
      unsubscribe();
    });
  });
});
