# 💰 SarfLog — Expense Tracker

> A full-stack personal finance app built with FastAPI & React.
> Track expenses, manage budgets, analyze spending — in English, Russian, and Uzbek.

[![CI](https://github.com/wassabi-glitch/expense-tracker/actions/workflows/ci.yml/badge.svg)](https://github.com/wassabi-glitch/expense-tracker/actions)

---

## ✨ Features

### Expense Management
- Create, edit, and delete expenses with title, amount, category, date, and description
- Advanced filtering by category, date range, and keyword search
- Sortable and paginated expense list
- CSV export with translated headers/categories and proper UTF-8 encoding for Excel

### Budget Tracking
- Set monthly budgets per category
- Real-time progress bars showing spending vs. limit
- Status indicators: **On Track**, **Warning**, **High Risk**, **Over Limit**
- Historical budget browsing with month/category/status filters

### Analytics Dashboard
- Lifetime spending summary (total spent, average transaction, transaction count)
- Daily spending trend chart (area chart)
- Category breakdown chart (horizontal bar chart)
- Quick presets (7d, 30d, 90d, 365d) and custom date range picker
- Input validation with user-friendly hints

### Authentication & Security
- Email/password sign-up with email verification
- Secure sign-in with JWT access tokens
- Google OAuth 2.0 integration
- Password reset via email link
- Resend verification email support
- Redis-backed rate limiting on sensitive endpoints (login, signup, export, budgets)
- CORS and trusted host protection

### Internationalization (i18n)
- Full support for **English**, **Russian**, and **Uzbek**
- Localized date/currency formatting (UZS with space-separated thousands)
- Translated validation messages, categories, and UI labels
- Language switcher persisted in localStorage

---

## 🏗️ Tech Stack

### Backend
| Technology | Purpose |
|---|---|
| **FastAPI** | REST API framework |
| **PostgreSQL 15** | Primary database |
| **SQLAlchemy 2.0** | ORM |
| **Alembic** | Database migrations |
| **Redis 7** | Rate limiting & caching |
| **Pydantic v2** | Request/response validation |
| **python-jose** | JWT token handling |
| **bcrypt** | Password hashing |
| **Uvicorn** | ASGI server |

### Frontend
| Technology | Purpose |
|---|---|
| **React 19** | UI framework |
| **Vite 7** | Build tool & dev server |
| **Tailwind CSS 4** | Styling |
| **Radix UI** | Accessible UI primitives |
| **Recharts** | Charts & data visualization |
| **React Router 7** | Client-side routing |
| **Zod** | Form validation |
| **i18next** | Internationalization |
| **Lucide React** | Icons |
| **date-fns** | Date utilities |

### Infrastructure
| Technology | Purpose |
|---|---|
| **Docker & Docker Compose** | Containerized local development |
| **GitHub Actions** | CI pipeline (lint, test, build, security audit) |

---

## 📁 Project Structure

```
ExpenseTracker/
├── app/                        # Backend application
│   ├── main.py                 # FastAPI app entry point
│   ├── models.py               # SQLAlchemy models
│   ├── schemas.py              # Pydantic schemas
│   ├── crud.py                 # Database operations
│   ├── oauth2.py               # JWT authentication
│   ├── session.py              # Database session
│   ├── utils.py                # Password hashing utilities
│   ├── timezone.py             # Timezone helpers
│   ├── email_service.py        # SMTP email sending
│   ├── email_verification.py   # Email token generation
│   ├── redis_rate_limiter.py   # Rate limiting middleware
│   └── routers/
│       ├── auth.py             # Login, signup, password reset
│       ├── users.py            # User profile management
│       ├── expenses.py         # CRUD + export + filtering
│       ├── budget.py           # Budget CRUD + stats
│       ├── analytics.py        # Trend & category analytics
│       └── oauth_google.py     # Google OAuth flow
├── frontend/
│   └── src/
│       ├── components/         # Shared UI components
│       │   ├── ui/             # Radix-based primitives
│       │   ├── AuthFormCard.jsx
│       │   ├── ConfirmDialog.jsx
│       │   ├── EmptyState.jsx
│       │   ├── Layout.jsx
│       │   ├── PageHeader.jsx
│       │   └── ProtectedRoute.jsx
│       ├── features/           # Feature-based modules
│       │   ├── auth/           # Login, Signup, ForgotPassword, etc.
│       │   ├── expenses/       # Expenses page + export
│       │   ├── budgets/        # Budgets page
│       │   ├── dashboard/      # Dashboard overview
│       │   ├── analytics/      # Analytics charts
│       │   └── settings/       # User settings
│       ├── lib/                # Shared utilities
│       │   ├── api.js          # API client (fetch wrapper)
│       │   ├── format.js       # Currency/date formatting
│       │   └── category.js     # Category icons & localization
│       └── i18n/               # Translation files (en, ru, uz)
├── tests/                      # Backend test suite
│   ├── conftest.py             # Shared fixtures
│   ├── test_auth.py
│   ├── test_expenses.py
│   ├── test_budget.py
│   ├── test_budget_alerts.py
│   ├── test_analytics.py
│   ├── test_export.py
│   └── test_health.py
├── alembic/                    # Database migrations
├── .github/workflows/ci.yml   # CI pipeline
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── Makefile
```

---

## 🚀 Getting Started

### Prerequisites
- **Python 3.12+**
- **Node.js 20+**
- **Docker & Docker Compose** (recommended)

### Option 1: Docker (Recommended)

```bash
# 1. Clone the repository
git clone https://github.com/wassabi-glitch/expense-tracker.git
cd expense-tracker

# 2. Create environment file
cp .env.example .env
# Edit .env with your values (DB credentials, secret key, SMTP, etc.)

# 3. Start all services
docker-compose up --build -d

# 4. Run database migrations
docker-compose exec api python -m alembic upgrade head

# 5. Verify
# API:      http://localhost:9000/health
# Swagger:  http://localhost:9000/docs
```

### Option 2: Manual Setup

```bash
# Backend
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
python -m alembic upgrade head
uvicorn app.main:app --reload --port 9000

# Frontend (in a separate terminal)
cd frontend
npm install
npm run dev
# App runs at http://localhost:5173
```

### Environment Variables

| Variable | Description | Example |
|---|---|---|
| `DATABASE_HOSTNAME` | PostgreSQL host | `localhost` |
| `DATABASE_PORT` | PostgreSQL port | `5433` |
| `DATABASE_USERNAME` | DB username | `postgres` |
| `DATABASE_PASSWORD` | DB password | `your_password` |
| `DATABASE_NAME` | DB name | `ExpenseTracker` |
| `SECRET_KEY` | JWT signing key | `your_secret_key` |
| `ALGORITHM` | JWT algorithm | `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Token TTL | `60` |
| `REDIS_URL` | Redis connection URL | `redis://localhost:6379/0` |
| `CORS_ORIGINS` | Allowed frontend origins | `http://localhost:5173` |
| `SMTP_HOST` | Email SMTP host | `sandbox.smtp.mailtrap.io` |
| `SMTP_PORT` | Email SMTP port | `587` |
| `SMTP_USERNAME` | SMTP username | `your_smtp_user` |
| `SMTP_PASSWORD` | SMTP password | `your_smtp_pass` |
| `FRONTEND_URL` | Frontend base URL | `http://localhost:5173` |

---

## 🧪 Testing

```bash
# Run all backend tests
pytest -q

# Run with coverage
pytest -q --cov=app --cov-report=term-missing --cov-fail-under=60

# Frontend lint check
cd frontend && npm run lint
```

**Test coverage includes:** authentication flows, expense CRUD, budget operations, budget alerts, analytics endpoints, CSV export, and health checks.

---

## 🔄 CI Pipeline

Every push and pull request triggers a **5-job CI pipeline**:

| Job | Description |
|---|---|
| **Lint** | Ruff (Python) + ESLint (JavaScript) |
| **Backend Tests** | Pytest with PostgreSQL service + Redis |
| **SAST (Bandit)** | Static security analysis for Python |
| **Frontend Build** | Vite production build verification |
| **Dependency Audit** | pip-audit + npm audit for vulnerability scanning |

---

## 📝 API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/users/sign-up` | Register new user |
| `POST` | `/users/sign-in` | Login (returns JWT) |
| `GET` | `/users/me` | Get current user profile |
| `GET` | `/auth/verify-email` | Verify email token |
| `POST` | `/auth/forgot-password` | Request password reset |
| `POST` | `/auth/reset-password` | Reset password with token |
| `POST` | `/auth/resend-verification` | Resend verification email |
| `GET` | `/auth/google/login` | Initiate Google OAuth |
| `GET` | `/auth/google/callback` | Google OAuth callback |
| `GET` | `/expenses/` | List expenses (filtered, paginated, sorted) |
| `POST` | `/expenses/` | Create expense |
| `PUT` | `/expenses/{id}` | Update expense |
| `DELETE` | `/expenses/{id}` | Delete expense |
| `GET` | `/expenses/export` | Export expenses as CSV |
| `GET` | `/expenses/categories` | List available categories |
| `GET` | `/budgets/` | List all budgets |
| `POST` | `/budgets/` | Create budget |
| `PUT` | `/budgets/{id}` | Update budget |
| `DELETE` | `/budgets/{id}` | Delete budget |
| `GET` | `/analytics/this-month-stats` | Current month budget stats |
| `GET` | `/analytics/history` | Lifetime spending summary |
| `GET` | `/analytics/daily-trend` | Daily spending trend |
| `GET` | `/analytics/category-breakdown` | Spending by category |
| `GET` | `/health` | Health check |

---

## 🌐 Supported Languages

| Language | Code | Coverage |
|---|---|---|
| English | `en` | Full |
| Russian | `ru` | Full |
| Uzbek | `uz` | Full |

---

## 🛡️ Security

- Passwords hashed with **bcrypt**
- JWT-based authentication
- Redis-backed **rate limiting** on sensitive endpoints
- **CORS** origin restrictions
- **Trusted host** middleware
- **Input validation** via Pydantic + Zod
- **Dependency auditing** (pip-audit + npm audit) enforced in CI
- See [SECURITY.md](SECURITY.md) for the security policy

---

## �️ V1 Roadmap

| Step | Feature | Status |
|------|---------|--------|
| **Step 0** | CI/CD Hardening — PostgreSQL in CI, branch protection, linting, dependency audits | ✅ Done |
| **Step 1** | Frontend Refactor — Feature-based architecture, shared components, dead code cleanup | ✅ Done |
| **Step 2** | Auth System Completion — Refresh tokens (HttpOnly cookie), token rotation, server-side revocation, `/auth/refresh` endpoint | 🔲 Next |
| **Step 3** | Premium Users + Recurring Expenses — Premium flag, auto-recurring expenses (daily/weekly/monthly) | 🔲 Planned |
| **Step 4** | Budget Rollover (Premium) — Carry unused budget to next month, Settings toggle | 🔲 Planned |
| **Step 5** | Advanced Analytics (Premium) — Month-over-month, category trends, spending velocity, locked charts for free users | 🔲 Planned |
| **Step 6** | Notification System — Toast notifications, budget alerts (80% spent, over budget) | 🔲 Planned |
| **Step 7** | Payment Integration — Payme/Click integration, subscription management, billing page | 🔲 Planned |
| **Step 8** | Production Deployment — sarflog.uz domain, Nginx + SSL, CI/CD deploy, monitoring, DB backups | 🔲 Planned |

---

## �📄 License

This project is private and not yet licensed for public distribution.

---

<p align="center">
  Built with ❤️ in Uzbekistan
</p>
