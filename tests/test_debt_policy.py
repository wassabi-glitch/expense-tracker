from datetime import datetime, timezone

from app import models
from app.services.debt_policy import (
    evaluate_debt_action,
    evaluate_debt_actions,
    evaluate_ledger_entry_reversal,
    is_formal_debt,
    is_informal_debt,
    is_pristine_debt,
)
from tests.helpers import create_user_and_token, user_timezone_today


def _user(session, email):
    return session.query(models.User).filter(models.User.email == email).first()


def _make_debt(session, user, **overrides):
    defaults = {
        "owner_id": user.id,
        "debt_type": models.DebtType.OWED,
        "origin_kind": models.DebtOriginKind.PERSONAL_REIMBURSEMENT,
        "counterparty_kind": models.DebtCounterpartyKind.PERSON,
        "counterparty_name": "Ali",
        "initial_amount": 500_000,
        "remaining_amount": 500_000,
        "currency": "UZS",
        "description": "Dinner split",
        "status": models.DebtStatus.ACTIVE,
        "date": user_timezone_today(),
        "expected_return_date": user_timezone_today(),
    }
    defaults.update(overrides)
    debt = models.Debt(**defaults)
    session.add(debt)
    session.flush()
    return debt


def test_informal_debt_allows_component_forgiveness_without_settlement_action(client, session):
    create_user_and_token(client, "policy1", "policy1@example.com", "Password123!")
    user = _user(session, "policy1@example.com")
    debt = _make_debt(session, user)

    assert is_informal_debt(debt)
    assert not is_formal_debt(debt)

    partial = evaluate_debt_action(session, debt, models.DebtActionKind.FORGIVE_PARTIAL)
    full = evaluate_debt_action(session, debt, models.DebtActionKind.FORGIVE_FULL)

    assert partial.allowed is True
    assert full.allowed is True
    action_names = {action.value for action in evaluate_debt_actions(session, debt)}
    assert "SETTLE" not in action_names


def test_formal_debt_uses_same_component_forgiveness_as_informal_debt(client, session):
    create_user_and_token(client, "policy2", "policy2@example.com", "Password123!")
    user = _user(session, "policy2@example.com")
    debt = _make_debt(
        session,
        user,
        debt_type=models.DebtType.OWING,
        origin_kind=models.DebtOriginKind.CASH_BORROWED,
        counterparty_kind=models.DebtCounterpartyKind.BANK,
        counterparty_name="Bank",
    )
    session.add(
        models.DebtFormalDetails(
            debt_id=debt.id,
            owner_id=user.id,
            institution_name="Bank",
            contract_number="LN-1",
        )
    )
    session.flush()

    assert is_formal_debt(debt)

    forgiveness = evaluate_debt_action(session, debt, models.DebtActionKind.FORGIVE_PARTIAL)
    collateral = evaluate_debt_action(session, debt, models.DebtActionKind.SET_COLLATERAL)

    assert forgiveness.allowed is True
    assert collateral.allowed is True


def test_legacy_payment_plan_link_does_not_create_managed_debt_policy(client, session):
    create_user_and_token(client, "policyplan", "policyplan@example.com", "Password123!")
    user = _user(session, "policyplan@example.com")
    debt = _make_debt(
        session,
        user,
        debt_type=models.DebtType.OWING,
        origin_kind=models.DebtOriginKind.FINANCED_ASSET_PURCHASE,
        counterparty_kind=models.DebtCounterpartyKind.STORE,
        counterparty_name="Store",
    )
    plan = models.PaymentPlan(
        owner_id=user.id,
        debt_id=debt.id,
        item_name="Phone",
        store_or_bank_name="Store",
        plan_type=models.PaymentPlanType.STORE_INSTALLMENT,
        total_price=500_000,
        down_payment=0,
        remaining_amount=500_000,
        months=5,
        payment_count=5,
        frequency=models.PaymentPlanFrequency.MONTHLY,
        monthly_payment_amount=100_000,
        regular_payment_amount=100_000,
        status=models.PaymentPlanStatus.ACTIVE,
        start_date=user_timezone_today(),
        expense_category=models.ExpenseCategory.ELECTRONICS,
    )
    session.add(plan)
    session.flush()

    payment = evaluate_debt_action(session, debt, models.DebtActionKind.RECORD_PAYMENT)
    charge = evaluate_debt_action(session, debt, models.DebtActionKind.ADD_CHARGE)
    assert payment.allowed is True
    assert charge.allowed is True


