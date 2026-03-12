from datetime import date

from app import models
from app.redis_rate_limiter import redis_client
from tests.helpers import create_user_and_token, create_budget


def _make_user_premium(session, email: str):
    user = session.query(models.User).filter(models.User.email == email).first()
    assert user is not None
    user.is_premium = True
    session.commit()


def _set_rollover_enabled(session, email: str, enabled: bool):
    user = session.query(models.User).filter(models.User.email == email).first()
    assert user is not None
    assert user.profile is not None
    user.profile.budget_rollover_enabled = enabled
    session.commit()


def test_create_budget_success(client):
    headers = create_user_and_token(
        client, "budgetuser", "budgetuser@example.com", "Password123!"
    )
    res = create_budget(client, headers, category="Food", monthly_limit=500)
    assert res.status_code == 201
    data = res.json()
    assert data["category"] == "Groceries"
    assert data["monthly_limit"] == 500
    assert "spent" in data
    assert "budget_year" in data
    assert "budget_month" in data


def test_create_budget_duplicate(client):
    headers = create_user_and_token(
        client, "dupbudget", "dupbudget@example.com", "Password123!"
    )
    res1 = create_budget(client, headers, category="Food", monthly_limit=300)
    assert res1.status_code == 201
    res2 = create_budget(client, headers, category="Food", monthly_limit=300)
    assert res2.status_code == 409


