# pyrefly: ignore [missing-import]
import pytest
from app import models
from app.models import SecurityEvent, SecurityAction, SecurityStatus
from app.redis_rate_limiter import redis_client


# -----------------
# SIGN-UP TESTS
# -----------------
def test_signup_success(client, session):
    payload = {
        "username": "alice",
        "email": "alice@example.com",
        "password": "SecurePass1!"
    }

    response = client.post("/users/sign-up", json=payload)
    assert response.status_code == 201
    assert "X-RateLimit-Limit" in response.headers
    assert "X-RateLimit-Remaining" in response.headers
    assert "X-RateLimit-Reset" in response.headers

    data = response.json()
    assert data["username"] == payload["username"]
    assert data["email"] == payload["email"]
    assert "id" in data
    assert "password" not in data

    new_user = session.query(models.User).filter(
        models.User.email == "alice@example.com"
    ).first()
    assert new_user is not None
    assert new_user.hashed_password != payload["password"]

    # Verify SIGNUP security event was recorded
    event = session.query(SecurityEvent).filter(
        SecurityEvent.user_id == new_user.id,
        SecurityEvent.action == SecurityAction.SIGNUP,
    ).first()
    assert event is not None
    assert event.status == SecurityStatus.SUCCESS


def test_signup_existing_email(client):
    payload = {
        "username": "user1",
        "email": "duplicate@example.com",
        "password": "Password123!"
    }

    res1 = client.post("/users/sign-up", json=payload)
    assert res1.status_code == 201

    res2 = client.post("/users/sign-up", json=payload)
    assert res2.status_code == 400


def test_signup_existing_username(client):
    payload1 = {
        "username": "sameuser",
        "email": "user1@example.com",
        "password": "Password123!"
    }
    payload2 = {
        "username": "sameuser",
        "email": "user2@example.com",
        "password": "Password123!"
    }

    res1 = client.post("/users/sign-up", json=payload1)
    assert res1.status_code == 201

    res2 = client.post("/users/sign-up", json=payload2)
    assert res2.status_code in (400, 409)


def test_signup_idempotency_success(client, session):
    payload = {
        "username": "idem_user",
        "email": "idem@example.com",
        "password": "Password123!"
    }
    headers = {"Idempotency-Key": "123e4567-e89b-12d3-a456-426614174000"}

    res1 = client.post("/users/sign-up", json=payload, headers=headers)
    assert res1.status_code == 201
    data1 = res1.json()

    res2 = client.post("/users/sign-up", json=payload, headers=headers)
    assert res2.status_code == 201
    data2 = res2.json()

    assert data1 == data2

def test_signup_idempotency_conflict(client):
    payload = {
        "username": "idem_user_2",
        "email": "idem2@example.com",
        "password": "Password123!"
    }
    idem_key = "123e4567-e89b-12d3-a456-426614174001"
    headers = {"Idempotency-Key": idem_key}

    # Manually lock the key in redis to simulate an in-progress request
    redis_client.set(f"idempotency:signup:{idem_key}", "locked")

    res = client.post("/users/sign-up", json=payload, headers=headers)
    assert res.status_code == 409
    assert res.json()["detail"] == "auth.idempotency_conflict_in_progress"

    # Cleanup
    redis_client.delete(f"idempotency:signup:{idem_key}")



@pytest.mark.parametrize("payload, status_code", [
    ({"username": "user", "email": "badformat.com", "password": "Password123!"}, 422),
    ({"username": "user", "email": "ok@example.com", "password": ""}, 422),
    ({"email": "ok@example.com", "password": "Password123!"}, 422),
    ({"username": "user", "email": None, "password": "Password123!"}, 422),
])
def test_signup_invalid_input(client, payload, status_code):
    res = client.post("/users/sign-up", json=payload)
    assert res.status_code == status_code


