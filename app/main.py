from fastapi import FastAPI, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from sqlalchemy.orm import Session
from starlette.middleware.httpsredirect import HTTPSRedirectMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.session import get_db
from .routers import users, expenses, budget, analytics
from .models import ExpenseCategory
from config import settings

# Tables are managed by Alembic migrations.

app = FastAPI(
    title="Expense Tracker API",
    description="A professional API to track your spending and manage budgets.",
    version="1.0.0"
)

origins = settings.cors_origins_list

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Timezone"],
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
    """Check if the API and Database are connected."""
    return {"status": "online", "database": "connected"}

@app.get("/meta/categories", tags=["Meta"])
def get_categories():
    return [category.value for category in ExpenseCategory]


# Include Routers
app.include_router(users.router)
app.include_router(expenses.router)
app.include_router(budget.router)
app.include_router(analytics.router)
