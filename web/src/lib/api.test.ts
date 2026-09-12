import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const authMocks = vi.hoisted(() => ({
  getAccessToken: vi.fn<() => string | null>(),
  refreshAccessToken: vi.fn<() => Promise<string | null>>(),
  clearTokens: vi.fn(),
}));

vi.mock("./auth", () => authMocks);

import { apiFetch, apiGet, apiPatch, apiPost, ApiError } from "./api";

function jsonResponse(body: unknown, status = 200): Response {
  return { ok: status >= 200 && status < 300, status, statusText: "", json: async () => body } as Response;
}

describe("apiFetch", () => {
  beforeEach(() => {
    authMocks.getAccessToken.mockReturnValue("access-1");
    authMocks.refreshAccessToken.mockReset();
    authMocks.clearTokens.mockReset();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("attaches the bearer token", async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ ok: true }));
    vi.stubGlobal("fetch", fetchMock);
    await apiGet("/members/me");
    const [, init] = fetchMock.mock.calls[0];
    expect(new Headers(init.headers).get("Authorization")).toBe("Bearer access-1");
  });

  it("returns parsed JSON on success", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse({ id: 1 })));
    expect(await apiGet<{ id: number }>("/members/me")).toEqual({ id: 1 });
  });

  it("returns undefined for a 204 without reading a body", async () => {
    const res = { ok: true, status: 204, statusText: "", json: vi.fn() } as unknown as Response;
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(res));
    expect(await apiPost("/executor/calls/report")).toBeUndefined();
    expect((res.json as ReturnType<typeof vi.fn>)).not.toHaveBeenCalled();
  });

  it("refreshes once and retries on a 401, then succeeds", async () => {
    const fetchMock = vi.fn().mockResolvedValueOnce(jsonResponse({}, 401)).mockResolvedValueOnce(jsonResponse({ id: 2 }));
    vi.stubGlobal("fetch", fetchMock);
    authMocks.refreshAccessToken.mockResolvedValue("access-2");

    const result = await apiGet<{ id: number }>("/members/me");

    expect(result).toEqual({ id: 2 });
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it("clears tokens and throws when refresh fails after a 401", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse({}, 401)));
    authMocks.refreshAccessToken.mockResolvedValue(null);
    await expect(apiGet("/members/me")).rejects.toThrow(ApiError);
    expect(authMocks.clearTokens).toHaveBeenCalled();
  });

  it("throws ApiError with the server detail on a non-401 error", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse({ detail: "risk_pct must be in..." }, 422)));
    await expect(apiPatch("/calls/1", {})).rejects.toThrow("risk_pct must be in...");
  });

  it("falls back to statusText when the error body is not JSON", async () => {
    const res = {
      ok: false, status: 500, statusText: "Internal Server Error",
      json: async () => {
        throw new Error("not json");
      },
    } as unknown as Response;
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(res));
    await expect(apiGet("/members/me")).rejects.toThrow("Internal Server Error");
  });

  it("apiPost sends a JSON body when given one", async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ ok: true }));
    vi.stubGlobal("fetch", fetchMock);
    await apiPost("/calls", { symbol: "XAUUSD" });
    const [, init] = fetchMock.mock.calls[0];
    expect(init.body).toBe(JSON.stringify({ symbol: "XAUUSD" }));
    expect(new Headers(init.headers).get("Content-Type")).toBe("application/json");
  });

  it("apiPost omits body/content-type when none given", async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ ok: true }));
    vi.stubGlobal("fetch", fetchMock);
    await apiPost("/bot-settings/me/rotate-key");
    const [, init] = fetchMock.mock.calls[0];
    expect(init.body).toBeUndefined();
    expect(new Headers(init.headers).has("Content-Type")).toBe(false);
  });
});

describe("apiFetch direct use", () => {
  it("works when called directly, not just via the apiGet/apiPost wrappers", async () => {
    authMocks.getAccessToken.mockReturnValue(null);
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse({ x: 1 })));
    expect(await apiFetch<{ x: number }>("/members/me", { method: "GET" })).toEqual({ x: 1 });
  });
});
