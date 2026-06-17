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
from ..services.debt_policy import evaluate_debt_action
from ..services.debt_service import (
    create_debt_ledger_entry,
    get_debt_total_charges,
    reconcile_debt,
    reverse_debt_transaction_ledger,
    reverse_wallet_effect,
)
from ..services.goal_funding_service import validate_wallet_goal_protection_for_outflow
from ..services.session_draft_service import validate_session_item_links
from ..services.wallet_service import WalletService
from ..session import get_db
from .debts import (
    _build_action_decisions_out,
    _build_activity_item,
    _build_debt_out,
    _create_financial_event_reversal,
    _create_debt_payment,
    _find_payment_events,
)
from .wallets import _get_owned_wallet_or_404

router = APIRouter(
    prefix="/installments",
    tags=["Installments (Nasiya)"],
)

INSTALLMENTS_WRITE_BUCKET_CAPACITY = 20
INSTALLMENTS_WRITE_REFILL_RATE = 20 / 60
INSTALLMENT_SETUP_UPDATE_FIELDS = {"total_price", "months", "frequency", "start_date"}


def enforce_installments_write_rate_limit(user_id: int) -> dict[str, str]:
    rl = consume_token_bucket(
        scope="installments_write",
        identifier=str(user_id),
        capacity=INSTALLMENTS_WRITE_BUCKET_CAPACITY,
        refill_rate_per_second=INSTALLMENTS_WRITE_REFILL_RATE,
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
            detail="installments.write_rate_limited",
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


def _scheduled_due_date(start_date: date, frequency: models.InstallmentFrequency, index: int) -> date:
    if frequency == models.InstallmentFrequency.WEEKLY:
        return start_date + timedelta(weeks=index)
    if frequency == models.InstallmentFrequency.BIWEEKLY:
        return start_date + timedelta(weeks=index * 2)
    if frequency == models.InstallmentFrequency.QUARTERLY:
        return _add_months(start_date, index * 3)
    if frequency == models.InstallmentFrequency.YEARLY:
        return _add_years(start_date, index)
    return _add_months(start_date, index)


def _resolve_budget_for_installment_month(
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
    allocations: list[schemas.InstallmentWalletAllocationIn],
    expected_total: int,
) -> list[tuple[models.Wallet, int]]:
    if expected_total <= 0:
        return []

    if not allocations:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="installments.wallet_allocations_required")

    allocation_total = int(sum(int(item.amount) for item in allocations))
    if allocation_total != int(expected_total):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="installments.wallet_total_mismatch")

    seen_wallet_ids: set[int] = set()
    validated: list[tuple[models.Wallet, int]] = []
    for allocation in allocations:
        if allocation.wallet_id in seen_wallet_ids:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="installments.wallet_duplicate")
        seen_wallet_ids.add(allocation.wallet_id)
        wallet = _get_owned_wallet_or_404(db, owner_id, allocation.wallet_id)
        if not wallet.is_active:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="wallets.archived_locked")
        validated.append((wallet, int(allocation.amount)))
    return validated


def _create_installment_expense_event(
    db: Session,
    owner_id: int,
    *,
    title: str,
    amount: int,
    category: models.ExpenseCategory,
    expense_date: date,
    wallet_allocations: list[schemas.InstallmentWalletAllocationIn],
    reference_type: str,
    installment_plan_id: int,
    installment_payment_id: int | None = None,
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
    budget = _resolve_budget_for_installment_month(db, owner_id, category, expense_date)
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
            outflow_type="installment_payment",
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
            installment_plan_id=installment_plan_id,
            installment_payment_id=installment_payment_id,
        )
    )
    check_budget_alerts(db, budget)
    db.flush()
    return event


def _get_owned_plan_or_404(db: Session, user_id: int, plan_id: int) -> models.InstallmentPlan:
    plan = (
        db.query(models.InstallmentPlan)
        .options(
            selectinload(models.InstallmentPlan.payments).selectinload(models.InstallmentPayment.allocations),
            selectinload(models.InstallmentPlan.debt),
        )
        .filter(
            models.InstallmentPlan.id == plan_id,
            models.InstallmentPlan.owner_id == user_id,
        )
        .first()
    )
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="installments.not_found")
    return plan


def _raise_policy_denied(decision) -> None:
    if not decision.allowed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=decision.reason_code or "debts.policy.action_blocked",
        )


def _is_pristine_installment_plan(db: Session, plan: models.InstallmentPlan) -> bool:
    for payment in plan.payments or []:
        if int(payment.paid_amount or 0) > 0:
            return False
        if int(payment.written_off_amount or 0) > 0:
            return False
        if payment.event_id is not None or payment.debt_ledger_entry_id is not None:
            return False
        if payment.debt_charge_id is not None:
            return False
        if payment.component_type != models.InstallmentPaymentComponentType.PRINCIPAL:
            return False
        if payment.allocations:
            return False

    return (
        db.query(models.Goals.id)
        .filter(
            models.Goals.owner_id == plan.owner_id,
            models.Goals.intent == models.GoalIntent.PAY_OBLIGATION,
            models.Goals.linked_installment_plan_id == plan.id,
            models.Goals.status != models.GoalStatus.ARCHIVED,
        )
        .first()
        is None
    )


def _regenerate_pristine_installment_schedule(db: Session, plan: models.InstallmentPlan) -> None:
    remaining_amount = int(plan.total_price) - int(plan.down_payment)
    if remaining_amount < 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="installments.invalid_down_payment")

    payment_count = int(plan.months)
    base_payment = remaining_amount // payment_count if remaining_amount > 0 else 0

    for payment in list(plan.payments or []):
        if payment.component_type == models.InstallmentPaymentComponentType.PRINCIPAL:
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
    plan.status = models.InstallmentStatus.PAID if remaining_amount == 0 else models.InstallmentStatus.ACTIVE

    if remaining_amount > 0:
        remainder = remaining_amount % payment_count
        for index in range(1, payment_count + 1):
            payment_amount = base_payment + (remainder if index == payment_count else 0)
            if payment_amount <= 0:
                continue
            plan.payments.append(
                models.InstallmentPayment(
                    owner_id=plan.owner_id,
                    amount=payment_amount,
                    due_date=_scheduled_due_date(plan.start_date, plan.frequency, index),
                    component_type=models.InstallmentPaymentComponentType.PRINCIPAL,
                    status=models.InstallmentPaymentStatus.PENDING,
                )
            )