@pytest.mark.parametrize("password", [
    "short7!",        # too short
    "nouppercase1!",  # missing uppercase
    "NOLOWERCASE1!",  # missing lowercase
    "NoNumber!",      # missing number
    "NoSpecial123",   # missing special
    "pass wordA1!",   # contains space
    "A" * 65 + "1!",  # too long
])
def test_signup_weak_password(client, password):
    res = client.post("/users/sign-up", json={
        "username": "weakuser",
        "email": "weak@example.com",
        "password": password
    })
    assert res.status_code == 422


@pytest.mark.parametrize("username", [
    "ab",               # too short
    "a" * 33,           # too long
    "user name",        # contains space
    "user-name",        # invalid char
    ".user",            # starts with dot
    "user_",            # ends with underscore
    "user..name",       # consecutive dots
    "user__name",       # consecutive underscores
    "user._name",       # mixed separators
    "12345",            # only numbers
])
def test_signup_invalid_username(client, username):
    res = client.post("/users/sign-up", json={
        "username": username,
        "email": "valid@example.com",
        "password": "password123"
    })
    assert res.status_code == 422


def test_signup_email_normalized(client):
    res = client.post("/users/sign-up", json={
        "username": "normalizeuser",
        "email": "  Alice@Example.COM  ",
        "password": "Password123!"
    })
    assert res.status_code == 201
    data = res.json()
    assert data["email"] == "alice@example.com"


def test_signup_rate_limit_blocks_after_repeated_attempts(client):
    for key in redis_client.scan_iter("rl:signup:*"):
        redis_client.delete(key)

    for i in range(5):
        res = client.post("/users/sign-up", json={
            "username": f"rlsignup{i}",
            "email": f"rlsignup{i}@example.com",
            "password": "Password123!",
        })
        assert res.status_code == 201
        assert "X-RateLimit-Limit" in res.headers
        assert "X-RateLimit-Remaining" in res.headers
        assert "X-RateLimit-Reset" in res.headers

    blocked = None
    for i in range(30):
        res = client.post("/users/sign-up", json={
            "username": f"rlsignup_blocked_{i}",
            "email": f"rlsignup_blocked_{i}@example.com",
            "password": "Password123!",
        })
        if res.status_code == 429:
            blocked = res
            break
    assert blocked is not None
    assert blocked.status_code == 429
    assert "Retry-After" in blocked.headers


def test_signup_global_rate_limit_blocks(client):
    import time
    now = int(time.time())
    # Manually exhaust the global token bucket to simulate a global spike
    redis_client.hset("tb:signup_global:global", mapping={"tokens": 0, "last_refill": now})
    
    res = client.post("/users/sign-up", json={
        "username": "globalrl",
        "email": "globalrl@example.com",
        "password": "Password123!",
    })
    assert res.status_code == 429
    assert res.json()["detail"] == "auth.signup_global_rate_limited"
    assert "Retry-After" in res.headers

    # Cleanup
    redis_client.delete("tb:signup_global:global")


# -----------------
# SIGN-IN TESTS
# -----------------
def test_signin_success(client, session):
    client.post("/users/sign-up", json={
        "username": "bob",
        "email": "bob@example.com",
        "password": "MyPassword1!"
    })

    # Mark user as verified (sign-in rejects unverified users)
    user = session.query(models.User).filter(
        models.User.email == "bob@example.com"
    ).first()
    user.is_verified = True
    session.commit()

    response = client.post("/users/sign-in", data={
        "username": "bob@example.com",
        "password": "MyPassword1!"
    })

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert "X-RateLimit-Limit" in response.headers
    assert "X-RateLimit-Remaining" in response.headers
    assert "X-RateLimit-Reset" in response.headers

    # Verify LOGIN security event was recorded
    user = session.query(models.User).filter(
        models.User.email == "bob@example.com"
    ).first()
    event = session.query(SecurityEvent).filter(
        SecurityEvent.user_id == user.id,
        SecurityEvent.action == SecurityAction.LOGIN,
        SecurityEvent.status == SecurityStatus.SUCCESS,
    ).first()
    assert event is not None


