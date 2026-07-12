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
    assert payload["status"] == "OPEN"
    assert payload["display_state"] == "EXPECTED"
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
    assert payload["source"]["status"] == "OPEN"
    assert payload["source"]["display_state"] == "EXPECTED"
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
    assert payload["inflow"]["status"] == "CLOSED"
    assert payload["inflow"]["display_state"] == "FULLY_RECEIVED"
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


def test_over_receipt_above_promise_cap_is_rejected(client, session):
    """Ticket 2: receipt cannot exceed Promise original_amount.
    Excess money must be recorded as separate income."""
    headers = create_user_and_token(client, "g29overpay", "g29overpay@example.com", "Password123!")
    today = user_timezone_today()
    source = _source(client, headers, "Client overpayment")
    wallet = _wallet(client, headers)
    inflow = _create_earned(client, headers, source["id"], 300_000, today)

    # First receive 200k (leaves 100k remaining)
    partial = client.post(
        f"/expected-inflows/{inflow['id']}/realize",
        json={
            "actual_amount": 200_000,
            "received_date": today.isoformat(),
            "wallet_allocations": [{"wallet_id": wallet["id"], "amount": 200_000}],
            "idempotency_key": "g29-overpay-p1",
        },
        headers=headers,
    )
    assert partial.status_code == 200, partial.text
    assert partial.json()["inflows"][0]["remaining_amount"] == 100_000

    # Then try to over-receive: 150k against 100k remaining → rejected
    realized = client.post(
        f"/expected-inflows/{inflow['id']}/realize",
        json={
            "actual_amount": 150_000,
            "received_date": today.isoformat(),
            "wallet_allocations": [{"wallet_id": wallet["id"], "amount": 150_000}],
            "idempotency_key": "g29-overpay-receipt",
        },
        headers=headers,
    )

    assert realized.status_code == 400, realized.text
    assert realized.json()["detail"] == "expected_inflow.over_cap"

    # Exact remaining amount should still be accepted
    exact = client.post(
        f"/expected-inflows/{inflow['id']}/realize",
        json={
            "actual_amount": 100_000,
            "received_date": today.isoformat(),
            "wallet_allocations": [{"wallet_id": wallet["id"], "amount": 100_000}],
            "idempotency_key": "g29-exact-receipt",
        },
        headers=headers,
    )
    assert exact.status_code == 200, exact.text
    payload = exact.json()
    assert payload["inflow"]["received_amount"] == 300_000
    assert payload["inflow"]["outstanding_amount"] == 0
    assert payload["inflow"]["status"] == "CLOSED"
    assert payload["inflow"]["display_state"] == "FULLY_RECEIVED"


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
            "expected_return_date": today.isoformat(),
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
    assert sale_inflow["status"] == "CLOSED"
    assert sale_inflow["display_state"] == "SETTLED"
    assert sale_inflow["written_off_amount"] == 50_000
    assert sale_inflow["close_reason"] == "SETTLED"
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
    assert payload["status"] == "OPEN"
    assert payload["display_state"] == "EXPECTED"
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
    assert reversed_payload["status"] == "OPEN"
    assert reversed_payload["display_state"] == "EXPECTED"


# ---------------------------------------------------------------------------
# Ticket 7: First-class receipt reversal
# ---------------------------------------------------------------------------


def test_full_receipt_reversal_restores_outstanding_and_preserves_history(client):
    """Reverse an entire receipt — outstanding restored, wallet corrected, original realization visible."""
    headers = create_user_and_token(client, "t7fullrev", "t7fullrev@example.com", "Password123!")
    today = user_timezone_today()
    source = _source(client, headers)
    wallet = _wallet(client, headers)
    inflow = _create_earned(client, headers, source["id"], 1_000_000, today)

    def _wallet_balance(wallet_id):
        wallets = client.get("/wallets", headers=headers)
        assert wallets.status_code == 200
        return next(w["owned_balance"] for w in wallets.json() if w["id"] == wallet_id)

    # Capture wallet balance before receipt.
    balance_before = _wallet_balance(wallet["id"])

    # Receive full amount → should auto-close.
    realized = client.post(
        f"/expected-inflows/{inflow['id']}/realize",
        json={
            "actual_amount": 1_000_000,
            "received_date": today.isoformat(),
            "wallet_allocations": [{"wallet_id": wallet["id"], "amount": 1_000_000}],
            "idempotency_key": "t7-full-receipt",
        },
        headers=headers,
    )
    assert realized.status_code == 200, realized.text
    after_receipt = realized.json()["inflows"][0]
    assert after_receipt["status"] == "CLOSED"
    assert after_receipt["display_state"] == "FULLY_RECEIVED"
    assert after_receipt["outstanding_amount"] == 0

    # Wallet balance increased by 1,000,000.
    assert _wallet_balance(wallet["id"]) == balance_before + 1_000_000

    realization_id = after_receipt["realizations"][0]["id"]

    # Reverse the receipt.
    reversed_resp = client.post(
        f"/expected-inflows/{inflow['id']}/realizations/{realization_id}/reverse",
        json={"note": "Posted to wrong contract"},
        headers=headers,
    )
    assert reversed_resp.status_code == 200, reversed_resp.text
    reversed_data = reversed_resp.json()
    assert reversed_data["status"] == "OPEN"
    assert reversed_data["display_state"] == "EXPECTED"
    assert reversed_data["outstanding_amount"] == 1_000_000
    assert reversed_data["received_amount"] == 0

    # Wallet balance restored to pre-receipt level.
    assert _wallet_balance(wallet["id"]) == balance_before

    # Original realization is preserved as history.
    assert len(reversed_data["realizations"]) == 1
    orig = reversed_data["realizations"][0]
    assert orig["actual_amount"] == 1_000_000
    assert orig["reversed_at"] is not None
    assert orig["reversal_note"] == "Posted to wrong contract"

    # Activity includes both RECEIVED and RECEIPT_REVERSED.
    activity_types = {item["activity_type"] for item in reversed_data["activity"]}
    assert "RECEIVED" in activity_types
    assert "RECEIPT_REVERSED" in activity_types


def test_partial_receipt_reversal_recalculates_math_correctly(client):
    """Reverse part of a multi-receipt scenario — schedule/Promise math recalculates."""
    headers = create_user_and_token(client, "t7partial", "t7partial@example.com", "Password123!")
    today = user_timezone_today()
    source = _source(client, headers)
    wallet = _wallet(client, headers)
    inflow = _create_earned(client, headers, source["id"], 1_000_000, today)

    # First receipt: 400k.
    r1 = client.post(
        f"/expected-inflows/{inflow['id']}/realize",
        json={
            "actual_amount": 400_000,
            "received_date": today.isoformat(),
            "wallet_allocations": [{"wallet_id": wallet["id"], "amount": 400_000}],
            "idempotency_key": "t7-partial-1",
        },
        headers=headers,
    )
    assert r1.status_code == 200, r1.text

    # Second receipt: 200k.
    r2 = client.post(
        f"/expected-inflows/{inflow['id']}/realize",
        json={
            "actual_amount": 200_000,
            "received_date": today.isoformat(),
            "wallet_allocations": [{"wallet_id": wallet["id"], "amount": 200_000}],
            "idempotency_key": "t7-partial-2",
        },
        headers=headers,
    )
    assert r2.status_code == 200, r2.text

    detail = client.get(f"/expected-inflows/{inflow['id']}", headers=headers)
    assert detail.json()["received_amount"] == 600_000
    assert detail.json()["outstanding_amount"] == 400_000

    # Reverse the first receipt.
    r1_id = detail.json()["realizations"][0]["id"]
    rev = client.post(
        f"/expected-inflows/{inflow['id']}/realizations/{r1_id}/reverse",
        json={"note": "Wrong amount"},
        headers=headers,
    )
    assert rev.status_code == 200, rev.text
    after = rev.json()
    assert after["received_amount"] == 200_000
    assert after["outstanding_amount"] == 800_000
    assert after["status"] == "OPEN"


def test_receipt_reversal_after_closure_auto_reopens(client):
    """Reversing the only receipt on a closed Promise reopens it."""
    headers = create_user_and_token(client, "t7reopen", "t7reopen@example.com", "Password123!")
    today = user_timezone_today()
    source = _source(client, headers)
    wallet = _wallet(client, headers)
    inflow = _create_earned(client, headers, source["id"], 500_000, today)

    # Receive exact amount → auto-close.
    client.post(
        f"/expected-inflows/{inflow['id']}/realize",
        json={
            "actual_amount": 500_000,
            "received_date": today.isoformat(),
            "wallet_allocations": [{"wallet_id": wallet["id"], "amount": 500_000}],
            "idempotency_key": "t7-auto-close",
        },
        headers=headers,
    )
    closed = client.get(f"/expected-inflows/{inflow['id']}", headers=headers)
    assert closed.json()["status"] == "CLOSED"

    # Reverse → auto-reopen.
    realization_id = closed.json()["realizations"][0]["id"]
    reopened = client.post(
        f"/expected-inflows/{inflow['id']}/realizations/{realization_id}/reverse",
        json={},
        headers=headers,
    )
    assert reopened.status_code == 200, reopened.text
    assert reopened.json()["status"] == "OPEN"


def test_receipt_reversal_blocks_already_reversed(client):
    """Cannot reverse a realization that was already reversed."""
    headers = create_user_and_token(client, "t7dup", "t7dup@example.com", "Password123!")
    today = user_timezone_today()
    source = _source(client, headers)
    wallet = _wallet(client, headers)
    inflow = _create_earned(client, headers, source["id"], 300_000, today)

    realized = client.post(
        f"/expected-inflows/{inflow['id']}/realize",
        json={
            "actual_amount": 300_000,
            "received_date": today.isoformat(),
            "wallet_allocations": [{"wallet_id": wallet["id"], "amount": 300_000}],
            "idempotency_key": "t7-dup-key",
        },
        headers=headers,
    )
    assert realized.status_code == 200, realized.text
    detail = client.get(f"/expected-inflows/{inflow['id']}", headers=headers)
    assert len(detail.json()["realizations"]) >= 1
    realization_id = detail.json()["realizations"][0]["id"]

    # First reversal succeeds.
    r1 = client.post(
        f"/expected-inflows/{inflow['id']}/realizations/{realization_id}/reverse",
        json={},
        headers=headers,
    )
    assert r1.status_code == 200, r1.text

    # Second reversal is rejected.
    r2 = client.post(
        f"/expected-inflows/{inflow['id']}/realizations/{realization_id}/reverse",
        json={},
        headers=headers,
    )
    assert r2.status_code == 409


def test_receipt_reversal_not_found_for_wrong_ids(client):
    """404 when realization doesn't belong to the promise or doesn't exist."""
    headers = create_user_and_token(client, "t7nf", "t7nf@example.com", "Password123!")
    today = user_timezone_today()
    source = _source(client, headers)
    wallet = _wallet(client, headers)

    inflow1 = _create_earned(client, headers, source["id"], 100_000, today)
    inflow2 = _create_earned(client, headers, source["id"], 200_000, today)

    realized = client.post(
        f"/expected-inflows/{inflow1['id']}/realize",
        json={
            "actual_amount": 100_000,
            "received_date": today.isoformat(),
            "wallet_allocations": [{"wallet_id": wallet["id"], "amount": 100_000}],
            "idempotency_key": "t7-nf-key1",
        },
        headers=headers,
    )
    assert realized.status_code == 200, realized.text
    detail = client.get(f"/expected-inflows/{inflow1['id']}", headers=headers)
    assert len(detail.json()["realizations"]) >= 1
    real_id = detail.json()["realizations"][0]["id"]

    # Try to reverse realization of inflow1 under inflow2's id.
    wrong = client.post(
        f"/expected-inflows/{inflow2['id']}/realizations/{real_id}/reverse",
        json={},
        headers=headers,
    )
    assert wrong.status_code == 404

    # Try a non-existent realization id.
    bogus = client.post(
        f"/expected-inflows/{inflow1['id']}/realizations/99999/reverse",
        json={},
        headers=headers,
    )
    assert bogus.status_code == 404


# ---------------------------------------------------------------------------
# Ticket 8: Write-off reversal preserves append-only history
# ---------------------------------------------------------------------------


