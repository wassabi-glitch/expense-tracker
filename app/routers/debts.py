from collections import defaultdict
from datetime import date, datetime, timezone, tzinfo
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Response, status
# pyrefly: ignore [missing-import]
from sqlalchemy import func, or_
# pyrefly: ignore [missing-import]
from sqlalchemy.orm import Session, joinedload

from app.timezone import get_effective_user_timezone, today_in_tz
from app.utils import check_budget_alerts

from .. import models, oauth2, schemas
from ..redis_rate_limiter import consume_token_bucket
from ..services.debt_service import (
    POSTED_DEBT_LEDGER_STATUS,
    create_debt_ledger_entry,
    get_debt_total_charges,
    get_debt_total_charges_by_debt_ids,
    get_debt_total_paid,
    get_debt_total_paid_by_debt_ids,
    reconcile_debt,
    reverse_debt_transaction_ledger,
    reverse_wallet_effect,
)
from ..services.debt_payment_service import create_debt_payment as create_debt_payment_service
from ..services.debt_policy import (
    evaluate_debt_action,
    evaluate_debt_actions,
    evaluate_ledger_entry_reversal,
    is_pristine_debt,
)
from ..services.goal_funding_service import sync_debt_goal_targets, validate_wallet_goal_protection_for_outflow
from ..services.expense_posting_service import post_expense_event
from ..services.session_draft_service import validate_session_item_links
from ..services.wallet_service import WalletService
from ..session import get_db
from .wallets import _execute_wallet_transfer, _get_owned_wallet_or_404

router = APIRouter(
    prefix="/debts",
    tags=["Debts (Qarz)"],
)

DEBTS_WRITE_BUCKET_CAPACITY = 20
DEBTS_WRITE_REFILL_RATE = 20 / 60
CONSUMPTION_ORIGIN_KINDS = {
    models.DebtOriginKind.DEFERRED_EXPENSE,
    models.DebtOriginKind.FINANCED_ASSET_PURCHASE,
}
FORMAL_SCHEDULE_PRODUCT_KINDS = {
    models.DebtProductKind.MORTGAGE,
    models.DebtProductKind.CAR_LOAN,
    models.DebtProductKind.STORE_INSTALLMENT,
    models.DebtProductKind.SERVICE_PAY_LATER,
}
ACTIVE_PAYABLE_DEBT_STATUSES = (
    models.DebtStatus.ACTIVE,
    models.DebtStatus.OVERDUE,
    models.DebtStatus.DEFAULTED,
    models.DebtStatus.IN_COLLECTION,
)


def _is_debt_archived(debt: models.Debt) -> bool:
    return getattr(debt, "archived_at", None) is not None or debt.status == models.DebtStatus.ARCHIVED


def _debt_lifecycle_status(debt: models.Debt) -> schemas.DebtLifecycleStatus:
    if int(debt.remaining_amount or 0) <= 0:
        return schemas.DebtLifecycleStatus.CLOSED
    return schemas.DebtLifecycleStatus.OPEN


def _debt_time_status(
    debt: models.Debt,
    *,
    today: date | None = None,
) -> schemas.DebtTimeStatus | None:
    if _debt_lifecycle_status(debt) == schemas.DebtLifecycleStatus.CLOSED:
        return None
    due_date = getattr(debt, "expected_return_date", None)
    if due_date is not None and due_date < (today or date.today()):
        return schemas.DebtTimeStatus.OVERDUE
    return schemas.DebtTimeStatus.ON_TRACK


def _matches_debt_lifecycle_filter(debt: models.Debt, lifecycle_status: schemas.DebtLifecycleStatus | None) -> bool:
    if lifecycle_status is None:
        return True
    return _debt_lifecycle_status(debt) == lifecycle_status


def _matches_debt_time_filter(
    debt: models.Debt,
    time_status: schemas.DebtTimeStatus | None,
    *,
    today: date,
) -> bool:
    if time_status is None:
        return True
    return _debt_time_status(debt, today=today) == time_status


def enforce_debts_write_rate_limit(user_id: int) -> dict[str, str]:
    rl = consume_token_bucket(
        scope="debts_write",
        identifier=str(user_id),
        capacity=DEBTS_WRITE_BUCKET_CAPACITY,
        refill_rate_per_second=DEBTS_WRITE_REFILL_RATE,
    )
    headers = {
        "X-RateLimit-Limit": str(rl.limit),
        "X-RateLimit-Remaining": str(rl.remaining),
        "X-RateLimit-Reset": str(rl.reset_seconds),
    }
    if not rl.allowed:
        headers["Retry-After"] = str(rl.reset_seconds)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="debts.write_rate_limited",
            headers=headers,
        )
    return headers


def _apply_rate_limit_headers(response: Response, headers: dict[str, str]) -> None:
    for key, value in headers.items():
        response.headers[key] = value


def _get_owned_debt_or_404(db: Session, user_id: int, debt_id: int) -> models.Debt:
    debt = (
        db.query(models.Debt)
        .filter(models.Debt.id == debt_id, models.Debt.owner_id == user_id)
        .first()
    )
    if not debt:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="debts.not_found")
    return debt


def _resolve_wallet(db: Session, user_id: int, wallet_id: int | None) -> models.Wallet:
    if wallet_id is not None:
        return _get_owned_wallet_or_404(db, user_id, wallet_id)

    wallet = (
        db.query(models.Wallet)
        .filter(models.Wallet.owner_id == user_id, models.Wallet.is_default)
        .first()
    )
    if wallet:
        return wallet

    wallet = db.query(models.Wallet).filter(models.Wallet.owner_id == user_id).first()
    if not wallet:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="wallets.at_least_one_required",
        )
    return wallet


def _infer_debt_origin_kind(payload: schemas.DebtCreate) -> models.DebtOriginKind:
    if "origin_kind" in payload.model_fields_set:
        return payload.origin_kind
    money_moved = payload.is_money_transferred or bool(payload.initial_wallet_allocations)
    if payload.debt_type == models.DebtType.OWING:
        return (
            models.DebtOriginKind.CASH_BORROWED
            if money_moved
            else models.DebtOriginKind.DEFERRED_EXPENSE
        )
    if money_moved:
        return models.DebtOriginKind.CASH_LENT
    if payload.income_source_id is not None:
        return models.DebtOriginKind.RECEIVABLE_INCOME
    return models.DebtOriginKind.PERSONAL_REIMBURSEMENT


def _infer_debt_product_kind(
    payload: schemas.DebtCreate,
    origin_kind: models.DebtOriginKind,
) -> models.DebtProductKind:
    if payload.product_kind is not None:
        return payload.product_kind
    if origin_kind == models.DebtOriginKind.RECEIVABLE_INCOME:
        return models.DebtProductKind.CLIENT_RECEIVABLE
    if origin_kind in (
        models.DebtOriginKind.SPLIT_REIMBURSEMENT,
        models.DebtOriginKind.PERSONAL_REIMBURSEMENT,
    ):
        return models.DebtProductKind.PERSONAL_REIMBURSEMENT
    return models.DebtProductKind.INFORMAL_DEBT


def _infer_counterparty_kind(
    payload: schemas.DebtCreate,
    origin_kind: models.DebtOriginKind,
) -> models.DebtCounterpartyKind:
    if "counterparty_kind" in payload.model_fields_set:
        return payload.counterparty_kind
    if origin_kind in (
        models.DebtOriginKind.CASH_BORROWED,
        models.DebtOriginKind.CASH_LENT,
        models.DebtOriginKind.DEFERRED_EXPENSE,
        models.DebtOriginKind.SPLIT_REIMBURSEMENT,
        models.DebtOriginKind.PERSONAL_REIMBURSEMENT,
        models.DebtOriginKind.DAMAGE_COMPENSATION,
    ):
        return models.DebtCounterpartyKind.PERSON
    return models.DebtCounterpartyKind.OTHER


def _debt_txn_marker(transaction_id: int) -> str:
    return f"[debt_txn:{transaction_id}]"


def _debt_initial_marker(debt_id: int) -> str:
    return f"[debt_initial:{debt_id}]"


def _append_marker(description: str, marker: str) -> str:
    return f"{description} {marker}".strip()


def _debt_event_query(db: Session, owner_id: int, debt_id: int):
    return (
        db.query(models.FinancialEvent)
        .join(models.EntityLedger, models.EntityLedger.event_id == models.FinancialEvent.id)
        .filter(
            models.FinancialEvent.owner_id == owner_id,
            models.EntityLedger.debt_id == debt_id,
        )
        .options(
            joinedload(models.FinancialEvent.wallet_legs).joinedload(models.WalletLedger.wallet),
            joinedload(models.FinancialEvent.entity_legs),
        )
    )


def _find_payment_events(
    db: Session,
    owner_id: int,
    debt_id: int,
    debt_transaction_id: int,
) -> list[models.FinancialEvent]:
    marker = _debt_txn_marker(debt_transaction_id)
    return (
        _debt_event_query(db, owner_id, debt_id)
        .filter(models.FinancialEvent.description.like(f"%{marker}%"))
        .order_by(models.FinancialEvent.id.asc())
        .all()
    )


def _find_all_debt_events(
    db: Session,
    owner_id: int,
    debt_id: int,
) -> list[models.FinancialEvent]:
    return _debt_event_query(db, owner_id, debt_id).order_by(models.FinancialEvent.id.asc()).all()


def _update_event_amounts(
    event: models.FinancialEvent,
    signed_wallet_amount: int,
    absolute_entity_amount: int,
) -> None:
    if event.wallet_legs:
        event.wallet_legs[0].amount = signed_wallet_amount
    if event.entity_legs:
        event.entity_legs[0].amount = absolute_entity_amount


