import csv
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