def test_write_off_reversal_preserves_original_write_off_in_history(client):
    """After reversal the original write-off is still visible with original data."""
    headers = create_user_and_token(client, "t8history", "t8history@example.com", "Password123!")
    today = user_timezone_today()
    source = _source(client, headers)
    inflow = _create_earned(client, headers, source["id"], 500_000, today)

    wo = client.post(
        f"/expected-inflows/{inflow['id']}/write-off",
        json={"amount": 150_000, "reason": "Client insolvent", "written_off_date": today.isoformat()},
        headers=headers,
    )
    assert wo.status_code == 200, wo.text
    wo_data = wo.json()
    assert wo_data["written_off_amount"] == 150_000
    write_off_id = wo_data["write_offs"][0]["id"]

    rev = client.post(
        f"/expected-inflows/{inflow['id']}/write-offs/{write_off_id}/reverse",
        json={"note": "Client paid later"},
        headers=headers,
    )
    assert rev.status_code == 200, rev.text
    rev_data = rev.json()
    assert rev_data["written_off_amount"] == 0

    # Original write-off still present with its fields intact.
    assert len(rev_data["write_offs"]) == 1
    orig_wo = rev_data["write_offs"][0]
    assert orig_wo["amount"] == 150_000
    assert orig_wo["reason"] == "Client insolvent"
    assert orig_wo["reversed_at"] is not None
    assert orig_wo["reversal_note"] == "Client paid later"

    # Activity contains both WRITTEN_OFF and WRITE_OFF_REVERSED.
    activity_types = {item["activity_type"] for item in rev_data["activity"]}
    assert "WRITTEN_OFF" in activity_types
    assert "WRITE_OFF_REVERSED" in activity_types


def test_write_off_reversal_reopens_closed_promise(client):
    """Reversing a write-off that closed the Promise reopens it."""
    headers = create_user_and_token(client, "t8reopen", "t8reopen@example.com", "Password123!")
    today = user_timezone_today()
    source = _source(client, headers)
    inflow = _create_earned(client, headers, source["id"], 300_000, today)

    # Write off full amount → auto-close.
    wo = client.post(
        f"/expected-inflows/{inflow['id']}/write-off",
        json={"amount": 300_000, "reason": "Lost cause", "written_off_date": today.isoformat()},
        headers=headers,
    )
    assert wo.status_code == 200, wo.text
    assert wo.json()["status"] == "CLOSED"
    assert wo.json()["display_state"] == "WRITTEN_OFF"

    write_off_id = wo.json()["write_offs"][0]["id"]
    rev = client.post(
        f"/expected-inflows/{inflow['id']}/write-offs/{write_off_id}/reverse",
        json={},
        headers=headers,
    )
    assert rev.status_code == 200, rev.text
    assert rev.json()["status"] == "OPEN"
    assert rev.json()["display_state"] == "EXPECTED"
    assert rev.json()["outstanding_amount"] == 300_000


def test_write_off_reversal_prevents_double_reversal(client):
    """Reversing the same write-off twice is rejected."""
    headers = create_user_and_token(client, "t8double", "t8double@example.com", "Password123!")
    today = user_timezone_today()
    source = _source(client, headers)
    inflow = _create_earned(client, headers, source["id"], 200_000, today)

    wo = client.post(
        f"/expected-inflows/{inflow['id']}/write-off",
        json={"amount": 50_000, "reason": "Disputed", "written_off_date": today.isoformat()},
        headers=headers,
    )
    write_off_id = wo.json()["write_offs"][0]["id"]

    r1 = client.post(
        f"/expected-inflows/{inflow['id']}/write-offs/{write_off_id}/reverse",
        json={},
        headers=headers,
    )
    assert r1.status_code == 200

    r2 = client.post(
        f"/expected-inflows/{inflow['id']}/write-offs/{write_off_id}/reverse",
        json={},
        headers=headers,
    )
    assert r2.status_code == 409


def test_write_off_reversal_after_mixed_settlement(client):
    """Reversing a write-off in a mixed settlement restores correct math."""
    headers = create_user_and_token(client, "t8mixed", "t8mixed@example.com", "Password123!")
    today = user_timezone_today()
    source = _source(client, headers)
    wallet = _wallet(client, headers)
    inflow = _create_earned(client, headers, source["id"], 600_000, today)

    # Receive 400k.
    client.post(
        f"/expected-inflows/{inflow['id']}/realize",
        json={
            "actual_amount": 400_000,
            "received_date": today.isoformat(),
            "wallet_allocations": [{"wallet_id": wallet["id"], "amount": 400_000}],
            "idempotency_key": "t8-mixed-receipt",
        },
        headers=headers,
    )
    # Write off the remaining 200k → mixed settlement.
    wo = client.post(
        f"/expected-inflows/{inflow['id']}/write-off",
        json={"amount": 200_000, "reason": "Balance forgiven", "written_off_date": today.isoformat()},
        headers=headers,
    )
    assert wo.status_code == 200, wo.text
    assert wo.json()["status"] == "CLOSED"
    assert wo.json()["display_state"] == "SETTLED"
    assert wo.json()["received_amount"] == 400_000
    assert wo.json()["written_off_amount"] == 200_000
    assert wo.json()["outstanding_amount"] == 0

    # Reverse the write-off.
    write_off_id = wo.json()["write_offs"][0]["id"]
    rev = client.post(
        f"/expected-inflows/{inflow['id']}/write-offs/{write_off_id}/reverse",
        json={"note": "Customer will pay after all"},
        headers=headers,
    )
    assert rev.status_code == 200, rev.text
    assert rev.json()["status"] == "OPEN"
    assert rev.json()["display_state"] == "EXPECTED"
    assert rev.json()["written_off_amount"] == 0
    assert rev.json()["outstanding_amount"] == 200_000
    assert rev.json()["received_amount"] == 400_000


def test_receipt_then_write_off_then_reverse_both_in_any_order(client):
    """Receipt + write-off can be reversed in any order (ADR 0014)."""
    headers = create_user_and_token(client, "t8anyorder", "t8anyorder@example.com", "Password123!")
    today = user_timezone_today()
    source = _source(client, headers)
    wallet = _wallet(client, headers)
    inflow = _create_earned(client, headers, source["id"], 500_000, today)

    # Receive 300k.
    r = client.post(
        f"/expected-inflows/{inflow['id']}/realize",
        json={
            "actual_amount": 300_000,
            "received_date": today.isoformat(),
            "wallet_allocations": [{"wallet_id": wallet["id"], "amount": 300_000}],
            "idempotency_key": "t8-order-receipt",
        },
        headers=headers,
    )
    assert r.status_code == 200, r.text

    # Write off 100k.
    wo = client.post(
        f"/expected-inflows/{inflow['id']}/write-off",
        json={"amount": 100_000, "reason": "Partial dispute", "written_off_date": today.isoformat()},
        headers=headers,
    )
    assert wo.status_code == 200, wo.text

    detail = client.get(f"/expected-inflows/{inflow['id']}", headers=headers)
    assert detail.json()["outstanding_amount"] == 100_000
    assert detail.json()["status"] == "OPEN"

    # Reverse write-off first (while receipt still stands).
    rev_wo = client.post(
        f"/expected-inflows/{inflow['id']}/write-offs/{wo.json()['write_offs'][0]['id']}/reverse",
        json={},
        headers=headers,
    )
    assert rev_wo.status_code == 200, rev_wo.text
    assert rev_wo.json()["written_off_amount"] == 0
    assert rev_wo.json()["outstanding_amount"] == 200_000

    # Then reverse receipt.
    rev_r = client.post(
        f"/expected-inflows/{inflow['id']}/realizations/{r.json()['inflows'][0]['realizations'][0]['id']}/reverse",
        json={},
        headers=headers,
    )
    assert rev_r.status_code == 200, rev_r.text
    assert rev_r.json()["received_amount"] == 0
    assert rev_r.json()["outstanding_amount"] == 500_000
    assert rev_r.json()["status"] == "OPEN"


# ---------------------------------------------------------------------------
# Ticket 9: Leaves-only reschedule reversal
# ---------------------------------------------------------------------------


def test_reverse_simple_one_child_reschedule(client):
    """Reschedule with one replacement child can be reversed."""
    headers = create_user_and_token(client, "t9simple", "t9simple@example.com", "Password123!")
    today = user_timezone_today()
    source = _source(client, headers)
    inflow = _create_earned(client, headers, source["id"], 500_000, today)

    # Find the only active schedule (created by _create_earned).
    detail = client.get(f"/expected-inflows/{inflow['id']}", headers=headers)
    schedule_id = detail.json()["schedules"][0]["id"]

    # Reschedule to a future date.
    future = _month_date(today, 1)
    rescheduled = client.post(
        f"/expected-inflows/{inflow['id']}/reschedule",
        json={
            "source_schedule_id": schedule_id,
            "allocations": [{"amount": 500_000, "due_date": future.isoformat()}],
        },
        headers=headers,
    )
    assert rescheduled.status_code == 200, rescheduled.text
    result = rescheduled.json()
    assert result["source"]["is_rescheduled"] is True
    assert len(result["replacements"]) == 1

    # Reverse the reschedule.
    rev = client.post(
        f"/expected-inflows/{inflow['id']}/reschedules/{schedule_id}/reverse",
        headers=headers,
    )
    assert rev.status_code == 200, rev.text
    after = rev.json()
    # Source schedule is restored — should be EXPECTED/active again.
    source_schedule = next(s for s in after["schedules"] if s["id"] == schedule_id)
    assert source_schedule["read_state"] == "OUTSTANDING"
    # Child is closed with RESCHEDULE_REVERSED reason.
    child = next(s for s in after["schedules"] if s["parent_id"] == schedule_id)
    assert child["close_reason"] == "RESCHEDULE_REVERSED"
    assert child["is_active"] is False


def test_reverse_multi_child_untouched_reschedule(client):
    """Multi-child reschedule can be reversed when all children are untouched."""
    headers = create_user_and_token(client, "t9multi", "t9multi@example.com", "Password123!")
    today = user_timezone_today()
    source = _source(client, headers)
    inflow = _create_earned(client, headers, source["id"], 600_000, today)

    detail = client.get(f"/expected-inflows/{inflow['id']}", headers=headers)
    schedule_id = detail.json()["schedules"][0]["id"]

    future1 = _month_date(today, 1)
    future2 = _month_date(today, 2)
    rescheduled = client.post(
        f"/expected-inflows/{inflow['id']}/reschedule",
        json={
            "source_schedule_id": schedule_id,
            "allocations": [
                {"amount": 300_000, "due_date": future1.isoformat()},
                {"amount": 300_000, "due_date": future2.isoformat()},
            ],
        },
        headers=headers,
    )
    assert rescheduled.status_code == 200, rescheduled.text
    assert len(rescheduled.json()["replacements"]) == 2

    rev = client.post(
        f"/expected-inflows/{inflow['id']}/reschedules/{schedule_id}/reverse",
        headers=headers,
    )
    assert rev.status_code == 200, rev.text
    after = rev.json()
    source_schedule = next(s for s in after["schedules"] if s["id"] == schedule_id)
    assert source_schedule["read_state"] == "OUTSTANDING"


def test_reschedule_reversal_blocked_by_child_receipt(client):
    """Cannot reverse when a child has received money."""
    headers = create_user_and_token(client, "t9blocked", "t9blocked@example.com", "Password123!")
    today = user_timezone_today()
    source = _source(client, headers)
    wallet = _wallet(client, headers)
    inflow = _create_earned(client, headers, source["id"], 400_000, today)

    detail = client.get(f"/expected-inflows/{inflow['id']}", headers=headers)
    schedule_id = detail.json()["schedules"][0]["id"]

    future = _month_date(today, 1)
    rescheduled = client.post(
        f"/expected-inflows/{inflow['id']}/reschedule",
        json={
            "source_schedule_id": schedule_id,
            "allocations": [{"amount": 400_000, "due_date": future.isoformat()}],
        },
        headers=headers,
    )
    assert rescheduled.status_code == 200, rescheduled.text
    child_id = rescheduled.json()["replacements"][0]["id"]

    # Receive against the child.
    realized = client.post(
        f"/expected-inflows/{inflow['id']}/realize",
        json={
            "actual_amount": 100_000,
            "received_date": today.isoformat(),
            "wallet_allocations": [{"wallet_id": wallet["id"], "amount": 100_000}],
            "schedule_allocations": [{"schedule_id": child_id, "amount": 100_000}],
            "idempotency_key": "t9-blocked",
        },
        headers=headers,
    )
    assert realized.status_code == 200, realized.text

    # Reversal is blocked.
    rev = client.post(
        f"/expected-inflows/{inflow['id']}/reschedules/{schedule_id}/reverse",
        headers=headers,
    )
    assert rev.status_code == 409


