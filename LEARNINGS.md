# Learning Notes (ExpenseTracker)

## Alembic (Migrations)
- **Mental model**: Models define schema. Alembic stores *versioned changes* (migrations). You apply migrations to sync DB.
- **Setup steps**
  1) Install Alembic.
  2) Initialize Alembic (creates `alembic/` + `alembic.ini`).
  3) In `alembic/env.py`: import models and set `target_metadata = models.Base.metadata`.
  4) Remove `Base.metadata.create_all()` from app startup.
  5) Generate initial migration: `alembic revision --autogenerate -m "initial"`.
  6) Apply migration: `alembic upgrade head`.
- **Future changes**: update models ? `alembic revision --autogenerate -m "..."` ? `alembic upgrade head`.

## .env + Config
- Keep secrets in `.env` and load them using a settings class (`config.py`).
- Use those settings in DB + auth modules instead of hard-coding values.
- Add `.env` to `.gitignore` so secrets are not committed.

## Testing (FastAPI + pytest + SQLite)
- **Why**: tests should not touch real data.
- **Approach**: use SQLite in-memory DB and override `get_db` dependency.
- **Template summary**:
  1) Create SQLite engine.
  2) Create `sessionmaker` for tests.
  3) Override `get_db` to use test session.
  4) Create tables (`Base.metadata.create_all`).
  5) Use `TestClient(app)`.

## Minimal pytest flow
1) Install pytest.
2) Create `tests/` folder.
3) Write a simple test.
4) Run `pytest`.

## Makefile Commands (Project DX)
- `make run` ? start API with reload.
- `make migrate` ? create migration (pass `m=message`).
- `make upgrade` ? apply migrations.
- `make test` ? run tests.

## Advice for Future
- Don�t memorize code; keep templates.
- Always understand the *goal* of each step, not every syntax detail.

## Auth Testing (Sign-up / Sign-in)
- `/users/sign-up` expects JSON; `/users/sign-in` expects **form data**.
- Tests should cover:
  - success case
  - duplicate email
  - duplicate username
  - invalid input (email format, missing fields)
  - password strength rules
- When checking saved passwords, assert against `hashed_password`, not `password`.

## Validation Lessons (Schemas)
- Username rules enforced in schema:
  - length 3�32
  - letters/numbers/dot/underscore only
  - no spaces
  - cannot start/end with `.` or `_`
  - no consecutive/mixed separators
  - not only numbers
- Email is normalized (trim + lowercase) and length-checked.
- Password rules enforced:
  - 8�64 chars, no spaces
  - must include lowercase, uppercase, number, special character

## Pytest Fixtures (conftest.py)
- Use fixtures for `client` and `session` instead of manual `get_client()`.
- Ensure models are imported before `Base.metadata.create_all()`.
- Use per-test DB setup to avoid data leaking between tests.

## CSV Export (Expenses)
- **Purpose**: allow users to download expenses as a CSV file for Excel/Sheets.
- **Endpoint**: `GET /expenses/export` with optional filters: `start_date`, `end_date`, `category`.
- **Core steps**:
  1) Query expenses for the current user (apply filters).
  2) Create a `StringIO` buffer to build CSV text in memory.
  3) Use `csv.writer` to write rows into that buffer.
  4) Write a header row: `date,title,amount,category,description`.
  5) Loop over expenses and write one CSV row per expense.
  6) Use `StreamingResponse` with `Content-Disposition` so the browser downloads a file.
- **Line-by-line meaning**:
  - `import csv` ? built-in CSV writer.
  - `from io import StringIO` ? in-memory text buffer.
  - `output = StringIO()` ? place to write CSV lines.
  - `writer = csv.writer(output)` ? helper that formats rows correctly.
  - `writer.writerow([...])` ? writes a row (header or data).
  - `exp.category.value if hasattr(...) else exp.category` ? handles enum vs string.
  - `output.seek(0)` ? rewind buffer so response starts from the top.
  - `StreamingResponse(output, media_type="text/csv")` ? send CSV file.
  - `Content-Disposition: attachment; filename=expenses.csv` ? prompts download.

## CSV Export Testing
- Use `csv.reader(StringIO(text))` to parse CSV responses in tests.
- `rows` is a list of rows, each row is a list of string columns.
- Validate:
  - status code is 200
  - `Content-Type` starts with `text/csv`
  - first row matches header
  - filtered export returns only expected rows

## Docker Compose (Local)
- `docker-compose up` starts all containers (API, DB, Redis).
- Check running containers: `docker-compose ps`.
- Run migrations inside the API container:
  - `docker-compose exec api python -m alembic upgrade head`
- Health check after start:
  - `http://localhost:9000/health`

## Docker (Purpose + Steps)
- **Purpose**: Package the app and all its dependencies so it runs the same everywhere (local, server, CI).
- **Why we use it**:
  - No �works on my machine� issues.
  - Easy to deploy the same image to production.
  - Spin up API + DB + Redis together with one command.
