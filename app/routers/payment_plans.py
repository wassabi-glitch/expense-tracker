import calendar
from datetime import date, timedelta, tzinfo
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Response, status
# pyrefly: ignore [missing-import]
from sqlalchemy import func
# pyrefly: ignore [missing-import]
from sqlalchemy.orm import Session, selectinload

from app.timezone import get_effective_user_timezone, today_in_tz
from app.utils import check_budget_alerts
from .. import models, oauth2, schemas
from ..redis_rate_limiter import consume_token_bucket
from ..services.budget_service import (
    materialize_budget_for_month,
    validate_budget_limit,
    validate_project_budget,
    validate_subcategory_limit,
)
from ..services.debt_service import (
    reconcile_debt,
)
from ..services.goal_funding_service import validate_wallet_goal_protection_for_outflow
from ..services.session_draft_service import validate_session_item_links
from ..services.wallet_service import WalletService
from ..session import get_db
from .debts import (
    _create_financial_event_reversal,
)
from .wallets import _get_owned_wallet_or_404

router = APIRouter(
    prefix="/payment-plans",
    tags=["PaymentPlans (Nasiya)"],
)

PAYMENT_PLANS_WRITE_BUCKET_CAPACITY = 20
PAYMENT_PLANS_WRITE_REFILL_RATE = 20 / 60
PAYMENT_PLAN_SETUP_UPDATE_FIELDS = {"total_price", "down_payment", "months", "frequency", "start_date"}


def enforce_payment_plans_write_rate_limit(user_id: int) -> dict[str, str]:
    rl = consume_token_bucket(
        scope="payment_plans_write",
        identifier=str(user_id),
        capacity=PAYMENT_PLANS_WRITE_BUCKET_CAPACITY,
        refill_rate_per_second=PAYMENT_PLANS_WRITE_REFILL_RATE,
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
            detail="payment_plans.write_rate_limited",
            headers=headers,
        )
    return headers


def _add_months(sourcedate: date, months: int) -> date:
    month = sourcedate.month - 1 + months
    year = sourcedate.year + month // 12
    month = month % 12 + 1
    day = min(sourcedate.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def _add_years(sourcedate: date, years: int) -> date:
    try:
        return sourcedate.replace(year=sourcedate.year + years)
    except ValueError:
        return sourcedate.replace(year=sourcedate.year + years, day=28)


def _scheduled_due_date(start_date: date, frequency: models.PaymentPlanFrequency, index: int) -> date:
    if frequency == models.PaymentPlanFrequency.WEEKLY:
        return start_date + timedelta(weeks=index)
    if frequency == models.PaymentPlanFrequency.BIWEEKLY:
        return start_date + timedelta(weeks=index * 2)
    if frequency == models.PaymentPlanFrequency.QUARTERLY:
        return _add_months(start_date, index * 3)
    if frequency == models.PaymentPlanFrequency.YEARLY:
        return _add_years(start_date, index)
    return _add_months(start_date, index)


def _resolve_budget_for_payment_plan_month(
    db: Session,
    user_id: int,
    category: models.ExpenseCategory,
    expense_date: date,
) -> models.Budget:
    budget = (
        db.query(models.Budget)
        .filter(
            models.Budget.owner_id == user_id,
            models.Budget.category == category,
            models.Budget.budget_year == expense_date.year,
            models.Budget.budget_month == expense_date.month,
        )
        .with_for_update()
        .first()
    )

    if not budget:
        budget = materialize_budget_for_month(db, user_id, category, expense_date.year, expense_date.month)
        if not budget:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="expenses.budget_required",
            )

    return budget


def _validated_wallet_allocations(
    db: Session,
    owner_id: int,
    allocations: list[schemas.PaymentPlanWalletAllocationIn],
    expected_total: int,
) -> list[tuple[models.Wallet, int]]:
    if expected_total <= 0:
        return []

    if not allocations:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="payment_plans.wallet_allocations_required")

    allocation_total = int(sum(int(item.amount) for item in allocations))
    if allocation_total != int(expected_total):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="payment_plans.wallet_total_mismatch")

    seen_wallet_ids: set[int] = set()
    validated: list[tuple[models.Wallet, int]] = []
    for allocation in allocations:
        if allocation.wallet_id in seen_wallet_ids:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="payment_plans.wallet_duplicate")
        seen_wallet_ids.add(allocation.wallet_id)
        wallet = _get_owned_wallet_or_404(db, owner_id, allocation.wallet_id)
        if not wallet.is_active:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="wallets.archived_locked")
        validated.append((wallet, int(allocation.amount)))
    return validated


def _create_payment_plan_expense_event(
    db: Session,
    owner_id: int,
    *,
    title: str,
    amount: int,
    category: models.ExpenseCategory,
    expense_date: date,
    wallet_allocations: list[schemas.PaymentPlanWalletAllocationIn],
    reference_type: str,
    payment_plan_id: int,
    payment_plan_payment_id: int | None = None,
    subcategory_id: int | None = None,
    project_id: int | None = None,
    project_subcategory_id: int | None = None,
    note: str | None = None,
    user_tz: tzinfo,
) -> models.FinancialEvent:
    local_today = today_in_tz(user_tz)
    if expense_date > local_today:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="expenses.date_in_future")

    validated_wallets = _validated_wallet_allocations(db, owner_id, wallet_allocations, amount)
    budget = _resolve_budget_for_payment_plan_month(db, owner_id, category, expense_date)
    subcategory, project, project_subcategory = validate_session_item_links(
        db,
        owner_id,
        category,
        subcategory_id,
        project_id,
        project_subcategory_id,
    )
    if project is not None:
        validate_project_budget(
            db,
            owner_id,
            project,
            category,
            amount,
            expense_date,
            project_subcategory=project_subcategory,
        )
    validate_budget_limit(db, owner_id, budget, amount, project=project)
    if subcategory is not None:
        validate_subcategory_limit(db, owner_id, subcategory, amount, expense_date, project=project)
    for wallet, allocation_amount in validated_wallets:
        validate_wallet_goal_protection_for_outflow(
            db,
            owner_id,
            wallet,
            allocation_amount,
            outflow_type="payment_plan_payment",
            error_code="wallets.goal_protection_conflict",
        )

    event = models.FinancialEvent(
        owner_id=owner_id,
        title=title,
        description=note,
        event_type=models.TransactionType.EXPENSE,
        reference_type=reference_type,
        date=expense_date,
    )
    db.add(event)
    db.flush()

    for wallet, allocation_amount in validated_wallets:
        WalletService.adjust_balance(db, wallet.id, -allocation_amount, models.TransactionType.EXPENSE)
        db.add(
            models.WalletLedger(
                owner_id=owner_id,
                event_id=event.id,
                wallet_id=wallet.id,
                amount=-allocation_amount,
            )
        )

    db.add(
        models.EntityLedger(
            event_id=event.id,
            label=title,
            amount=int(amount),
            category=category,
            budget_id=budget.id,
            subcategory_id=subcategory.id if subcategory is not None else None,
            project_id=project.id if project is not None else None,
            project_subcategory_id=project_subcategory.id if project_subcategory is not None else None,
            payment_plan_id=payment_plan_id,
            payment_plan_payment_id=payment_plan_payment_id,
        )
    )
    check_budget_alerts(db, budget)
    db.flush()
    return event


def _get_owned_plan_or_404(db: Session, user_id: int, plan_id: int) -> models.PaymentPlan:
    plan = (
        db.query(models.PaymentPlan)
        .options(
            selectinload(models.PaymentPlan.payments).selectinload(models.PaymentPlanPayment.allocations),
        )
        .filter(
            models.PaymentPlan.id == plan_id,
            models.PaymentPlan.owner_id == user_id,
        )
        .first()
    )
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="payment_plans.not_found")
    return plan


def _raise_policy_denied(decision) -> None:
    if not decision.allowed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=decision.reason_code or "debts.policy.action_blocked",
        )


