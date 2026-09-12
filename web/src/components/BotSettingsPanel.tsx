import { useState } from "react";
import { useBotSettings, useRotateApiKey, useUpdateBotSettings } from "../hooks/useApi";

export function BotSettingsPanel() {
  const settings = useBotSettings();
  const updateSettings = useUpdateBotSettings();
  const rotateKey = useRotateApiKey();
  const [symbolsInput, setSymbolsInput] = useState("");
  const [revealedKey, setRevealedKey] = useState<string | null>(null);

  if (!settings.data) return null;

  return (
    <div className="flex flex-col gap-4 border-b border-line px-4 py-5 sm:px-6">
      <h2 className="text-sm font-semibold uppercase tracking-wide text-secondary">Hands-free (AI bot)</h2>

      <label className="flex items-center gap-3 text-sm text-primary">
        <input
          type="checkbox"
          checked={settings.data.enabled}
          onChange={(e) => updateSettings.mutate({ enabled: e.target.checked })}
          className="h-4 w-4 accent-gold"
        />
        Auto-execute calls on my MT5 account
      </label>

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
        <label className="flex flex-col gap-1 text-xs text-secondary">
          Risk % per trade
          <input
            type="number" step="0.1" min="0.1" max="5" defaultValue={settings.data.risk_pct}
            onBlur={(e) => updateSettings.mutate({ risk_pct: Number(e.target.value) })}
            className="rounded border border-line bg-transparent px-2 py-1 text-sm text-primary tabular-nums"
          />
        </label>
        <label className="flex flex-col gap-1 text-xs text-secondary">
          Max daily loss %
          <input
            type="number" step="0.5" min="0.5" max="20" defaultValue={settings.data.max_daily_loss_pct}
            onBlur={(e) => updateSettings.mutate({ max_daily_loss_pct: Number(e.target.value) })}
            className="rounded border border-line bg-transparent px-2 py-1 text-sm text-primary tabular-nums"
          />
        </label>
        <label className="col-span-2 flex flex-col gap-1 text-xs text-secondary sm:col-span-1">
          Symbols (blank = all)
          <input
            type="text" placeholder={settings.data.symbols.join(", ") || "e.g. XAUUSD"}
            value={symbolsInput}
            onChange={(e) => setSymbolsInput(e.target.value)}
            onBlur={() => {
              if (symbolsInput.trim() === "") return;
              updateSettings.mutate({ symbols: symbolsInput.split(",").map((s) => s.trim()).filter(Boolean) });
            }}
            className="rounded border border-line bg-transparent px-2 py-1 text-sm text-primary"
          />
        </label>
      </div>

      <div className="flex flex-col gap-2">
        <p className="text-xs text-secondary">
          Magic number <span className="tabular-nums text-primary">{settings.data.magic}</span> — install the local
          executor (<code className="text-primary">python -m executor.run</code>) with this account's API key.
        </p>
        <button
          type="button"
          onClick={() => rotateKey.mutate(undefined, { onSuccess: (data) => setRevealedKey(data.api_key) })}
          className="self-start rounded border border-line px-3 py-1.5 text-xs text-secondary hover:text-primary"
        >
          {rotateKey.isPending ? "Generating…" : "Generate / rotate API key"}
        </button>
        {revealedKey && (
          <div className="rounded border border-gold/40 bg-gold/5 px-3 py-2 text-xs">
            <p className="mb-1 text-secondary">
              Shown once — put this in the executor's <code className="text-primary">.env</code> as{" "}
              <code className="text-primary">API_KEY</code>:
            </p>
            <code className="break-all font-mono text-primary">{revealedKey}</code>
          </div>
        )}
      </div>
    </div>
  );
}