def test_reschedule_reversal_blocked_by_child_write_off(client):
    """Cannot reverse when a child has been written off."""
    headers = create_user_and_token(client, "t9woff", "t9woff@example.com", "Password123!")
    today = user_timezone_today()
    source = _source(client, headers)
    inflow = _create_earned(client, headers, source["id"], 300_000, today)

    detail = client.get(f"/expected-inflows/{inflow['id']}", headers=headers)
    schedule_id = detail.json()["schedules"][0]["id"]

    future = _month_date(today, 1)
    rescheduled = client.post(
        f"/expected-inflows/{inflow['id']}/reschedule",
        json={
            "source_schedule_id": schedule_id,
            "allocations": [{"amount": 300_000, "due_date": future.isoformat()}],
        },
        headers=headers,
    )
    assert rescheduled.status_code == 200, rescheduled.text
    child_id = rescheduled.json()["replacements"][0]["id"]

    # Write off against the child.
    wo = client.post(
        f"/expected-inflows/{inflow['id']}/write-off",
        json={
            "amount": 100_000,
            "reason": "Disputed",
            "written_off_date": today.isoformat(),
            "schedule_allocations": [{"schedule_id": child_id, "amount": 100_000}],
        },
        headers=headers,
    )
    assert wo.status_code == 200, wo.text

    # Reversal is blocked.
    rev = client.post(
        f"/expected-inflows/{inflow['id']}/reschedules/{schedule_id}/reverse",
        headers=headers,
    )
    assert rev.status_code == 409


def test_reschedule_reversal_blocked_by_child_reschedule(client):
    """Cannot reverse when a child has been rescheduled again."""
    headers = create_user_and_token(client, "t9childres", "t9childres@example.com", "Password123!")
    today = user_timezone_today()
    source = _source(client, headers)
    inflow = _create_earned(client, headers, source["id"], 500_000, today)

    detail = client.get(f"/expected-inflows/{inflow['id']}", headers=headers)
    schedule_id = detail.json()["schedules"][0]["id"]

    future = _month_date(today, 1)
    rescheduled = client.post(
        f"/expected-inflows/{inflow['id']}/reschedule",
        json={
            "source_schedule_id": schedule_id,
            "allocations": [{"amount": 500_000, "due_date": future.isoformat()}],
        },
        headers=headers,
    )
    assert rescheduled.status_code == 200, rescheduled.text
    child_id = rescheduled.json()["replacements"][0]["id"]

    # Reschedule the child again.
    future2 = _month_date(today, 2)
    r2 = client.post(
        f"/expected-inflows/{inflow['id']}/reschedule",
        json={
            "source_schedule_id": child_id,
            "allocations": [{"amount": 500_000, "due_date": future2.isoformat()}],
        },
        headers=headers,
    )
    assert r2.status_code == 200, r2.text

    # Reversal of the original reschedule is blocked.
    rev = client.post(
        f"/expected-inflows/{inflow['id']}/reschedules/{schedule_id}/reverse",
        headers=headers,
    )
    assert rev.status_code == 409


# ---------------------------------------------------------------------------
# Ticket 11: Harden budget backing, timezone, and source-kind coverage
# ---------------------------------------------------------------------------


def test_budget_backing_excludes_superseded_schedules(client, session):
    """After rescheduling, the superseded schedule no longer backs the budget."""
    headers = create_user_and_token(client, "t11sup", "t11sup@example.com", "Password123!")
    today = user_timezone_today()
    source = _source(client, headers)
    inflow = _create_earned(client, headers, source["id"], 500_000, today)

    # Initial backing = full amount.
    summary = client.get(
        f"/budgets/month-summary?budget_year={today.year}&budget_month={today.month}",
        headers=headers,
    )
    assert summary.status_code == 200, summary.text
    assert summary.json()["expected_income_remaining"] == 500_000

    # Reschedule to next month.
    detail = client.get(f"/expected-inflows/{inflow['id']}", headers=headers)
    schedule_id = detail.json()["schedules"][0]["id"]
    future = _month_date(today, 1)
    rescheduled = client.post(
        f"/expected-inflows/{inflow['id']}/reschedule",
        json={
            "source_schedule_id": schedule_id,
            "allocations": [{"amount": 500_000, "due_date": future.isoformat()}],
        },
        headers=headers,
    )
    assert rescheduled.status_code == 200, rescheduled.text

    # Current month backing is now 0 (superseded schedule excluded).
    summary_after = client.get(
        f"/budgets/month-summary?budget_year={today.year}&budget_month={today.month}",
        headers=headers,
    )
    assert summary_after.status_code == 200, summary_after.text
    assert summary_after.json()["expected_income_remaining"] == 0

    # Future month backing shows the replacement.
    future_summary = client.get(
        f"/budgets/month-summary?budget_year={future.year}&budget_month={future.month}",
        headers=headers,
    )
    assert future_summary.status_code == 200, future_summary.text
    assert future_summary.json()["expected_income_remaining"] == 500_000


def test_budget_backing_excludes_written_off_amounts(client, session):
    """After a write-off, backing excludes the written-off portion."""
    headers = create_user_and_token(client, "t11woff", "t11woff@example.com", "Password123!")
    today = user_timezone_today()
    source = _source(client, headers)
    inflow = _create_earned(client, headers, source["id"], 400_000, today)

    # Write off 150k.
    client.post(
        f"/expected-inflows/{inflow['id']}/write-off",
        json={"amount": 150_000, "reason": "Partial dispute", "written_off_date": today.isoformat()},
        headers=headers,
    )
    summary = client.get(
        f"/budgets/month-summary?budget_year={today.year}&budget_month={today.month}",
        headers=headers,
    )
    assert summary.status_code == 200, summary.text
    # Backing = original - written off = 250k.
    assert summary.json()["expected_income_remaining"] == 250_000


def test_budget_backing_excludes_closed_promise_amounts(client, session):
    """After full receipt closes the Promise, backing drops to zero."""
    headers = create_user_and_token(client, "t11closed", "t11closed@example.com", "Password123!")
    today = user_timezone_today()
    source = _source(client, headers)
    wallet = _wallet(client, headers)
    inflow = _create_earned(client, headers, source["id"], 300_000, today)

    # Full receipt → auto-close.
    client.post(
        f"/expected-inflows/{inflow['id']}/realize",
        json={
            "actual_amount": 300_000,
            "received_date": today.isoformat(),
            "wallet_allocations": [{"wallet_id": wallet["id"], "amount": 300_000}],
            "idempotency_key": "t11-closed-receipt",
        },
        headers=headers,
    )
    summary = client.get(
        f"/budgets/month-summary?budget_year={today.year}&budget_month={today.month}",
        headers=headers,
    )
    assert summary.status_code == 200, summary.text
    assert summary.json()["expected_income_remaining"] == 0


def test_receivable_receipt_reversal_preserves_debt_effects(client, session):
    """Reversing a receivable receipt correctly recalculates Promise math.

    The receivable source kind follows the same Promise cap and reversal
    rules as earned income. Debt balance restoration is handled by the
    debt domain's own reversal mechanism (called via void_financial_event).
    """
    headers = create_user_and_token(client, "t11recv", "t11recv@example.com", "Password123!")
    today = user_timezone_today()
    wallet = _wallet(client, headers)

    # Create an OWED debt (receivable).
    debt_resp = client.post(
        "/debts",
        json={
            "debt_type": "OWED",
            "counterparty_name": "Test debtor",
            "initial_amount": 1_000_000,
            "origin_kind": "IMPORTED_BALANCE",
            "currency": "UZS",
            "date": today.isoformat(),
            "expected_return_date": today.isoformat(),
            "is_money_transferred": False,
        },
        headers=headers,
    )
    assert debt_resp.status_code == 201, debt_resp.text
    debt = debt_resp.json()

    inflow = client.post(
        "/expected-inflows",
        json={
            "kind": "RECEIVABLE",
            "debt_id": debt["id"],
            "amount": 500_000,
            "due_date": today.isoformat(),
        },
        headers=headers,
    )
    assert inflow.status_code == 201, inflow.text
    inflow_data = inflow.json()

    # Receive 300k of the receivable.
    r = client.post(
        f"/expected-inflows/{inflow_data['id']}/realize",
        json={
            "actual_amount": 300_000,
            "received_date": today.isoformat(),
            "wallet_allocations": [{"wallet_id": wallet["id"], "amount": 300_000}],
            "idempotency_key": "t11-recv-receipt",
        },
        headers=headers,
    )
    assert r.status_code == 200, r.text
    after_receipt = r.json()["inflows"][0]
    assert after_receipt["received_amount"] == 300_000
    assert after_receipt["outstanding_amount"] == 200_000

    # Reverse the receipt — Promise math recalculates correctly.
    realization_id = after_receipt["realizations"][0]["id"]
    rev = client.post(
        f"/expected-inflows/{inflow_data['id']}/realizations/{realization_id}/reverse",
        json={},
        headers=headers,
    )
    assert rev.status_code == 200, rev.text
    assert rev.json()["received_amount"] == 0
    assert rev.json()["outstanding_amount"] == 500_000
    assert rev.json()["status"] == "OPEN"


def test_refund_receipt_reversal_preserves_refund_links(client, session):
    """Reversing a refund receipt preserves the refund event linkage."""
    headers = create_user_and_token(client, "t11refund", "t11refund@example.com", "Password123!")
    today = user_timezone_today()
    wallet = _wallet(client, headers)
    create_budget(client, headers, category="Electronics", monthly_limit=1_000_000)

    # Create an expense to refund against.
    expense = client.post(
        "/expenses",
        json={
            "title": "Refundable purchase",
            "amount": 200_000,
            "category": "Electronics",
            "date": today.isoformat(),
            "wallet_id": wallet["id"],
        },
        headers=headers,
    )
    assert expense.status_code == 201, expense.text
    event_id = expense.json()["id"]

    inflow = client.post(
        "/expected-inflows",
        json={
            "kind": "REFUND",
            "refund_event_id": event_id,
            "amount": 150_000,
            "due_date": today.isoformat(),
        },
        headers=headers,
    )
    assert inflow.status_code == 201, inflow.text
    inflow_data = inflow.json()

    # Receive the refund.
    r = client.post(
        f"/expected-inflows/{inflow_data['id']}/realize",
        json={
            "actual_amount": 150_000,
            "received_date": today.isoformat(),
            "wallet_allocations": [{"wallet_id": wallet["id"], "amount": 150_000}],
            "idempotency_key": "t11-refund-receipt",
        },
        headers=headers,
    )
    assert r.status_code == 200, r.text

    # Reverse the receipt.
    realization_id = r.json()["inflows"][0]["realizations"][0]["id"]
    rev = client.post(
        f"/expected-inflows/{inflow_data['id']}/realizations/{realization_id}/reverse",
        json={},
        headers=headers,
    )
    assert rev.status_code == 200, rev.text
    # Refund link preserved — the inflow still references the original event.
    assert rev.json()["refund_event_id"] == event_id


def test_asset_sale_reversal_preserves_asset_and_math(client, session):
    """Reversing an asset-sale receipt restores outstanding correctly."""
    headers = create_user_and_token(client, "t11asset", "t11asset@example.com", "Password123!")
    today = user_timezone_today()
    wallet = _wallet(client, headers)

    asset = client.post(
        "/assets",
        json={
            "title": "Old laptop",
            "purchase_value": 300_000,
            "current_value": 300_000,
            "status": "owned",
        },
        headers=headers,
    )
    assert asset.status_code == 201, asset.text

    inflow = client.post(
        "/expected-inflows",
        json={
            "kind": "ASSET_SALE",
            "asset_id": asset.json()["id"],
            "amount": 250_000,
            "due_date": today.isoformat(),
        },
        headers=headers,
    )
    assert inflow.status_code == 201, inflow.text
    inflow_data = inflow.json()

    # Receive the asset sale.
    r = client.post(
        f"/expected-inflows/{inflow_data['id']}/realize",
        json={
            "actual_amount": 250_000,
            "received_date": today.isoformat(),
            "wallet_allocations": [{"wallet_id": wallet["id"], "amount": 250_000}],
            "idempotency_key": "t11-asset-receipt",
        },
        headers=headers,
    )
    assert r.status_code == 200, r.text

    # Reverse the receipt.
    realization_id = r.json()["inflows"][0]["realizations"][0]["id"]
    rev = client.post(
        f"/expected-inflows/{inflow_data['id']}/realizations/{realization_id}/reverse",
        json={},
        headers=headers,
    )
    assert rev.status_code == 200, rev.text
    assert rev.json()["received_amount"] == 0
    assert rev.json()["outstanding_amount"] == 250_000


