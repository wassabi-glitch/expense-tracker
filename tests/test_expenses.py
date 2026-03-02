from datetime import date, timedelta

import app.routers.expenses as expenses_router
from app import models
from app.redis_rate_limiter import redis_client
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
    res = create_expense(client, headers, title="Burger", amount=12, category="Food")
    assert res.status_code == 201
    assert "X-RateLimit-Limit" in res.headers
    assert "X-RateLimit-Remaining" in res.headers
    assert "X-RateLimit-Reset" in res.headers
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

    res_long = create_expense(client, headers, title="a" * 33, amount=10, category="Food")
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
    assert res_future.status_code == 400

    past_date = date(2019, 12, 31).isoformat()
    res_past = client.post("/expenses/", json={
        "title": "Past",
        "amount": 10,
        "category": "Food",
        "description": "test",
        "date": past_date,
    }, headers=headers)
    assert res_past.status_code == 422


def test_create_expense_future_date_uses_request_timezone(client, monkeypatch):
    headers = create_user_and_token(
        client, "expusertz1", "expusertz1@example.com", "Password123!"
    )
    create_budget(client, headers, category="Food", monthly_limit=500, budget_year=2026, budget_month=2)

    def fake_today_in_tz(tz):
        key = getattr(tz, "key", "")
        if key == "Asia/Tashkent":
            return date(2026, 2, 2)
        return date(2026, 2, 1)

    monkeypatch.setattr(expenses_router, "today_in_tz", fake_today_in_tz)

    base_payload = {
        "title": "Lunch",
        "amount": 10,
        "category": "Food",
        "description": "test",
        "date": "2026-02-02",
    }

    res_tashkent = client.post(
        "/expenses/",
        json=base_payload,
        headers={**headers, "X-Timezone": "Asia/Tashkent"},
    )
    assert res_tashkent.status_code == 201, res_tashkent.text

    res_utc = client.post(
        "/expenses/",
        json={**base_payload, "title": "Dinner"},
        headers={**headers, "X-Timezone": "UTC"},
    )
    assert res_utc.status_code == 400
    assert res_utc.json()["detail"] == "expenses.date_in_future"


def test_update_expense_future_date_uses_request_timezone(client, monkeypatch):
    headers = create_user_and_token(
        client, "expusertz2", "expusertz2@example.com", "Password123!"
    )
    create_budget(client, headers, category="Food", monthly_limit=500, budget_year=2026, budget_month=2)

    created = client.post(
        "/expenses/",
        json={
            "title": "Lunch",
            "amount": 10,
            "category": "Food",
            "description": "test",
            "date": "2026-02-01",
        },
        headers=headers,
    )
    assert created.status_code == 201, created.text
    expense_id = created.json()["id"]

    def fake_today_in_tz(tz):
        key = getattr(tz, "key", "")
        if key == "Asia/Tashkent":
            return date(2026, 2, 2)
        return date(2026, 2, 1)

    monkeypatch.setattr(expenses_router, "today_in_tz", fake_today_in_tz)

    res_tashkent = client.put(
        f"/expenses/{expense_id}",
        json={
            "title": "Lunch Updated",
            "amount": 11,
            "description": "test updated",
            "date": "2026-02-02",
        },
        headers={**headers, "X-Timezone": "Asia/Tashkent"},
    )
    assert res_tashkent.status_code == 200, res_tashkent.text

    res_utc = client.put(
        f"/expenses/{expense_id}",
        json={
            "title": "Lunch Updated",
            "amount": 11,
            "description": "test updated",
            "date": "2026-02-03",
        },
        headers={**headers, "X-Timezone": "UTC"},
    )
    assert res_utc.status_code == 400
    assert res_utc.json()["detail"] == "expenses.date_in_future"


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

    res_oldest = client.get("/expenses/?sort=oldest", headers=headers)
    assert res_oldest.status_code == 200
    dates = [item["date"] for item in res_oldest.json()]
    assert dates == sorted(dates)