@pytest.mark.parametrize("email,password,status_code", [
    ("wrong@example.com", "password123", 403),
    ("bob@example.com", "wrongpassword", 403),
    (None, "password123", 422),
    ("bob@example.com", None, 422),
])
def test_signin_failure(client, email, password, status_code):
    client.post("/users/sign-up", json={
        "username": "bob",
        "email": "bob@example.com",
        "password": "Password123!"
    })

    res = client.post("/users/sign-in", data={
        "username": email,
        "password": password
    })

    assert res.status_code == status_code


def test_signin_rate_limit_blocks_after_repeated_failures(client):
    for key in redis_client.scan_iter("rl:login:*"):
        redis_client.delete(key)

    email = "ratelimit@example.com"
    client.post("/users/sign-up", json={
        "username": "ratelimituser",
        "email": email,
        "password": "Password123!"
    })

    for _ in range(5):
        res = client.post("/users/sign-in", data={
            "username": email,
            "password": "WrongPassword123!",
        })
        assert res.status_code == 403
        assert "X-RateLimit-Limit" in res.headers
        assert "X-RateLimit-Remaining" in res.headers
        assert "X-RateLimit-Reset" in res.headers

    blocked = None
    for _ in range(30):
        res = client.post("/users/sign-in", data={
            "username": email,
            "password": "WrongPassword123!",
        })
        if res.status_code == 429:
            blocked = res
            break
    assert blocked is not None
    assert blocked.status_code == 429
    assert "Retry-After" in blocked.headers


def test_signup_disposable_email_blocked(client):
    # Using mailinator.com which is in the standard disposable email blocklist
    res = client.post("/users/sign-up", json={
        "username": "spammer",
        "email": "spammer123@mailinator.com",
        "password": "Password123!"
    })
    
    assert res.status_code == 400
    assert res.json().get("detail") == "auth.disposable_email_blocked"


# -----------------
# VERIFY EMAIL TESTS
# -----------------
def test_verify_email_success(client, session):
    client.post("/users/sign-up", json={
        "username": "verifyuser",
        "email": "verify@example.com",
        "password": "Password123!"
    })

    user = session.query(models.User).filter(
        models.User.email == "verify@example.com"
    ).first()
    assert not user.is_verified

    from app.email_verification import issue_email_verification_token
    raw_token = issue_email_verification_token(session, user)

    res = client.post("/auth/verify-email", json={"token": raw_token})
    assert res.status_code == 200
    assert "X-RateLimit-Limit" in res.headers
    
    session.refresh(user)
    assert user.is_verified

    # Verify EMAIL_VERIFIED security event was recorded
    event = session.query(SecurityEvent).filter(
        SecurityEvent.user_id == user.id,
        SecurityEvent.action == SecurityAction.EMAIL_VERIFIED,
    ).first()
    assert event is not None
    assert event.status == SecurityStatus.SUCCESS

def test_verify_email_idempotent(client, session):
    client.post("/users/sign-up", json={
        "username": "idemuser",
        "email": "idem@example.com",
        "password": "Password123!"
    })

    user = session.query(models.User).filter(
        models.User.email == "idem@example.com"
    ).first()

    from app.email_verification import issue_email_verification_token
    raw_token = issue_email_verification_token(session, user)

    res1 = client.post("/auth/verify-email", json={"token": raw_token})
    assert res1.status_code == 200

    # Second click (e.g. from the user after a scanner clicked it)
    res2 = client.post("/auth/verify-email", json={"token": raw_token})
    assert res2.status_code == 200

def test_verify_email_rate_limit(client):
    for key in redis_client.scan_iter("rl:verify_email:*"):
        redis_client.delete(key)

    for _ in range(5):
        res = client.post("/auth/verify-email", json={"token": "some-invalid-token"})
        assert res.status_code == 400

    res = client.post("/auth/verify-email", json={"token": "some-invalid-token"})
    assert res.status_code == 429
    assert res.json()["detail"] == "auth.verify_email_rate_limited"

# -----------------
# LOGIN RATE LIMIT TESTS
# -----------------
def test_login_email_rate_limit(client):
    for key in redis_client.scan_iter("rl:login_email:*"):
        redis_client.delete(key)

    for _ in range(5):
        res = client.post("/users/sign-in", data={
            "username": "targeted@example.com",
            "password": "WrongPassword!"
        })
        assert res.status_code == 403

    res = client.post("/users/sign-in", data={
        "username": "targeted@example.com",
        "password": "WrongPassword!"
    })
    assert res.status_code == 429
    assert res.json()["detail"] == "auth.login_rate_limited"


