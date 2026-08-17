# Deployment Guide

Quick reference for deploying Lev LaChayal. For architecture/dev details see `README.md`.

## How it's shipped

One **unified image**: the root `Dockerfile` builds the React app and bakes it into the FastAPI backend image (served from `/`, API under `/api`, uploads under `/uploads`). No separate frontend service, no CORS to configure. A second, lighter service runs the ARQ background worker from `backend/Dockerfile`.

| Service | Root directory | Config file | Runs |
|---|---|---|---|
| `web` | repo root | `railway.json` | migrations, then `uvicorn` (serves API + frontend) |
| `worker` | `backend/` | `railway.worker.json` | `arq app.worker.WorkerSettings` |

## Deploy to Railway

1. **Provision plugins first**: Add Railway's **PostgreSQL** and **Redis** templates to the project — you'll reference their connection strings as variables below.
2. **Create the `web` service**: point it at this repo, root directory = repo root (not `backend/`). Railway will find `railway.json` automatically.
3. **Create the `worker` service**: same repo, root directory = `backend/`, config file = `railway.worker.json` (set this explicitly in the service's settings — Railway defaults to `railway.json` otherwise).
4. **Set environment variables** (table below), then deploy.
5. **Seed the first admin** (one-time, after first successful deploy):
   ```bash
   railway run --service web python -m app.scripts.seed_admin admin@lev.org "Admin Name" "a-strong-password"
   ```
6. Log in, go to **Staff**, create additional accounts. Residents can also self-register at `/register` and get approved from **Registrations**.

## Environment variables

### `web` service

| Variable | Required | Value | Notes |
|---|---|---|---|
| `DATABASE_URL` | Yes | `${{Postgres.DATABASE_URL}}` | **Rewrite the scheme** to `postgresql+asyncpg://` — Railway's plugin gives plain `postgresql://` |
| `REDIS_URL` | Yes | `${{Redis.REDIS_URL}}` | Shared with `worker` |
| `JWT_SECRET_KEY` | Yes | `openssl rand -hex 32` | Rotating invalidates all sessions |
| `ENVIRONMENT` | Yes | `production` | **Never** `test` in production — that mounts a `/testing/reset` endpoint that drops all tables |
| `UPLOAD_DIR` | No | `uploads` (default) | Attach a Railway **volume** at this path or damage-report photos vanish on every redeploy |
| `JWT_ALGORITHM` | No | `HS256` (default) | |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | No | `15` (default) | |
| `REFRESH_TOKEN_EXPIRE_DAYS` | No | `30` (default) | |
| `CORS_ORIGINS` | No | usually unneeded | Same origin serves both now; only needed for a separate cross-origin client |
| `MAX_UPLOAD_SIZE_MB` | No | `10` (default) | |
| `PORT` | Auto | — | Railway injects this |

### `worker` service

| Variable | Required | Value |
|---|---|---|
| `DATABASE_URL` | Yes | same as `web` |
| `REDIS_URL` | Yes | same as `web` — this is how they share the ARQ queue |
| `ENVIRONMENT` | Yes | `production` |

No `JWT_SECRET_KEY` / `CORS_ORIGINS` / `PORT` — the worker never serves HTTP.

## Local production-like check before deploying

```bash
docker compose up --build     # NOT docker-compose.dev.yml — that's for hot-reload dev
```

This builds the same image Railway deploys and runs it against local Postgres/Redis on `http://localhost:8000`. Use this to catch anything that only breaks in the production build (it's caught real bugs before — see "Known gotchas" below).

## Database migrations

Migrations run automatically on `web` startup (`alembic upgrade head` before `uvicorn` starts). To run one manually against a deployed environment:

```bash
railway run --service web alembic upgrade head
```

Current migrations: `0001_initial_schema` → `0002_resident_portal` (adds the `resident` role, announcements, meal invitations) → `0003_registration_requests` (self-registration queue).

## Known gotchas (already fixed in this codebase, but relevant if you extend it)

- **Datetime columns** need `sa_type=DateTime(timezone=True)` explicitly — SQLite tolerates naive datetimes, Postgres/asyncpg doesn't.
- **Circular foreign keys** (e.g. `users.resident_id` ↔ `residents.assigned_av_bayit_id`) need `use_alter=True` on one side, or schema drop/create breaks on Postgres.
- Behind Railway's proxy, uvicorn needs `--proxy-headers --forwarded-allow-ips='*'` (already set in `railway.json`) or the login rate limiter sees every request as coming from the same IP.
- If you ever run `docker compose up` locally without `-f docker-compose.dev.yml` while the dev stack is already running, it'll fail silently on port conflicts (5432/6379/8000 already taken) rather than erroring loudly — check `docker ps -a` for containers stuck in `Created` if something seems off.

## Rollback

Railway keeps prior deployments — redeploy an older build from its dashboard. Database migrations are forward-only in practice; if a migration needs undoing, use `alembic downgrade <revision>` against that environment rather than relying on a code rollback to fix schema state.
