import pytest
from app import models


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


# -----------------
# SIGN-IN TESTS
# -----------------
def test_signin_success(client):
    client.post("/users/sign-up", json={
        "username": "bob",
        "email": "bob@example.com",
        "password": "MyPassword1!"
    })

    response = client.post("/users/sign-in", data={
        "username": "bob@example.com",
        "password": "MyPassword1!"
    })

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


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
