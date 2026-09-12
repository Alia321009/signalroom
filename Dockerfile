# Multi-stage: build the dashboard, then run the API which serves it
# (app/main.py mounts web/dist same-origin -- same production topology
# the sibling trading-bot project uses). Works on any container host: a
# VPS with plain `docker run`, Railway, Render, Fly.io, etc.

FROM node:22-slim AS web-build
WORKDIR /web
COPY web/package.json web/package-lock.json ./
RUN npm ci
COPY web/ ./
RUN npm run build

FROM python:3.12-slim AS runtime
WORKDIR /srv

# psycopg[binary] needs no extra system libs; kept minimal deliberately --
# no compiler toolchain baked into the final image.
COPY requirements/base.txt requirements/base.txt
RUN pip install --no-cache-dir -r requirements/base.txt

COPY app/ app/
COPY alembic/ alembic/
COPY alembic.ini .
COPY docker-entrypoint.sh .
RUN chmod +x docker-entrypoint.sh

COPY --from=web-build /web/dist/ web/dist/

ENV PORT=8000
EXPOSE 8000

ENTRYPOINT ["./docker-entrypoint.sh"]