def test_login_ip_rate_limit(client):
    for key in redis_client.scan_iter("rl:login_ip:*"):
        redis_client.delete(key)

    # Email bucket allows 5. So we must use 20 *different* emails 
    # to bypass the email bucket and hit the IP bucket limit (20)
    for i in range(20):
        res = client.post("/users/sign-in", data={
            "username": f"bot{i}@example.com",
            "password": "WrongPassword!"
        })
        assert res.status_code == 403

    res = client.post("/users/sign-in", data={
        "username": "bot20@example.com",
        "password": "WrongPassword!"
    })
    assert res.status_code == 429
    assert res.json()["detail"] == "auth.login_rate_limited"

def test_login_idempotency_conflict(client):
    from app.redis_rate_limiter import redis_client
    # Manually lock the sign-in key for this idempotency key
    idem_key = "test-login-idem-123"
    cache_key = f"idempotency:signin:{idem_key}"
    redis_client.set(cache_key, "IN_PROGRESS", ex=30)
    
    res = client.post("/users/sign-in", data={
        "username": "someuser@example.com",
        "password": "Password123!"
    }, headers={"Idempotency-Key": idem_key})
    
    assert res.status_code == 409
    assert res.json()["detail"] == "auth.idempotency_conflict_in_progress"

# -----------------
# LOGOUT ALL TESTS
# -----------------
def test_logout_all(client, session):
    email = "logoutall@example.com"
    password = "SecurePass1!"
    
    client.post("/users/sign-up", json={
        "username": "logoutall",
        "email": email,
        "password": password
    })
    
    user = session.query(models.User).filter(
        models.User.email == email
    ).first()
    user.is_verified = True
    session.commit()
    
    # Log in Device 1
    res1 = client.post("/users/sign-in", data={
        "username": email,
        "password": password
    })
    token1 = res1.json()["access_token"]
    cookie1 = res1.cookies.get("refresh_token")
    
    # Log in Device 2
    res2 = client.post("/users/sign-in", data={
        "username": email,
        "password": password
    })
    cookie2 = res2.cookies.get("refresh_token")
    
    assert cookie1 != cookie2
    
    # Call logout-all from Device 1
    logout_res = client.post("/auth/logout-all", headers={
        "Authorization": f"Bearer {token1}"
    })
    assert logout_res.status_code == 200
    assert logout_res.json()["message"] == "Logged out of all devices successfully."

    # Verify LOGOUT_ALL security event was recorded
    event = session.query(SecurityEvent).filter(
        SecurityEvent.user_id == user.id,
        SecurityEvent.action == SecurityAction.LOGOUT_ALL,
    ).first()
    assert event is not None
    assert event.status == SecurityStatus.SUCCESS
    
    # Verify Device 1 refresh fails
    client.cookies.set("refresh_token", cookie1)
    refresh_res1 = client.post("/auth/refresh")
    assert refresh_res1.status_code == 401
    
    # Verify Device 2 refresh fails
    client.cookies.set("refresh_token", cookie2)
    refresh_res2 = client.post("/auth/refresh")
    assert refresh_res2.status_code == 401


# -----------------
# CHANGE PASSWORD
# -----------------

