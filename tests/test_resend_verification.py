from unittest.mock import patch
from app import models
from app.redis_rate_limiter import redis_client

def test_resend_verification_success_dispatch(client, session):
    client.post("/users/sign-up", json={
        "username": "resenduser",
        "email": "resend@example.com",
        "password": "Password123!"
    })

    # Clear rate limit keys
    for key in redis_client.scan_iter("rl:resend_verification:*"):
        redis_client.delete(key)

    # Trigger resend
    res = client.post("/auth/resend-verification", json={"email": "resend@example.com"})
    assert res.status_code == 200
    assert "If the account exists" in res.json()["message"]

def test_resend_verification_enumeration_resistance(client):
    # Non-existent user
    res = client.post("/auth/resend-verification", json={"email": "nobody@example.com"})
    assert res.status_code == 200
    assert "If the account exists" in res.json()["message"]

def test_resend_verification_already_verified(client, session):
    client.post("/users/sign-up", json={
        "username": "verified",
        "email": "verified@example.com",
        "password": "Password123!"
    })
    
    user = session.query(models.User).filter(models.User.email == "verified@example.com").first()
    user.is_verified = True
    session.commit()

    res = client.post("/auth/resend-verification", json={"email": "verified@example.com"})
    assert res.status_code == 200
    assert "If the account exists" in res.json()["message"]

def test_resend_verification_rate_limiting(client):
    for key in redis_client.scan_iter("rl:resend_verification:*"):
        redis_client.delete(key)

    email = "ratelimit@example.com"
    for _ in range(3):
        res = client.post("/auth/resend-verification", json={"email": email})
        assert res.status_code == 200

    blocked = None
    for _ in range(5):
        res = client.post("/auth/resend-verification", json={"email": email})
        if res.status_code == 429:
            blocked = res
            break
            
    assert blocked is not None
    assert blocked.status_code == 429
    assert "Retry-After" in blocked.headers

def test_resend_verification_provider_failure(client, session):
    client.post("/users/sign-up", json={
        "username": "failuser",
        "email": "fail@example.com",
        "password": "Password123!"
    })
    
    with patch("app.routers.auth.send_verification_email", return_value=False):
        res = client.post("/auth/resend-verification", json={"email": "fail@example.com"})
        assert res.status_code == 200
        # It still returns 200 to resist enumeration, but logs the failure internally
        assert "If the account exists" in res.json()["message"]

def test_resend_verification_token_replacement(client, session):
    client.post("/users/sign-up", json={
        "username": "replace",
        "email": "replace@example.com",
        "password": "Password123!"
    })
    
    user = session.query(models.User).filter(models.User.email == "replace@example.com").first()
    
    # Check tokens created by sign-up
    tokens_before = session.query(models.EmailVerificationToken).filter(
        models.EmailVerificationToken.user_id == user.id,
        models.EmailVerificationToken.used_at.is_(None)
    ).count()
    
    assert tokens_before == 1
    
    # Resend
    client.post("/auth/resend-verification", json={"email": "replace@example.com"})
    
    # Old token should be marked used_at, new token should be unused
    unused_tokens = session.query(models.EmailVerificationToken).filter(
        models.EmailVerificationToken.user_id == user.id,
        models.EmailVerificationToken.used_at.is_(None)
    ).count()
    
    used_tokens = session.query(models.EmailVerificationToken).filter(
        models.EmailVerificationToken.user_id == user.id,
        models.EmailVerificationToken.used_at.is_not(None)
    ).count()
    
    assert unused_tokens == 1
    assert used_tokens >= 1
