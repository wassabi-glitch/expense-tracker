from datetime import date, tzinfo
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session
from sqlalchemy.orm import selectinload

from .. import models, oauth2, schemas
from ..session import get_db
from ..services.budget_service import (
    apply_budget_month_setup,
    build_budget_subcategory_out,
    build_budget_month_summary,
    build_budget_month_setup_preview,
    build_budget_out,
    compute_budget_chain,
    get_budget_subcategory_limit,
    get_budget_month_computations,
    get_budget_detail,
    get_owned_subcategory_or_404,
    get_project_budget_summaries,
    get_subcategory_spent_for_month,
    recompute_budget_chain,
    validate_budget_plan_capacity,
    validate_subcategory_total_limit,
)
from ..services.category_policy import validate_active_expense_category
from ..services.debt_payment_service import create_debt_payment as create_debt_payment_service
from ..services.debt_service import reconcile_debt
from ..services.goal_funding_service import sync_debt_goal_targets
from ..services.wallet_service import WalletService
from app.redis_rate_limiter import consume_token_bucket
from app.timezone import get_effective_user_timezone, today_in_tz


router = APIRouter(
    prefix="/budgets",
    tags=["Budgets"],
)

BUDGET_WRITE_BUCKET_CAPACITY = 10
BUDGET_WRITE_REFILL_RATE = 10 / 60


def _get_budget_or_404(
    db: Session,
    owner_id: int,
    budget_year: int,
    budget_month: int,
    category: models.ExpenseCategory,
) -> models.Budget:
    budget = (
        db.query(models.Budget)
        .filter(
            models.Budget.owner_id == owner_id,
            models.Budget.category == category,
            models.Budget.budget_year == budget_year,
            models.Budget.budget_month == budget_month,
        )
        .first()
    )
    if not budget:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="budgets.not_found")
    return budget


def _get_budget_by_id_or_404(
    db: Session,
    owner_id: int,
    budget_id: int,
) -> models.Budget:
    budget = (
        db.query(models.Budget)
        .filter(models.Budget.id == budget_id, models.Budget.owner_id == owner_id)
        .with_for_update()
        .first()
    )
    if not budget:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="budgets.not_found")
    return budget


def _budgets_for_category(
    db: Session,
    owner_id: int,
    category: models.ExpenseCategory,
) -> list[models.Budget]:
    return (
        db.query(models.Budget)
        .filter(
            models.Budget.owner_id == owner_id,
            models.Budget.category == category,
        )
        .order_by(models.Budget.budget_year.asc(), models.Budget.budget_month.asc())
        .all()
    )


def _get_active_income_source_or_404(
    db: Session,
    owner_id: int,
    source_id: int,
) -> models.IncomeSource:
    source = (
        db.query(models.IncomeSource)
        .filter(
            models.IncomeSource.id == source_id,
            models.IncomeSource.owner_id == owner_id,
        )
        .first()
    )
    if not source:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="income.source_not_found")
    if not source.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="income.source_inactive")
    return source


def _get_expected_income_or_404(
    db: Session,
    owner_id: int,
    expected_income_id: int,
) -> models.ExpectedIncome:
    expected_income = (
        db.query(models.ExpectedIncome)
        .options(
            selectinload(models.ExpectedIncome.source),
            selectinload(models.ExpectedIncome.debt),
        )
        .filter(
            models.ExpectedIncome.id == expected_income_id,
            models.ExpectedIncome.owner_id == owner_id,
        )
        .first()
    )
    if not expected_income:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="expected_income.not_found")
    return expected_income


def _get_expected_payment_debt_or_404(
    db: Session,
    owner_id: int,
    debt_id: int,
) -> models.Debt:
    debt = (
        db.query(models.Debt)
        .filter(
            models.Debt.id == debt_id,
            models.Debt.owner_id == owner_id,
        )
        .first()
    )
    if not debt:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="debts.not_found")
    if debt.debt_type != models.DebtType.OWED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="expected_income.debt_must_be_receivable")
    if debt.status != models.DebtStatus.ACTIVE or int(debt.remaining_amount or 0) <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="expected_income.debt_not_active_receivable")
    return debt


