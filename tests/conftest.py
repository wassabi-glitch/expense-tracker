import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.redis_rate_limiter import RateLimitResult, redis_client
from app.session import Base, get_db
from app import models  # noqa: F401 — registers SQLAlchemy tables
from config import settings

# Tests rely on being able to toggle premium via a dev-only endpoint.
# In production, this endpoint is still blocked by `settings.is_production`.
settings.debug_allow_premium_toggle = True
settings.smtp_host = None # Disable emails in tests
settings.resend_api_key = None # Disable Resend API emails in tests


class InMemoryRedis:
    def __init__(self):
        self.values = {}
        self.sets = {}

    def setex(self, key, _ttl, value):
        self.values[key] = value
        return True

    def get(self, key):
        return self.values.get(key)

    def delete(self, *keys):
        removed = 0
        for key in keys:
            removed += int(key in self.values or key in self.sets)
            self.values.pop(key, None)
            self.sets.pop(key, None)
        return removed

    def sadd(self, key, *values):
        bucket = self.sets.setdefault(key, set())
        before = len(bucket)
        bucket.update(values)
        return len(bucket) - before

    def srem(self, key, *values):
        bucket = self.sets.setdefault(key, set())
        before = len(bucket)
        for value in values:
            bucket.discard(value)
        return before - len(bucket)

    def smembers(self, key):
        return set(self.sets.get(key, set()))

    def expire(self, _key, _ttl):
        return True


_REDIS_AVAILABLE_CACHE = None


def _redis_available() -> bool:
    global _REDIS_AVAILABLE_CACHE
    if _REDIS_AVAILABLE_CACHE is not None:
        return _REDIS_AVAILABLE_CACHE
    try:
        _REDIS_AVAILABLE_CACHE = bool(redis_client.ping())
    except Exception:
        _REDIS_AVAILABLE_CACHE = False
    return _REDIS_AVAILABLE_CACHE


@pytest.fixture(autouse=True)
def silent_scheduler(monkeypatch):
    """Ensure the background scheduler never starts during tests."""
    # We mock it at the entry point in main.py to be 100% safe.
    monkeypatch.setattr("app.main.start_scheduler", lambda: None)


@pytest.fixture(autouse=True)
def fake_refresh_token_store(monkeypatch):
    """Keep auth tests local when Docker Redis is not running."""
    monkeypatch.setattr("app.oauth2._redis", InMemoryRedis())


@pytest.fixture(autouse=True)
def fake_rate_limits_without_redis(monkeypatch):
    if _redis_available():
        return

    def allow_limit(*_args, **_kwargs):
        return RateLimitResult(allowed=True, limit=999, remaining=999, reset_seconds=1)

    for module_name in (
        "app.routers.users",
        "app.routers.auth",
        "app.routers.expenses",
    ):
        monkeypatch.setattr(f"{module_name}.check_and_consume", allow_limit, raising=False)

    for module_name in (
        "app.routers.budget",
        "app.routers.debts",
        "app.routers.expenses",
        "app.routers.goals",
        "app.routers.income",
        "app.routers.notifications",
        "app.routers.payment_plans",
        "app.routers.projects",
        "app.routers.recurring",
    ):
        monkeypatch.setattr(f"{module_name}.consume_token_bucket", allow_limit, raising=False)


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
    try:
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
    except Exception:
        # Most tests use the rate limiter's fail-open behavior. A few explicit
        # Redis tests skip themselves when the local Redis service is absent.
        pass


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
