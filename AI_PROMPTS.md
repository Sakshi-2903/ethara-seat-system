# AI_PROMPTS.md

## AI Tool Used

**Claude (Anthropic)** — used inside Claude's own chat/agentic coding environment, which can read
the assessment brief, write files directly, run shell commands, install dependencies, start the
backend server, and run `curl` requests against it to verify behavior before handing code over.
Because of that, this project was built through iterative *instructions and verification steps*
rather than copy-pasted prompt/response pairs into a separate chat window — the log below
reconstructs the equivalent prompts for each stage, plus what was actually generated, checked, and
fixed at each step.

---

## Prompt 1 — Planning / Architecture

**Prompt used:**
> "Read the attached assessment doc. Build a full-stack seat allocation and project mapping system
> for ~5,000 employees at Ethara: employee management, project mapping, seat allocation with
> proximity-based suggestion, new joiner onboarding, search/filter, a dashboard, and a natural
> language AI assistant. Use FastAPI + SQLAlchemy + SQLite for the backend and React + Vite +
> Tailwind for the frontend. Follow the required API endpoints and database model from the doc
> exactly. Seed data must meet the minimums in Section 6."

**What AI generated correctly:** A clean layered structure — `models.py` / `schemas.py` /
`seat_logic.py` / `routers/*` — that maps directly onto the doc's Section 7 schema and Section 5
endpoint list, plus a route/page split on the frontend (Dashboard, Directory, Seats, New Joiner,
Assistant) that matches Section 3's feature list.

**What AI generated incorrectly / had to be adjusted:** Nothing structural — the main corrections
happened later, during backend startup (see Prompt 6 below).

**How verified:** Compared the planned file list and endpoint list line-by-line against Sections 5
and 7 of the assessment doc before writing any code.

---

## Prompt 2 — Database Design

**Prompt used:**
> "Create SQLAlchemy models for employees, projects, seats, and seat_allocations exactly matching
> the fields in Section 7 of the doc. Add the constraints implied by Section 8's business rules:
> unique employee email, unique seat number per floor+zone, and status enums for employment,
> seat, project, and allocation state."

**What AI generated correctly:** All four tables with the exact field names from the doc, a
`UniqueConstraint` on `(floor, zone, seat_number)`, a unique index on `Employee.email`, and enum
columns (`EmploymentStatus`, `SeatStatus`, `ProjectStatus`, `AllocationStatus`) instead of free-text
status strings, which makes invalid statuses impossible at the ORM layer.

**What AI generated incorrectly:** Nothing wrong outright, but the first pass didn't index
`Seat.status` or `Employee.status`, which would slow down the dashboard's status-count queries at
5,000+ rows. Added `index=True` to those columns manually.

**How verified:** Ran `Base.metadata.create_all()` against a throwaway SQLite file and inspected
the resulting schema with `sqlite3 .schema` to confirm constraints landed as expected.

---

## Prompt 3 — Backend APIs

**Prompt used:**
> "Implement the REST endpoints from Section 5 as FastAPI routers: employees (CRUD), projects
> (create/list/employees-by-project), seats (create/list/available/allocate/release), and
> dashboard (summary/project-utilization/floor-utilization). Use Pydantic schemas for
> request/response validation and raise 400/404 with clear messages on business-rule violations."

**What AI generated correctly:** All endpoints from the doc's Section 5 table, with pagination
(`limit`/`offset`) and filtering (`search`, `project_id`, `status`, `department`, `floor`, `zone`)
added beyond the minimum spec because Section 3.5 requires search/filter by those exact fields.

**What AI generated incorrectly:** The first version of `POST /employees` didn't check for a
duplicate email before insert, relying only on the DB's unique constraint — which would surface as
an ugly 500 IntegrityError instead of a clean 400. Added an explicit pre-check with a friendly
error message ("Duplicate employee email is not allowed") to match Section 8's business rules.

**How verified:** Started the server with `uvicorn` and hit every endpoint with `curl`, including
deliberately re-submitting a duplicate email and a duplicate seat number to confirm the 400
responses fire instead of crashing.

---

## Prompt 4 — Seat Allocation Logic

