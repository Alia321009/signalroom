import { useState } from "react";
import type { Call, CallStatus } from "../lib/types";
import { CallCard } from "./CallCard";
import { useUpdateCall } from "../hooks/useApi";

const STATUS_OPTIONS: CallStatus[] = ["pending", "active", "tp1_hit", "tp2_hit", "tp3_hit", "sl_hit", "expired", "cancelled"];

function AdminActions({ call }: { call: Call }) {
  const updateCall = useUpdateCall();
  const [outcomeR, setOutcomeR] = useState(call.outcome_r?.toString() ?? "");

  return (
    <div className="flex flex-wrap items-center gap-2 pt-1">
      <select
        aria-label={`Update status for call ${call.id}`}
        value={call.status}
        onChange={(e) => updateCall.mutate({ id: call.id, status: e.target.value })}
        className="rounded border border-line bg-transparent px-2 py-1 text-xs text-primary"
      >
        {STATUS_OPTIONS.map((s) => (
          <option key={s} value={s}>
            {s}
          </option>
        ))}
      </select>
      <input
        aria-label={`Outcome R for call ${call.id}`}
        type="number"
        step="any"
        value={outcomeR}
        onChange={(e) => setOutcomeR(e.target.value)}
        placeholder="Outcome R"
        className="w-24 rounded border border-line bg-transparent px-2 py-1 text-xs text-primary tabular-nums"
      />
      <button
        type="button"
        onClick={() => updateCall.mutate({ id: call.id, outcome_r: Number(outcomeR) })}
        disabled={outcomeR === ""}
        className="rounded border border-line px-2 py-1 text-xs text-secondary hover:text-primary disabled:opacity-40"
      >
        Save R
      </button>
    </div>
  );
}

export function CallsList({ calls, isAdmin }: { calls: Call[]; isAdmin: boolean }) {
  if (calls.length === 0) {
    return <p className="px-4 py-8 text-sm text-secondary sm:px-6">No calls yet.</p>;
  }
  return (
    <div className="flex flex-col">
      {calls.map((call) => (
        <CallCard key={call.id} call={call} actions={isAdmin ? <AdminActions call={call} /> : undefined} />
      ))}
    </div>
  );
}
