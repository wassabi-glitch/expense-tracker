from app import models
from app.redis_rate_limiter import redis_client
from tests.helpers import create_user_and_token


def _setup_premium_user_with_balance(client, headers, initial_balance=2_000_000):
    onboard = client.post(
        "/users/me/onboarding",
        json={
            "life_status": "employed",
            "initial_balance": initial_balance,
        },
        headers=headers,
    )
    assert onboard.status_code == 200
    premium = client.post("/users/me/toggle-premium", headers=headers)
    assert premium.status_code == 200
    assert premium.json()["is_premium"] is True


def test_create_goal_and_list_with_zero_progress(client):
    headers = create_user_and_token(
        client, "goaluser1", "goaluser1@example.com", "Password123!"
    )
    _setup_premium_user_with_balance(client, headers)

    created = client.post(
        "/goals/",
        json={
            "title": "Laptop",
            "target_amount": 5_000_000,
            "target_date": "2026-12-31",
        },
        headers=headers,
    )
    assert created.status_code == 201
    payload = created.json()
    assert payload["title"] == "Laptop"
    assert payload["funded_amount"] == 0
    assert payload["remaining_amount"] == 5_000_000
    assert payload["progress_percent"] == 0
    assert payload["status"] == "ACTIVE"

    listed = client.get("/goals/", headers=headers)
    assert listed.status_code == 200
    assert len(listed.json()) == 1
    assert listed.json()[0]["title"] == "Laptop"


def test_goal_contribution_uses_free_savings_and_updates_status(client):
    headers = create_user_and_token(
        client, "goaluser2", "goaluser2@example.com", "Password123!"
    )
    _setup_premium_user_with_balance(client, headers)
    deposit = client.post("/savings/deposit", json={"amount": 900_000}, headers=headers)
    assert deposit.status_code == 201

    created = client.post(
        "/goals/",
        json={"title": "Phone", "target_amount": 800_000},
        headers=headers,
    )
    assert created.status_code == 201
    goal_id = created.json()["id"]

    contributed = client.post(
        f"/goals/{goal_id}/contribute",
        json={"amount": 800_000},
        headers=headers,
    )
    assert contributed.status_code == 200
    payload = contributed.json()
    assert payload["funded_amount"] == 800_000
    assert payload["remaining_amount"] == 0
    assert payload["status"] == "COMPLETED"

    summary = client.get("/savings/summary", headers=headers)
    assert summary.status_code == 200
    assert summary.json() == {
        "total_balance": 2_000_000,
        "free_savings_balance": 100_000,
        "locked_in_goals": 800_000,
        "spendable_balance": 1_100_000,
    }


def test_goal_contribution_rejects_when_free_savings_insufficient(client):
    headers = create_user_and_token(
        client, "goaluser3", "goaluser3@example.com", "Password123!"
    )
    _setup_premium_user_with_balance(client, headers)
    deposit = client.post("/savings/deposit", json={"amount": 200_000}, headers=headers)
    assert deposit.status_code == 201

    created = client.post(
        "/goals/",
        json={"title": "Trip", "target_amount": 1_500_000},
        headers=headers,
    )
    assert created.status_code == 201
    goal_id = created.json()["id"]

    blocked = client.post(
        f"/goals/{goal_id}/contribute",
        json={"amount": 300_000},
        headers=headers,
    )
    assert blocked.status_code == 400
    assert blocked.json()["detail"] == "goals.insufficient_free_savings_balance"


def test_goal_return_reduces_locked_amount_and_reopens_goal(client):
    headers = create_user_and_token(
        client, "goaluser4", "goaluser4@example.com", "Password123!"
    )
    _setup_premium_user_with_balance(client, headers)
    assert client.post("/savings/deposit", json={"amount": 1_000_000}, headers=headers).status_code == 201

    created = client.post(
        "/goals/",
        json={"title": "Emergency fund", "target_amount": 900_000},
        headers=headers,
    )
    assert created.status_code == 201
    goal_id = created.json()["id"]
    assert client.post(f"/goals/{goal_id}/contribute", json={"amount": 900_000}, headers=headers).status_code == 200

    returned = client.post(
        f"/goals/{goal_id}/return",
        json={"amount": 300_000},
        headers=headers,
    )
    assert returned.status_code == 200
    payload = returned.json()
    assert payload["funded_amount"] == 600_000
    assert payload["remaining_amount"] == 300_000
    assert payload["status"] == "ACTIVE"

    summary = client.get("/savings/summary", headers=headers)
    assert summary.status_code == 200
    assert summary.json() == {
        "total_balance": 2_000_000,
        "free_savings_balance": 400_000,
        "locked_in_goals": 600_000,
        "spendable_balance": 1_000_000,
    }


