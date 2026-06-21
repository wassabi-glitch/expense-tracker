from datetime import date, timedelta

from app import models
from tests.helpers import create_budget, create_expense, create_user_and_token, user_timezone_today


def _wallet(client, headers):
    response = client.get("/wallets", headers=headers)
    assert response.status_code == 200, response.text
    return response.json()[0]


def _source(client, headers, name="Salary"):
    response = client.post("/income/sources", json={"name": name}, headers=headers)
    assert response.status_code == 201, response.text
    return response.json()


def _month_date(source: date, offset: int) -> date:
    month_index = source.year * 12 + source.month - 1 + offset
    return date(month_index // 12, month_index % 12 + 1, min(source.day, 28))


def _create_earned(client, headers, source_id, amount, due_date):
    response = client.post(
        "/expected-inflows",
        json={
            "kind": "EARNED",
            "source_id": source_id,
            "amount": amount,
            "due_date": due_date.isoformat(),
        },
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_earned_partial_realization_updates_wallet_lifecycle_and_backing(client, session):
    headers = create_user_and_token(client, "g29earned", "g29earned@example.com", "Password123!")
    today = user_timezone_today()
    source = _source(client, headers)
    wallet = _wallet(client, headers)
    inflow = _create_earned(client, headers, source["id"], 1_000_000, today)

    summary = client.get(
        f"/budgets/month-summary?budget_year={today.year}&budget_month={today.month}",
        headers=headers,
    )
    assert summary.status_code == 200, summary.text
    assert summary.json()["expected_income_remaining"] == 1_000_000

    realized = client.post(
        f"/expected-inflows/{inflow['id']}/realize",
        json={
            "actual_amount": 400_000,
            "received_date": today.isoformat(),
            "wallet_allocations": [{"wallet_id": wallet["id"], "amount": 400_000}],
            "idempotency_key": "g29-earned-partial-1",
        },
        headers=headers,
    )
    assert realized.status_code == 200, realized.text
    payload = realized.json()["inflows"][0]
    assert payload["status"] == "PARTIALLY_RECEIVED"
    assert payload["received_amount"] == 400_000
    assert payload["remaining_amount"] == 600_000
    assert payload["backing_amount"] == 600_000

    summary = client.get(
        f"/budgets/month-summary?budget_year={today.year}&budget_month={today.month}",
        headers=headers,
    )
    assert summary.status_code == 200, summary.text
    assert summary.json()["expected_income_remaining"] == 600_000

    session.expire_all()
    persisted_wallet = session.query(models.Wallet).filter(models.Wallet.id == wallet["id"]).first()
    assert int(persisted_wallet.current_balance) == 10_400_000


def test_partial_inflow_reschedules_complete_remainder_without_ledger_effect(client, session):
    headers = create_user_and_token(client, "g29schedule", "g29schedule@example.com", "Password123!")
    today = user_timezone_today()
    source = _source(client, headers, "Contract")
    wallet = _wallet(client, headers)
    inflow = _create_earned(client, headers, source["id"], 1_000_000, today)
    received = client.post(
        f"/expected-inflows/{inflow['id']}/realize",
        json={
            "actual_amount": 400_000,
            "received_date": today.isoformat(),
            "wallet_allocations": [{"wallet_id": wallet["id"], "amount": 400_000}],
            "idempotency_key": "g29-schedule-partial",
        },
        headers=headers,
    )
    assert received.status_code == 200, received.text
    events_before = session.query(models.FinancialEvent).count()

    july = _month_date(today, 1)
    august = _month_date(today, 2)
    rescheduled = client.post(
        f"/expected-inflows/{inflow['id']}/reschedule",
        json={
            "allocations": [
                {"amount": 100_000, "due_date": july.isoformat()},
                {"amount": 500_000, "due_date": august.isoformat()},
            ]
        },
        headers=headers,
    )
    assert rescheduled.status_code == 200, rescheduled.text
    payload = rescheduled.json()
    assert payload["source"]["status"] == "PARTIALLY_RECEIVED"
    assert payload["source"]["is_rescheduled"] is True
    assert payload["source"]["amount"] == 1_000_000
    assert payload["source"]["received_amount"] == 400_000
    assert sorted(item["amount"] for item in payload["replacements"]) == [100_000, 500_000]
    assert all(item["parent_id"] == inflow["id"] for item in payload["replacements"])
    assert session.query(models.FinancialEvent).count() == events_before


def test_reschedule_retains_unmoved_amount_and_rejects_new_past_date(client):
    headers = create_user_and_token(client, "g29move", "g29move@example.com", "Password123!")
    today = user_timezone_today()
    original_due = today - timedelta(days=7)
    source = _source(client, headers, "Late project")
    inflow = _create_earned(client, headers, source["id"], 500_000, original_due)

    invalid = client.post(
        f"/expected-inflows/{inflow['id']}/reschedule",
        json={"allocations": [{"amount": 500_000, "due_date": (today - timedelta(days=1)).isoformat()}]},
        headers=headers,
    )
    assert invalid.status_code == 400, invalid.text
    assert invalid.json()["detail"] == "expected_inflow.reschedule_date_in_past"

    valid = client.post(
        f"/expected-inflows/{inflow['id']}/reschedule",
        json={
            "allocations": [
                {"amount": 300_000, "due_date": original_due.isoformat()},
                {"amount": 200_000, "due_date": (today + timedelta(days=30)).isoformat()},
            ]
        },
        headers=headers,
    )
    assert valid.status_code == 200, valid.text
    replacements = valid.json()["replacements"]
    assert {(item["amount"], item["due_date"]) for item in replacements} == {
        (300_000, original_due.isoformat()),
        (200_000, (today + timedelta(days=30)).isoformat()),
    }


def test_one_earned_receipt_can_resolve_sibling_schedules_once(client, session):
    headers = create_user_and_token(client, "g29multi", "g29multi@example.com", "Password123!")
    today = user_timezone_today()
    source = _source(client, headers, "Client")
    wallet = _wallet(client, headers)
    inflow = _create_earned(client, headers, source["id"], 300_000, today)
    rescheduled = client.post(
        f"/expected-inflows/{inflow['id']}/reschedule",
        json={
            "allocations": [
                {"amount": 100_000, "due_date": _month_date(today, 1).isoformat()},
                {"amount": 200_000, "due_date": _month_date(today, 2).isoformat()},
            ]
        },
        headers=headers,
    )
    assert rescheduled.status_code == 200, rescheduled.text
    replacements = rescheduled.json()["replacements"]
    events_before = session.query(models.FinancialEvent).count()

    realized = client.post(
        f"/expected-inflows/{inflow['id']}/realize",
        json={
            "actual_amount": 300_000,
            "received_date": today.isoformat(),
            "wallet_allocations": [{"wallet_id": wallet["id"], "amount": 300_000}],
            "schedule_allocations": [
                {"schedule_id": replacements[0]["id"], "amount": replacements[0]["amount"]},
                {"schedule_id": replacements[1]["id"], "amount": replacements[1]["amount"]},
            ],
            "idempotency_key": "g29-multi-expected",
        },
        headers=headers,
    )
    assert realized.status_code == 200, realized.text
    payload = realized.json()
    assert len(payload["realization"]["event_ids"]) == 1
    assert payload["inflow"]["status"] == "RESOLVED"
    assert session.query(models.FinancialEvent).count() == events_before + 1

    retried = client.post(
        f"/expected-inflows/{inflow['id']}/realize",
        json={
            "actual_amount": 300_000,
            "received_date": today.isoformat(),
            "wallet_allocations": [{"wallet_id": wallet["id"], "amount": 300_000}],
            "schedule_allocations": [
                {"schedule_id": replacements[0]["id"], "amount": replacements[0]["amount"]},
                {"schedule_id": replacements[1]["id"], "amount": replacements[1]["amount"]},
            ],
            "idempotency_key": "g29-multi-expected",
        },
        headers=headers,
    )
    assert retried.status_code == 200, retried.text
    assert session.query(models.FinancialEvent).count() == events_before + 1


def test_earned_receipt_can_exceed_expected_amount_without_overallocating_schedule(client, session):
    headers = create_user_and_token(client, "g29overpay", "g29overpay@example.com", "Password123!")
    today = user_timezone_today()
    source = _source(client, headers, "Client overpayment")
    wallet = _wallet(client, headers)
    inflow = _create_earned(client, headers, source["id"], 300_000, today)

    realized = client.post(
        f"/expected-inflows/{inflow['id']}/realize",
        json={
            "actual_amount": 350_000,
            "received_date": today.isoformat(),
            "wallet_allocations": [{"wallet_id": wallet["id"], "amount": 350_000}],
            "idempotency_key": "g29-overpay-receipt",
        },
        headers=headers,
    )

    assert realized.status_code == 200, realized.text
    payload = realized.json()
    assert payload["realization"]["actual_amount"] == 350_000
    assert payload["inflow"]["received_amount"] == 300_000
    assert payload["inflow"]["outstanding_amount"] == 0
    assert payload["inflow"]["status"] == "RESOLVED"
    event = session.get(models.FinancialEvent, payload["realization"]["event_ids"][0])
    assert event is not None
    assert sum(int(row.amount) for row in event.wallet_ledgers) == 350_000


def test_receivable_realization_links_principal_and_charge_events(client, session):
    headers = create_user_and_token(client, "g29debt", "g29debt@example.com", "Password123!")
    today = user_timezone_today()
    wallet = _wallet(client, headers)
    debt = client.post(
        "/debts",
        json={
            "debt_type": "OWED",
            "counterparty_name": "Ali",
            "initial_amount": 500_000,
            "currency": "UZS",
            "date": today.isoformat(),
            "is_money_transferred": False,
        },
        headers=headers,
    )
    assert debt.status_code == 201, debt.text
    charged = client.post(
        f"/debts/{debt.json()['id']}/add-charge",
        json={"amount": 200_000, "reason": "Late fee"},
        headers=headers,
    )
    assert charged.status_code == 201, charged.text
    inflow = client.post(
        "/expected-inflows",
        json={
            "kind": "RECEIVABLE",
            "debt_id": debt.json()["id"],
            "amount": 700_000,
            "due_date": today.isoformat(),
        },
        headers=headers,
    )
    assert inflow.status_code == 201, inflow.text

    realized = client.post(
        f"/expected-inflows/{inflow.json()['id']}/realize",
        json={
            "actual_amount": 600_000,
            "received_date": today.isoformat(),
            "wallet_allocations": [{"wallet_id": wallet["id"], "amount": 600_000}],
            "idempotency_key": "g29-debt-mixed",
        },
        headers=headers,
    )
    assert realized.status_code == 200, realized.text
    assert len(realized.json()["realization"]["event_ids"]) == 2
    assert realized.json()["inflows"][0]["remaining_amount"] == 100_000
    debt_after = client.get(f"/debts/{debt.json()['id']}", headers=headers)
    assert debt_after.status_code == 200, debt_after.text
    assert debt_after.json()["remaining_amount"] == 100_000
    event_types = {
        event.event_type
        for event in session.query(models.FinancialEvent)
        .filter(models.FinancialEvent.id.in_(realized.json()["realization"]["event_ids"]))
        .all()
    }
    assert models.TransactionType.DEBT_SETTLEMENT in event_types
    assert models.TransactionType.INCOME in event_types


def test_refund_and_asset_sale_expectations_delegate_to_source_domains(client, session):
    headers = create_user_and_token(client, "g29sources", "g29sources@example.com", "Password123!")
    today = user_timezone_today()
    wallet = _wallet(client, headers)
    create_budget(client, headers, category="Groceries", monthly_limit=1_000_000)
    expense = create_expense(client, headers, title="Returned groceries", amount=200_000, category="Groceries")
    assert expense.status_code == 201, expense.text
    expected_refund = client.post(
        "/expected-inflows",
        json={
            "kind": "REFUND",
            "refund_event_id": expense.json()["id"],
            "amount": 100_000,
            "due_date": today.isoformat(),
        },
        headers=headers,
    )
    assert expected_refund.status_code == 201, expected_refund.text
    refund = client.post(
        f"/expected-inflows/{expected_refund.json()['id']}/realize",
        json={
            "actual_amount": 100_000,
            "received_date": today.isoformat(),
            "wallet_allocations": [{"wallet_id": wallet["id"], "amount": 100_000}],
            "idempotency_key": "g29-refund",
        },
        headers=headers,
    )
    assert refund.status_code == 200, refund.text
    refund_event = session.query(models.FinancialEvent).filter(
        models.FinancialEvent.id == refund.json()["realization"]["event_ids"][0]
    ).first()
    assert refund_event.event_type == models.TransactionType.REFUND
    assert refund_event.linked_event_id == expense.json()["id"]

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
    expected_sale = client.post(
        "/expected-inflows",
        json={
            "kind": "ASSET_SALE",
            "asset_id": asset.json()["id"],
            "amount": 300_000,
            "due_date": today.isoformat(),
        },
        headers=headers,
    )
    assert expected_sale.status_code == 201, expected_sale.text
    sale = client.post(
        f"/expected-inflows/{expected_sale.json()['id']}/realize",
        json={
            "actual_amount": 250_000,
            "received_date": today.isoformat(),
            "wallet_allocations": [{"wallet_id": wallet["id"], "amount": 250_000}],
            "idempotency_key": "g29-asset-sale",
        },
        headers=headers,
    )
    assert sale.status_code == 200, sale.text
    sale_inflow = sale.json()["inflows"][0]
    assert sale_inflow["status"] == "WRITTEN_OFF"
    assert sale_inflow["written_off_amount"] == 50_000
    assert sale_inflow["close_reason"] == "WRITTEN_OFF"
    asset_after = client.get(f"/assets/{asset.json()['id']}", headers=headers)
    assert asset_after.status_code == 200, asset_after.text
    assert asset_after.json()["status"] == "sold"
    assert asset_after.json()["sale_value"] == 250_000


def test_partial_write_off_locks_financial_edits_and_can_be_reversed(client):
    headers = create_user_and_token(client, "g29writeoff", "g29writeoff@example.com", "Password123!")
    today = user_timezone_today()
    source = _source(client, headers, "Disputed contract")
    wallet = _wallet(client, headers)
    inflow = _create_earned(client, headers, source["id"], 500_000, today)

    received = client.post(
        f"/expected-inflows/{inflow['id']}/realize",
        json={
            "actual_amount": 200_000,
            "received_date": today.isoformat(),
            "wallet_allocations": [{"wallet_id": wallet["id"], "amount": 200_000}],
            "idempotency_key": "g29-writeoff-receipt",
        },
        headers=headers,
    )
    assert received.status_code == 200, received.text

    written_off = client.post(
        f"/expected-inflows/{inflow['id']}/write-off",
        json={
            "amount": 100_000,
            "reason": "Customer disputed this portion",
            "written_off_date": today.isoformat(),
        },
        headers=headers,
    )
    assert written_off.status_code == 200, written_off.text
    payload = written_off.json()
    assert payload["status"] == "PARTIALLY_RECEIVED"
    assert payload["received_amount"] == 200_000
    assert payload["written_off_amount"] == 100_000
    assert payload["outstanding_amount"] == 200_000
    assert payload["is_partially_written_off"] is True
    assert payload["original_amount"] == payload["received_amount"] + payload["written_off_amount"] + payload["outstanding_amount"]

    locked = client.patch(
        f"/expected-inflows/{inflow['id']}",
        json={"amount": 600_000},
        headers=headers,
    )
    assert locked.status_code == 409, locked.text
    renamed = client.patch(
        f"/expected-inflows/{inflow['id']}",
        json={"title": "Renamed disputed contract"},
        headers=headers,
    )
    assert renamed.status_code == 200, renamed.text
    assert renamed.json()["title"] == "Renamed disputed contract"

    write_off_id = payload["write_offs"][0]["id"]
    reversed_response = client.post(
        f"/expected-inflows/{inflow['id']}/write-offs/{write_off_id}/reverse",
        json={"note": "Customer accepted the disputed amount"},
        headers=headers,
    )
    assert reversed_response.status_code == 200, reversed_response.text
    reversed_payload = reversed_response.json()
    assert reversed_payload["written_off_amount"] == 0
    assert reversed_payload["outstanding_amount"] == 300_000
    assert reversed_payload["status"] == "PARTIALLY_RECEIVED"
