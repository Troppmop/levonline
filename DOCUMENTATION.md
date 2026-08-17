# Lev LaChayal — Project Documentation

A residence management system for a Lev LaChayal-style facility (residents, host families, and staff), covering presence tracking, food inventory, maintenance/cleaning requests, meal hosting coordination, house announcements, and self-service resident registration. Ships as an installable, mobile-first PWA with role-specific portals.

For setup instructions see `README.md`. For deployment steps see `DEPLOYMENT.md`. This file explains **what the system is made of and what it does**.

---

## 1. Stack

| Layer | Technology |
|---|---|
| Backend | FastAPI (async), SQLModel (SQLAlchemy + Pydantic), PostgreSQL, Alembic |
| Background jobs | ARQ + Redis |
| Frontend | React + Vite + TypeScript + Tailwind CSS |
| Data fetching | TanStack Query (newer pages) / fetch + `useState` (older admin CRUD pages) |
| Auth | OAuth2 password flow, JWT access tokens, rotating refresh tokens |
| PWA | `vite-plugin-pwa` — installable, "Add to Home Screen," offline app shell |
| Deployment | Docker (multi-stage, unified single-origin image), Railway |
| Testing | pytest (backend, 34 tests), Playwright (E2E, desktop + iPhone 13 + Pixel 5) |

---

## 2. Project structure

```
levonline/
├── Dockerfile                    # unified prod image: builds frontend, bakes into backend image
├── docker-compose.yml            # production-like local stack (builds the unified image)
├── docker-compose.dev.yml        # dev stack: hot-reload backend + Vite dev server
├── railway.json                  # Railway config for the "web" service (repo root)
├── DEPLOYMENT.md / README.md
│
├── backend/
│   ├── Dockerfile                # backend-only image (used by the "worker" service)
│   ├── railway.json               # legacy split-service "web" config (alternative to root one)
│   ├── railway.worker.json        # Railway config for the "worker" service
│   ├── alembic/versions/          # 0001 → 0002 → 0003, see §7
│   ├── tests/                     # pytest suite, 34 tests across 9 files
│   └── app/
│       ├── main.py                # FastAPI app, middleware, error handlers, SPA static serving
│       ├── worker.py              # ARQ WorkerSettings — cron jobs, background tasks
│       ├── api/
│       │   ├── router.py          # aggregates all route modules under /api/v1
│       │   ├── deps.py            # auth dependencies: CurrentUser, StaffOrAdmin, NotResident, CurrentResident
│       │   ├── pagination.py      # shared offset/limit query-param dependency
│       │   └── routes/            # one file per resource (thin HTTP <-> schema handlers)
│       ├── services/               # business logic, one class per domain area
│       ├── repositories/           # async SQLAlchemy queries only, no business logic
│       ├── models/                 # SQLModel table definitions
│       ├── schemas/                 # Pydantic request/response contracts (separate from table models)
│       ├── core/                   # config, db session, security, logging, rate limiting, file storage
│       └── scripts/seed_admin.py   # bootstraps the very first admin account
│
└── frontend/
    ├── src/
    │   ├── App.tsx                 # all routing, role-based layout switching
    │   ├── layouts/ResidentLayout.tsx
    │   ├── components/BottomNav.tsx
    │   ├── hooks/useAuth.tsx       # auth context: login/logout/current user
    │   ├── api/client.ts           # fetch wrapper: token storage, auto-refresh-on-401
    │   ├── types/index.ts          # TS types mirroring backend schemas
    │   └── pages/
    │       ├── (staff shell)  Dashboard, Residents, Rooms, Inventory, Maintenance,
    │       │                  Meals, Announcements, RegistrationRequests, Admin, Profile
    │       ├── resident/      ResidentHome, ResidentReport, ResidentMeals
    │       └── (public)       Login, Register
    ├── public/icons/                # PWA icons (generated via scripts/generate-icons.mjs)
    └── e2e/                          # Playwright specs
```

**Backend layering rule**: `api/` never talks to the database directly — it calls a `service`, which orchestrates one or more `repository` calls inside a single transactional session. Every write goes through `app.core.db.get_session`, which **commits on clean exit and rolls back automatically on any exception**. No route or service manages transactions manually.

---

## 3. Users & access model

There is **one login page** for everyone. The app routes to a different experience based on role after login:

