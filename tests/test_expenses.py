from datetime import date, timedelta

from tests.helpers import create_user_and_token, create_budget, create_expense


def test_create_expense_requires_budget(client):
    headers = create_user_and_token(
        client, "expuser", "expuser@example.com", "Password123!"
    )
    res = create_expense(client, headers, category="Food")
    assert res.status_code == 400


def test_create_and_get_expense(client):
    headers = create_user_and_token(
        client, "expuser2", "expuser2@example.com", "Password123!"
    )
    create_budget(client, headers, category="Food", monthly_limit=500)
    res = create_expense(client, headers, title="Burger", amount=12.5, category="Food")
    assert res.status_code == 201
    expense_id = res.json()["id"]

    res_get = client.get(f"/expenses/{expense_id}", headers=headers)
    assert res_get.status_code == 200
    assert res_get.json()["title"] == "Burger"


def test_list_expenses(client):
    headers = create_user_and_token(
        client, "expuser3", "expuser3@example.com", "Password123!"
    )
    create_budget(client, headers, category="Food", monthly_limit=500)
    create_expense(client, headers, title="Item A", amount=5, category="Food")
    create_expense(client, headers, title="Item B", amount=7, category="Food")
    res = client.get("/expenses/", headers=headers)
    assert res.status_code == 200
    assert len(res.json()) == 2


def test_create_expense_invalid_title(client):
    headers = create_user_and_token(
        client, "expuser6", "expuser6@example.com", "Password123!"
    )
    create_budget(client, headers, category="Food", monthly_limit=500)

    res_short = create_expense(client, headers, title="ab", amount=10, category="Food")
    assert res_short.status_code == 422

    res_blank = create_expense(client, headers, title="   ", amount=10, category="Food")
    assert res_blank.status_code == 422

    res_long = create_expense(client, headers, title="a" * 81, amount=10, category="Food")
    assert res_long.status_code == 422


def test_create_expense_invalid_description(client):
    headers = create_user_and_token(
        client, "expuser7", "expuser7@example.com", "Password123!"
    )
    create_budget(client, headers, category="Food", monthly_limit=500)

    res = create_expense(
        client,
        headers,
        title="Valid Title",
        amount=10,
        category="Food",
        description="x" * 501,
    )
    assert res.status_code == 422


def test_title_description_trimmed(client):
    headers = create_user_and_token(
        client, "expuser8", "expuser8@example.com", "Password123!"
    )
    create_budget(client, headers, category="Food", monthly_limit=500)

    res = create_expense(
        client,
        headers,
        title="  Sandwich  ",
        amount=10,
        category="Food",
        description="  tasty  ",
    )
    assert res.status_code == 201
    data = res.json()
    assert data["title"] == "Sandwich"
    assert data["description"] == "tasty"


def test_create_expense_invalid_amount(client):
    headers = create_user_and_token(
        client, "expuser9", "expuser9@example.com", "Password123!"
    )
    create_budget(client, headers, category="Food", monthly_limit=500)

    res_zero = create_expense(client, headers, title="Zero", amount=0, category="Food")
    assert res_zero.status_code == 422

    res_negative = create_expense(client, headers, title="Neg", amount=-5, category="Food")
    assert res_negative.status_code == 422


def test_create_expense_invalid_category(client):
    headers = create_user_and_token(
        client, "expuser10", "expuser10@example.com", "Password123!"
    )
    create_budget(client, headers, category="Food", monthly_limit=500)

    res = client.post("/expenses/", json={
        "title": "BadCategory",
        "amount": 10,
        "category": "InvalidCategory",
        "description": "test",
        "date": date.today().isoformat(),
    }, headers=headers)
    assert res.status_code == 422


def test_create_expense_invalid_date(client):
    headers = create_user_and_token(
        client, "expuser11", "expuser11@example.com", "Password123!"
    )
    create_budget(client, headers, category="Food", monthly_limit=500)

    future_date = (date.today() + timedelta(days=1)).isoformat()
    res_future = client.post("/expenses/", json={
        "title": "Future",
        "amount": 10,
        "category": "Food",
        "description": "test",
        "date": future_date,
    }, headers=headers)
    assert res_future.status_code == 422

    past_date = date(2019, 12, 31).isoformat()
    res_past = client.post("/expenses/", json={
        "title": "Past",
        "amount": 10,
        "category": "Food",
        "description": "test",
        "date": past_date,
    }, headers=headers)
    assert res_past.status_code == 422


def test_list_expenses_filters_and_sort(client):
    headers = create_user_and_token(
        client, "expuser12", "expuser12@example.com", "Password123!"
    )
    create_budget(client, headers, category="Food", monthly_limit=500)
    create_budget(client, headers, category="Transport", monthly_limit=500)

    create_expense(client, headers, title="Coffee", amount=3, category="Food")
    create_expense(client, headers, title="Taxi Ride", amount=25, category="Transport")
    create_expense(client, headers, title="Big Lunch", amount=15, category="Food")

    res_search = client.get("/expenses/?search=coffee", headers=headers)
    assert res_search.status_code == 200
    assert len(res_search.json()) == 1

    res_category = client.get("/expenses/?category=Food", headers=headers)
    assert res_category.status_code == 200
    assert all(item["category"] == "Food" for item in res_category.json())

    res_sort = client.get("/expenses/?sort=expensive", headers=headers)
    assert res_sort.status_code == 200
    amounts = [item["amount"] for item in res_sort.json()]
    assert amounts == sorted(amounts, reverse=True)


def test_list_expenses_time_range(client):
    headers = create_user_and_token(
        client, "expuser13", "expuser13@example.com", "Password123!"
    )
    create_budget(client, headers, category="Food", monthly_limit=500)

    old_date = (date.today() - timedelta(days=40)).isoformat()
    recent_date = (date.today() - timedelta(days=5)).isoformat()

    client.post("/expenses/", json={
        "title": "Old",
        "amount": 10,
        "category": "Food",
        "description": "test",
        "date": old_date,
    }, headers=headers)
    client.post("/expenses/", json={
        "title": "Recent",
        "amount": 10,
        "category": "Food",
        "description": "test",
        "date": recent_date,
    }, headers=headers)

    res = client.get("/expenses/?time_range=past_month", headers=headers)
    assert res.status_code == 200
    titles = [item["title"] for item in res.json()]
    assert "Recent" in titles
    assert "Old" not in titles


def test_update_expense(client):
    headers = create_user_and_token(
        client, "expuser4", "expuser4@example.com", "Password123!"
    )
    create_budget(client, headers, category="Food", monthly_limit=500)
    res = create_expense(client, headers, title="Old", amount=10, category="Food")
    expense_id = res.json()["id"]

    res_update = client.put(
        f"/expenses/{expense_id}",
        json={
            "title": "New",
            "amount": 20,
            "category": "Food",
            "date": "2024-01-01",
        },
        headers=headers,
    )
    assert res_update.status_code == 200
    assert res_update.json()["title"] == "New"


def test_delete_expense(client):
    headers = create_user_and_token(
        client, "expuser5", "expuser5@example.com", "Password123!"
    )
    create_budget(client, headers, category="Food", monthly_limit=500)
    res = create_expense(client, headers, title="Delete", amount=10, category="Food")
    expense_id = res.json()["id"]

    res_del = client.delete(f"/expenses/{expense_id}", headers=headers)
    assert res_del.status_code == 204
    res_get = client.get(f"/expenses/{expense_id}", headers=headers)
    assert res_get.status_code == 404