**Prompt used:**
> "Implement the seat allocation algorithm in Section 3.4 and the rules in Section 8: one active
> seat per employee, one active employee per seat, released seats become available again, reserved
> seats can't be allocated directly, and new joiners should be prioritized for seats near their
> project team, falling back to alternate zones/floors if none are free nearby."

**What AI generated correctly:** A `find_best_seat_for_employee` function that first looks for the
floor+zone where the most teammates on the same active project already sit, then falls back to
same-floor/any-zone, then any available seat anywhere — which satisfies "if no seats are available
in the preferred zone, system should suggest alternate zones" from Section 3.4.

**What AI generated incorrectly:** The first draft allowed allocating directly onto a `reserved`
seat if `seat_id` was passed explicitly, which violates the rule "reserved seats cannot be
allocated unless status is changed." Added a status check that raises a `SeatAllocationError` for
any seat not currently `available`, regardless of whether the seat was auto-suggested or explicitly
requested.

**How verified:** Ran a live sequence of `curl` calls: allocate a seat to a pending employee →
confirm dashboard counts shift (`available_seats` -1, `occupied_seats` +1) → attempt a second
allocation for the same employee and confirm it's rejected → release the seat → confirm the
dashboard counts revert exactly to baseline.

---

## Prompt 5 — AI Assistant

**Prompt used:**
> "Build the /ai/query endpoint from Section 5. Default to a rule-based keyword/intent parser (no
> external API key required) that can answer: where an employee is seated, their project, available
> seats by floor/zone, who is seated near them, and project seat utilization — matching the example
> in Section 3.7 exactly. Also add an optional path that uses the Claude API to extract intent from
> free text, but have it resolve against the same underlying database functions so it can't
> hallucinate a seat number, and fall back to the rule-based parser if no API key is set or the
> call fails."

**What AI generated correctly:** A keyword/regex-based intent classifier (floor number, zone
letter, email, and name extraction) wired to five deterministic answer functions, plus an optional
`answer_query_with_llm` wrapper that only uses the LLM to *classify intent and extract entities* —
it still calls the same database-backed functions to produce the actual answer, so numbers in the
response are always real, not generated text.

**What AI generated incorrectly:** The first version of the "who is near me" intent matched too
eagerly on any query containing the word "near," which collided with an unrelated hypothetical
query about "the nearest available seat." Tightened the trigger phrases to `"near me"`, `"sitting
near"`, and `"who is near"` specifically.

**How verified:** Sent all five example queries from Section 3.7 and Section 5 through
`POST /ai/query` via `curl` and manually checked each answer against the underlying employee/seat
records in SQLite.

---

## Prompt 6 — Debugging

**Prompt used:** (not a single prompt — this was iterative, driven by actually running the app)

**What went wrong and was fixed during live testing:**
1. `uvicorn` failed on startup with `ModuleNotFoundError: No module named 'email_validator'` because
   Pydantic's `EmailStr` needs it as a separate package. Fixed by adding `email-validator` to
   `requirements.txt` and installing it.
2. Background server processes didn't persist across separate shell invocations in the sandboxed
   dev environment, causing several `curl: (7) Failed to connect` failures. Fixed by starting the
   server and running the verification `curl` calls in the *same* shell session (and later with
   `setsid ... < /dev/null &` for a fully detached process).

**How verified:** Once fixed, re-ran the full `curl` verification sequence from Prompt 4 end to end
with no errors, then re-ran the seed script to reset the database to a clean baseline before
final packaging.

---

## Prompt 7 — Frontend

**Prompt used:**
> "Build the React frontend with Vite and Tailwind v4. Pages: Dashboard (summary stats,
> floor-occupancy bars, project utilization table), Directory (debounced employee search +
> detail panel), Seat Map (filter by floor/zone/status + release action), New Joiner (create
> employee, then auto-allocate a seat), and Ask Ethara (chat UI for the /ai/query endpoint).
> Design it as a distinctive internal workplace tool, not a generic dashboard template — dark
> sidebar, signage-style accent color, monospace seat codes."