def _validate_expected_income_source_shape(source_id: int | None, debt_id: int | None) -> None:
    if (source_id is None) == (debt_id is None):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="expected_income.one_source_required")


def _resolve_expected_income_wallet_allocations(
    db: Session,
    owner_id: int,
    *,
    amount: int,
    wallet_id: int | None,
    wallet_allocations: list[schemas.IncomeWalletAllocationIn],
) -> list[tuple[models.Wallet, int]]:
    requested = wallet_allocations
    if not requested and wallet_id is not None:
        requested = [schemas.IncomeWalletAllocationIn(wallet_id=wallet_id, amount=amount)]
    if not requested:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="income.wallet_required")

    total = sum(int(item.amount) for item in requested)
    if total != int(amount):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="income.wallet_allocation_total_mismatch")

    resolved: list[tuple[models.Wallet, int]] = []
    seen_wallet_ids: set[int] = set()
    for allocation in requested:
        if allocation.wallet_id in seen_wallet_ids:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="income.wallet_allocation_duplicate")
        seen_wallet_ids.add(allocation.wallet_id)
        wallet = (
            db.query(models.Wallet)
            .filter(models.Wallet.id == allocation.wallet_id, models.Wallet.owner_id == owner_id)
            .first()
        )
        if wallet is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="wallets.not_found")
        if not wallet.is_active:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="wallets.archived_locked")
        resolved.append((wallet, int(allocation.amount)))
    return resolved


def _record_expected_income_event(
    db: Session,
    *,
    owner_id: int,
    amount: int,
    source_id: int | None,
    note: str | None,
    income_date: date,
    wallet_allocations: list[tuple[models.Wallet, int]],
) -> models.FinancialEvent:
    event = models.FinancialEvent(
        owner_id=owner_id,
        title="Expected income received",
        description=note,
        event_type=models.TransactionType.INCOME,
        date=income_date,
    )
    db.add(event)
    db.flush()

    for wallet, allocation_amount in wallet_allocations:
        WalletService.adjust_balance(db, wallet.id, int(allocation_amount), models.TransactionType.INCOME)
        db.add(
            models.WalletLedger(
                owner_id=owner_id,
                event_id=event.id,
                wallet_id=wallet.id,
                amount=int(allocation_amount),
            )
        )

    db.add(
        models.EntityLedger(
            event_id=event.id,
            amount=int(amount),
            income_source_id=source_id,
        )
    )
    db.flush()
    return event


def _validate_expected_income_month(
    due_date: date,
    budget_year: int,
    budget_month: int,
) -> None:
    if due_date.year != budget_year or due_date.month != budget_month:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="expected_income.month_mismatch")


def enforce_budget_write_rate_limit(user_id: int) -> dict[str, str]:
    rl = consume_token_bucket(
        scope="budgets_write",
        identifier=str(user_id),
        capacity=BUDGET_WRITE_BUCKET_CAPACITY,
        refill_rate_per_second=BUDGET_WRITE_REFILL_RATE,
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
            detail="budgets.write_rate_limited",
            headers=headers,
        )
    return headers


def validate_budget_month_window(
    budget_year: int,
    budget_month: int,
    user_tz: tzinfo,
) -> None:
    candidate = date(budget_year, budget_month, 1)
    min_allowed = date(schemas.MIN_BUDGET_YEAR, 1, 1)
    today_local = today_in_tz(user_tz)
    max_allowed = date(
        today_local.year + schemas.MAX_BUDGET_YEARS_AHEAD,
        today_local.month,
        1,
    )

    if candidate < min_allowed:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="budgets.month_too_early")
    if candidate > max_allowed:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="budgets.month_too_far_in_future")


def _apply_headers(response: Response, headers: dict[str, str]) -> None:
    for key, value in headers.items():
        response.headers[key] = value


def _validate_rollover_fields(
    rollover_mode: str | None,
    max_rollover_amount: int | None,
) -> None:
    if rollover_mode is None:
        return
    normalized = rollover_mode.upper()
    if normalized not in {"FIXED", "PERCENT"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="budgets.rollover_mode_invalid")
    if normalized == "PERCENT" and max_rollover_amount is not None and max_rollover_amount > 100:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="budgets.rollover_percent_invalid")


