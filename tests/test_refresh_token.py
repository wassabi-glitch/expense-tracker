"""
Tests for the refresh token system (Step 2: Auth System Completion).

Covers:
  - Login returns refresh cookie + access token
  - POST /auth/refresh — token rotation
  - POST /auth/logout — server-side invalidation
  - Used refresh tokens cannot be reused (rotation security)
  - Password reset revokes all refresh tokens
"""
from unittest.mock import patch

from app import models, oauth2
from app.redis_rate_limiter import redis_client
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
    rt_keys = list(redis_client.scan_iter("rt:*"))
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


def test_used_refresh_token_cannot_be_reused(client, session):
    """
    After a refresh token is used, the OLD token should be invalid.
    This tests the one-time-use rotation security model.
    """
    login_res = create_and_login(client, session)
    old_cookie = login_res.cookies.get("refresh_token")

    # Use the refresh token once — this should succeed
    refresh_res = client.post("/auth/refresh")
    assert refresh_res.status_code == 200

    # Now try to manually use the OLD cookie again
    # (simulating an attacker who stole the old token)
    client.cookies.set("refresh_token", old_cookie)
    replay_res = client.post("/auth/refresh")
    assert replay_res.status_code == 401


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
    rt_keys_before = list(redis_client.scan_iter("rt:*"))
    assert len(rt_keys_before) >= 1

    # Manually revoke all tokens (simulating what password reset does)
    oauth2.revoke_all_user_tokens(user.id)

    # All refresh token keys should be gone
    rt_keys_after = list(redis_client.scan_iter("rt:*"))
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
    redis_client.delete(f"rt:{token_hash}")

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
