# pyrefly: ignore [missing-import]
import pytest
import concurrent.futures
# pyrefly: ignore [missing-import]
import pytest
from datetime import datetime, timedelta, timezone
from app import models
from app.session import get_db
from app.main import app
from app.redis_rate_limiter import redis_client
from tests.helpers import create_user_and_token
from app.routers.auth import _hash_reset_token
from app.oauth2 import create_refresh_token
from app import oauth2

def test_forgot_password_success(client):
    create_user_and_token(client, "recovery_test1", "recovery1@test.com", "Password123!")
    res = client.post("/auth/forgot-password", json={"email": "recovery1@test.com"})
    assert res.status_code == 200
    assert "inbox" in res.json()["message"].lower()

    override_db_factory = app.dependency_overrides.get(get_db)
    db_gen = override_db_factory()
    db = next(db_gen)
    try:
        user = db.query(models.User).filter(models.User.email == "recovery1@test.com").first()
        token = db.query(models.PasswordResetToken).filter(models.PasswordResetToken.user_id == user.id).first()
        assert token is not None
        assert token.used_at is None
    finally:
        db.close()
        try:
            next(db_gen)
        except StopIteration:
            pass

def test_forgot_password_ghost_user(client):
    res = client.post("/auth/forgot-password", json={"email": "doesnotexist@test.com"})
    assert res.status_code == 200
    assert "inbox" in res.json()["message"].lower()

def test_forgot_password_rate_limit(client):
    email = "ratelimit@test.com"
    redis_client.flushall()
    # Email bucket has capacity 3, so the 4th should fail
    for i in range(10):
        res = client.post("/auth/forgot-password", json={"email": email})
        if res.status_code == 429:
            assert res.json()["detail"] == "auth.forgot_password_rate_limited"
            # It should fail on the 4th iteration (i=3) since capacity is 3
            assert i == 3
            break
    else:
        pytest.fail("Rate limit was never hit")

def test_reset_password_rate_limit(client):
    redis_client.flushall()
    # Token bucket has capacity 5, so the 6th should fail
    for i in range(10):
        res = client.post("/auth/reset-password", json={
            "token": "some_fake_token_for_rl_test",
            "new_password": "NewValidPassword123!"
        })
        if res.status_code == 429:
            assert res.json()["detail"] == "auth.reset_password_rate_limited"
            # It should fail on the 6th iteration (i=5) since capacity is 5
            assert i == 5
            break
    else:
        pytest.fail("Rate limit was never hit")

def test_reset_password_invalid_token(client):
    res = client.post("/auth/reset-password", json={
        "token": "invalid_or_fake_token_12345",
        "new_password": "NewPassword123!"
    })
    assert res.status_code == 400
    assert res.json()["detail"] == "auth.reset_token_invalid_or_expired"

def _create_mock_reset_token(db, user_id, raw_token, minutes_offset=30, used=False):
    now = datetime.now(timezone.utc)
    token_hash = _hash_reset_token(raw_token)
    token = models.PasswordResetToken(
        user_id=user_id,
        token_hash=token_hash,
        expires_at=now + timedelta(minutes=minutes_offset),
        used_at=now if used else None
    )
    db.add(token)
    db.commit()
    return token

def test_reset_password_contains_email(client):
    create_user_and_token(client, "recovery_email", "johndoe@test.com", "Password123!")
    
    override_db_factory = app.dependency_overrides.get(get_db)
    db_gen = override_db_factory()
    db = next(db_gen)
    raw_token = "mock_token_for_email_test"
    try:
        user = db.query(models.User).filter(models.User.email == "johndoe@test.com").first()
        _create_mock_reset_token(db, user.id, raw_token)
    finally:
        db.close()
        try:
            next(db_gen)
        except StopIteration:
            pass

    res = client.post("/auth/reset-password", json={
        "token": raw_token,
        "new_password": "JohnDoe123!"
    })
    assert res.status_code == 400
    assert res.json()["detail"] == "auth.password_contains_email_local_part"

def test_reset_password_expired_token(client):
    create_user_and_token(client, "recovery_exp", "exp@test.com", "Password123!")
    override_db_factory = app.dependency_overrides.get(get_db)
    db_gen = override_db_factory()
    db = next(db_gen)
    raw_token = "mock_expired_token"
    try:
        user = db.query(models.User).filter(models.User.email == "exp@test.com").first()
        _create_mock_reset_token(db, user.id, raw_token, minutes_offset=-5)
    finally:
        db.close()
        try:
            next(db_gen)
        except StopIteration:
            pass

    res = client.post("/auth/reset-password", json={
        "token": raw_token,
        "new_password": "NewValidPassword123!"
    })
    assert res.status_code == 400
    assert res.json()["detail"] == "auth.reset_token_invalid_or_expired"

