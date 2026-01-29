from datetime import date, timedelta
import json
from tests.helpers import create_expense, create_user_and_token, create_budget


def test_analytics_history(client):
    headers = create_user_and_token(
        client, "analyticsuser", "analyticsuser@example.com", "Password123!"
    )
    create_budget(client, headers, category="Food", monthly_limit=500)

    # Add two expenses directly
    client.post("/expenses/", json={
        "title": "Item One",
        "amount": 10,
        "category": "Food",
        "description": "test",
        "date": date.today().isoformat(),
    }, headers=headers)
    client.post("/expenses/", json={
        "title": "Item Two",
        "amount": 20,
        "category": "Food",
        "description": "test",
        "date": date.today().isoformat(),
    }, headers=headers)

    res = client.get("/analytics/history", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["total_spent_lifetime"] == 30
    assert data["total_transaction"] == 2


def test_analytics_daily_trend(client):
    headers = create_user_and_token(
        client, "trenduser", "trenduser@example.com", "Password123!"
    )
    create_budget(client, headers, category="Food", monthly_limit=500)

    today = date.today()
    yesterday = today - timedelta(days=1)
    client.post("/expenses/", json={
        "title": "Yes",
        "amount": 5,
        "category": "Food",
        "description": "test",
        "date": yesterday.isoformat(),
    }, headers=headers)

    res = client.get("/analytics/daily-trend?days=2", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 2


def test_daily_trend_days_filter(client):
    headers = create_user_and_token(
        client, "daysfilteruser", "daysfilteruser@example.com", "Password123!"
    )
    create_budget(client, headers, category="Food", monthly_limit=500)

    today = date.today()
    three_days_ago = today - timedelta(days=3)

    client.post("/expenses/", json={
        "title": "Three Days",
        "amount": 10,
        "category": "Food",
        "description": "test",
        "date": three_days_ago.isoformat(),
    }, headers=headers)

    res = client.get("/analytics/daily-trend?days=2", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 2


def test_analytic_daily_trend_invalid_days(client):
    headers = create_user_and_token(
        client, "invaliddayuser", "invaliddayuser@example.com", "Password123!"
    )
    create_budget(client, headers, category="Food", monthly_limit=500)
    over_366_days_in_the_past = date.today() - timedelta(days=400)
    just_within_366_days_in_the_past = date.today() - timedelta(days=365)
    client.post("/expenses/", json={
        "title": "Older than 366 days",
        "amount": 15,
        "category": "Food",
        "description": "Test",
        "date": over_366_days_in_the_past.isoformat(),
    }, headers=headers)
    client.post("/expenses/", json={
        "title": "Just within 366 days",
        "amount": 15,
        "category": "Food",
                    "description": "Test",
                    "date": just_within_366_days_in_the_past.isoformat(),
    }, headers=headers)
    res1 = client.get("/analytics/daily-trend?days=0", headers=headers)
    res2 = client.get("/analytics/daily-trend?days=400", headers=headers)
    assert res1.status_code == 400
    assert res2.status_code == 400

    res_missing_end = client.get(
        f"/analytics/daily-trend?start_date={just_within_366_days_in_the_past.isoformat()}",
        headers=headers,
    )
    res_missing_start = client.get(
        f"/analytics/daily-trend?end_date={date.today().isoformat()}",
        headers=headers,
    )
    assert res_missing_end.status_code == 400
    assert res_missing_start.status_code == 400

    res3 = client.get(
        f"/analytics/daily-trend?start_date={just_within_366_days_in_the_past.isoformat()}&end_date={date.today().isoformat()}",
        headers=headers,
    )
    assert res3.status_code == 200
    assert len(res3.json()) == 366


def test_daily_trend_date_range_filters(client):
    headers = create_user_and_token(
        client, "daterangeuser", "daterangeuser@example.com", "Password123!"
    )
    create_budget(client, headers, category="Food", monthly_limit=500)

    today = date.today()
    two_days_ago = today - timedelta(days=2)
    one_day_ago = today - timedelta(days=1)

    client.post("/expenses/", json={
        "title": "Two Days",
        "amount": 10,
        "category": "Food",
        "description": "test",
        "date": two_days_ago.isoformat(),
    }, headers=headers)
    client.post("/expenses/", json={
        "title": "One Day",
        "amount": 10,
        "category": "Food",
        "description": "test",
        "date": one_day_ago.isoformat(),
    }, headers=headers)

    res = client.get(
        f"/analytics/daily-trend?start_date={two_days_ago.isoformat()}&end_date={one_day_ago.isoformat()}",
        headers=headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 2


def test_daily_trend_invalid_range(client):
    headers = create_user_and_token(
        client, "invalidrangeuser", "invalidrangeuser@example.com", "Password123!"
    )
    create_budget(client, headers, category="Food", monthly_limit=500)

    today = date.today()
    yesterday = today - timedelta(days=1)

    res = client.get(
        f"/analytics/daily-trend?start_date={today.isoformat()}&end_date={yesterday.isoformat()}",
        headers=headers,
    )
    assert res.status_code == 400