def _resolve_existing_plan_category(
    plan: models.InstallmentPlan,
    requested_category: models.ExpenseCategory | None = None,
) -> models.ExpenseCategory:
    category = plan.expense_category or requested_category or _suggested_category_for_plan_type(plan.plan_type)
    if category is None or category == models.ExpenseCategory.INSTALLMENTS_DEBT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="installments.validation.real_expense_category_required",
        )
    return category


def _plan_category(plan: models.InstallmentPlan) -> models.ExpenseCategory:
    return _resolve_existing_plan_category(plan)


def _counterparty_name(plan: models.InstallmentPlan) -> str:
    return (plan.store_or_bank_name or plan.item_name or "Installment provider")[:100]


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


def _resolve_plan_category(payload: schemas.InstallmentPlanCreate) -> models.ExpenseCategory:
    category = payload.expense_category
    if category is None and "category" in payload.model_fields_set:
        category = payload.category
    if category is None or category == models.ExpenseCategory.INSTALLMENTS_DEBT:
        category = _suggested_category_for_plan_type(payload.plan_type)
    if category is None or category == models.ExpenseCategory.INSTALLMENTS_DEBT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="installments.validation.real_expense_category_required",
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


def _plan_payment_count(plan: models.InstallmentPlan) -> int:
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


def _remaining_payment_amount(payment: models.InstallmentPayment) -> int:
    return max(
        0,
        int(payment.amount) - int(payment.paid_amount or 0) - int(payment.written_off_amount or 0),
    )


def _payment_component_type(payment: models.InstallmentPayment) -> models.InstallmentPaymentComponentType:
    return payment.component_type or models.InstallmentPaymentComponentType.PRINCIPAL


def _active_unpaid_payments(plan: models.InstallmentPlan) -> list[models.InstallmentPayment]:
    return sorted(
        [
            payment
            for payment in (plan.payments or [])
            if payment.status not in {
                models.InstallmentPaymentStatus.PAID,
                models.InstallmentPaymentStatus.SKIPPED,
            }
            and _remaining_payment_amount(payment) > 0
        ],
        key=lambda payment: (payment.due_date, payment.id or 0),
    )


def _unpaid_schedule_total(plan: models.InstallmentPlan) -> int:
    return sum(_remaining_payment_amount(payment) for payment in _active_unpaid_payments(plan))


def _build_schedule_allocation_plan(
    plan: models.InstallmentPlan,
    amount: int,
) -> list[tuple[models.InstallmentPayment, int]]:
    remaining_to_allocate = int(amount)
    allocations: list[tuple[models.InstallmentPayment, int]] = []
    for payment in _active_unpaid_payments(plan):
        if remaining_to_allocate <= 0:
            break
        allocation_amount = min(remaining_to_allocate, _remaining_payment_amount(payment))
        if allocation_amount > 0:
            allocations.append((payment, allocation_amount))
            remaining_to_allocate -= allocation_amount

    if remaining_to_allocate != 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="installments.payment.amount_exceeds_schedule")
    return allocations


def _schedule_component_amounts(
    allocations: list[tuple[models.InstallmentPayment, int]],
) -> tuple[int, int]:
    principal_amount = 0
    charge_amount = 0
    for payment, amount in allocations:
        if _payment_component_type(payment) == models.InstallmentPaymentComponentType.CHARGE:
            charge_amount += int(amount)
        else:
            principal_amount += int(amount)
    return principal_amount, charge_amount


def _ledger_entries_by_component(
    db: Session,
    debt_transaction_id: int,
) -> dict[models.InstallmentPaymentComponentType, models.DebtLedgerEntry]:
    entries = (
        db.query(models.DebtLedgerEntry)
        .filter(models.DebtLedgerEntry.source_debt_transaction_id == debt_transaction_id)
        .all()
    )
    by_component: dict[models.InstallmentPaymentComponentType, models.DebtLedgerEntry] = {}
    for entry in entries:
        if int(entry.principal_delta or 0) < 0:
            by_component[models.InstallmentPaymentComponentType.PRINCIPAL] = entry
        if int(entry.charge_delta or 0) < 0:
            by_component[models.InstallmentPaymentComponentType.CHARGE] = entry
    return by_component


def _debt_wallet_allocations(
    allocations: list[schemas.InstallmentWalletAllocationIn],
) -> list[schemas.DebtTransactionWalletAllocationIn]:
    return [
        schemas.DebtTransactionWalletAllocationIn(
            wallet_id=allocation.wallet_id,
            amount=int(allocation.amount),
        )
        for allocation in allocations
    ]


def _single_wallet_id_or_none(
    allocations: list[schemas.InstallmentWalletAllocationIn],
) -> int | None:
    return allocations[0].wallet_id if len(allocations) == 1 else None


