# Ethara Seat Allocation & Project Mapping System

A full-stack app for managing seat allocation and project mapping for ~5,000 employees.
Built with **FastAPI + SQLAlchemy + SQLite** on the backend and **React + Vite + Tailwind v4**
on the frontend, per the assessment brief.

```
ethara-seat-system/
├── backend/          FastAPI app, models, seed script
├── frontend/          React (Vite) app
├── AI_PROMPTS.md       Required AI-usage documentation (Section 9 of the brief)
└── README.md           This file
```

## Features

- **Employee management** — create/list/update/deactivate, with department, role, project, and status
- **Project mapping** — 11 seeded projects, one active project per employee
- **Seat allocation** — floor/zone/bay/seat model with available/occupied/reserved/maintenance
  status, duplicate-allocation prevention, and proximity-based auto-suggestion for new joiners
  (same project team → same floor → any available seat)
- **New joiner flow** — create an employee and auto-allocate their seat in one action
- **Search & filter** — by name, employee ID, email, project, floor, zone, seat status
- **Dashboard** — total employees/seats, occupied/available/reserved counts, project-wise and
  floor-wise utilization, pending-allocation count
- **Authentication & roles** — JWT login with three roles: **Admin** and **HR** have full
  read/write access (create/update employees, allocate/release seats); **Employee** accounts are
  read-only for other people's data (search, dashboard, AI assistant, own record) and can't reach
  the New Joiner flow or release someone else's seat. The login screen surfaces Admin and Employee
  as one-click demo accounts (the `hr` account still works — it's just not shown as a shortcut,
  since Admin and HR have identical permissions in this app), includes a password visibility
  toggle and a "Forgot password?" note (this is a demo app with no email infrastructure, so it
  explains that rather than faking a reset flow), and carries a subtle branded background
  watermark through to the rest of the app after signing in
- **Self-service seat booking ("My Seat")** — any logged-in user linked to an employee record
  (typically Employee-role accounts) can book an available seat for themselves or release the one
  they're in, from a dedicated page or via the AI assistant ("book me a seat", "release my seat").
  The backend enforces this at the API level regardless of role: an Employee account can only ever
  allocate/release **their own** `employee_id` — attempting to target anyone else returns a 403,
  even if the request is crafted by hand outside the UI
- **AI assistant** (`POST /ai/query`) — rule-based natural language parser for the exact query
  types in the brief ("Where is employee Amit seated?", "Show all available seats on Floor 3",
  "How many seats are occupied for Project X", "Who is sitting near me"), with an optional
  Claude-powered intent-extraction layer that still resolves against the real database (see
  `backend/app/ai_assistant.py`)

## Sample data

`backend/seed.py` generates, exceeding every minimum in Section 6 of the brief:

| Requirement | Minimum | Seeded |
|---|---|---|
| Employees | 5,000 | 5,000 |
| Floors | 5 | 5 |
| Zones | 10 | 10 |
| Seats | 5,500 | 5,600 |
| Projects | 10 | 11 |
| Available seats | 500 | 600 |
| Reserved seats | 100 | 120 |
| Pending allocation | 50 | 150 |

`seed.py` also creates three demo login accounts:

| Role | Username | Password | Access |
|---|---|---|---|
| Admin | `admin` | `admin123` | Full read/write |
| HR | `hr` | `hr123` | Full read/write |
| Employee | `employee` | `employee123` | Read-only (linked to a real seated employee) |

## Running locally

### Backend

```bash
cd backend
python3 -m venv venv && source venv/bin/activate   # optional but recommended
pip install -r requirements.txt
python3 seed.py            # populates ethara_seats.db with sample data
uvicorn app.main:app --reload --port 8000
```

- API root: http://localhost:8000/
- Interactive API docs (Swagger UI): **http://localhost:8000/docs**
- Health check: http://localhost:8000/health

By default the backend uses SQLite (`ethara_seats.db`). To use PostgreSQL instead, set:

```bash
export DATABASE_URL="postgresql://user:password@host:5432/ethara"
```

No code changes are needed — `backend/app/database.py` reads `DATABASE_URL` from the environment.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

- App: http://localhost:5173/
- The Vite dev server proxies `/api/*` to `http://localhost:8000` (see `vite.config.js`). Set
  `VITE_API_PROXY_TARGET` to point the dev proxy elsewhere.