def _is_pristine_payment_plan(db: Session, plan: models.PaymentPlan) -> bool:
    for payment in plan.payments or []:
        if int(payment.paid_amount or 0) > 0:
            return False
        if int(payment.written_off_amount or 0) > 0:
            return False
        if payment.event_id is not None or payment.payment_plan_ledger_entry_id is not None:
            return False
        if payment.payment_plan_charge_id is not None:
            return False
        if payment.component_type != models.PaymentPlanPaymentComponentType.PRINCIPAL:
            return False
        if payment.allocations:
            return False

    return (
        db.query(models.Goals.id)
        .filter(
            models.Goals.owner_id == plan.owner_id,
            models.Goals.intent == models.GoalIntent.PAY_OBLIGATION,
            models.Goals.linked_payment_plan_id == plan.id,
            models.Goals.status != models.GoalStatus.ARCHIVED,
        )
        .first()
        is None
    )


def _regenerate_pristine_payment_plan_schedule(db: Session, plan: models.PaymentPlan) -> None:
    remaining_amount = int(plan.total_price) - int(plan.down_payment)
    if remaining_amount < 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="payment_plans.invalid_down_payment")

    payment_count = int(plan.months)
    base_payment = remaining_amount // payment_count if remaining_amount > 0 else 0

    for payment in list(plan.payments or []):
        if payment.component_type == models.PaymentPlanPaymentComponentType.PRINCIPAL:
            db.delete(payment)
            plan.payments.remove(payment)

    plan.remaining_amount = remaining_amount
    plan.payment_count = payment_count
    plan.monthly_payment_amount = base_payment
    plan.regular_payment_amount = base_payment
    plan.schedule_rule = {
        "source": "STANDARD_INTERVAL",
        "frequency": plan.frequency.value,
        "payment_count": payment_count,
    }
    plan.status = models.PaymentPlanStatus.PAID if remaining_amount == 0 else models.PaymentPlanStatus.ACTIVE

    if remaining_amount > 0:
        remainder = remaining_amount % payment_count
        for index in range(1, payment_count + 1):
            payment_amount = base_payment + (remainder if index == payment_count else 0)
            if payment_amount <= 0:
                continue
            plan.payments.append(
                models.PaymentPlanPayment(
                    owner_id=plan.owner_id,
                    amount=payment_amount,
                    due_date=_scheduled_due_date(plan.start_date, plan.frequency, index),
                    component_type=models.PaymentPlanPaymentComponentType.PRINCIPAL,
                    status=models.PaymentPlanPaymentStatus.PENDING,
                )
            )


def _resolve_existing_plan_category(
    plan: models.PaymentPlan,
    requested_category: models.ExpenseCategory | None = None,
) -> models.ExpenseCategory:
    category = plan.expense_category or requested_category or _suggested_category_for_plan_type(plan.plan_type)
    if category is None or category == models.ExpenseCategory.PAYMENT_PLANS_DEBT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="payment_plans.validation.real_expense_category_required",
        )
    return category


def _plan_category(plan: models.PaymentPlan) -> models.ExpenseCategory:
    return _resolve_existing_plan_category(plan)


def _counterparty_name(plan: models.PaymentPlan) -> str:
    return (plan.store_or_bank_name or plan.item_name or "PaymentPlan provider")[:100]


def _suggested_category_for_plan_type(
    plan_type: models.PaymentPlanType,
) -> models.ExpenseCategory | None:
    if plan_type == models.PaymentPlanType.MORTGAGE:
        return models.ExpenseCategory.HOUSING
    if plan_type == models.PaymentPlanType.AUTO_LOAN:
        return models.ExpenseCategory.TRANSPORT
    if plan_type == models.PaymentPlanType.EDUCATION_LOAN:
        return models.ExpenseCategory.EDUCATION
    return None


def _resolve_plan_category(payload: schemas.PaymentPlanCreate) -> models.ExpenseCategory:
    category = payload.expense_category
    if category is None and "category" in payload.model_fields_set:
        category = payload.category
    if category is None or category == models.ExpenseCategory.PAYMENT_PLANS_DEBT:
        category = _suggested_category_for_plan_type(payload.plan_type)
    if category is None or category == models.ExpenseCategory.PAYMENT_PLANS_DEBT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="payment_plans.validation.real_expense_category_required",
        )
    return category


def _validate_plan_links(
    db: Session,
    owner_id: int,
    *,
    category: models.ExpenseCategory,
    expense_subcategory_id: int | None,
    project_id: int | None,
    project_subcategory_id: int | None,
) -> None:
    validate_session_item_links(
        db,
        owner_id,
        category,
        expense_subcategory_id,
        project_id,
        project_subcategory_id,
    )


def _plan_payment_count(plan: models.PaymentPlan) -> int:
    return int(plan.payment_count or plan.months)


def _debt_counterparty_kind_for_plan(plan_type: models.PaymentPlanType) -> models.DebtCounterpartyKind:
    if plan_type in {
        models.PaymentPlanType.MORTGAGE,
        models.PaymentPlanType.AUTO_LOAN,
        models.PaymentPlanType.BANK_LOAN,
    }:
        return models.DebtCounterpartyKind.BANK
    if plan_type in {
        models.PaymentPlanType.STORE_INSTALLMENT,
        models.PaymentPlanType.PRODUCT_FINANCING,
    }:
        return models.DebtCounterpartyKind.STORE
    if plan_type == models.PaymentPlanType.SERVICE_CONTRACT:
        return models.DebtCounterpartyKind.COMPANY
    return models.DebtCounterpartyKind.OTHER


def _debt_product_kind_for_plan(plan_type: models.PaymentPlanType) -> models.DebtProductKind:
    if plan_type == models.PaymentPlanType.MORTGAGE:
        return models.DebtProductKind.MORTGAGE
    if plan_type == models.PaymentPlanType.AUTO_LOAN:
        return models.DebtProductKind.CAR_LOAN
    if plan_type == models.PaymentPlanType.BANK_LOAN:
        return models.DebtProductKind.BANK_LOAN
    if plan_type in {
        models.PaymentPlanType.STORE_INSTALLMENT,
        models.PaymentPlanType.PRODUCT_FINANCING,
    }:
        return models.DebtProductKind.STORE_INSTALLMENT
    if plan_type == models.PaymentPlanType.SERVICE_CONTRACT:
        return models.DebtProductKind.SERVICE_PAY_LATER
    return models.DebtProductKind.OTHER


def _remaining_payment_amount(payment: models.PaymentPlanPayment) -> int:
    return max(
        0,
        int(payment.amount) - int(payment.paid_amount or 0) - int(payment.written_off_amount or 0),
    )


def _payment_component_type(payment: models.PaymentPlanPayment) -> models.PaymentPlanPaymentComponentType:
    return payment.component_type or models.PaymentPlanPaymentComponentType.PRINCIPAL


def _active_unpaid_payments(plan: models.PaymentPlan) -> list[models.PaymentPlanPayment]:
    return sorted(
        [
            payment
            for payment in (plan.payments or [])
            if payment.status not in {
                models.PaymentPlanPaymentStatus.PAID,
                models.PaymentPlanPaymentStatus.SKIPPED,
            }
            and _remaining_payment_amount(payment) > 0
        ],
        key=lambda payment: (payment.due_date, payment.id or 0),
    )


def _unpaid_schedule_total(plan: models.PaymentPlan) -> int:
    return sum(_remaining_payment_amount(payment) for payment in _active_unpaid_payments(plan))


def _build_schedule_allocation_plan(
    plan: models.PaymentPlan,
    amount: int,
) -> list[tuple[models.PaymentPlanPayment, int]]:
    remaining_to_allocate = int(amount)
    allocations: list[tuple[models.PaymentPlanPayment, int]] = []
    for payment in _active_unpaid_payments(plan):
        if remaining_to_allocate <= 0:
            break
        allocation_amount = min(remaining_to_allocate, _remaining_payment_amount(payment))
        if allocation_amount > 0:
            allocations.append((payment, allocation_amount))
            remaining_to_allocate -= allocation_amount

    if remaining_to_allocate != 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="payment_plans.payment.amount_exceeds_schedule")
    return allocations