def _retag_installment_payment_event(
    db: Session,
    debt_ledger_entry: models.DebtLedgerEntry,
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
        event.reference_type = models.ReferenceType.INSTALLMENT_PAYMENT


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
            detail="installments.loan_disbursement_wallet_not_allowed",
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


def _create_plan_debt(
    db: Session,
    plan: models.InstallmentPlan,
    *,
    linked_asset_id: int | None = None,
    loan_disbursement_wallet_id: int | None = None,
    user_tz: tzinfo | None = None,
) -> models.Debt | None:
    amount = int(plan.remaining_amount or 0)
    if amount <= 0:
        return None
    disbursement_wallet: models.Wallet | None = None
    if loan_disbursement_wallet_id is not None:
        if plan.plan_type != models.PaymentPlanType.BANK_LOAN:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="installments.loan_disbursement_only_for_bank_loan",
            )
        if user_tz is not None and plan.start_date > today_in_tz(user_tz):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="installments.loan_disbursement_date_in_future")
        disbursement_wallet = _get_loan_disbursement_wallet_or_404(
            db,
            plan.owner_id,
            loan_disbursement_wallet_id,
        )

    debt = models.Debt(
        owner_id=plan.owner_id,
        debt_type=models.DebtType.OWING,
        origin_kind=_debt_origin_kind_for_plan(plan.plan_type),
        counterparty_kind=_debt_counterparty_kind_for_plan(plan.plan_type),
        product_kind=_debt_product_kind_for_plan(plan.plan_type),
        counterparty_name=_counterparty_name(plan),
        initial_amount=amount,
        remaining_amount=amount,
        currency=plan.currency or "UZS",
        description=f"Installment plan for {plan.item_name}",
        status=models.DebtStatus.ACTIVE,
        date=plan.start_date,
        expected_return_date=_scheduled_due_date(plan.start_date, plan.frequency, _plan_payment_count(plan)),
        is_money_transferred=bool(disbursement_wallet),
        initial_wallet_id=disbursement_wallet.id if disbursement_wallet else None,
        expense_category=_plan_category(plan),
        expense_subcategory_id=plan.expense_subcategory_id,
        project_id=plan.project_id,
        project_subcategory_id=plan.project_subcategory_id,
    )
    db.add(debt)
    db.flush()

    disbursement_event: models.FinancialEvent | None = None
    if disbursement_wallet is not None:
        disbursement_event = _create_loan_disbursement_event(
            db,
            debt=debt,
            wallet=disbursement_wallet,
            amount=amount,
            disbursement_date=plan.start_date,
            title=f"{plan.item_name} loan disbursement",
            note=f"Loan disbursement from {plan.store_or_bank_name}" if plan.store_or_bank_name else None,
        )
        debt.linked_event_id = disbursement_event.id

    create_debt_ledger_entry(
        db,
        owner_id=plan.owner_id,
        debt_id=debt.id,
        entry_type=models.DebtLedgerEntryType.INITIAL,
        amount_delta=amount,
        principal_delta=amount,
        financial_event_id=disbursement_event.id if disbursement_event else None,
        wallet_id=disbursement_wallet.id if disbursement_wallet else None,
        event_subtype=(
            "LOAN_DISBURSEMENT"
            if disbursement_event is not None
            else "PAYMENT_PLAN_ORIGIN"
        ),
        entry_date=plan.start_date,
        source=models.DebtLedgerEntrySource.USER,
        note=f"Installment obligation for {plan.item_name}",
    )

    details = models.DebtFormalDetails(
        debt_id=debt.id,
        owner_id=plan.owner_id,
        institution_name=plan.store_or_bank_name,
        linked_asset_id=linked_asset_id,
        terms_summary=f"{_plan_payment_count(plan)} {plan.frequency.value.lower()} payments",
    )
    db.add(details)

    plan.debt_id = debt.id
    db.flush()
    reconcile_debt(db, debt.id)
    return debt


def _ensure_plan_debt(db: Session, plan: models.InstallmentPlan) -> models.Debt:
    if plan.debt is not None:
        return plan.debt
    if plan.debt_id is not None:
        debt = (
            db.query(models.Debt)
            .filter(models.Debt.id == plan.debt_id, models.Debt.owner_id == plan.owner_id)
            .first()
        )
        if debt:
            plan.debt = debt
            return debt

    debt = _create_plan_debt(db, plan, linked_asset_id=plan.asset_id)
    if debt is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="installments.no_remaining_balance")
    plan.debt = debt
    return debt


def _sync_plan_from_debt(db: Session, plan: models.InstallmentPlan, debt: models.Debt) -> models.InstallmentPlan:
    reconciled = reconcile_debt(db, debt.id)
    plan.remaining_amount = int(reconciled.remaining_amount or 0)
    if plan.status != models.InstallmentStatus.ARCHIVED:
        plan.status = (
            models.InstallmentStatus.PAID
            if int(plan.remaining_amount or 0) <= 0 and _unpaid_schedule_total(plan) <= 0
            else models.InstallmentStatus.ACTIVE
        )
    db.flush()
    return plan


def _apply_amount_to_installment_payment(
    db: Session,
    *,
    owner_id: int,
    payment: models.InstallmentPayment,
    amount: int,
    paid_date: date,
    debt_transaction: models.DebtTransaction,
    debt_ledger_entry: models.DebtLedgerEntry,
    wallet_id: int | None,
    note: str | None,
) -> None:
    remaining_for_row = _remaining_payment_amount(payment)
    if amount <= 0 or amount > remaining_for_row:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="installments.payment.invalid_allocation")

    payment.paid_amount = int(payment.paid_amount or 0) + int(amount)
    payment.paid_date = paid_date
    payment.event_id = debt_ledger_entry.financial_event_id
    payment.debt_ledger_entry_id = debt_ledger_entry.id
    if note is not None:
        payment.note = note
    payment.status = (
        models.InstallmentPaymentStatus.PAID
        if _remaining_payment_amount(payment) == 0
        else models.InstallmentPaymentStatus.PARTIAL
    )

    db.add(
        models.InstallmentPaymentAllocation(
            owner_id=owner_id,
            installment_payment_id=payment.id,
            financial_event_id=debt_ledger_entry.financial_event_id,
            debt_transaction_id=debt_transaction.id,
            debt_ledger_entry_id=debt_ledger_entry.id,
            wallet_id=wallet_id,
            amount=int(amount),
            paid_date=paid_date,
            note=note,
        )
    )


