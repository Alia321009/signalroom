export function formatPrice(value: number, digits: number = 2): string {
  return value.toFixed(digits);
}

export function formatRMultiple(value: number | null): string {
  if (value === null) return "—";
  return `${value >= 0 ? "+" : ""}${value.toFixed(2)}R`;
}

export function formatDateTime(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "—";
  return d.toLocaleString("en-US", { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit", hour12: false });
}

export function statusLabel(status: string): string {
  return status.replace(/_/g, " ");
}

export function statusTone(status: string): "profit" | "loss" | "neutral" {
  if (status.endsWith("_hit") && !status.startsWith("sl")) return "profit";
  if (status === "sl_hit") return "loss";
  return "neutral";
}