**What AI generated correctly:** All five pages wired to the `api.js` client, a shared `StatCard`
component, and a design direction (ink/paper palette, amber "signal" accent evoking office
wayfinding signage, monospace seat-code badges) intentionally chosen to avoid the generic
cream-and-terracotta or all-black-with-neon-accent look AI tools default to.

**What AI generated incorrectly:** The initial Tailwind setup targeted Tailwind v3's config file
approach; the environment installed Tailwind v4, which uses the `@tailwindcss/vite` plugin and
`@theme` CSS tokens instead of `tailwind.config.js`. Rewrote `vite.config.js` and `index.css`
around the v4 approach.

**How verified:** Ran `npm run build` to confirm a clean production build, then ran `npm run dev`
alongside the live backend and used `curl` through the Vite dev-server proxy (`/api/...`) to
confirm the frontend's exact fetch paths resolve to real backend data.

---

## Prompt 8 — Deployment

**Prompt used:**
> "Prepare this for deployment on Railway/Render (backend) and Vercel/Netlify (frontend): env-var
> driven DATABASE_URL, CORS enabled for the frontend origin, a production build step for the
> frontend, and a README with exact deploy steps for both."

**What AI generated correctly:** `database.py` already reads `DATABASE_URL` from the environment
with a SQLite fallback, so pointing it at a managed Postgres instance on Railway/Render is a
one-line env var change with no code change. CORS is wide-open (`allow_origins=["*"]`) for the
assessment; the README notes narrowing this to the deployed frontend origin for anything beyond a
demo.

**What candidate (human) still needs to do:** This assistant's environment has no network access to
Railway, Render, Vercel, or Netlify, so it cannot create accounts, push to a live deployment
platform, or generate real hosted URLs. The README includes the exact CLI/dashboard steps to
deploy both halves.

---

## Prompt 9 — Access Control / Authentication (added post-review)

**Prompt used:**
> "The dashboard/API currently has zero access control — anyone can allocate, release, create, or
> delete seats and employees. Add a full login screen with Admin/HR vs Employee roles. Admin and HR
> should keep full read-write access; Employee accounts should be read-only (search, dashboard, AI
> assistant, and their own record) and should not see or be able to reach the New Joiner flow or
> the seat release action."

**What AI generated correctly:**
- A `users` table (`username`, bcrypt `password_hash`, `role` enum, optional linked `employee_id`)
  and a `POST /auth/login` endpoint issuing a JWT (8-hour expiry) via `PyJWT`.
- A `get_current_user` FastAPI dependency (validates the bearer token) and two stricter
  dependencies built on top of it: `require_write_access` (admin/hr only) and `require_admin`.
- Every write endpoint (`POST/PUT/DELETE /employees`, `POST /projects`, `POST /seats`,
  `POST /seats/allocate`, `POST /seats/release`) now requires `require_write_access`; every read
  endpoint (`GET` routes, dashboard, `/ai/query`) requires `get_current_user` (any logged-in role).
- `seed.py` now creates three demo accounts (`admin/admin123`, `hr/hr123`, `employee/employee123`),
  with the employee account linked to a real seated employee record so "Where is my seat?" has a
  meaningful answer for that demo login.
- Frontend: an `AuthProvider` (`src/auth.jsx`) storing the JWT + role in `localStorage`, a `Login`
  page with clickable demo-account buttons, `api.js` attaching the bearer token to every request
  and force-logging-out on a 401, and `App.jsx` gating the whole app behind login, hiding the "New
  Joiner" nav item and route for employee accounts, and hiding the "Release seat" button on the
  Seat Map for read-only users.

**What AI generated incorrectly / had to be corrected:**
- The first pass on the frontend `App.jsx` edit (done live, interactively, while the human was also
  hand-editing the same file to add the company logo) produced a merge conflict: the human's manual
  edit left orphaned JSX (a leftover `E` text node and an extra closing `</div>`) because the logo
  `<img>` was pasted in without removing the full old badge block. This wasn't an AI-authored bug —
  it was a human/AI edit collision — but it's noted here because it broke the build and had to be
  diagned and replaced with a clean, complete file rather than another partial edit.
- The initial write-protection pass forgot the mobile header's logo `<img>` (only the desktop
  sidebar got it), caught on review and added to match.