def _apply_schedule_allocation_plan(
    db: Session,
    *,
    allocations: list[tuple[models.InstallmentPayment, int]],
    paid_date: date,
    debt_transaction: models.DebtTransaction,
    ledger_entries_by_component: dict[models.InstallmentPaymentComponentType, models.DebtLedgerEntry],
    wallet_id: int | None,
    note: str | None,
) -> None:
    for payment, allocation_amount in allocations:
        component_type = _payment_component_type(payment)
        debt_ledger_entry = ledger_entries_by_component.get(component_type)
        if debt_ledger_entry is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="installments.payment.missing_component_ledger")
        _apply_amount_to_installment_payment(
            db,
            owner_id=payment.owner_id,
            payment=payment,
            amount=allocation_amount,
            paid_date=paid_date,
            debt_transaction=debt_transaction,
            debt_ledger_entry=debt_ledger_entry,
            wallet_id=wallet_id,
            note=note,
        )


def _build_installment_details(db: Session, plan: models.InstallmentPlan) -> schemas.InstallmentPlanDetailsOut:
    debt = plan.debt
    debt_activity: list[schemas.DebtActivityItemOut] = []
    debt_actions: list[schemas.DebtActionDecisionOut] = []
    debt_out: schemas.DebtOut | None = None
    if debt is not None:
        ledger_entries = (
            db.query(models.DebtLedgerEntry)
            .filter(
                models.DebtLedgerEntry.owner_id == plan.owner_id,
                models.DebtLedgerEntry.debt_id == debt.id,
            )
            .order_by(models.DebtLedgerEntry.entry_date.asc(), models.DebtLedgerEntry.id.asc())
            .all()
        )
        debt_out = _build_debt_out(debt, total_charges=get_debt_total_charges(db, debt.id))
        debt_actions = _build_action_decisions_out(db, debt, allow_payment_plan_managed=True)
        debt_activity = [_build_activity_item(db, debt, entry) for entry in ledger_entries]

    return schemas.InstallmentPlanDetailsOut(
        plan=schemas.InstallmentPlanWithPaymentsOut.model_validate(plan),
        debt=debt_out,
        debt_actions=debt_actions,
        debt_activity=debt_activity,
    )