def _build_debt_out(
    debt: models.Debt,
    total_charges: int = 0,
    total_paid: int = 0,
    remaining_principal_amount: int = 0,
    remaining_charge_amount: int = 0,
    has_archived_transactions: bool = False,
    today: date | None = None,
) -> schemas.DebtOut:
    debt_out = schemas.DebtOut.model_validate(debt)
    debt_out.lifecycle_status = _debt_lifecycle_status(debt)
    debt_out.time_status = _debt_time_status(debt, today=today)
    debt_out.is_archived = _is_debt_archived(debt)
    debt_out.total_charges = int(total_charges)
    debt_out.total_paid = int(total_paid)
    debt_out.remaining_principal_amount = int(remaining_principal_amount)
    debt_out.remaining_charge_amount = int(remaining_charge_amount)
    debt_out.has_archived_transactions = has_archived_transactions
    debt_out.workflow_warnings = _debt_workflow_warnings(debt, today=today)
    return debt_out


def _build_debt_out_with_ledger_totals(
    db: Session,
    debt: models.Debt,
    *,
    has_archived_transactions: bool = False,
    today: date | None = None,
) -> schemas.DebtOut:
    principal_balance, charge_balance = _debt_component_balances(db, debt)
    return _build_debt_out(
        debt,
        total_charges=get_debt_total_charges(db, debt.id),
        total_paid=get_debt_total_paid(db, debt.id),
        remaining_principal_amount=principal_balance,
        remaining_charge_amount=charge_balance,
        has_archived_transactions=has_archived_transactions,
        today=today,
    )


def _is_wallet_backed_obligation(wallet: models.Wallet) -> bool:
    if int(wallet.current_balance or 0) >= 0:
        return False
    if wallet.wallet_type == models.WalletType.CREDIT:
        return True
    return wallet.wallet_type == models.WalletType.DEBIT and bool(wallet.has_overdraft)


def _build_wallet_obligation_out(wallet: models.Wallet) -> schemas.DebtOut:
    amount = abs(int(wallet.current_balance or 0))
    return schemas.DebtOut(
        id=-int(wallet.id),
        owner_id=int(wallet.owner_id),
        debt_type=models.DebtType.OWING,
        origin_kind=models.DebtOriginKind.IMPORTED_BALANCE,
        counterparty_kind=models.DebtCounterpartyKind.OTHER,
        product_kind=None,
        counterparty_name=wallet.name,
        initial_amount=amount,
        remaining_amount=amount,
        currency=wallet.currency,
        description="Wallet-backed liability",
        date=wallet.created_at.date() if wallet.created_at is not None else date.today(),
        expected_return_date=None,
        lifecycle_status=schemas.DebtLifecycleStatus.OPEN,
        time_status=schemas.DebtTimeStatus.ON_TRACK,
        archived_at=None,
        is_archived=False,
        created_at=wallet.created_at or datetime.now(timezone.utc),
        updated_at=wallet.updated_at or wallet.created_at or datetime.now(timezone.utc),
        is_money_transferred=False,
        initial_wallet_id=wallet.id,
        has_archived_transactions=not bool(wallet.is_active),
        total_charges=0,
        total_paid=0,
        remaining_principal_amount=amount,
        remaining_charge_amount=0,
        expense_category=None,
        expense_subcategory_id=None,
        project_id=None,
        project_subcategory_id=None,
        income_source_id=None,
        workflow_warnings=[],
        source_type="WALLET",
        wallet_id=wallet.id,
        wallet_name=wallet.name,
        wallet_type=wallet.wallet_type,
        available_actions=["wallet_transfer_payoff"],
    )


def _debt_workflow_warnings(debt: models.Debt, *, today: date | None = None) -> list[str]:
    warnings: list[str] = []
    if _is_debt_archived(debt):
        return warnings

    if debt.product_kind in FORMAL_SCHEDULE_PRODUCT_KINDS:
        warnings.append("debts.warning.formal_scheduled_debt_consider_payment_plan")
    if (
        debt.debt_type == models.DebtType.OWING
        and _debt_lifecycle_status(debt) == schemas.DebtLifecycleStatus.OPEN
    ):
        effective_today = today or date.today()
        if debt.expected_return_date is None:
            warnings.append("debts.suggestion.open_ended_paydown")
        elif debt.expected_return_date < effective_today:
            warnings.append("debts.warning.payable_overdue_hard")
        else:
            warnings.append("debts.warning.payable_due_hard")
    if (
        debt.debt_type == models.DebtType.OWED
        and _debt_lifecycle_status(debt) == schemas.DebtLifecycleStatus.OPEN
    ):
        warnings.append("debts.warning.receivable_expected_payment_requires_explicit_plan")
    return warnings


def _validate_debt_planning_links(
    db: Session,
    owner_id: int,
    *,
    origin_kind: models.DebtOriginKind,
    expense_category: models.ExpenseCategory | None,
    expense_subcategory_id: int | None,
    project_id: int | None,
    project_subcategory_id: int | None,
) -> None:
    if origin_kind in CONSUMPTION_ORIGIN_KINDS:
        if expense_category is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="debts.validation.expense_category.required",
            )
        if expense_category == models.ExpenseCategory.PAYMENT_PLANS_DEBT:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="debts.validation.real_expense_category_required",
            )

    if expense_subcategory_id is not None or project_id is not None or project_subcategory_id is not None:
        if expense_category is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="debts.validation.expense_category.required_for_links",
            )
        validate_session_item_links(
            db,
            owner_id,
            expense_category,
            expense_subcategory_id,
            project_id,
            project_subcategory_id,
        )


def _validate_income_source_link(db: Session, owner_id: int, income_source_id: int | None) -> None:
    if income_source_id is None:
        return
    source = (
        db.query(models.IncomeSource)
        .filter(
            models.IncomeSource.id == income_source_id,
            models.IncomeSource.owner_id == owner_id,
        )
        .first()
    )
    if source is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="income.source_not_found")
    if not source.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="income.source_inactive")


def _validate_debt_income_semantics(
    db: Session,
    owner_id: int,
    *,
    origin_kind: models.DebtOriginKind,
    income_source_id: int | None,
) -> None:
    if origin_kind == models.DebtOriginKind.RECEIVABLE_INCOME and income_source_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="debts.validation.income_source.required",
        )
    _validate_income_source_link(db, owner_id, income_source_id)


def _build_debt_transaction_out(
    transaction: models.DebtTransaction,
) -> schemas.DebtTransactionOut:
    wallet = schemas.WalletOut.model_validate(transaction.wallet) if transaction.wallet else None
    wallet_allocations = [
        schemas.DebtTransactionWalletAllocationOut.model_validate(allocation)
        for allocation in (transaction.wallet_allocations or [])
    ]
    return schemas.DebtTransactionOut(
        id=transaction.id,
        owner_id=transaction.owner_id,
        debt_id=transaction.debt_id,
        amount=int(transaction.amount),
        date=transaction.date,
        note=transaction.note,
        wallet_id=transaction.wallet_id,
        created_at=transaction.created_at,
        wallet=wallet,
        wallet_allocations=wallet_allocations,
    )


def _build_action_decision_out(decision) -> schemas.DebtActionDecisionOut:
    return schemas.DebtActionDecisionOut(**decision.to_dict())


def _build_action_decisions_out(
    db: Session,
    debt: models.Debt,
) -> list[schemas.DebtActionDecisionOut]:
    return [
        _build_action_decision_out(decision)
        for decision in evaluate_debt_actions(db, debt).values()
    ]


def _raise_policy_denied(decision) -> None:
    if not decision.allowed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=decision.reason_code or "debts.policy.action_blocked",
        )


def _reconcile_debt_preserving_lifecycle(db: Session, debt: models.Debt) -> models.Debt:
    previous_status = debt.status
    reconciled = reconcile_debt(db, debt.id)
    if (
        int(reconciled.remaining_amount or 0) > 0
        and previous_status
        in (
            models.DebtStatus.OVERDUE,
            models.DebtStatus.DEFAULTED,
            models.DebtStatus.IN_COLLECTION,
        )
    ):
        reconciled.status = previous_status
        db.flush()
    return reconciled


def _posted_charge_balance(db: Session, debt_id: int) -> int:
    return max(
        0,
        int(
            db.query(func.coalesce(func.sum(models.DebtLedgerEntry.charge_delta), 0))
            .filter(
                models.DebtLedgerEntry.debt_id == debt_id,
                models.DebtLedgerEntry.status == POSTED_DEBT_LEDGER_STATUS,
            )
            .scalar()
            or 0
        ),
    )


def _posted_principal_balance(db: Session, debt_id: int) -> int:
    return max(
        0,
        int(
            db.query(func.coalesce(func.sum(models.DebtLedgerEntry.principal_delta), 0))
            .filter(
                models.DebtLedgerEntry.debt_id == debt_id,
                models.DebtLedgerEntry.status == POSTED_DEBT_LEDGER_STATUS,
            )
            .scalar()
            or 0
        ),
    )


def _debt_component_balances(db: Session, debt: models.Debt) -> tuple[int, int]:
    charge_balance = _posted_charge_balance(db, debt.id)
    principal_balance = _posted_principal_balance(db, debt.id)
    remaining = int(debt.remaining_amount or 0)
    component_total = principal_balance + charge_balance
    if component_total != remaining:
        principal_balance = max(0, remaining - charge_balance)
    return principal_balance, charge_balance


def _split_amount_between_charges_and_principal(
    db: Session,
    debt: models.Debt,
    amount: int,
) -> tuple[int, int]:
    principal_balance, charge_balance = _debt_component_balances(db, debt)
    principal_amount = min(int(amount), int(principal_balance))
    charge_amount = int(amount) - principal_amount
    return principal_amount, charge_amount


def _forgiveness_component_amounts(
    db: Session,
    debt: models.Debt,
    amount: int,
    component: schemas.DebtForgivenessComponent | None,
) -> tuple[int, int, str]:
    principal_balance, charge_balance = _debt_component_balances(db, debt)
    remaining = int(debt.remaining_amount or 0)
    if component is None:
        if int(amount) != remaining:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="debts.forgiveness.component_required",
            )
        component = schemas.DebtForgivenessComponent.TOTAL

    if component == schemas.DebtForgivenessComponent.PRINCIPAL:
        if int(amount) > principal_balance:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="debts.forgiveness.amount_too_high")
        return int(amount), 0, "PRINCIPAL_FORGIVE"
    if component == schemas.DebtForgivenessComponent.CHARGES:
        if int(amount) > charge_balance:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="debts.forgiveness.amount_too_high")
        return 0, int(amount), "CHARGE_WAIVER"

    if int(amount) != remaining:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="debts.forgiveness.total_requires_full_remaining",
        )
    return principal_balance, charge_balance, "FULL_FORGIVE"