| Role | Portal | Summary |
|---|---|---|
| `admin` | Staff shell | Everything, plus creating/managing every other account type |
| `staff` | Staff shell | Full building operations: residents, rooms, inventory, maintenance/cleaning, announcements |
| `av_bayit` | Staff shell (scoped) | Read-only on residents/inventory; logs meal hosting and sends meal invitations to *their assigned residents only*; posts announcements only to their own assigned group |
| `resident` | Dedicated mobile portal at `/r/*` | Self-service: toggle own Home/Away status, view daily announcement feed, file damage/cleaning reports with photos, accept/decline meal invitations. Cannot browse other residents or reach any staff route |

**Residents are not merged with login accounts.** `User.resident_id` is a nullable FK linking a login to a `Resident` profile — this keeps "who can log in" separate from "resident profile data," so a resident can exist in the system (tracked by staff) long before or without ever having a login.

Access control is enforced **server-side**, not just hidden in the UI, via FastAPI dependencies in `app/api/deps.py`:
- `CurrentUser` — any authenticated user
- `StaffOrAdmin` — building-operations gate (residents/rooms/inventory/maintenance writes)
- `NotResident` — gate for roster-browsing endpoints (staff/admin/av_bayit; blocks resident accounts)
- `CurrentResident` — resolves the calling user's own linked `Resident` record, 403s for anyone else

### How accounts are created

1. **First admin**: bootstrapped via `python -m app.scripts.seed_admin <email> "<name>" <password>` (run once, from the deployed container — see `DEPLOYMENT.md`).
2. **Everyone else**: an admin creates staff/av_bayit/admin accounts, or links a resident login to an existing `Resident` profile, from the **Staff** page (`/admin`, admin-only).
3. **Self-registration**: residents can also apply themselves — see §4.1.

---

## 4. Features by module

### 4.1 Authentication & registration