def _create_installment_plan_in_transaction(
    db: Session,
    owner_id: int,
    payload: schemas.InstallmentPlanCreate,
    *,
    user_tz: tzinfo,
    existing_down_payment_event: models.FinancialEvent | None = None,
    linked_asset_id: int | None = None,
) -> models.InstallmentPlan:
    remaining_amount = int(payload.total_price) - int(payload.down_payment)
    if remaining_amount < 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="installments.invalid_down_payment")
    if payload.track_as_asset and payload.plan_type not in ASSET_ELIGIBLE_PAYMENT_PLAN_TYPES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="installments.asset_tracking_not_allowed_for_type")
    if payload.loan_disbursement_wallet_id is not None and payload.plan_type != models.PaymentPlanType.BANK_LOAN:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="installments.loan_disbursement_only_for_bank_loan")
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
    plan = models.InstallmentPlan(
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
        status=models.InstallmentStatus.PAID if remaining_amount == 0 else models.InstallmentStatus.ACTIVE,
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
        down_payment_event = _create_installment_expense_event(
            db,
            owner_id,
            title=f"{payload.item_name} down payment",
            amount=int(payload.down_payment),
            category=plan_category,
            expense_date=payload.start_date,
            wallet_allocations=payload.wallet_allocations,
            reference_type=models.ReferenceType.INSTALLMENT_DOWN_PAYMENT,
            installment_plan_id=plan.id,
            subcategory_id=payload.expense_subcategory_id,
            project_id=payload.project_id,
            project_subcategory_id=payload.project_subcategory_id,
            note=f"Installment down payment at {payload.store_or_bank_name}" if payload.store_or_bank_name else None,
            user_tz=user_tz,
        )
    elif down_payment_event is not None:
        (
            db.query(models.EntityLedger)
            .filter(models.EntityLedger.event_id == down_payment_event.id)
            .update({"installment_plan_id": plan.id}, synchronize_session=False)
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

    linked_debt = _create_plan_debt(
        db,
        plan,
        linked_asset_id=plan.asset_id,
        loan_disbursement_wallet_id=payload.loan_disbursement_wallet_id,
        user_tz=user_tz,
    )
    if linked_debt and linked_debt.formal_details and plan.asset_id:
        linked_debt.formal_details.linked_asset_id = plan.asset_id

    if remaining_amount > 0:
        remainder = remaining_amount % payment_count
        for index in range(1, payment_count + 1):
            payment_amount = base_payment + (remainder if index == payment_count else 0)
            if payment_amount <= 0:
                continue
            db.add(
                models.InstallmentPayment(
                    owner_id=owner_id,
                    plan_id=plan.id,
                    amount=payment_amount,
                    due_date=_scheduled_due_date(payload.start_date, payload.frequency, index),
                    component_type=models.InstallmentPaymentComponentType.PRINCIPAL,
                    status=models.InstallmentPaymentStatus.PENDING,
                )
            )

    db.flush()
    return plan


@router.get("/summary", response_model=schemas.InstallmentSummaryOut)
def get_installment_summary(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
    user_tz: tzinfo = Depends(get_effective_user_timezone),
):
    today = today_in_tz(user_tz)

    pending = (
        db.query(
            func.count(models.InstallmentPayment.id),
            func.coalesce(
                func.sum(
                    models.InstallmentPayment.amount
                    - models.InstallmentPayment.paid_amount
                    - models.InstallmentPayment.written_off_amount
                ),
                0,
            ),
        )
        .filter(
            models.InstallmentPayment.owner_id == current_user.id,
            models.InstallmentPayment.status.in_(
                [
                    models.InstallmentPaymentStatus.PENDING,
                    models.InstallmentPaymentStatus.PARTIAL,
                ]
            ),
            models.InstallmentPayment.due_date > today,
        )
        .first()
    )

    current_month_start = today.replace(day=1)
    paid = (
        db.query(
            func.count(models.InstallmentPaymentAllocation.id),
            func.coalesce(func.sum(models.InstallmentPaymentAllocation.amount), 0),
        )
        .filter(
            models.InstallmentPaymentAllocation.owner_id == current_user.id,
            models.InstallmentPaymentAllocation.paid_date >= current_month_start,
        )
        .first()
    )

    overdue = (
        db.query(
            func.count(models.InstallmentPayment.id),
            func.coalesce(
                func.sum(
                    models.InstallmentPayment.amount
                    - models.InstallmentPayment.paid_amount
                    - models.InstallmentPayment.written_off_amount
                ),
                0,
            ),
        )
        .filter(
            models.InstallmentPayment.owner_id == current_user.id,
            models.InstallmentPayment.status.in_(
                [
                    models.InstallmentPaymentStatus.PENDING,
                    models.InstallmentPaymentStatus.PARTIAL,
                ]
            ),
            models.InstallmentPayment.due_date <= today,
        )
        .first()
    )

    return schemas.InstallmentSummaryOut(
        pending_count=pending[0] or 0,
        pending_amount=int(pending[1] or 0),
        paid_count=paid[0] or 0,
        paid_amount=int(paid[1] or 0),
        overdue_count=overdue[0] or 0,
        overdue_amount=int(overdue[1] or 0),
    )


@router.post("", response_model=schemas.InstallmentPlanWithPaymentsOut, status_code=status.HTTP_201_CREATED)
def create_installment_plan(
    payload: schemas.InstallmentPlanCreate,
    response: Response,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
    user_tz: tzinfo = Depends(get_effective_user_timezone),
):
    rate_headers = enforce_installments_write_rate_limit(current_user.id)
    for key, value in rate_headers.items():
        response.headers[key] = value

    plan = _create_installment_plan_in_transaction(
        db,
        current_user.id,
        payload,
        user_tz=user_tz,
    )
    db.commit()
    db.refresh(plan)
    return plan


@router.get("", response_model=schemas.InstallmentPlanListOut)
def list_installment_plans(
    status: Optional[models.InstallmentStatus] = None,
    limit: int = 50,
    skip: int = 0,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
):
    query = (
        db.query(models.InstallmentPlan)
        .options(selectinload(models.InstallmentPlan.payments))
        .filter(models.InstallmentPlan.owner_id == current_user.id)
    )
    if status:
        query = query.filter(models.InstallmentPlan.status == status)

    total = query.count()
    items = query.order_by(models.InstallmentPlan.created_at.desc()).offset(skip).limit(limit).all()
    return schemas.InstallmentPlanListOut(total=total, items=items)


@router.get("/{plan_id}", response_model=schemas.InstallmentPlanWithPaymentsOut)
def get_installment_plan(
    plan_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
):
    return _get_owned_plan_or_404(db, current_user.id, plan_id)


@router.get("/{plan_id}/details", response_model=schemas.InstallmentPlanDetailsOut)
def get_installment_plan_details(
    plan_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
):
    plan = _get_owned_plan_or_404(db, current_user.id, plan_id)
    return _build_installment_details(db, plan)


@router.patch("/{plan_id}", response_model=schemas.InstallmentPlanWithPaymentsOut)
def update_installment_plan(
    plan_id: int,
    payload: schemas.InstallmentPlanUpdate,
    response: Response,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
):
    rate_headers = enforce_installments_write_rate_limit(current_user.id)
    for key, value in rate_headers.items():
        response.headers[key] = value

    plan = _get_owned_plan_or_404(db, current_user.id, plan_id)
    if plan.status == models.InstallmentStatus.ARCHIVED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="installments.archived_locked")

    update_data = payload.model_dump(exclude_unset=True)
    if "status" in update_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="installments.update.status_requires_action")
    setup_fields = INSTALLMENT_SETUP_UPDATE_FIELDS.intersection(update_data)
    if setup_fields and not _is_pristine_installment_plan(db, plan):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="installments.update.setup_requires_pristine")

    for field, value in update_data.items():
        setattr(plan, field, value)

    if setup_fields:
        _regenerate_pristine_installment_schedule(db, plan)

    if plan.debt is not None:
        plan.debt.counterparty_name = _counterparty_name(plan)
        if setup_fields:
            plan.debt.initial_amount = int(plan.remaining_amount)
            plan.debt.remaining_amount = int(plan.remaining_amount)
            plan.debt.expected_return_date = _scheduled_due_date(plan.start_date, plan.frequency, _plan_payment_count(plan))
            initial_entry = (
                db.query(models.DebtLedgerEntry)
                .filter(
                    models.DebtLedgerEntry.owner_id == current_user.id,
                    models.DebtLedgerEntry.debt_id == plan.debt.id,
                    models.DebtLedgerEntry.entry_type == models.DebtLedgerEntryType.INITIAL,
                )
                .first()
            )
            if initial_entry is not None:
                initial_entry.amount_delta = int(plan.remaining_amount)
                initial_entry.principal_delta = int(plan.remaining_amount)
        if plan.debt.formal_details is not None:
            plan.debt.formal_details.institution_name = plan.store_or_bank_name
            if setup_fields:
                plan.debt.formal_details.next_due_date = _scheduled_due_date(plan.start_date, plan.frequency, 1)
                plan.debt.formal_details.terms_summary = f"{_plan_payment_count(plan)} {plan.frequency.value.lower()} payments"

    db.commit()
    db.refresh(plan)
    return plan


