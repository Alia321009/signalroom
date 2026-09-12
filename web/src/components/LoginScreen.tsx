import { useState } from "react";
import { login, register, verifyTotp } from "../lib/auth";

export function LoginScreen() {
  const [mode, setMode] = useState<"login" | "register">("login");
  const [step, setStep] = useState<"credentials" | "totp">("credentials");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [code, setCode] = useState("");
  const [tempToken, setTempToken] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function handleCredentials(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      const token = mode === "login" ? await login(email, password) : await register(email, password);
      setTempToken(token);
      setStep("totp");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong");
    } finally {
      setBusy(false);
    }
  }

  async function handleTotp(e: React.FormEvent) {
    e.preventDefault();
    if (!tempToken) return;
    setError(null);
    setBusy(true);
    try {
      await verifyTotp(tempToken, code);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Verification failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-ground px-4">
      <div className="w-full max-w-sm">
        <h1 className="mb-1 text-center text-lg font-semibold tracking-tight text-primary">SignalRoom</h1>
        <p className="mb-8 text-center text-sm text-secondary">Live gold calls, entry to close.</p>

        {step === "credentials" ? (
          <form onSubmit={handleCredentials} className="flex flex-col gap-4" aria-label={mode === "login" ? "Login" : "Sign up"}>
            <label className="flex flex-col gap-1 text-sm text-secondary">
              Email
              <input
                type="email" required autoFocus value={email} onChange={(e) => setEmail(e.target.value)}
                className="rounded border border-line bg-transparent px-3 py-2 text-primary outline-none focus:border-gold"
              />
            </label>
            <label className="flex flex-col gap-1 text-sm text-secondary">
              Password
              <input
                type="password" required value={password} onChange={(e) => setPassword(e.target.value)}
                className="rounded border border-line bg-transparent px-3 py-2 text-primary outline-none focus:border-gold"
              />
            </label>
            {error && <p className="text-sm text-loss">{error}</p>}
            <button type="submit" disabled={busy} className="mt-2 rounded bg-gold py-2 text-sm font-medium text-ground disabled:opacity-50">
              {busy ? "Please wait…" : mode === "login" ? "Log in" : "Create account"}
            </button>
            <button
              type="button"
              onClick={() => {
                setMode(mode === "login" ? "register" : "login");
                setError(null);
              }}
              className="text-xs text-secondary underline"
            >
              {mode === "login" ? "Need an account? Sign up free" : "Already have an account? Log in"}
            </button>
          </form>
        ) : (
          <form onSubmit={handleTotp} className="flex flex-col gap-4" aria-label="Two-factor verification">
            <label className="flex flex-col gap-1 text-sm text-secondary">
              6-digit code (leave blank if you haven't set up 2FA)
              <input
                type="text" inputMode="numeric" pattern="[0-9]*" autoFocus value={code} onChange={(e) => setCode(e.target.value)}
                className="rounded border border-line bg-transparent px-3 py-2 font-mono text-primary tabular-nums outline-none focus:border-gold"
              />
            </label>
            {error && <p className="text-sm text-loss">{error}</p>}
            <button type="submit" disabled={busy} className="mt-2 rounded bg-gold py-2 text-sm font-medium text-ground disabled:opacity-50">
              {busy ? "Verifying…" : "Continue"}
            </button>
            <button
              type="button"
              onClick={() => {
                setStep("credentials");
                setCode("");
                setError(null);
              }}
              className="text-xs text-secondary underline"
            >
              Back
            </button>
          </form>
        )}
      </div>
    </div>
  );
}