@router.post("/", response_model=schemas.BudgetOut, status_code=status.HTTP_201_CREATED)
def create_budget(
    budget: schemas.BudgetCreate,
    response: Response,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
    user_tz: tzinfo = Depends(get_effective_user_timezone),
):
    _apply_headers(response, enforce_budget_write_rate_limit(current_user.id))
    validate_budget_month_window(budget.budget_year, budget.budget_month, user_tz)
    validate_active_expense_category(
        budget.category,
        error_detail="budgets.validation.real_expense_category_required",
    )
    _validate_rollover_fields(budget.rollover_mode, budget.max_rollover_amount)

    duplicate = (
        db.query(models.Budget)
        .filter(
            models.Budget.owner_id == current_user.id,
            models.Budget.category == budget.category,
            models.Budget.budget_year == budget.budget_year,
            models.Budget.budget_month == budget.budget_month,
        )
        .first()
    )
    if duplicate:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="budgets.already_exists")

    if budget.sweep_target_goal_id is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="budgets.sweep_removed")

    new_budget = models.Budget(**budget.model_dump(), owner_id=current_user.id, owner=current_user)
    db.add(new_budget)
    db.flush()
    recompute_budget_chain(db, current_user.id, budget.category)
    validate_budget_plan_capacity(db, current_user.id, budget.budget_year, budget.budget_month)
    db.commit()
    db.refresh(new_budget)

    category_budgets = _budgets_for_category(db, current_user.id, budget.category)
    computed = compute_budget_chain(db, current_user.id, category_budgets)
    return next(build_budget_out(item) for item in computed if item.budget.id == new_budget.id)


@router.get("/", response_model=List[schemas.BudgetOut])
def get_budgets(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
):
    budgets = (
        db.query(models.Budget)
        .filter(models.Budget.owner_id == current_user.id)
        .order_by(
            models.Budget.category.asc(),
            models.Budget.budget_year.asc(),
            models.Budget.budget_month.asc(),
        )
        .all()
    )
    if not budgets:
        return []

    grouped: dict[models.ExpenseCategory, list[models.Budget]] = {}
    for budget in budgets:
        grouped.setdefault(budget.category, []).append(budget)

    outputs: list[schemas.BudgetOut] = []
    for items in grouped.values():
        outputs.extend(build_budget_out(item) for item in compute_budget_chain(db, current_user.id, items))

    outputs.sort(key=lambda item: (item.budget_year, item.budget_month, str(item.category)), reverse=True)
    return outputs


@router.get("/item", response_model=schemas.BudgetOut)
def get_budget(
    budget_year: int,
    budget_month: int,
    category: schemas.ExpenseCategory,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
):
    budget = _get_budget_or_404(db, current_user.id, budget_year, budget_month, category)
    computed = compute_budget_chain(db, current_user.id, [budget])
    return build_budget_out(computed[0])


@router.get("/item/detail", response_model=schemas.BudgetDetailOut)
def get_budget_detail_route(
    budget_year: int,
    budget_month: int,
    category: schemas.ExpenseCategory,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
):
    budget = _get_budget_or_404(db, current_user.id, budget_year, budget_month, category)
    return get_budget_detail(db, current_user.id, budget)


@router.patch("/item", response_model=schemas.BudgetOut)
def update_budget(
    budget_year: int,
    budget_month: int,
    category: schemas.ExpenseCategory,
    budget_update: schemas.BudgetUpdate,
    response: Response,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
):
    _apply_headers(response, enforce_budget_write_rate_limit(current_user.id))
    budget = _get_budget_or_404(db, current_user.id, budget_year, budget_month, category)
    previous_effective_total = sum(
        int(item.effective_monthly_limit or 0)
        for item in get_budget_month_computations(db, current_user.id, budget_year, budget_month)
    )

    update_data = budget_update.model_dump(exclude_unset=True)
    if "rollover_mode" in update_data or "max_rollover_amount" in update_data:
        _validate_rollover_fields(
            update_data.get("rollover_mode", budget.rollover_mode),
            update_data.get("max_rollover_amount", budget.max_rollover_amount),
        )

    if "sweep_target_goal_id" in update_data and update_data["sweep_target_goal_id"] is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="budgets.sweep_removed")

    for field, value in update_data.items():
        setattr(budget, field, value)

    recompute_budget_chain(db, current_user.id, category)
    next_effective_total = sum(
        int(item.effective_monthly_limit or 0)
        for item in get_budget_month_computations(db, current_user.id, budget_year, budget_month)
    )
    if next_effective_total > previous_effective_total:
        validate_budget_plan_capacity(db, current_user.id, budget_year, budget_month)
    db.commit()
    db.refresh(budget)
    computed = compute_budget_chain(db, current_user.id, [budget])
    return build_budget_out(computed[0])


