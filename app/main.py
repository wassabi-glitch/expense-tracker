from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
import os
from pathlib import Path
import logging


from . import models
from app.session import get_db
from .routers import users, expenses, budget, analytics
from alembic import command
from alembic.config import Config

# Tables are managed by Alembic migrations.

app = FastAPI(
    title="Expense Tracker API",
    description="A professional API to track your spending and manage budgets.",
    version="1.0.0"
)

# TODO: Replace with your frontend domain(s) in production.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logger = logging.getLogger(__name__)


def run_migrations() -> None:
    """Run Alembic migrations on startup when enabled."""
    if os.getenv("RUN_MIGRATIONS_ON_STARTUP") != "1":
        return
    try:
        root_dir = Path(__file__).resolve().parent.parent
        alembic_ini = root_dir / "alembic.ini"
        cfg = Config(str(alembic_ini))
        command.upgrade(cfg, "head")
        logger.info("Alembic migrations applied on startup.")
    except Exception:
        logger.exception("Failed to run Alembic migrations on startup.")


@app.get("/", tags=["Root"])
def read_root():
    return {"message": "Welcome to your Expense Tracker API. Head to /docs for the swagger UI!"}


@app.get("/health", tags=["Health"])
def health_check(db: Session = Depends(get_db)):
    """Check if the API and Database are connected."""
    return {"status": "online", "database": "connected"}


# Include Routers
app.include_router(users.router)
app.include_router(expenses.router)
app.include_router(budget.router)
app.include_router(analytics.router)


@app.on_event("startup")
def on_startup():
    run_migrations()
