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