def _balance_correction_deltas(
    db: Session,
    debt: models.Debt,
    payload: schemas.DebtBalanceAdjustmentCreate,
) -> tuple[int, int, int, str, dict]:
    principal_balance, charge_balance = _debt_component_balances(db, debt)
    remaining = int(debt.remaining_amount or 0)
    component = payload.component

    if component == schemas.DebtBalanceCorrectionComponent.PRINCIPAL:
        if payload.confirmed_principal_balance is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="debts.adjustment.principal_required")
        principal_delta = int(payload.confirmed_principal_balance) - principal_balance
        return principal_delta, principal_delta, 0, "PRINCIPAL_CORRECTION", {
            "component": component.value,
            "before_principal": principal_balance,
            "after_principal": int(payload.confirmed_principal_balance),
        }

    if component == schemas.DebtBalanceCorrectionComponent.CHARGES:
        if payload.confirmed_charge_balance is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="debts.adjustment.charges_required")
        charge_delta = int(payload.confirmed_charge_balance) - charge_balance
        return charge_delta, 0, charge_delta, "CHARGE_CORRECTION", {
            "component": component.value,
            "before_charges": charge_balance,
            "after_charges": int(payload.confirmed_charge_balance),
        }

    if payload.confirmed_balance is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="debts.adjustment.confirmed_balance_required")
    delta = int(payload.confirmed_balance) - remaining
    return delta, delta, 0, "TOTAL_BALANCE_CORRECTION", {
        "component": component.value,
        "allocation_strategy": "TOTAL_DIFFERENCE_ALLOCATED_TO_PRINCIPAL",
        "before_total": remaining,
        "after_total": int(payload.confirmed_balance),
        "before_principal": principal_balance,
        "before_charges": charge_balance,
    }


def _activity_title(entry: models.DebtLedgerEntry) -> str:
    if entry.event_subtype == "PAYMENT_PLAN_WRITE_OFF":
        return "Payment plan payment written off"
    if entry.entry_type == models.DebtLedgerEntryType.INITIAL:
        return "Debt created"
    if entry.entry_type == models.DebtLedgerEntryType.PAYMENT:
        return "Payment recorded"
    if entry.entry_type == models.DebtLedgerEntryType.CHARGE:
        return "Charge added"
    if entry.entry_type == models.DebtLedgerEntryType.FORGIVENESS:
        return "Balance forgiven"
    if entry.entry_type == models.DebtLedgerEntryType.ADJUSTMENT:
        return "Balance adjusted"
    if entry.entry_type == models.DebtLedgerEntryType.ASSET_SETTLEMENT:
        return "Asset settlement"
    if entry.entry_type == models.DebtLedgerEntryType.REVERSAL:
        return "Action reversed"
    return "Debt activity"


def _build_activity_item(
    db: Session,
    debt: models.Debt,
    entry: models.DebtLedgerEntry,
) -> schemas.DebtActivityItemOut:
    return schemas.DebtActivityItemOut(
        ledger_entry_id=entry.id,
        kind=entry.entry_type,
        title=_activity_title(entry),
        description=entry.note,
        amount_delta=int(entry.amount_delta),
        principal_delta=int(entry.principal_delta or 0),
        charge_delta=int(entry.charge_delta or 0),
        balance_after=entry.balance_after,
        event_subtype=entry.event_subtype,
        entry_date=entry.entry_date,
        created_at=entry.created_at,
        source=entry.source,
        is_reversible=bool(entry.is_reversible),
        reversal=_build_action_decision_out(evaluate_ledger_entry_reversal(db, debt, entry)),
        financial_event_id=entry.financial_event_id,
        source_debt_transaction_id=entry.source_debt_transaction_id,
        source_debt_charge_id=entry.source_debt_charge_id,
        reverses_entry_id=entry.reverses_entry_id,
        wallet_id=entry.wallet_id,
        asset_id=entry.asset_id,
    )


def _validate_payment_wallet_allocations(
    db: Session,
    debt: models.Debt,
    allocations: list[schemas.DebtTransactionWalletAllocationIn],
    expected_total: int,
) -> list[tuple[models.Wallet, int]]:
    if expected_total <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="debts.payment.amount_required")
    if not allocations:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="debts.payment.wallet_allocations_required")

    total = sum(int(item.amount) for item in allocations)
    if total != int(expected_total):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="debts.payment.wallet_total_mismatch")

    seen_wallet_ids: set[int] = set()
    validated: list[tuple[models.Wallet, int]] = []
    is_outflow = debt.debt_type == models.DebtType.OWING
    for allocation in allocations:
        if allocation.wallet_id in seen_wallet_ids:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="debts.payment.wallet_duplicate")
        seen_wallet_ids.add(allocation.wallet_id)
        wallet = _get_owned_wallet_or_404(db, debt.owner_id, allocation.wallet_id)
        if not wallet.is_active:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="wallets.archived_locked")
        if is_outflow:
            validate_wallet_goal_protection_for_outflow(
                db,
                debt.owner_id,
                wallet,
                int(allocation.amount),
                outflow_type="debt_payment",
                error_code="wallets.goal_protection_conflict",
            )
        validated.append((wallet, int(allocation.amount)))
    return validated


def _payment_direction_multiplier(debt: models.Debt) -> int:
    return 1 if debt.debt_type == models.DebtType.OWED else -1


def _record_event_for_debt(
    db: Session,
    debt: models.Debt,
    wallet_id: int,
    transaction_type: models.TransactionType,
    amount_delta: int,
    title: str,
    description: str,
    transaction_date: date,
    category: models.ExpenseCategory | None = None,
    income_source_id: int | None = None,
    reference_type: str | None = None,
) -> models.FinancialEvent:
    if amount_delta < 0:
        wallet = _get_owned_wallet_or_404(db, debt.owner_id, wallet_id)
        validate_wallet_goal_protection_for_outflow(
            db,
            debt.owner_id,
            wallet,
            abs(int(amount_delta)),
            outflow_type="debt_payment",
            error_code="wallets.goal_protection_conflict",
        )
    return WalletService.record_transaction(
        db=db,
        owner_id=debt.owner_id,
        wallet_id=wallet_id,
        transaction_type=transaction_type,
        amount_delta=amount_delta,
        title=title,
        description=description,
        category=category,
        income_source_id=income_source_id,
        debt_id=debt.id,
        transaction_date=transaction_date,
        reference_type=reference_type,
    )


def _resolve_initial_wallet_allocations(
    db: Session,
    owner_id: int,
    payload: schemas.DebtCreate,
) -> list[tuple[models.Wallet, int]]:
    raw_allocations = list(payload.initial_wallet_allocations or [])

    if not raw_allocations and payload.is_money_transferred and payload.initial_wallet_id is not None:
        raw_allocations = [
            schemas.DebtInitialWalletAllocationIn(
                wallet_id=payload.initial_wallet_id,
                amount=payload.initial_amount,
            )
        ]

    if not raw_allocations:
        if payload.is_money_transferred:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="wallets.at_least_one_required")
        return []

    seen_wallet_ids: set[int] = set()
    resolved: list[tuple[models.Wallet, int]] = []
    is_outflow = payload.debt_type == models.DebtType.OWED

    for allocation in raw_allocations:
        if allocation.wallet_id in seen_wallet_ids:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="debts.initial.wallet_duplicate")
        seen_wallet_ids.add(allocation.wallet_id)

        wallet = _get_owned_wallet_or_404(db, owner_id, allocation.wallet_id)
        if not wallet.is_active:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="wallets.archived_locked")
        if is_outflow:
            validate_wallet_goal_protection_for_outflow(
                db,
                owner_id,
                wallet,
                int(allocation.amount),
                outflow_type="debt_initial",
                error_code="wallets.goal_protection_conflict",
            )
        resolved.append((wallet, int(allocation.amount)))

    return resolved


def _initial_transfer_reference_type(debt: models.Debt) -> str:
    if (
        debt.debt_type == models.DebtType.OWING
        and debt.origin_kind == models.DebtOriginKind.CASH_BORROWED
        and debt.counterparty_kind == models.DebtCounterpartyKind.BANK
    ):
        return models.ReferenceType.LOAN_DISBURSEMENT
    if (
        debt.debt_type == models.DebtType.OWING
        and debt.product_kind == models.DebtProductKind.BANK_LOAN
    ):
        return models.ReferenceType.LOAN_DISBURSEMENT
    return models.ReferenceType.DEBT_INITIAL


def _record_initial_transfer_event(
    db: Session,
    debt: models.Debt,
    wallet_allocations: list[tuple[models.Wallet, int]],
) -> models.FinancialEvent:
    if not wallet_allocations:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="wallets.at_least_one_required")

    event = models.FinancialEvent(
        owner_id=debt.owner_id,
        title=f"{debt.counterparty_name}"[:100],
        description=_append_marker(
            f"Initial transfer for {debt.counterparty_name}",
            _debt_initial_marker(debt.id),
        ),
        event_type=models.TransactionType.DEBT_SETTLEMENT,
        reference_type=_initial_transfer_reference_type(debt),
        date=debt.date,
    )
    db.add(event)
    db.flush()

    direction = 1 if debt.debt_type == models.DebtType.OWING else -1
    for wallet, allocation_amount in wallet_allocations:
        signed_amount = direction * int(allocation_amount)
        WalletService.adjust_balance(
            db,
            wallet.id,
            signed_amount,
            models.TransactionType.DEBT_SETTLEMENT,
        )
        db.add(
            models.WalletLedger(
                owner_id=debt.owner_id,
                event_id=event.id,
                wallet_id=wallet.id,
                amount=signed_amount,
            )
        )

    db.add(
        models.EntityLedger(
            event_id=event.id,
            label=f"Initial debt for {debt.counterparty_name}"[:100],
            amount=int(debt.initial_amount),
            debt_id=debt.id,
        )
    )
    db.flush()
    return event


