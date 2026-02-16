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
- Don’t memorize code; keep templates.
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
  - length 3–32
  - letters/numbers/dot/underscore only
  - no spaces
  - cannot start/end with `.` or `_`
  - no consecutive/mixed separators
  - not only numbers
- Email is normalized (trim + lowercase) and length-checked.
- Password rules enforced:
  - 8–64 chars, no spaces
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
  - No “works on my machine” issues.
  - Easy to deploy the same image to production.
  - Spin up API + DB + Redis together with one command.
- **Key concepts**:
  - **Image** = blueprint; **Container** = running instance.
  - **Dockerfile** = recipe to build the image.
  - **docker-compose.yml** = run multiple containers as one app.
- **Steps we followed (this project)**:
  1) Install Docker Desktop and ensure it’s running.
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
