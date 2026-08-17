# Lev LaChayal Residence Management App

Production-ready, mobile-first system for managing resident presence, food inventory, maintenance/cleaning requests, meal hosting coordination, resident profiles, and house announcements — with dedicated experiences for Administrators, Av/Eim Bayit host families, and Residents.

## Stack

| Layer | Technology |
|---|---|
| Backend | FastAPI (async), SQLModel, PostgreSQL, Alembic |
| Background jobs | ARQ + Redis |
| Frontend | React + Vite + TypeScript + Tailwind CSS, served as a PWA (installable, "Add to Home Screen") |
| Data fetching | TanStack Query (used in all resident/dashboard/announcement pages; older admin CRUD pages still use plain fetch — a good next-step migration) |
| Auth | OAuth2 password flow, JWT access tokens, rotating refresh tokens, 4 roles (`admin`, `staff`, `av_bayit`, `resident`) |
| E2E tests | Playwright, desktop + mobile viewports (iPhone 13, Pixel 5), with a DB-reset strategy for isolated runs |
| Deployment | Docker (multi-stage, unified single-origin image), Railway |

## Architecture

The backend is layered so business logic never leans on FastAPI or the database driver directly:

```
backend/app/
  api/          # thin route handlers (HTTP <-> schemas)
  services/     # business logic, transaction-scoped
  repositories/ # async SQLAlchemy queries only
  models/       # SQLModel table definitions
  schemas/      # Pydantic request/response contracts
  core/         # config, db session, security, storage
  worker.py     # ARQ background jobs (low-stock alerts, meal reminders)
```

Every write goes through `app.core.db.get_session`, which commits on clean exit and **rolls back automatically on any exception** — no route or service needs to manage transactions manually.

In production, FastAPI serves the built React app directly (single origin — see "Unified deployment" below) alongside the API under `/api` and uploaded files under `/uploads`.

## Users & access

**Residents now have real login accounts** (role `resident`), linked to their `Resident` profile via a nullable `User.resident_id` FK — the profile record and the login credential are kept as separate concepts on purpose, so nothing about the existing resident data model had to change. Everyone logs in through the same page; the app then routes by role:

| Role | Portal | Can do |
|---|---|---|
| `admin` | Staff shell (desktop + mobile bottom nav) | Everything, plus creating/managing every other account type |
| `staff` | Staff shell | Full building operations: residents, rooms, inventory, maintenance/cleaning, announcements |
| `av_bayit` | Staff shell (scoped) | Read-only on residents/inventory (to plan hosting); logs meal hosting records and sends meal invitations to *their assigned residents*; posts announcements *only* to their own assigned residents; **cannot** edit residents, rooms, inventory, or maintenance tickets |
| `resident` | Dedicated mobile portal at `/r/*` | Toggle their own Home/Away status, view the daily announcement feed, file damage/cleaning reports (with photo upload), accept/decline meal invitations. Cannot browse other residents or reach any staff route — enforced server-side, not just hidden in the UI |

All of this is enforced in the API layer (`app/api/deps.py`: `StaffOrAdmin`, `NotResident`, `CurrentResident`), not just the UI — e.g. `GET /residents` 403s for a resident account even if they hit the URL directly.

**Creating accounts:** the first admin can't self-register (registration requires an existing admin to authorize it), so it's bootstrapped from the backend:

```bash
# local dev (docker-compose.dev.yml, service name "backend"):
docker compose -f docker-compose.dev.yml exec backend python -m app.scripts.seed_admin admin@lev.org "Admin Name" "a-strong-password"

# production-like stack (docker-compose.yml, service name "web") or Railway:
docker compose exec web python -m app.scripts.seed_admin admin@lev.org "Admin Name" "a-strong-password"
```

After that, any admin creates every other account type — staff, av_bayit, additional admins, **and resident logins** — from the **Staff** page in the app nav (admin-only). Creating a resident login requires picking an existing `Resident` profile from a dropdown; the login is then locked to that one profile.

## Local development

Requires Docker Desktop. Two compose files, two different jobs:

- **`docker-compose.dev.yml`** — day-to-day development. Backend runs with `--reload` and bind-mounted source; frontend runs the Vite dev server with hot reload. Use this.
- **`docker-compose.yml`** (default) — production-like. Builds the same unified image Railway deploys (frontend baked into the backend image, no separate frontend container). Slower to iterate with, but useful for a final "does this actually work as it will in prod" check before deploying.

```bash
cp backend/.env.example backend/.env   # edit secrets as needed
docker compose -f docker-compose.dev.yml up --build
```

- Backend API: http://localhost:8000 (docs at `/docs`)
- Frontend: http://localhost:5173 (Vite dev server, hot reload, proxies `/api` and `/uploads` to the backend)
- Postgres: localhost:5432, Redis: localhost:6379