def _principal_payment_event_classification(
    debt: models.Debt,
    income_source_id: int | None = None,
) -> tuple[models.TransactionType, models.ExpenseCategory | None, int | None, str | None]:
    transaction_type = models.TransactionType.DEBT_SETTLEMENT
    category = None
    effective_income_source_id = None
    reference_type = models.ReferenceType.DEBT_REPAYMENT

    if not debt.is_money_transferred:
        if debt.origin_kind == models.DebtOriginKind.DAMAGE_COMPENSATION:
            reference_type = models.ReferenceType.DAMAGE_COMPENSATION
            if debt.debt_type == models.DebtType.OWING:
                transaction_type = models.TransactionType.EXPENSE
                category = debt.expense_category
        elif debt.expense_category and debt.debt_type == models.DebtType.OWING:
            transaction_type = models.TransactionType.EXPENSE
            category = debt.expense_category
            reference_type = models.ReferenceType.DEBT_EXPENSE
        elif debt.income_source_id and debt.debt_type == models.DebtType.OWED:
            transaction_type = models.TransactionType.INCOME
            effective_income_source_id = income_source_id or debt.income_source_id
            reference_type = models.ReferenceType.DEBT_INCOME

    return transaction_type, category, effective_income_source_id, reference_type


def _charge_payment_event_classification(
    debt: models.Debt,
    income_source_id: int | None = None,
) -> tuple[models.TransactionType, models.ExpenseCategory | None, int | None, str]:
    if debt.debt_type == models.DebtType.OWING:
        return (
            models.TransactionType.EXPENSE,
            models.ExpenseCategory.DEBT_CHARGES,
            None,
            models.ReferenceType.DEBT_CHARGE,
        )
    return (
        models.TransactionType.INCOME,
        None,
        income_source_id or debt.income_source_id,
        models.ReferenceType.DEBT_CHARGE,
    )


def _split_wallet_allocations_principal_first(
    allocations: list[tuple[models.Wallet, int]],
    *,
    principal_amount: int,
    charge_amount: int,
) -> tuple[list[tuple[models.Wallet, int]], list[tuple[models.Wallet, int]]]:
    principal_remaining = int(principal_amount)
    charge_remaining = int(charge_amount)
    principal_allocations: list[tuple[models.Wallet, int]] = []
    charge_allocations: list[tuple[models.Wallet, int]] = []

    for wallet, allocation_amount in allocations:
        remaining = int(allocation_amount)
        if principal_remaining > 0:
            principal_part = min(remaining, principal_remaining)
            if principal_part > 0:
                principal_allocations.append((wallet, principal_part))
                remaining -= principal_part
                principal_remaining -= principal_part

        if remaining > 0 and charge_remaining > 0:
            charge_part = min(remaining, charge_remaining)
            if charge_part > 0:
                charge_allocations.append((wallet, charge_part))
                remaining -= charge_part
                charge_remaining -= charge_part

    if principal_remaining != 0 or charge_remaining != 0:
        raise ValueError("debts.payment.wallet_component_allocation_mismatch")

    return principal_allocations, charge_allocations


def _record_wallet_allocated_debt_event(
    db: Session,
    debt: models.Debt,
    debt_transaction: models.DebtTransaction,
    allocations: list[tuple[models.Wallet, int]],
    *,
    transaction_type: models.TransactionType,
    reference_type: str,
    category: models.ExpenseCategory | None,
    income_source_id: int | None,
    description_suffix: str | None = None,
) -> models.FinancialEvent:
    direction_mult = _payment_direction_multiplier(debt)
    description = debt_transaction.note or f"Payment for {debt.counterparty_name}"
    if description_suffix:
        description = f"{description} - {description_suffix}"
    description = _append_marker(description, _debt_txn_marker(debt_transaction.id))
    event_amount = sum(int(allocation_amount) for _, allocation_amount in allocations)

    if transaction_type == models.TransactionType.EXPENSE:
        if category is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="expenses.category_required")
        use_debt_planning_links = category == debt.expense_category
        posted = post_expense_event(
            db,
            debt.owner_id,
            title=f"{debt.counterparty_name}"[:32],
            amount=int(event_amount),
            category=category,
            expense_date=debt_transaction.date,
            description=description,
            wallet_allocations=[
                {"wallet_id": wallet.id, "amount": int(allocation_amount)}
                for wallet, allocation_amount in allocations
            ],
            subcategory_id=debt.expense_subcategory_id if use_debt_planning_links else None,
            project_id=debt.project_id if use_debt_planning_links else None,
            project_subcategory_id=debt.project_subcategory_id if use_debt_planning_links else None,
            reference_type=reference_type,
            enforce_goal_protection=False,
            debt_id=debt.id,
        )
        check_budget_alerts(db, posted.budget)
        return posted.event

    event = models.FinancialEvent(
        owner_id=debt.owner_id,
        title=f"{debt.counterparty_name}"[:32],
        description=description,
        event_type=transaction_type,
        reference_type=reference_type,
        date=debt_transaction.date,
    )
    db.add(event)
    db.flush()

    for wallet, allocation_amount in allocations:
        signed_amount = int(allocation_amount) * direction_mult
        WalletService.adjust_balance(db, wallet.id, signed_amount, transaction_type)
        db.add(
            models.WalletLedger(
                owner_id=debt.owner_id,
                event_id=event.id,
                wallet_id=wallet.id,
                amount=signed_amount,
            )
        )

    db.add(
        models.EntityLedger(
            event_id=event.id,
            label=debt_transaction.note,
            amount=int(event_amount),
            category=category,
            subcategory_id=debt.expense_subcategory_id if category else None,
            project_id=debt.project_id if category else None,
            project_subcategory_id=debt.project_subcategory_id if category else None,
            debt_id=debt.id,
            income_source_id=income_source_id,
        )
    )
    db.flush()
    return event


def _record_debt_payment_financial_events(
    db: Session,
    debt: models.Debt,
    debt_transaction: models.DebtTransaction,
    allocations: list[tuple[models.Wallet, int]],
    *,
    principal_amount: int,
    charge_amount: int,
    income_source_id: int | None = None,
) -> dict[str, models.FinancialEvent]:
    principal_allocations, charge_allocations = _split_wallet_allocations_principal_first(
        allocations,
        principal_amount=principal_amount,
        charge_amount=charge_amount,
    )
    events: dict[str, models.FinancialEvent] = {}

    if principal_allocations:
        transaction_type, category, effective_income_source_id, reference_type = _principal_payment_event_classification(
            debt,
            income_source_id=income_source_id,
        )
        events["principal"] = _record_wallet_allocated_debt_event(
            db,
            debt,
            debt_transaction,
            principal_allocations,
            transaction_type=transaction_type,
            reference_type=reference_type,
            category=category,
            income_source_id=effective_income_source_id,
            description_suffix="principal",
        )

    if charge_allocations:
        transaction_type, category, effective_income_source_id, reference_type = _charge_payment_event_classification(
            debt,
            income_source_id=income_source_id,
        )
        events["charge"] = _record_wallet_allocated_debt_event(
            db,
            debt,
            debt_transaction,
            charge_allocations,
            transaction_type=transaction_type,
            reference_type=reference_type,
            category=category,
            income_source_id=effective_income_source_id,
            description_suffix="charge",
        )

    return events


def _create_debt_payment(
    db: Session,
    debt: models.Debt,
    *,
    amount: int,
    transaction_date: date,
    wallet_allocations: list[schemas.DebtTransactionWalletAllocationIn],
    note: str | None = None,
    income_source_id: int | None = None,
    principal_amount_override: int | None = None,
    charge_amount_override: int | None = None,
) -> tuple[models.DebtTransaction, models.DebtLedgerEntry]:
    debt = (
        db.query(models.Debt)
        .filter(models.Debt.id == debt.id, models.Debt.owner_id == debt.owner_id)
        .with_for_update()
        .first()
    )
    if not debt:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="debts.not_found")
    if int(debt.remaining_amount or 0) < int(amount):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="debts.transaction.amount_too_high")

    validated_allocations = _validate_payment_wallet_allocations(db, debt, wallet_allocations, amount)
    primary_wallet = validated_allocations[0][0]
    debt_transaction = models.DebtTransaction(
        owner_id=debt.owner_id,
        wallet_id=primary_wallet.id,
        debt_id=debt.id,
        amount=int(amount),
        date=transaction_date,
        note=note,
    )
    db.add(debt_transaction)
    db.flush()

    for wallet, allocation_amount in validated_allocations:
        db.add(
            models.DebtTransactionWalletAllocation(
                owner_id=debt.owner_id,
                debt_id=debt.id,
                debt_transaction_id=debt_transaction.id,
                wallet_id=wallet.id,
                amount=int(allocation_amount),
            )
        )

    if principal_amount_override is None and charge_amount_override is None:
        principal_amount, charge_amount = _split_amount_between_charges_and_principal(db, debt, amount)
    else:
        principal_amount = int(principal_amount_override or 0)
        charge_amount = int(charge_amount_override or 0)
        if principal_amount < 0 or charge_amount < 0 or principal_amount + charge_amount != int(amount):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="debts.payment.invalid_component_split")

        charge_balance = _posted_charge_balance(db, debt.id)
        principal_balance = max(0, int(debt.remaining_amount or 0) - int(charge_balance))
        if principal_amount > principal_balance or charge_amount > charge_balance:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="debts.transaction.amount_too_high")

    payment_events = _record_debt_payment_financial_events(
        db,
        debt,
        debt_transaction,
        validated_allocations,
        principal_amount=principal_amount,
        charge_amount=charge_amount,
        income_source_id=income_source_id,
    )
    ledger_entries: list[models.DebtLedgerEntry] = []
    if principal_amount > 0:
        ledger_entries.append(
            create_debt_ledger_entry(
                db,
                owner_id=debt.owner_id,
                debt_id=debt.id,
                entry_type=models.DebtLedgerEntryType.PAYMENT,
                amount_delta=-int(principal_amount),
                principal_delta=-int(principal_amount),
                source_debt_transaction_id=debt_transaction.id,
                financial_event_id=payment_events.get("principal").id if payment_events.get("principal") else None,
                wallet_id=primary_wallet.id,
                event_subtype="PRINCIPAL_PAYMENT",
                entry_date=transaction_date,
                note=note or f"Payment for {debt.counterparty_name}",
            )
        )
    if charge_amount > 0:
        ledger_entries.append(
            create_debt_ledger_entry(
                db,
                owner_id=debt.owner_id,
                debt_id=debt.id,
                entry_type=models.DebtLedgerEntryType.PAYMENT,
                amount_delta=-int(charge_amount),
                charge_delta=-int(charge_amount),
                source_debt_transaction_id=debt_transaction.id,
                financial_event_id=payment_events.get("charge").id if payment_events.get("charge") else None,
                wallet_id=primary_wallet.id,
                event_subtype="CHARGE_PAYMENT",
                entry_date=transaction_date,
                note=note or f"Payment for {debt.counterparty_name}",
            )
        )
    if not ledger_entries:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="debts.payment.amount_required")
    return debt_transaction, ledger_entries[0]


