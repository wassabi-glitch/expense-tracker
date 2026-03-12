from datetime import date, timedelta

from app import models
from app.redis_rate_limiter import redis_client
from tests.helpers import create_budget, create_expense, create_user_and_token


def test_income_source_create_and_duplicate_conflict(client):
    headers = create_user_and_token(
        client, "incomeuser1", "incomeuser1@example.com", "Password123!"
    )

    created = client.post("/income/sources", json={"name": "Salary"}, headers=headers)
    assert created.status_code == 201
    assert created.json()["name"] == "Salary"

    duplicate = client.post("/income/sources", json={"name": "salary"}, headers=headers)
    assert duplicate.status_code == 409


def test_income_entry_crud_and_list(client):
    headers = create_user_and_token(
        client, "incomeuser2", "incomeuser2@example.com", "Password123!"
    )

    source = client.post("/income/sources", json={"name": "Freelance"}, headers=headers)
    assert source.status_code == 201
    source_id = source.json()["id"]

    created = client.post(
        "/income/entries",
        json={
            "amount": 500000,
            "source_id": source_id,
            "note": "First payment",
            "date": date.today().isoformat(),
        },
        headers=headers,
    )
    assert created.status_code == 201
    entry_id = created.json()["id"]

    listed = client.get("/income/entries?limit=10&skip=0", headers=headers)
    assert listed.status_code == 200
    payload = listed.json()
    assert payload["total"] == 1
    assert payload["items"][0]["id"] == entry_id

    updated = client.put(
        f"/income/entries/{entry_id}",
        json={
            "amount": 700000,
            "source_id": source_id,
            "note": "Updated payment",
            "date": date.today().isoformat(),
        },
        headers=headers,
    )
    assert updated.status_code == 200
    assert updated.json()["amount"] == 700000

    deleted = client.delete(f"/income/entries/{entry_id}", headers=headers)
    assert deleted.status_code == 204