def _schedule_component_amounts(
    allocations: list[tuple[models.PaymentPlanPayment, int]],
) -> tuple[int, int]:
    principal_amount = 0
    charge_amount = 0
    for payment, amount in allocations:
        if _payment_component_type(payment) == models.PaymentPlanPaymentComponentType.CHARGE:
            charge_amount += int(amount)
        else:
            principal_amount += int(amount)
    return principal_amount, charge_amount


def _ledger_entries_by_component(
    db: Session,
    debt_transaction_id: int,
) -> dict[models.PaymentPlanPaymentComponentType, models.DebtLedgerEntry]:
    entries = (
        db.query(models.DebtLedgerEntry)
        .filter(models.DebtLedgerEntry.source_debt_transaction_id == debt_transaction_id)
        .all()
    )
    by_component: dict[models.PaymentPlanPaymentComponentType, models.DebtLedgerEntry] = {}
    for entry in entries:
        if int(entry.principal_delta or 0) < 0:
            by_component[models.PaymentPlanPaymentComponentType.PRINCIPAL] = entry
        if int(entry.charge_delta or 0) < 0:
            by_component[models.PaymentPlanPaymentComponentType.CHARGE] = entry
    return by_component


def _debt_wallet_allocations(
    allocations: list[schemas.PaymentPlanWalletAllocationIn],
) -> list[schemas.DebtTransactionWalletAllocationIn]:
    return [
        schemas.DebtTransactionWalletAllocationIn(
            wallet_id=allocation.wallet_id,
            amount=int(allocation.amount),
        )
        for allocation in allocations
    ]


def _single_wallet_id_or_none(
    allocations: list[schemas.PaymentPlanWalletAllocationIn],
) -> int | None:
    return allocations[0].wallet_id if len(allocations) == 1 else None


def _take_wallet_allocations(
    remaining_allocations: list[dict[str, int]],
    amount: int,
) -> list[schemas.PaymentPlanWalletAllocationIn]:
    amount_left = int(amount)
    taken: list[schemas.PaymentPlanWalletAllocationIn] = []
    for allocation in remaining_allocations:
        if amount_left <= 0:
            break
        available = int(allocation["amount"])
        if available <= 0:
            continue
        allocation_amount = min(available, amount_left)
        taken.append(
            schemas.PaymentPlanWalletAllocationIn(
                wallet_id=int(allocation["wallet_id"]),
                amount=allocation_amount,
            )
        )
        allocation["amount"] = available - allocation_amount
        amount_left -= allocation_amount

    if amount_left != 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="payment_plans.wallet_total_mismatch")
    return taken


def _retag_payment_plan_payment_event(
    db: Session,
    debt_ledger_entry: models.PaymentPlanLedgerEntry,
) -> None:
    if not debt_ledger_entry.financial_event_id:
        return
    event = (
        db.query(models.FinancialEvent)
        .filter(models.FinancialEvent.id == debt_ledger_entry.financial_event_id)
        .first()
    )
    if (
        event is not None
        and event.event_type == models.TransactionType.EXPENSE
        and event.reference_type == models.ReferenceType.DEBT_EXPENSE
    ):
        event.reference_type = models.ReferenceType.PAYMENT_PLAN_PAYMENT


ASSET_ELIGIBLE_PAYMENT_PLAN_TYPES = {
    models.PaymentPlanType.STORE_INSTALLMENT,
    models.PaymentPlanType.MORTGAGE,
    models.PaymentPlanType.AUTO_LOAN,
}


LOAN_DISBURSEMENT_WALLET_TYPES = {
    models.WalletType.CASH,
    models.WalletType.DEBIT,
    models.WalletType.SAVINGS,
}


def _debt_origin_kind_for_plan(plan_type: models.PaymentPlanType) -> models.DebtOriginKind:
    if plan_type == models.PaymentPlanType.BANK_LOAN:
        return models.DebtOriginKind.CASH_BORROWED
    if plan_type in {
        models.PaymentPlanType.EDUCATION_LOAN,
        models.PaymentPlanType.SERVICE_CONTRACT,
    }:
        return models.DebtOriginKind.DEFERRED_EXPENSE
    return models.DebtOriginKind.FINANCED_ASSET_PURCHASE


def _get_loan_disbursement_wallet_or_404(
    db: Session,
    owner_id: int,
    wallet_id: int,
) -> models.Wallet:
    wallet = _get_owned_wallet_or_404(db, owner_id, wallet_id)
    if not wallet.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="wallets.archived_locked")
    if (
        wallet.wallet_type not in LOAN_DISBURSEMENT_WALLET_TYPES
        or wallet.accounting_type != models.AccountingType.ASSET
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="payment_plans.loan_disbursement_wallet_not_allowed",
        )
    return wallet


def _create_loan_disbursement_event(
    db: Session,
    *,
    debt: models.Debt,
    wallet: models.Wallet,
    amount: int,
    disbursement_date: date,
    title: str,
    note: str | None = None,
) -> models.FinancialEvent:
    WalletService.adjust_balance(db, wallet.id, int(amount), models.TransactionType.DEBT_SETTLEMENT)

    event = models.FinancialEvent(
        owner_id=debt.owner_id,
        title=title[:100],
        description=note,
        event_type=models.TransactionType.DEBT_SETTLEMENT,
        reference_type=models.ReferenceType.LOAN_DISBURSEMENT,
        date=disbursement_date,
    )
    db.add(event)
    db.flush()

    db.add(
        models.WalletLedger(
            owner_id=debt.owner_id,
            event_id=event.id,
            wallet_id=wallet.id,
            amount=int(amount),
        )
    )
    db.add(
        models.EntityLedger(
            event_id=event.id,
            label=title,
            amount=int(amount),
            debt_id=debt.id,
        )
    )
    db.flush()
    return event


def _sync_plan_from_debt(db: Session, plan: models.PaymentPlan, debt: models.Debt) -> models.PaymentPlan:
    reconciled = reconcile_debt(db, debt.id)
    plan.remaining_amount = int(reconciled.remaining_amount or 0)
    if plan.status != models.PaymentPlanStatus.ARCHIVED:
        plan.status = (
            models.PaymentPlanStatus.PAID
            if int(plan.remaining_amount or 0) <= 0 and _unpaid_schedule_total(plan) <= 0
            else models.PaymentPlanStatus.ACTIVE
        )
    db.flush()
    return plan


def _apply_amount_to_payment_plan_payment(
    db: Session,
    *,
    owner_id: int,
    payment: models.PaymentPlanPayment,
    amount: int,
    paid_date: date,
    debt_transaction: models.PaymentPlanTransaction,
    debt_ledger_entry: models.PaymentPlanLedgerEntry,
    
    note: str | None,
) -> None:
    remaining_for_row = _remaining_payment_amount(payment)
    if amount <= 0 or amount > remaining_for_row:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="payment_plans.payment.invalid_allocation")

    payment.paid_amount = int(payment.paid_amount or 0) + int(amount)
    payment.paid_date = paid_date
    payment.event_id = debt_ledger_entry.financial_event_id
    payment.payment_plan_ledger_entry_id = debt_ledger_entry.id
    if note is not None:
        payment.note = note
    payment.status = (
        models.PaymentPlanPaymentStatus.PAID
        if _remaining_payment_amount(payment) == 0
        else models.PaymentPlanPaymentStatus.PARTIAL
    )

    db.add(
        models.PaymentPlanPaymentAllocation(
            owner_id=owner_id,
            payment_plan_payment_id=payment.id,
            financial_event_id=debt_ledger_entry.financial_event_id,
            payment_plan_transaction_id=debt_transaction.id,
            payment_plan_ledger_entry_id=debt_ledger_entry.id,
            
            amount=int(amount),
            paid_date=paid_date,
            note=note,
        )
    )


