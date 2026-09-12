import { useMembers, useUpdateSubscription } from "../hooks/useApi";
import { formatDateTime } from "../lib/format";
import type { Member } from "../lib/types";

const TIERS = ["none", "broker_referral", "paid", "trial"];
const STATUSES = ["pending", "active", "expired", "revoked"];

function MemberRow({ member }: { member: Member }) {
  const updateSubscription = useUpdateSubscription();
  const sub = member.subscription;

  return (
    <tr className="border-t border-line">
      <td className="px-3 py-2 text-primary">{member.email}</td>
      <td className="px-3 py-2 text-secondary">{sub?.broker ?? "—"}</td>
      <td className="px-3 py-2">
        <select
          aria-label={`Tier for ${member.email}`}
          value={sub?.tier ?? "none"}
          onChange={(e) => updateSubscription.mutate({ memberId: member.id, tier: e.target.value })}
          className="rounded border border-line bg-transparent px-2 py-1 text-xs text-primary"
        >
          {TIERS.map((t) => (
            <option key={t} value={t}>
              {t}
            </option>
          ))}
        </select>
      </td>
      <td className="px-3 py-2">
        <select
          aria-label={`Status for ${member.email}`}
          value={sub?.status ?? "pending"}
          onChange={(e) => updateSubscription.mutate({ memberId: member.id, status: e.target.value })}
          className="rounded border border-line bg-transparent px-2 py-1 text-xs text-primary"
        >
          {STATUSES.map((s) => (
            <option key={s} value={s}>
              {s}
            </option>
          ))}
        </select>
      </td>
      <td className="px-3 py-2 text-xs text-secondary">
        {sub?.last_trade_activity_at ? formatDateTime(sub.last_trade_activity_at) : "never"}
      </td>
    </tr>
  );
}

export function MembersPanel() {
  const members = useMembers();

  if (!members.data) return null;
  if (members.data.length === 0) {
    return <p className="px-4 py-8 text-sm text-secondary sm:px-6">No members yet.</p>;
  }

  return (
    <div className="overflow-x-auto border-b border-line">
      <table className="w-full min-w-[560px] text-sm">
        <thead>
          <tr className="text-left text-xs uppercase tracking-wide text-secondary">
            <th className="px-3 py-2 font-normal">Email</th>
            <th className="px-3 py-2 font-normal">Broker</th>
            <th className="px-3 py-2 font-normal">Tier</th>
            <th className="px-3 py-2 font-normal">Status</th>
            <th className="px-3 py-2 font-normal">Last trade</th>
          </tr>
        </thead>
        <tbody>
          {members.data.map((m) => (
            <MemberRow key={m.id} member={m} />
          ))}
        </tbody>
      </table>
    </div>
  );
}