The backend container runs `alembic upgrade head` automatically on startup. See "Users & access" above for creating the first admin login.

### Running without Docker

```bash
cd backend
python -m venv .venv && source .venv/bin/activate   # or .venv\Scripts\activate on Windows
pip install -r requirements-dev.txt
alembic upgrade head
uvicorn app.main:app --reload

# separate terminal: background worker
arq app.worker.WorkerSettings
```

```bash
cd frontend
npm install
npm run dev
```

## Testing

**Backend (pytest, in-memory SQLite):**
```bash
cd backend
pip install -r requirements-dev.txt
pytest
```

**E2E (Playwright):** runs against three projects — desktop Chrome, iPhone 13, and Pixel 5 — covering login/role-routing (including that a resident account can never reach a staff route), the presence board, and role-specific flows (resident status toggle, Av/Eim Bayit meal invitations). The suite resets the database to a known, seeded state before every run via a `/api/v1/testing/reset` endpoint that is *only* mounted when `ENVIRONMENT=test` — it never exists in staging/production builds.

```bash
# terminal 1: backend in test mode (separate DB recommended)
cd backend
ENVIRONMENT=test uvicorn app.main:app --port 8000

# terminal 2: frontend
cd frontend
npm run dev

# terminal 3: run the suite
cd frontend
npx playwright install --with-deps chromium webkit
npm run test:e2e
```

Note: `ENVIRONMENT=test` also relaxes the login rate limit (see Security notes) — a full Playwright run logs in many times across roles/specs, which would otherwise trip the same 5/min limit real users are protected by.

**CI (`.github/workflows/ci.yml`):** runs on every push/PR — backend lint + pytest, a separate job that runs the real Alembic migrations (up and down) against a live Postgres service container to catch Postgres-only issues SQLite-backed tests can't, and frontend lint + typecheck + build.

## Database migrations

```bash
cd backend
alembic revision --autogenerate -m "describe the change"
alembic upgrade head
```

- `0001_initial_schema.py` — users, refresh tokens, rooms, residents (+ activity log), inventory items (+ transaction log), damage reports (+ status history), meal hosting records.
- `0002_resident_portal.py` — adds the `resident` role, `User.resident_id` / `Resident.assigned_av_bayit_id` links, damage-report `category` (damage vs. cleaning), `announcements`, and `meal_invitations`.

## Unified deployment (production)

The root-level `Dockerfile` builds the React app and copies its output into the backend image at `./static`; FastAPI serves it directly (see the catch-all route at the bottom of `app/main.py`) alongside `/api` and `/uploads` — one origin, no CORS setup needed for the browser, no separate nginx/frontend service. `docker-compose.yml` mirrors this for local validation; Railway deploys it via the root `railway.json`.

The ARQ worker doesn't need the frontend, so it still builds from `backend/Dockerfile` with its own `backend/railway.worker.json`.