def _apply_schedule_allocation_plan(
    db: Session,
    *,
    allocations: list[tuple[models.PaymentPlanPayment, int]],
    paid_date: date,
    debt_transaction: models.PaymentPlanTransaction,
    ledger_entries_by_component: dict[models.PaymentPlanPaymentComponentType, models.PaymentPlanLedgerEntry],
    
    note: str | None,
) -> None:
    for payment, allocation_amount in allocations:
        component_type = _payment_component_type(payment)
        debt_ledger_entry = ledger_entries_by_component.get(component_type)
        if debt_ledger_entry is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="payment_plans.payment.missing_component_ledger")
        _apply_amount_to_payment_plan_payment(
            db,
            owner_id=payment.owner_id,
            payment=payment,
            amount=allocation_amount,
            paid_date=paid_date,
            debt_transaction=debt_transaction,
            debt_ledger_entry=debt_ledger_entry,
            
            note=note,
        )


def _build_payment_plan_details(db: Session, plan: models.PaymentPlan) -> schemas.PaymentPlanDetailsOut:
    plan_ledger_entries = (
        db.query(models.PaymentPlanLedgerEntry)
        .filter(
            models.PaymentPlanLedgerEntry.owner_id == plan.owner_id,
            models.PaymentPlanLedgerEntry.plan_id == plan.id,
        )
        .order_by(models.PaymentPlanLedgerEntry.entry_date.asc(), models.PaymentPlanLedgerEntry.id.asc())
        .all()
    )
    reversed_entry_ids = {
        int(entry.reverses_entry_id)
        for entry in plan_ledger_entries
        if entry.reverses_entry_id is not None
    }
    plan_activity = [
        schemas.PaymentPlanActivityItemOut(
            id=entry.id,
            entry_date=entry.entry_date,
            entry_type=entry.entry_type.value,
            event_subtype=entry.event_subtype,
            amount_delta=int(entry.amount_delta),
            principal_delta=int(entry.principal_delta or 0),
            charge_delta=int(entry.charge_delta or 0),
            balance_after=entry.balance_after,
            note=entry.note,
            source=entry.source.value,
            is_reversible=bool(entry.is_reversible),
            is_reversed=entry.id in reversed_entry_ids or entry.status == "REVERSED",
            reverses_entry_id=entry.reverses_entry_id,
        )
        for entry in plan_ledger_entries
    ]

    return schemas.PaymentPlanDetailsOut(
        plan=schemas.PaymentPlanWithPaymentsOut.model_validate(plan),
        plan_activity=plan_activity,
    )


def _create_payment_plan_in_transaction(
    db: Session,
    owner_id: int,
    payload: schemas.PaymentPlanCreate,
    *,
    user_tz: tzinfo,
    existing_down_payment_event: models.FinancialEvent | None = None,
    linked_asset_id: int | None = None,
) -> models.PaymentPlan:
    remaining_amount = int(payload.total_price) - int(payload.down_payment)
    if remaining_amount < 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="payment_plans.invalid_down_payment")
    if payload.track_as_asset and payload.plan_type not in ASSET_ELIGIBLE_PAYMENT_PLAN_TYPES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="payment_plans.asset_tracking_not_allowed_for_type")
    if payload.loan_disbursement_wallet_id is not None and payload.plan_type != models.PaymentPlanType.BANK_LOAN:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="payment_plans.loan_disbursement_only_for_bank_loan")
    if existing_down_payment_event is not None and existing_down_payment_event.owner_id != owner_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="expenses.not_found")

    payment_count = int(payload.months)
    base_payment = remaining_amount // payment_count if remaining_amount > 0 else 0
    plan_category = _resolve_plan_category(payload)
    _validate_plan_links(
        db,
        owner_id,
        category=plan_category,
        expense_subcategory_id=payload.expense_subcategory_id,
        project_id=payload.project_id,
        project_subcategory_id=payload.project_subcategory_id,
    )
    plan = models.PaymentPlan(
        owner_id=owner_id,
        item_name=payload.item_name,
        store_or_bank_name=payload.store_or_bank_name,
        plan_type=payload.plan_type,
        total_price=payload.total_price,
        down_payment=payload.down_payment,
        remaining_amount=remaining_amount,
        months=payload.months,
        payment_count=payment_count,
        frequency=payload.frequency,
        monthly_payment_amount=base_payment,
        regular_payment_amount=base_payment,
        schedule_rule={
            "source": "STANDARD_INTERVAL",
            "frequency": payload.frequency.value,
            "payment_count": payment_count,
        },
        status=models.PaymentPlanStatus.PAID if remaining_amount == 0 else models.PaymentPlanStatus.ACTIVE,
        start_date=payload.start_date,
        expense_category=plan_category,
        expense_subcategory_id=payload.expense_subcategory_id,
        project_id=payload.project_id,
        project_subcategory_id=payload.project_subcategory_id,
        asset_id=linked_asset_id,
    )
    db.add(plan)
    db.flush()

    down_payment_event: models.FinancialEvent | None = existing_down_payment_event
    if payload.down_payment > 0 and down_payment_event is None:
        down_payment_event = _create_payment_plan_expense_event(
            db,
            owner_id,
            title=f"{payload.item_name} down payment",
            amount=int(payload.down_payment),
            category=plan_category,
            expense_date=payload.start_date,
            wallet_allocations=payload.wallet_allocations,
            reference_type=models.ReferenceType.PAYMENT_PLAN_DOWN_PAYMENT,
            payment_plan_id=plan.id,
            subcategory_id=payload.expense_subcategory_id,
            project_id=payload.project_id,
            project_subcategory_id=payload.project_subcategory_id,
            note=f"PaymentPlan down payment at {payload.store_or_bank_name}" if payload.store_or_bank_name else None,
            user_tz=user_tz,
        )
    elif down_payment_event is not None:
        (
            db.query(models.EntityLedger)
            .filter(models.EntityLedger.event_id == down_payment_event.id)
            .update({"payment_plan_id": plan.id}, synchronize_session=False)
        )

    if payload.track_as_asset and linked_asset_id is None:
        asset = models.Asset(
            owner_id=owner_id,
            title=payload.item_name,
            description=payload.store_or_bank_name,
            origin_event_id=down_payment_event.id if down_payment_event else None,
            purchase_value=int(payload.total_price),
            current_value=int(payload.asset_current_value if payload.asset_current_value is not None else payload.total_price),
            status="owned",
        )
        db.add(asset)
        db.flush()
        plan.asset_id = asset.id

    disbursement_event = None
    if payload.loan_disbursement_wallet_id is not None:
        disbursement_wallet = _get_loan_disbursement_wallet_or_404(db, owner_id, payload.loan_disbursement_wallet_id)
        WalletService.adjust_balance(db, disbursement_wallet.id, remaining_amount, models.TransactionType.DEBT_SETTLEMENT)
        disbursement_event = models.FinancialEvent(
            owner_id=owner_id,
            title=f"{payload.item_name} loan disbursement"[:100],
            description=f"Loan disbursement from {payload.store_or_bank_name}" if payload.store_or_bank_name else None,
            event_type=models.TransactionType.DEBT_SETTLEMENT,
            reference_type=models.ReferenceType.LOAN_DISBURSEMENT,
            date=payload.start_date,
        )
        db.add(disbursement_event)
        db.flush()
        db.add(models.WalletLedger(owner_id=owner_id, event_id=disbursement_event.id, wallet_id=disbursement_wallet.id, amount=remaining_amount))
        db.add(models.EntityLedger(event_id=disbursement_event.id, label=f"{payload.item_name} loan disbursement", amount=remaining_amount, payment_plan_id=plan.id))
        db.flush()

    if remaining_amount > 0:
        db.add(models.PaymentPlanLedgerEntry(
            owner_id=owner_id,
            plan_id=plan.id,
            financial_event_id=disbursement_event.id if disbursement_event else None,
            entry_type=models.PaymentPlanLedgerEntryType.INITIAL,
            amount_delta=remaining_amount,
            principal_delta=remaining_amount,
            balance_after=remaining_amount,
            event_subtype="LOAN_DISBURSEMENT" if disbursement_event else "PAYMENT_PLAN_ORIGIN",
            entry_date=payload.start_date,
            source=models.PaymentPlanLedgerEntrySource.USER,
            note=f"Payment plan obligation for {payload.item_name}",
        ))
        db.flush()

    if remaining_amount > 0:
        remainder = remaining_amount % payment_count
        for index in range(1, payment_count + 1):
            payment_amount = base_payment + (remainder if index == payment_count else 0)
            if payment_amount <= 0:
                continue
            db.add(
                models.PaymentPlanPayment(
                    owner_id=owner_id,
                    plan_id=plan.id,
                    amount=payment_amount,
                    due_date=_scheduled_due_date(payload.start_date, payload.frequency, index),
                    component_type=models.PaymentPlanPaymentComponentType.PRINCIPAL,
                    status=models.PaymentPlanPaymentStatus.PENDING,
                )
            )

    db.flush()
    return plan



