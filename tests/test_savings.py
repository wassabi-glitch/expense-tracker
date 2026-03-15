from app import models
from app.redis_rate_limiter import redis_client
from tests.helpers import create_user_and_token


def test_savings_deposit_creates_transaction_and_updates_summary(client):
    email = "savingsuser1@example.com"
    headers = create_user_and_token(
        client, "savingsuser1", email, "Password123!"
    )

    onboard = client.post(
        "/users/me/onboarding",
        json={
            "life_status": "employed",
            "initial_balance": 2_000_000,
        },
        headers=headers,
    )
    assert onboard.status_code == 200
    # Test DB fixture in conftest is separate from the request helper, so use the premium toggle endpoint.
    premium = client.post("/users/me/toggle-premium", headers=headers)
    assert premium.status_code == 200
    assert premium.json()["is_premium"] is True

    created = client.post("/savings/deposit", json={"amount": 500_000}, headers=headers)
    assert created.status_code == 201
    payload = created.json()
    assert payload["amount"] == 500_000
    assert payload["transaction_type"] == "DEPOSIT"

    summary = client.get("/savings/summary", headers=headers)
    assert summary.status_code == 200
    assert summary.json() == {
        "total_balance": 2_000_000,
        "free_savings_balance": 500_000,
        "locked_in_goals": 0,
        "spendable_balance": 1_500_000,
    }


def test_savings_deposit_rejects_when_amount_exceeds_spendable_balance(client):
    email = "savingsuser2@example.com"
    headers = create_user_and_token(
        client, "savingsuser2", email, "Password123!"
    )

    onboard = client.post(
        "/users/me/onboarding",
        json={
            "life_status": "student",
            "initial_balance": 300_000,
        },
        headers=headers,
    )
    assert onboard.status_code == 200
    premium = client.post("/users/me/toggle-premium", headers=headers)
    assert premium.status_code == 200

    blocked = client.post("/savings/deposit", json={"amount": 500_000}, headers=headers)
    assert blocked.status_code == 400
    assert blocked.json()["detail"] == "savings.insufficient_spendable_balance"


def test_savings_summary_counts_locked_goal_money_separately(client, session):
    email = "savingsuser3@example.com"
    headers = create_user_and_token(
        client, "savingsuser3", email, "Password123!"
    )
    user = session.query(models.User).filter(models.User.email == email).first()
    assert user is not None
    user.is_premium = True

    session.add(
        models.UserProfile(
            user_id=user.id,
            life_status=models.LifeStatus.EMPLOYED,
            monthly_income_amount=0,
            initial_balance=2_000_000,
        )
    )
    session.flush()

    session.add(
        models.SavingsTransactions(
            owner_id=user.id,
            amount=700_000,
            transaction_type=models.SavingsTransactionType.DEPOSIT,
        )
    )
    session.flush()

    goal = models.Goals(
        owner_id=user.id,
        title="Laptop",
        target_amount=1_500_000,
        status=models.GoalStatus.ACTIVE,
    )
    session.add(goal)
    session.flush()

    session.add(
        models.GoalContributions(
            owner_id=user.id,
            goal_id=goal.id,
            amount=200_000,
            contribution_type=models.GoalContributionType.ALLOCATE,
        )
    )
    session.commit()

    summary = client.get("/savings/summary", headers=headers)
    assert summary.status_code == 200
    assert summary.json() == {
        "total_balance": 2_000_000,
        "free_savings_balance": 500_000,
        "locked_in_goals": 200_000,
        "spendable_balance": 1_300_000,
    }


def test_savings_withdraw_creates_transaction_and_updates_summary(client):
    email = "savingsuser4@example.com"
    headers = create_user_and_token(
        client, "savingsuser4", email, "Password123!"
    )

    onboard = client.post(
        "/users/me/onboarding",
        json={
            "life_status": "employed",
            "initial_balance": 2_000_000,
        },
        headers=headers,
    )
    assert onboard.status_code == 200
    premium = client.post("/users/me/toggle-premium", headers=headers)
    assert premium.status_code == 200

    deposited = client.post("/savings/deposit", json={"amount": 800_000}, headers=headers)
    assert deposited.status_code == 201

    withdrawn = client.post("/savings/withdraw", json={"amount": 300_000}, headers=headers)
    assert withdrawn.status_code == 201
    payload = withdrawn.json()
    assert payload["amount"] == 300_000
    assert payload["transaction_type"] == "WITHDRAWAL"

    summary = client.get("/savings/summary", headers=headers)
    assert summary.status_code == 200
    assert summary.json() == {
        "total_balance": 2_000_000,
        "free_savings_balance": 500_000,
        "locked_in_goals": 0,
        "spendable_balance": 1_500_000,
    }


def test_savings_withdraw_rejects_when_amount_exceeds_free_savings_balance(client):
    email = "savingsuser5@example.com"
    headers = create_user_and_token(
        client, "savingsuser5", email, "Password123!"
    )

    onboard = client.post(
        "/users/me/onboarding",
        json={
            "life_status": "student",
            "initial_balance": 1_000_000,
        },
        headers=headers,
    )
    assert onboard.status_code == 200
    premium = client.post("/users/me/toggle-premium", headers=headers)
    assert premium.status_code == 200

    deposited = client.post("/savings/deposit", json={"amount": 200_000}, headers=headers)
    assert deposited.status_code == 201

    blocked = client.post("/savings/withdraw", json={"amount": 300_000}, headers=headers)
    assert blocked.status_code == 400
    assert blocked.json()["detail"] == "savings.insufficient_free_savings_balance"


def test_savings_routes_require_premium(client):
    headers = create_user_and_token(
        client, "savingsuser6", "savingsuser6@example.com", "Password123!"
    )

    summary = client.get("/savings/summary", headers=headers)
    assert summary.status_code == 403
    assert summary.json()["detail"] == "users.premium_required"

    deposit = client.post("/savings/deposit", json={"amount": 100_000}, headers=headers)
    assert deposit.status_code == 403
    assert deposit.json()["detail"] == "users.premium_required"

    withdraw = client.post("/savings/withdraw", json={"amount": 100_000}, headers=headers)
    assert withdraw.status_code == 403
    assert withdraw.json()["detail"] == "users.premium_required"


def test_savings_write_rate_limit_blocks_excess_requests(client):
    for key in redis_client.scan_iter("tb:savings_write:*"):
        redis_client.delete(key)

    headers = create_user_and_token(
        client, "savingsuser7", "savingsuser7@example.com", "Password123!"
    )
    onboard = client.post(
        "/users/me/onboarding",
        json={"life_status": "employed", "initial_balance": 2_000_000},
        headers=headers,
    )
    assert onboard.status_code == 200
    premium = client.post("/users/me/toggle-premium", headers=headers)
    assert premium.status_code == 200

    blocked = None
    for _ in range(20):
        res = client.post("/savings/deposit", json={"amount": 1}, headers=headers)
        if res.status_code == 429:
            blocked = res
            break

    assert blocked is not None
    assert blocked.status_code == 429
    assert "Retry-After" in blocked.headers
    assert blocked.json()["detail"] == "savings.write_rate_limited"
