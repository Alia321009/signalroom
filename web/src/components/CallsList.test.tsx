import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

const apiMocks = vi.hoisted(() => ({ useUpdateCall: vi.fn() }));
vi.mock("../hooks/useApi", () => apiMocks);

import { CallsList } from "./CallsList";
import type { Call } from "../lib/types";

function call(overrides: Partial<Call> = {}): Call {
  return {
    id: 1, created_by: 1, symbol: "XAUUSD", direction: "buy", entry: 4220, sl: 4210,
    tp1: 4230, tp2: null, tp3: null, valid_until: "2026-01-01T04:00:00Z", status: "pending",
    notes: null, created_at: "2026-01-01T00:00:00Z", updated_at: "2026-01-01T00:00:00Z",
    closed_at: null, outcome_r: null,
    ...overrides,
  };
}

describe("CallsList", () => {
  it("shows a plain empty state with no calls", () => {
    render(<CallsList calls={[]} isAdmin={false} />);
    expect(screen.getByText("No calls yet.")).toBeInTheDocument();
  });

  it("renders a call's symbol, direction, and levels", () => {
    apiMocks.useUpdateCall.mockReturnValue({ mutate: vi.fn() });
    render(<CallsList calls={[call()]} isAdmin={false} />);
    expect(screen.getByText("XAUUSD")).toBeInTheDocument();
    expect(screen.getByText("buy")).toBeInTheDocument();
    expect(screen.getByText("4220.0000")).toBeInTheDocument();
  });

  it("does not show admin controls for a member", () => {
    apiMocks.useUpdateCall.mockReturnValue({ mutate: vi.fn() });
    render(<CallsList calls={[call()]} isAdmin={false} />);
    expect(screen.queryByLabelText(/Update status/)).not.toBeInTheDocument();
  });

  it("shows admin controls for the admin view", () => {
    apiMocks.useUpdateCall.mockReturnValue({ mutate: vi.fn() });
    render(<CallsList calls={[call()]} isAdmin />);
    expect(screen.getByLabelText("Update status for call 1")).toBeInTheDocument();
    expect(screen.getByLabelText("Outcome R for call 1")).toBeInTheDocument();
  });

  it("shows an em dash for unset TP2/TP3", () => {
    apiMocks.useUpdateCall.mockReturnValue({ mutate: vi.fn() });
    render(<CallsList calls={[call()]} isAdmin={false} />);
    const dashes = screen.getAllByText("—");
    expect(dashes.length).toBeGreaterThanOrEqual(2);
  });

  it("renders a positive outcome_r with a formatted R suffix", () => {
    apiMocks.useUpdateCall.mockReturnValue({ mutate: vi.fn() });
    render(<CallsList calls={[call({ outcome_r: 2.0, status: "tp1_hit" })]} isAdmin={false} />);
    expect(screen.getByText("+2.00R")).toBeInTheDocument();
  });
});
