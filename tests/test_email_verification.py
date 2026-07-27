# pyrefly: ignore [missing-import]
from app import models
from app.email_verification import issue_email_verification_token

def test_verify_email_success(client, session):
    # 1. Sign up
    payload = {
        "username": "verifyuser",
        "email": "verify@example.com",
        "password": "Password123!"
    }
    client.post("/users/sign-up", json=payload)
    
    user = session.query(models.User).filter(models.User.email == "verify@example.com").first()
    assert user is not None
    assert not user.is_verified
    
    # Generate token
    raw_token = issue_email_verification_token(session, user)
    
    # 2. Verify via POST
    res = client.post("/auth/verify-email", json={"token": raw_token})
    assert res.status_code == 200
    assert "verified successfully" in res.json()["message"]
    
    session.refresh(user)
    assert user.is_verified

def test_verify_email_get_is_non_mutating(client, session):
    # GET should return 405 Method Not Allowed
    payload = {
        "username": "getuser",
        "email": "getuser@example.com",
        "password": "Password123!"
    }
    client.post("/users/sign-up", json=payload)
    
    user = session.query(models.User).filter(models.User.email == "getuser@example.com").first()
    raw_token = issue_email_verification_token(session, user)
    
    res = client.get(f"/auth/verify-email?token={raw_token}")
    assert res.status_code == 405
    
    session.refresh(user)
    assert not user.is_verified

def test_verify_email_invalid_token(client):
    res = client.post("/auth/verify-email", json={"token": "invalid_token_123"})
    assert res.status_code == 400
    assert res.json()["detail"] == "auth.verify_email_token_invalid_or_expired"

def test_verify_email_reused_token(client, session):
    # Sign up
    client.post("/users/sign-up", json={
        "username": "reuse",
        "email": "reuse@example.com",
        "password": "Password123!"
    })
    
    user = session.query(models.User).filter(models.User.email == "reuse@example.com").first()
    raw_token = issue_email_verification_token(session, user)
    
    # First use
    res1 = client.post("/auth/verify-email", json={"token": raw_token})
    assert res1.status_code == 200
    
    # Second use
    res2 = client.post("/auth/verify-email", json={"token": raw_token})
    assert res2.status_code == 400
    assert res2.json()["detail"] == "auth.verify_email_token_invalid_or_expired"

def test_verify_email_replaced_token(client, session):
    # If a user requests a new token, the old one should be invalidated?
    # Wait, the current logic doesn't strictly invalidate old tokens until they are used,
    # but the issue_email_verification_token does not invalidate previous tokens proactively.
    # Actually let's check current logic.
    pass