@router.delete("/item", status_code=status.HTTP_204_NO_CONTENT)
def delete_budget(
    budget_year: int,
    budget_month: int,
    category: schemas.ExpenseCategory,
    response: Response,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
):
    _apply_headers(response, enforce_budget_write_rate_limit(current_user.id))
    budget = _get_budget_or_404(db, current_user.id, budget_year, budget_month, category)

    start, end = date(budget_year, budget_month, 1), date(budget_year + 1, 1, 1) if budget_month == 12 else date(budget_year, budget_month + 1, 1)
    has_dependent_expense = (
        db.query(models.EntityLedger.id)
        .join(models.FinancialEvent, models.FinancialEvent.id == models.EntityLedger.event_id)
        .filter(
            models.FinancialEvent.owner_id == current_user.id,
            models.FinancialEvent.status == models.FinancialEventStatus.POSTED,
            models.EntityLedger.budget_id == budget.id,
            models.FinancialEvent.event_type.in_(
                [models.TransactionType.EXPENSE, models.TransactionType.REFUND]
            ),
            models.FinancialEvent.date >= start,
            models.FinancialEvent.date < end,
        )
        .first()
    )
    if has_dependent_expense:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="budgets.has_linked_expenses")

    db.delete(budget)
    db.flush()
    recompute_budget_chain(db, current_user.id, category)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/projects", response_model=list[schemas.ProjectBudgetOut])
def get_project_budgets(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
):
    return get_project_budget_summaries(db, current_user.id)


@router.get("/month-summary", response_model=schemas.BudgetMonthSummaryOut)
def get_budget_month_summary(
    budget_year: int,
    budget_month: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
    user_tz: tzinfo = Depends(get_effective_user_timezone),
):
    validate_budget_month_window(budget_year, budget_month, user_tz)
    return build_budget_month_summary(db, current_user.id, budget_year, budget_month)


@router.post("/month-setup/preview", response_model=schemas.BudgetMonthSetupPreviewOut)
def preview_budget_month_setup(
    payload: schemas.BudgetMonthSetupRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
    user_tz: tzinfo = Depends(get_effective_user_timezone),
):
    validate_budget_month_window(payload.budget_year, payload.budget_month, user_tz)
    return build_budget_month_setup_preview(
        db,
        current_user.id,
        payload.budget_year,
        payload.budget_month,
        payload.mode,
    )


@router.post("/month-setup/apply", response_model=schemas.BudgetMonthSetupPreviewOut)
def apply_budget_month_setup_route(
    payload: schemas.BudgetMonthSetupRequest,
    response: Response,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
    user_tz: tzinfo = Depends(get_effective_user_timezone),
):
    _apply_headers(response, enforce_budget_write_rate_limit(current_user.id))
    validate_budget_month_window(payload.budget_year, payload.budget_month, user_tz)
    result = apply_budget_month_setup(
        db,
        current_user.id,
        payload.budget_year,
        payload.budget_month,
        payload.mode,
    )
    db.commit()
    return result


@router.get("/expected-incomes", response_model=list[schemas.ExpectedIncomeOut])
def list_expected_incomes(
    budget_year: int,
    budget_month: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
    user_tz: tzinfo = Depends(get_effective_user_timezone),
):
    validate_budget_month_window(budget_year, budget_month, user_tz)
    return (
        db.query(models.ExpectedIncome)
        .options(
            selectinload(models.ExpectedIncome.source),
            selectinload(models.ExpectedIncome.debt),
        )
        .filter(
            models.ExpectedIncome.owner_id == current_user.id,
            models.ExpectedIncome.budget_year == budget_year,
            models.ExpectedIncome.budget_month == budget_month,
        )
        .order_by(models.ExpectedIncome.due_date.asc(), models.ExpectedIncome.id.asc())
        .all()
    )