def test_list_expenses_newest_uses_expense_date(client):
    headers = create_user_and_token(
        client, "expuser14", "expuser14@example.com", "Password123!"
    )
    create_budget(client, headers, category="Food", monthly_limit=500, budget_year=2024, budget_month=1)
    create_budget(client, headers, category="Food", monthly_limit=500, budget_year=2025, budget_month=1)

    client.post("/expenses/", json={
        "title": "Older by date",
        "amount": 10,
        "category": "Food",
        "description": "test",
        "date": "2024-01-01",
    }, headers=headers)
    client.post("/expenses/", json={
        "title": "Newer by date",
        "amount": 10,
        "category": "Food",
        "description": "test",
        "date": "2025-01-01",
    }, headers=headers)

    res = client.get("/expenses/?sort=newest", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert len(data) >= 2
    assert data[0]["date"] >= data[1]["date"]
    assert data[0]["title"] == "Newer by date"


def test_list_expenses_time_range(client):
    headers = create_user_and_token(
        client, "expuser13", "expuser13@example.com", "Password123!"
    )
    old_date = (date.today() - timedelta(days=40)).isoformat()
    recent_date = (date.today() - timedelta(days=5)).isoformat()
    old_dt = date.fromisoformat(old_date)
    recent_dt = date.fromisoformat(recent_date)
    create_budget(client, headers, category="Food", monthly_limit=500, budget_year=old_dt.year, budget_month=old_dt.month)
    if (old_dt.year, old_dt.month) != (recent_dt.year, recent_dt.month):
        create_budget(client, headers, category="Food", monthly_limit=500, budget_year=recent_dt.year, budget_month=recent_dt.month)

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
    create_budget(client, headers, category="Food", monthly_limit=500, budget_year=2024, budget_month=1)
    res = create_expense(client, headers, title="Old", amount=10, category="Food")
    expense_id = res.json()["id"]

    res_update = client.put(
        f"/expenses/{expense_id}",
        json={
            "title": "New",
            "amount": 20,
            "description": "updated description",
            "date": "2024-01-01",
        },
        headers=headers,
    )
    assert res_update.status_code == 200
    assert res_update.json()["title"] == "New"


def test_update_expense_allows_optional_description(client):
    headers = create_user_and_token(
        client, "expuser18", "expuser18@example.com", "Password123!"
    )
    create_budget(client, headers, category="Food", monthly_limit=500)
    create_budget(client, headers, category="Food", monthly_limit=500, budget_year=2024, budget_month=1)
    res = create_expense(client, headers, title="Meal", amount=10, category="Food", description="note")
    expense_id = res.json()["id"]

    res_update = client.put(
        f"/expenses/{expense_id}",
        json={
            "title": "Meal Updated",
            "amount": 25,
            "description": None,
            "date": "2024-01-01",
        },
        headers=headers,
    )
    assert res_update.status_code == 200, res_update.text
    assert res_update.json()["category"] == "Food"
    assert res_update.json()["description"] is None


def test_update_expense_rejects_category_field(client):
    headers = create_user_and_token(
        client, "expuser16", "expuser16@example.com", "Password123!"
    )
    create_budget(client, headers, category="Food", monthly_limit=500)
    create_budget(client, headers, category="Food", monthly_limit=500, budget_year=2024, budget_month=1)
    res = create_expense(client, headers, title="Lunch", amount=10, category="Food")
    expense_id = res.json()["id"]

    res_update = client.put(
        f"/expenses/{expense_id}",
        json={
            "title": "Lunch",
            "amount": 10,
            "category": "Transport",
            "description": "test",
            "date": "2024-01-01",
        },
        headers=headers,
    )
    assert res_update.status_code == 422


def test_update_expense_requires_full_payload(client):
    headers = create_user_and_token(
        client, "expuser17", "expuser17@example.com", "Password123!"
    )
    create_budget(client, headers, category="Food", monthly_limit=500)
    create_budget(client, headers, category="Food", monthly_limit=500, budget_year=2024, budget_month=1)
    res = create_expense(client, headers, title="Snack", amount=5, category="Food")
    expense_id = res.json()["id"]

    res_update = client.put(
        f"/expenses/{expense_id}",
        json={"date": "2024-01-01"},
        headers=headers,
    )
    assert res_update.status_code == 422


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


def test_expense_write_rate_limit_blocks_burst(client):
    for key in redis_client.scan_iter("tb:expenses_write:*"):
        redis_client.delete(key)

    headers = create_user_and_token(
        client, "expuser15", "expuser15@example.com", "Password123!"
    )
    create_budget(client, headers, category="Food", monthly_limit=5000)

    blocked = None
    for i in range(25):
        res = client.post("/expenses/", json={
            "title": f"Burst {i}",
            "amount": 10,
            "category": "Food",
            "description": "test",
            "date": date.today().isoformat(),
        }, headers=headers)
        if res.status_code == 429:
            blocked = res
            break

    assert blocked is not None
    assert blocked.status_code == 429
    assert "Retry-After" in blocked.headers


def test_create_expense_sets_budget_id_for_matching_month_budget(client, session):
    headers = create_user_and_token(
        client, "expbudgetfk1", "expbudgetfk1@example.com", "Password123!"
    )
    target_date = date(2024, 1, 15)
    budget_res = create_budget(
        client,
        headers,
        category="Food",
        monthly_limit=500,
        budget_year=2024,
        budget_month=1,
    )
    assert budget_res.status_code == 201, budget_res.text
    budget_id = budget_res.json()["id"]

    res = create_expense(
        client,
        headers,
        title="Lunch",
        amount=10,
        category="Food",
        expense_date=target_date,
    )
    assert res.status_code == 201, res.text
    expense_id = res.json()["id"]

    db_expense = session.query(models.Expense).filter(models.Expense.id == expense_id).first()
    assert db_expense is not None
    assert db_expense.budget_id == budget_id


def test_update_expense_rebinds_budget_id_when_date_month_changes(client, session):
    headers = create_user_and_token(
        client, "expbudgetfk2", "expbudgetfk2@example.com", "Password123!"
    )
    jan_budget = create_budget(
        client,
        headers,
        category="Food",
        monthly_limit=500,
        budget_year=2024,
        budget_month=1,
    )
    feb_budget = create_budget(
        client,
        headers,
        category="Food",
        monthly_limit=700,
        budget_year=2024,
        budget_month=2,
    )
    assert jan_budget.status_code == 201, jan_budget.text
    assert feb_budget.status_code == 201, feb_budget.text
    jan_budget_id = jan_budget.json()["id"]
    feb_budget_id = feb_budget.json()["id"]

    created = create_expense(
        client,
        headers,
        title="Meal",
        amount=20,
        category="Food",
        expense_date=date(2024, 1, 20),
    )
    assert created.status_code == 201, created.text
    expense_id = created.json()["id"]

    db_expense_before = session.query(models.Expense).filter(models.Expense.id == expense_id).first()
    assert db_expense_before is not None
    assert db_expense_before.budget_id == jan_budget_id

    updated = client.put(
        f"/expenses/{expense_id}",
        json={
            "title": "Meal moved",
            "amount": 25,
            "description": "moved to feb",
            "date": "2024-02-10",
        },
        headers=headers,
    )
    assert updated.status_code == 200, updated.text

    session.expire_all()
    db_expense_after = session.query(models.Expense).filter(models.Expense.id == expense_id).first()
    assert db_expense_after is not None
    assert db_expense_after.budget_id == feb_budget_id