def test_reset_password_success_and_revocation(client):
    create_user_and_token(client, "recovery_succ", "success@test.com", "Password123!")
    override_db_factory = app.dependency_overrides.get(get_db)
    db_gen = override_db_factory()
    db = next(db_gen)
    raw_token = "mock_success_token"
    try:
        user = db.query(models.User).filter(models.User.email == "success@test.com").first()
        _create_mock_reset_token(db, user.id, raw_token)
        
        # Create a refresh token to simulate an active session
        refresh_token = create_refresh_token(user.id)
        
        # Verify redis has a token
        if hasattr(oauth2._redis, "values"):
            rt_keys = [k for k in oauth2._redis.values.keys() if k.startswith("rt:")]
        else:
            rt_keys = list(oauth2._redis.scan_iter("rt:*"))
        assert len(rt_keys) >= 1
    finally:
        db.close()
        try:
            next(db_gen)
        except StopIteration:
            pass

    res = client.post("/auth/reset-password", json={
        "token": raw_token,
        "new_password": "NewValidPassword123!"
    })
    assert res.status_code == 200
    assert "successful" in res.json()["message"].lower()
    
    # Check that the token was used
    db_gen = override_db_factory()
    db = next(db_gen)
    try:
        user = db.query(models.User).filter(models.User.email == "success@test.com").first()
        token_hash = _hash_reset_token(raw_token)
        token = db.query(models.PasswordResetToken).filter(models.PasswordResetToken.token_hash == token_hash).first()
        assert token.used_at is not None
        
        # Crucially, check that the refresh token was revoked (session invalidation)
        if hasattr(oauth2._redis, "values"):
            rt_keys_after = [k for k in oauth2._redis.values.keys() if k.startswith("rt:")]
        else:
            rt_keys_after = list(oauth2._redis.scan_iter("rt:*"))
        assert len(rt_keys_after) == 0
    finally:
        db.close()
        try:
            next(db_gen)
        except StopIteration:
            pass

def test_reset_password_race_condition(client):
    from tests.conftest import engine
    if engine.dialect.name == "sqlite":
        # pyrefly: ignore [missing-import]
        import pytest
        pytest.skip("In-memory SQLite with StaticPool does not support concurrent transactions")
        
    create_user_and_token(client, "recovery_race", "race@test.com", "Password123!")
    override_db_factory = app.dependency_overrides.get(get_db)
    db_gen = override_db_factory()
    db = next(db_gen)
    raw_token = "mock_race_token"
    try:
        user = db.query(models.User).filter(models.User.email == "race@test.com").first()
        _create_mock_reset_token(db, user.id, raw_token)
    finally:
        db.close()
        try:
            next(db_gen)
        except StopIteration:
            pass

    # We send 3 concurrent requests to reset password using the same token
    def make_request():
        return client.post("/auth/reset-password", json={
            "token": raw_token,
            "new_password": "NewValidPass123!"
        })

    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        futures = [executor.submit(make_request) for _ in range(3)]
        results = [f.result() for f in concurrent.futures.as_completed(futures)]

    # We expect exactly one 200 OK
    successes = [r for r in results if r.status_code == 200]
    # The others should fail with 400 invalid_token or 429 rate limit
    failures = [r for r in results if r.status_code in (400, 429)]

    assert len(successes) == 1, f"Expected 1 success, got {len(successes)}"
    assert len(failures) == 2, f"Expected 2 failures, got {len(failures)}"


def test_forgot_password_idempotency_conflict(client):
    from tests.conftest import engine
    if engine.dialect.name == "sqlite":
        # pyrefly: ignore [missing-import]
        import pytest
        pytest.skip("In-memory SQLite with StaticPool does not support concurrent transactions")

    redis_client.flushall()
    
    email = "ratelimit@test.com"
    idempotency_key = "test-idem-key-123"
    
    def make_request():
        return client.post("/auth/forgot-password", json={"email": email}, headers={"Idempotency-Key": idempotency_key})

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        f1 = executor.submit(make_request)
        f2 = executor.submit(make_request)
        
        responses = [f1.result(), f2.result()]

    status_codes = [r.status_code for r in responses]
    
    # We might have one 200 and one 409, or both 409 if the timing is extremely unlucky. But usually 200 + 409.
    assert 409 in status_codes
    assert 200 in status_codes
    
    conflict_res = next(r for r in responses if r.status_code == 409)
    assert conflict_res.json()["detail"] == "auth.idempotency_conflict_in_progress"