def test_goal_return_rejects_when_goal_balance_insufficient(client):
    headers = create_user_and_token(
        client, "goaluser5", "goaluser5@example.com", "Password123!"
    )
    _setup_premium_user_with_balance(client, headers)
    assert client.post("/savings/deposit", json={"amount": 500_000}, headers=headers).status_code == 201

    created = client.post(
        "/goals/",
        json={"title": "Camera", "target_amount": 1_000_000},
        headers=headers,
    )
    assert created.status_code == 201
    goal_id = created.json()["id"]
    assert client.post(f"/goals/{goal_id}/contribute", json={"amount": 200_000}, headers=headers).status_code == 200

    blocked = client.post(
        f"/goals/{goal_id}/return",
        json={"amount": 300_000},
        headers=headers,
    )
    assert blocked.status_code == 400
    assert blocked.json()["detail"] == "goals.insufficient_goal_balance"


def test_goals_routes_require_premium(client):
    headers = create_user_and_token(
        client, "goaluser6", "goaluser6@example.com", "Password123!"
    )

    listed = client.get("/goals/", headers=headers)
    assert listed.status_code == 403
    assert listed.json()["detail"] == "users.premium_required"

    created = client.post(
        "/goals/",
        json={"title": "Bike", "target_amount": 1_000_000},
        headers=headers,
    )
    assert created.status_code == 403
    assert created.json()["detail"] == "users.premium_required"


def test_update_goal_allows_title_target_and_date_changes(client):
    headers = create_user_and_token(
        client, "goaluser7", "goaluser7@example.com", "Password123!"
    )
    _setup_premium_user_with_balance(client, headers)

    created = client.post(
        "/goals/",
        json={"title": "Bike", "target_amount": 1_000_000, "target_date": "2026-06-01"},
        headers=headers,
    )
    goal_id = created.json()["id"]

    updated = client.patch(
        f"/goals/{goal_id}",
        json={"title": "Road bike", "target_amount": 1_200_000, "target_date": "2026-07-01"},
        headers=headers,
    )
    assert updated.status_code == 200
    payload = updated.json()
    assert payload["title"] == "Road bike"
    assert payload["target_amount"] == 1_200_000
    assert payload["target_date"] == "2026-07-01"


def test_update_goal_rejects_target_below_funded_amount(client):
    headers = create_user_and_token(
        client, "goaluser8", "goaluser8@example.com", "Password123!"
    )
    _setup_premium_user_with_balance(client, headers)
    assert client.post("/savings/deposit", json={"amount": 500_000}, headers=headers).status_code == 201
    created = client.post(
        "/goals/",
        json={"title": "Console", "target_amount": 700_000},
        headers=headers,
    )
    goal_id = created.json()["id"]
    assert client.post(f"/goals/{goal_id}/contribute", json={"amount": 300_000}, headers=headers).status_code == 200

    updated = client.patch(
        f"/goals/{goal_id}",
        json={"target_amount": 200_000},
        headers=headers,
    )
    assert updated.status_code == 400
    assert updated.json()["detail"] == "goals.target_below_funded_amount"


def test_archive_restore_and_delete_goal_flow(client):
    headers = create_user_and_token(
        client, "goaluser9", "goaluser9@example.com", "Password123!"
    )
    _setup_premium_user_with_balance(client, headers)

    created = client.post(
        "/goals/",
        json={"title": "Desk", "target_amount": 400_000},
        headers=headers,
    )
    goal_id = created.json()["id"]

    archived = client.post(f"/goals/{goal_id}/archive", headers=headers)
    assert archived.status_code == 200
    assert archived.json()["status"] == "ARCHIVED"

    restored = client.post(f"/goals/{goal_id}/restore", headers=headers)
    assert restored.status_code == 200
    assert restored.json()["status"] == "ACTIVE"

    assert client.post(f"/goals/{goal_id}/archive", headers=headers).status_code == 200
    deleted = client.delete(f"/goals/{goal_id}", headers=headers)
    assert deleted.status_code == 204
    listed = client.get("/goals/", headers=headers)
    assert listed.status_code == 200
    assert listed.json() == []


def test_archive_releases_locked_funds_back_to_free_savings(client):
    headers = create_user_and_token(
        client, "goaluser10", "goaluser10@example.com", "Password123!"
    )
    _setup_premium_user_with_balance(client, headers)
    assert client.post("/savings/deposit", json={"amount": 500_000}, headers=headers).status_code == 201
    created = client.post(
        "/goals/",
        json={"title": "Desk lamp", "target_amount": 300_000},
        headers=headers,
    )
    goal_id = created.json()["id"]
    assert client.post(f"/goals/{goal_id}/contribute", json={"amount": 100_000}, headers=headers).status_code == 200

    archived = client.post(f"/goals/{goal_id}/archive", headers=headers)
    assert archived.status_code == 200
    payload = archived.json()
    assert payload["status"] == "ARCHIVED"
    assert payload["funded_amount"] == 0
    assert payload["remaining_amount"] == 300_000

    summary = client.get("/savings/summary", headers=headers)
    assert summary.status_code == 200
    assert summary.json() == {
        "total_balance": 2_000_000,
        "free_savings_balance": 500_000,
        "locked_in_goals": 0,
        "spendable_balance": 1_500_000,
    }