def _create_financial_event_reversal(
    db: Session,
    owner_id: int,
    event: models.FinancialEvent,
    reversal_date: date,
    note: str | None,
) -> models.FinancialEvent:
    reversal = models.FinancialEvent(
        owner_id=owner_id,
        title=f"Reverse {event.title}"[:100],
        description=note or f"Reversal for debt event #{event.id}",
        event_type=event.event_type,
        status=models.FinancialEventStatus.REVERSAL,
        reference_type=models.ReferenceType.VOID_REVERSAL,
        linked_event_id=event.id,
        reverses_event_id=event.id,
        date=reversal_date,
    )
    db.add(reversal)
    db.flush()

    for wallet_leg in event.wallet_legs:
        reversal_amount = -int(wallet_leg.amount)
        WalletService.adjust_balance(db, wallet_leg.wallet_id, reversal_amount)
        db.add(
            models.WalletLedger(
                owner_id=owner_id,
                event_id=reversal.id,
                wallet_id=wallet_leg.wallet_id,
                amount=reversal_amount,
            )
        )

    for entity_leg in event.entity_legs:
        db.add(
            models.EntityLedger(
                event_id=reversal.id,
                label=entity_leg.label,
                amount=-int(entity_leg.amount),
                original_amount=(
                    -int(entity_leg.original_amount)
                    if entity_leg.original_amount is not None
                    else None
                ),
                category=entity_leg.category,
                subcategory_id=entity_leg.subcategory_id,
                project_id=entity_leg.project_id,
                project_subcategory_id=entity_leg.project_subcategory_id,
                budget_id=entity_leg.budget_id,
                debt_id=entity_leg.debt_id,
                income_source_id=entity_leg.income_source_id,
                payment_plan_id=entity_leg.payment_plan_id,
                payment_plan_payment_id=entity_leg.payment_plan_payment_id,
            )
        )

    event.status = models.FinancialEventStatus.VOIDED
    event.voided_at = datetime.now(timezone.utc)
    event.void_reason = note or "Debt ledger entry reversed"
    event.void_reversal_event_id = reversal.id
    db.flush()
    return reversal


@router.get("/summary", response_model=schemas.DebtSummaryOut)
def get_debt_summary(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
):
    total_i_owe = (
        db.query(func.coalesce(func.sum(models.Debt.remaining_amount), 0))
        .filter(
            models.Debt.owner_id == current_user.id,
            models.Debt.debt_type == models.DebtType.OWING,
            models.Debt.remaining_amount > 0,
            models.Debt.archived_at.is_(None),
            models.Debt.status != models.DebtStatus.ARCHIVED,
        )
        .scalar()
    ) or 0

    total_owed_to_me = (
        db.query(func.coalesce(func.sum(models.Debt.remaining_amount), 0))
        .filter(
            models.Debt.owner_id == current_user.id,
            models.Debt.debt_type == models.DebtType.OWED,
            models.Debt.remaining_amount > 0,
            models.Debt.archived_at.is_(None),
            models.Debt.status != models.DebtStatus.ARCHIVED,
        )
        .scalar()
    ) or 0

    return schemas.DebtSummaryOut(
        total_i_owe=int(total_i_owe),
        total_owed_to_me=int(total_owed_to_me),
    )


@router.post("", response_model=schemas.DebtOut, status_code=status.HTTP_201_CREATED)
def create_debt(
    payload: schemas.DebtCreate,
    response: Response,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
    user_tz: tzinfo = Depends(get_effective_user_timezone),
):
    _apply_rate_limit_headers(response, enforce_debts_write_rate_limit(current_user.id))

    if (
        payload.debt_type == models.DebtType.OWING
        and not payload.is_money_transferred
        and not payload.initial_wallet_allocations
        and payload.expense_category is None
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="debts.validation.expense_category.required",
        )

    origin_kind = _infer_debt_origin_kind(payload)
    product_kind = _infer_debt_product_kind(payload, origin_kind)
    counterparty_kind = _infer_counterparty_kind(payload, origin_kind)
    initial_wallet_allocations = _resolve_initial_wallet_allocations(db, current_user.id, payload)
    is_money_transferred = bool(initial_wallet_allocations)
    initial_amount = (
        sum(int(amount) for _, amount in initial_wallet_allocations)
        if is_money_transferred
        else int(payload.initial_amount)
    )
    single_initial_wallet_id = (
        initial_wallet_allocations[0][0].id
        if len(initial_wallet_allocations) == 1
        else None
    )
    _validate_debt_planning_links(
        db,
        current_user.id,
        origin_kind=origin_kind,
        expense_category=payload.expense_category,
        expense_subcategory_id=payload.expense_subcategory_id,
        project_id=payload.project_id,
        project_subcategory_id=payload.project_subcategory_id,
    )
    _validate_debt_income_semantics(
        db,
        current_user.id,
        origin_kind=origin_kind,
        income_source_id=payload.income_source_id,
    )

    debt = models.Debt(
        owner_id=current_user.id,
        debt_type=payload.debt_type,
        origin_kind=origin_kind,
        counterparty_kind=counterparty_kind,
        product_kind=product_kind,
        counterparty_name=payload.counterparty_name,
        initial_amount=initial_amount,
        remaining_amount=initial_amount,
        currency=payload.currency,
        description=payload.description,
        date=payload.date if payload.date else today_in_tz(user_tz),
        expected_return_date=payload.expected_return_date,
        status=models.DebtStatus.ACTIVE,
        initial_wallet_id=single_initial_wallet_id,
        is_money_transferred=is_money_transferred,
        expense_category=payload.expense_category,
        expense_subcategory_id=payload.expense_subcategory_id,
        project_id=payload.project_id,
        project_subcategory_id=payload.project_subcategory_id,
        income_source_id=payload.income_source_id,
    )
    db.add(debt)
    if not current_user.is_premium:
        current_user.total_debts_created += 1

    db.flush()

    initial_event = None
    if debt.is_money_transferred:
        event = _record_initial_transfer_event(db, debt, initial_wallet_allocations)
        debt.linked_event_id = event.id
        initial_event = event

    create_debt_ledger_entry(
        db,
        owner_id=current_user.id,
        debt_id=debt.id,
        entry_type=models.DebtLedgerEntryType.INITIAL,
        amount_delta=debt.initial_amount,
        principal_delta=debt.initial_amount,
        entry_date=debt.date,
        financial_event_id=initial_event.id if initial_event is not None else None,
        wallet_id=single_initial_wallet_id,
        note=f"Initial debt for {debt.counterparty_name}",
    )
    _reconcile_debt_preserving_lifecycle(db, debt)
    sync_debt_goal_targets(db, current_user.id, debt.id)

    db.commit()
    db.refresh(debt)
    return _build_debt_out_with_ledger_totals(db, debt, today=today_in_tz(user_tz))


@router.get("", response_model=schemas.DebtListOut)
def list_debts(
    debt_type: Optional[models.DebtType] = None,
    lifecycle_status: Optional[schemas.DebtLifecycleStatus] = None,
    time_status: Optional[schemas.DebtTimeStatus] = None,
    include_archived: bool = False,
    archived: Optional[bool] = None,
    search: Optional[str] = None,
    limit: int = 50,
    skip: int = 0,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
    user_tz: tzinfo = Depends(get_effective_user_timezone),
):
    query = db.query(models.Debt).filter(models.Debt.owner_id == current_user.id)

    if debt_type:
        query = query.filter(models.Debt.debt_type == debt_type)
    if archived is True:
        query = query.filter(or_(models.Debt.archived_at.is_not(None), models.Debt.status == models.DebtStatus.ARCHIVED))
    elif archived is False or not include_archived:
        query = query.filter(models.Debt.archived_at.is_(None), models.Debt.status != models.DebtStatus.ARCHIVED)
    if search:
        query = query.filter(models.Debt.counterparty_name.ilike(f"%{search}%"))

    today = today_in_tz(user_tz)
    formal_items = query.order_by(models.Debt.id.desc()).all()
    formal_items = [
        debt
        for debt in formal_items
        if _matches_debt_lifecycle_filter(debt, lifecycle_status)
        and _matches_debt_time_filter(debt, time_status, today=today)
    ]

    user_wallets = {
        wallet.id: wallet
        for wallet in db.query(models.Wallet).filter(models.Wallet.owner_id == current_user.id).all()
    }
    debt_ids = [debt.id for debt in formal_items]

    charges_by_debt = get_debt_total_charges_by_debt_ids(db, debt_ids)
    paid_by_debt = get_debt_total_paid_by_debt_ids(db, debt_ids)

    debt_transactions = []
    if debt_ids:
        debt_transactions = (
            db.query(models.DebtTransaction)
            .filter(models.DebtTransaction.debt_id.in_(debt_ids))
            .all()
        )
    txns_by_debt: dict[int, list[models.DebtTransaction]] = defaultdict(list)
    for transaction in debt_transactions:
        txns_by_debt[transaction.debt_id].append(transaction)

    result_items = []
    for debt in formal_items:
        has_archived = False
        if debt.initial_wallet_id:
            wallet = user_wallets.get(debt.initial_wallet_id)
            if wallet and not wallet.is_active:
                has_archived = True

        if not has_archived:
            for transaction in txns_by_debt.get(debt.id, []):
                wallet = user_wallets.get(transaction.wallet_id)
                if wallet and not wallet.is_active:
                    has_archived = True
                    break

        principal_balance, charge_balance = _debt_component_balances(db, debt)
        result_items.append(
            _build_debt_out(
                debt,
                total_charges=charges_by_debt.get(debt.id, 0),
                total_paid=paid_by_debt.get(debt.id, 0),
                remaining_principal_amount=principal_balance,
                remaining_charge_amount=charge_balance,
                has_archived_transactions=has_archived,
                today=today,
            )
        )

    include_wallet_obligations = (
        (debt_type is None or debt_type == models.DebtType.OWING)
        and archived is not True
        and not include_archived
        and (lifecycle_status is None or lifecycle_status == schemas.DebtLifecycleStatus.OPEN)
        and time_status is None
    )
    if include_wallet_obligations:
        for wallet in user_wallets.values():
            if not _is_wallet_backed_obligation(wallet):
                continue
            if search and search.lower() not in wallet.name.lower():
                continue
            result_items.append(_build_wallet_obligation_out(wallet))

    result_items.sort(key=lambda item: (item.source_type != "DEBT", item.id), reverse=True)
    total = len(result_items)
    return schemas.DebtListOut(total=total, items=result_items[skip:skip + limit])