def test_timezone_due_overdue_uses_user_timezone(client):
    """Overdue flag respects the user's effective timezone."""
    headers = create_user_and_token(client, "t11tz", "t11tz@example.com", "Password123!")
    # create_user_and_token sets X-Timezone to TEST_TIMEZONE (Asia/Tashkent).
    today = user_timezone_today()
    source = _source(client, headers)

    # Create with today as due date — should NOT be overdue.
    inflow = _create_earned(client, headers, source["id"], 100_000, today)
    detail = client.get(f"/expected-inflows/{inflow['id']}", headers=headers)
    assert detail.json()["is_overdue"] is False

    # Create with yesterday as due date — should BE overdue.
    yesterday = today - __import__("datetime").timedelta(days=1)
    inflow2 = _create_earned(client, headers, source["id"], 100_000, yesterday)
    detail2 = client.get(f"/expected-inflows/{inflow2['id']}", headers=headers)
    assert detail2.json()["is_overdue"] is True


def test_pristine_promise_can_be_deleted_non_pristine_cannot(client):
    """Pristine (no activity) Promises can be deleted; non-pristine cannot."""
    headers = create_user_and_token(client, "t11del", "t11del@example.com", "Password123!")
    today = user_timezone_today()
    source = _source(client, headers)
    wallet = _wallet(client, headers)

    pristine = _create_earned(client, headers, source["id"], 100_000, today)
    # Pristine delete should work.
    del_resp = client.delete(f"/expected-inflows/{pristine['id']}", headers=headers)
    assert del_resp.status_code == 204

    non_pristine = _create_earned(client, headers, source["id"], 200_000, today)
    client.post(
        f"/expected-inflows/{non_pristine['id']}/realize",
        json={
            "actual_amount": 100_000,
            "received_date": today.isoformat(),
            "wallet_allocations": [{"wallet_id": wallet["id"], "amount": 100_000}],
            "idempotency_key": "t11-nonpristine-receipt",
        },
        headers=headers,
    )
    # Non-pristine delete should be rejected.
    del_resp2 = client.delete(f"/expected-inflows/{non_pristine['id']}", headers=headers)
    assert del_resp2.status_code == 409


# ---------------------------------------------------------------------------
# Ticket 12: End-to-end regression and documentation alignment
# ---------------------------------------------------------------------------


def test_end_to_end_full_lifecycle_all_display_states(client):
    """Full workflow: create → receive → reschedule → write-off → reverse all."""
    headers = create_user_and_token(client, "t12e2e", "t12e2e@example.com", "Password123!")
    today = user_timezone_today()
    source = _source(client, headers)
    wallet = _wallet(client, headers)

    # 1. Create → EXPECTED display state.
    inflow = client.post(
        "/expected-inflows",
        json={
            "kind": "EARNED",
            "source_id": source["id"],
            "amount": 1_000_000,
            "due_date": today.isoformat(),
        },
        headers=headers,
    )
    assert inflow.status_code == 201, inflow.text
    inflow_data = inflow.json()
    pid = inflow_data["id"]
    assert inflow_data["display_state"] == "EXPECTED"
    assert inflow_data["status"] == "OPEN"

    # 2. Partial receive → still EXPECTED (outstanding > 0).
    r1 = client.post(
        f"/expected-inflows/{pid}/realize",
        json={
            "actual_amount": 300_000,
            "received_date": today.isoformat(),
            "wallet_allocations": [{"wallet_id": wallet["id"], "amount": 300_000}],
            "idempotency_key": "t12-e2e-r1",
        },
        headers=headers,
    )
    assert r1.status_code == 200, r1.text

    # 3. Full receipt of remainder → FULLY_RECEIVED.
    r2 = client.post(
        f"/expected-inflows/{pid}/realize",
        json={
            "actual_amount": 700_000,
            "received_date": today.isoformat(),
            "wallet_allocations": [{"wallet_id": wallet["id"], "amount": 700_000}],
            "idempotency_key": "t12-e2e-r2",
        },
        headers=headers,
    )
    assert r2.status_code == 200, r2.text
    detail = client.get(f"/expected-inflows/{pid}", headers=headers)
    assert detail.json()["display_state"] == "FULLY_RECEIVED"
    assert detail.json()["status"] == "CLOSED"

    # 4. Reverse one receipt → back to EXPECTED (auto-reopen).
    r2_id = r2.json()["inflows"][0]["realizations"][1]["id"]
    client.post(
        f"/expected-inflows/{pid}/realizations/{r2_id}/reverse",
        json={"note": "Test reversal"},
        headers=headers,
    )
    detail = client.get(f"/expected-inflows/{pid}", headers=headers)
    assert detail.json()["status"] == "OPEN"
    assert detail.json()["display_state"] == "EXPECTED"

    # 5. Write off outstanding → SETTLED display.
    wo = client.post(
        f"/expected-inflows/{pid}/write-off",
        json={"amount": 700_000, "reason": "Final settlement", "written_off_date": today.isoformat()},
        headers=headers,
    )
    assert wo.status_code == 200, wo.text
    detail = client.get(f"/expected-inflows/{pid}", headers=headers)
    assert detail.json()["display_state"] == "SETTLED"
    assert detail.json()["status"] == "CLOSED"

    # 6. Reverse write-off → back to EXPECTED.
    wo_id = wo.json()["write_offs"][0]["id"]
    client.post(
        f"/expected-inflows/{pid}/write-offs/{wo_id}/reverse",
        json={"note": "Customer paid"},
        headers=headers,
    )
    detail = client.get(f"/expected-inflows/{pid}", headers=headers)
    assert detail.json()["status"] == "OPEN"
    assert detail.json()["display_state"] == "EXPECTED"

    # 7. Write off remaining to close → WRITTEN_OFF display.
    # First reverse the remaining receipt so we have only outstanding.
    r1_id = detail.json()["realizations"][0]["id"]
    if detail.json()["realizations"][0]["reversed_at"] is None:
        client.post(
            f"/expected-inflows/{pid}/realizations/{r1_id}/reverse",
            json={},
            headers=headers,
        )

    wo2 = client.post(
        f"/expected-inflows/{pid}/write-off",
        json={"amount": 1_000_000, "reason": "Full loss", "written_off_date": today.isoformat()},
        headers=headers,
    )
    assert wo2.status_code == 200, wo2.text
    detail = client.get(f"/expected-inflows/{pid}", headers=headers)
    assert detail.json()["display_state"] == "WRITTEN_OFF"
    assert detail.json()["status"] == "CLOSED"


def test_end_to_end_reschedule_reverse_workflow(client):
    """Create → reschedule → verify superseded → reverse → verify restored."""
    headers = create_user_and_token(client, "t12res", "t12res@example.com", "Password123!")
    today = user_timezone_today()
    source = _source(client, headers)
    inflow = _create_earned(client, headers, source["id"], 500_000, today)

    detail = client.get(f"/expected-inflows/{inflow['id']}", headers=headers)
    schedule_id = detail.json()["schedules"][0]["id"]

    # Reschedule.
    future = _month_date(today, 1)
    res = client.post(
        f"/expected-inflows/{inflow['id']}/reschedule",
        json={
            "source_schedule_id": schedule_id,
            "allocations": [{"amount": 500_000, "due_date": future.isoformat()}],
        },
        headers=headers,
    )
    assert res.status_code == 200, res.text
    detail_after = client.get(f"/expected-inflows/{inflow['id']}", headers=headers)
    source_sched = next(s for s in detail_after.json()["schedules"] if s["id"] == schedule_id)
    assert source_sched["read_state"] == "SUPERSEDED"

    # Reverse the reschedule.
    rev = client.post(
        f"/expected-inflows/{inflow['id']}/reschedules/{schedule_id}/reverse",
        headers=headers,
    )
    assert rev.status_code == 200, rev.text
    detail_final = client.get(f"/expected-inflows/{inflow['id']}", headers=headers)
    source_sched2 = next(s for s in detail_final.json()["schedules"] if s["id"] == schedule_id)
    assert source_sched2["read_state"] == "OUTSTANDING"
    assert source_sched2["is_active"] is True


def test_cannot_over_receive_above_promise_cap(client):
    """Receipts above original amount are always rejected."""
    headers = create_user_and_token(client, "t12cap", "t12cap@example.com", "Password123!")
    today = user_timezone_today()
    source = _source(client, headers)
    wallet = _wallet(client, headers)
    inflow = _create_earned(client, headers, source["id"], 500_000, today)

    # Partial receipt then over-receipt — both rejected.
    client.post(
        f"/expected-inflows/{inflow['id']}/realize",
        json={
            "actual_amount": 300_000,
            "received_date": today.isoformat(),
            "wallet_allocations": [{"wallet_id": wallet["id"], "amount": 300_000}],
            "idempotency_key": "t12-cap-1",
        },
        headers=headers,
    )
    # Try to receive 300k more (would be 600k total on 500k cap).
    over = client.post(
        f"/expected-inflows/{inflow['id']}/realize",
        json={
            "actual_amount": 300_000,
            "received_date": today.isoformat(),
            "wallet_allocations": [{"wallet_id": wallet["id"], "amount": 300_000}],
            "idempotency_key": "t12-cap-2",
        },
        headers=headers,
    )
    assert over.status_code == 400


def test_non_pristine_schedule_data_preserved_in_history(client):
    """History remains intact through complex workflows — no hard deletion."""
    headers = create_user_and_token(client, "t12hist", "t12hist@example.com", "Password123!")
    today = user_timezone_today()
    source = _source(client, headers)
    wallet = _wallet(client, headers)
    inflow = _create_earned(client, headers, source["id"], 500_000, today)
    pid = inflow["id"]

    # Perform: receive → write-off → reverse both.
    client.post(
        f"/expected-inflows/{pid}/realize",
        json={
            "actual_amount": 200_000,
            "received_date": today.isoformat(),
            "wallet_allocations": [{"wallet_id": wallet["id"], "amount": 200_000}],
            "idempotency_key": "t12-hist-r",
        },
        headers=headers,
    )
    wo = client.post(
        f"/expected-inflows/{pid}/write-off",
        json={"amount": 100_000, "reason": "Disputed", "written_off_date": today.isoformat()},
        headers=headers,
    )
    assert wo.status_code == 200, wo.text

    detail = client.get(f"/expected-inflows/{pid}", headers=headers)
    data = detail.json()

    # Verify all history is present: creation, receipt, write-off.
    activity_types = {a["activity_type"] for a in data["activity"]}
    assert "CREATED" in activity_types
    assert "RECEIVED" in activity_types
    assert "WRITTEN_OFF" in activity_types

    # Realizations preserved.
    assert len(data["realizations"]) >= 1
    # Write-offs preserved.
    assert len(data["write_offs"]) >= 1
    # Schedules preserved.
    assert len(data["schedules"]) >= 1


# ---------------------------------------------------------------------------
# Ticket 1: Ledger identity — Promise title is the primary ledger title
# ---------------------------------------------------------------------------


def test_earned_receipt_title_equals_promise_title(client, session):
    """Receiving an earned Expected Inflow posts Money In with the Promise title."""
    headers = create_user_and_token(client, "t1earned", "t1earned@example.com", "Password123!")
    today = user_timezone_today()
    source = _source(client, headers, "Freelance client")
    wallet = _wallet(client, headers)

    inflow = client.post(
        "/expected-inflows",
        json={
            "kind": "EARNED",
            "source_id": source["id"],
            "title": "Website redesign — phase 1",
            "amount": 500_000,
            "due_date": today.isoformat(),
        },
        headers=headers,
    )
    assert inflow.status_code == 201, inflow.text
    assert inflow.json()["title"] == "Website redesign — phase 1"

    realized = client.post(
        f"/expected-inflows/{inflow.json()['id']}/realize",
        json={
            "actual_amount": 500_000,
            "received_date": today.isoformat(),
            "wallet_allocations": [{"wallet_id": wallet["id"], "amount": 500_000}],
            "idempotency_key": "t1-earned-title",
        },
        headers=headers,
    )
    assert realized.status_code == 200, realized.text
    event_id = realized.json()["realization"]["event_ids"][0]
    event = session.query(models.FinancialEvent).filter(models.FinancialEvent.id == event_id).first()
    assert event.title == "Website redesign — phase 1"
    # Source context is available through entity leg, not the title.
    entity_leg = session.query(models.EntityLedger).filter(
        models.EntityLedger.event_id == event_id,
    ).first()
    assert entity_leg.income_source_id == source["id"]


