"""
Tests for the refresh token system (Step 2: Auth System Completion).

Covers:
  - Login returns refresh cookie + access token
  - POST /auth/refresh — token rotation
  - POST /auth/logout — server-side invalidation
  - Used refresh tokens cannot be reused (rotation security)
  - Password reset revokes all refresh tokens
"""
import concurrent.futures
from unittest.mock import patch


from app import models, oauth2
from app.redis_rate_limiter import RateLimitResult
from app.routers import oauth_google


# ───────────────────────────────────────────────────
# Helper: create a verified user and log them in
# ───────────────────────────────────────────────────

def create_and_login(client, session, email="refresh@example.com",
                     username="refreshuser", password="SecurePass1!"):
    """Signs up a user, verifies them, logs in, and returns the response."""
    client.post("/users/sign-up", json={
        "username": username,
        "email": email,
        "password": password,
    })
    user = session.query(models.User).filter(
        models.User.email == email
    ).first()
    user.is_verified = True
    session.commit()

    response = client.post("/users/sign-in", data={
        "username": email,
        "password": password,
    })
    return response


# ═══════════════════════════════════════════════════
# LOGIN: Refresh cookie is set
# ═══════════════════════════════════════════════════

def test_login_returns_refresh_cookie(client, session):
    """Login should return an access token AND set a refresh_token cookie."""
    response = create_and_login(client, session)

    assert response.status_code == 200
    data = response.json()

    # Access token is in the response body
    assert "access_token" in data
    assert data["token_type"] == "bearer"

    # Refresh token is in a Set-Cookie header
    assert "refresh_token" in response.cookies


def test_login_stores_refresh_token_in_redis(client, session):
    """After login, there should be a refresh token hash stored in Redis."""
    create_and_login(client, session)

    # Check that at least one rt:* key exists in Redis
    if hasattr(oauth2._redis, "values"):
        rt_keys = [k for k in oauth2._redis.values.keys() if k.startswith("rt:")]
    else:
        rt_keys = list(oauth2._redis.scan_iter("rt:*"))
    assert len(rt_keys) >= 1


# ═══════════════════════════════════════════════════
# POST /auth/refresh — Happy path
# ═══════════════════════════════════════════════════

def test_refresh_returns_new_access_token(client, session):
    """POST /auth/refresh with a valid cookie should return a new access token."""
    login_res = create_and_login(client, session)
    assert "refresh_token" in login_res.cookies

    # Call /auth/refresh — the cookie is sent automatically by TestClient
    refresh_res = client.post("/auth/refresh")

    assert refresh_res.status_code == 200
    data = refresh_res.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_refresh_rotates_cookie(client, session):
    """After refresh, the old cookie should be replaced with a new one."""
    login_res = create_and_login(client, session)
    old_cookie = login_res.cookies.get("refresh_token")
    assert old_cookie is not None

    refresh_res = client.post("/auth/refresh")
    assert refresh_res.status_code == 200

    new_cookie = refresh_res.cookies.get("refresh_token")
    assert new_cookie is not None
    # The cookie value should have changed (rotation)
    assert new_cookie != old_cookie


def test_refresh_new_access_token_works(client, session):
    """The new access token from refresh should be usable for API calls."""
    create_and_login(client, session)

    refresh_res = client.post("/auth/refresh")
    assert refresh_res.status_code == 200

    new_token = refresh_res.json()["access_token"]
    me_res = client.get("/users/me", headers={
        "Authorization": f"Bearer {new_token}"
    })
    assert me_res.status_code == 200
    assert me_res.json()["email"] == "refresh@example.com"


# ═══════════════════════════════════════════════════
# POST /auth/refresh — Error cases
# ═══════════════════════════════════════════════════

def test_refresh_without_cookie_returns_401(client):
    """POST /auth/refresh without a cookie should return 401."""
    response = client.post("/auth/refresh")
    assert response.status_code == 401


def test_refresh_with_invalid_cookie_returns_401(client):
    """POST /auth/refresh with a garbage cookie should return 401."""
    client.cookies.set("refresh_token", "garbage_token_value")
    response = client.post("/auth/refresh")
    assert response.status_code == 401


