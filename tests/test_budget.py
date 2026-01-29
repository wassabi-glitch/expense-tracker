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
    create_budget(client, headers, category="Food", monthly_limit=300)
    create_budget(client, headers, category="Transport", monthly_limit=200)
    res = client.get("/budgets/", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 2


def test_get_budget_by_category(client):
    headers = create_user_and_token(
        client, "getbudget", "getbudget@example.com", "Password123!"
    )
    create_budget(client, headers, category="Food", monthly_limit=300)
    res = client.get("/budgets/Food", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["category"] == "Food"


def test_update_budget(client):
    headers = create_user_and_token(
        client, "updatebudget", "updatebudget@example.com", "Password123!"
    )
    create_budget(client, headers, category="Food", monthly_limit=300)
    res = client.put("/budgets/Food", json={"monthly_limit": 800}, headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["monthly_limit"] == 800


def test_delete_budget(client):
    headers = create_user_and_token(
        client, "deletebudget", "deletebudget@example.com", "Password123!"
    )
    create_budget(client, headers, category="Food", monthly_limit=300)
    res = client.delete("/budgets/Food", headers=headers)
    assert res.status_code == 204
    res_list = client.get("/budgets/", headers=headers)
    assert res_list.status_code == 200
    assert res_list.json() == []