def test_receivable_receipt_title_equals_promise_title(client, session):
    """Receiving a receivable Expected Inflow posts Money In with the Promise title."""
    headers = create_user_and_token(client, "t1recv", "t1recv@example.com", "Password123!")
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
            "expected_return_date": today.isoformat(),
            "is_money_transferred": False,
        },
        headers=headers,
    )
    assert debt.status_code == 201, debt.text

    inflow = client.post(
        "/expected-inflows",
        json={
            "kind": "RECEIVABLE",
            "debt_id": debt.json()["id"],
            "title": "Ali repayment — March",
            "amount": 300_000,
            "due_date": today.isoformat(),
        },
        headers=headers,
    )
    assert inflow.status_code == 201, inflow.text
    assert inflow.json()["title"] == "Ali repayment — March"

    realized = client.post(
        f"/expected-inflows/{inflow.json()['id']}/realize",
        json={
            "actual_amount": 300_000,
            "received_date": today.isoformat(),
            "wallet_allocations": [{"wallet_id": wallet["id"], "amount": 300_000}],
            "idempotency_key": "t1-recv-title",
        },
        headers=headers,
    )
    assert realized.status_code == 200, realized.text
    for event_id in realized.json()["realization"]["event_ids"]:
        event = session.query(models.FinancialEvent).filter(models.FinancialEvent.id == event_id).first()
        assert event.title == "Ali repayment — March", f"Event {event_id} title mismatch"


def test_refund_receipt_title_equals_promise_title(client, session):
    """Receiving a refund Expected Inflow posts Money In with the Promise title,
    not with 'Refund' or 'Partial Refund'."""
    headers = create_user_and_token(client, "t1refund", "t1refund@example.com", "Password123!")
    today = user_timezone_today()
    wallet = _wallet(client, headers)
    create_budget(client, headers, category="Groceries", monthly_limit=1_000_000)

    expense = create_expense(client, headers, title="Returned groceries", amount=200_000, category="Groceries")
    assert expense.status_code == 201, expense.text

    inflow = client.post(
        "/expected-inflows",
        json={
            "kind": "REFUND",
            "refund_event_id": expense.json()["id"],
            "title": "Grocery refund — damaged items",
            "amount": 150_000,
            "due_date": today.isoformat(),
        },
        headers=headers,
    )
    assert inflow.status_code == 201, inflow.text

    realized = client.post(
        f"/expected-inflows/{inflow.json()['id']}/realize",
        json={
            "actual_amount": 150_000,
            "received_date": today.isoformat(),
            "wallet_allocations": [{"wallet_id": wallet["id"], "amount": 150_000}],
            "idempotency_key": "t1-refund-title",
        },
        headers=headers,
    )
    assert realized.status_code == 200, realized.text
    event_id = realized.json()["realization"]["event_ids"][0]
    event = session.query(models.FinancialEvent).filter(models.FinancialEvent.id == event_id).first()
    # Title must be the Promise title, NOT "Refund", "Partial Refund", or "Refund for ..."
    assert event.title == "Grocery refund — damaged items"
    assert "Refund" not in event.title
    assert "REFUND" not in event.title
    # Refund type is communicated through event_type, not the title.
    assert event.event_type == models.TransactionType.REFUND
    # Original expense link preserved.
    assert event.linked_event_id == expense.json()["id"]


def test_asset_sale_receipt_title_equals_promise_title(client, session):
    """Receiving an asset-sale Expected Inflow posts Money In with the Promise title,
    not with 'Asset Sale:' prefix."""
    headers = create_user_and_token(client, "t1asset", "t1asset@example.com", "Password123!")
    today = user_timezone_today()
    wallet = _wallet(client, headers)

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

    inflow = client.post(
        "/expected-inflows",
        json={
            "kind": "ASSET_SALE",
            "asset_id": asset.json()["id"],
            "title": "Phone sale to colleague",
            "amount": 300_000,
            "due_date": today.isoformat(),
        },
        headers=headers,
    )
    assert inflow.status_code == 201, inflow.text

    realized = client.post(
        f"/expected-inflows/{inflow.json()['id']}/realize",
        json={
            "actual_amount": 300_000,
            "received_date": today.isoformat(),
            "wallet_allocations": [{"wallet_id": wallet["id"], "amount": 300_000}],
            "idempotency_key": "t1-asset-title",
        },
        headers=headers,
    )
    assert realized.status_code == 200, realized.text
    event_id = realized.json()["realization"]["event_ids"][0]
    event = session.query(models.FinancialEvent).filter(models.FinancialEvent.id == event_id).first()
    # Title must be the Promise title, NOT "Asset Sale: Old phone"
    assert event.title == "Phone sale to colleague"
    assert "Asset Sale" not in event.title
    # Asset-sale type is communicated through reference_type, not the title.
    assert event.reference_type == models.ReferenceType.ASSET_SALE


def test_no_source_kind_uses_generic_titles(client, session):
    """Prove no source-kind receipt path uses generic titles such as
    'client payment received', 'refund received', or 'asset sale received'."""
    headers = create_user_and_token(client, "t1generic", "t1generic@example.com", "Password123!")
    today = user_timezone_today()
    wallet = _wallet(client, headers)

    # --- EARNED ---
    source = _source(client, headers, "Consulting")
    earned = client.post(
        "/expected-inflows",
        json={
            "kind": "EARNED",
            "source_id": source["id"],
            "title": "Q3 consulting invoice",
            "amount": 200_000,
            "due_date": today.isoformat(),
        },
        headers=headers,
    )
    assert earned.status_code == 201, earned.text
    r = client.post(
        f"/expected-inflows/{earned.json()['id']}/realize",
        json={
            "actual_amount": 200_000,
            "received_date": today.isoformat(),
            "wallet_allocations": [{"wallet_id": wallet["id"], "amount": 200_000}],
            "idempotency_key": "t1-generic-earned",
        },
        headers=headers,
    )
    assert r.status_code == 200, r.text
    event_id = r.json()["realization"]["event_ids"][0]
    event = session.query(models.FinancialEvent).filter(models.FinancialEvent.id == event_id).first()
    assert event.title == "Q3 consulting invoice"

    # --- RECEIVABLE ---
    debt = client.post(
        "/debts",
        json={
            "debt_type": "OWED",
            "counterparty_name": "Bob",
            "initial_amount": 200_000,
            "currency": "UZS",
            "date": today.isoformat(),
            "expected_return_date": today.isoformat(),
            "is_money_transferred": False,
        },
        headers=headers,
    )
    assert debt.status_code == 201, debt.text
    receivable = client.post(
        "/expected-inflows",
        json={
            "kind": "RECEIVABLE",
            "debt_id": debt.json()["id"],
            "title": "Bob loan return",
            "amount": 100_000,
            "due_date": today.isoformat(),
        },
        headers=headers,
    )
    assert receivable.status_code == 201, receivable.text
    r2 = client.post(
        f"/expected-inflows/{receivable.json()['id']}/realize",
        json={
            "actual_amount": 100_000,
            "received_date": today.isoformat(),
            "wallet_allocations": [{"wallet_id": wallet["id"], "amount": 100_000}],
            "idempotency_key": "t1-generic-recv",
        },
        headers=headers,
    )
    assert r2.status_code == 200, r2.text
    for eid in r2.json()["realization"]["event_ids"]:
        ev = session.query(models.FinancialEvent).filter(models.FinancialEvent.id == eid).first()
        assert ev.title == "Bob loan return", f"Receivable event {eid} title mismatch: {ev.title}"

    # --- REFUND ---
    create_budget(client, headers, category="Electronics", monthly_limit=500_000)
    expense = create_expense(client, headers, title="Printer ink", amount=50_000, category="Electronics")
    assert expense.status_code == 201, expense.text
    refund = client.post(
        "/expected-inflows",
        json={
            "kind": "REFUND",
            "refund_event_id": expense.json()["id"],
            "title": "Printer ink refund",
            "amount": 50_000,
            "due_date": today.isoformat(),
        },
        headers=headers,
    )
    assert refund.status_code == 201, refund.text
    r3 = client.post(
        f"/expected-inflows/{refund.json()['id']}/realize",
        json={
            "actual_amount": 50_000,
            "received_date": today.isoformat(),
            "wallet_allocations": [{"wallet_id": wallet["id"], "amount": 50_000}],
            "idempotency_key": "t1-generic-refund",
        },
        headers=headers,
    )
    assert r3.status_code == 200, r3.text
    eid3 = r3.json()["realization"]["event_ids"][0]
    ev3 = session.query(models.FinancialEvent).filter(models.FinancialEvent.id == eid3).first()
    assert ev3.title == "Printer ink refund"
    assert ev3.event_type == models.TransactionType.REFUND  # type is in event_type

    # --- ASSET_SALE ---
    asset = client.post(
        "/assets",
        json={"title": "Desk", "purchase_value": 100_000, "current_value": 80_000, "status": "owned"},
        headers=headers,
    )
    assert asset.status_code == 201, asset.text
    sale = client.post(
        "/expected-inflows",
        json={
            "kind": "ASSET_SALE",
            "asset_id": asset.json()["id"],
            "title": "Desk sale",
            "amount": 80_000,
            "due_date": today.isoformat(),
        },
        headers=headers,
    )
    assert sale.status_code == 201, sale.text
    r4 = client.post(
        f"/expected-inflows/{sale.json()['id']}/realize",
        json={
            "actual_amount": 80_000,
            "received_date": today.isoformat(),
            "wallet_allocations": [{"wallet_id": wallet["id"], "amount": 80_000}],
            "idempotency_key": "t1-generic-asset",
        },
        headers=headers,
    )
    assert r4.status_code == 200, r4.text
    eid4 = r4.json()["realization"]["event_ids"][0]
    ev4 = session.query(models.FinancialEvent).filter(models.FinancialEvent.id == eid4).first()
    assert ev4.title == "Desk sale"
    assert ev4.reference_type == models.ReferenceType.ASSET_SALE  # type is in reference_type


def test_source_analytics_use_source_relationships_not_title_parsing(client, session):
    """Prove source analytics still use source relationships rather than parsing the title.
    The entity leg carries the income_source_id even though the title is user-authored."""
    headers = create_user_and_token(client, "t1analytics", "t1analytics@example.com", "Password123!")
    today = user_timezone_today()
    source = _source(client, headers, "Analytics client")
    wallet = _wallet(client, headers)

    inflow = client.post(
        "/expected-inflows",
        json={
            "kind": "EARNED",
            "source_id": source["id"],
            "title": "Custom project name — NOT the source name",
            "amount": 300_000,
            "due_date": today.isoformat(),
        },
        headers=headers,
    )
    assert inflow.status_code == 201, inflow.text

    realized = client.post(
        f"/expected-inflows/{inflow.json()['id']}/realize",
        json={
            "actual_amount": 300_000,
            "received_date": today.isoformat(),
            "wallet_allocations": [{"wallet_id": wallet["id"], "amount": 300_000}],
            "idempotency_key": "t1-analytics",
        },
        headers=headers,
    )
    assert realized.status_code == 200, realized.text
    event_id = realized.json()["realization"]["event_ids"][0]

    # The ledger event title is user-authored — NOT the source name.
    event = session.query(models.FinancialEvent).filter(models.FinancialEvent.id == event_id).first()
    assert event.title == "Custom project name — NOT the source name"

    # The entity ledger still carries the source relationship for analytics.
    entity_leg = session.query(models.EntityLedger).filter(
        models.EntityLedger.event_id == event_id,
    ).first()
    assert entity_leg.income_source_id == source["id"]


# ---------------------------------------------------------------------------
# Ticket 7: Explicit receivable Debt → Expected Inflow planning
# ---------------------------------------------------------------------------


def test_open_owed_debts_do_not_auto_project_into_cashflow(client, session):
    """Open OWED debts do NOT appear in cashflow unless an Expected Inflow
    is explicitly created for them."""
    headers = create_user_and_token(client, "t7noproj", "t7noproj@example.com", "Password123!")
    today = user_timezone_today()

    # Create an OWED debt
    debt = client.post(
        "/debts",
        json={
            "debt_type": "OWED",
            "counterparty_name": "Non-projecting debtor",
            "initial_amount": 500_000,
            "currency": "UZS",
            "date": today.isoformat(),
            "expected_return_date": today.isoformat(),
            "is_money_transferred": False,
        },
        headers=headers,
    )
    assert debt.status_code == 201, debt.text

    # Cashflow should NOT include this debt — only Expected Inflows appear
    cashflow = client.get(
        f"/expected-inflows/cashflow?budget_year={today.year}&budget_month={today.month}",
        headers=headers,
    )
    assert cashflow.status_code == 200, cashflow.text
    rows = cashflow.json()
    debt_rows = [r for r in rows if r.get("promise_title", "").lower().find("non-projecting") >= 0]
    assert len(debt_rows) == 0

    # Timeline should NOT include the debt either
    timeline = client.get(
        f"/expected-inflows/timeline?start_date={today.isoformat()}&end_date={today.isoformat()}",
        headers=headers,
    )
    assert timeline.status_code == 200, timeline.text
    timeline_debt_items = [
        i for i in timeline.json()
        if i.get("source_label") == "Non-projecting debtor"
    ]
    assert len(timeline_debt_items) == 0