- **Login**: OAuth2 password flow → short-lived JWT access token (15 min default) + opaque refresh token (30 days default, stored server-side only as a SHA-256 hash).
- **Refresh rotation**: every refresh call issues a new token and revokes the old one. Replaying an already-used refresh token is treated as theft and revokes the *entire* session chain for that user — and that revocation is committed immediately (before the request's own rollback-on-error would otherwise undo it).
- **Rate limiting**: login (5/min) and refresh (20/min) are IP-limited via Redis-backed `slowapi`; self-registration is capped at 5/hour. Limits relax automatically when `ENVIRONMENT=test` so E2E suites logging in repeatedly don't trip them.
- **Self-registration queue** (`ResidentRegistrationRequest` model): a soldier fills out `/register` (name, email, phone, password) — this creates a **pending application only**, no `User` or `Resident` exists yet. Staff/admin review pending applications on the **Registrations** page, optionally assigning a room, and:
  - **Approve** → creates the `Resident` profile *and* the linked `User` login in one action, using the password the applicant originally chose.
  - **Reject** → optional reason note; no account is ever created. The applicant gets a specific, friendly error if they try to log in with those credentials ("still pending" / "not approved: `<reason>`") — but only once the password is verified against the stored application hash, so this can't be used to probe arbitrary emails for their status.
  - A rejected applicant can submit a fresh application with the same email later.
- **Self-service profile** (`/profile` or `/r/profile`): every role can edit their own name/email and change their password. Changing password revokes every other refresh token (forces re-login on other devices) as a safety measure.

### 4.2 Resident presence & profiles

- `Resident` model: name, contact info, room assignment, Home/Away `status`, move-in/move-out dates, security deposit tracking (amount, paid, returned + dates), notes, `assigned_av_bayit_id` (which host family they're paired with), active/inactive flag.
- **Presence tracker** (`/presence`): rooms grouped and ordered by floor + display position — not alphabetically by resident — so it visually matches the building layout. Staff can toggle any resident's status inline.
- **Resident self-service**: a resident can view (`GET /residents/me`) and toggle (`PATCH /residents/me/status`) only their own record.
- **Activity log** (`ResidentActivityLog`): append-only audit trail — every status change, profile edit, deactivation, and self-registration approval is logged automatically by the service layer, with who did it and when.
- **Rooms** (`/rooms`): floor, room number, display order, capacity. Drives the presence tracker layout.

### 4.3 Food inventory

- `InventoryItem`: name, category (perishable / non-perishable / cleaning supplies / paper goods / other), location (Floor 1/2/3 kitchen, basement), quantity, unit, low-stock threshold, expiration date.
- **Every quantity change is logged** (`InventoryTransaction`) — stock levels are reconstructable/auditable, not just a mutable counter. Adjustments that would push quantity negative are rejected (422) before any write happens.
- **Low-stock view** (`/inventory/low-stock`): items at or below their threshold, surfaced on the admin Dashboard.
- Background job (`check_low_stock`, hourly cron in the ARQ worker) scans and logs low-stock alerts — currently logs only; wiring to real notifications (email/SMS/Slack) is a documented next step.

### 4.4 Maintenance & cleaning requests

- `DamageReport` model (name kept for migration continuity — covers **both** damage reports and cleaning requests via a `category` field, since they share the same lifecycle): title, description, category, status, optional room/resident link, assigned staff member, photo URLs, resolution notes.
- **Status pipeline**: `New → Acknowledged → In Progress → Closed`, with only valid forward transitions allowed (enforced server-side; e.g. New → Closed directly is rejected). Every transition is recorded in `DamageReportStatusHistory` with who changed it, when, and an optional note.
- **Photo upload**: residents/staff can attach photos to a report (validated content-type, size-capped, stored under `UPLOAD_DIR` — mount a persistent volume in production or uploads are lost on redeploy).
- **Resident scoping**: residents can only see/act on their own reports (auto-scoped server-side — a resident's `resident_id` is forced onto any report they create, regardless of what they submit); staff/admin see the building-wide list, filterable by status/category/room.

### 4.5 Meal coordination

Two related but distinct concepts:

- **`MealHostingRecord`** — the after-the-fact historical log ("who hosted whom, when") used for reporting. Any authenticated user can log one; summarized via `/meals/summary` (meals/guests hosted per family).
- **`MealInvitation`** — the forward-looking RSVP workflow. An Av/Eim Bayit family (or staff) invites a specific resident to a meal; the resident sees it in their portal and **accepts or declines**. Av/Eim Bayit accounts can only invite residents *assigned to them* (`?assigned_to_me=true` filter on the roster).

### 4.6 Announcements

- `Announcement`: title, body, category (general / Tefillah times / emergency), pinned flag, optional expiry, optional audience targeting.
- **Audience rules**: `audience_av_bayit_id = null` means visible to everyone; set means visible only to residents assigned to that Av/Eim Bayit family. Staff/admin can post to any audience (including emergency/global); Av/Eim Bayit accounts can only post to their own assigned group; residents cannot post at all. A resident's feed shows general announcements plus anything targeted at their specific host family.

### 4.7 Admin dashboard

- Live snapshot (`/dashboard`): Home/Total occupancy count, low-stock item count, open maintenance ticket count, total resident count — each tile links through to the relevant management page.

### 4.8 Mobile PWA

- Installable ("Add to Home Screen" on iOS/Android), offline-capable app shell via a generated service worker (`vite-plugin-pwa`). API responses are explicitly **never** cached offline-first (`NetworkOnly` for `/api/*`) — this is live operational data, not content that should go stale.
- **Role-based bottom navigation** (`components/BottomNav.tsx`): fixed tab bar shown only below the `sm` breakpoint (real mobile viewports); the existing top nav takes over on wider screens. Tab items differ per role (admin/staff/av_bayit each get a different curated set; residents get their own separate 3-tab bar under `/r/*`).
- Residents get an entirely separate, simplified layout (`ResidentLayout.tsx`) rather than a cut-down version of the staff shell.

---

## 5. Domain model reference

| Model | Purpose |
|---|---|
| `User` | Login credential: email, hashed password, role, `resident_id` (nullable) |
| `RefreshToken` | Hashed refresh tokens, rotation chain (`replaced_by_id`), revocation flag |
| `ResidentRegistrationRequest` | Pending/approved/rejected self-registration applications |
| `Resident` | Profile data: contact info, room, status, deposit tracking, `assigned_av_bayit_id` |
| `ResidentActivityLog` | Append-only audit trail per resident |
| `Room` | Floor, room number, display order, capacity |
| `InventoryItem` / `InventoryTransaction` | Stock levels + full change history |
| `DamageReport` / `DamageReportStatusHistory` | Maintenance & cleaning tickets + status audit trail |
| `MealHostingRecord` | Historical "who was hosted when" log |
| `MealInvitation` | Forward-looking RSVP (pending/accepted/declined) |
| `Announcement` | House announcements, optionally audience-scoped |

**Two intentional circular foreign keys** exist (`User.resident_id` ↔ `Resident.assigned_av_bayit_id`) — both reference the other's table. One side (`User.resident_id`) is declared with `use_alter=True` so SQLAlchemy can create/drop the schema without a dependency-cycle error. See the "Known gotchas" section of `DEPLOYMENT.md` if you touch either of these fields.

---

## 6. API surface

All routes are under `/api/v1`. Grouped by router file (`backend/app/api/routes/`):

| Router | Key endpoints |
|---|---|
| `auth.py` | `POST /login`, `POST /refresh`, `POST /logout`, `GET/PATCH /me`, `POST /me/change-password`, `POST /register` (admin-only) |
| `registration.py` | `POST /registration/apply` (public), `GET /registration/requests`, `POST /registration/requests/{id}/approve\|reject` |
| `residents.py` | `GET /residents/presence`, CRUD on `/residents`, `GET/PATCH /residents/me*` (self-service) |
| `rooms.py` | CRUD on `/rooms` |
| `inventory.py` | CRUD on `/inventory`, `POST /inventory/{id}/adjust`, `GET /inventory/low-stock` |
| `maintenance.py` | CRUD on `/maintenance/reports`, `PATCH .../status`, `POST .../photos` |
| `meals.py` | CRUD on `/meals` (+ `/summary`), `/meals/invitations*` |
| `announcements.py` | CRUD on `/announcements` |
| `testing.py` | `POST /testing/reset` — **only mounted when `ENVIRONMENT=test`**, drops and reseeds all tables for E2E isolation |

List endpoints share a common `offset`/`limit` pagination dependency (`api/pagination.py`, capped at 500/page).

`/health` (liveness, no DB touch) and `/health/ready` (checks Postgres + Redis) are outside the `/api/v1` prefix.

---

## 7. Database migrations

```
0001_initial_schema.py      users, refresh_tokens, rooms, residents (+activity log),
                             inventory_items (+transactions), damage_reports (+history),
                             meal_hosting_records
0002_resident_portal.py     adds the `resident` role, User<->Resident links, announcements,
                             meal_invitations, damage_reports.category
0003_registration_requests  resident_registration_requests table
```

Run `alembic revision --autogenerate -m "..."` from `backend/`, then `alembic upgrade head`. In production this runs as a Railway `preDeployCommand` — **not** chained into the app's own start command (that was a real bug: it raced the health check and hung on cold start; see `DEPLOYMENT.md`).

---

## 8. Background jobs (ARQ worker)

`backend/app/worker.py`, deployed as its own Railway service (`worker`) sharing the same Redis instance as the API:

- `check_low_stock` — hourly cron, scans inventory for items at/below threshold
- `send_meal_reminder` — daily cron (15:00 UTC), nudges on unlogged hosting for the day

Both currently just log; wiring to a real notification channel (email/SMS/push) is a deliberate next step, not yet built.

---

## 9. Testing

- **Backend**: 34 pytest tests across 9 files (in-memory SQLite), covering auth rotation/reuse-detection, the rollback-on-exception contract itself (`test_db_rollback.py`), resident RBAC boundaries, inventory negative-stock rejection, maintenance status-transition rules, and the full registration approve/reject flow.
- **E2E**: Playwright across desktop Chrome, iPhone 13, and Pixel 5 — login/role-routing (a resident account can never reach a staff route, even via direct URL), the presence board, resident status toggle, and Av/Eim Bayit meal invitations. Uses `/testing/reset` for isolated, repeatable runs.
- **CI** (`.github/workflows/ci.yml`): backend lint + pytest, a dedicated job running the real Alembic migrations against a live Postgres container (catches Postgres-only issues SQLite can't), and frontend lint + typecheck + build.

---

## 10. Known limitations (deliberate, not oversights)

- No real push notifications yet — background job alerts are logged, not delivered.
- No full poll/voting feature for group communication — shipped as simpler audience-targeted announcements instead.
- Older admin CRUD pages (Residents, Inventory, Maintenance, Rooms) still use plain `fetch`/`useState`; newer pages use TanStack Query. Full migration is a reasonable follow-up, not done.
- Damage-report photo uploads validate the client-supplied `Content-Type` header (not tamper-proof) — acceptable for an internal tool; would need byte-sniffing (e.g. `python-magic`) if ever exposed more broadly.
- Access tokens aren't individually revocable (standard for short-lived JWTs) — only refresh tokens are revoked on logout/password-change, so a stolen access token remains valid until its 15-minute expiry.