@router.post("/expected-incomes", response_model=schemas.ExpectedIncomeOut, status_code=status.HTTP_201_CREATED)
def create_expected_income(
    payload: schemas.ExpectedIncomeCreate,
    response: Response,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
    user_tz: tzinfo = Depends(get_effective_user_timezone),
):
    _apply_headers(response, enforce_budget_write_rate_limit(current_user.id))
    validate_budget_month_window(payload.budget_year, payload.budget_month, user_tz)
    _validate_expected_income_month(payload.due_date, payload.budget_year, payload.budget_month)
    _validate_expected_income_source_shape(payload.source_id, payload.debt_id)
    if payload.source_id is not None:
        _get_active_income_source_or_404(db, current_user.id, payload.source_id)
    if payload.debt_id is not None:
        _get_expected_payment_debt_or_404(db, current_user.id, payload.debt_id)

    expected_income = models.ExpectedIncome(
        owner_id=current_user.id,
        source_id=payload.source_id,
        debt_id=payload.debt_id,
        amount=payload.amount,
        due_date=payload.due_date,
        budget_year=payload.budget_year,
        budget_month=payload.budget_month,
        status=models.ExpectedIncomeStatus.EXPECTED,
        note=payload.note.strip() if payload.note else None,
    )
    db.add(expected_income)
    db.commit()
    db.refresh(expected_income)
    return _get_expected_income_or_404(db, current_user.id, int(expected_income.id))


@router.patch("/expected-incomes/{expected_income_id}", response_model=schemas.ExpectedIncomeOut)
def update_expected_income(
    expected_income_id: int,
    payload: schemas.ExpectedIncomeUpdate,
    response: Response,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
    user_tz: tzinfo = Depends(get_effective_user_timezone),
):
    _apply_headers(response, enforce_budget_write_rate_limit(current_user.id))
    expected_income = _get_expected_income_or_404(db, current_user.id, expected_income_id)
    update_data = payload.model_dump(exclude_unset=True)

    if "source_id" in update_data and update_data["source_id"] is not None:
        _get_active_income_source_or_404(db, current_user.id, int(update_data["source_id"]))
    if "debt_id" in update_data and update_data["debt_id"] is not None:
        _get_expected_payment_debt_or_404(db, current_user.id, int(update_data["debt_id"]))

    next_source_id = update_data.get("source_id", expected_income.source_id)
    next_debt_id = update_data.get("debt_id", expected_income.debt_id)
    _validate_expected_income_source_shape(next_source_id, next_debt_id)

    next_due_date = update_data.get("due_date", expected_income.due_date)
    next_budget_year = update_data.get("budget_year", expected_income.budget_year)
    next_budget_month = update_data.get("budget_month", expected_income.budget_month)
    validate_budget_month_window(int(next_budget_year), int(next_budget_month), user_tz)
    _validate_expected_income_month(next_due_date, int(next_budget_year), int(next_budget_month))

    for field, value in update_data.items():
        setattr(expected_income, field, value.strip() if field == "note" and value else value)

    db.commit()
    db.refresh(expected_income)
    return _get_expected_income_or_404(db, current_user.id, int(expected_income.id))