@router.post("/{plan_id}/payments/undo-latest", response_model=schemas.InstallmentPlanDetailsOut)
def undo_latest_installment_payment(
    plan_id: int,
    response: Response,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
    user_tz: tzinfo = Depends(get_effective_user_timezone),
):
    rate_headers = enforce_installments_write_rate_limit(current_user.id)
    for key, value in rate_headers.items():
        response.headers[key] = value

    plan = _get_owned_plan_or_404(db, current_user.id, plan_id)
    if plan.status == models.InstallmentStatus.ARCHIVED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="installments.archived_locked")

    latest_allocation = (
        db.query(models.InstallmentPaymentAllocation)
        .join(
            models.InstallmentPayment,
            models.InstallmentPayment.id == models.InstallmentPaymentAllocation.installment_payment_id,
        )
        .filter(
            models.InstallmentPayment.plan_id == plan.id,
            models.InstallmentPayment.owner_id == current_user.id,
            models.InstallmentPaymentAllocation.debt_transaction_id.isnot(None),
        )
        .order_by(models.InstallmentPaymentAllocation.paid_date.desc(), models.InstallmentPaymentAllocation.id.desc())
        .first()
    )
    if latest_allocation is None or latest_allocation.debt_transaction_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="installments.undo.no_payment")

    transaction_id = int(latest_allocation.debt_transaction_id)
    goal_link = (
        db.query(models.Goals.id)
        .filter(
            models.Goals.owner_id == current_user.id,
            models.Goals.linked_debt_transaction_id == transaction_id,
            models.Goals.status != models.GoalStatus.ARCHIVED,
        )
        .first()
    )
    if goal_link is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="installments.undo.goal_linked_payment")

    debt = _ensure_plan_debt(db, plan)
    transaction = (
        db.query(models.DebtTransaction)
        .filter(
            models.DebtTransaction.id == transaction_id,
            models.DebtTransaction.owner_id == current_user.id,
            models.DebtTransaction.debt_id == debt.id,
        )
        .first()
    )
    if transaction is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="debts.transaction.not_found")

    undo_date = today_in_tz(user_tz)
    linked_events = _find_payment_events(db, current_user.id, debt.id, transaction.id)
    if linked_events:
        for event in linked_events:
            _create_financial_event_reversal(
                db,
                current_user.id,
                event,
                undo_date,
                "Installment payment undone",
            )
    elif transaction.wallet_id is not None:
        reverse_delta = transaction.amount if debt.debt_type == models.DebtType.OWING else -transaction.amount
        WalletService.adjust_balance(db, transaction.wallet_id, reverse_delta)

    reverse_debt_transaction_ledger(
        db,
        owner_id=current_user.id,
        debt_id=debt.id,
        transaction_id=transaction.id,
        entry_date=undo_date,
        note="Installment payment undone",
    )

    allocations = (
        db.query(models.InstallmentPaymentAllocation)
        .join(
            models.InstallmentPayment,
            models.InstallmentPayment.id == models.InstallmentPaymentAllocation.installment_payment_id,
        )
        .filter(
            models.InstallmentPayment.plan_id == plan.id,
            models.InstallmentPayment.owner_id == current_user.id,
            models.InstallmentPaymentAllocation.debt_transaction_id == transaction.id,
        )
        .all()
    )
    affected_payments = {allocation.payment for allocation in allocations}
    for allocation in allocations:
        payment = allocation.payment
        payment.paid_amount = max(0, int(payment.paid_amount or 0) - int(allocation.amount or 0))
        db.delete(allocation)
    db.flush()

    for payment in affected_payments:
        remaining_allocations = sorted(payment.allocations, key=lambda item: (item.paid_date, item.id))
        if remaining_allocations:
            latest = remaining_allocations[-1]
            payment.event_id = latest.financial_event_id
            payment.debt_ledger_entry_id = latest.debt_ledger_entry_id
            payment.paid_date = latest.paid_date
        elif int(payment.written_off_amount or 0) == 0:
            payment.event_id = None
            payment.debt_ledger_entry_id = None
            payment.paid_date = None

        if _remaining_payment_amount(payment) == 0:
            payment.status = models.InstallmentPaymentStatus.PAID
        elif int(payment.paid_amount or 0) > 0 or int(payment.written_off_amount or 0) > 0:
            payment.status = models.InstallmentPaymentStatus.PARTIAL
        else:
            payment.status = models.InstallmentPaymentStatus.PENDING

    _sync_plan_from_debt(db, plan, debt)
    from app.services.goal_funding_service import sync_debt_goal_targets
    sync_debt_goal_targets(db, current_user.id, debt.id)

    db.commit()
    db.refresh(plan)
    return _build_installment_details(db, plan)


@router.post("/{plan_id}/payments", response_model=schemas.InstallmentPlanDetailsOut, status_code=status.HTTP_201_CREATED)
def record_installment_payment(
    plan_id: int,
    payload: schemas.InstallmentPaymentRecordCreate,
    response: Response,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
    user_tz: tzinfo = Depends(get_effective_user_timezone),
):
    rate_headers = enforce_installments_write_rate_limit(current_user.id)
    for key, value in rate_headers.items():
        response.headers[key] = value

    plan = _get_owned_plan_or_404(db, current_user.id, plan_id)
    if plan.status == models.InstallmentStatus.ARCHIVED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="installments.archived_locked")

    amount = int(payload.amount)
    unpaid_schedule_total = _unpaid_schedule_total(plan)
    if unpaid_schedule_total <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="installments.no_unpaid_schedule")
    if amount > unpaid_schedule_total:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="installments.payment.amount_exceeds_schedule")
    schedule_allocations = _build_schedule_allocation_plan(plan, amount)
    principal_amount, charge_amount = _schedule_component_amounts(schedule_allocations)

    debt = _ensure_plan_debt(db, plan)
    _raise_policy_denied(
        evaluate_debt_action(
            db,
            debt,
            models.DebtActionKind.RECORD_PAYMENT,
            allow_payment_plan_managed=True,
        )
    )

    paid_date = payload.paid_date or today_in_tz(user_tz)
    debt_transaction, debt_ledger_entry = _create_debt_payment(
        db,
        debt,
        amount=amount,
        transaction_date=paid_date,
        wallet_allocations=_debt_wallet_allocations(payload.wallet_allocations),
        note=payload.note or f"{plan.item_name} installment payment",
        principal_amount_override=principal_amount,
        charge_amount_override=charge_amount,
    )
    ledger_entries_by_component = _ledger_entries_by_component(db, debt_transaction.id)
    for ledger_entry in ledger_entries_by_component.values():
        _retag_installment_payment_event(db, ledger_entry)
    _apply_schedule_allocation_plan(
        db,
        allocations=schedule_allocations,
        paid_date=paid_date,
        debt_transaction=debt_transaction,
        ledger_entries_by_component=ledger_entries_by_component,
        wallet_id=_single_wallet_id_or_none(payload.wallet_allocations),
        note=payload.note,
    )
    _sync_plan_from_debt(db, plan, debt)
    
    from ..services.goal_funding_service import sync_debt_goal_targets
    sync_debt_goal_targets(db, current_user.id, debt.id)

    db.commit()
    plan = _get_owned_plan_or_404(db, current_user.id, plan.id)
    return _build_installment_details(db, plan)


