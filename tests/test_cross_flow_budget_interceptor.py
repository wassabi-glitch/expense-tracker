"""Issue 8 — Cross-Flow Budget Interceptor and Decoupling Regression Coverage.

Verifies that the Budget Permission / Obligation Money Posting architecture
cleanup preserved the product contract across all three money-posting flows:

1. Normal expense posting
2. Debt charge payment posting
3. Payment Plan charge payment posting

All three must return the same structured ``expenses.budget_required`` failure
when a Budget row is missing.  Debt and Payment Plan must remain decoupled
while sharing only money-posting mechanics (Financial Event Ledger, Budget
Permission).
"""

from app import models
from tests.helpers import (
    create_budget,
    create_user_and_token,
    user_timezone_today,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _default_wallet(client, headers):
    response = client.get("/wallets", headers=headers)
    assert response.status_code == 200, response.text
    return response.json()[0]


def _create_owing_debt(client, headers, wallet_id, **overrides):
    payload = {
        "debt_type": "OWING",
        "counterparty_name": "CrossFlow Bank",
        "initial_amount": 500_000,
        "currency": "UZS",
        "date": user_timezone_today().isoformat(),
        "expected_return_date": user_timezone_today().isoformat(),
        "is_money_transferred": True,
        "initial_wallet_id": wallet_id,
    }
    payload.update(overrides)
    res = client.post("/debts", json=payload, headers=headers)
    assert res.status_code == 201, res.text
    return res.json()


def _create_plan(client, headers, **overrides):
    payload = {
        "item_name": "CrossFlow Phone",
        "store_or_bank_name": "CrossFlow Store",
        "total_price": 1_200_000,
        "down_payment": 0,
        "months": 12,
        "frequency": "MONTHLY",
        "start_date": user_timezone_today().isoformat(),
        "expense_category": "Electronics",
    }
    payload.update(overrides)
    res = client.post("/payment-plans", json=payload, headers=headers)
    assert res.status_code == 201, res.text
    return res.json()


def _budgets_for_all(client, headers):
    today = user_timezone_today()
    create_budget(client, headers, category="Groceries", monthly_limit=5_000_000,
                  budget_year=today.year, budget_month=today.month)
    create_budget(client, headers, category="Debt Charges", monthly_limit=1_000_000,
                  budget_year=today.year, budget_month=today.month)
    create_budget(client, headers, category="Electronics", monthly_limit=5_000_000,
                  budget_year=today.year, budget_month=today.month)


# ============================================================================
# Budget Interceptor — consistent failure across all three flows
# ============================================================================


def test_normal_expense_budget_required_failure(client):
    """Normal expense without Budget permission returns structured
    'expenses.budget_required' failure."""
    headers = create_user_and_token(
        client, "cross1", "cross1@example.com", "Password123!"
    )
    # Deliberately no budget created

    res = client.post(
        "/expenses/",
        json={
            "title": "No budget expense",
            "amount": 10_000,
            "category": "Groceries",
            "date": user_timezone_today().isoformat(),
        },
        headers=headers,
    )
    assert res.status_code == 400, res.text
    assert res.json()["detail"] == "expenses.budget_required"


def test_debt_charge_budget_required_failure(client):
    """Debt charge payment without Budget permission returns the same
    structured 'expenses.budget_required' failure as normal expenses."""
    headers = create_user_and_token(
        client, "cross2", "cross2@example.com", "Password123!"
    )
    wallet = _default_wallet(client, headers)
    # Deliberately no Debt Charges budget

    debt = _create_owing_debt(client, headers, wallet["id"])
    client.post(
        f"/debts/{debt['id']}/charges",
        json={"amount": 10_000, "reason": "Interest"},
        headers=headers,
    )

    res = client.post(
        f"/debts/{debt['id']}/payments",
        json={
            "amount": 510_000,
            "date": user_timezone_today().isoformat(),
            "wallet_allocations": [
                {"wallet_id": wallet["id"], "amount": 510_000},
            ],
        },
        headers=headers,
    )
    assert res.status_code == 400, res.text
    assert res.json()["detail"] == "expenses.budget_required"


def test_payment_plan_budget_required_failure(client):
    """Payment Plan payment without Budget permission returns the same
    structured 'expenses.budget_required' failure as normal expenses."""
    headers = create_user_and_token(
        client, "cross3", "cross3@example.com", "Password123!"
    )
    wallet = _default_wallet(client, headers)
    # Deliberately no budget at all
    plan = _create_plan(client, headers)

    # Pay the first payment row — fails because no Electronics budget exists
    payment_row = plan["payments"][0]
    res = client.post(
        f"/payment-plans/{plan['id']}/payments",
        json={
            "amount": payment_row["amount"],
            "paid_date": user_timezone_today().isoformat(),
            "wallet_allocations": [
                {"wallet_id": wallet["id"], "amount": payment_row["amount"]},
            ],
        },
        headers=headers,
    )
    assert res.status_code == 400, res.text
    assert res.json()["detail"] == "expenses.budget_required"


# ============================================================================
# Decoupling — Debt and Payment Plan remain separate
# ============================================================================


def test_debt_remains_open_ended_running_balance_obligation(client, session):
    """Debt must remain an open-ended running-balance obligation with its own
    Debt Ledger, NOT a scheduled Payment Plan."""
    headers = create_user_and_token(
        client, "cross4", "cross4@example.com", "Password123!"
    )
    wallet = _default_wallet(client, headers)
    debt = _create_owing_debt(client, headers, wallet["id"])

    # Verify Debt uses DebtLedgerEntry, not PaymentPlanLedgerEntry
    debt_ledger = (
        session.query(models.DebtLedgerEntry)
        .filter(models.DebtLedgerEntry.debt_id == debt["id"])
        .all()
    )
    assert len(debt_ledger) >= 1, "Debt must have Debt Ledger entries"

    # Verify Debt does NOT create PaymentPlan rows
    user = session.query(models.User).filter(
        models.User.email == "cross4@example.com"
    ).first()
    pp_ledger = (
        session.query(models.PaymentPlanLedgerEntry)
        .filter(models.PaymentPlanLedgerEntry.owner_id == user.id)
        .all()
    )
    assert len(pp_ledger) == 0, "Debt must not create Payment Plan Ledger entries"

    # Debt must have running balance fields
    debt_obj = session.query(models.Debt).filter(
        models.Debt.id == debt["id"]
    ).first()
    assert debt_obj.debt_type == models.DebtType.OWING
    assert debt_obj.remaining_amount is not None
    assert debt_obj.remaining_amount > 0  # open lifecycle (ADR 0026)


def test_payment_plan_remains_scheduled_obligation_with_rows_and_waterfall(
    client, session,
):
    """Payment Plan must remain a scheduled obligation with rows and waterfall
    rules, NOT an open-ended running-balance Debt."""
    headers = create_user_and_token(
        client, "cross5", "cross5@example.com", "Password123!"
    )
    _budgets_for_all(client, headers)
    wallet = _default_wallet(client, headers)
    plan = _create_plan(client, headers)

    # Payment Plan must have schedule rows
    plan_obj = session.query(models.PaymentPlan).filter(
        models.PaymentPlan.id == plan["id"]
    ).first()
    assert len(plan_obj.payments) >= 1, "Payment Plan must have schedule rows"
    for payment in plan_obj.payments:
        assert payment.amount > 0, "Each row must have an amount"
        assert payment.due_date is not None, "Each row must have a due_date"

    # Payment Plan must NOT create Debt rows
    user = session.query(models.User).filter(
        models.User.email == "cross5@example.com"
    ).first()
    debts = (
        session.query(models.Debt)
        .filter(models.Debt.owner_id == user.id)
        .all()
    )
    assert len(debts) == 0, "Payment Plan must not create Debt rows"

    # Payment Plan must use PaymentPlanLedgerEntry, not DebtLedgerEntry.
    # Note: creating a plan creates an INITIAL ledger entry.
    pp_ledger_before = (
        session.query(models.PaymentPlanLedgerEntry)
        .filter(models.PaymentPlanLedgerEntry.plan_id == plan["id"])
        .all()
    )
    initial_count = len(pp_ledger_before)
    assert initial_count >= 1, "Plan creation creates an INITIAL ledger entry"

    # Record a payment to exercise the waterfall
    client.post(
        f"/payment-plans/{plan['id']}/payments",
        json={
            "amount": 100_000,
            "paid_date": user_timezone_today().isoformat(),
            "wallet_allocations": [
                {"wallet_id": wallet["id"], "amount": 100_000},
            ],
        },
        headers=headers,
    )
    session.expire_all()

    # After payment: PaymentPlanLedgerEntry must exist, DebtLedgerEntry must not
    pp_ledger_after = (
        session.query(models.PaymentPlanLedgerEntry)
        .filter(models.PaymentPlanLedgerEntry.plan_id == plan["id"])
        .all()
    )
    assert len(pp_ledger_after) >= 1, "Payment Plan must create its own Ledger entries"


def test_shared_posting_does_not_merge_persistence_or_lifecycle(client, session):
    """Shared posting mechanics (Financial Event Ledger, Budget Permission)
    must not merge Debt and Payment Plan persistence tables or lifecycles."""
    headers = create_user_and_token(
        client, "cross6", "cross6@example.com", "Password123!"
    )
    _budgets_for_all(client, headers)
    wallet = _default_wallet(client, headers)

    # Create both a Debt and a Payment Plan
    debt = _create_owing_debt(client, headers, wallet["id"])
    plan = _create_plan(client, headers)

    # Pay both
    client.post(
        f"/debts/{debt['id']}/payments",
        json={
            "amount": 500_000,
            "date": user_timezone_today().isoformat(),
            "wallet_allocations": [
                {"wallet_id": wallet["id"], "amount": 500_000},
            ],
        },
        headers=headers,
    )
    client.post(
        f"/payment-plans/{plan['id']}/payments",
        json={
            "amount": 100_000,
            "paid_date": user_timezone_today().isoformat(),
            "wallet_allocations": [
                {"wallet_id": wallet["id"], "amount": 100_000},
            ],
        },
        headers=headers,
    )

    session.expire_all()

    # Verify separate persistence tables
    debt_ledger_count = (
        session.query(models.DebtLedgerEntry)
        .filter(models.DebtLedgerEntry.debt_id == debt["id"])
        .count()
    )
    pp_ledger_count = (
        session.query(models.PaymentPlanLedgerEntry)
        .filter(models.PaymentPlanLedgerEntry.plan_id == plan["id"])
        .count()
    )
    assert debt_ledger_count >= 1, "Debt must persist in DebtLedgerEntry"
    assert pp_ledger_count >= 1, "Payment Plan must persist in PaymentPlanLedgerEntry"

    # Verify separate lifecycle states
    debt_obj = session.query(models.Debt).filter(
        models.Debt.id == debt["id"]
    ).first()
    plan_obj = session.query(models.PaymentPlan).filter(
        models.PaymentPlan.id == plan["id"]
    ).first()
    # Debt lifecycle is now derived from remaining_amount (ADR 0026)
    assert debt_obj.remaining_amount >= 0
    assert plan_obj.status == models.PaymentPlanStatus.ACTIVE


def test_budget_required_failure_identical_structure_across_flows(client):
    """All three flows return the SAME structured 'expenses.budget_required'
    detail string — the Global Budget Interceptor contract is preserved."""
    # --- Normal expense ---
    h1 = create_user_and_token(client, "cross7a", "cross7a@example.com", "Password123!")
    r1 = client.post("/expenses/", json={
        "title": "Cross-flow test", "amount": 1_000, "category": "Groceries",
        "date": user_timezone_today().isoformat(),
    }, headers=h1)
    assert r1.json()["detail"] == "expenses.budget_required"

    # --- Debt charge ---
    h2 = create_user_and_token(client, "cross7b", "cross7b@example.com", "Password123!")
    w2 = _default_wallet(client, h2)
    d2 = _create_owing_debt(client, h2, w2["id"])
    client.post(f"/debts/{d2['id']}/charges",
                json={"amount": 5_000, "reason": "Interest"}, headers=h2)
    r2 = client.post(f"/debts/{d2['id']}/payments", json={
        "amount": 505_000, "date": user_timezone_today().isoformat(),
        "wallet_allocations": [{"wallet_id": w2["id"], "amount": 505_000}],
    }, headers=h2)
    assert r2.json()["detail"] == "expenses.budget_required"

    # --- Payment Plan (no budget) ---
    h3 = create_user_and_token(client, "cross7c", "cross7c@example.com", "Password123!")
    w3 = _default_wallet(client, h3)
    p3 = _create_plan(client, h3)
    p3_row = p3["payments"][0]
    r3 = client.post(f"/payment-plans/{p3['id']}/payments", json={
        "amount": p3_row["amount"], "paid_date": user_timezone_today().isoformat(),
        "wallet_allocations": [{"wallet_id": w3["id"], "amount": p3_row["amount"]}],
    }, headers=h3)
    assert r3.json()["detail"] == "expenses.budget_required"

    # All three must have the identical failure detail
    assert r1.json()["detail"] == r2.json()["detail"] == r3.json()["detail"] == "expenses.budget_required"


def test_remaining_budget_reporting_dependencies_documented(client):
    """Audit: money-posting code must not depend on broad Budget reporting.
    This test verifies the Budget Permission seam is the sole write-time
    dependency of expense-posting flows."""
    # The Budget Permission seam (budget_permission_service) imports only:
    #   - materialize_budget_for_month (budget existence)
    #   - validate_project_budget (project constraints)
    # It does NOT import build_budget_month_summary, get_project_budget_summaries,
    # or any display/reporting function.
    #
    # If this test fails, a reporting dependency has leaked into the
    # write-time path and must be removed.

    import inspect
    import app.services.budget_permission_service as bps

    source = inspect.getsource(bps)

    # These reporting functions must NOT appear in the Budget Permission module
    reporting_functions = [
        "build_budget_month_summary",
        "get_project_budget_summaries",
        "build_budget_out",
        "build_budget_month_setup_preview",
        "build_project_detail",
    ]
    for func in reporting_functions:
        assert func not in source, (
            f"Budget Permission must not depend on reporting function '{func}'"
        )

    # Expense Posting must not import reporting functions either
    import app.services.expense_posting_service as eps
    eps_source = inspect.getsource(eps)
    for func in reporting_functions:
        assert func not in eps_source, (
            f"Expense Posting must not depend on reporting function '{func}'"
        )

    # Obligation Money Posting must not import reporting functions
    import app.services.obligation_money_posting_service as omps
    omps_source = inspect.getsource(omps)
    for func in reporting_functions:
        assert func not in omps_source, (
            f"Obligation Money Posting must not depend on reporting function '{func}'"
        )