*(The original split-service setup — a separate nginx-served frontend proxying to the backend — still exists as `frontend/Dockerfile` + `frontend/railway.json` + `backend/railway.json`, and still works if you'd rather deploy frontend and backend as independent services. The unified image above is the recommended default.)*

### Required environment variables

**`web` service** (repo root, `railway.json`, Dockerfile at repo root)

| Variable | Required | Example / source | Notes |
|---|---|---|---|
| `DATABASE_URL` | Yes | `${{Postgres.DATABASE_URL}}`, scheme rewritten to `postgresql+asyncpg://` | Railway's Postgres plugin gives a `postgresql://` URL by default — change the scheme to `postgresql+asyncpg://` for the async driver |
| `REDIS_URL` | Yes | `${{Redis.REDIS_URL}}` | Shared with the worker service |
| `JWT_SECRET_KEY` | Yes | 32+ byte random string (`openssl rand -hex 32`) | Rotating this invalidates all existing access/refresh tokens |
| `JWT_ALGORITHM` | No | `HS256` (default) | |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | No | `15` (default) | |
| `REFRESH_TOKEN_EXPIRE_DAYS` | No | `30` (default) | |
| `CORS_ORIGINS` | No | same origin now serves both, so usually unneeded | Comma-separated if you still need cross-origin access for something |
| `ENVIRONMENT` | Yes | `production` | Must **not** be `test` in production — that value mounts the `/testing/reset` endpoint, which drops all tables |
| `UPLOAD_DIR` | No | `uploads` (default) | Mount a Railway **volume** at this path, or damage-report photos are lost on every redeploy/restart |
| `MAX_UPLOAD_SIZE_MB` | No | `10` (default) | |
| `PORT` | Auto | — | Injected by Railway; the start command in `railway.json` already reads `$PORT` |

**Worker service** (root directory `backend/`, config file `railway.worker.json`)

| Variable | Required | Notes |
|---|---|---|
| `DATABASE_URL` | Yes | Same value as the web service |
| `REDIS_URL` | Yes | Same value as the web service — this is how web and worker share the ARQ queue |
| `ENVIRONMENT` | Yes | `production` |

No `JWT_SECRET_KEY`/`CORS_ORIGINS`/`PORT` needed — the worker never serves HTTP.

### One-time setup after first deploy

```bash
railway run --service web python -m app.scripts.seed_admin admin@lev.org "Admin Name" "a-strong-password"
```

## Security notes

- Passwords are hashed with bcrypt (min 8 chars, capped at bcrypt's 72-byte input limit); refresh tokens are stored only as SHA-256 hashes, never in plaintext.
- Refresh tokens rotate on every use; reuse of an already-rotated token is treated as theft and revokes the entire session chain (`AuthService.refresh`). That revocation is committed immediately, before the request returns its error — otherwise the request-scoped rollback would silently undo the very revocation meant to kill the session.
- Building-operations endpoints (residents, rooms, inventory, maintenance writes) require `staff` or `admin`. `av_bayit` accounts are read-only there, scoped to meal hosting/invitations and their own assigned residents. `resident` accounts can only ever act on their own profile — enforced via `CurrentResident`, not client-side checks. See "Users & access" above.
- Login and refresh are rate-limited (5/min and 20/min per IP in production, Redis-backed; relaxed automatically when `ENVIRONMENT=test` — see Testing). The backend's start command runs uvicorn with `--proxy-headers --forwarded-allow-ips='*'` so the real client IP is read from `X-Forwarded-For` — without this, every request behind Railway's (or any) reverse proxy looks like it came from the same IP, and the login limiter would count all users' attempts together instead of per-client.
- `/health` is a cheap liveness check (used by the container `HEALTHCHECK`); `/health/ready` additionally verifies Postgres and Redis connectivity — use that one for deploy-time smoke checks.
- All service-layer writes run inside the request-scoped session from `get_session`, which rolls back on any unhandled exception.
- Known trade-off: access tokens aren't individually revocable (standard for short-lived JWTs) — logout only revokes the refresh token, so a stolen access token stays valid until it expires (15 min default).
- Known limitation: damage-report photo uploads validate the client-supplied `Content-Type` header, which isn't tamper-proof. Fine for an internal tool; if this is ever exposed more broadly, sniff the actual file bytes (e.g. via `python-magic`) instead of trusting the header.
- Known gap: Av/Eim Bayit "reminder" notifications and low-stock alerts are logged by the ARQ worker (see `app/worker.py`), not delivered as real push notifications — wiring up actual mobile push (VAPID/web-push) is a reasonable next step but wasn't in scope here.

### Bugs this stack caught by actually running it

Several real bugs only surfaced when validated against a live Postgres instance in Docker (not the SQLite-backed unit tests, which quietly tolerate mismatches Postgres correctly rejects) — worth knowing if you extend the schema:
- **Timestamp columns must be explicitly `timezone=True`.** SQLModel's default mapping for a bare `datetime` field is a naive column; the app always writes tz-aware UTC values, and asyncpg rejects that mismatch outright (SQLite silently accepts it). See `sa_type=DateTime(timezone=True)` in `app/models/base.py` and similar — any new datetime field needs the same treatment.
- **Alembic + Postgres native ENUMs**: don't reuse the same `postgresql.ENUM(...)` Python object both to `CREATE TYPE` explicitly and as a column type in `op.create_table` — SQLAlchemy re-issues `CREATE TYPE` for every column reference and errors on the duplicate. Create the type via raw `op.execute(...)`, then build a fresh `ENUM(..., create_type=False)` per column (see `0001_initial_schema.py`).
- **pydantic-settings + `list[str]` env vars**: it tries to JSON-decode env values for list-typed fields before any custom validator runs, so a plain comma-separated string crashes on boot. `CORS_ORIGINS` is kept as a plain `str` with a `cors_origins` property that splits it, rather than a `list[str]` field.
- **Circular FKs need `name` *and* `use_alter=True`, not just `name`.** `User.resident_id` and `Resident.assigned_av_bayit_id` reference each other, so SQLAlchemy's metadata-driven `create_all`/`drop_all` (used by the `/testing/reset` endpoint and — if you ever add a genuinely cyclic scenario — test fixtures) can't topologically sort the two tables unless one FK is explicitly deferred to a post-`CREATE TABLE` `ALTER TABLE`. Naming the constraint alone raised a clearer error but didn't fix it; adding `use_alter=True` (see `app/models/user.py`) did. Hand-written Alembic migrations never hit this — they add columns one at a time, sidestepping the whole-graph sort — so this only bites metadata-driven create/drop.