@router.post("/payments/{payment_id}/mark-paid", response_model=schemas.InstallmentPaymentOut)
def mark_payment_paid(
    payment_id: int,
    payload: schemas.MarkPaidIn,
    response: Response,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
    user_tz: tzinfo = Depends(get_effective_user_timezone),
):
    rate_headers = enforce_installments_write_rate_limit(current_user.id)
    for key, value in rate_headers.items():
        response.headers[key] = value

    payment = (
        db.query(models.InstallmentPayment)
        .options(
            selectinload(models.InstallmentPayment.plan)
            .selectinload(models.InstallmentPlan.payments)
            .selectinload(models.InstallmentPayment.allocations),
            selectinload(models.InstallmentPayment.plan).selectinload(models.InstallmentPlan.debt),
        )
        .filter(
            models.InstallmentPayment.id == payment_id,
            models.InstallmentPayment.owner_id == current_user.id,
        )
        .first()
    )
    if not payment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="installments.payment_not_found")
    if payment.status == models.InstallmentPaymentStatus.PAID:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="installments.already_paid")

    paid_date = payload.paid_date or today_in_tz(user_tz)
    plan = payment.plan
    if plan.status == models.InstallmentStatus.ARCHIVED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="installments.archived_locked")
    payment_category = _resolve_existing_plan_category(plan, payload.category)
    if plan.expense_category is None:
        plan.expense_category = payment_category

    remaining_for_payment = _remaining_payment_amount(payment)
    if remaining_for_payment <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="installments.already_paid")
    component_type = _payment_component_type(payment)
    principal_amount = remaining_for_payment if component_type == models.InstallmentPaymentComponentType.PRINCIPAL else 0
    charge_amount = remaining_for_payment if component_type == models.InstallmentPaymentComponentType.CHARGE else 0

    debt = _ensure_plan_debt(db, plan)
    if debt.expense_category is None:
        debt.expense_category = payment_category
    _raise_policy_denied(
        evaluate_debt_action(
            db,
            debt,
            models.DebtActionKind.RECORD_PAYMENT,
            allow_payment_plan_managed=True,
        )
    )

    debt_transaction, debt_ledger_entry = _create_debt_payment(
        db,
        debt,
        amount=remaining_for_payment,
        transaction_date=paid_date,
        wallet_allocations=_debt_wallet_allocations(payload.wallet_allocations),
        note=payload.note or payment.note or f"{plan.item_name} installment payment",
        principal_amount_override=principal_amount,
        charge_amount_override=charge_amount,
    )
    ledger_entries_by_component = _ledger_entries_by_component(db, debt_transaction.id)
    debt_ledger_entry = ledger_entries_by_component.get(component_type)
    if debt_ledger_entry is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="installments.payment.missing_component_ledger")
    _retag_installment_payment_event(db, debt_ledger_entry)
    _apply_amount_to_installment_payment(
        db,
        owner_id=current_user.id,
        payment=payment,
        amount=remaining_for_payment,
        paid_date=paid_date,
        debt_transaction=debt_transaction,
        debt_ledger_entry=debt_ledger_entry,
        wallet_id=_single_wallet_id_or_none(payload.wallet_allocations),
        note=payload.note,
    )
    _sync_plan_from_debt(db, plan, debt)
    
    from app.services.goal_funding_service import sync_debt_goal_targets
    sync_debt_goal_targets(db, current_user.id, debt.id)

    db.commit()
    db.refresh(payment)
    return payment


@router.post("/payments/{payment_id}/write-off", response_model=schemas.InstallmentPaymentOut)
def write_off_payment(
    payment_id: int,
    response: Response,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
    user_tz: tzinfo = Depends(get_effective_user_timezone),
):
    rate_headers = enforce_installments_write_rate_limit(current_user.id)
    for key, value in rate_headers.items():
        response.headers[key] = value

    payment = (
        db.query(models.InstallmentPayment)
        .options(
            selectinload(models.InstallmentPayment.plan).selectinload(models.InstallmentPlan.debt),
        )
        .filter(
            models.InstallmentPayment.id == payment_id,
            models.InstallmentPayment.owner_id == current_user.id,
        )
        .first()
    )
    if not payment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="installments.payment_not_found")
    if payment.status == models.InstallmentPaymentStatus.PAID:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="installments.already_paid")

    plan = payment.plan
    if plan.status == models.InstallmentStatus.ARCHIVED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="installments.archived_locked")

    remaining_for_payment = _remaining_payment_amount(payment)
    if remaining_for_payment <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="installments.already_paid")

    debt = _ensure_plan_debt(db, plan)

    component_type = _payment_component_type(payment)
    principal_delta = -remaining_for_payment if component_type == models.InstallmentPaymentComponentType.PRINCIPAL else 0
    charge_delta = -remaining_for_payment if component_type == models.InstallmentPaymentComponentType.CHARGE else 0

    ledger_entry = create_debt_ledger_entry(
        db,
        owner_id=current_user.id,
        debt_id=debt.id,
        entry_type=models.DebtLedgerEntryType.ADJUSTMENT,
        amount_delta=-remaining_for_payment,
        principal_delta=principal_delta,
        charge_delta=charge_delta,
        source_debt_charge_id=payment.debt_charge_id if component_type == models.InstallmentPaymentComponentType.CHARGE else None,
        event_subtype="INSTALLMENT_WRITE_OFF",
        entry_date=today_in_tz(user_tz),
        source=models.DebtLedgerEntrySource.USER,
        note=f"Write-off for installment payment (ID: {payment.id})",
    )

    payment.written_off_amount = int(payment.written_off_amount or 0) + int(remaining_for_payment)
    payment.status = models.InstallmentPaymentStatus.PAID
    payment.debt_ledger_entry_id = ledger_entry.id
    
    # Goal Auto-Heals
    _sync_plan_from_debt(db, plan, debt)
    from app.services.goal_funding_service import sync_debt_goal_targets
    sync_debt_goal_targets(db, current_user.id, debt.id)
    
    db.commit()
    db.refresh(payment)
    return payment