@router.get("/summary", response_model=schemas.PaymentPlanSummaryOut)
def get_payment_plan_summary(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
    user_tz: tzinfo = Depends(get_effective_user_timezone),
):
    today = today_in_tz(user_tz)

    pending = (
        db.query(
            func.count(models.PaymentPlanPayment.id),
            func.coalesce(
                func.sum(
                    models.PaymentPlanPayment.amount
                    - models.PaymentPlanPayment.paid_amount
                    - models.PaymentPlanPayment.written_off_amount
                ),
                0,
            ),
        )
        .filter(
            models.PaymentPlanPayment.owner_id == current_user.id,
            models.PaymentPlanPayment.status.in_(
                [
                    models.PaymentPlanPaymentStatus.PENDING,
                    models.PaymentPlanPaymentStatus.PARTIAL,
                ]
            ),
            models.PaymentPlanPayment.due_date > today,
        )
        .first()
    )

    current_month_start = today.replace(day=1)
    paid = (
        db.query(
            func.count(models.PaymentPlanPaymentAllocation.id),
            func.coalesce(func.sum(models.PaymentPlanPaymentAllocation.amount), 0),
        )
        .filter(
            models.PaymentPlanPaymentAllocation.owner_id == current_user.id,
            models.PaymentPlanPaymentAllocation.paid_date >= current_month_start,
        )
        .first()
    )

    overdue = (
        db.query(
            func.count(models.PaymentPlanPayment.id),
            func.coalesce(
                func.sum(
                    models.PaymentPlanPayment.amount
                    - models.PaymentPlanPayment.paid_amount
                    - models.PaymentPlanPayment.written_off_amount
                ),
                0,
            ),
        )
        .filter(
            models.PaymentPlanPayment.owner_id == current_user.id,
            models.PaymentPlanPayment.status.in_(
                [
                    models.PaymentPlanPaymentStatus.PENDING,
                    models.PaymentPlanPaymentStatus.PARTIAL,
                ]
            ),
            models.PaymentPlanPayment.due_date <= today,
        )
        .first()
    )

    return schemas.PaymentPlanSummaryOut(
        pending_count=pending[0] or 0,
        pending_amount=int(pending[1] or 0),
        paid_count=paid[0] or 0,
        paid_amount=int(paid[1] or 0),
        overdue_count=overdue[0] or 0,
        overdue_amount=int(overdue[1] or 0),
    )


@router.post("", response_model=schemas.PaymentPlanWithPaymentsOut, status_code=status.HTTP_201_CREATED)
def create_payment_plan(
    payload: schemas.PaymentPlanCreate,
    response: Response,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
    user_tz: tzinfo = Depends(get_effective_user_timezone),
):
    rate_headers = enforce_payment_plans_write_rate_limit(current_user.id)
    for key, value in rate_headers.items():
        response.headers[key] = value

    plan = _create_payment_plan_in_transaction(
        db,
        current_user.id,
        payload,
        user_tz=user_tz,
    )
    db.commit()
    db.refresh(plan)
    return plan


@router.get("", response_model=schemas.PaymentPlanListOut)
def list_payment_plans(
    status: Optional[models.PaymentPlanStatus] = None,
    limit: int = 50,
    skip: int = 0,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
):
    query = (
        db.query(models.PaymentPlan)
        .options(selectinload(models.PaymentPlan.payments))
        .filter(models.PaymentPlan.owner_id == current_user.id)
    )
    if status:
        query = query.filter(models.PaymentPlan.status == status)

    total = query.count()
    items = query.order_by(models.PaymentPlan.created_at.desc()).offset(skip).limit(limit).all()
    return schemas.PaymentPlanListOut(total=total, items=items)


@router.get("/{plan_id}", response_model=schemas.PaymentPlanWithPaymentsOut)
def get_payment_plan(
    plan_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
):
    return _get_owned_plan_or_404(db, current_user.id, plan_id)


@router.get("/{plan_id}/details", response_model=schemas.PaymentPlanDetailsOut)
def get_payment_plan_details(
    plan_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
):
    plan = _get_owned_plan_or_404(db, current_user.id, plan_id)
    return _build_payment_plan_details(db, plan)


@router.patch("/{plan_id}", response_model=schemas.PaymentPlanWithPaymentsOut)
def update_payment_plan(
    plan_id: int,
    payload: schemas.PaymentPlanUpdate,
    response: Response,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
):
    rate_headers = enforce_payment_plans_write_rate_limit(current_user.id)
    for key, value in rate_headers.items():
        response.headers[key] = value

    plan = _get_owned_plan_or_404(db, current_user.id, plan_id)
    if plan.status == models.PaymentPlanStatus.ARCHIVED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="payment_plans.archived_locked")

    update_data = payload.model_dump(exclude_unset=True)
    if "status" in update_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="payment_plans.update.status_requires_action")
    setup_fields = PAYMENT_PLAN_SETUP_UPDATE_FIELDS.intersection(update_data)
    if setup_fields and not _is_pristine_payment_plan(db, plan):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="payment_plans.update.setup_requires_pristine")

    if {
        "expense_category",
        "expense_subcategory_id",
        "project_id",
        "project_subcategory_id",
    }.intersection(update_data):
        next_category = update_data.get("expense_category", plan.expense_category)
        if next_category is None or next_category == models.ExpenseCategory.PAYMENT_PLANS_DEBT:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="payment_plans.validation.real_expense_category_required",
            )
        _validate_plan_links(
            db,
            current_user.id,
            category=next_category,
            expense_subcategory_id=update_data.get("expense_subcategory_id", plan.expense_subcategory_id),
            project_id=update_data.get("project_id", plan.project_id),
            project_subcategory_id=update_data.get("project_subcategory_id", plan.project_subcategory_id),
        )

    for field, value in update_data.items():
        setattr(plan, field, value)

    if setup_fields:
        _regenerate_pristine_payment_plan_schedule(db, plan)

    db.commit()
    db.refresh(plan)
    return plan