def test_dashboard_summary_uses_only_real_income_entries_after_onboarding(client):
    headers = create_user_and_token(
        client, "incomeuser3", "incomeuser3@example.com", "Password123!"
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

    sources = client.get("/income/sources?include_inactive=true", headers=headers)
    assert sources.status_code == 200
    salary_source = next((s for s in sources.json() if s["name"] == "Salary"), None)
    assert salary_source is not None
    source_id = salary_source["id"]

    entry = client.post(
        "/income/entries",
        json={
            "amount": 3_500_000,
            "source_id": source_id,
            "note": "Monthly salary",
            "date": date.today().isoformat(),
        },
        headers=headers,
    )
    assert entry.status_code == 201

    create_budget(client, headers, category="Food", monthly_limit=2_000_000)
    expense = create_expense(client, headers, title="Lunch", amount=500000, category="Food")
    assert expense.status_code == 201

    summary = client.get("/analytics/dashboard-summary", headers=headers)
    assert summary.status_code == 200
    payload = summary.json()
    assert payload["income"] == 3_500_000
    assert payload["spent"] == 500000
    assert payload["remaining"] == 3_000_000
    assert payload["overall_balance"] == 5_000_000


def test_income_entry_rejects_date_outside_current_month(client):
    headers = create_user_and_token(
        client, "incomeuser4", "incomeuser4@example.com", "Password123!"
    )
    source = client.post("/income/sources", json={"name": "Salary"}, headers=headers)
    assert source.status_code == 201
    source_id = source.json()["id"]

    today = date.today()
    month_start = today.replace(day=1)
    outside_date = month_start - timedelta(days=1)

    res = client.post(
        "/income/entries",
        json={
            "amount": 100000,
            "source_id": source_id,
            "date": outside_date.isoformat(),
            "note": "old",
        },
        headers=headers,
    )
    assert res.status_code == 400
    assert "income.date_outside_current_month" in res.text


def test_income_source_toggle_active_and_delete(client):
    headers = create_user_and_token(
        client, "incomeuser5", "incomeuser5@example.com", "Password123!"
    )

    source = client.post("/income/sources", json={"name": "Bonus"}, headers=headers)
    assert source.status_code == 201
    source_id = source.json()["id"]

    toggled = client.patch(
        f"/income/sources/{source_id}/active",
        json={"is_active": False},
        headers=headers,
    )
    assert toggled.status_code == 200
    assert toggled.json()["is_active"] is False

    deleted = client.delete(f"/income/sources/{source_id}", headers=headers)
    assert deleted.status_code == 204

    listed = client.get("/income/sources?include_inactive=true", headers=headers)
    assert listed.status_code == 200
    assert all(item["id"] != source_id for item in listed.json())


def test_income_source_limit_blocks_21st_source(client, session):
    email = "incomeuser6@example.com"
    headers = create_user_and_token(
        client, "incomeuser6", email, "Password123!"
    )
    user = session.query(models.User).filter(models.User.email == email).first()
    assert user is not None

    session.add_all([
        models.IncomeSource(owner_id=user.id, name=f"Source {i}", is_active=True)
        for i in range(20)
    ])
    session.commit()

    res = client.post("/income/sources", json={"name": "Source 21"}, headers=headers)
    assert res.status_code == 400
    assert res.json()["detail"] == "income.source_limit_reached"


def test_income_entry_month_limit_blocks_301st_entry(client, session):
    email = "incomeuser7@example.com"
    headers = create_user_and_token(
        client, "incomeuser7", email, "Password123!"
    )
    user = session.query(models.User).filter(models.User.email == email).first()
    assert user is not None

    source = models.IncomeSource(owner_id=user.id, name="Salary", is_active=True)
    session.add(source)
    session.flush()

    today = date.today()
    session.add_all([
        models.IncomeEntry(
            owner_id=user.id,
            source_id=source.id,
            amount=1000 + i,
            note=f"Entry {i}",
            date=today,
        )
        for i in range(300)
    ])
    session.commit()

    res = client.post(
        "/income/entries",
        json={
            "amount": 500000,
            "source_id": source.id,
            "note": "Overflow entry",
            "date": today.isoformat(),
        },
        headers=headers,
    )
    assert res.status_code == 400
    assert res.json()["detail"] == "income.entry_month_limit_reached"


def test_income_source_write_rate_limit_blocks_burst(client):
    for key in redis_client.scan_iter("tb:income_sources_write:*"):
        redis_client.delete(key)

    headers = create_user_and_token(
        client, "incomeuser8", "incomeuser8@example.com", "Password123!"
    )

    blocked = None
    for i in range(30):
        res = client.post("/income/sources", json={"name": f"Source {i}"}, headers=headers)
        if res.status_code == 429:
            blocked = res
            break

    assert blocked is not None
    assert blocked.status_code == 429
    assert blocked.json()["detail"] == "income.sources_write_rate_limited"
    assert "Retry-After" in blocked.headers


def test_income_entry_write_rate_limit_blocks_burst(client):
    for key in redis_client.scan_iter("tb:income_entries_write:*"):
        redis_client.delete(key)

    headers = create_user_and_token(
        client, "incomeuser9", "incomeuser9@example.com", "Password123!"
    )
    source = client.post("/income/sources", json={"name": "Freelance"}, headers=headers)
    assert source.status_code == 201
    source_id = source.json()["id"]

    blocked = None
    for i in range(40):
        res = client.post(
            "/income/entries",
            json={
                "amount": 100000 + i,
                "source_id": source_id,
                "note": f"Burst {i}",
                "date": date.today().isoformat(),
            },
            headers=headers,
        )
        if res.status_code == 429:
            blocked = res
            break

    assert blocked is not None
    assert blocked.status_code == 429
    assert blocked.json()["detail"] == "income.entries_write_rate_limited"
    assert "Retry-After" in blocked.headers