def test_get_budgets_list(client):
    headers = create_user_and_token(
        client, "listbudget", "listbudget@example.com", "Password123!"
    )
    today = date.today()
    create_budget(client, headers, category="Food", monthly_limit=300, budget_year=today.year, budget_month=today.month)
    create_budget(client, headers, category="Transport", monthly_limit=200, budget_year=today.year, budget_month=today.month)
    
    client.post(
        "/expenses/",
        json={
            "title": "Burger",
            "amount": 50,
            "category": "Groceries",
            "date": today.isoformat(),
        },
        headers=headers,
    )

    res = client.get("/budgets/", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 2
    
    food_budget = next(b for b in data if b["category"] == "Groceries")
    transport_budget = next(b for b in data if b["category"] == "Transport")
    
    assert food_budget["spent"] == 50
    assert transport_budget["spent"] == 0


def test_get_budgets_computes_premium_rollover(client, session):
    email = "rolloverbudget@example.com"
    headers = create_user_and_token(
        client, "rolloverbudget", email, "Password123!"
    )
    _make_user_premium(session, email)
    onboard = client.post(
        "/users/me/onboarding",
        json={"life_status": "employed", "initial_balance": 100000},
        headers=headers,
    )
    assert onboard.status_code == 200, onboard.text

    create_budget(client, headers, category="Food", monthly_limit=300, budget_year=2026, budget_month=1)
    create_budget(client, headers, category="Food", monthly_limit=300, budget_year=2026, budget_month=2)

    jan_expense = client.post(
        "/expenses/",
        json={
            "title": "Jan food",
            "amount": 200,
            "category": "Groceries",
            "date": "2026-01-10",
        },
        headers=headers,
    )
    assert jan_expense.status_code == 201, jan_expense.text

    res = client.get("/budgets/", headers=headers)
    assert res.status_code == 200
    data = res.json()

    jan = next(b for b in data if b["category"] == "Groceries" and b["budget_year"] == 2026 and b["budget_month"] == 1)
    feb = next(b for b in data if b["category"] == "Groceries" and b["budget_year"] == 2026 and b["budget_month"] == 2)

    assert jan["monthly_limit"] == 300
    assert jan["rollover_amount"] == 0
    assert jan["effective_monthly_limit"] == 300
    assert jan["spent"] == 200

    assert feb["monthly_limit"] == 300
    assert feb["rollover_amount"] == 100
    assert feb["effective_monthly_limit"] == 400


def test_get_budgets_disables_rollover_when_preference_off(client, session):
    email = "rolloveroff@example.com"
    headers = create_user_and_token(
        client, "rolloveroff", email, "Password123!"
    )
    _make_user_premium(session, email)

    onboard = client.post(
        "/users/me/onboarding",
        json={"life_status": "employed", "initial_balance": 100000},
        headers=headers,
    )
    assert onboard.status_code == 200, onboard.text

    _set_rollover_enabled(session, email, False)

    create_budget(client, headers, category="Food", monthly_limit=300, budget_year=2026, budget_month=1)
    create_budget(client, headers, category="Food", monthly_limit=300, budget_year=2026, budget_month=2)

    jan_expense = client.post(
        "/expenses/",
        json={
            "title": "Jan food",
            "amount": 200,
            "category": "Groceries",
            "date": "2026-01-10",
        },
        headers=headers,
    )
    assert jan_expense.status_code == 201, jan_expense.text

    res = client.get("/budgets/", headers=headers)
    assert res.status_code == 200
    data = res.json()

    jan = next(b for b in data if b["category"] == "Groceries" and b["budget_year"] == 2026 and b["budget_month"] == 1)
    feb = next(b for b in data if b["category"] == "Groceries" and b["budget_year"] == 2026 and b["budget_month"] == 2)

    assert jan["rollover_amount"] == 0
    assert jan["effective_monthly_limit"] == 300
    assert feb["rollover_amount"] == 0
    assert feb["effective_monthly_limit"] == 300


def test_get_budget_by_category(client):
    headers = create_user_and_token(
        client, "getbudget", "getbudget@example.com", "Password123!"
    )
    today = date.today()
    create_budget(client, headers, category="Food", monthly_limit=300, budget_year=today.year, budget_month=today.month)
    res = client.get(f"/budgets/{today.year}/{today.month}/Groceries", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["category"] == "Groceries"
    assert "spent" in data


def test_update_budget(client):
    headers = create_user_and_token(
        client, "updatebudget", "updatebudget@example.com", "Password123!"
    )
    today = date.today()
    create_budget(client, headers, category="Food", monthly_limit=300, budget_year=today.year, budget_month=today.month)
    res = client.patch(f"/budgets/{today.year}/{today.month}/Groceries", json={"monthly_limit": 800}, headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["monthly_limit"] == 800
    assert "spent" in data


def test_delete_budget(client):
    headers = create_user_and_token(
        client, "deletebudget", "deletebudget@example.com", "Password123!"
    )
    today = date.today()
    create_budget(client, headers, category="Food", monthly_limit=300, budget_year=today.year, budget_month=today.month)
    res = client.delete(f"/budgets/{today.year}/{today.month}/Groceries", headers=headers)
    assert res.status_code == 204
    res_list = client.get("/budgets/", headers=headers)
    assert res_list.status_code == 200
    assert res_list.json() == []


def test_delete_budget_blocks_when_linked_expenses_exist(client):
    headers = create_user_and_token(
        client, "deletebudgetlinked", "deletebudgetlinked@example.com", "Password123!"
    )
    today = date.today()
    create_budget(
        client,
        headers,
        category="Food",
        monthly_limit=300,
        budget_year=today.year,
        budget_month=today.month,
    )
    expense_res = client.post(
        "/expenses/",
        json={
            "title": "Linked expense",
            "amount": 10,
            "category": "Groceries",
            "description": "test",
            "date": today.isoformat(),
        },
        headers=headers,
    )
    assert expense_res.status_code == 201, expense_res.text

    res = client.delete(f"/budgets/{today.year}/{today.month}/Groceries", headers=headers)
    assert res.status_code == 409
    assert res.json()["detail"] == "budgets.has_linked_expenses"

    still_exists = client.get(f"/budgets/{today.year}/{today.month}/Groceries", headers=headers)
    assert still_exists.status_code == 200


def test_budget_write_rate_limit_blocks_burst(client):
    for key in redis_client.scan_iter("tb:budgets_write:*"):
        redis_client.delete(key)

    headers = create_user_and_token(
        client, "budgetrtlim", "budgetrtlim@example.com", "Password123!"
    )
    
    blocked = None
    # BUDGET_WRITE_BUCKET_CAPACITY is 10, so 15 requests should trigger it
    for i in range(15):
        res = client.post(
            "/budgets/",
            json={"category": "Groceries", "monthly_limit": 500 + i, "budget_year": 2026, "budget_month": i % 12 + 1},
            headers=headers
        )
        if res.status_code == 429:
            blocked = res
            break

    assert blocked is not None
    assert blocked.status_code == 429
    assert "Retry-After" in blocked.headers
    assert blocked.json()["detail"] == "budgets.write_rate_limited"