@router.post("/{plan_id}/payments/undo-latest", response_model=schemas.PaymentPlanDetailsOut)
def undo_latest_payment_plan_payment(
    plan_id: int,
    response: Response,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
    user_tz: tzinfo = Depends(get_effective_user_timezone),
):
    rate_headers = enforce_payment_plans_write_rate_limit(current_user.id)
    for key, value in rate_headers.items():
        response.headers[key] = value

    plan = _get_owned_plan_or_404(db, current_user.id, plan_id)
    if plan.status == models.PaymentPlanStatus.ARCHIVED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="payment_plans.archived_locked")

    latest_allocation = (
        db.query(models.PaymentPlanPaymentAllocation)
        .join(
            models.PaymentPlanPayment,
            models.PaymentPlanPayment.id == models.PaymentPlanPaymentAllocation.payment_plan_payment_id,
        )
        .filter(
            models.PaymentPlanPayment.plan_id == plan.id,
            models.PaymentPlanPayment.owner_id == current_user.id,
            models.PaymentPlanPaymentAllocation.payment_plan_transaction_id.isnot(None),
        )
        .order_by(models.PaymentPlanPaymentAllocation.paid_date.desc(), models.PaymentPlanPaymentAllocation.id.desc())
        .first()
    )
    if latest_allocation is None or latest_allocation.payment_plan_transaction_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="payment_plans.undo.no_payment")

    transaction_id = int(latest_allocation.payment_plan_transaction_id)
    allocations = (
        db.query(models.PaymentPlanPaymentAllocation)
        .options(selectinload(models.PaymentPlanPaymentAllocation.payment))
        .filter(
            models.PaymentPlanPaymentAllocation.owner_id == current_user.id,
            models.PaymentPlanPaymentAllocation.payment_plan_transaction_id == transaction_id,
        )
        .all()
    )
    if not allocations:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="payment_plans.undo.no_payment")

    ledger_entries = (
        db.query(models.PaymentPlanLedgerEntry)
        .filter(
            models.PaymentPlanLedgerEntry.owner_id == current_user.id,
            models.PaymentPlanLedgerEntry.plan_id == plan.id,
            models.PaymentPlanLedgerEntry.source_transaction_id == transaction_id,
            models.PaymentPlanLedgerEntry.entry_type == models.PaymentPlanLedgerEntryType.PAYMENT,
            models.PaymentPlanLedgerEntry.status == "POSTED",
        )
        .all()
    )
    if not ledger_entries:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="payment_plans.undo.no_payment")

    financial_event_ids = {
        int(allocation.financial_event_id)
        for allocation in allocations
        if allocation.financial_event_id is not None
    }
    for financial_event_id in financial_event_ids:
        financial_event = (
            db.query(models.FinancialEvent)
            .filter(
                models.FinancialEvent.id == financial_event_id,
                models.FinancialEvent.owner_id == current_user.id,
            )
            .first()
        )
        if financial_event is not None and financial_event.status != models.FinancialEventStatus.VOIDED:
            _create_financial_event_reversal(
                db,
                current_user.id,
                financial_event,
                today_in_tz(user_tz),
                "Undo payment plan payment",
            )

    touched_payments: dict[int, models.PaymentPlanPayment] = {}
    allocation_ids = {allocation.id for allocation in allocations}
    for allocation in allocations:
        payment = allocation.payment
        touched_payments[payment.id] = payment
        payment.paid_amount = max(0, int(payment.paid_amount or 0) - int(allocation.amount))
        db.delete(allocation)

    db.flush()

    for payment in touched_payments.values():
        remaining_allocations = sorted(
            [allocation for allocation in payment.allocations if allocation.id not in allocation_ids],
            key=lambda allocation: (allocation.paid_date, allocation.id or 0),
        )
        latest_remaining = remaining_allocations[-1] if remaining_allocations else None
        payment.event_id = latest_remaining.financial_event_id if latest_remaining else None
        payment.payment_plan_ledger_entry_id = latest_remaining.payment_plan_ledger_entry_id if latest_remaining else None
        payment.paid_date = latest_remaining.paid_date if latest_remaining else None
        if _remaining_payment_amount(payment) <= 0:
            payment.status = models.PaymentPlanPaymentStatus.PAID
        elif int(payment.paid_amount or 0) > 0 or int(payment.written_off_amount or 0) > 0:
            payment.status = models.PaymentPlanPaymentStatus.PARTIAL
        else:
            payment.status = models.PaymentPlanPaymentStatus.PENDING

    plan.remaining_amount = int(plan.remaining_amount or 0) + sum(
        -int(ledger_entry.amount_delta) for ledger_entry in ledger_entries
    )
    if plan.status != models.PaymentPlanStatus.ARCHIVED:
        plan.status = (
            models.PaymentPlanStatus.PAID
            if int(plan.remaining_amount or 0) <= 0 and _unpaid_schedule_total(plan) <= 0
            else models.PaymentPlanStatus.ACTIVE
        )

    for ledger_entry in ledger_entries:
        db.add(
            models.PaymentPlanLedgerEntry(
                owner_id=current_user.id,
                plan_id=plan.id,
                reverses_entry_id=ledger_entry.id,
                entry_type=models.PaymentPlanLedgerEntryType.REVERSAL,
                amount_delta=-int(ledger_entry.amount_delta),
                principal_delta=-int(ledger_entry.principal_delta or 0),
                charge_delta=-int(ledger_entry.charge_delta or 0),
                balance_after=int(plan.remaining_amount or 0),
                event_subtype="PAYMENT_PLAN_PAYMENT_UNDO",
                entry_date=today_in_tz(user_tz),
                source=models.PaymentPlanLedgerEntrySource.USER,
                note="Undo payment plan payment",
            )
        )
        ledger_entry.status = "REVERSED"
        ledger_entry.is_reversible = False

    db.query(models.PaymentPlanTransaction).filter(
        models.PaymentPlanTransaction.id == transaction_id,
        models.PaymentPlanTransaction.owner_id == current_user.id,
    ).delete(synchronize_session=False)

    db.commit()
    db.refresh(plan)
    return _build_payment_plan_details(db, plan)


@router.post("/{plan_id}/payments", response_model=schemas.PaymentPlanDetailsOut, status_code=status.HTTP_201_CREATED)
def record_payment_plan_payment(
    plan_id: int,
    payload: schemas.PaymentPlanPaymentRecordCreate,
    response: Response,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
    user_tz: tzinfo = Depends(get_effective_user_timezone),
):
    rate_headers = enforce_payment_plans_write_rate_limit(current_user.id)
    for key, value in rate_headers.items():
        response.headers[key] = value

    plan = _get_owned_plan_or_404(db, current_user.id, plan_id)
    if plan.status == models.PaymentPlanStatus.ARCHIVED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="payment_plans.archived_locked")

    amount = int(payload.amount)
    unpaid_schedule_total = _unpaid_schedule_total(plan)
    if unpaid_schedule_total <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="payment_plans.no_unpaid_schedule")
    if amount > unpaid_schedule_total:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="payment_plans.payment.amount_exceeds_schedule")
    schedule_allocations = _build_schedule_allocation_plan(plan, amount)
    principal_amount, charge_amount = _schedule_component_amounts(schedule_allocations)

    payment_category = _resolve_existing_plan_category(plan, None)
    if plan.expense_category is None:
        plan.expense_category = payment_category

    paid_date = payload.paid_date or today_in_tz(user_tz)
    
    component_totals: dict[models.PaymentPlanPaymentComponentType, int] = {}
    component_order: list[models.PaymentPlanPaymentComponentType] = []
    for payment, alloc_amount in schedule_allocations:
        component_type = _payment_component_type(payment)
        if component_type not in component_totals:
            component_order.append(component_type)
            component_totals[component_type] = 0
        component_totals[component_type] += int(alloc_amount)

    financial_events_by_component: dict[models.PaymentPlanPaymentComponentType, models.FinancialEvent] = {}
    if payload.wallet_allocations:
        remaining_wallet_allocations = [
            {"wallet_id": int(allocation.wallet_id), "amount": int(allocation.amount)}
            for allocation in payload.wallet_allocations
        ]
        for component_type in component_order:
            component_amount = int(component_totals[component_type])
            component_allocations = _take_wallet_allocations(remaining_wallet_allocations, component_amount)
            is_charge = component_type == models.PaymentPlanPaymentComponentType.CHARGE
            financial_events_by_component[component_type] = _create_payment_plan_expense_event(
                db,
                current_user.id,
                title=f"{plan.item_name} {'charge ' if is_charge else ''}payment",
                amount=component_amount,
                category=models.ExpenseCategory.DEBT_CHARGES if is_charge else plan.expense_category,
                expense_date=paid_date,
                wallet_allocations=component_allocations,
                reference_type=(
                    models.ReferenceType.PAYMENT_PLAN_FEE
                    if is_charge
                    else models.ReferenceType.PAYMENT_PLAN_PAYMENT
                ),
                payment_plan_id=plan.id,
                subcategory_id=None if is_charge else plan.expense_subcategory_id,
                project_id=None if is_charge else plan.project_id,
                project_subcategory_id=None if is_charge else plan.project_subcategory_id,
                note=payload.note or f"{plan.item_name} payment_plan payment",
                user_tz=user_tz,
            )

    payment_plan_transaction = models.PaymentPlanTransaction(
        owner_id=current_user.id,
        plan_id=plan.id,
        amount=amount,
        date=paid_date,
        note=payload.note or f"{plan.item_name} payment_plan payment",
    )
    db.add(payment_plan_transaction)
    db.flush()

    for wa in payload.wallet_allocations:
        db.add(models.PaymentPlanTransactionWalletAllocation(
            owner_id=current_user.id,
            plan_id=plan.id,
            payment_plan_transaction_id=payment_plan_transaction.id,
            wallet_id=wa.wallet_id,
            amount=int(wa.amount),
        ))

    plan.remaining_amount = int(plan.remaining_amount or 0) - amount

    ledger_entries_by_component: dict[models.PaymentPlanPaymentComponentType, models.PaymentPlanLedgerEntry] = {}
    for component_type in component_order:
        component_amount = int(component_totals[component_type])
        is_charge = component_type == models.PaymentPlanPaymentComponentType.CHARGE
        financial_event = financial_events_by_component.get(component_type)
        ledger_entry = models.PaymentPlanLedgerEntry(
            owner_id=current_user.id,
            plan_id=plan.id,
            financial_event_id=financial_event.id if financial_event is not None else None,
            source_transaction_id=payment_plan_transaction.id,
            entry_type=models.PaymentPlanLedgerEntryType.PAYMENT,
            amount_delta=-component_amount,
            principal_delta=0 if is_charge else -component_amount,
            charge_delta=-component_amount if is_charge else 0,
            balance_after=int(plan.remaining_amount or 0),
            entry_date=paid_date,
            source=models.PaymentPlanLedgerEntrySource.USER,
            note=payment_plan_transaction.note,
        )
        db.add(ledger_entry)
        db.flush()
        ledger_entries_by_component[component_type] = ledger_entry

    for payment, alloc_amount in schedule_allocations:
        component_type = _payment_component_type(payment)
        _apply_amount_to_payment_plan_payment(
            db,
            owner_id=current_user.id,
            payment=payment,
            amount=alloc_amount,
            paid_date=paid_date,
            debt_transaction=payment_plan_transaction,
            debt_ledger_entry=ledger_entries_by_component[component_type],
            note=payload.note,
        )

    if plan.status != models.PaymentPlanStatus.ARCHIVED:
        plan.status = (
            models.PaymentPlanStatus.PAID
            if int(plan.remaining_amount or 0) <= 0 and _unpaid_schedule_total(plan) <= 0
            else models.PaymentPlanStatus.ACTIVE
        )

    db.commit()
    db.refresh(plan)
    return _build_payment_plan_details(db, plan)


