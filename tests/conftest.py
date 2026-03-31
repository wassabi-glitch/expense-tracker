import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.redis_rate_limiter import redis_client
from app.session import Base, get_db
from app import models  # noqa: F401 — registers SQLAlchemy tables
from config import settings

# Tests rely on being able to toggle premium via a dev-only endpoint.
# In production, this endpoint is still blocked by `settings.is_production`.
settings.debug_allow_premium_toggle = True
settings.smtp_host = None # Disable emails in tests


# ---------------------------------------------------------------------------
# Database engine — environment-aware
# ---------------------------------------------------------------------------
# CI sets DATABASE_URL to a real PostgreSQL instance so tests run against the
# same engine as production.  Locally, we fall back to an in-memory SQLite
# database so you can run `pytest` without any external services.
# ---------------------------------------------------------------------------
DATABASE_URL = os.getenv("DATABASE_URL")

if DATABASE_URL:
    # CI / PostgreSQL path
    engine = create_engine(DATABASE_URL)
    TestingSessionLocal = sessionmaker(
        autocommit=False, autoflush=False, bind=engine
    )
else:
    # Local dev / SQLite path (unchanged from before)
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(
        autocommit=False, autoflush=False, bind=engine
    )


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(autouse=True)
def clear_rate_limit_state():
    # Prevent cross-test leakage from Redis-backed rate limiter keys.
    for key in redis_client.scan_iter("rl:*"):
        redis_client.delete(key)
    for key in redis_client.scan_iter("tb:*"):
        redis_client.delete(key)
    # Clean up refresh token keys between tests.
    for key in redis_client.scan_iter("rt:*"):
        redis_client.delete(key)
    for key in redis_client.scan_iter("rt_family:*"):
        redis_client.delete(key)
    for key in redis_client.scan_iter("rt_user:*"):
        redis_client.delete(key)


@pytest.fixture()
def session():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture()
def client():
    Base.metadata.create_all(bind=engine)
    with TestClient(app) as c:
        yield c
    Base.metadata.drop_all(bind=engine)
