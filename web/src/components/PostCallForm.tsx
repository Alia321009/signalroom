import { useState } from "react";
import { useCreateCall } from "../hooks/useApi";

function defaultValidUntil(): string {
  const d = new Date(Date.now() + 4 * 60 * 60 * 1000);
  d.setSeconds(0, 0);
  return d.toISOString().slice(0, 16); // datetime-local format
}

export function PostCallForm() {
  const createCall = useCreateCall();
  const [symbol, setSymbol] = useState("XAUUSD");
  const [direction, setDirection] = useState<"buy" | "sell">("buy");
  const [entry, setEntry] = useState("");
  const [sl, setSl] = useState("");
  const [tp1, setTp1] = useState("");
  const [tp2, setTp2] = useState("");
  const [tp3, setTp3] = useState("");
  const [validUntil, setValidUntil] = useState(defaultValidUntil());
  const [notes, setNotes] = useState("");

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    createCall.mutate(
      {
        symbol, direction, entry: Number(entry), sl: Number(sl), tp1: Number(tp1),
        tp2: tp2 ? Number(tp2) : null, tp3: tp3 ? Number(tp3) : null,
        valid_until: new Date(validUntil).toISOString(), notes: notes || null,
      },
      {
        onSuccess: () => {
          setEntry("");
          setSl("");
          setTp1("");
          setTp2("");
          setTp3("");
          setNotes("");
        },
      },
    );
  }

  const inputClass = "rounded border border-line bg-transparent px-3 py-2 text-sm text-primary tabular-nums outline-none focus:border-gold";

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-3 border-b border-line px-4 py-5 sm:px-6" aria-label="Post a call">
      <h2 className="text-sm font-semibold uppercase tracking-wide text-secondary">Post a call</h2>
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <input aria-label="Symbol" required value={symbol} onChange={(e) => setSymbol(e.target.value.toUpperCase())} className={inputClass} placeholder="XAUUSD" />
        <select aria-label="Direction" value={direction} onChange={(e) => setDirection(e.target.value as "buy" | "sell")} className={inputClass}>
          <option value="buy">Buy</option>
          <option value="sell">Sell</option>
        </select>
        <input aria-label="Entry" required type="number" step="any" value={entry} onChange={(e) => setEntry(e.target.value)} className={inputClass} placeholder="Entry" />
        <input aria-label="Stop loss" required type="number" step="any" value={sl} onChange={(e) => setSl(e.target.value)} className={inputClass} placeholder="Stop loss" />
        <input aria-label="Take profit 1" required type="number" step="any" value={tp1} onChange={(e) => setTp1(e.target.value)} className={inputClass} placeholder="TP1" />
        <input aria-label="Take profit 2" type="number" step="any" value={tp2} onChange={(e) => setTp2(e.target.value)} className={inputClass} placeholder="TP2 (optional)" />
        <input aria-label="Take profit 3" type="number" step="any" value={tp3} onChange={(e) => setTp3(e.target.value)} className={inputClass} placeholder="TP3 (optional)" />
        <input aria-label="Valid until" required type="datetime-local" value={validUntil} onChange={(e) => setValidUntil(e.target.value)} className={inputClass} />
      </div>
      <textarea aria-label="Notes" value={notes} onChange={(e) => setNotes(e.target.value)} className={inputClass} placeholder="Notes (optional) — nothing vague" rows={2} />
      {createCall.isError && <p className="text-sm text-loss">{createCall.error.message}</p>}
      <button type="submit" disabled={createCall.isPending} className="self-start rounded bg-gold px-4 py-2 text-sm font-medium text-ground disabled:opacity-50">
        {createCall.isPending ? "Posting…" : "Post call"}
      </button>
    </form>
  );
}