@router.post("/payments/{payment_id}/undo-write-off", response_model=schemas.InstallmentPaymentOut)
def undo_write_off_payment(
    payment_id: int,
    response: Response,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
):
    rate_headers = enforce_installments_write_rate_limit(current_user.id)
    for key, value in rate_headers.items():
        response.headers[key] = value

    payment = (
        db.query(models.InstallmentPayment)
        .options(
            selectinload(models.InstallmentPayment.plan).selectinload(models.InstallmentPlan.debt),
            selectinload(models.InstallmentPayment.debt_ledger_entry)
        )
        .filter(
            models.InstallmentPayment.id == payment_id,
            models.InstallmentPayment.owner_id == current_user.id,
        )
        .first()
    )
    if not payment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="installments.payment_not_found")
    
    if payment.status != models.InstallmentPaymentStatus.PAID or not payment.debt_ledger_entry_id:
         raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="installments.not_written_off")
         
    ledger_entry = payment.debt_ledger_entry
    if (
        ledger_entry.entry_type != models.DebtLedgerEntryType.ADJUSTMENT
        or ledger_entry.event_subtype != "INSTALLMENT_WRITE_OFF"
    ):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="installments.not_written_off")

    plan = payment.plan
    debt = _ensure_plan_debt(db, plan)

    written_off_amount = min(int(payment.written_off_amount or 0), abs(int(ledger_entry.amount_delta or 0)))
    db.delete(ledger_entry)
    payment.debt_ledger_entry_id = None
    payment.written_off_amount = max(0, int(payment.written_off_amount or 0) - int(written_off_amount))
    db.flush()

    payment.status = (
        models.InstallmentPaymentStatus.PARTIAL 
        if int(payment.paid_amount or 0) > 0 
        else models.InstallmentPaymentStatus.PENDING
    )

    _sync_plan_from_debt(db, plan, debt)
    from app.services.goal_funding_service import sync_debt_goal_targets
    sync_debt_goal_targets(db, current_user.id, debt.id)
    
    db.commit()
    db.refresh(payment)
    return payment


@router.post("/{plan_id}/charges", response_model=schemas.InstallmentPlanWithPaymentsOut, status_code=status.HTTP_201_CREATED)
def add_installment_charge(
    plan_id: int,
    payload: schemas.InstallmentChargeCreate,
    response: Response,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
    user_tz: tzinfo = Depends(get_effective_user_timezone),
):
    rate_headers = enforce_installments_write_rate_limit(current_user.id)
    for key, value in rate_headers.items():
        response.headers[key] = value

    plan = _get_owned_plan_or_404(db, current_user.id, plan_id)
    if plan.status == models.InstallmentStatus.ARCHIVED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="installments.archived_locked")
    if payload.wallet_allocations:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="installments.charge_record_first_then_pay",
        )

    charge_date = payload.date or today_in_tz(user_tz)
    debt = _ensure_plan_debt(db, plan)
    _raise_policy_denied(
        evaluate_debt_action(
            db,
            debt,
            models.DebtActionKind.ADD_CHARGE,
            allow_payment_plan_managed=True,
        )
    )

    charge_type = payload.charge_type.upper()
    title_suffix = "penalty" if charge_type == "PENALTY" else "fee"
    charge = models.DebtCharge(
        owner_id=current_user.id,
        debt_id=debt.id,
        amount=int(payload.amount),
        reason=payload.note or f"Installment {title_suffix}",
        date=charge_date,
    )
    db.add(charge)
    db.flush()

    create_debt_ledger_entry(
        db,
        owner_id=current_user.id,
        debt_id=debt.id,
        entry_type=models.DebtLedgerEntryType.CHARGE,
        amount_delta=int(payload.amount),
        charge_delta=int(payload.amount),
        source_debt_charge_id=charge.id,
        event_subtype=f"INSTALLMENT_{charge_type}",
        entry_date=charge_date,
        note=payload.note,
    )

    db.add(
        models.InstallmentPayment(
            owner_id=current_user.id,
            plan_id=plan.id,
            debt_charge_id=charge.id,
            amount=int(payload.amount),
            due_date=charge_date,
            component_type=models.InstallmentPaymentComponentType.CHARGE,
            status=models.InstallmentPaymentStatus.PENDING,
            note=payload.note or f"Installment {title_suffix}",
        )
    )
    _sync_plan_from_debt(db, plan, debt)

    db.commit()
    db.refresh(plan)
    return plan


@router.delete("/{plan_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_installment_plan(
    plan_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
):
    plan = _get_owned_plan_or_404(db, current_user.id, plan_id)
    if not _is_pristine_installment_plan(db, plan):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="installments.delete.pristine_required")
    linked_debt = plan.debt
    linked_event = None
    if linked_debt is not None and linked_debt.linked_event_id is not None:
        linked_event = (
            db.query(models.FinancialEvent)
            .filter(
                models.FinancialEvent.id == linked_debt.linked_event_id,
                models.FinancialEvent.owner_id == current_user.id,
            )
            .first()
        )
        if linked_event is not None:
            for leg in linked_event.wallet_legs:
                if leg.wallet and not leg.wallet.is_active:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="installments.delete.wallet_archived",
                    )

    db.delete(plan)
    if linked_event is not None:
        reverse_wallet_effect(db, linked_event)
        db.delete(linked_event)
    if linked_debt is not None:
        db.delete(linked_debt)
    db.commit()