@router.post("/wallet-obligations/{wallet_id}/payoff", response_model=schemas.WalletTransferOut)
def pay_wallet_backed_obligation(
    wallet_id: int,
    payload: schemas.WalletBackedObligationPayoffCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
):
    target_wallet = _get_owned_wallet_or_404(db, current_user.id, wallet_id)
    if not _is_wallet_backed_obligation(target_wallet):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="debts.wallet_obligation.not_payable",
        )

    remaining_amount = abs(int(target_wallet.current_balance or 0))
    if payload.amount > remaining_amount:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="debts.wallet_obligation.payoff_exceeds_balance",
        )

    if target_wallet.wallet_type == models.WalletType.CREDIT:
        default_note = f"Credit card repayment: {target_wallet.name}"
    else:
        default_note = f"Overdraft cover: {target_wallet.name}"

    transfer_payload = schemas.WalletTransferCreate(
        from_wallet_id=payload.from_wallet_id,
        to_wallet_id=target_wallet.id,
        amount=payload.amount,
        note=payload.note or default_note,
        date=payload.date,
        goal_resolution=payload.goal_resolution,
        fee_amount=payload.fee_amount,
        fee_wallet_id=payload.fee_wallet_id,
        fee_note=payload.fee_note,
    )
    return _execute_wallet_transfer(
        transfer_payload,
        db,
        current_user,
        reference_type=models.ReferenceType.WALLET_OBLIGATION_PAYOFF,
    )


@router.get("/{debt_id}", response_model=schemas.DebtWithTransactionsOut)
def get_debt(
    debt_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
    user_tz: tzinfo = Depends(get_effective_user_timezone),
):
    debt = _get_owned_debt_or_404(db, current_user.id, debt_id)

    transactions = (
        db.query(models.DebtTransaction)
        .options(
            joinedload(models.DebtTransaction.wallet),
            joinedload(models.DebtTransaction.wallet_allocations).joinedload(models.DebtTransactionWalletAllocation.wallet),
        )
        .filter(
            models.DebtTransaction.debt_id == debt.id,
            models.DebtTransaction.owner_id == current_user.id,
        )
        .order_by(models.DebtTransaction.date.desc(), models.DebtTransaction.id.desc())
        .all()
    )
    charges = (
        db.query(models.DebtCharge)
        .filter(
            models.DebtCharge.debt_id == debt.id,
            models.DebtCharge.owner_id == current_user.id,
        )
        .order_by(models.DebtCharge.date.desc(), models.DebtCharge.id.desc())
        .all()
    )
    ledger_entries = (
        db.query(models.DebtLedgerEntry)
        .filter(
            models.DebtLedgerEntry.debt_id == debt.id,
            models.DebtLedgerEntry.owner_id == current_user.id,
        )
        .order_by(models.DebtLedgerEntry.entry_date.desc(), models.DebtLedgerEntry.id.desc())
        .all()
    )
    debt_out = schemas.DebtWithTransactionsOut(
        **_build_debt_out_with_ledger_totals(db, debt, today=today_in_tz(user_tz)).model_dump(),
        transactions=[_build_debt_transaction_out(transaction) for transaction in transactions],
        charges=[schemas.DebtChargeOut.model_validate(charge) for charge in charges],
        ledger_entries=[schemas.DebtLedgerEntryOut.model_validate(entry) for entry in ledger_entries],
    )
    return debt_out


@router.get("/{debt_id}/actions", response_model=list[schemas.DebtActionDecisionOut])
def get_debt_actions(
    debt_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
):
    debt = _get_owned_debt_or_404(db, current_user.id, debt_id)
    return _build_action_decisions_out(db, debt)


@router.post("/{debt_id}/archive", response_model=schemas.DebtOut)
def archive_debt(
    debt_id: int,
    response: Response,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
    user_tz: tzinfo = Depends(get_effective_user_timezone),
):
    _apply_rate_limit_headers(response, enforce_debts_write_rate_limit(current_user.id))
    debt = _get_owned_debt_or_404(db, current_user.id, debt_id)
    _raise_policy_denied(evaluate_debt_action(db, debt, models.DebtActionKind.ARCHIVE))

    if not _is_debt_archived(debt):
        debt.archived_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(debt)
    return _build_debt_out_with_ledger_totals(db, debt, today=today_in_tz(user_tz))


def _restore_debt_from_archive(
    debt_id: int,
    response: Response,
    db: Session,
    current_user: models.User,
    user_tz: tzinfo,
) -> schemas.DebtOut:
    _apply_rate_limit_headers(response, enforce_debts_write_rate_limit(current_user.id))
    debt = _get_owned_debt_or_404(db, current_user.id, debt_id)
    _raise_policy_denied(evaluate_debt_action(db, debt, models.DebtActionKind.RESTORE))

    debt.archived_at = None
    if debt.status == models.DebtStatus.ARCHIVED:
        debt.status = models.DebtStatus.PAID if int(debt.remaining_amount or 0) <= 0 else models.DebtStatus.ACTIVE
    db.commit()
    db.refresh(debt)
    return _build_debt_out_with_ledger_totals(db, debt, today=today_in_tz(user_tz))


@router.post("/{debt_id}/restore", response_model=schemas.DebtOut)
def restore_debt(
    debt_id: int,
    response: Response,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
    user_tz: tzinfo = Depends(get_effective_user_timezone),
):
    return _restore_debt_from_archive(debt_id, response, db, current_user, user_tz)


@router.post("/{debt_id}/unarchive", response_model=schemas.DebtOut)
def unarchive_debt(
    debt_id: int,
    response: Response,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
    user_tz: tzinfo = Depends(get_effective_user_timezone),
):
    return _restore_debt_from_archive(debt_id, response, db, current_user, user_tz)


@router.get("/{debt_id}/details", response_model=schemas.DebtDetailsOut)
def get_debt_details(
    debt_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
    user_tz: tzinfo = Depends(get_effective_user_timezone),
):
    debt = (
        db.query(models.Debt)
        .options(
            joinedload(models.Debt.formal_details),
        )
        .filter(models.Debt.id == debt_id, models.Debt.owner_id == current_user.id)
        .first()
    )
    if not debt:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="debts.not_found")

    transactions = (
        db.query(models.DebtTransaction)
        .options(
            joinedload(models.DebtTransaction.wallet),
            joinedload(models.DebtTransaction.wallet_allocations).joinedload(models.DebtTransactionWalletAllocation.wallet),
        )
        .filter(
            models.DebtTransaction.debt_id == debt.id,
            models.DebtTransaction.owner_id == current_user.id,
        )
        .order_by(models.DebtTransaction.date.desc(), models.DebtTransaction.id.desc())
        .all()
    )
    charges = (
        db.query(models.DebtCharge)
        .filter(
            models.DebtCharge.debt_id == debt.id,
            models.DebtCharge.owner_id == current_user.id,
        )
        .order_by(models.DebtCharge.date.desc(), models.DebtCharge.id.desc())
        .all()
    )
    ledger_entries = (
        db.query(models.DebtLedgerEntry)
        .filter(
            models.DebtLedgerEntry.debt_id == debt.id,
            models.DebtLedgerEntry.owner_id == current_user.id,
        )
        .order_by(models.DebtLedgerEntry.entry_date.asc(), models.DebtLedgerEntry.id.asc())
        .all()
    )

    return schemas.DebtDetailsOut(
        debt=_build_debt_out_with_ledger_totals(db, debt, today=today_in_tz(user_tz)),
        formal_details=(
            schemas.DebtFormalDetailsOut.model_validate(debt.formal_details)
            if debt.formal_details
            else None
        ),
        actions=_build_action_decisions_out(db, debt),
        transactions=[_build_debt_transaction_out(transaction) for transaction in transactions],
        charges=[schemas.DebtChargeOut.model_validate(charge) for charge in charges],
        ledger_entries=[schemas.DebtLedgerEntryOut.model_validate(entry) for entry in reversed(ledger_entries)],
        activity=[_build_activity_item(db, debt, entry) for entry in ledger_entries],
    )