- **Key concepts**:
  - **Image** = blueprint; **Container** = running instance.
  - **Dockerfile** = recipe to build the image.
  - **docker-compose.yml** = run multiple containers as one app.
- **Steps we followed (this project)**:
  1) Install Docker Desktop and ensure it�s running.
  2) Build and start containers:
     - `docker-compose up --build`
  3) Check containers are running:
     - `docker-compose ps`
  4) Run DB migrations inside the API container:
     - `docker-compose exec api python -m alembic upgrade head`
  5) Verify API is up:
     - `http://localhost:9000/health`
  6) Stop containers when done:
     - `docker-compose down`

## Render Deployment (Success)
- App is live at Render URL and responds on `/health`.
- Use `/docs` to confirm Swagger UI is available.
- Common success check: `/health` returns `{status: online, database: connected}`.

## Docker Daily Workflow (Simple)
- Daily start: `docker-compose up -d`
- Check containers: `docker-compose ps`
- Rebuild only when image-related files change (Dockerfile, requirements, base image): `docker-compose up -d --build`
- Stop when done: `docker-compose down`
- Optional logs: `docker-compose logs -f api`

## URL Params Mental Model (Reusable)
- **Core idea**: URL query params are the single source of truth for page filters/sort/pagination, and both frontend + backend map to/from that contract.
- **Think in 5 layers**:
  1) UI state (inputs like search/category/page).
  2) URL state (`?search=...&page=...`) for shareable/bookmarkable screens.
  3) API client serialization (`URLSearchParams` / query builder).
  4) Backend endpoint params (typed query args).
  5) DB/query filters + validation.

- **Implementation recipe (any project)**:
  1) Define a small query contract: names, types, defaults (ex: `search`, `category`, `sort`, `page`, `limit`, `start_date`, `end_date`).
  2) On page load, read URL params into UI state.
  3) When UI changes, update URL params (omit empty/default values to keep URL clean).
  4) Build request query string from state using a serializer.
  5) Backend parses typed params and applies filters/sorting/pagination.
  6) Validate invalid combinations (ex: only one of `start_date/end_date`, negative page, huge date ranges).
  7) Keep defaults aligned frontend/backend.

- **Why this scales**:
  - Deep links work (`copy URL` = same screen state).
  - Browser back/forward works naturally.
  - Filters are testable as pure input/output.
  - Easy to add new params later without rewriting flows.

- **Design rules I should keep**:
  - Keep one canonical param name per concept (`start_date`, not mixed aliases).
  - URL should represent user-visible state only (not internal UI toggles).
  - Use safe defaults and bounds (`days <= 366`, `page >= 1`).
  - Frontend should prevent obvious invalid combos; backend must still enforce.
  - Prefer idempotent GET endpoints for filtered reads.

- **Quick add-a-new-param checklist** (example: `min_amount`):
  1) Add to page state + initialize from URL.
  2) Add to URL write-back effect.
  3) Add to API query builder.
  4) Add typed backend query arg.
  5) Apply DB filter + validation.
  6) Add/adjust tests for that param and combinations.

## Pinned: Future Feature Ideas (Roadmap)

### 1) Income + Salary Layer
- Monthly income
- Salary utilization
- Savings rate

### 2) Budget Intelligence
- Budget recommendations
- Income-based limits

### 3) Behavioral Insights
- Spending comparisons
- Category dominance
- Alerts

### 4) Burn Rate Forecast
- Safe daily spend
- Salary runway
- Projected balance

### 5) Recurring Expenses
- Subscription tracking
- Auto budgeting

### 6) User-Type Personalization
- Student / Employed / Business dashboards

### 7) Business Mode (Optional advanced tier)
- Profit tracking
- Business vs personal split
- Tax export

## Auth System (Production V1) - Pending Work
- **Refresh tokens**: Add refresh token flow for session continuity (short-lived access token + longer-lived refresh token).
- **Refresh token storage**: Store refresh token in **HttpOnly cookie** (not localStorage); use `Secure` and `SameSite` appropriately.
- **Refresh token rotation**: Rotate refresh token on every refresh request (one-time-use refresh tokens).
- **Revocation / session store**: Persist refresh tokens (or token family/session records) server-side so logout and compromise response can revoke them.
- **Logout invalidation**: Invalidate refresh token/session server-side on logout (not only delete frontend tokens).
- **Refresh endpoint**: Add `/auth/refresh` endpoint and frontend auto-refresh flow before/after access token expiry.
- **Session expiry UX**: Handle refresh failure gracefully (silent retry -> sign-in redirect + user message).
- **Multi-device sessions**: Decide policy (allow multiple sessions vs limit devices) and add session management UI later if needed.
- **Security hardening**: Audit CSRF implications for cookie-based refresh flow and add CSRF protection if required by final cookie strategy.
- **Monitoring/audit**: Log auth security events (login, logout, refresh, reset, verification, failures/rate limits) for observability.
- **Auth tests (production-level)**: Add tests for refresh success/failure, rotation, revoked tokens, logout invalidation, and expired token edge cases.