def test_explicit_creation_links_debt_to_expected_inflow(client, session):
    """Users can explicitly create an Expected Inflow from a receivable Debt.
    The inflow links back to the debt, has a user-authored title, and the debt
    remains open until real receipt."""
    headers = create_user_and_token(client, "t7explicit", "t7explicit@example.com", "Password123!")
    today = user_timezone_today()
    wallet = _wallet(client, headers)

    # Create an OWED debt
    debt = client.post(
        "/debts",
        json={
            "debt_type": "OWED",
            "counterparty_name": "Charlie",
            "initial_amount": 400_000,
            "currency": "UZS",
            "date": today.isoformat(),
            "expected_return_date": today.isoformat(),
            "is_money_transferred": False,
        },
        headers=headers,
    )
    assert debt.status_code == 201, debt.text
    debt_id = debt.json()["id"]
    assert debt.json()["remaining_amount"] == 400_000

    # Create a receivable Expected Inflow linked to the debt
    inflow = client.post(
        "/expected-inflows",
        json={
            "kind": "RECEIVABLE",
            "debt_id": debt_id,
            "title": "Charlie repayment — July",
            "amount": 300_000,
            "due_date": today.isoformat(),
        },
        headers=headers,
    )
    assert inflow.status_code == 201, inflow.text
    inflow_data = inflow.json()
    assert inflow_data["kind"] == "RECEIVABLE"
    assert inflow_data["debt_id"] == debt_id
    assert inflow_data["title"] == "Charlie repayment — July"

    # Debt remains open — not closed by the inflow creation
    debt_after = client.get(f"/debts/{debt_id}", headers=headers)
    assert debt_after.status_code == 200, debt_after.text
    assert debt_after.json()["remaining_amount"] == 400_000
    assert debt_after.json()["lifecycle_status"] == "OPEN"

    # Cashflow now includes the inflow (because it was explicitly created)
    cashflow = client.get(
        f"/expected-inflows/cashflow?budget_year={today.year}&budget_month={today.month}",
        headers=headers,
    )
    assert cashflow.status_code == 200, cashflow.text
    rows = cashflow.json()
    inflow_rows = [r for r in rows if r["promise_id"] == inflow_data["id"]]
    assert len(inflow_rows) == 1

    # Receive 200k — debt balance should reduce
    client.post(
        f"/expected-inflows/{inflow_data['id']}/realize",
        json={
            "actual_amount": 200_000,
            "received_date": today.isoformat(),
            "wallet_allocations": [{"wallet_id": wallet["id"], "amount": 200_000}],
            "idempotency_key": "t7-explicit-receipt",
        },
        headers=headers,
    )
    debt_after_receipt = client.get(f"/debts/{debt_id}", headers=headers)
    assert debt_after_receipt.status_code == 200, debt_after_receipt.text
    assert debt_after_receipt.json()["remaining_amount"] == 200_000  # 400k - 200k


# ---------------------------------------------------------------------------
# Ticket 8: Receivable split repayment schedules
# ---------------------------------------------------------------------------


def test_receivable_promise_reschedule_creates_multiple_schedules(client):
    """One receivable Debt can be planned as one Promise with multiple schedules
    via the reschedule flow."""
    headers = create_user_and_token(client, "t8split", "t8split@example.com", "Password123!")
    today = user_timezone_today()

    debt = client.post(
        "/debts",
        json={
            "debt_type": "OWED",
            "counterparty_name": "Split debtor",
            "initial_amount": 600_000,
            "currency": "UZS",
            "date": today.isoformat(),
            "expected_return_date": today.isoformat(),
            "is_money_transferred": False,
        },
        headers=headers,
    )
    assert debt.status_code == 201, debt.text
    debt_id = debt.json()["id"]

    # Create a receivable Expected Inflow
    inflow = client.post(
        "/expected-inflows",
        json={
            "kind": "RECEIVABLE",
            "debt_id": debt_id,
            "title": "Split repayment plan",
            "amount": 600_000,
            "due_date": today.isoformat(),
        },
        headers=headers,
    )
    assert inflow.status_code == 201, inflow.text
    inflow_id = inflow.json()["id"]

    # Reschedule into 3 repayment dates
    july = _month_date(today, 1)
    aug = _month_date(today, 2)
    rescheduled = client.post(
        f"/expected-inflows/{inflow_id}/reschedule",
        json={
            "allocations": [
                {"amount": 200_000, "due_date": today.isoformat()},
                {"amount": 200_000, "due_date": july.isoformat()},
                {"amount": 200_000, "due_date": aug.isoformat()},
            ],
        },
        headers=headers,
    )
    assert rescheduled.status_code == 200, rescheduled.text
    result = rescheduled.json()
    assert result["source"]["is_rescheduled"] is True
    assert len(result["replacements"]) == 3

    # Each schedule appears in its respective cashflow month
    for month_offset, expected_amount in [(today, 200_000), (july, 200_000), (aug, 200_000)]:
        cashflow = client.get(
            f"/expected-inflows/cashflow?budget_year={month_offset.year}&budget_month={month_offset.month}",
            headers=headers,
        )
        assert cashflow.status_code == 200, cashflow.text
        month_rows = [r for r in cashflow.json() if r["promise_id"] == inflow_id]
        assert len(month_rows) == 1
        assert month_rows[0]["amount"] == expected_amount


def test_receivable_split_receipt_reduces_debt_balance(client):
    """Receiving one split schedule reduces both the Expected Inflow outstanding
    and the linked Debt remaining balance."""
    headers = create_user_and_token(client, "t8reduce", "t8reduce@example.com", "Password123!")
    today = user_timezone_today()
    wallet = _wallet(client, headers)

    debt = client.post(
        "/debts",
        json={
            "debt_type": "OWED",
            "counterparty_name": "Reduce debtor",
            "initial_amount": 500_000,
            "currency": "UZS",
            "date": today.isoformat(),
            "expected_return_date": today.isoformat(),
            "is_money_transferred": False,
        },
        headers=headers,
    )
    assert debt.status_code == 201, debt.text
    debt_id = debt.json()["id"]

    inflow = client.post(
        "/expected-inflows",
        json={
            "kind": "RECEIVABLE",
            "debt_id": debt_id,
            "title": "Reduce test",
            "amount": 500_000,
            "due_date": today.isoformat(),
        },
        headers=headers,
    )
    assert inflow.status_code == 201, inflow.text
    inflow_id = inflow.json()["id"]

    # Reschedule into 2 parts
    future = _month_date(today, 1)
    rescheduled = client.post(
        f"/expected-inflows/{inflow_id}/reschedule",
        json={
            "allocations": [
                {"amount": 300_000, "due_date": today.isoformat()},
                {"amount": 200_000, "due_date": future.isoformat()},
            ],
        },
        headers=headers,
    )
    assert rescheduled.status_code == 200, rescheduled.text
    replacements = rescheduled.json()["replacements"]
    first_schedule_id = replacements[0]["id"]
    second_schedule_id = replacements[1]["id"]

    # Receive the first schedule (300k)
    realized = client.post(
        f"/expected-inflows/{inflow_id}/realize",
        json={
            "actual_amount": 300_000,
            "received_date": today.isoformat(),
            "wallet_allocations": [{"wallet_id": wallet["id"], "amount": 300_000}],
            "schedule_allocations": [{"schedule_id": first_schedule_id, "amount": 300_000}],
            "idempotency_key": "t8-reduce-1",
        },
        headers=headers,
    )
    assert realized.status_code == 200, realized.text

    # Expected Inflow: 300k received, 200k remaining
    detail = client.get(f"/expected-inflows/{inflow_id}", headers=headers)
    assert detail.json()["received_amount"] == 300_000
    assert detail.json()["outstanding_amount"] == 200_000

    # Debt: 300k reduced from 500k = 200k remaining
    debt_after = client.get(f"/debts/{debt_id}", headers=headers)
    assert debt_after.status_code == 200, debt_after.text
    assert debt_after.json()["remaining_amount"] == 200_000

    # Receive the second schedule (200k) — full reconciliation
    realized2 = client.post(
        f"/expected-inflows/{inflow_id}/realize",
        json={
            "actual_amount": 200_000,
            "received_date": today.isoformat(),
            "wallet_allocations": [{"wallet_id": wallet["id"], "amount": 200_000}],
            "schedule_allocations": [{"schedule_id": second_schedule_id, "amount": 200_000}],
            "idempotency_key": "t8-reduce-2",
        },
        headers=headers,
    )
    assert realized2.status_code == 200, realized2.text

    detail2 = client.get(f"/expected-inflows/{inflow_id}", headers=headers)
    assert detail2.json()["received_amount"] == 500_000
    assert detail2.json()["outstanding_amount"] == 0

    debt_final = client.get(f"/debts/{debt_id}", headers=headers)
    assert debt_final.json()["remaining_amount"] == 0


def test_receivable_receipt_reversal_restores_inflow_and_debt(client):
    """Reversing a receivable receipt restores both Expected Inflow outstanding
    and the linked Debt remaining amount."""
    headers = create_user_and_token(client, "t8reverse", "t8reverse@example.com", "Password123!")
    today = user_timezone_today()
    wallet = _wallet(client, headers)

    debt = client.post(
        "/debts",
        json={
            "debt_type": "OWED",
            "counterparty_name": "Reverse debtor",
            "initial_amount": 300_000,
            "currency": "UZS",
            "date": today.isoformat(),
            "expected_return_date": today.isoformat(),
            "is_money_transferred": False,
        },
        headers=headers,
    )
    assert debt.status_code == 201, debt.text
    debt_id = debt.json()["id"]

    inflow = client.post(
        "/expected-inflows",
        json={
            "kind": "RECEIVABLE",
            "debt_id": debt_id,
            "title": "Reverse test",
            "amount": 300_000,
            "due_date": today.isoformat(),
        },
        headers=headers,
    )
    assert inflow.status_code == 201, inflow.text
    inflow_id = inflow.json()["id"]

    # Receive full amount
    realized = client.post(
        f"/expected-inflows/{inflow_id}/realize",
        json={
            "actual_amount": 300_000,
            "received_date": today.isoformat(),
            "wallet_allocations": [{"wallet_id": wallet["id"], "amount": 300_000}],
            "idempotency_key": "t8-reverse-full",
        },
        headers=headers,
    )
    assert realized.status_code == 200, realized.text

    detail = client.get(f"/expected-inflows/{inflow_id}", headers=headers)
    assert detail.json()["received_amount"] == 300_000
    assert detail.json()["outstanding_amount"] == 0

    debt_before_reversal = client.get(f"/debts/{debt_id}", headers=headers)
    assert debt_before_reversal.json()["remaining_amount"] == 0

    # Reverse the receipt
    realization_id = detail.json()["realizations"][0]["id"]
    reversed_resp = client.post(
        f"/expected-inflows/{inflow_id}/realizations/{realization_id}/reverse",
        json={"note": "Reversal test"},
        headers=headers,
    )
    assert reversed_resp.status_code == 200, reversed_resp.text

    # Expected Inflow restored
    after = client.get(f"/expected-inflows/{inflow_id}", headers=headers)
    assert after.json()["received_amount"] == 0
    assert after.json()["outstanding_amount"] == 300_000

    # Debt balance restored
    debt_after = client.get(f"/debts/{debt_id}", headers=headers)
    assert debt_after.status_code == 200, debt_after.text
    assert debt_after.json()["remaining_amount"] == 300_000


