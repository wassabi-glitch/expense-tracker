from tests.helpers import create_user_and_token


def _setup_premium_user_with_goal_wallet(client, headers, initial_balance=2_000_000):
    onboard = client.post(
        "/users/me/onboarding",
        json={
            "life_statuses": ["employed"],
            "wallets": [
                {
                    "name": "Savings",
                    "wallet_type": "SAVINGS",
                    "initial_balance": initial_balance,
                    "can_fund_goals": True,
                }
            ],
        },
        headers=headers,
    )
    assert onboard.status_code == 200
    premium = client.post("/users/me/toggle-premium", headers=headers)
    assert premium.status_code == 200
    wallets = client.get("/wallets", headers=headers)
    assert wallets.status_code == 200
    return wallets.json()[0]["id"]


def test_goal_funding_summary_counts_wallet_money_once(client):
    headers = create_user_and_token(
        client, "savingsuser1", "savingsuser1@example.com", "Password123!"
    )
    wallet_id = _setup_premium_user_with_goal_wallet(client, headers)

    created = client.post(
        "/goals/",
        json={"title": "Laptop", "target_amount": 1_000_000},
        headers=headers,
    )
    assert created.status_code == 201
    goal_id = created.json()["id"]

    allocated = client.post(
        f"/goals/{goal_id}/allocations",
        json={"wallet_id": wallet_id, "amount": 500_000},
        headers=headers,
    )
    assert allocated.status_code == 200

    summary = client.get("/goals/funding-summary", headers=headers)
    assert summary.status_code == 200
    payload = summary.json()
    assert payload["total_wallet_balance"] == 2_000_000
    assert payload["allocated_to_goals"] == 500_000
    assert payload["available_for_goals"] == 1_500_000
    assert payload["over_allocated_amount"] == 0
    assert payload["wallets"][0]["balance"] == 2_000_000
    assert payload["wallets"][0]["allocated_to_goals"] == 500_000


def test_old_virtual_savings_transfers_are_removed(client):
    headers = create_user_and_token(
        client, "savingsuser2", "savingsuser2@example.com", "Password123!"
    )
    _setup_premium_user_with_goal_wallet(client, headers)

    deposit = client.post("/savings/deposit", json={"amount": 100_000}, headers=headers)
    withdraw = client.post("/savings/withdraw", json={"amount": 100_000}, headers=headers)

    assert deposit.status_code == 410
    assert deposit.json()["detail"] == "savings.virtual_savings_removed"
    assert withdraw.status_code == 410
    assert withdraw.json()["detail"] == "savings.virtual_savings_removed"


def test_savings_summary_alias_uses_goal_funding_summary(client):
    headers = create_user_and_token(
        client, "savingsuser3", "savingsuser3@example.com", "Password123!"
    )
    _setup_premium_user_with_goal_wallet(client, headers, initial_balance=700_000)

    summary = client.get("/savings/summary", headers=headers)
    assert summary.status_code == 200
    assert summary.json()["total_wallet_balance"] == 700_000
    assert summary.json()["allocated_to_goals"] == 0


def test_savings_routes_require_premium(client):
    headers = create_user_and_token(
        client, "savingsuser4", "savingsuser4@example.com", "Password123!"
    )

    summary = client.get("/savings/summary", headers=headers)
    assert summary.status_code == 403
    assert summary.json()["detail"] == "users.premium_required"
