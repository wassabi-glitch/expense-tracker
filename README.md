# Expense Tracker API

A FastAPI backend for tracking expenses, budgets, and analytics, with JWT auth, CSV export, and Alembic migrations.

## Features
- User sign-up / sign-in (JWT)
- Expense CRUD with filters (date range, category, search, sorting)
- Budget limits with threshold tracking (50/90/100%)
- Analytics (history + daily trend)
- CSV export of expenses
- Full test suite (pytest)

## Tech Stack
- FastAPI
- SQLAlchemy
- PostgreSQL
- Alembic
- Pydantic

## Project Structure
- `app/main.py` – FastAPI app + routers
- `app/models.py` – SQLAlchemy models
- `app/schemas.py` – Pydantic schemas + validation
- `app/routers/` – API endpoints
- `app/utils.py` – auth helpers + budget alerts
- `alembic/` – migrations
- `tests/` – pytest suite

## Setup (Local)

### 1) Create & activate venv
```bash
python -m venv venv
# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate
```

### 2) Install dependencies
```bash
pip install -r requirements.txt
```

### 3) Configure environment
Create a `.env` file in project root:
```
DATABASE_HOSTNAME=localhost
DATABASE_PORT=5432
DATABASE_PASSWORD=YOUR_DB_PASSWORD
DATABASE_NAME=ExpenseTracker
DATABASE_USERNAME=postgres
SECRET_KEY=YOUR_SECRET
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
```

### 4) Run migrations
```bash
python -m alembic upgrade head
```

### 5) Run the app
```bash
uvicorn app.main:app --reload
```

Open API docs:
- http://127.0.0.1:8000/docs

## Running Tests
```bash
pytest -q
```

## Auth Flow
1. **Sign-up** ? `POST /users/sign-up` (JSON)
2. **Sign-in** ? `POST /users/sign-in` (form data)
3. Use returned token in headers:
```
Authorization: Bearer <token>
```

## Core Endpoints (Summary)

### Users
- `POST /users/sign-up`
- `POST /users/sign-in`

### Expenses
- `POST /expenses/`
- `GET /expenses/`
- `GET /expenses/{id}`
- `PUT /expenses/{id}`
- `DELETE /expenses/{id}`
- `GET /analytics/this-month-stats`
- `GET /expenses/export`

### Budgets
- `POST /budgets/`
- `GET /budgets/`
- `GET /budgets/{category}`
- `PUT /budgets/{category}`
- `DELETE /budgets/{category}`

### Analytics
- `GET /analytics/history`
- `GET /analytics/daily-trend?days=...`
- `GET /analytics/daily-trend?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD`

## CSV Export
Example:
```
GET /expenses/export?start_date=2024-01-01&end_date=2024-12-31&category=Food
```
Returns a downloadable `expenses.csv`.

## Notes
- Expense validation: date cannot be in the future and must be year >= 2020.
- Username and password validation rules enforced in schemas.
- CORS is currently permissive (`*`). Restrict to frontend domain for production.

## Deployment (Preview)
- Set environment variables in your host (do not rely on `.env`).
- Run Alembic migrations on deploy.
- Use a production server (e.g., Uvicorn + Gunicorn).

---

If you want, we can now walk through Docker and deployment next.