@router.post("/payments/{payment_id}/mark-paid", response_model=schemas.PaymentPlanPaymentOut)
def mark_payment_paid(
    payment_id: int,
    payload: schemas.MarkPaidIn,
    response: Response,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
    user_tz: tzinfo = Depends(get_effective_user_timezone),
):
    rate_headers = enforce_payment_plans_write_rate_limit(current_user.id)
    for key, value in rate_headers.items():
        response.headers[key] = value

    payment = (
        db.query(models.PaymentPlanPayment)
        .options(
            selectinload(models.PaymentPlanPayment.plan)
            .selectinload(models.PaymentPlan.payments)
            .selectinload(models.PaymentPlanPayment.allocations),
            selectinload(models.PaymentPlanPayment.plan),
        )
        .filter(
            models.PaymentPlanPayment.id == payment_id,
            models.PaymentPlanPayment.owner_id == current_user.id,
        )
        .first()
    )
    if not payment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="payment_plans.payment_not_found")
    if payment.status == models.PaymentPlanPaymentStatus.PAID:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="payment_plans.already_paid")

    paid_date = payload.paid_date or today_in_tz(user_tz)
    plan = payment.plan
    if plan.status == models.PaymentPlanStatus.ARCHIVED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="payment_plans.archived_locked")
    payment_category = _resolve_existing_plan_category(plan, payload.category)
    if plan.expense_category is None:
        plan.expense_category = payment_category

    remaining_for_payment = _remaining_payment_amount(payment)
    if remaining_for_payment <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="payment_plans.already_paid")
    component_type = _payment_component_type(payment)
    principal_amount = remaining_for_payment if component_type == models.PaymentPlanPaymentComponentType.PRINCIPAL else 0
    charge_amount = remaining_for_payment if component_type == models.PaymentPlanPaymentComponentType.CHARGE else 0

    payment_category = _resolve_existing_plan_category(plan, payload.category)
    if plan.expense_category is None:
        plan.expense_category = payment_category

    remaining_for_payment = _remaining_payment_amount(payment)
    if remaining_for_payment <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="payment_plans.already_paid")
    component_type = _payment_component_type(payment)
    principal_amount = remaining_for_payment if component_type == models.PaymentPlanPaymentComponentType.PRINCIPAL else 0
    charge_amount = remaining_for_payment if component_type == models.PaymentPlanPaymentComponentType.CHARGE else 0

    financial_event = None
    if payload.wallet_allocations:
        is_charge = component_type == models.PaymentPlanPaymentComponentType.CHARGE
        financial_event = _create_payment_plan_expense_event(
            db,
            current_user.id,
            title=f"{plan.item_name} {'charge ' if is_charge else ''}payment",
            amount=int(remaining_for_payment),
            category=models.ExpenseCategory.DEBT_CHARGES if is_charge else plan.expense_category,
            expense_date=paid_date,
            wallet_allocations=payload.wallet_allocations,
            reference_type=(
                models.ReferenceType.PAYMENT_PLAN_FEE
                if is_charge
                else models.ReferenceType.PAYMENT_PLAN_PAYMENT
            ),
            payment_plan_id=plan.id,
            subcategory_id=None if is_charge else plan.expense_subcategory_id,
            project_id=None if is_charge else plan.project_id,
            project_subcategory_id=None if is_charge else plan.project_subcategory_id,
            note=payload.note or f"{plan.item_name} payment_plan payment",
            user_tz=user_tz,
        )

    payment_plan_transaction = models.PaymentPlanTransaction(
        owner_id=current_user.id,
        plan_id=plan.id,
        amount=remaining_for_payment,
        date=paid_date,
        note=payload.note or payment.note or f"{plan.item_name} payment_plan payment",
    )
    db.add(payment_plan_transaction)
    db.flush()

    for wa in payload.wallet_allocations:
        db.add(models.PaymentPlanTransactionWalletAllocation(
            owner_id=current_user.id,
            plan_id=plan.id,
            payment_plan_transaction_id=payment_plan_transaction.id,
            wallet_id=wa.wallet_id,
            amount=int(wa.amount),
        ))

    plan.remaining_amount = int(plan.remaining_amount or 0) - remaining_for_payment

    ledger_entry = models.PaymentPlanLedgerEntry(
        owner_id=current_user.id,
        plan_id=plan.id,
        financial_event_id=financial_event.id if financial_event is not None else None,
        source_transaction_id=payment_plan_transaction.id,
        entry_type=models.PaymentPlanLedgerEntryType.PAYMENT,
        amount_delta=-int(remaining_for_payment),
        principal_delta=-int(principal_amount),
        charge_delta=-int(charge_amount),
        balance_after=int(plan.remaining_amount or 0),
        entry_date=paid_date,
        source=models.PaymentPlanLedgerEntrySource.USER,
        note=payment_plan_transaction.note,
    )
    db.add(ledger_entry)
    db.flush()

    _apply_amount_to_payment_plan_payment(
        db,
        owner_id=current_user.id,
        payment=payment,
        amount=remaining_for_payment,
        paid_date=paid_date,
        debt_transaction=payment_plan_transaction,
        debt_ledger_entry=ledger_entry,
        note=payload.note,
    )
    if plan.status != models.PaymentPlanStatus.ARCHIVED:
        plan.status = (
            models.PaymentPlanStatus.PAID
            if int(plan.remaining_amount or 0) <= 0 and _unpaid_schedule_total(plan) <= 0
            else models.PaymentPlanStatus.ACTIVE
        )
    db.commit()
    db.refresh(payment)
    return payment




