from app import models
from tests.helpers import create_user_and_token


def test_me_requires_onboarding_until_profile_completed(client):
    headers = create_user_and_token(
        client,
        "onboarduser1",
        "onboarduser1@example.com",
        "Password123!",
    )

    me_before = client.get("/users/me", headers=headers)
    assert me_before.status_code == 200
    assert me_before.json()["needs_onboarding"] is True
    assert me_before.json()["profile"] is None

    onboard_res = client.post(
        "/users/me/onboarding",
        json={
            "life_status": "employed",
            "initial_balance": 5000000,
        },
        headers=headers,
    )
    assert onboard_res.status_code == 200
    onboard_data = onboard_res.json()
    assert onboard_data["needs_onboarding"] is False
    assert onboard_data["profile"]["life_status"] == "employed"
    assert onboard_data["profile"]["initial_balance"] == 5000000
    assert onboard_data["profile"]["monthly_income_amount"] == 0
    assert onboard_data["profile"]["onboarding_completed_at"] is not None

    me_after = client.get("/users/me", headers=headers)
    assert me_after.status_code == 200
    assert me_after.json()["needs_onboarding"] is False
    assert me_after.json()["profile"]["life_status"] == "employed"


def test_onboarding_upsert_updates_existing_profile(client, session):
    headers = create_user_and_token(
        client,
        "onboarduser2",
        "onboarduser2@example.com",
        "Password123!",
    )

    first = client.post(
        "/users/me/onboarding",
        json={
            "life_status": "student",
            "initial_balance": 100000,
        },
        headers=headers,
    )
    assert first.status_code == 200

    second = client.post(
        "/users/me/onboarding",
        json={
            "life_status": "self_employed",
            "initial_balance": 200000,
        },
        headers=headers,
    )
    assert second.status_code == 200
    second_data = second.json()
    assert second_data["profile"]["life_status"] == "self_employed"
    assert second_data["profile"]["initial_balance"] == 200000

    profiles = session.query(models.UserProfile).all()
    assert len(profiles) == 1
    entries = session.query(models.IncomeEntry).all()
    assert len(entries) == 0


def test_onboarding_creates_status_based_income_sources_without_entries(client):
    headers = create_user_and_token(
        client,
        "onboarduser4",
        "onboarduser4@example.com",
        "Password123!",
    )

    onboard = client.post(
        "/users/me/onboarding",
        json={
            "life_status": "student",
            "initial_balance": 2500000,
        },
        headers=headers,
    )
    assert onboard.status_code == 200

    sources = client.get("/income/sources?include_inactive=true", headers=headers)
    assert sources.status_code == 200
    sources_data = sources.json()
    source_names = {s["name"] for s in sources_data}
    assert {"Allowance", "Scholarship", "Part-time work"}.issubset(source_names)

    entries = client.get("/income/entries", headers=headers)
    assert entries.status_code == 200
    entries_data = entries.json()
    assert entries_data["total"] == 0


def test_onboarding_rejects_too_large_initial_balance(client):
    headers = create_user_and_token(
        client,
        "onboarduser3",
        "onboarduser3@example.com",
        "Password123!",
    )

    res = client.post(
        "/users/me/onboarding",
        json={
            "life_status": "business_owner",
            "initial_balance": 1_000_000_000_000,
        },
        headers=headers,
    )

    assert res.status_code == 422