For a production build:

```bash
npm run build      # outputs to frontend/dist
npm run preview    # serve the production build locally
```

If you deploy the frontend separately from the backend (e.g. Vercel + Railway), replace the
dev-only `/api` proxy with an absolute backend URL in `frontend/src/api.js`
(`const BASE = import.meta.env.VITE_API_URL`) and set `VITE_API_URL` as a build-time env var on
the hosting platform.

## API overview

Full interactive documentation is auto-generated by FastAPI at `/docs` once the backend is
running. Endpoint summary:

| Area | Endpoints |
|---|---|
| Employees | `POST/GET /employees`, `GET/PUT/DELETE /employees/{id}` |
| Projects | `POST/GET /projects`, `GET /projects/{id}/employees` |
| Seats | `POST/GET /seats`, `GET /seats/available`, `POST /seats/allocate`, `POST /seats/release` |
| Dashboard | `GET /dashboard/summary`, `GET /dashboard/project-utilization`, `GET /dashboard/floor-utilization` |
| AI Assistant | `POST /ai/query` |

Example AI assistant call (all `/ai/query` requests need a bearer token — see `/auth/login`):

```bash
curl -X POST http://localhost:8000/ai/query \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"query": "Where is my seat?"}'
```

Self-service booking/release via natural language (resolves to the logged-in user's own
`employee_id` from the JWT — never from free text in the query):

```bash
curl -X POST http://localhost:8000/ai/query \
  -H "Authorization: Bearer <employee-token>" \
  -H "Content-Type: application/json" \
  -d '{"query": "I need to reserve a seat for myself"}'

curl -X POST http://localhost:8000/ai/query \
  -H "Authorization: Bearer <employee-token>" \
  -H "Content-Type: application/json" \
  -d '{"query": "Release my seat"}'
```

Admin/HR accounts can additionally book on someone else's behalf via `"book a seat for <Name>"` —
Employee accounts attempting the same phrasing get a polite refusal pointing them to "book me a
seat" instead.

## Core business rules (enforced in `backend/app/seat_logic.py`)

- One employee can have only one **active** seat allocation at a time.
- One seat can be allocated to only one active employee at a time.
- Releasing an allocation sets the seat back to `available` and the employee back to
  `pending_allocation`.
- Seats with status `reserved` or `maintenance` cannot be allocated until their status changes.
- New joiners are matched first to the floor/zone where most of their project teammates already
  sit; if that zone is full, the system falls back to the same floor, then any available seat.
- Duplicate employee emails and duplicate seat numbers (same floor + zone) are rejected with a
  400 response.
- **Self-service scope**: Employee-role accounts may call `POST /seats/allocate` and
  `POST /seats/release` for themselves only. The API resolves "who" from the JWT
  (`current_user.employee_id`), not from any employee_id the client sends — an Employee account
  passing someone else's `employee_id`, or a `seat_id` belonging to someone else's active
  allocation, gets a 403. Admin/HR accounts are unrestricted (see `backend/app/routers/seats.py`).

## Deployment

This assistant's build environment has no network access to hosting platforms, so it cannot spin
up a live URL directly — the steps below are what to run to deploy each half.

**Actual deployment used for this project**, and why: backend on **Railway**, database on
**Render's** managed Postgres (not Railway's own Postgres), frontend on **Netlify** (moved there
after Vercel intermittently failed to pick up a fresh production build — see `AI_PROMPTS.md`,
"Prompt 12," for the full investigation). All three platforms are on the assessment's approved
list (Section 4/11). The database ended up split from the backend's hosting platform because
Railway's Postgres, when accessed via its public TCP proxy from outside Railway's network (needed
for a one-time local seeding step), reliably hung partway through a bulk write — see
`AI_PROMPTS.md` ("Prompt 11 — Deployment & Debugging") for that investigation. Render's external
Postgres URL doesn't have this issue, so the database moved there; the backend still runs on
Railway and connects to Render's database over its public URL.

### Backend (Railway)

