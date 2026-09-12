import type { Call } from "../lib/types";
import { formatDateTime, formatPrice, formatRMultiple, statusLabel, statusTone } from "../lib/format";
import { useFlashOnChange } from "../lib/useFlashOnChange";

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex flex-col gap-0.5">
      <span className="text-[10px] uppercase tracking-wide text-secondary">{label}</span>
      <span className="tabular-nums text-sm text-primary">{value}</span>
    </div>
  );
}

export function CallCard({ call, actions }: { call: Call; actions?: React.ReactNode }) {
  const flashing = useFlashOnChange(call.status);
  const tone = statusTone(call.status);
  const toneClass = tone === "profit" ? "text-profit" : tone === "loss" ? "text-loss" : "text-secondary";

  return (
    <div className={`flex flex-col gap-3 border-b border-line px-4 py-4 sm:px-6 ${flashing ? "flash-on-change" : ""}`}>
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <span className="text-base font-semibold tracking-tight text-primary">{call.symbol}</span>
          <span className={`text-xs font-medium uppercase ${call.direction === "buy" ? "text-profit" : "text-loss"}`}>
            {call.direction}
          </span>
        </div>
        <span className={`text-xs font-medium uppercase tracking-wide ${toneClass}`}>{statusLabel(call.status)}</span>
      </div>

      <div className="grid grid-cols-3 gap-3 sm:grid-cols-6">
        <Field label="Entry" value={formatPrice(call.entry, 4)} />
        <Field label="Stop" value={formatPrice(call.sl, 4)} />
        <Field label="TP1" value={formatPrice(call.tp1, 4)} />
        <Field label="TP2" value={call.tp2 !== null ? formatPrice(call.tp2, 4) : "—"} />
        <Field label="TP3" value={call.tp3 !== null ? formatPrice(call.tp3, 4) : "—"} />
        <Field label="Outcome" value={formatRMultiple(call.outcome_r)} />
      </div>

      {call.notes && <p className="text-sm text-secondary">{call.notes}</p>}

      <div className="flex items-center justify-between text-xs text-secondary">
        <span>Valid until {formatDateTime(call.valid_until)}</span>
        <span>Posted {formatDateTime(call.created_at)}</span>
      </div>

      {actions}
    </div>
  );
}