def test_used_refresh_token_cannot_be_reused_and_revokes_family(client, session):
    """
    After a refresh token is used, the OLD token should be invalid.
    If the old token is replayed, the ENTIRE token family (including
    the newest active token) must be revoked.
    """
    login_res = create_and_login(client, session)
    old_cookie = login_res.cookies.get("refresh_token")

    # Use the refresh token once — this should succeed
    refresh_res = client.post("/auth/refresh")
    assert refresh_res.status_code == 200
    new_cookie = refresh_res.cookies.get("refresh_token")

    # Fast-forward the rotated marker's timestamp so it's outside the 5-second grace period
    from app.oauth2 import _hash_token, _redis
    old_hash = _hash_token(old_cookie)
    rotated_marker_key = f"rotated:{old_hash}"
    rotated_info = _redis.get(rotated_marker_key)
    if rotated_info:
        parts = rotated_info.split("|", 2)
        if len(parts) >= 2:
            import time
            fake_time = int(time.time()) - 10
            new_info = f"{parts[0]}|{parts[1]}|{fake_time}"
            _redis.setex(rotated_marker_key, 604800, new_info)

    # Now try to manually use the OLD cookie again
    # (simulating an attacker who stole the old token)
    client.cookies.set("refresh_token", old_cookie)
    replay_res = client.post("/auth/refresh")
    assert replay_res.status_code == 401

    # Because a replay occurred, the active token family should be revoked.
    # Trying to use the newest token should now fail as well.
    client.cookies.set("refresh_token", new_cookie)
    active_res = client.post("/auth/refresh")
    assert active_res.status_code == 401


# ═══════════════════════════════════════════════════
# POST /auth/logout
# ═══════════════════════════════════════════════════

def test_logout_clears_cookie(client, session):
    """POST /auth/logout should clear the refresh_token cookie."""
    create_and_login(client, session)

    logout_res = client.post("/auth/logout")
    assert logout_res.status_code == 200
    assert logout_res.json()["message"] == "Logged out successfully."


def test_logout_invalidates_refresh_token(client, session):
    """After logout, the refresh token should no longer work."""
    login_res = create_and_login(client, session)
    old_cookie = login_res.cookies.get("refresh_token")

    # Logout
    client.post("/auth/logout")

    # Try to use the old cookie — should fail
    client.cookies.set("refresh_token", old_cookie)
    refresh_res = client.post("/auth/refresh")
    assert refresh_res.status_code == 401


def test_logout_without_cookie_succeeds(client):
    """Logout without a cookie should still return 200 (idempotent)."""
    response = client.post("/auth/logout")
    assert response.status_code == 200


# ═══════════════════════════════════════════════════
# Password Reset → Revokes All Tokens
# ═══════════════════════════════════════════════════

def test_password_reset_revokes_all_refresh_tokens(client, session):
    """
    After a password reset, ALL refresh tokens for that user should be
    invalidated. This ensures that if someone resets their password
    because their account was compromised, the attacker's session dies.
    """
    # Create user and log in
    create_and_login(client, session)

    user = session.query(models.User).filter(
        models.User.email == "refresh@example.com"
    ).first()

    # Verify there ARE refresh tokens in Redis
    if hasattr(oauth2._redis, "values"):
        rt_keys_before = [k for k in oauth2._redis.values.keys() if k.startswith("rt:")]
    else:
        rt_keys_before = list(oauth2._redis.scan_iter("rt:*"))
    assert len(rt_keys_before) >= 1

    # Manually revoke all tokens (simulating what password reset does)
    oauth2.revoke_all_user_tokens(user.id)

    # All refresh token keys should be gone
    if hasattr(oauth2._redis, "values"):
        rt_keys_after = [k for k in oauth2._redis.values.keys() if k.startswith("rt:")]
    else:
        rt_keys_after = list(oauth2._redis.scan_iter("rt:*"))
    assert len(rt_keys_after) == 0

    # Trying to refresh should fail
    refresh_res = client.post("/auth/refresh")
    assert refresh_res.status_code == 401


# ═══════════════════════════════════════════════════
# Access token from login works for protected routes
# ═══════════════════════════════════════════════════

def test_login_access_token_works_for_protected_routes(client, session):
    """The access token returned from login should work for /users/me."""
    login_res = create_and_login(client, session)
    token = login_res.json()["access_token"]

    me_res = client.get("/users/me", headers={
        "Authorization": f"Bearer {token}"
    })
    assert me_res.status_code == 200
    assert me_res.json()["email"] == "refresh@example.com"


# ═══════════════════════════════════════════════════
# Edge Case: Expired Token
# ═══════════════════════════════════════════════════

def test_expired_refresh_token_rejected(client, session):
    """An explicitly expired refresh token should be rejected with 401."""

    create_and_login(client, session)
    user = session.query(models.User).filter(models.User.email == "refresh@example.com").first()

    # Create a token normally
    expired_token = oauth2.create_refresh_token(user.id)
    token_hash = oauth2._hash_token(expired_token)
    
    # Simulate expiration by simply deleting it from Redis (which is what TTL does)
    oauth2._redis.delete(f"rt:{token_hash}")

    client.cookies.set("refresh_token", expired_token)
    response = client.post("/auth/refresh")
    
    assert response.status_code == 401