def test_delete_requires_archived_status(client):
    headers = create_user_and_token(
        client, "goaluser11", "goaluser11@example.com", "Password123!"
    )
    _setup_premium_user_with_balance(client, headers)
    created = client.post(
        "/goals/",
        json={"title": "Monitor", "target_amount": 300_000},
        headers=headers,
    )
    goal_id = created.json()["id"]
    deleted = client.delete(f"/goals/{goal_id}", headers=headers)
    assert deleted.status_code == 400
    assert deleted.json()["detail"] == "goals.delete_requires_archived"


def test_create_goal_rejects_when_active_limit_is_reached(client, session):
    headers = create_user_and_token(
        client, "goaluser12", "goaluser12@example.com", "Password123!"
    )
    _setup_premium_user_with_balance(client, headers)
    user = session.query(models.User).filter(models.User.email == "goaluser12@example.com").first()
    assert user is not None

    for i in range(20):
        session.add(
            models.Goals(
                owner_id=user.id,
                title=f"Goal {i:02d}",
                target_amount=100_000 + i,
                status=models.GoalStatus.ACTIVE,
            )
        )
    session.commit()

    blocked = client.post(
        "/goals/",
        json={"title": "Overflow goal", "target_amount": 999_999},
        headers=headers,
    )
    assert blocked.status_code == 400
    assert blocked.json()["detail"] == "goals.active_limit_reached"


def test_archive_rejects_when_archived_limit_is_reached(client, session):
    headers = create_user_and_token(
        client, "goaluser13", "goaluser13@example.com", "Password123!"
    )
    _setup_premium_user_with_balance(client, headers)
    user = session.query(models.User).filter(models.User.email == "goaluser13@example.com").first()
    assert user is not None

    for i in range(100):
        session.add(
            models.Goals(
                owner_id=user.id,
                title=f"Archive {i:02d}",
                target_amount=100_000 + i,
                status=models.GoalStatus.ARCHIVED,
            )
        )
    session.commit()

    created = client.post(
        "/goals/",
        json={"title": "Archive overflow", "target_amount": 250_000},
        headers=headers,
    )
    assert created.status_code == 201

    blocked = client.post(f"/goals/{created.json()['id']}/archive", headers=headers)
    assert blocked.status_code == 400
    assert blocked.json()["detail"] == "goals.archived_limit_reached"


def test_restore_rejects_when_active_limit_is_reached(client, session):
    headers = create_user_and_token(
        client, "goaluser14", "goaluser14@example.com", "Password123!"
    )
    _setup_premium_user_with_balance(client, headers)
    user = session.query(models.User).filter(models.User.email == "goaluser14@example.com").first()
    assert user is not None

    archived_goal = client.post(
        "/goals/",
        json={"title": "Archived source", "target_amount": 400_000},
        headers=headers,
    )
    archived_goal_id = archived_goal.json()["id"]
    archived = client.post(f"/goals/{archived_goal_id}/archive", headers=headers)
    assert archived.status_code == 200

    for i in range(20):
        session.add(
            models.Goals(
                owner_id=user.id,
                title=f"Active {i:02d}",
                target_amount=200_000 + i,
                status=models.GoalStatus.ACTIVE,
            )
        )
    session.commit()

    blocked = client.post(f"/goals/{archived_goal_id}/restore", headers=headers)
    assert blocked.status_code == 400
    assert blocked.json()["detail"] == "goals.active_limit_reached"


def test_goal_write_rate_limit_blocks_excess_requests(client):
    for key in redis_client.scan_iter("tb:goals_lifecycle_write:*"):
        redis_client.delete(key)

    headers = create_user_and_token(
        client, "goaluser15", "goaluser15@example.com", "Password123!"
    )
    _setup_premium_user_with_balance(client, headers)

    blocked = None
    for i in range(20):
        res = client.post(
            "/goals/",
            json={"title": f"Speed {i:02d}", "target_amount": 150_000 + i},
            headers=headers,
        )
        if res.status_code == 429:
            blocked = res
            break

    assert blocked is not None
    assert blocked.status_code == 429
    assert "Retry-After" in blocked.headers
    assert blocked.json()["detail"] == "goals.write_rate_limited"