@router.post("/expected-incomes/{expected_income_id}/mark-received", response_model=schemas.ExpectedIncomeOut)
def mark_expected_income_received(
    expected_income_id: int,
    payload: schemas.ExpectedIncomeMarkReceivedCreate,
    response: Response,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
    user_tz: tzinfo = Depends(get_effective_user_timezone),
):
    _apply_headers(response, enforce_budget_write_rate_limit(current_user.id))
    expected_income = _get_expected_income_or_404(db, current_user.id, expected_income_id)
    if expected_income.status != models.ExpectedIncomeStatus.EXPECTED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="expected_income.not_expected")

    received_date = payload.date or today_in_tz(user_tz)
    wallet_allocations = _resolve_expected_income_wallet_allocations(
        db,
        current_user.id,
        amount=int(payload.received_amount),
        wallet_id=payload.wallet_id,
        wallet_allocations=payload.wallet_allocations,
    )

    if expected_income.debt_id is not None:
        debt = _get_expected_payment_debt_or_404(db, current_user.id, int(expected_income.debt_id))
        _, ledger_entry = create_debt_payment_service(
            db,
            debt,
            amount=int(payload.received_amount),
            transaction_date=received_date,
            wallet_allocations=[
                schemas.DebtTransactionWalletAllocationIn(
                    wallet_id=wallet.id,
                    amount=int(allocation_amount),
                )
                for wallet, allocation_amount in wallet_allocations
            ],
            note=payload.note or expected_income.note,
            income_source_id=debt.income_source_id,
        )
        reconcile_debt(db, debt.id)
        sync_debt_goal_targets(db, current_user.id, debt.id)
        linked_transaction_id = ledger_entry.financial_event_id
    else:
        event = _record_expected_income_event(
            db,
            owner_id=current_user.id,
            amount=int(payload.received_amount),
            source_id=expected_income.source_id,
            note=payload.note or expected_income.note,
            income_date=received_date,
            wallet_allocations=wallet_allocations,
        )
        linked_transaction_id = event.id

    expected_income.status = models.ExpectedIncomeStatus.RECEIVED
    expected_income.received_amount = int(payload.received_amount)
    expected_income.linked_transaction_id = linked_transaction_id
    db.commit()
    db.refresh(expected_income)
    return _get_expected_income_or_404(db, current_user.id, int(expected_income.id))


@router.delete("/expected-incomes/{expected_income_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_expected_income(
    expected_income_id: int,
    response: Response,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
):
    _apply_headers(response, enforce_budget_write_rate_limit(current_user.id))
    expected_income = _get_expected_income_or_404(db, current_user.id, expected_income_id)
    db.delete(expected_income)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/reallocate", response_model=list[schemas.BudgetOut])
def reallocate_budget(
    payload: schemas.BudgetReallocateRequest,
    response: Response,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
):
    _apply_headers(response, enforce_budget_write_rate_limit(current_user.id))
    if payload.from_category == payload.to_category:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="budgets.reallocate_same_category")

    from_budget = _get_budget_or_404(db, current_user.id, payload.budget_year, payload.budget_month, payload.from_category)
    to_budget = _get_budget_or_404(db, current_user.id, payload.budget_year, payload.budget_month, payload.to_category)
    from_computation = compute_budget_chain(db, current_user.id, [from_budget])[0]
    if from_computation.effective_available < payload.amount:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="budgets.reallocate_insufficient_remaining")

    from_budget.monthly_limit = int(from_budget.monthly_limit) - payload.amount
    to_budget.monthly_limit = int(to_budget.monthly_limit) + payload.amount
    recompute_budget_chain(db, current_user.id, from_budget.category)
    recompute_budget_chain(db, current_user.id, to_budget.category)
    db.commit()
    db.refresh(from_budget)
    db.refresh(to_budget)

    return [
        build_budget_out(compute_budget_chain(db, current_user.id, [from_budget])[0]),
        build_budget_out(compute_budget_chain(db, current_user.id, [to_budget])[0]),
    ]


@router.post("/recalculate", response_model=list[schemas.BudgetOut])
def recalculate_budget_chain(
    payload: schemas.BudgetRecalculateRequest,
    response: Response,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
):
    _apply_headers(response, enforce_budget_write_rate_limit(current_user.id))
    recompute_budget_chain(db, current_user.id, payload.category)
    db.commit()
    budgets = _budgets_for_category(db, current_user.id, payload.category)
    return [build_budget_out(item) for item in compute_budget_chain(db, current_user.id, budgets)]


@router.get("/{budget_id}/subcategories", response_model=list[schemas.BudgetSubcategoryOut])
def list_budget_subcategories(
    budget_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
):
    budget = (
        db.query(models.Budget)
        .filter(models.Budget.id == budget_id, models.Budget.owner_id == current_user.id)
        .first()
    )
    if not budget:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="budgets.not_found")
    return get_budget_detail(db, current_user.id, budget).subcategories


