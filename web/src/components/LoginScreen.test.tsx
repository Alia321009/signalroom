import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

const authMocks = vi.hoisted(() => ({ login: vi.fn(), register: vi.fn(), verifyTotp: vi.fn() }));
vi.mock("../lib/auth", () => authMocks);

import { LoginScreen } from "./LoginScreen";

describe("LoginScreen", () => {
  it("logs in and advances to the totp step", async () => {
    authMocks.login.mockResolvedValue("temp-1");
    const user = userEvent.setup();
    render(<LoginScreen />);

    await user.type(screen.getByLabelText("Email"), "a@b.com");
    await user.type(screen.getByLabelText("Password"), "hunter22");
    await user.click(screen.getByRole("button", { name: "Log in" }));

    await waitFor(() => expect(screen.getByLabelText(/6-digit code/)).toBeInTheDocument());
    expect(authMocks.login).toHaveBeenCalledWith("a@b.com", "hunter22");
  });

  it("switches to sign-up mode and calls register instead of login", async () => {
    authMocks.register.mockResolvedValue("temp-2");
    const user = userEvent.setup();
    render(<LoginScreen />);

    await user.click(screen.getByRole("button", { name: /Need an account/ }));
    await user.type(screen.getByLabelText("Email"), "new@b.com");
    await user.type(screen.getByLabelText("Password"), "hunter22");
    await user.click(screen.getByRole("button", { name: "Create account" }));

    await waitFor(() => expect(authMocks.register).toHaveBeenCalledWith("new@b.com", "hunter22"));
  });

  it("shows the server error on a failed login", async () => {
    authMocks.login.mockRejectedValue(new Error("Invalid email or password"));
    const user = userEvent.setup();
    render(<LoginScreen />);

    await user.type(screen.getByLabelText("Email"), "a@b.com");
    await user.type(screen.getByLabelText("Password"), "wrong");
    await user.click(screen.getByRole("button", { name: "Log in" }));

    await waitFor(() => expect(screen.getByText("Invalid email or password")).toBeInTheDocument());
  });

  it("submits an empty totp code by default", async () => {
    authMocks.login.mockResolvedValue("temp-1");
    authMocks.verifyTotp.mockResolvedValue(undefined);
    const user = userEvent.setup();
    render(<LoginScreen />);

    await user.type(screen.getByLabelText("Email"), "a@b.com");
    await user.type(screen.getByLabelText("Password"), "hunter22");
    await user.click(screen.getByRole("button", { name: "Log in" }));
    await waitFor(() => screen.getByLabelText(/6-digit code/));

    await user.click(screen.getByRole("button", { name: "Continue" }));

    await waitFor(() => expect(authMocks.verifyTotp).toHaveBeenCalledWith("temp-1", ""));
  });

  it("Back returns to the credentials step", async () => {
    authMocks.login.mockResolvedValue("temp-1");
    const user = userEvent.setup();
    render(<LoginScreen />);

    await user.type(screen.getByLabelText("Email"), "a@b.com");
    await user.type(screen.getByLabelText("Password"), "hunter22");
    await user.click(screen.getByRole("button", { name: "Log in" }));
    await waitFor(() => screen.getByLabelText(/6-digit code/));

    await user.click(screen.getByRole("button", { name: "Back" }));

    expect(screen.getByLabelText("Email")).toBeInTheDocument();
  });
});