## Budget Page UI Polish Roadmap (Planned)
- **Card hierarchy**: Make category title stronger, month smaller/muted, and amount line more visually prominent.
- **Progress bar upgrade**: Increase thickness, roundness, add subtle glow, and animate fill on load; use status colors (`0-60%` green, `60-85%` yellow, `85%+` red).
- **Spacing density**: Increase card internal padding and grid gap for cleaner breathing space.
- **Destructive action tone**: Soften delete action (ghost/icon/overflow menu) so it doesn�t dominate the card.
- **Card separation**: Add subtle border + soft shadow for better depth on dark background.
- **Outcome framing**: Show remaining amount explicitly (ex: `remaining: X UZS`) alongside used/limit.
- **Hover micro-interactions**: Lift card on hover, increase shadow, and reveal/emphasize controls smoothly.
- **Controls for scanning**: Add budget sorting/filtering (by month/category/% used/remaining).
- **History clutter control**: Default to current month budgets, with explicit toggle to show historical budgets.
- **Category iconography**: Add category icons to improve scan speed.
- **Status badges**: Add badge states like `On Track`, `Close to Limit`, `Over Budget`.
- **Motion polish**: Add count-up and progress-fill animations for first render.

## Budget UI Implementation Order (Next Session)
1. Card hierarchy + spacing + subtle border/shadow.
2. Progress bar visual/status/animation upgrade.
3. Delete action redesign (non-dominant destructive UI).
4. Remaining amount line + status badge.
5. Hover interactions + motion polish.
6. Filters/sorting + history toggle.
7. Category icons and final consistency pass.

## Budgets: Historical Card Stats Gap (Not a Bug, Missing Endpoint)
- Current behavior: budget cards show `spent/remaining/status` only for the current month.
- Reason: frontend uses `/analytics/this-month-stats`, which intentionally filters to current year/month.
- Impact: historical cards (e.g., December 2025 Transport) show `0 used` even if expenses exist.
- Planned fix (later): add backend endpoint that returns per-budget stats for all budget months, then map in `Budgets.jsx` by `(category, budget_year, budget_month)`.
## Development Roadmap (Planned - March 2026)

### Step 0: CI/CD Hardening
- Add PostgreSQL service to CI pipeline
- Add Alembic migration check before tests
- Enable branch protection on main (require PR + passing checks)
- Add linting (ruff for Python, eslint for JS)
- Harden dependency audits (remove continue-on-error)

### Step 1: Frontend Refactor
- Refactor frontend pages into reusable components
- Reduce code duplication across pages
- Clean up spaghetti before building new features

### Step 2: Auth System Completion
- Implement refresh token flow (short-lived access + longer-lived refresh)
- Refresh token storage in HttpOnly cookie
- Refresh token rotation (one-time-use)
- Server-side revocation + session store
- Logout invalidation server-side
- /auth/refresh endpoint + frontend auto-refresh
- Comprehensive auth tests

### Step 3: Premium Users + Recurring Expenses
- Update DB models to include premium user flag (is_premium on User)
- Build recurring expenses feature (premium only)
  - Mark expenses as recurring (daily/weekly/monthly)
  - Auto-create expenses on schedule
  - Dashboard shows upcoming recurring charges
- Write tests, pass CI, merge

### Step 4: Budget Rollover (Premium)
- Add budget rollover toggle in Settings page
- Only premium users can enable the toggle
- Free users see the toggle locked with upgrade CTA
- Backend: carry unused budget to next month when enabled
- Write tests, pass CI, merge

### Step 5: Advanced Analytics (Premium)
- Add premium analytics charts to Analytics page
  - Month-over-month comparison
  - Category trend over time
  - Budget utilization report
  - Top expenses list
  - Spending velocity
- Free users see blurred/locked premium charts with upgrade CTA
- Premium users see full charts
- Write tests, pass CI, merge

### Step 6: Notification System (All Users)
- Toast notification system for all users (free + paid)
- Budget alerts (80% spent, over budget, etc.)
- Action confirmations
- Error feedback

### Step 7: Production Deployment
- Register sarflog.uz domain
- Set up Uzbek cloud server
- Configure Nginx + SSL
- Deploy via CI/CD pipeline
- Set up UptimeRobot monitoring
- Set up automated DB backups

### Decisions Made
- **Rate limiters stay as-is** (prevent abuse, not a premium gate)
- **No custom categories** (titles + descriptions cover this; categories stay as enums, may add more later)
- **No unlimited export tier** (rate limits are security, not monetization)
- **Income Layer + User-Type Personalization merged** into one future feature (students get allowance label, employed get salary label)
- **Budget rollover gated via Settings toggle**, not page-level
- **Advanced analytics gated at page level** (blurred charts, not Settings)
- **Each step: test -> CI -> merge to main before starting next step**