@router.post("/payments/{payment_id}/write-off", response_model=schemas.PaymentPlanPaymentOut)
def write_off_payment(
    payment_id: int,
    response: Response,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
    user_tz: tzinfo = Depends(get_effective_user_timezone),
):
    rate_headers = enforce_payment_plans_write_rate_limit(current_user.id)
    for key, value in rate_headers.items():
        response.headers[key] = value

    payment = (
        db.query(models.PaymentPlanPayment)
        .options(
            selectinload(models.PaymentPlanPayment.plan),
        )
        .filter(
            models.PaymentPlanPayment.id == payment_id,
            models.PaymentPlanPayment.owner_id == current_user.id,
        )
        .first()
    )
    if not payment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="payment_plans.payment_not_found")
    if payment.status == models.PaymentPlanPaymentStatus.PAID:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="payment_plans.already_paid")

    plan = payment.plan
    if plan.status == models.PaymentPlanStatus.ARCHIVED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="payment_plans.archived_locked")

    remaining_for_payment = _remaining_payment_amount(payment)
    if remaining_for_payment <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="payment_plans.already_paid")

    component_type = _payment_component_type(payment)
    principal_delta = remaining_for_payment if component_type == models.PaymentPlanPaymentComponentType.PRINCIPAL else 0
    charge_delta = remaining_for_payment if component_type == models.PaymentPlanPaymentComponentType.CHARGE else 0
    paid_date = today_in_tz(user_tz)

    payment_plan_transaction = models.PaymentPlanTransaction(
        owner_id=current_user.id,
        plan_id=plan.id,
        amount=remaining_for_payment,
        date=paid_date,
        note=payment.note or "Write-off",
    )
    db.add(payment_plan_transaction)
    db.flush()

    plan.remaining_amount = int(plan.remaining_amount or 0) - remaining_for_payment

    ledger_entry = models.PaymentPlanLedgerEntry(
        owner_id=current_user.id,
        plan_id=plan.id,
        source_transaction_id=payment_plan_transaction.id,
        entry_type=models.PaymentPlanLedgerEntryType.ADJUSTMENT,
        event_subtype="PAYMENT_PLAN_WRITE_OFF",
        amount_delta=-int(remaining_for_payment),
        principal_delta=-int(principal_delta),
        charge_delta=-int(charge_delta),
        balance_after=int(plan.remaining_amount or 0),
        entry_date=paid_date,
        source=models.PaymentPlanLedgerEntrySource.USER,
        note=payment_plan_transaction.note,
    )
    db.add(ledger_entry)
    db.flush()

    payment.written_off_amount = int(payment.written_off_amount or 0) + int(remaining_for_payment)
    payment.payment_plan_ledger_entry_id = ledger_entry.id
    if _remaining_payment_amount(payment) <= 0:
        payment.status = models.PaymentPlanPaymentStatus.PAID
    if plan.status != models.PaymentPlanStatus.ARCHIVED:
        plan.status = (
            models.PaymentPlanStatus.PAID
            if int(plan.remaining_amount or 0) <= 0 and _unpaid_schedule_total(plan) <= 0
            else models.PaymentPlanStatus.ACTIVE
        )
    
    db.commit()
    db.refresh(payment)
    return payment


@router.post("/payments/{payment_id}/undo-write-off", response_model=schemas.PaymentPlanPaymentOut)
def undo_write_off_payment(
    payment_id: int,
    response: Response,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
):
    rate_headers = enforce_payment_plans_write_rate_limit(current_user.id)
    for key, value in rate_headers.items():
        response.headers[key] = value

    payment = (
        db.query(models.PaymentPlanPayment)
        .options(
            selectinload(models.PaymentPlanPayment.plan),
            selectinload(models.PaymentPlanPayment.ledger_entry),
        )
        .filter(
            models.PaymentPlanPayment.id == payment_id,
            models.PaymentPlanPayment.owner_id == current_user.id,
        )
        .first()
    )
    if not payment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="payment_plans.payment_not_found")
    
    if payment.status != models.PaymentPlanPaymentStatus.PAID or not payment.payment_plan_ledger_entry_id:
         raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="payment_plans.not_written_off")
         
    ledger_entry = payment.ledger_entry
    if (
        ledger_entry is None
        or ledger_entry.entry_type != models.PaymentPlanLedgerEntryType.ADJUSTMENT
        or ledger_entry.event_subtype != "PAYMENT_PLAN_WRITE_OFF"
    ):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="payment_plans.not_written_off")

    plan = payment.plan

    # Reverse remaining amount
    plan.remaining_amount = int(plan.remaining_amount or 0) + int(payment.written_off_amount or 0)

    payment.written_off_amount = 0
    payment.payment_plan_ledger_entry_id = None
    if _remaining_payment_amount(payment) > 0:
        payment.status = models.PaymentPlanPaymentStatus.PENDING if not payment.paid_amount else models.PaymentPlanPaymentStatus.PARTIAL

    db.delete(ledger_entry)

    if ledger_entry.source_transaction_id:
        db.query(models.PaymentPlanTransaction).filter_by(id=ledger_entry.source_transaction_id).delete()

    db.commit()
    db.refresh(payment)
    return payment



@router.post("/{plan_id}/charges", response_model=schemas.PaymentPlanWithPaymentsOut, status_code=status.HTTP_201_CREATED)
def add_payment_plan_charge(
    plan_id: int,
    payload: schemas.PaymentPlanChargeCreate,
    response: Response,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
    user_tz: tzinfo = Depends(get_effective_user_timezone),
):
    rate_headers = enforce_payment_plans_write_rate_limit(current_user.id)
    for key, value in rate_headers.items():
        response.headers[key] = value

    plan = _get_owned_plan_or_404(db, current_user.id, plan_id)
    if plan.status == models.PaymentPlanStatus.ARCHIVED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="payment_plans.archived_locked")
    if payload.wallet_allocations:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="payment_plans.charge_record_first_then_pay",
        )

    charge_date = payload.date or today_in_tz(user_tz)

    charge_type = payload.charge_type.upper()
    title_suffix = "penalty" if charge_type == "PENALTY" else "fee"
    charge = models.PaymentPlanCharge(
        owner_id=current_user.id,
        plan_id=plan.id,
        amount=int(payload.amount),
        reason=payload.note or f"PaymentPlan {title_suffix}",
        date=charge_date,
    )
    db.add(charge)
    db.flush()

    ledger_entry = models.PaymentPlanLedgerEntry(
        owner_id=current_user.id,
        plan_id=plan.id,
        entry_type=models.PaymentPlanLedgerEntryType.CHARGE,
        amount_delta=int(payload.amount),
        charge_delta=int(payload.amount),
        source_charge_id=charge.id,
        source=models.PaymentPlanLedgerEntrySource.USER,
        entry_date=charge_date,
        note=payload.note,
    )
    db.add(ledger_entry)

    db.add(
        models.PaymentPlanPayment(
            owner_id=current_user.id,
            plan_id=plan.id,
            payment_plan_charge_id=charge.id,
            amount=int(payload.amount),
            paid_amount=0,
            due_date=charge_date,
            component_type=models.PaymentPlanPaymentComponentType.CHARGE,
            status=models.PaymentPlanPaymentStatus.PENDING,
            note=payload.note or f"PaymentPlan {title_suffix}",
        )
    )

    plan.remaining_amount = int(plan.remaining_amount or 0) + int(payload.amount)
    if plan.status != models.PaymentPlanStatus.ARCHIVED:
        plan.status = models.PaymentPlanStatus.ACTIVE
    db.commit()
    db.refresh(plan)
    return plan

@router.delete("/{plan_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_payment_plan(
    plan_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
):
    plan = _get_owned_plan_or_404(db, current_user.id, plan_id)
    if not _is_pristine_payment_plan(db, plan):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="payment_plans.delete.pristine_required")

    db.delete(plan)
    db.commit()
