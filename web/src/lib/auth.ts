// Auth state and token lifecycle, matching app/routers/auth.py: POST
// /auth/register (members) or /auth/login (both roles) -> temp_token,
// then POST /auth/verify-2fa (an empty totp_code is valid for a member
// who hasn't enrolled 2FA; the admin account always requires a real one)
// -> access+refresh JWT. POST /auth/refresh -> new access token.
//
// Access token: kept in memory only, never touches storage. Refresh
// token: persisted to localStorage so a reload doesn't force a re-login.

const REFRESH_KEY = "sr_refresh_token";

let accessToken: string | null = null;
let refreshToken: string | null = localStorage.getItem(REFRESH_KEY);
let currentRole: "admin" | "member" | null = null;

type AuthListener = (authed: boolean) => void;
const listeners = new Set<AuthListener>();

function notify() {
  for (const l of listeners) l(accessToken !== null);
}

export function onAuthChange(listener: AuthListener): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

export function getAccessToken(): string | null {
  return accessToken;
}

export function getRole(): "admin" | "member" | null {
  return currentRole;
}

export function isAuthenticated(): boolean {
  return accessToken !== null;
}

function setTokens(access: string, refresh: string | null): void {
  accessToken = access;
  if (refresh !== null) {
    refreshToken = refresh;
    localStorage.setItem(REFRESH_KEY, refresh);
  }
  // JWTs are three dot-separated base64url segments; the payload carries
  // no role claim today (app/auth.py only signs {sub, type, iat, exp}), so
  // role is discovered from whoami (GET /members/me) right after auth
  // rather than decoded from the token -- see fetchAndCacheRole below.
  notify();
}

export function clearTokens(): void {
  accessToken = null;
  refreshToken = null;
  currentRole = null;
  localStorage.removeItem(REFRESH_KEY);
  notify();
}

interface TempTokenResponse {
  temp_token: string;
}

interface TokenPairResponse {
  access_token: string;
  refresh_token: string;
}

interface AccessTokenResponse {
  access_token: string;
}

async function parseErrorDetail(res: Response, fallback: string): Promise<string> {
  try {
    const body = await res.json();
    if (body && typeof body.detail === "string") return body.detail;
  } catch {
    // not JSON -- use fallback
  }
  return fallback;
}

export async function register(email: string, password: string): Promise<string> {
  const res = await fetch("/auth/register", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!res.ok) {
    throw new Error(await parseErrorDetail(res, res.status === 409 ? "An account with this email already exists" : `Registration failed (${res.status})`));
  }
  const data = (await res.json()) as TempTokenResponse;
  return data.temp_token;
}

export async function login(email: string, password: string): Promise<string> {
  const res = await fetch("/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!res.ok) {
    throw new Error(await parseErrorDetail(res, res.status === 401 ? "Invalid email or password" : `Login failed (${res.status})`));
  }
  const data = (await res.json()) as TempTokenResponse;
  return data.temp_token;
}

/** totpCode may be "" -- valid for a member with no TOTP enrolled; the
 * admin account always rejects an empty code. */
export async function verifyTotp(tempToken: string, totpCode: string): Promise<void> {
  const res = await fetch("/auth/verify-2fa", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ temp_token: tempToken, totp_code: totpCode }),
  });
  if (!res.ok) {
    throw new Error(await parseErrorDetail(res, res.status === 401 ? "Invalid or expired code" : `Verification failed (${res.status})`));
  }
  const data = (await res.json()) as TokenPairResponse;
  setTokens(data.access_token, data.refresh_token);
  await fetchAndCacheRole();
}

async function fetchAndCacheRole(): Promise<void> {
  try {
    const res = await fetch("/members/me", { headers: { Authorization: `Bearer ${accessToken}` } });
    if (res.ok) {
      const body = await res.json();
      currentRole = body.role;
      notify();
    }
  } catch {
    // best-effort -- a failed role fetch just leaves currentRole null,
    // and App.tsx treats "authed but role unknown" as a brief loading
    // state, not a crash
  }
}

let refreshInFlight: Promise<string | null> | null = null;

export async function refreshAccessToken(): Promise<string | null> {
  if (refreshInFlight) return refreshInFlight;

  // Built as a separate local `promise`, assigned to the module-level
  // guard only afterwards, with clearing done via a real .finally()
  // promise-chain callback -- not a try/finally inside the async body.
  // A synchronously-resolving body (e.g. no refresh token stored) would
  // otherwise have its try/finally reset run BEFORE the outer assignment
  // finishes, letting that assignment immediately clobber the reset back
  // to a stale resolved promise. Lesson learned and documented the hard
  // way in the sibling trading-bot project; applied correctly here from
  // the start.
  const promise = (async () => {
    try {
      if (!refreshToken) return null;
      const res = await fetch("/auth/refresh", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: refreshToken }),
      });
      if (!res.ok) {
        clearTokens();
        return null;
      }
      const data = (await res.json()) as AccessTokenResponse;
      accessToken = data.access_token;
      notify();
      return accessToken;
    } catch {
      return null;
    }
  })();

  refreshInFlight = promise;
  promise.finally(() => {
    if (refreshInFlight === promise) refreshInFlight = null;
  });
  return promise;
}

export function logout(): void {
  clearTokens();
}