def test_receivable_three_part_repayment_full_reconcile(client):
    """Three-part repayment plan: create → reschedule into 3 → receive each →
    full reconciliation of inflow and debt."""
    headers = create_user_and_token(client, "t8three", "t8three@example.com", "Password123!")
    today = user_timezone_today()
    wallet = _wallet(client, headers)

    debt = client.post(
        "/debts",
        json={
            "debt_type": "OWED",
            "counterparty_name": "Three-part debtor",
            "initial_amount": 900_000,
            "currency": "UZS",
            "date": today.isoformat(),
            "expected_return_date": today.isoformat(),
            "is_money_transferred": False,
        },
        headers=headers,
    )
    assert debt.status_code == 201, debt.text
    debt_id = debt.json()["id"]

    inflow = client.post(
        "/expected-inflows",
        json={
            "kind": "RECEIVABLE",
            "debt_id": debt_id,
            "title": "Three-part repayment",
            "amount": 900_000,
            "due_date": today.isoformat(),
        },
        headers=headers,
    )
    assert inflow.status_code == 201, inflow.text
    inflow_id = inflow.json()["id"]

    # Reschedule into 3 parts
    m1 = _month_date(today, 1)
    m2 = _month_date(today, 2)
    rescheduled = client.post(
        f"/expected-inflows/{inflow_id}/reschedule",
        json={
            "allocations": [
                {"amount": 300_000, "due_date": today.isoformat()},
                {"amount": 300_000, "due_date": m1.isoformat()},
                {"amount": 300_000, "due_date": m2.isoformat()},
            ],
        },
        headers=headers,
    )
    assert rescheduled.status_code == 200, rescheduled.text
    replacements = rescheduled.json()["replacements"]
    assert len(replacements) == 3

    # Receive each part and verify debt reduces step by step
    for i, schedule_id in enumerate([r["id"] for r in replacements]):
        client.post(
            f"/expected-inflows/{inflow_id}/realize",
            json={
                "actual_amount": 300_000,
                "received_date": today.isoformat(),
                "wallet_allocations": [{"wallet_id": wallet["id"], "amount": 300_000}],
                "schedule_allocations": [{"schedule_id": schedule_id, "amount": 300_000}],
                "idempotency_key": f"t8-three-{i}",
            },
            headers=headers,
        )
        detail = client.get(f"/expected-inflows/{inflow_id}", headers=headers)
        expected_received = 300_000 * (i + 1)
        expected_remaining = 900_000 - expected_received
        assert detail.json()["received_amount"] == expected_received
        assert detail.json()["outstanding_amount"] == expected_remaining

        debt_after = client.get(f"/debts/{debt_id}", headers=headers)
        assert debt_after.json()["remaining_amount"] == expected_remaining

    # Full reconciliation
    final = client.get(f"/expected-inflows/{inflow_id}", headers=headers)
    assert final.json()["received_amount"] == 900_000
    assert final.json()["outstanding_amount"] == 0
    assert final.json()["status"] == "CLOSED"

    debt_final = client.get(f"/debts/{debt_id}", headers=headers)
    assert debt_final.json()["remaining_amount"] == 0


# ---------------------------------------------------------------------------
# Ticket 9: Decouple Debt deadlines from Expected Inflow due dates
# ---------------------------------------------------------------------------