**How verified:**
- Backend: ran the server locally and hit it with `curl` end to end — confirmed an unauthenticated
  request to `/dashboard/summary` returns `401`, a valid `employee` login can read the dashboard but
  gets `403 "Only Admin or HR accounts can perform this action."` when attempting
  `POST /seats/allocate`, and a valid `admin` login can allocate and release a seat successfully. Also
  confirmed a wrong password returns `401`.
- Frontend: ran `npm run build` after the change to confirm the production bundle compiles with no
  errors before handing the file back.

---

## Prompt 10 — Employee Self-Service (Book / Release Own Seat)

**Prompt used:**
> "Employees should be able to book and un-reserve a seat for themselves, not just view read-only
> data. If someone asks the AI assistant 'I need to reserve a seat for myself,' it should actually
> do it. Add this and update the docs."

**What AI generated correctly:**
- Relaxed `POST /seats/allocate` and `POST /seats/release` from admin/hr-only to
  **role-and-ownership-based**: Admin/HR remain unrestricted; Employee-role accounts may act only
  on their own `employee_id`, resolved from the JWT (`current_user.employee_id`), not from any
  value the client sends. If an Employee account's request targets a different `employee_id`, or a
  `seat_id` whose active allocation belongs to someone else, the API returns `403` before touching
  the database.
- `SeatAllocateRequest.employee_id` and `SeatReleaseRequest.employee_id`/`seat_id` were already
  optional in the schema, so an Employee account can simply POST `{}` to book or release their own
  seat without needing to know their own `employee_id` client-side — the backend fills it in.
