import { useSetBroker } from "../hooks/useApi";

/** Shown to a member with no broker/tier chosen yet -- mirrors
 * growthclubpk.com's own "Open Exness or XM" onboarding step. */
export function BrokerPicker() {
  const setBroker = useSetBroker();

  return (
    <div className="flex flex-col gap-3 border-b border-line px-4 py-6 sm:px-6">
      <h2 className="text-sm font-semibold uppercase tracking-wide text-secondary">Get access</h2>
      <p className="text-sm text-secondary">
        Open an account with one of our broker partners to unlock the free tier, or pick a broker you already use.
      </p>
      <div className="flex gap-3">
        <button
          type="button"
          onClick={() => setBroker.mutate("exness")}
          className="rounded bg-gold px-4 py-2 text-sm font-medium text-ground disabled:opacity-50"
          disabled={setBroker.isPending}
        >
          I use Exness
        </button>
        <button
          type="button"
          onClick={() => setBroker.mutate("xm")}
          className="rounded border border-line px-4 py-2 text-sm text-primary disabled:opacity-50"
          disabled={setBroker.isPending}
        >
          I use XM
        </button>
      </div>
    </div>
  );
}