def _require_subcategory_in_budget_category(
    subcategory: models.UserSubcategory,
    budget: models.Budget,
) -> None:
    if subcategory.category != budget.category:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="budgets.subcategory_category_mismatch")


def _upsert_budget_subcategory_limit(
    db: Session,
    *,
    owner_id: int,
    budget_id: int,
    subcategory_id: int,
    monthly_limit: int,
) -> models.BudgetSubcategoryLimit:
    limit = get_budget_subcategory_limit(db, owner_id, budget_id, subcategory_id)
    if limit is None:
        limit = models.BudgetSubcategoryLimit(
            owner_id=owner_id,
            budget_id=budget_id,
            subcategory_id=subcategory_id,
            monthly_limit=int(monthly_limit),
        )
        db.add(limit)
    else:
        limit.monthly_limit = int(monthly_limit)
    return limit


@router.post("/{budget_id}/subcategories/reallocate", response_model=list[schemas.BudgetSubcategoryOut])
def reallocate_budget_subcategory(
    budget_id: int,
    payload: schemas.BudgetSubcategoryReallocateRequest,
    response: Response,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
):
    _apply_headers(response, enforce_budget_write_rate_limit(current_user.id))
    budget = _get_budget_by_id_or_404(db, current_user.id, budget_id)
    validate_active_expense_category(
        budget.category,
        error_detail="budgets.validation.real_expense_category_required",
    )

    to_subcategory = get_owned_subcategory_or_404(db, current_user.id, payload.to_subcategory_id)
    _require_subcategory_in_budget_category(to_subcategory, budget)
    if not to_subcategory.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="budgets.subcategory_inactive")

    amount = int(payload.amount)
    target_limit = get_budget_subcategory_limit(db, current_user.id, int(budget.id), int(to_subcategory.id))

    if payload.from_subcategory_id is None:
        current_total = sum(
            int(limit.monthly_limit)
            for limit in db.query(models.BudgetSubcategoryLimit)
            .filter(
                models.BudgetSubcategoryLimit.owner_id == current_user.id,
                models.BudgetSubcategoryLimit.budget_id == budget.id,
            )
            .all()
        )
        buffer_amount = int(budget.monthly_limit) - int(current_total)
        if buffer_amount < amount:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="budgets.subcategory_reallocate_insufficient_buffer",
            )
        _upsert_budget_subcategory_limit(
            db,
            owner_id=current_user.id,
            budget_id=int(budget.id),
            subcategory_id=int(to_subcategory.id),
            monthly_limit=(int(target_limit.monthly_limit) if target_limit is not None else 0) + amount,
        )
    else:
        if int(payload.from_subcategory_id) == int(payload.to_subcategory_id):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="budgets.subcategory_reallocate_same")
        from_subcategory = get_owned_subcategory_or_404(db, current_user.id, payload.from_subcategory_id)
        _require_subcategory_in_budget_category(from_subcategory, budget)
        source_limit = get_budget_subcategory_limit(db, current_user.id, int(budget.id), int(from_subcategory.id))
        if source_limit is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="budgets.subcategory_reallocate_insufficient_remaining",
            )
        spent_by_subcategory = get_subcategory_spent_for_month(
            db,
            current_user.id,
            budget.category,
            int(budget.budget_year),
            int(budget.budget_month),
        )
        source_remaining = int(source_limit.monthly_limit) - int(spent_by_subcategory.get(int(from_subcategory.id), 0))
        if source_remaining < amount:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="budgets.subcategory_reallocate_insufficient_remaining",
            )
        next_source_limit = int(source_limit.monthly_limit) - amount
        if next_source_limit <= 0:
            db.delete(source_limit)
        else:
            source_limit.monthly_limit = next_source_limit
        _upsert_budget_subcategory_limit(
            db,
            owner_id=current_user.id,
            budget_id=int(budget.id),
            subcategory_id=int(to_subcategory.id),
            monthly_limit=(int(target_limit.monthly_limit) if target_limit is not None else 0) + amount,
        )

    db.commit()
    db.refresh(budget)
    return get_budget_detail(db, current_user.id, budget).subcategories