def test_pristine_debt_allows_only_initial_ledger_history(client, session):
    create_user_and_token(client, "policypristine", "policypristine@example.com", "Password123!")
    user = _user(session, "policypristine@example.com")
    debt = _make_debt(session, user)
    initial_entry = models.DebtLedgerEntry(
        owner_id=user.id,
        debt_id=debt.id,
        entry_type=models.DebtLedgerEntryType.INITIAL,
        amount_delta=500_000,
        principal_delta=500_000,
        entry_date=user_timezone_today(),
        status="POSTED",
    )
    session.add(initial_entry)
    session.flush()

    assert is_pristine_debt(session, debt) is True

    for entry_type in (
        models.DebtLedgerEntryType.CHARGE,
        models.DebtLedgerEntryType.PAYMENT,
        models.DebtLedgerEntryType.FORGIVENESS,
        models.DebtLedgerEntryType.ADJUSTMENT,
        models.DebtLedgerEntryType.ASSET_SETTLEMENT,
        models.DebtLedgerEntryType.REVERSAL,
    ):
        active_debt = _make_debt(session, user, counterparty_name=f"{entry_type.value} debt")
        session.add(
            models.DebtLedgerEntry(
                owner_id=user.id,
                debt_id=active_debt.id,
                entry_type=entry_type,
                amount_delta=-1,
                principal_delta=-1,
                entry_date=user_timezone_today(),
                status="POSTED",
            )
        )
        session.flush()

        assert is_pristine_debt(session, active_debt) is False


def test_closed_and_archived_debt_actions_are_restricted(client, session):
    create_user_and_token(client, "policy3", "policy3@example.com", "Password123!")
    user = _user(session, "policy3@example.com")
    paid_debt = _make_debt(
        session,
        user,
        status=models.DebtStatus.PAID,
        remaining_amount=0,
    )
    archived_debt = _make_debt(
        session,
        user,
        counterparty_name="Archived",
        status=models.DebtStatus.ARCHIVED,
    )
    open_debt = _make_debt(session, user, counterparty_name="Open archive candidate")

    payment = evaluate_debt_action(session, paid_debt, models.DebtActionKind.RECORD_PAYMENT)
    archive = evaluate_debt_action(session, paid_debt, models.DebtActionKind.ARCHIVE)
    open_archive = evaluate_debt_action(session, open_debt, models.DebtActionKind.ARCHIVE)
    archived_payment = evaluate_debt_action(session, archived_debt, models.DebtActionKind.RECORD_PAYMENT)
    restore = evaluate_debt_action(session, archived_debt, models.DebtActionKind.RESTORE)

    assert payment.allowed is False
    assert payment.reason_code == "debts.policy.closed_debt_immutable"
    assert archive.allowed is True
    assert open_archive.allowed is True
    assert archived_payment.allowed is False
    assert archived_payment.reason_code == "debts.policy.archived_immutable"
    assert restore.allowed is True


def test_archived_debt_immutability_and_restore_are_derived_from_archive_metadata(client, session):
    create_user_and_token(client, "policy4", "policy4@example.com", "Password123!")
    user = _user(session, "policy4@example.com")
    debt = _make_debt(session, user)
    debt.archived_at = datetime.now(timezone.utc)
    session.flush()

    charge = evaluate_debt_action(session, debt, models.DebtActionKind.ADD_CHARGE)
    restore = evaluate_debt_action(session, debt, models.DebtActionKind.RESTORE)

    assert charge.allowed is False
    assert charge.reason_code == "debts.policy.archived_immutable"
    assert restore.allowed is True


def test_ledger_entry_reversal_blocks_already_reversed_entries(client, session):
    create_user_and_token(client, "policy5", "policy5@example.com", "Password123!")
    user = _user(session, "policy5@example.com")
    debt = _make_debt(session, user)
    payment_entry = models.DebtLedgerEntry(
        owner_id=user.id,
        debt_id=debt.id,
        entry_type=models.DebtLedgerEntryType.PAYMENT,
        amount_delta=-100_000,
        principal_delta=-100_000,
        entry_date=user_timezone_today(),
        status="POSTED",
        is_reversible=True,
    )
    session.add(payment_entry)
    session.flush()

    allowed = evaluate_ledger_entry_reversal(session, debt, payment_entry)
    assert allowed.allowed is True

    session.add(
        models.DebtLedgerEntry(
            owner_id=user.id,
            debt_id=debt.id,
            entry_type=models.DebtLedgerEntryType.REVERSAL,
            amount_delta=100_000,
            principal_delta=100_000,
            reverses_entry_id=payment_entry.id,
            entry_date=user_timezone_today(),
            status="POSTED",
        )
    )
    session.flush()

    blocked = evaluate_ledger_entry_reversal(session, debt, payment_entry)
    assert blocked.allowed is False
    assert blocked.reason_code == "debts.policy.entry_already_reversed"