1. Push the `backend/` folder to a GitHub repo (with the repo's root containing both `backend/`
   and `frontend/`, and Railway's **Root Directory** setting for this service set to `backend`).
2. Create a new Railway service, connect the repo.
3. In **Settings → Build**, set the Build Command: `pip install -r requirements.txt`
4. In **Settings → Deploy**, set the Start Command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
5. In **Variables**, set:
   - `DATABASE_URL` — a Postgres connection string (see "Database" below)
   - `JWT_SECRET_KEY` — any long random string (signs login tokens; don't leave this unset)
6. In **Settings → Networking → Public Networking**, click **Generate Domain** — this is your
   **live backend URL**.
7. Seed the database once (see "Seeding" below).

### Database (Render Postgres)

1. On Render, **New +** → **PostgreSQL**, free tier, any region.
2. Once created, copy the **External Database URL** — this is what both your own laptop (for
   seeding) and your Railway-hosted backend (for normal operation) will use, since they're on
   different platforms/networks and only the external URL is reachable from outside Render.
3. Set this as `DATABASE_URL` on the Railway backend service (Step 5 above).

### Seeding

From your own machine, with the backend's Python virtual environment active:
```powershell
cd backend
$env:DATABASE_URL="<paste the Render External Database URL>"
python seed.py
```
This runs once against the live database and populates it with the full sample dataset (Section 6
minimums) plus the three demo login accounts. `seed.py` uses chunked bulk inserts with progress
output specifically so this is safe to run against a remote database — see `AI_PROMPTS.md` for why
that mattered here.

### Frontend (Netlify)

1. Push the `frontend/` folder (same repo).
2. New site on Netlify, import the repo.
3. **Base directory**: `frontend`
4. **Build command**: `npm run build`
5. **Publish directory**: `dist` (relative to Base directory above — Netlify will show/resolve
   this as `frontend/dist`; do **not** type `frontend/dist` yourself here, or it resolves to a
   nonexistent `frontend/frontend/dist`).
6. Leave **Package directory** and **Functions directory** empty.
7. Environment variable: `VITE_API_URL` = your Railway backend URL from above (no trailing slash).
8. Deploy — the resulting `*.netlify.app` URL is your **live frontend URL**.

If you'd rather use Vercel: the same settings apply (Root Directory `frontend`, Build Command
`npm run build`, Output Directory `dist`, same `VITE_API_URL` variable) — this project deployed
cleanly on Vercel too once its environment variable and build-cache state were sorted out; Netlify
was chosen here mainly to get an independent, freshly-configured environment while debugging (see
`AI_PROMPTS.md`, Prompt 12), not because of any inherent Vercel limitation.

**Important — every environment variable added *after* a platform's first build requires a
genuinely fresh rebuild to take effect**, since Vite bakes `import.meta.env.*` values in at build
time, not runtime. The most reliable way to force one is an empty commit:
```powershell
git commit --allow-empty -m "Trigger fresh build"
git push
```
Relying on a platform's "Redeploy" button on an old build is not equivalent — it can serve a
cached build that predates the variable.

### CORS

`backend/app/main.py` currently allows all origins (`allow_origins=["*"]`) for ease of local
development and demoing. Before sharing a real deployment, narrow this to your deployed frontend's
exact Netlify (or Vercel) origin.

### A gotcha worth knowing if you touch API calls

Every network request the frontend makes should go through the shared `request()` helper in
`frontend/src/api.js` (which reads `VITE_API_URL`), **not** a standalone `fetch()` call written
directly in a page or context file. `frontend/src/auth.jsx`'s login function briefly bypassed this
with a hardcoded `/api/auth/login` path, which worked fine in local dev (where `/api` is proxied)
but silently 404'd once deployed — every other page worked correctly the whole time, only login
was affected, which made it a genuinely confusing bug to track down. See `AI_PROMPTS.md`, Prompt
12, for the full story if you want the cautionary tale.

## Submission checklist mapping

| Required by brief | Where to find it |
|---|---|
| GitHub repository | push this folder |
| Live deployment link | follow "Deployment" above |
| README.md | this file |
| AI_PROMPTS.md | `AI_PROMPTS.md` in the project root |
| Database schema | `backend/app/models.py`, or run `sqlite3 ethara_seats.db .schema` |
| Sample seed data | `backend/seed.py` (run it to populate) |
| Screenshots | take these from your own running instance |
| API documentation | auto-generated Swagger UI at `/docs` on the running backend |
| Debugging notes | see "Prompt 6 — Debugging" in `AI_PROMPTS.md` |
| Deployment notes | see "Deployment" section above |
