import { useMe, useCalls } from "../hooks/useApi";
import { useLiveFeed } from "../lib/useLiveFeed";
import { logout } from "../lib/auth";
import { PostCallForm } from "./PostCallForm";
import { CallsList } from "./CallsList";
import { MembersPanel } from "./MembersPanel";
import { BotSettingsPanel } from "./BotSettingsPanel";
import { BrokerPicker } from "./BrokerPicker";

export function Dashboard() {
  const me = useMe();
  const calls = useCalls();
  const { connected } = useLiveFeed();

  if (!me.data) {
    return <div className="flex min-h-screen items-center justify-center bg-ground text-secondary">Loading…</div>;
  }

  const isAdmin = me.data.role === "admin";

  return (
    <div className="flex min-h-screen flex-col bg-ground text-primary">
      <header className="sticky top-0 z-10 flex items-center justify-between border-b border-line bg-ground px-4 py-3 sm:px-6">
        <div className="flex items-center gap-3">
          <span className="text-sm font-semibold tracking-tight">SignalRoom</span>
          <span className="flex items-center gap-1.5 text-xs text-secondary">
            <span className={`h-1.5 w-1.5 rounded-full ${connected ? "bg-profit" : "bg-loss"}`} />
            {connected ? "Live" : "Reconnecting…"}
          </span>
        </div>
        <div className="flex items-center gap-4">
          <span className="text-xs text-secondary">{me.data.email}</span>
          <button type="button" onClick={logout} className="text-xs text-secondary underline">
            Sign out
          </button>
        </div>
      </header>

      {isAdmin ? (
        <>
          <PostCallForm />
          <CallsList calls={calls.data ?? []} isAdmin />
          <MembersPanel />
        </>
      ) : (
        <>
          {(me.data.subscription?.tier ?? "none") === "none" && <BrokerPicker />}
          <BotSettingsPanel />
          <CallsList calls={calls.data ?? []} isAdmin={false} />
        </>
      )}
    </div>
  );
}