@router.post("/{budget_id}/subcategories", response_model=schemas.BudgetSubcategoryOut, status_code=status.HTTP_201_CREATED)
def create_budget_subcategory(
    budget_id: int,
    payload: schemas.BudgetSubcategoryCreate,
    response: Response,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
):
    _apply_headers(response, enforce_budget_write_rate_limit(current_user.id))
    budget = (
        db.query(models.Budget)
        .filter(models.Budget.id == budget_id, models.Budget.owner_id == current_user.id)
        .first()
    )
    if not budget:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="budgets.not_found")
    validate_active_expense_category(
        budget.category,
        error_detail="budgets.validation.real_expense_category_required",
    )
    if payload.category != budget.category:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="budgets.subcategory_category_mismatch")

    validate_subcategory_total_limit(
        db=db,
        owner_id=current_user.id,
        budget=budget,
        incoming_limit=payload.monthly_limit,
    )

    subcategory = models.UserSubcategory(
        owner_id=current_user.id,
        category=payload.category,
        name=payload.name.strip(),
        is_active=payload.is_active,
    )
    db.add(subcategory)
    db.flush()
    if payload.monthly_limit is not None:
        db.add(
            models.BudgetSubcategoryLimit(
                owner_id=current_user.id,
                budget_id=budget.id,
                subcategory_id=subcategory.id,
                monthly_limit=int(payload.monthly_limit),
            )
        )
    db.commit()
    db.refresh(subcategory)
    return build_budget_subcategory_out(subcategory, payload.monthly_limit)


@router.patch("/subcategories/{subcategory_id}", response_model=schemas.BudgetSubcategoryOut)
def update_budget_subcategory(
    subcategory_id: int,
    payload: schemas.BudgetSubcategoryUpdate,
    response: Response,
    budget_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
):
    _apply_headers(response, enforce_budget_write_rate_limit(current_user.id))
    subcategory = get_owned_subcategory_or_404(db, current_user.id, subcategory_id)
    if budget_id is not None:
        budget = _get_budget_by_id_or_404(db, current_user.id, budget_id)
        _require_subcategory_in_budget_category(subcategory, budget)
    else:
        budget = (
            db.query(models.Budget)
            .filter(
                models.Budget.owner_id == current_user.id,
                models.Budget.category == subcategory.category,
            )
            .order_by(models.Budget.budget_year.desc(), models.Budget.budget_month.desc())
            .first()
        )
    if not budget:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="budgets.parent_budget_required")

    update_data = payload.model_dump(exclude_unset=True)
    if "monthly_limit" in update_data:
        validate_subcategory_total_limit(
            db=db,
            owner_id=current_user.id,
            budget=budget,
            incoming_limit=update_data["monthly_limit"],
            exclude_subcategory_id=subcategory.id,
        )

    for field, value in update_data.items():
        if field == "monthly_limit":
            continue
        setattr(subcategory, field, value.strip() if field == "name" and value is not None else value)
    if "monthly_limit" in update_data:
        limit = get_budget_subcategory_limit(db, current_user.id, int(budget.id), int(subcategory.id))
        next_limit = update_data["monthly_limit"]
        if next_limit is None:
            if limit is not None:
                db.delete(limit)
        elif limit is None:
            db.add(
                models.BudgetSubcategoryLimit(
                    owner_id=current_user.id,
                    budget_id=budget.id,
                    subcategory_id=subcategory.id,
                    monthly_limit=int(next_limit),
                )
            )
        else:
            limit.monthly_limit = int(next_limit)
    db.commit()
    db.refresh(subcategory)
    limit = get_budget_subcategory_limit(db, current_user.id, int(budget.id), int(subcategory.id))
    return build_budget_subcategory_out(
        subcategory,
        int(limit.monthly_limit) if limit is not None else None,
    )


@router.delete("/subcategories/{subcategory_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_budget_subcategory(
    subcategory_id: int,
    response: Response,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
):
    _apply_headers(response, enforce_budget_write_rate_limit(current_user.id))
    subcategory = get_owned_subcategory_or_404(db, current_user.id, subcategory_id)
    has_linked_entries = (
        db.query(models.EntityLedger.id)
        .filter(models.EntityLedger.subcategory_id == subcategory.id)
        .first()
    )
    if has_linked_entries:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="budgets.subcategory_has_linked_expenses")
    db.delete(subcategory)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
