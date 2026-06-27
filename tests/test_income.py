from datetime import timedelta

from app import models
from app.redis_rate_limiter import redis_client
from tests.helpers import create_budget, create_expense, create_user_and_token, user_timezone_today


def _get_user(session, email: str) -> models.User:
    user = session.query(models.User).filter(models.User.email == email).first()
    assert user is not None
    return user


def _default_wallet(session, user_id: int) -> models.Wallet:
    wallet = (
        session.query(models.Wallet)
        .filter(models.Wallet.owner_id == user_id, models.Wallet.is_default)
        .first()
    )
    assert wallet is not None
    return wallet


def _create_wallet(session, owner_id: int, name: str, balance: int = 1_000_000) -> models.Wallet:
    wallet = models.Wallet(
        owner_id=owner_id,
        name=name,
        wallet_type=models.WalletType.DEBIT,
        accounting_type=models.AccountingType.ASSET,
        initial_balance=balance,
        current_balance=balance,
        is_default=False,
    )
    session.add(wallet)
    session.commit()
    session.refresh(wallet)
    return wallet


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
            "date": user_timezone_today().isoformat(),
        },
        headers=headers,
    )
    assert created.status_code == 201
    entry_id = created.json()["id"]
    assert created.json()["wallet_allocations"][0]["amount"] == 500000

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
            "date": user_timezone_today().isoformat(),
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
            "life_statuses": ["employed"],
            "wallets": [
                {
                    "name": "Main Wallet",
                    "wallet_type": "DEBIT",
                    "initial_balance": 2_000_000,
                }
            ],
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
            "date": user_timezone_today().isoformat(),
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