def test_debt_expected_return_date_update_does_not_mutate_inflow_due_date(client):
    """Updating a Debt's expected_return_date does NOT change linked Expected
    Inflow schedule due dates. The two date concepts are independent."""
    headers = create_user_and_token(client, "t9debtup", "t9debtup@example.com", "Password123!")
    today = user_timezone_today()

    debt = client.post(
        "/debts",
        json={
            "debt_type": "OWED",
            "counterparty_name": "Date-decouple debtor",
            "initial_amount": 400_000,
            "currency": "UZS",
            "date": today.isoformat(),
            "expected_return_date": today.isoformat(),
            "is_money_transferred": False,
        },
        headers=headers,
    )
    assert debt.status_code == 201, debt.text
    debt_id = debt.json()["id"]

    inflow = client.post(
        "/expected-inflows",
        json={
            "kind": "RECEIVABLE",
            "debt_id": debt_id,
            "title": "Decouple test",
            "amount": 400_000,
            "due_date": today.isoformat(),
        },
        headers=headers,
    )
    assert inflow.status_code == 201, inflow.text
    inflow_id = inflow.json()["id"]

    # Capture original inflow due date
    detail_before = client.get(f"/expected-inflows/{inflow_id}", headers=headers)
    original_due_date = detail_before.json()["schedules"][0]["due_date"]

    # Update the Debt's expected_return_date
    future = today + __import__("datetime").timedelta(days=60)
    updated = client.patch(
        f"/debts/{debt_id}",
        json={"expected_return_date": future.isoformat()},
        headers=headers,
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["expected_return_date"] == future.isoformat()

    # Inflow due date must be UNCHANGED
    detail_after = client.get(f"/expected-inflows/{inflow_id}", headers=headers)
    assert detail_after.json()["schedules"][0]["due_date"] == original_due_date


def test_inflow_reschedule_does_not_mutate_debt_expected_return_date(client):
    """Rescheduling an Expected Inflow does NOT change the linked Debt's
    expected_return_date."""
    headers = create_user_and_token(client, "t9inflowres", "t9inflowres@example.com", "Password123!")
    today = user_timezone_today()

    debt = client.post(
        "/debts",
        json={
            "debt_type": "OWED",
            "counterparty_name": "Reschedule-decouple debtor",
            "initial_amount": 500_000,
            "currency": "UZS",
            "date": today.isoformat(),
            "expected_return_date": today.isoformat(),
            "is_money_transferred": False,
        },
        headers=headers,
    )
    assert debt.status_code == 201, debt.text
    debt_id = debt.json()["id"]
    original_debt_return_date = debt.json()["expected_return_date"]

    inflow = client.post(
        "/expected-inflows",
        json={
            "kind": "RECEIVABLE",
            "debt_id": debt_id,
            "title": "Reschedule decouple",
            "amount": 500_000,
            "due_date": today.isoformat(),
        },
        headers=headers,
    )
    assert inflow.status_code == 201, inflow.text
    inflow_id = inflow.json()["id"]

    # Reschedule to a future date
    future_month = _month_date(today, 2)
    rescheduled = client.post(
        f"/expected-inflows/{inflow_id}/reschedule",
        json={
            "allocations": [{"amount": 500_000, "due_date": future_month.isoformat()}],
        },
        headers=headers,
    )
    assert rescheduled.status_code == 200, rescheduled.text
    result = rescheduled.json()
    new_due_date = result["replacements"][0]["due_date"]
    assert new_due_date != original_debt_return_date  # they diverge

    # Debt expected_return_date must be UNCHANGED
    debt_after = client.get(f"/debts/{debt_id}", headers=headers)
    assert debt_after.json()["expected_return_date"] == original_debt_return_date


def test_overdue_debt_with_future_inflow_missed_deadline(client):
    """A late receivable can remain overdue while its Expected Inflow projects
    the new expected cash date. The Debt deadline and cashflow date are
    independent."""
    headers = create_user_and_token(client, "t9overdue", "t9overdue@example.com", "Password123!")
    today = user_timezone_today()

    # Debt was due yesterday → overdue
    yesterday = today - __import__("datetime").timedelta(days=1)
    debt = client.post(
        "/debts",
        json={
            "debt_type": "OWED",
            "counterparty_name": "Late payer",
            "initial_amount": 300_000,
            "currency": "UZS",
            "date": (today - __import__("datetime").timedelta(days=30)).isoformat(),
            "expected_return_date": yesterday.isoformat(),
            "is_money_transferred": False,
        },
        headers=headers,
    )
    assert debt.status_code == 201, debt.text
    debt_id = debt.json()["id"]
    debt_data = debt.json()
    assert debt_data["time_status"] == "OVERDUE"

    # Plan the inflow for next month — realistic cash arrival
    future = _month_date(today, 1)
    inflow = client.post(
        "/expected-inflows",
        json={
            "kind": "RECEIVABLE",
            "debt_id": debt_id,
            "title": "Late payer — now expects July",
            "amount": 300_000,
            "due_date": future.isoformat(),
        },
        headers=headers,
    )
    assert inflow.status_code == 201, inflow.text
    inflow_id = inflow.json()["id"]

    # Debt remains overdue
    debt_after = client.get(f"/debts/{debt_id}", headers=headers)
    assert debt_after.json()["time_status"] == "OVERDUE"

    # Expected Inflow is in the future — not overdue
    detail = client.get(f"/expected-inflows/{inflow_id}", headers=headers)
    assert detail.json()["is_overdue"] is False
    assert detail.json()["schedules"][0]["due_date"] == future.isoformat()
    assert detail.json()["schedules"][0]["due_date"] != yesterday.isoformat()


def test_deadline_dates_use_effective_user_timezone(client):
    """Both Debt overdue and Expected Inflow due dates use the effective
    user timezone.  The X-Timezone header determines 'today' for both domains."""
    # Use an explicit timezone header to prove timezone-boundary behavior
    headers_tashkent = create_user_and_token(
        client, "t9tz", "t9tz@example.com", "Password123!",
    )
    # create_user_and_token already sets X-Timezone to TEST_TIMEZONE (Asia/Tashkent)
    today_tashkent = user_timezone_today()

    # Debt due yesterday in Tashkent → overdue
    yesterday = today_tashkent - __import__("datetime").timedelta(days=1)
    debt = client.post(
        "/debts",
        json={
            "debt_type": "OWED",
            "counterparty_name": "Timezone debtor",
            "initial_amount": 200_000,
            "currency": "UZS",
            "date": (today_tashkent - __import__("datetime").timedelta(days=30)).isoformat(),
            "expected_return_date": yesterday.isoformat(),
            "is_money_transferred": False,
        },
        headers=headers_tashkent,
    )
    assert debt.status_code == 201, debt.text
    assert debt.json()["time_status"] == "OVERDUE"

    # Inflow due today in Tashkent → NOT overdue
    inflow = client.post(
        "/expected-inflows",
        json={
            "kind": "RECEIVABLE",
            "debt_id": debt.json()["id"],
            "title": "TZ test inflow",
            "amount": 200_000,
            "due_date": today_tashkent.isoformat(),
        },
        headers=headers_tashkent,
    )
    assert inflow.status_code == 201, inflow.text
    detail = client.get(f"/expected-inflows/{inflow.json()['id']}", headers=headers_tashkent)
    assert detail.json()["is_overdue"] is False

    # Verify X-Timezone was honored — due_date matches Tashkent today
    assert detail.json()["schedules"][0]["due_date"] == today_tashkent.isoformat()


# ---------------------------------------------------------------------------
# Ticket 10: Epic 5 cross-domain regression coverage
# ---------------------------------------------------------------------------


def test_epic5_regression_money_in_identity_all_source_kinds(client, session):
    """All five Money In source kinds (earned, refund, receivable, asset sale,
    correction) use user-authored titles, not robot-generated ones."""
    headers = create_user_and_token(client, "t10identity", "t10identity@example.com", "Password123!")
    today = user_timezone_today()
    wallet = _wallet(client, headers)

    # --- EARNED ---
    source = _source(client, headers, "Epic5 earned")
    earned = client.post(
        "/expected-inflows",
        json={
            "kind": "EARNED",
            "source_id": source["id"],
            "title": "Epic5 earned title",
            "amount": 100_000,
            "due_date": today.isoformat(),
        },
        headers=headers,
    )
    assert earned.status_code == 201
    r = client.post(
        f"/expected-inflows/{earned.json()['id']}/realize",
        json={
            "actual_amount": 100_000,
            "received_date": today.isoformat(),
            "wallet_allocations": [{"wallet_id": wallet["id"], "amount": 100_000}],
            "idempotency_key": "t10-earned-id",
        },
        headers=headers,
    )
    assert r.status_code == 200
    eid_earned = r.json()["realization"]["event_ids"][0]
    ev = session.query(models.FinancialEvent).filter(models.FinancialEvent.id == eid_earned).first()
    assert ev.title == "Epic5 earned title"
    assert ev.event_type == models.TransactionType.INCOME

    # --- REFUND ---
    create_budget(client, headers, category="Groceries", monthly_limit=1_000_000)
    expense = create_expense(client, headers, title="Epic5 refundable", amount=50_000, category="Groceries")
    assert expense.status_code == 201
    refund_inflow = client.post(
        "/expected-inflows",
        json={
            "kind": "REFUND",
            "refund_event_id": expense.json()["id"],
            "title": "Epic5 refund title",
            "amount": 50_000,
            "due_date": today.isoformat(),
        },
        headers=headers,
    )
    assert refund_inflow.status_code == 201
    rr = client.post(
        f"/expected-inflows/{refund_inflow.json()['id']}/realize",
        json={
            "actual_amount": 50_000,
            "received_date": today.isoformat(),
            "wallet_allocations": [{"wallet_id": wallet["id"], "amount": 50_000}],
            "idempotency_key": "t10-refund-id",
        },
        headers=headers,
    )
    assert rr.status_code == 200
    eid_refund = rr.json()["realization"]["event_ids"][0]
    ev_refund = session.query(models.FinancialEvent).filter(models.FinancialEvent.id == eid_refund).first()
    assert ev_refund.title == "Epic5 refund title"
    assert ev_refund.event_type == models.TransactionType.REFUND

    # --- RECEIVABLE ---
    debt = client.post(
        "/debts",
        json={
            "debt_type": "OWED",
            "counterparty_name": "Epic5 debtor",
            "initial_amount": 200_000,
            "currency": "UZS",
            "date": today.isoformat(),
            "expected_return_date": today.isoformat(),
            "is_money_transferred": False,
        },
        headers=headers,
    )
    assert debt.status_code == 201
    recv = client.post(
        "/expected-inflows",
        json={
            "kind": "RECEIVABLE",
            "debt_id": debt.json()["id"],
            "title": "Epic5 receivable title",
            "amount": 200_000,
            "due_date": today.isoformat(),
        },
        headers=headers,
    )
    assert recv.status_code == 201
    rcv_r = client.post(
        f"/expected-inflows/{recv.json()['id']}/realize",
        json={
            "actual_amount": 200_000,
            "received_date": today.isoformat(),
            "wallet_allocations": [{"wallet_id": wallet["id"], "amount": 200_000}],
            "idempotency_key": "t10-recv-id",
        },
        headers=headers,
    )
    assert rcv_r.status_code == 200
    for eid in rcv_r.json()["realization"]["event_ids"]:
        evt = session.query(models.FinancialEvent).filter(models.FinancialEvent.id == eid).first()
        assert evt.title == "Epic5 receivable title"

    # --- ASSET SALE ---
    asset = client.post(
        "/assets",
        json={"title": "Epic5 asset", "purchase_value": 100_000, "current_value": 80_000, "status": "owned"},
        headers=headers,
    )
    assert asset.status_code == 201
    sale = client.post(
        "/expected-inflows",
        json={
            "kind": "ASSET_SALE",
            "asset_id": asset.json()["id"],
            "title": "Epic5 asset sale title",
            "amount": 80_000,
            "due_date": today.isoformat(),
        },
        headers=headers,
    )
    assert sale.status_code == 201
    sr = client.post(
        f"/expected-inflows/{sale.json()['id']}/realize",
        json={
            "actual_amount": 80_000,
            "received_date": today.isoformat(),
            "wallet_allocations": [{"wallet_id": wallet["id"], "amount": 80_000}],
            "idempotency_key": "t10-asset-id",
        },
        headers=headers,
    )
    assert sr.status_code == 200
    eid_sale = sr.json()["realization"]["event_ids"][0]
    ev_sale = session.query(models.FinancialEvent).filter(models.FinancialEvent.id == eid_sale).first()
    assert ev_sale.title == "Epic5 asset sale title"
    assert ev_sale.reference_type == models.ReferenceType.ASSET_SALE

    # --- CORRECTION (direct expense refund) ---
    expense2 = create_expense(client, headers, title="Epic5 correction expense", amount=30_000, category="Groceries")
    assert expense2.status_code == 201
    refund_direct = client.post(
        f"/expenses/{expense2.json()['id']}/refund",
        json={"amount": 30_000},
        headers=headers,
    )
    assert refund_direct.status_code == 201
    assert refund_direct.json()["title"] == "Epic5 correction expense"


def test_epic5_regression_source_analytics_with_user_authored_titles(client):
    """Source analytics still work when ledger titles are user-authored
    (not parsed from title strings)."""
    headers = create_user_and_token(client, "t10analytics", "t10analytics@example.com", "Password123!")
    today = user_timezone_today()
    wallet = _wallet(client, headers)

    source = _source(client, headers, "Epic5 analytics source")
    inflow = client.post(
        "/expected-inflows",
        json={
            "kind": "EARNED",
            "source_id": source["id"],
            "title": "Completely custom title — NOT the source name",
            "amount": 150_000,
            "due_date": today.isoformat(),
        },
        headers=headers,
    )
    assert inflow.status_code == 201
    pid = inflow.json()["id"]

    client.post(
        f"/expected-inflows/{pid}/realize",
        json={
            "actual_amount": 100_000,
            "received_date": today.isoformat(),
            "wallet_allocations": [{"wallet_id": wallet["id"], "amount": 100_000}],
            "idempotency_key": "t10-analytics-rr",
        },
        headers=headers,
    )

    analytics = client.get(f"/income/sources/{source['id']}/analytics", headers=headers)
    assert analytics.status_code == 200
    data = analytics.json()
    assert data["lifetime_expected"] == 150_000
    assert data["lifetime_received"] == 100_000
    assert data["outstanding_expected"] == 50_000
    assert data["reliability_pct"] is not None
    assert data["promise_ids"] == [pid]


def test_epic5_regression_refunds_excluded_from_income_included_in_wallet_and_category(client):
    """Refunds are excluded from earned-income analytics while included in
    wallet inflow and category spend math."""
    headers = create_user_and_token(client, "t10refdual", "t10refdual@example.com", "Password123!")
    today = user_timezone_today()
    create_budget(client, headers, category="Electronics", monthly_limit=500_000)

    # Get income baseline
    summary_before = client.get("/analytics/dashboard-summary", headers=headers)
    assert summary_before.status_code == 200
    income_before = summary_before.json()["income"]

    expense = create_expense(client, headers, title="Dual test expense", amount=40_000, category="Electronics")
    assert expense.status_code == 201
    expense_id = expense.json()["id"]

    # Refund appears in Money In
    client.post(f"/expenses/{expense_id}/refund", json={"amount": 40_000}, headers=headers)
    money_in = client.get("/money-in", headers=headers)
    refund_items = [i for i in money_in.json()["items"] if i["title"] == "Dual test expense"]
    assert len(refund_items) == 1
    assert refund_items[0]["kind"] == "returned"
    assert refund_items[0]["counts_as_income"] is False

    # Income analytics should NOT have increased
    summary_after = client.get("/analytics/dashboard-summary", headers=headers)
    assert summary_after.json()["income"] == income_before

    # Wallet balance increased (refund = money in)
    wallets = client.get("/wallets", headers=headers)
    assert len(wallets.json()) > 0

    # Category spend is zero after full refund
    month_summary = client.get(
        f"/budgets/month-summary?budget_year={today.year}&budget_month={today.month}",
        headers=headers,
    )
    assert month_summary.json()["normal_budget_spent"] == 0


def test_epic5_regression_open_receivables_require_explicit_inflow_creation(client):
    """Open receivable Debts do NOT appear in cashflow until an Expected Inflow
    is explicitly created for them."""
    headers = create_user_and_token(client, "t10explicit", "t10explicit@example.com", "Password123!")
    today = user_timezone_today()

    # Create two OWED debts
    d1 = client.post(
        "/debts",
        json={
            "debt_type": "OWED", "counterparty_name": "Auto-test A",
            "initial_amount": 500_000, "currency": "UZS",
            "date": today.isoformat(), "expected_return_date": today.isoformat(),
            "is_money_transferred": False,
        },
        headers=headers,
    )
    assert d1.status_code == 201
    d2 = client.post(
        "/debts",
        json={
            "debt_type": "OWED", "counterparty_name": "Auto-test B",
            "initial_amount": 300_000, "currency": "UZS",
            "date": today.isoformat(), "expected_return_date": today.isoformat(),
            "is_money_transferred": False,
        },
        headers=headers,
    )
    assert d2.status_code == 201

    # Neither debt auto-appears in cashflow
    cashflow = client.get(
        f"/expected-inflows/cashflow?budget_year={today.year}&budget_month={today.month}",
        headers=headers,
    )
    assert cashflow.status_code == 200
    cf_labels = {r["source_label"] for r in cashflow.json()}
    assert "Auto-test A" not in cf_labels
    assert "Auto-test B" not in cf_labels

    # Explicitly create inflow for debt A only
    inflow = client.post(
        "/expected-inflows",
        json={
            "kind": "RECEIVABLE",
            "debt_id": d1.json()["id"],
            "title": "Only A is planned",
            "amount": 400_000,
            "due_date": today.isoformat(),
        },
        headers=headers,
    )
    assert inflow.status_code == 201

    # Now A appears in cashflow, B still doesn't
    cashflow2 = client.get(
        f"/expected-inflows/cashflow?budget_year={today.year}&budget_month={today.month}",
        headers=headers,
    )
    cf_labels2 = {r["source_label"] for r in cashflow2.json()}
    assert "Auto-test A" in cf_labels2
    assert "Auto-test B" not in cf_labels2


def test_epic5_regression_split_receivable_and_debt_reconciliation(client):
    """Split receivable schedules reduce debt balance, and receipt reversal
    restores both inflow outstanding and debt remaining."""
    headers = create_user_and_token(client, "t10split", "t10split@example.com", "Password123!")
    today = user_timezone_today()
    wallet = _wallet(client, headers)

    debt = client.post(
        "/debts",
        json={
            "debt_type": "OWED", "counterparty_name": "Split reconciler",
            "initial_amount": 600_000, "currency": "UZS",
            "date": today.isoformat(), "expected_return_date": today.isoformat(),
            "is_money_transferred": False,
        },
        headers=headers,
    )
    assert debt.status_code == 201
    debt_id = debt.json()["id"]

    inflow = client.post(
        "/expected-inflows",
        json={
            "kind": "RECEIVABLE", "debt_id": debt_id,
            "title": "Split reconciliation", "amount": 600_000,
            "due_date": today.isoformat(),
        },
        headers=headers,
    )
    assert inflow.status_code == 201
    inflow_id = inflow.json()["id"]

    # Split into 2 schedules
    future = _month_date(today, 1)
    rescheduled = client.post(
        f"/expected-inflows/{inflow_id}/reschedule",
        json={
            "allocations": [
                {"amount": 350_000, "due_date": today.isoformat()},
                {"amount": 250_000, "due_date": future.isoformat()},
            ],
        },
        headers=headers,
    )
    assert rescheduled.status_code == 200
    reps = rescheduled.json()["replacements"]

    # Receive first schedule
    r1 = client.post(
        f"/expected-inflows/{inflow_id}/realize",
        json={
            "actual_amount": 350_000, "received_date": today.isoformat(),
            "wallet_allocations": [{"wallet_id": wallet["id"], "amount": 350_000}],
            "schedule_allocations": [{"schedule_id": reps[0]["id"], "amount": 350_000}],
            "idempotency_key": "t10-split-r1",
        },
        headers=headers,
    )
    assert r1.status_code == 200

    detail = client.get(f"/expected-inflows/{inflow_id}", headers=headers)
    assert detail.json()["received_amount"] == 350_000
    assert detail.json()["outstanding_amount"] == 250_000

    debt_mid = client.get(f"/debts/{debt_id}", headers=headers)
    assert debt_mid.json()["remaining_amount"] == 250_000

    # Reverse the receipt
    realization_id = detail.json()["realizations"][0]["id"]
    rev = client.post(
        f"/expected-inflows/{inflow_id}/realizations/{realization_id}/reverse",
        json={"note": "Regression reversal"},
        headers=headers,
    )
    assert rev.status_code == 200

    detail2 = client.get(f"/expected-inflows/{inflow_id}", headers=headers)
    assert detail2.json()["received_amount"] == 0
    assert detail2.json()["outstanding_amount"] == 600_000

    debt_after = client.get(f"/debts/{debt_id}", headers=headers)
    assert debt_after.json()["remaining_amount"] == 600_000


def test_epic5_regression_deadline_independence_full_workflow(client):
    """Full workflow: debt overdue → inflow planned for future → debt stays
    overdue → inflow stays in future month → deadlines are independent."""
    headers = create_user_and_token(client, "t10deadline", "t10deadline@example.com", "Password123!")
    today = user_timezone_today()

    yesterday = today - __import__("datetime").timedelta(days=1)
    next_month = _month_date(today, 1)

    debt = client.post(
        "/debts",
        json={
            "debt_type": "OWED", "counterparty_name": "Deadline indy",
            "initial_amount": 400_000, "currency": "UZS",
            "date": (today - __import__("datetime").timedelta(days=60)).isoformat(),
            "expected_return_date": yesterday.isoformat(),
            "is_money_transferred": False,
        },
        headers=headers,
    )
    assert debt.status_code == 201
    debt_id = debt.json()["id"]
    assert debt.json()["time_status"] == "OVERDUE"

    inflow = client.post(
        "/expected-inflows",
        json={
            "kind": "RECEIVABLE", "debt_id": debt_id,
            "title": "Late but planned",
            "amount": 400_000, "due_date": next_month.isoformat(),
        },
        headers=headers,
    )
    assert inflow.status_code == 201
    inflow_id = inflow.json()["id"]

    # Debt still overdue, inflow in future
    debt_now = client.get(f"/debts/{debt_id}", headers=headers)
    assert debt_now.json()["time_status"] == "OVERDUE"
    detail = client.get(f"/expected-inflows/{inflow_id}", headers=headers)
    assert detail.json()["is_overdue"] is False
    assert detail.json()["schedules"][0]["due_date"] == next_month.isoformat()
    assert detail.json()["schedules"][0]["due_date"] != yesterday.isoformat()
