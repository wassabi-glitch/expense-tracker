import csv
from datetime import date, timedelta
from io import StringIO

from tests.helpers import create_user_and_token, create_budget, create_expense


def _parse_csv(text):
    reader = csv.reader(StringIO(text))
    rows = list(reader)
    return rows


def test_export_expenses_basic(client):
    headers = create_user_and_token(
        client, "exportuser", "exportuser@example.com", "Password123!"
    )
    create_budget(client, headers, category="Food", monthly_limit=500)
    create_expense(client, headers, title="Apples", amount=20, category="Food")

    res = client.get("/expenses/export", headers=headers)
    assert res.status_code == 200
    assert res.headers["content-type"].startswith("text/csv")

    rows = _parse_csv(res.text)
    assert rows[0] == ["date", "title", "amount", "category", "description"]
    assert rows[1][1] == "Apples"


def test_export_expenses_filters(client):
    headers = create_user_and_token(
        client, "exportuser2", "exportuser2@example.com", "Password123!"
    )
    create_budget(client, headers, category="Food", monthly_limit=500)
    create_budget(client, headers, category="Transport", monthly_limit=500)
    create_expense(client, headers, title="Food Item", amount=5, category="Food")
    create_expense(client, headers, title="Taxi Ride", amount=15, category="Transport")

    res = client.get("/expenses/export?category=Food", headers=headers)
    assert res.status_code == 200

    rows = _parse_csv(res.text)
    assert rows[0] == ["date", "title", "amount", "category", "description"]
    assert len(rows) == 2
    assert rows[1][3] == "Food"


def test_export_expenses_sorted_by_date_desc(client):
    headers = create_user_and_token(
        client, "exportuser3", "exportuser3@example.com", "Password123!"
    )
    create_budget(client, headers, category="Food", monthly_limit=500)

    today = date.today()
    two_days_ago = today - timedelta(days=2)
    one_day_ago = today - timedelta(days=1)

    res_old = client.post(
        "/expenses/",
        json={
            "title": "Older",
            "amount": 10,
            "category": "Food",
            "description": "old",
            "date": two_days_ago.isoformat(),
        },
        headers=headers,
    )
    assert res_old.status_code == 201

    res_new = client.post(
        "/expenses/",
        json={
            "title": "Newest",
            "amount": 20,
            "category": "Food",
            "description": "new",
            "date": one_day_ago.isoformat(),
        },
        headers=headers,
    )
    assert res_new.status_code == 201

    res = client.get("/expenses/export", headers=headers)
    assert res.status_code == 200

    rows = _parse_csv(res.text)
    data_rows = rows[1:]
    exported_dates = [row[0] for row in data_rows]
    assert exported_dates == sorted(exported_dates, reverse=True)


def test_export_expenses_sorted_by_date_asc(client):
    headers = create_user_and_token(
        client, "exportuser4", "exportuser4@example.com", "Password123!"
    )
    create_budget(client, headers, category="Food", monthly_limit=500)

    today = date.today()
    two_days_ago = today - timedelta(days=2)
    one_day_ago = today - timedelta(days=1)

    res_old = client.post(
        "/expenses/",
        json={
            "title": "Older",
            "amount": 10,
            "category": "Food",
            "description": "old",
            "date": two_days_ago.isoformat(),
        },
        headers=headers,
    )
    assert res_old.status_code == 201

    res_new = client.post(
        "/expenses/",
        json={
            "title": "Newest",
            "amount": 20,
            "category": "Food",
            "description": "new",
            "date": one_day_ago.isoformat(),
        },
        headers=headers,
    )
    assert res_new.status_code == 201

    res = client.get("/expenses/export?sort=oldest", headers=headers)
    assert res.status_code == 200

    rows = _parse_csv(res.text)
    data_rows = rows[1:]
    exported_dates = [row[0] for row in data_rows]
    assert exported_dates == sorted(exported_dates)


def test_export_escapes_formula_like_cells(client):
    headers = create_user_and_token(
        client, "exportuser5", "exportuser5@example.com", "Password123!"
    )
    create_budget(client, headers, category="Food", monthly_limit=500)

    res_create = client.post(
        "/expenses/",
        json={
            "title": "=SUM(1,2)",
            "amount": 10,
            "category": "Food",
            "description": "+cmd|' /C calc'!A0",
            "date": date.today().isoformat(),
        },
        headers=headers,
    )
    assert res_create.status_code == 201

    res = client.get("/expenses/export", headers=headers)
    assert res.status_code == 200

    rows = _parse_csv(res.text)
    assert rows[1][1] == "'=SUM(1,2)"
    assert rows[1][4] == "'+cmd|' /C calc'!A0"