def test_income_entry_supports_multi_wallet_allocations(client, session):
    email = "incomeuser_multiwallet@example.com"
    headers = create_user_and_token(
        client, "incomeusermultiwallet", email, "Password123!"
    )
    user = _get_user(session, email)
    default_wallet = _default_wallet(session, user.id)
    second_wallet = _create_wallet(session, user.id, "Salary Savings")

    source = client.post("/income/sources", json={"name": "Salary"}, headers=headers)
    assert source.status_code == 201, source.text
    source_id = source.json()["id"]

    created = client.post(
        "/income/entries",
        json={
            "amount": 500_000,
            "source_id": source_id,
            "note": "Split salary",
            "date": user_timezone_today().isoformat(),
            "wallet_allocations": [
                {"wallet_id": default_wallet.id, "amount": 200_000},
                {"wallet_id": second_wallet.id, "amount": 300_000},
            ],
        },
        headers=headers,
    )
    assert created.status_code == 201, created.text
    entry_id = created.json()["id"]
    assert created.json()["wallet_id"] is None
    assert sorted((item["wallet_id"], item["amount"]) for item in created.json()["wallet_allocations"]) == [
        (default_wallet.id, 200_000),
        (second_wallet.id, 300_000),
    ]

    session.expire_all()
    default_wallet = session.query(models.Wallet).filter(models.Wallet.id == default_wallet.id).first()
    second_wallet = session.query(models.Wallet).filter(models.Wallet.id == second_wallet.id).first()
    assert default_wallet.current_balance == 10_200_000
    assert second_wallet.current_balance == 1_300_000

    listed = client.get("/income/entries?limit=10&skip=0", headers=headers)
    assert listed.status_code == 200, listed.text
    listed_entry = listed.json()["items"][0]
    assert listed_entry["id"] == entry_id
    assert sorted((item["wallet_id"], item["amount"]) for item in listed_entry["wallet_allocations"]) == [
        (default_wallet.id, 200_000),
        (second_wallet.id, 300_000),
    ]

    updated = client.put(
        f"/income/entries/{entry_id}",
        json={
            "amount": 600_000,
            "source_id": source_id,
            "note": "Updated split salary",
            "date": user_timezone_today().isoformat(),
            "wallet_allocations": [
                {"wallet_id": default_wallet.id, "amount": 100_000},
                {"wallet_id": second_wallet.id, "amount": 500_000},
            ],
        },
        headers=headers,
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["amount"] == 600_000

    session.expire_all()
    default_wallet = session.query(models.Wallet).filter(models.Wallet.id == default_wallet.id).first()
    second_wallet = session.query(models.Wallet).filter(models.Wallet.id == second_wallet.id).first()
    assert default_wallet.current_balance == 10_100_000
    assert second_wallet.current_balance == 1_500_000

    deleted = client.delete(f"/income/entries/{entry_id}", headers=headers)
    assert deleted.status_code == 204

    session.expire_all()
    default_wallet = session.query(models.Wallet).filter(models.Wallet.id == default_wallet.id).first()
    second_wallet = session.query(models.Wallet).filter(models.Wallet.id == second_wallet.id).first()
    assert default_wallet.current_balance == 10_000_000
    assert second_wallet.current_balance == 1_000_000


def test_money_in_lists_and_classifies_incoming_money(client, session):
    email = "moneyinuser@example.com"
    headers = create_user_and_token(client, "moneyinuser", email, "Password123!")
    user = _get_user(session, email)
    default_wallet = _default_wallet(session, user.id)

    source = client.post("/income/sources", json={"name": "Salary"}, headers=headers)
    assert source.status_code == 201, source.text
    source_id = source.json()["id"]
    income = client.post(
        "/income/entries",
        json={
            "amount": 1_000_000,
            "source_id": source_id,
            "date": user_timezone_today().isoformat(),
            "note": "Monthly salary",
            "wallet_id": default_wallet.id,
        },
        headers=headers,
    )
    assert income.status_code == 201, income.text

    create_budget(client, headers, category="Food", monthly_limit=1_000_000)
    expense = create_expense(client, headers, title="Refunded lunch", amount=100_000, category="Food")
    assert expense.status_code == 201, expense.text
    refund = client.post(
        f"/expenses/{expense.json()['id']}/refund",
        json={"amount": 40_000},
        headers=headers,
    )
    assert refund.status_code == 201, refund.text

    borrowed = client.post(
        "/debts",
        json={
            "debt_type": "OWING",
            "counterparty_name": "Friend",
            "origin_kind": "CASH_BORROWED",
            "initial_amount": 300_000,
            "currency": "UZS",
            "date": user_timezone_today().isoformat(),
            "expected_return_date": user_timezone_today().isoformat(),
            "is_money_transferred": True,
            "initial_wallet_allocations": [
                {"wallet_id": default_wallet.id, "amount": 300_000},
            ],
        },
        headers=headers,
    )
    assert borrowed.status_code == 201, borrowed.text

    asset = client.post(
        "/assets",
        json={
            "title": "Old phone",
            "purchase_value": 500_000,
            "current_value": 300_000,
            "status": "owned",
        },
        headers=headers,
    )
    assert asset.status_code == 201, asset.text
    sold = client.post(
        f"/assets/{asset.json()['id']}/sell",
        json={
            "sale_value": 200_000,
            "sold_date": user_timezone_today().isoformat(),
            "destination_wallet_id": default_wallet.id,
            "note": "Sold to neighbor",
        },
        headers=headers,
    )
    assert sold.status_code == 200, sold.text

    session.expire_all()
    wallet = session.query(models.Wallet).filter(models.Wallet.id == default_wallet.id).first()
    adjustment = client.post(
        f"/wallets/{default_wallet.id}/reconcile",
        json={"target_balance": int(wallet.current_balance) + 50_000, "note": "Bank correction"},
        headers=headers,
    )
    assert adjustment.status_code == 200, adjustment.text

    all_money_in = client.get("/money-in?limit=20&skip=0", headers=headers)
    assert all_money_in.status_code == 200, all_money_in.text
    all_payload = all_money_in.json()
    assert all_payload["total"] >= 5
    kinds = {item["kind"] for item in all_payload["items"]}
    assert {"income", "returned", "borrowed", "sold", "adjustment"}.issubset(kinds)

    paged_money_in = client.get("/money-in?limit=1&skip=1", headers=headers)
    assert paged_money_in.status_code == 200, paged_money_in.text
    assert paged_money_in.json()["total"] == all_payload["total"]
    assert len(paged_money_in.json()["items"]) == 1

    income_only = client.get("/money-in?kind=income", headers=headers)
    assert income_only.status_code == 200, income_only.text
    assert income_only.json()["total"] == 1
    assert income_only.json()["items"][0]["counts_as_income"] is True
    assert income_only.json()["items"][0]["source_name"] == "Salary"

    borrowed_only = client.get("/money-in?kind=borrowed", headers=headers)
    assert borrowed_only.status_code == 200, borrowed_only.text
    assert borrowed_only.json()["total"] == 1
    assert borrowed_only.json()["items"][0]["counts_as_income"] is False
    assert borrowed_only.json()["items"][0]["source_name"] == "Friend"

    salary_search = client.get("/money-in?search=salary", headers=headers)
    assert salary_search.status_code == 200, salary_search.text
    assert salary_search.json()["total"] == 1
    assert salary_search.json()["items"][0]["source_name"] == "Salary"

    friend_search = client.get("/money-in?search=friend", headers=headers)
    assert friend_search.status_code == 200, friend_search.text
    assert friend_search.json()["total"] == 1
    assert friend_search.json()["items"][0]["kind"] == "borrowed"

    asset_search = client.get("/money-in?search=old%20phone", headers=headers)
    assert asset_search.status_code == 200, asset_search.text
    assert asset_search.json()["total"] == 1
    assert asset_search.json()["items"][0]["kind"] == "sold"

    missing_search = client.get("/money-in?search=does-not-exist", headers=headers)
    assert missing_search.status_code == 200, missing_search.text
    assert missing_search.json() == {"total": 0, "items": []}


def test_income_entry_rejects_date_outside_current_month(client):
    headers = create_user_and_token(
        client, "incomeuser4", "incomeuser4@example.com", "Password123!"
    )
    source = client.post("/income/sources", json={"name": "Salary"}, headers=headers)
    assert source.status_code == 201
    source_id = source.json()["id"]

    today = user_timezone_today()
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

    today = user_timezone_today()
    wallet = session.query(models.Wallet).filter(models.Wallet.owner_id == user.id).first()

    session.add_all([
        models.FinancialEvent(
            owner_id=user.id,
            title=f"Entry {i}",
            event_type=models.TransactionType.INCOME,
            status=models.FinancialEventStatus.POSTED,
            description=f"Entry {i}",
            date=today,
            wallet_legs=[
                models.WalletLedger(
                    owner_id=user.id,
                    wallet_id=wallet.id,
                    amount=1000 + i,
                )
            ],
            entity_legs=[
                models.EntityLedger(
                    amount=1000 + i,
                    income_source_id=source.id,
                )
            ],
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
                "date": user_timezone_today().isoformat(),
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