def test_change_password_success(client, session):
    from tests.helpers import create_user_and_token
    headers = create_user_and_token(client, "changepw", "changepw@example.com", "OldPass1!")

    payload = {
        "current_password": "OldPass1!",
        "new_password": "NewStrongPass2@"
    }

    response = client.post(
        "/auth/change-password",
        json=payload,
        headers=headers
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert response.cookies.get("refresh_token") is not None
    
    # Try logging in with old password
    login_old = client.post("/users/sign-in", data={
        "username": "changepw@example.com",
        "password": "OldPass1!"
    })
    assert login_old.status_code == 403

    # Try logging in with new password
    login_new = client.post("/users/sign-in", data={
        "username": "changepw@example.com",
        "password": "NewStrongPass2@"
    })
    assert login_new.status_code == 200

    # Verify PASSWORD_CHANGED security event was recorded
    user = session.query(models.User).filter(
        models.User.email == "changepw@example.com"
    ).first()
    event = session.query(SecurityEvent).filter(
        SecurityEvent.user_id == user.id,
        SecurityEvent.action == SecurityAction.PASSWORD_CHANGED,
        SecurityEvent.status == SecurityStatus.SUCCESS,
    ).first()
    assert event is not None


def test_change_password_wrong_current(client, session):
    from tests.helpers import create_user_and_token
    headers = create_user_and_token(client, "wrongpw", "wrongpw@example.com", "OldPass1!")

    payload = {
        "current_password": "WrongPassword1!",
        "new_password": "NewStrongPass2@"
    }
    
    response = client.post(
        "/auth/change-password",
        json=payload,
        headers=headers
    )
    assert response.status_code == 403

    # Verify PASSWORD_CHANGED / FAILED security event was recorded
    user = session.query(models.User).filter(
        models.User.email == "wrongpw@example.com"
    ).first()
    event = session.query(SecurityEvent).filter(
        SecurityEvent.user_id == user.id,
        SecurityEvent.action == SecurityAction.PASSWORD_CHANGED,
        SecurityEvent.status == SecurityStatus.FAILED,
    ).first()
    assert event is not None
    assert event.metadata_["reason"] == "incorrect_current_password"


def test_change_password_google_only(client, session):
    # Simulate google-only user
    from app import models, utils
    
    email = "googleonly@example.com"
    user = models.User(
        email=email,
        username="googleonly",
        hashed_password=utils.hash_password("dummy-password-not-used"),
        is_verified=True,
    )
    session.add(user)
    session.flush()
    
    session.add(models.UserIdentity(
        user_id=user.id,
        provider="google",
        provider_user_id="12345",
        provider_email=email
    ))
    session.commit()
    
    from app.oauth2 import create_access_token
    token = create_access_token({"user_id": user.id})

    payload = {
        "current_password": "Anything123!",
        "new_password": "NewStrongPass2@"
    }
    
    response = client.post(
        "/auth/change-password",
        json=payload,
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 400
    assert "google_only_cannot_change_password" in response.json()["detail"]


def test_mobile_change_password_success(client, session):
    from tests.helpers import create_user_and_token
    headers = create_user_and_token(client, "mobchangepw", "mobchangepw@example.com", "OldPass1!")

    payload = {
        "current_password": "OldPass1!",
        "new_password": "NewStrongPass2@"
    }
    
    response = client.post(
        "/auth/mobile/change-password",
        json=payload,
        headers=headers
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data


# -----------------
# SECURITY EVENT DEDICATED TESTS
# -----------------

def test_security_event_login_failed_stores_ip(client, session):
    """Verify that a failed login records IP address."""
    client.post("/users/sign-up", json={
        "username": "iptest",
        "email": "iptest@example.com",
        "password": "Password123!"
    })

    client.post("/users/sign-in", data={
        "username": "iptest@example.com",
        "password": "WrongPassword1!",
    })

    events = session.query(SecurityEvent).filter(
        SecurityEvent.action == SecurityAction.LOGIN,
        SecurityEvent.status == SecurityStatus.FAILED,
    ).all()
    # Should have at least one failed login event
    assert len(events) >= 1
    event = events[-1]  # latest
    assert event.ip_address is not None
    assert event.ip_address != ""


def test_security_event_no_sensitive_data(client, session):
    """Verify that no passwords or tokens leak into security events."""
    from tests.helpers import create_user_and_token
    headers = create_user_and_token(client, "audituser", "audituser@example.com", "SecurePass1!")

    # Trigger a failed change-password (adds metadata with reason)
    client.post("/auth/change-password", json={
        "current_password": "WrongOldPass1!",
        "new_password": "NewStrongPass2@"
    }, headers=headers)

    # Check ALL security events — none should contain passwords or tokens
    all_events = session.query(SecurityEvent).all()
    for event in all_events:
        if event.metadata_:
            meta_str = str(event.metadata_)
            assert "SecurePass1!" not in meta_str
            assert "WrongOldPass1!" not in meta_str
            assert "NewStrongPass2@" not in meta_str
            # No JWT tokens
            assert "eyJ" not in meta_str


def test_security_event_user_id_nullable_on_failed_login(client, session):
    """When login fails for a nonexistent email, user_id should be None."""
    client.post("/users/sign-in", data={
        "username": "nobody_exists@example.com",
        "password": "AnyPassword1!",
    })

    event = session.query(SecurityEvent).filter(
        SecurityEvent.action == SecurityAction.LOGIN,
        SecurityEvent.status == SecurityStatus.FAILED,
    ).order_by(SecurityEvent.id.desc()).first()
    assert event is not None
    assert event.user_id is None
    assert event.metadata_["reason"] == "user_not_found"
    assert event.metadata_["email"] == "nobody_exists@example.com"


# -----------------
# RETRY-AFTER HEADER TESTS (Issue 3)
# -----------------


def test_change_password_rate_limit_includes_retry_after(client, monkeypatch):
    """Verify /auth/change-password 429 includes Retry-After header."""
    from tests.helpers import create_user_and_token
    from app.redis_rate_limiter import RateLimitResult

    headers = create_user_and_token(client, "cp_rl", "cp_rl@example.com", "Pass123!")

    def fake_check_and_consume(scope, identifier, window_seconds=60, max_attempts=5):
        return RateLimitResult(allowed=False, limit=max_attempts, remaining=0, reset_seconds=42)

    monkeypatch.setattr("app.routers.auth.check_and_consume", fake_check_and_consume)

    payload = {"current_password": "Pass123!", "new_password": "NewPass2@"}
    response = client.post("/auth/change-password", json=payload, headers=headers)
    assert response.status_code == 429
    assert response.json()["detail"] == "auth.change_password_rate_limited"
    assert "retry-after" in response.headers
    assert response.headers["retry-after"] == "42"


def test_mobile_change_password_rate_limit_includes_retry_after(client, monkeypatch):
    """Verify /auth/mobile/change-password 429 includes Retry-After header."""
    from tests.helpers import create_user_and_token
    from app.redis_rate_limiter import RateLimitResult

    headers = create_user_and_token(client, "mcp_rl", "mcp_rl@example.com", "Pass123!")

    def fake_check_and_consume(scope, identifier, window_seconds=60, max_attempts=5):
        return RateLimitResult(allowed=False, limit=max_attempts, remaining=0, reset_seconds=99)

    monkeypatch.setattr("app.routers.auth.check_and_consume", fake_check_and_consume)

    payload = {"current_password": "Pass123!", "new_password": "NewPass2@"}
    response = client.post("/auth/mobile/change-password", json=payload, headers=headers)
    assert response.status_code == 429
    assert response.json()["detail"] == "auth.change_password_rate_limited"
    assert "retry-after" in response.headers
    assert response.headers["retry-after"] == "99"


def test_verify_password_rate_limit_includes_retry_after(client, monkeypatch):
    """Verify /auth/verify-password 429 includes Retry-After header."""
    from tests.helpers import create_user_and_token
    from app.redis_rate_limiter import RateLimitResult

    headers = create_user_and_token(client, "vp_rl", "vp_rl@example.com", "Pass123!")

    def fake_check_and_consume(scope, identifier, window_seconds=60, max_attempts=5):
        return RateLimitResult(allowed=False, limit=max_attempts, remaining=0, reset_seconds=77)

    monkeypatch.setattr("app.routers.auth.check_and_consume", fake_check_and_consume)

    response = client.post(
        "/auth/verify-password",
        json={"password": "Pass123!"},
        headers=headers,
    )
    assert response.status_code == 429
    assert response.json()["detail"] == "auth.rate_limited"
    assert "retry-after" in response.headers
    assert response.headers["retry-after"] == "77"