- AI assistant: added a dedicated, deterministic write-intent layer (`try_handle_write_intent` in
  `ai_assistant.py`) that pattern-matches booking/release phrasing ("book me a seat", "reserve a
  seat for myself", "release my seat", "give up my seat", etc.) **before** any read-intent or LLM
  classification runs, and resolves "who" strictly from `current_user` (the authenticated JWT) —
  never from free text in the query. This means a state-changing action can never depend on an LLM
  correctly interpreting intent, and one employee can never trick the assistant into booking or
  releasing a seat on someone else's behalf by phrasing a request cleverly.
- Admin/HR accounts get an additional phrase pattern — "book a seat for `<Name>`" — that resolves
  to a named employee; Employee accounts hitting the same phrasing get a clear, polite refusal
  message redirecting them to "book me a seat" instead of a bare 403.
- Frontend: a new **My Seat** page (`src/pages/MySeat.jsx`), visible to any logged-in user, showing
  either their current seat with a "Release my seat" button, or — if unseated — a small form to
  book one with optional floor/zone preference (left blank, it defers to the same proximity-based
  auto-suggestion logic used for new joiners).

**What AI generated incorrectly / had to be corrected:**
- While this feature was being added, a stray edit elsewhere in `App.jsx` (from an earlier,
  unrelated manual change) had deleted the body of the `PeopleIcon` function and left `BookmarkIcon`
  (used by the new "My Seat" nav item) referenced but never defined. This wasn't introduced by this
  change, but it wasn't caught until this change's build step failed with a syntax error citing an
  unclosed brace. Fixed by restoring `PeopleIcon`'s SVG body and adding the missing `BookmarkIcon`
  definition.

**How verified:**
- Backend, live via `curl`: an Employee login released their own seat with `{"employee_id": <self>}`
  and then re-booked with an empty `{}` body (auto-suggest); the same account was rejected with
  `403` when targeting another employee's `employee_id` for allocate, and rejected with `403` when
  targeting another employee's seat by `seat_id` for release.
- AI assistant, live via `curl`: "I want to release my seat" → released; "I need to reserve a seat
  for myself" → booked and reported the exact seat; "book a seat for Amit" as an Employee account →
  refused with the redirect message; the same phrasing as an Admin account → booked successfully
  for the named employee.
- Frontend: confirmed the exact request shapes the My Seat page sends (`POST /seats/release {}` and
  `POST /seats/allocate {}`) resolve correctly through the Vite dev proxy end-to-end, and re-ran
  `npm run build` after fixing the `App.jsx` syntax error to confirm a clean production build.

---

## Prompt 11 — Deployment & Debugging (Railway → Render migration)

**Prompt used:** (iterative — this was live troubleshooting during actual deployment, not a single
upfront prompt)
> "Deploy the backend to Railway and seed the live database" — followed by pasting real crash
> logs and terminal output as each issue surfaced, and asking for fixes.

This was the most involved debugging session of the project, so it's documented in full here
rather than summarized, since it directly maps to the brief's required "Debugging notes" and
"Deployment notes" (Section 12).

**Issue 1 — `railpack could not determine how to build the app`.**
Railway built from the repo root and saw both `backend/` and `frontend/` with no single
entrypoint. Cause: the service's **Root Directory** setting hadn't actually been saved. Fixed by
re-entering `backend` in Settings → Source → Root Directory and confirming it took effect via a
fresh deploy log that showed a proper Python build instead of the "could not determine" error.

**Issue 2 — `ModuleNotFoundError: No module named 'psycopg2'`.**
The backend runs on SQLite locally, so nothing had ever exercised the Postgres code path.
Production used `DATABASE_URL` pointing at a real Postgres instance, and SQLAlchemy's
`create_engine` only imports `psycopg2` at that point — it was never in `requirements.txt`. Fixed
by adding `psycopg2-binary>=2.9.9`. Verified by installing it locally and confirming `import
psycopg2` succeeds, then redeploying and confirming the crash trace no longer appeared in Railway's
logs.

**Issue 3 — seeding a remote database appeared to hang indefinitely.**
This took several rounds to fully diagnose:
- First cause found: `seed.py` called `db.refresh()` once per inserted row (5,600 seats + 5,000
  employees ≈ 10,600 individual round trips) to fetch back auto-generated IDs. Locally, against
  SQLite on disk, this is unnoticeable. Against a remote database, at any realistic network
  latency, that's easily 10+ minutes of pure round-trip time with zero visible progress — which
  is exactly what "stuck" looked like. Fixed by replacing every per-row `db.refresh()` with a
  single bulk `SELECT ... ORDER BY id` after each batch commit, relying on the fact that insertion
  order matches ascending id order on a fresh auto-increment table.
- This fix alone wasn't enough: seeding *still* hung, but now specifically between the seats step
  finishing and the employees step's first insert — i.e., on the very next query after a batch of
  work had just completed successfully. That specific pattern (fine, then silently dead on the
  *next* call) is the signature of a connection that was quietly dropped by an intermediary (here,
  Railway's public TCP proxy) without the client being told — the socket just goes silent and the
  OS-level TCP timeout (which can be minutes on Windows) is what eventually would have surfaced an
  error, explaining why it looked like an indefinite hang rather than a clean failure.
- Rewrote the entire seeder to use **chunked bulk inserts** (`sqlalchemy.insert()` with batches of
  500 rows, `db.commit()` per batch, `print()` progress after each) instead of building 5,000+ ORM
  objects and inserting/refreshing them one at a time. This also makes it obvious in real time
  whether the process is alive.
- Also hardened `backend/app/database.py` for any non-SQLite `DATABASE_URL`: added
  `pool_pre_ping=True` (SQLAlchemy silently tests a connection before reusing it and transparently
  opens a fresh one if it's dead, instead of handing the caller a socket that will hang),
  `pool_recycle=280` (proactively retires connections before they're old enough to be at risk of a
  proxy timing them out from the other end), TCP `keepalives`, and a Postgres-side
  `statement_timeout=60000` so that if a query *does* somehow hang, it fails loudly after 60
  seconds with a real error instead of an unbounded wait.
- Despite all of the above, seeding through Railway's public Postgres proxy specifically continued
  to hang at the same point on a subsequent attempt. Root-caused as the proxy connection itself,
  not the application code — confirmed by testing the identical, already-fixed `seed.py` script
  against two different Postgres providers accessed from the same machine, same network: it hung
  again through Railway's proxy, but ran cleanly start-to-finish (a few seconds locally, under a
  minute over the network) against both Neon and Render's Postgres on the first attempt with no
  further code changes.

**Decision: moved the database off Railway's own Postgres, onto Render's, while keeping the
backend itself on Railway.** Both are on the assessment's approved platform list; nothing requires
the app-hosting platform and the database to be the same provider. This is documented explicitly
in the README's Deployment section rather than silently switched, since it's a real infrastructure
decision made for a concrete, reproduced reason — not an arbitrary preference.

**How verified:** the final `seed.py` was run start-to-finish against Render's Postgres from a
Windows machine over a real home internet connection (not the sandboxed dev environment this
project was originally built in), completing in well under a minute with full progress output and
the correct final summary counts (5,000 employees, 5,600 seats, 150 pending, matching every
Section 6 minimum). The Railway backend was then repointed at the same database via its
`DATABASE_URL` variable and its Swagger docs endpoint reconfirmed reachable after redeploy.

---

## Enhancements Beyond the Original Brief

The assessment brief (Sections 1–12) specifies the core system. Everything below was added on top
of that spec, at the candidate's request, and is called out separately here so it's clear what was
asked for vs. what was extended:

| Enhancement | Brief coverage |
|---|---|
| **JWT login with Admin / HR / Employee roles** | Not required — Section 12's checklist only lists "Sample login credentials **if** authentication is added" as optional |
| **Ownership-scoped self-service** (employees book/release their *own* seat) | Not mentioned — the brief's seat allocation flow (3.4) is written from an HR/Admin perspective only |
| **AI assistant can *act*, not just answer** ("book me a seat" / "release my seat") | Section 3.7 only asks the assistant to *answer* queries about seats/projects — performing the allocation itself is new |
| **Company logo / branded UI** | Not specified — the brief only asks for "simple responsive UI" (Section 4) |
| **Distinctive visual design system** (ink/paper/signage-amber palette, custom type pairing) | Not specified |

Everything else in this project — the data model, all required endpoints, the seed data minimums,
the read-only AI query types, and the dashboard — maps directly to a numbered section of the brief
and is documented against that section in Prompts 1–8 above.

## Summary: What AI Generated Correctly vs. Incorrectly (Overall)

**Correct on first pass:**
- Overall project structure and file layout
- Database schema matching Section 7 exactly
- All required REST endpoints from Section 5
- Rule-based AI assistant intent parsing for the five required query types
- Seed data generator hitting every Section 6 minimum
- JWT auth model (roles, dependencies, endpoint protection) and the login/role-gating UI
- Ownership-scoped self-service booking/release, and the AI assistant's deterministic write-intent
  layer that resolves identity from the JWT rather than free text

**Needed correction:**
- Missing `email-validator` dependency for Pydantic's `EmailStr` (backend startup crash)
- Reserved seats were allocatable via explicit `seat_id` before the status check was added
- Duplicate-email check relied on a raw DB constraint instead of a clean pre-check
- Tailwind v4 config approach vs. the v3 approach initially assumed
- Background process handling in the sandboxed dev shell (unrelated to app code, but cost debug time)
- A human/AI concurrent-edit collision on `App.jsx` while adding the company logo, which broke the
  JSX and required a full clean replacement rather than another partial patch
- The mobile header's logo image was missed on the first auth-gating pass
- A separate, unrelated `App.jsx` edit had silently deleted `PeopleIcon`'s function body and left
  `BookmarkIcon` undefined; only surfaced when the self-service feature's build step failed
- Missing `psycopg2-binary` for the Postgres path (only ever exercised in production, never
  locally against SQLite)
- Original seeder's per-row `db.refresh()` calls were invisible locally but made seeding a remote
  database prohibitively slow; needed a full rewrite to chunked bulk inserts
- Railway's public Postgres proxy reliably hung mid-seed for reasons outside the application code;
  resolved by moving the database to Render rather than continuing to chase a platform-specific
  networking issue

**How correctness was verified throughout:**
- Every endpoint was exercised with real `curl` requests against a running server, not just read
  for correctness
- Seed data counts were checked against every Section 6 minimum after generation
- The full allocate → duplicate-reject → release → dashboard-revert cycle was run live end-to-end
- The frontend was built (`npm run build`) and also run in dev mode against the live backend
  through the Vite proxy to confirm real data renders, not just that the code compiles
