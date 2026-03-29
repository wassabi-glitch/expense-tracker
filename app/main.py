from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from sqlalchemy import text
from sqlalchemy.orm import Session
from starlette.middleware.httpsredirect import HTTPSRedirectMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
import logging

from app.session import get_db
from app.routers import users, expenses, budget, analytics, auth, oauth_google, recurring, income, savings, goals, payments, notifications
from .models import ExpenseCategory
from config import settings

from contextlib import asynccontextmanager
logger = logging.getLogger(__name__)
try:
    from app.scheduler import start_scheduler
except Exception as exc:  # pragma: no cover - defensive fallback
    logger.warning("Scheduler is disabled: %s", exc)

    def start_scheduler():
        return None

# Tables are managed by Alembic migrations.

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Start the background scheduler
    scheduler = start_scheduler()
    yield
    # Shutdown: Stop the scheduler
    if scheduler:
        scheduler.shutdown()

app = FastAPI(
    title="Expense Tracker API",
    description="A professional API to track your spending and manage budgets.",
    version="1.0.0",
    lifespan=lifespan
)

origins = settings.cors_origins_list

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT","PATCH" ,"DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Timezone"],
    expose_headers=["Retry-After", "X-RateLimit-Limit", "X-RateLimit-Remaining", "X-RateLimit-Reset", "Content-Disposition"],
)

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=settings.trusted_hosts_list,
)

if settings.is_production:
    app.add_middleware(HTTPSRedirectMiddleware)


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response: Response = await call_next(request)

    connect_sources = ["'self'"] + settings.cors_origins_list
    csp_parts = [
        "default-src 'self'",
        "base-uri 'self'",
        "frame-ancestors 'none'",
        "object-src 'none'",
        "form-action 'self'",
        "script-src 'self'",
        "style-src 'self' 'unsafe-inline'",
        "img-src 'self' data: blob:",
        "font-src 'self' data:",
        f"connect-src {' '.join(connect_sources)}",
    ]
    if settings.is_production:
        csp_parts.append("upgrade-insecure-requests")

    response.headers["Content-Security-Policy"] = "; ".join(csp_parts)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
    response.headers["Cross-Origin-Resource-Policy"] = "same-origin"
    if settings.is_production:
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

    return response


@app.get("/", tags=["Root"])
def read_root():
    return {"message": "Welcome to your Expense Tracker API. Head to /docs for the swagger UI!"}


@app.get("/health", tags=["Health"])
def health_check(db: Session = Depends(get_db)):
    """Check if the API process is up and the DB is reachable."""
    try:
        db.execute(text("SELECT 1"))
        return {"status": "online", "database": "connected"}
    except Exception as exc:
        logger.error("Health DB check failed: %s", exc)
        raise HTTPException(
            status_code=503,
            detail={"status": "degraded", "database": "disconnected"},
        )


@app.get("/meta/categories", tags=["Meta"])
def get_categories():
    return [category.value for category in ExpenseCategory]


# Include Routers
app.include_router(users.router)
app.include_router(auth.router)
app.include_router(oauth_google.router)
app.include_router(expenses.router)
app.include_router(budget.router)
app.include_router(analytics.router)
app.include_router(recurring.router)
app.include_router(income.router)
app.include_router(savings.router)
app.include_router(goals.router)
app.include_router(payments.router)
app.include_router(notifications.router)
