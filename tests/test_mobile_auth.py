import pytest
from tests.helpers import TEST_TIMEZONE
from app.main import app
from app.session import get_db
from app import models

@pytest.fixture
def test_user(client):
    email = "mobile_test@example.com"
    password = "MobilePassword123!"
    
    client.post("/users/sign-up", json={
        "username": "mobile_test",
        "email": email,
        "password": password,
    }, headers={"X-Timezone": TEST_TIMEZONE})

    override_db_factory = app.dependency_overrides.get(get_db)
    if override_db_factory is not None:
        db_gen = override_db_factory()
        db = next(db_gen)
        try:
            user = db.query(models.User).filter(models.User.email == email).first()
            if user:
                user.is_verified = True
                db.commit()
        finally:
            db.close()
            try:
                next(db_gen)
            except StopIteration:
                pass
                
    return {"email": email, "password": password}


def test_mobile_sign_in_success(client, test_user):
    payload = {
        "email": test_user["email"],
        "password": test_user["password"]
    }
    response = client.post("/auth/mobile/sign-in", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"

def test_mobile_sign_in_invalid_credentials(client, test_user):
    payload = {
        "email": test_user["email"],
        "password": "wrongpassword"
    }
    response = client.post("/auth/mobile/sign-in", json=payload)
    assert response.status_code == 403
    assert response.json()["detail"] == "auth.invalid_credentials"

def test_mobile_refresh_token_success(client, test_user):
    # 1. Sign in
    payload = {
        "email": test_user["email"],
        "password": test_user["password"]
    }
    sign_in_res = client.post("/auth/mobile/sign-in", json=payload)
    assert sign_in_res.status_code == 200
    refresh_token = sign_in_res.json()["refresh_token"]

    # 2. Refresh
    refresh_res = client.post("/auth/mobile/refresh", json={"refresh_token": refresh_token})
    assert refresh_res.status_code == 200
    data = refresh_res.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["refresh_token"] != refresh_token

def test_mobile_logout(client, test_user):
    # 1. Sign in
    payload = {
        "email": test_user["email"],
        "password": test_user["password"]
    }
    sign_in_res = client.post("/auth/mobile/sign-in", json=payload)
    refresh_token = sign_in_res.json()["refresh_token"]

    # 2. Logout
    logout_res = client.post("/auth/mobile/logout", json={"refresh_token": refresh_token})
    assert logout_res.status_code == 200

    # 3. Try to refresh
    refresh_res = client.post("/auth/mobile/refresh", json={"refresh_token": refresh_token})
    assert refresh_res.status_code == 401
    assert refresh_res.json()["detail"] == "auth.refresh_token_invalid"
