# Deploying SignalRoom

Not deployable to the shared cPanel hosting account this was checked
against (no Python app support, no persistent processes, no WebSocket
proxying on shared plans — see the project chat history for that check).
This covers the paths that actually work: a container host (a VPS, or a
PaaS that runs your `Dockerfile`), which is what SignalRoom is packaged
for.

**Not verified against a live deployment** — this environment has no
Docker installed to build/run the image against, and no target host to
deploy to. The `Dockerfile`, `docker-entrypoint.sh`, and `Procfile` are
correct by inspection and reuse patterns already proven elsewhere in this
project (gunicorn+uvicorn is the standard production combo for FastAPI;
`alembic upgrade head` is the same migration step already verified
working locally) — but treat the very first deploy as the actual test,
and watch its logs.

## What you need, regardless of host

```
DATABASE_URL=postgresql+psycopg://user:password@host:5432/signalroom
JWT_SECRET=<random, e.g. python -c "import secrets; print(secrets.token_hex(32))">
JWT_REFRESH_SECRET=<a different random value>
ADMIN_EMAIL=you@yourdomain.com
ADMIN_PASSWORD=<a strong password>
ENVIRONMENT=production
LOG_LEVEL=INFO
```

Use Postgres, not SQLite, for anything with real users — SQLite has no
real concurrent-writer story, and `docker-entrypoint.sh` deliberately
defaults to a single gunicorn worker specifically because of that (raise
`WEB_CONCURRENCY` only once `DATABASE_URL` is Postgres).

## Option A: a VPS (DigitalOcean, Hetzner, Linode, ...)

```bash
# on the VPS, with Docker installed:
git clone <your-repo-url> signalroom && cd signalroom
cp .env.example .env    # fill in the values above
docker build -t signalroom .
docker run -d --name signalroom --env-file .env -p 8000:8000 --restart unless-stopped signalroom
```

Put a reverse proxy (nginx, Caddy) in front for TLS and to proxy
WebSocket upgrades:

```nginx
location / {
    proxy_pass http://127.0.0.1:8000;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_set_header Host $host;
}
```

Caddy does this by default with no extra config — `reverse_proxy
127.0.0.1:8000` in a Caddyfile is enough, including WebSocket upgrades.

A managed Postgres add-on (DigitalOcean Managed Databases, or a Postgres
container alongside this one) covers the database.

## Option B: a PaaS that builds from a Dockerfile (Railway, Render, Fly.io)

All three detect and build `Dockerfile` automatically on a git push and
handle TLS + WebSocket proxying for you — no nginx config needed. Steps
are the same shape on each: connect the repo, set the environment
variables above (the platform sets `PORT` itself — `docker-entrypoint.sh`
already reads it), add a Postgres instance (each of these platforms
offers one with one click), deploy.

## If your platform only supports a Procfile (no Docker)

The `Procfile` runs migrations then starts gunicorn, but — unlike the
Dockerfile — it does **not** build the dashboard for you (a buildpack
runs `pip install`, not `npm run build`). Either:
- build `web/dist` locally (`cd web && npm run build`) and commit it, or
- configure the platform's multi-buildpack support to run a Node
  buildpack before the Python one.

Prefer the Dockerfile path if the platform supports it — it's
self-contained and this gap doesn't exist there.

## After first deploy

- Watch the startup logs for the admin bootstrap's TOTP enrollment line
  (`admin_user_created_scan_this_totp_uri_now`) — logged once, add it to
  an authenticator app immediately.
- Confirm `GET /docs` loads and the dashboard loads at `/`.
- Confirm a WebSocket actually connects from the deployed dashboard (open
  it, log in, check the browser's network tab for a `101 Switching
  Protocols` on `/ws`) — this is the one thing most likely to silently
  fail if a reverse proxy in front of the app isn't configured for
  WebSocket upgrades.
