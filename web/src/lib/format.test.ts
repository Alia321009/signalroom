import { describe, expect, it } from "vitest";
import { formatPrice, formatRMultiple, formatDateTime, statusLabel, statusTone } from "./format";

describe("formatPrice", () => {
  it("defaults to 2 digits", () => {
    expect(formatPrice(1.5)).toBe("1.50");
  });
  it("respects a custom digit count", () => {
    expect(formatPrice(1.23456, 4)).toBe("1.2346");
  });
});

describe("formatRMultiple", () => {
  it("returns an em dash for null", () => {
    expect(formatRMultiple(null)).toBe("—");
  });
  it("prefixes a positive value with +", () => {
    expect(formatRMultiple(1.5)).toBe("+1.50R");
  });
  it("does not double the sign on a negative value", () => {
    expect(formatRMultiple(-0.8)).toBe("-0.80R");
  });
});

describe("formatDateTime", () => {
  it("returns an em dash for an invalid string", () => {
    expect(formatDateTime("not-a-date")).toBe("—");
  });
  it("formats a valid ISO string", () => {
    expect(formatDateTime("2026-01-15T10:30:00Z").length).toBeGreaterThan(0);
  });
});

describe("statusLabel", () => {
  it("replaces underscores with spaces", () => {
    expect(statusLabel("tp1_hit")).toBe("tp1 hit");
  });
});

describe("statusTone", () => {
  it("profit for a tp hit", () => {
    expect(statusTone("tp1_hit")).toBe("profit");
    expect(statusTone("tp2_hit")).toBe("profit");
  });
  it("loss for sl_hit specifically", () => {
    expect(statusTone("sl_hit")).toBe("loss");
  });
  it("neutral for everything else", () => {
    expect(statusTone("pending")).toBe("neutral");
    expect(statusTone("active")).toBe("neutral");
    expect(statusTone("cancelled")).toBe("neutral");
    expect(statusTone("expired")).toBe("neutral");
  });
});