@router.patch("/{debt_id}", response_model=schemas.DebtOut)
def update_debt(
    debt_id: int,
    payload: schemas.DebtUpdate,
    response: Response,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
    user_tz: tzinfo = Depends(get_effective_user_timezone),
):
    _apply_rate_limit_headers(response, enforce_debts_write_rate_limit(current_user.id))
    debt = _get_owned_debt_or_404(db, current_user.id, debt_id)

    if _is_debt_archived(debt):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="debts.update.archived_immutable")

    update_data = payload.model_dump(exclude_unset=True)
    next_date = update_data.get("date", debt.date)
    next_expected_return_date = update_data.get("expected_return_date", debt.expected_return_date)
    if next_expected_return_date is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="debts.validation.expected_date_required",
        )
    if next_date is not None and next_expected_return_date < next_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="debts.validation.expected_date_before_date",
        )

    if "status" in update_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="debts.update.status_requires_action")

    if "initial_amount" in update_data:
        new_amount = update_data.pop("initial_amount")
        if _debt_lifecycle_status(debt) != schemas.DebtLifecycleStatus.OPEN:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="debts.edit_amount.not_active")
        if not is_pristine_debt(db, debt):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="debts.update.opening_amount_requires_pristine",
            )

        delta = int(new_amount) - int(debt.initial_amount)
        new_remaining = int(debt.remaining_amount) + delta
        if new_remaining < 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="debts.edit_amount.remaining_would_be_negative",
            )

        if debt.is_money_transferred and debt.initial_wallet_id and delta != 0:
            wallet = _get_owned_wallet_or_404(db, current_user.id, debt.initial_wallet_id)
            if not wallet.is_active:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="debts.edit_amount.wallet_archived")

            wallet_delta = delta if debt.debt_type == models.DebtType.OWING else -delta
            if wallet_delta < 0:
                validate_wallet_goal_protection_for_outflow(
                    db,
                    current_user.id,
                    wallet,
                    abs(int(wallet_delta)),
                    outflow_type="debt_edit",
                    error_code="wallets.goal_protection_conflict",
                )
            try:
                WalletService.adjust_balance(db, wallet.id, wallet_delta)
            except HTTPException:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="debts.edit_amount.wallet_insufficient_funds",
                )

            if debt.linked_event_id:
                initial_event = (
                    db.query(models.FinancialEvent)
                    .options(
                        joinedload(models.FinancialEvent.wallet_legs),
                        joinedload(models.FinancialEvent.entity_legs),
                    )
                    .filter(models.FinancialEvent.id == debt.linked_event_id, models.FinancialEvent.owner_id == current_user.id)
                    .first()
                )
                if initial_event:
                    signed_amount = new_amount if debt.debt_type == models.DebtType.OWING else -new_amount
                    _update_event_amounts(initial_event, signed_amount, int(new_amount))

        debt.initial_amount = int(new_amount)
        debt.remaining_amount = int(new_remaining)
        if delta != 0:
            create_debt_ledger_entry(
                db,
                owner_id=current_user.id,
                debt_id=debt.id,
                entry_type=models.DebtLedgerEntryType.ADJUSTMENT,
                amount_delta=delta,
                principal_delta=delta,
                financial_event_id=debt.linked_event_id,
                wallet_id=debt.initial_wallet_id,
                entry_date=debt.date,
                note="Debt initial amount adjusted",
            )

    if (
        debt.debt_type == models.DebtType.OWING
        and not debt.is_money_transferred
        and "expense_category" in update_data
        and update_data["expense_category"] is None
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="debts.validation.expense_category.required",
        )

    next_origin_kind = update_data.get("origin_kind", debt.origin_kind)
    next_expense_category = update_data.get("expense_category", debt.expense_category)
    next_expense_subcategory_id = update_data.get("expense_subcategory_id", debt.expense_subcategory_id)
    next_project_id = update_data.get("project_id", debt.project_id)
    next_project_subcategory_id = update_data.get("project_subcategory_id", debt.project_subcategory_id)
    next_income_source_id = update_data.get("income_source_id", debt.income_source_id)
    if debt.debt_type == models.DebtType.OWING and not debt.is_money_transferred and next_expense_category is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="debts.validation.expense_category.required",
        )
    _validate_debt_planning_links(
        db,
        current_user.id,
        origin_kind=next_origin_kind,
        expense_category=next_expense_category,
        expense_subcategory_id=next_expense_subcategory_id,
        project_id=next_project_id,
        project_subcategory_id=next_project_subcategory_id,
    )
    _validate_debt_income_semantics(
        db,
        current_user.id,
        origin_kind=next_origin_kind,
        income_source_id=next_income_source_id,
    )

    for field, value in update_data.items():
        setattr(debt, field, value)

    _reconcile_debt_preserving_lifecycle(db, debt)
    sync_debt_goal_targets(db, current_user.id, debt.id)
    db.commit()
    db.refresh(debt)
    return _build_debt_out_with_ledger_totals(db, debt, today=today_in_tz(user_tz))


@router.delete("/{debt_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_debt(
    debt_id: int,
    response: Response,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
):
    _apply_rate_limit_headers(response, enforce_debts_write_rate_limit(current_user.id))
    debt = _get_owned_debt_or_404(db, current_user.id, debt_id)

    if _is_debt_archived(debt):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="debts.delete.archived_immutable")
    if not is_pristine_debt(db, debt):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="debts.delete.pristine_required")

    linked_events = _find_all_debt_events(db, current_user.id, debt.id)
    for event in linked_events:
        for leg in event.wallet_legs:
            if leg.wallet and not leg.wallet.is_active:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="debts.delete.wallet_archived",
                )

    for event in linked_events:
        reverse_wallet_effect(db, event)
        db.delete(event)

    db.delete(debt)
    db.commit()


@router.post("/transactions", response_model=schemas.DebtTransactionOut, status_code=status.HTTP_201_CREATED)
def create_transaction(
    payload: schemas.DebtTransactionCreate,
    response: Response,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
    user_tz: tzinfo = Depends(get_effective_user_timezone),
):
    _apply_rate_limit_headers(response, enforce_debts_write_rate_limit(current_user.id))
    debt = _get_owned_debt_or_404(db, current_user.id, payload.debt_id)

    if _is_debt_archived(debt) or _debt_lifecycle_status(debt) != schemas.DebtLifecycleStatus.OPEN:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="debts.transaction.not_active")
    _raise_policy_denied(evaluate_debt_action(db, debt, models.DebtActionKind.RECORD_PAYMENT))
    if debt.remaining_amount < payload.amount:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="debts.transaction.amount_too_high")

    wallet = _resolve_wallet(db, current_user.id, payload.wallet_id)
    transaction_date = payload.date if payload.date else today_in_tz(user_tz)
    debt_transaction, _ = create_debt_payment_service(
        db,
        debt,
        amount=int(payload.amount),
        transaction_date=transaction_date,
        wallet_allocations=[
            schemas.DebtTransactionWalletAllocationIn(
                wallet_id=wallet.id,
                amount=int(payload.amount),
            )
        ],
        note=payload.note,
        income_source_id=payload.income_source_id,
    )
    _reconcile_debt_preserving_lifecycle(db, debt)
    sync_debt_goal_targets(db, current_user.id, debt.id)
    db.commit()
    db.refresh(debt_transaction)
    db.refresh(wallet)
    return _build_debt_transaction_out(debt_transaction)


@router.delete("/transactions/{transaction_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_transaction(
    transaction_id: int,
    response: Response,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
):
    _apply_rate_limit_headers(response, enforce_debts_write_rate_limit(current_user.id))

    transaction = (
        db.query(models.DebtTransaction)
        .options(joinedload(models.DebtTransaction.wallet))
        .filter(
            models.DebtTransaction.id == transaction_id,
            models.DebtTransaction.owner_id == current_user.id,
        )
        .first()
    )
    if not transaction:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="debts.transaction.not_found")

    debt = _get_owned_debt_or_404(db, current_user.id, transaction.debt_id)
    if _is_debt_archived(debt) or debt.status == models.DebtStatus.FORGIVEN:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="debts.transaction.debt_archived")
    if transaction.wallet and not transaction.wallet.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="debts.transaction.wallet_archived")

    linked_events = _find_payment_events(db, current_user.id, debt.id, transaction.id)
    if linked_events:
        for event in linked_events:
            reverse_wallet_effect(db, event)
            db.delete(event)
    elif transaction.wallet_id is not None:
        reverse_delta = transaction.amount if debt.debt_type == models.DebtType.OWING else -transaction.amount
        WalletService.adjust_balance(db, transaction.wallet_id, reverse_delta)

    reverse_debt_transaction_ledger(
        db,
        owner_id=current_user.id,
        debt_id=debt.id,
        transaction_id=transaction.id,
        entry_date=transaction.date,
        note="Debt payment deleted",
    )
    db.delete(transaction)
    reconcile_debt(db, debt.id)
    sync_debt_goal_targets(db, current_user.id, debt.id)
    db.commit()


@router.post("/{debt_id}/payments", response_model=schemas.DebtTransactionOut, status_code=status.HTTP_201_CREATED)
def record_debt_payment(
    debt_id: int,
    payload: schemas.DebtPaymentCreate,
    response: Response,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
    user_tz: tzinfo = Depends(get_effective_user_timezone),
):
    _apply_rate_limit_headers(response, enforce_debts_write_rate_limit(current_user.id))
    debt = _get_owned_debt_or_404(db, current_user.id, debt_id)
    _raise_policy_denied(evaluate_debt_action(db, debt, models.DebtActionKind.RECORD_PAYMENT))

    transaction_date = payload.date or today_in_tz(user_tz)
    debt_transaction, _ = create_debt_payment_service(
        db,
        debt,
        amount=int(payload.amount),
        transaction_date=transaction_date,
        wallet_allocations=payload.wallet_allocations,
        note=payload.note,
        income_source_id=payload.income_source_id,
    )
    reconcile_debt(db, debt.id)
    sync_debt_goal_targets(db, current_user.id, debt.id)
    db.commit()
    db.refresh(debt_transaction)
    return _build_debt_transaction_out(debt_transaction)


