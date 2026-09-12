#!/bin/sh
set -e

echo "Running migrations..."
python -m alembic upgrade head

echo "Starting SignalRoom on port ${PORT:-8000}..."
# --workers: safe to raise above 1 only once DATABASE_URL points at
# Postgres -- SQLite has no real concurrent-writer story, and multiple
# worker processes each opening their own SQLite connection is a good way
# to hit "database is locked" under real traffic.
exec gunicorn app.main:app \
  --worker-class uvicorn.workers.UvicornWorker \
  --workers "${WEB_CONCURRENCY:-1}" \
  --bind "0.0.0.0:${PORT:-8000}" \
  --access-logfile - \
  --error-logfile -
