# SignalRoom

A paid trading-signal service platform: one trader (the admin) posts
discretionary calls (entry, stop, up to three take-profit targets, a
validity window), members see them live on a dashboard, and members who
want it can auto-execute those same calls on their own MT5 account via a
local bot.

Built after analyzing [growthclubpk.com](https://growthclubpk.com) — a
real gold-signal service with this exact shape (signals + optional MT5
auto-bot + broker-referral/paid-subscription funding). This is a fresh,
independent implementation of that product shape, not a clone of their
code, brand, or content.

## Architecture

```
signalroom/
├── app/            FastAPI backend — multi-tenant: members, subscriptions,
│                   calls, bot settings. SQLite locally, Postgres-ready.
├── web/            React 18 + TypeScript + Vite dashboard (member + admin views)
├── executor/       The LOCAL auto-bot — runs on a MEMBER's own machine
│                   next to their own already-logged-in MT5 terminal
├── alembic/        DB migrations
└── tests/          pytest, 95% coverage across app/ + executor/
```

**Why the executor is a separate, locally-run program**: MT5's Python
package attaches to one already-running, already-logged-in terminal via
IPC — it cannot centrally manage many different members' broker logins
from one server process the way a single-account bot can. The correct,
standard approach for a signal-copier product (and what real ones do) is
exactly this: a small program the member runs themselves, next to their
own terminal, that polls the service and mirrors calls locally. The
service never sees or stores a member's broker password.

## What's real and tested vs. known V1 gaps

**Done, tested (107 backend tests, 95% coverage; 43 frontend tests):**
- Full auth: member self-registration (no forced 2FA — matches the real
  site's own "just log in" UX), admin bootstrap with mandatory TOTP,
  JWT access/refresh, rate-limited login.
- The core product: admin posts/updates calls, members see them live via
  WebSocket, a public (unauthenticated) closed-calls track record.
- Multi-tenant subscription tracking (tier, status, broker, paid-until),
  admin-managed for now (see Payments below).
- Per-member bot settings (risk %, symbols, a dedicated API key) and the
  local executor: polls for calls, sizes positions by the member's own
  risk_pct and account balance, splits volume across up to 3 TP legs,
  closes positions when a call closes, reports fills back to the server.
- Two real bugs caught by tests during this build (not shipped):
  a WebSocket "is this call new or updated" check that compared
  `created_at == updated_at`, which — since SQLAlchemy stamps each column
  with a separate timestamp call at flush time — would almost never
  actually be equal even on a brand-new row; and a volume-splitting bug
  where rounding a per-leg size *up* to exactly `volume_min` could still
  over-allocate across multiple legs, producing a computed 0.0-sized
  leg after the rounding remainder was corrected back out of it — a
  zero-volume order a real broker would simply reject.

**Known V1 limitations, stated plainly rather than silently assumed:**
- **Payments are manual.** No Stripe/USDT gateway is wired in — an admin
  sets a member's tier/status by hand (`PATCH /members/{id}/subscription`).
  Adding a real gateway means: a webhook endpoint that flips `tier`/
  `paid_until` on a successful charge, and a checkout page in `web/`. The
  data model (`Subscription.tier`, `.paid_until`) is already shaped for it.
- **The executor uses market orders, not pending/limit orders.** A call is
  executed the instant it's first seen, not placed as a limit order
  sitting at the call's own `entry` price waiting to be touched. Building
  full pending-order lifecycle (place → wait → cancel on expiry → modify)
  is real additional scope. The call's `entry` is still recorded, so the
  gap between requested and actual fill price is visible in the data.
- **`record_execution_report` isn't idempotent.** A crashed executor that
  retries a report could double-count a fill. Low-risk in practice (the
  executor's own local state file is what actually prevents double-
  opening a position), but a production hardening pass should add an
  idempotency key.
- **No compliance/regulatory review.** Running a paid signal/auto-trading
  service can trigger investment-adviser or money-services licensing
  requirements depending on jurisdiction — this is a software build, not
  legal advice; get real legal review before taking real members' money.

## Setup

```powershell
cd C:\Users\HP\signalroom
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements\dev.txt
copy .env.example .env
# edit .env: JWT_SECRET/JWT_REFRESH_SECRET (random values), ADMIN_EMAIL/ADMIN_PASSWORD
.\.venv\Scripts\python.exe -m alembic upgrade head
```

## Running the backend

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

The admin's TOTP enrollment URI is logged once on first startup — add it
to an authenticator app immediately. Interactive API docs at
`http://localhost:8000/docs`.

## Running the dashboard

```powershell
cd web
npm install
npm run dev
```

Proxies every backend path to `:8000` in dev (`web/vite.config.ts`); in
production, `app/main.py` serves `web/dist` directly, same-origin.

## Running the local executor (a member's own machine)

```powershell
pip install -r requirements\executor.txt
copy .env.example .env
# set API_BASE_URL and API_KEY (get the key from the dashboard's
# "Hands-free" panel -- shown once, on generation/rotation)
python -m executor.run
```

Requires MT5 already installed, logged in, and running on that machine.

## Testing

```powershell
.\.venv\Scripts\python.exe -m pytest --cov --cov-report=term-missing
cd web && npm test
```

`executor/mt5_client.py` is deliberately excluded from coverage (no fake
MT5 terminal to test against — the same convention the sibling
trading-bot project uses for its own MT5 adapter). Everything else in
`executor/` — sizing math, local state persistence, and the poll/execute/
report orchestration loop — is tested via `httpx.MockTransport` and
monkeypatched MT5 calls, with no real terminal needed.

## Live smoke test

Verified against a real running instance: admin bootstrap + TOTP login,
a member registering and logging in with no 2FA, the admin posting a
real call, the member seeing it via `GET /calls`, picking a broker,
enabling the bot and generating an API key, the executor's own endpoints
(`GET /executor/settings`, `GET /executor/calls`) correctly filtering by
that member's symbol whitelist, the admin closing the call with an
outcome, and that closed call appearing in the public, unauthenticated
track record.