@router.post("/{debt_id}/add-charge", response_model=schemas.DebtChargeOut, status_code=status.HTTP_201_CREATED)
def add_charge(
    debt_id: int,
    payload: schemas.DebtAddChargeRequest,
    response: Response,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
    user_tz: tzinfo = Depends(get_effective_user_timezone),
):
    _apply_rate_limit_headers(response, enforce_debts_write_rate_limit(current_user.id))
    debt = _get_owned_debt_or_404(db, current_user.id, debt_id)
    _raise_policy_denied(evaluate_debt_action(db, debt, models.DebtActionKind.ADD_CHARGE))

    charge = models.DebtCharge(
        owner_id=current_user.id,
        debt_id=debt.id,
        amount=payload.amount,
        reason=payload.reason,
        date=today_in_tz(user_tz),
    )
    db.add(charge)
    db.flush()

    create_debt_ledger_entry(
        db,
        owner_id=current_user.id,
        debt_id=debt.id,
        entry_type=models.DebtLedgerEntryType.CHARGE,
        amount_delta=payload.amount,
        charge_delta=payload.amount,
        source_debt_charge_id=charge.id,
        entry_date=charge.date,
        note=payload.reason,
    )
    reconcile_debt(db, debt.id)
    sync_debt_goal_targets(db, current_user.id, debt.id)
    db.commit()
    db.refresh(charge)
    return schemas.DebtChargeOut.model_validate(charge)


@router.post("/{debt_id}/charges", response_model=schemas.DebtChargeOut, status_code=status.HTTP_201_CREATED)
def add_debt_charge(
    debt_id: int,
    payload: schemas.DebtAddChargeRequest,
    response: Response,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
    user_tz: tzinfo = Depends(get_effective_user_timezone),
):
    return add_charge(debt_id, payload, response, db, current_user, user_tz)


@router.post("/{debt_id}/forgive", response_model=schemas.DebtOut)
def forgive_debt(
    debt_id: int,
    response: Response,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
    user_tz: tzinfo = Depends(get_effective_user_timezone),
):
    _apply_rate_limit_headers(response, enforce_debts_write_rate_limit(current_user.id))
    debt = _get_owned_debt_or_404(db, current_user.id, debt_id)
    _raise_policy_denied(evaluate_debt_action(db, debt, models.DebtActionKind.FORGIVE_FULL))

    if int(debt.remaining_amount or 0) > 0:
        principal_amount, charge_amount, event_subtype = _forgiveness_component_amounts(
            db,
            debt,
            int(debt.remaining_amount),
            schemas.DebtForgivenessComponent.TOTAL,
        )
        create_debt_ledger_entry(
            db,
            owner_id=current_user.id,
            debt_id=debt.id,
            entry_type=models.DebtLedgerEntryType.FORGIVENESS,
            amount_delta=-int(debt.remaining_amount),
            principal_delta=-int(principal_amount),
            charge_delta=-int(charge_amount),
            event_subtype=event_subtype,
            entry_date=today_in_tz(user_tz),
            note="Debt forgiven",
        )
    reconcile_debt(db, debt.id)
    sync_debt_goal_targets(db, current_user.id, debt.id)
    debt.status = models.DebtStatus.FORGIVEN
    db.commit()
    db.refresh(debt)
    return _build_debt_out_with_ledger_totals(db, debt, today=today_in_tz(user_tz))


@router.post("/{debt_id}/forgiveness", response_model=schemas.DebtOut)
def forgive_debt_amount(
    debt_id: int,
    payload: schemas.DebtForgivenessCreate,
    response: Response,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
    user_tz: tzinfo = Depends(get_effective_user_timezone),
):
    _apply_rate_limit_headers(response, enforce_debts_write_rate_limit(current_user.id))
    debt = _get_owned_debt_or_404(db, current_user.id, debt_id)
    remaining = int(debt.remaining_amount or 0)
    forgiveness_amount = int(payload.amount or remaining)
    if forgiveness_amount <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="debts.forgiveness.amount_required")
    if forgiveness_amount > remaining:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="debts.forgiveness.amount_too_high")

    action_kind = (
        models.DebtActionKind.FORGIVE_FULL
        if forgiveness_amount == remaining
        else models.DebtActionKind.FORGIVE_PARTIAL
    )
    _raise_policy_denied(evaluate_debt_action(db, debt, action_kind))

    principal_amount, charge_amount, event_subtype = _forgiveness_component_amounts(
        db,
        debt,
        forgiveness_amount,
        payload.component,
    )
    create_debt_ledger_entry(
        db,
        owner_id=current_user.id,
        debt_id=debt.id,
        entry_type=models.DebtLedgerEntryType.FORGIVENESS,
        amount_delta=-forgiveness_amount,
        principal_delta=-int(principal_amount),
        charge_delta=-int(charge_amount),
        event_subtype=event_subtype,
        entry_date=payload.date or today_in_tz(user_tz),
        note=payload.note or "Debt forgiveness",
        extra_data={
            "component": (payload.component or schemas.DebtForgivenessComponent.TOTAL).value,
            "principal_amount": int(principal_amount),
            "charge_amount": int(charge_amount),
        },
    )
    _reconcile_debt_preserving_lifecycle(db, debt)
    sync_debt_goal_targets(db, current_user.id, debt.id)
    if forgiveness_amount == remaining:
        debt.status = models.DebtStatus.FORGIVEN
    db.commit()
    db.refresh(debt)
    return _build_debt_out_with_ledger_totals(db, debt, today=today_in_tz(user_tz))


@router.post("/{debt_id}/balance-adjustments", response_model=schemas.DebtOut)
def adjust_debt_balance(
    debt_id: int,
    payload: schemas.DebtBalanceAdjustmentCreate,
    response: Response,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
    user_tz: tzinfo = Depends(get_effective_user_timezone),
):
    _apply_rate_limit_headers(response, enforce_debts_write_rate_limit(current_user.id))
    debt = _get_owned_debt_or_404(db, current_user.id, debt_id)
    _raise_policy_denied(evaluate_debt_action(db, debt, models.DebtActionKind.ADJUST_BALANCE))

    delta, principal_delta, charge_delta, event_subtype, extra_data = _balance_correction_deltas(db, debt, payload)
    if delta != 0:
        create_debt_ledger_entry(
            db,
            owner_id=current_user.id,
            debt_id=debt.id,
            entry_type=models.DebtLedgerEntryType.ADJUSTMENT,
            amount_delta=delta,
            principal_delta=principal_delta,
            charge_delta=charge_delta,
            event_subtype=event_subtype,
            entry_date=payload.date or today_in_tz(user_tz),
            note=payload.note or "Debt balance corrected",
            extra_data=extra_data,
        )
    _reconcile_debt_preserving_lifecycle(db, debt)
    sync_debt_goal_targets(db, current_user.id, debt.id)
    db.commit()
    db.refresh(debt)
    return _build_debt_out_with_ledger_totals(db, debt, today=today_in_tz(user_tz))


@router.post("/{debt_id}/ledger/{entry_id}/reverse", response_model=schemas.DebtOut)
def reverse_debt_ledger_entry(
    debt_id: int,
    entry_id: int,
    payload: schemas.DebtLedgerEntryReverseCreate,
    response: Response,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
    user_tz: tzinfo = Depends(get_effective_user_timezone),
):
    _apply_rate_limit_headers(response, enforce_debts_write_rate_limit(current_user.id))
    debt = _get_owned_debt_or_404(db, current_user.id, debt_id)
    entry = (
        db.query(models.DebtLedgerEntry)
        .options(
            joinedload(models.DebtLedgerEntry.financial_event).joinedload(models.FinancialEvent.wallet_legs),
            joinedload(models.DebtLedgerEntry.financial_event).joinedload(models.FinancialEvent.entity_legs),
        )
        .filter(
            models.DebtLedgerEntry.id == entry_id,
            models.DebtLedgerEntry.owner_id == current_user.id,
        )
        .first()
    )
    if not entry:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="debts.ledger_entry.not_found")

    decision = evaluate_ledger_entry_reversal(db, debt, entry)
    _raise_policy_denied(decision)

    reversal_date = payload.date or today_in_tz(user_tz)
    reversal_event = None
    if entry.financial_event is not None:
        reversal_event = _create_financial_event_reversal(
            db,
            current_user.id,
            entry.financial_event,
            reversal_date,
            payload.note,
        )

    create_debt_ledger_entry(
        db,
        owner_id=current_user.id,
        debt_id=debt.id,
        entry_type=models.DebtLedgerEntryType.REVERSAL,
        amount_delta=-int(entry.amount_delta),
        principal_delta=-int(entry.principal_delta or 0),
        charge_delta=-int(entry.charge_delta or 0),
        financial_event_id=reversal_event.id if reversal_event else None,
        source_debt_transaction_id=entry.source_debt_transaction_id,
        source_debt_charge_id=entry.source_debt_charge_id,
        reverses_entry_id=entry.id,
        wallet_id=entry.wallet_id,
        asset_id=entry.asset_id,
        event_subtype="ENTRY_REVERSAL",
        entry_date=reversal_date,
        note=payload.note or "Debt ledger entry reversed",
    )
    _reconcile_debt_preserving_lifecycle(db, debt)
    sync_debt_goal_targets(db, current_user.id, debt.id)
    db.commit()
    db.refresh(debt)
    return _build_debt_out_with_ledger_totals(db, debt, today=today_in_tz(user_tz))


@router.patch("/{debt_id}/formal-details", response_model=schemas.DebtFormalDetailsOut)
def update_debt_formal_details(
    debt_id: int,
    payload: schemas.DebtFormalDetailsUpdate,
    response: Response,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
):
    _apply_rate_limit_headers(response, enforce_debts_write_rate_limit(current_user.id))
    debt = _get_owned_debt_or_404(db, current_user.id, debt_id)
    if _is_debt_archived(debt):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="debts.formal_details.archived_immutable")

    update_data = payload.model_dump(exclude_unset=True)
    for asset_field in ("linked_asset_id", "collateral_asset_id"):
        asset_id = update_data.get(asset_field)
        if asset_id is not None:
            asset = (
                db.query(models.Asset)
                .filter(models.Asset.id == asset_id, models.Asset.owner_id == current_user.id)
                .first()
            )
            if not asset:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="assets.not_found")

    details = debt.formal_details
    if details is None:
        details = models.DebtFormalDetails(
            debt_id=debt.id,
            owner_id=current_user.id,
        )
        db.add(details)
        db.flush()

    for field, value in update_data.items():
        setattr(details, field, value)

    db.commit()
    db.refresh(details)
    return schemas.DebtFormalDetailsOut.model_validate(details)