# ═══════════════════════════════════════════════════
# Google OAuth Integration
# ═══════════════════════════════════════════════════

@patch("app.routers.oauth_google.httpx.post")
@patch("app.routers.oauth_google.id_token.verify_oauth2_token")
def test_google_oauth_returns_refresh_cookie(mock_verify, mock_post, client, session):
    """Google OAuth callback should set a refresh_token cookie upon success."""
    
    # 1. Generate a valid state token to pass the CSRF check
    nonce = "testnonce"
    state_token = oauth_google._create_state(nonce)
    
    # 2. Mock Google's token endpoint response
    class MockResponse:
        status_code = 200
        def json(self):
            return {"id_token": "mocked_id_token"}
    mock_post.return_value = MockResponse()
    
    # 3. Mock the JWT verification result
    mock_verify.return_value = {
        "sub": "google_123456789",
        "email": "newgoogleuser@example.com",
        "email_verified": True,
        "nonce": nonce
    }
    
    # 4. Call the callback endpoint
    response = client.get(f"/auth/google/callback?code=mockcode&state={state_token}", follow_redirects=False)
    
    # The callback redirects back to the frontend
    assert response.status_code in (302, 307)
    
    # 5. Verify the cookie was set
    assert "refresh_token" in response.cookies


# ═══════════════════════════════════════════════════
# Concurrency / Race Condition Tests (AUTH-002)
# ═══════════════════════════════════════════════════

def test_concurrent_refresh_requests(client, session):
    """
    If multiple requests try to rotate the exact same refresh token concurrently,
    only ONE should succeed. The others should fail with 401.
    This proves that the rotation is atomic and replay logic doesn't falsely
    trigger due to a race condition.
    """
    login_res = create_and_login(client, session)
    old_cookie = login_res.cookies.get("refresh_token")
    
    # We will fire 5 concurrent requests all using the same old cookie
    def make_request():
        # Each thread gets its own cookies so they don't interfere
        client.cookies.clear()
        client.cookies.set("refresh_token", old_cookie)
        return client.post("/auth/refresh")

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(make_request) for _ in range(5)]
        results = [f.result() for f in concurrent.futures.as_completed(futures)]
    
    # Check outcomes
    status_codes = [res.status_code for res in results]
    
    # Exactly one request should succeed
    assert status_codes.count(200) == 1
    # Exactly four requests should fail with 401
    assert status_codes.count(401) == 4
    
    # The family should NOT be completely revoked (which a false replay would do).
    # The single successful request should have returned a valid new token.
    successful_res = next(res for res in results if res.status_code == 200)
    new_cookie = successful_res.cookies.get("refresh_token")
    
    client.cookies.set("refresh_token", new_cookie)
    verify_res = client.post("/auth/refresh")
    assert verify_res.status_code == 200


# ═══════════════════════════════════════════════════
# Session Cap (Max 10) Eviction
# ═══════════════════════════════════════════════════

@patch("app.routers.users.check_and_consume", return_value=RateLimitResult(allowed=True, limit=999, remaining=999, reset_seconds=1))
def test_session_cap_eviction(mock_rl, client, session):
    """
    If a user logs in 11 times, the session cap (10) should trigger.
    The oldest session (or one of the same-second sessions) should be silently evicted.
    Exactly 10 sessions should remain valid, and 1 should fail.
    """
    client.post("/users/sign-up", json={
        "username": "sessioncap",
        "email": "cap@example.com",
        "password": "SecurePass1!",
    })
    user = session.query(models.User).filter(
        models.User.email == "cap@example.com"
    ).first()
    user.is_verified = True
    session.commit()

    # Log in 11 times and store their cookies
    cookies_list = []
    for _ in range(11):
        res = client.post("/users/sign-in", data={
            "username": "cap@example.com",
            "password": "SecurePass1!",
        })
        cookies_list.append(res.cookies.get("refresh_token"))

    # Check how many are still valid
    valid_count = 0
    invalid_count = 0
    for cookie in cookies_list:
        client.cookies.clear()
        if cookie:
            client.cookies.set("refresh_token", cookie)
        res = client.post("/auth/refresh")
        if res.status_code == 200:
            valid_count += 1
        elif res.status_code == 401:
            invalid_count += 1

    assert valid_count == 10
    assert invalid_count == 1
