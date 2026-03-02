from datetime import date

from app.redis_rate_limiter import redis_client
from tests.helpers import create_user_and_token, create_budget


def test_create_budget_success(client):
    headers = create_user_and_token(
        client, "budgetuser", "budgetuser@example.com", "Password123!"
    )
    res = create_budget(client, headers, category="Food", monthly_limit=500)
    assert res.status_code == 201
    data = res.json()
    assert data["category"] == "Food"
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
            "category": "Food",
            "date": today.isoformat(),
        },
        headers=headers,
    )

    res = client.get("/budgets/", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 2
    
    food_budget = next(b for b in data if b["category"] == "Food")
    transport_budget = next(b for b in data if b["category"] == "Transport")
    
    assert food_budget["spent"] == 50
    assert transport_budget["spent"] == 0


def test_get_budget_by_category(client):
    headers = create_user_and_token(
        client, "getbudget", "getbudget@example.com", "Password123!"
    )
    today = date.today()
    create_budget(client, headers, category="Food", monthly_limit=300, budget_year=today.year, budget_month=today.month)
    res = client.get(f"/budgets/{today.year}/{today.month}/Food", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["category"] == "Food"
    assert "spent" in data


def test_update_budget(client):
    headers = create_user_and_token(
        client, "updatebudget", "updatebudget@example.com", "Password123!"
    )
    today = date.today()
    create_budget(client, headers, category="Food", monthly_limit=300, budget_year=today.year, budget_month=today.month)
    res = client.patch(f"/budgets/{today.year}/{today.month}/Food", json={"monthly_limit": 800}, headers=headers)
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
    res = client.delete(f"/budgets/{today.year}/{today.month}/Food", headers=headers)
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
            "category": "Food",
            "description": "test",
            "date": today.isoformat(),
        },
        headers=headers,
    )
    assert expense_res.status_code == 201, expense_res.text

    res = client.delete(f"/budgets/{today.year}/{today.month}/Food", headers=headers)
    assert res.status_code == 409
    assert res.json()["detail"] == "budgets.has_linked_expenses"

    still_exists = client.get(f"/budgets/{today.year}/{today.month}/Food", headers=headers)
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
            json={"category": "Food", "monthly_limit": 500 + i, "budget_year": 2026, "budget_month": i % 12 + 1},
            headers=headers
        )
        if res.status_code == 429:
            blocked = res
            break

    assert blocked is not None
    assert blocked.status_code == 429
    assert "Retry-After" in blocked.headers
    assert blocked.json()["detail"] == "budgets.write_rate_limited"
