from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date

from fastapi import HTTPException, status
# pyrefly: ignore [missing-import]
from sqlalchemy import and_, case, func, or_, select
# pyrefly: ignore [missing-import]
from sqlalchemy.orm import Session

from .. import models, schemas
from .goal_funding_service import get_wallet_goal_allocated_amount
from .borrowing_survival_service import get_or_build_summary as get_borrowing_survival_summary
from .category_floor_service import CategoryFloorWarning, build_category_floor_warnings
from .obligation_source_service import (
    exclude_legacy_payment_plan_debt_duplicate_filter,
    regular_debt_obligation_filters,
)
from .project_service import (
    OVERLAY_RESERVATION_HOLDING_STATUSES,
    get_project_funding_limit,
    get_project_target_estimate,
    get_project_type,
    get_project_wallet_allocated_amount,
    is_isolated_project,
    project_wallet_allocations_out,
)
from .wallet_value_service import owned_balance

BUDGET_MATERIALIZE_MIN_YEAR = 2020


@dataclass
class BudgetComputation:
    budget: models.Budget
    spent: int
    cash_spent: int
    cap_trim_amount: int
    reallocated_in: int
    reallocated_out: int
    effective_monthly_limit: int
    remaining: int
    effective_available: int
    is_over_limit: bool
    project_reserved_amount: int = 0
    project_spent_amount: int = 0
    free_general_limit: int = 0
    free_general_remaining: int = 0


@dataclass
class BudgetPlanBacking:
    owned_money_now: int
    protected_goal_money: int
    free_money_now: int
    expected_income_remaining: int
    backing_total: int


@dataclass
class BudgetPlanCapacity:
    owned_money_now: int
    protected_goal_money: int
    free_money_now: int
    expected_income_remaining: int
    cash_obligation_reserve_total: int
    valid_budget_spent: int
    cash_backing_total: int
    backing_total: int


def month_bounds(year: int, month: int) -> tuple[date, date]:
    start = date(year, month, 1)
    if month == 12:
        end = date(year + 1, 1, 1)
    else:
        end = date(year, month + 1, 1)
    return start, end


def add_month(year: int, month: int) -> tuple[int, int]:
    if month == 12:
        return year + 1, 1
    return year, month + 1


def previous_month(year: int, month: int) -> tuple[int, int]:
    if month == 1:
        return year - 1, 12
    return year, month - 1


def _isolated_project_spend_filter():
    return (
        (models.EntityLedger.project_id.is_(None))
        | (models.Project.project_type == models.ProjectType.OVERLAY)
        | (models.Project.id.is_(None))
    )


def _normal_monthly_budget_impact_filter():
    return or_(
        models.FinancialEvent.reference_type.is_(None),
        models.FinancialEvent.reference_type.notin_(
            [
                models.ReferenceType.GOAL_PLANNED_PURCHASE,
                models.ReferenceType.GOAL_ACHIEVED_OUTSIDE_FUNDS,
            ]
        ),
    )


def normal_monthly_budget_impact_filters():
    return (
        _isolated_project_spend_filter(),
        _normal_monthly_budget_impact_filter(),
        exclude_legacy_payment_plan_debt_duplicate_filter(),
    )


def _signed_expense_amount():
    return case(
        (
            and_(
                models.FinancialEvent.status == models.FinancialEventStatus.POSTED,
                models.FinancialEvent.event_type == models.TransactionType.EXPENSE,
            ),
            models.EntityLedger.amount,
        ),
        (
            and_(
                models.FinancialEvent.status == models.FinancialEventStatus.POSTED,
                models.FinancialEvent.event_type == models.TransactionType.REFUND,
            ),
            -models.EntityLedger.amount,
        ),
        else_=0,
    )


def get_budget_spent_amount(
    db: Session,
    owner_id: int,
    *,
    budget_id: int | None = None,
    category: models.ExpenseCategory | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    subcategory_id: int | None = None,
    exclude_event_id: int | None = None,
) -> int:
    signed_amount = _signed_expense_amount()
    query = (
        db.query(func.coalesce(func.sum(signed_amount), 0))
        .select_from(models.EntityLedger)
        .join(models.FinancialEvent, models.FinancialEvent.id == models.EntityLedger.event_id)
        .outerjoin(models.Project, models.Project.id == models.EntityLedger.project_id)
        .filter(
            models.FinancialEvent.owner_id == owner_id,
            models.FinancialEvent.status == models.FinancialEventStatus.POSTED,
            models.FinancialEvent.event_type.in_(
                [models.TransactionType.EXPENSE, models.TransactionType.REFUND]
            ),
            *normal_monthly_budget_impact_filters(),
        )
    )
    if budget_id is not None:
        query = query.filter(models.EntityLedger.budget_id == budget_id)
    if category is not None:
        query = query.filter(models.EntityLedger.category == category)
    if start_date is not None:
        query = query.filter(models.FinancialEvent.date >= start_date)
    if end_date is not None:
        query = query.filter(models.FinancialEvent.date < end_date)
    if subcategory_id is not None:
        query = query.filter(models.EntityLedger.subcategory_id == subcategory_id)
    if exclude_event_id is not None:
        query = query.filter(models.FinancialEvent.id != exclude_event_id)
    return int(query.scalar() or 0)


def get_budgeted_wallet_borrowing_pressure(
    db: Session,
    owner_id: int,
    *,
    start_date: date,
    end_date: date,
) -> bool:
    borrowed_leg = (
        db.query(models.WalletLedger.id)
        .join(models.FinancialEvent, models.FinancialEvent.id == models.WalletLedger.event_id)
        .join(models.Wallet, models.Wallet.id == models.WalletLedger.wallet_id)
        .join(models.EntityLedger, models.EntityLedger.event_id == models.FinancialEvent.id)
        .outerjoin(models.Project, models.Project.id == models.EntityLedger.project_id)
        .filter(
            models.FinancialEvent.owner_id == owner_id,
            models.FinancialEvent.status == models.FinancialEventStatus.POSTED,
            models.FinancialEvent.event_type == models.TransactionType.EXPENSE,
            models.FinancialEvent.date >= start_date,
            models.FinancialEvent.date < end_date,
            models.EntityLedger.budget_id.isnot(None),
            models.WalletLedger.amount < 0,
            or_(
                models.Wallet.wallet_type == models.WalletType.CREDIT,
                models.Wallet.accounting_type == models.AccountingType.LIABILITY,
                and_(
                    models.Wallet.has_overdraft == True,  # noqa: E712
                    models.Wallet.current_balance < 0,
                ),
            ),
            *normal_monthly_budget_impact_filters(),
        )
        .first()
    )
    return borrowed_leg is not None


def get_free_money_now(db: Session, owner_id: int) -> tuple[int, int, int]:
    wallets = (
        db.query(models.Wallet)
        .filter(
            models.Wallet.owner_id == owner_id,
            models.Wallet.is_active == True,  # noqa: E712
        )
        .all()
    )
    owned_money_now = sum(owned_balance(wallet) for wallet in wallets)
    protected_goal_money = sum(
        min(
            get_wallet_goal_allocated_amount(db, owner_id, int(wallet.id)),
            owned_balance(wallet),
        )
        for wallet in wallets
    )
    project_wallet_money = (
        db.query(
            models.ProjectWalletAllocation.wallet_id,
            func.coalesce(func.sum(models.ProjectWalletAllocation.amount), 0),
        )
        .join(models.Project, models.Project.id == models.ProjectWalletAllocation.project_id)
        .filter(
            models.ProjectWalletAllocation.owner_id == owner_id,
            models.Project.status.in_(
                [models.ProjectStatus.ACTIVE, models.ProjectStatus.STOPPED]
            ),
        )
        .group_by(models.ProjectWalletAllocation.wallet_id)
        .all()
    )
    owned_by_wallet = {int(wallet.id): owned_balance(wallet) for wallet in wallets}
    goal_by_wallet = {
        int(wallet.id): min(
            get_wallet_goal_allocated_amount(db, owner_id, int(wallet.id)),
            owned_by_wallet[int(wallet.id)],
        )
        for wallet in wallets
    }
    protected_project_money = sum(
        min(
            int(amount or 0),
            max(owned_by_wallet.get(int(wallet_id), 0) - goal_by_wallet.get(int(wallet_id), 0), 0),
        )
        for wallet_id, amount in project_wallet_money
    )
    free_money_now = max(
        int(owned_money_now) - int(protected_goal_money) - int(protected_project_money),
        0,
    )
    return int(owned_money_now), int(protected_goal_money), int(free_money_now)


def get_expected_income_remaining(
    db: Session,
    owner_id: int,
    budget_year: int,
    budget_month: int,
) -> int:
    from . import expected_inflow_service

    rows = expected_inflow_service.inflow_query(db).filter(
        models.ExpectedIncome.owner_id == owner_id,
        models.ExpectedIncome.budget_year == budget_year,
        models.ExpectedIncome.budget_month == budget_month,
    ).all()
    return int(sum(expected_inflow_service.active_backing_amount(row) for row in rows))


def get_expected_income_lifecycle_summary(
    db: Session,
    owner_id: int,
    budget_year: int,
    budget_month: int,
) -> tuple[list[schemas.ExpectedIncomeLifecycleTotalOut], list[schemas.ExpectedIncomeOut]]:
    from . import expected_inflow_service

    rows = (
        expected_inflow_service.inflow_query(db)
        .filter(
            models.ExpectedIncome.owner_id == owner_id,
            models.ExpectedIncome.budget_year == budget_year,
            models.ExpectedIncome.budget_month == budget_month,
        )
        .order_by(models.ExpectedIncome.due_date.asc(), models.ExpectedIncome.id.asc())
        .all()
    )
    totals_by_status: dict[models.ExpectedIncomeStatus, dict[str, int]] = {
        status: {"count": 0, "amount": 0, "received_amount": 0}
        for status in models.ExpectedIncomeStatus
    }
    for row in rows:
        bucket = totals_by_status[row.status]
        bucket["count"] += 1
        bucket["amount"] += int(row.amount or 0)
        bucket["received_amount"] += expected_inflow_service.received_amount(row)

    return (
        [
            schemas.ExpectedIncomeLifecycleTotalOut(
                status=status,
                count=values["count"],
                amount=values["amount"],
                received_amount=values["received_amount"],
            )
            for status, values in totals_by_status.items()
        ],
        [schemas.ExpectedIncomeOut.model_validate(row) for row in rows],
    )


def get_budget_plan_backing(
    db: Session,
    owner_id: int,
    budget_year: int,
    budget_month: int,
) -> BudgetPlanBacking:
    owned_money_now, protected_goal_money, free_money_now = get_free_money_now(db, owner_id)
    expected_income_remaining = get_expected_income_remaining(db, owner_id, budget_year, budget_month)
    return BudgetPlanBacking(
        owned_money_now=owned_money_now,
        protected_goal_money=protected_goal_money,
        free_money_now=free_money_now,
        expected_income_remaining=expected_income_remaining,
        backing_total=int(free_money_now) + int(expected_income_remaining),
    )


def get_cash_obligation_reserve_total(
    db: Session,
    owner_id: int,
    budget_year: int,
    budget_month: int,
) -> int:
    start, end = month_bounds(budget_year, budget_month)
    formal_due_debt_ids = select(models.DebtFormalDetails.debt_id).filter(
        models.DebtFormalDetails.owner_id == owner_id,
        models.DebtFormalDetails.next_due_date >= start,
        models.DebtFormalDetails.next_due_date < end,
    )
    total = (
        db.query(func.coalesce(func.sum(models.Debt.remaining_amount), 0))
        .filter(
            models.Debt.owner_id == owner_id,
            models.Debt.debt_type == models.DebtType.OWING,
            *regular_debt_obligation_filters(owner_id),
            models.Debt.expense_category.is_(None),
            or_(
                and_(models.Debt.expected_return_date >= start, models.Debt.expected_return_date < end),
                models.Debt.id.in_(formal_due_debt_ids),
            ),
        )
        .scalar()
    )
    return int(total or 0)


def get_budget_category_floors(
    db: Session,
    owner_id: int,
    budget_year: int,
    budget_month: int,
    computed: list[BudgetComputation] | None = None,
) -> list[CategoryFloorWarning]:
    start, end = month_bounds(budget_year, budget_month)
    if computed is None:
        computed = get_budget_month_computations(db, owner_id, budget_year, budget_month)
    effective_limit_by_category: dict[models.ExpenseCategory, int] = {}
    for item in computed:
        effective_limit_by_category[item.budget.category] = (
            effective_limit_by_category.get(item.budget.category, 0)
            + int(item.effective_monthly_limit or 0)
        )

    return build_category_floor_warnings(
        db,
        owner_id,
        start=start,
        end=end,
        effective_limits=effective_limit_by_category,
    )


def _enum_value(value) -> str:
    return value.value if hasattr(value, "value") else str(value)


def get_budget_spent_by_id(db: Session, owner_id: int) -> dict[int, int]:
    signed_amount = _signed_expense_amount()
    rows = (
        db.query(
            models.EntityLedger.budget_id,
            func.coalesce(func.sum(signed_amount), 0).label("spent"),
        )
        .join(models.FinancialEvent, models.FinancialEvent.id == models.EntityLedger.event_id)
        .outerjoin(models.Project, models.Project.id == models.EntityLedger.project_id)
        .filter(
            models.FinancialEvent.owner_id == owner_id,
            models.FinancialEvent.status == models.FinancialEventStatus.POSTED,
            models.EntityLedger.budget_id.isnot(None),
            models.FinancialEvent.event_type.in_(
                [models.TransactionType.EXPENSE, models.TransactionType.REFUND]
            ),
            *normal_monthly_budget_impact_filters(),
        )
        .group_by(models.EntityLedger.budget_id)
        .all()
    )
    return {int(row.budget_id): int(row.spent or 0) for row in rows if row.budget_id is not None}


def get_cash_backed_budget_spent_by_id(db: Session, owner_id: int) -> dict[int, int]:
    signed_amount = _signed_expense_amount()
    entity_rows = (
        db.query(
            models.EntityLedger.event_id,
            models.EntityLedger.budget_id,
            func.coalesce(func.sum(signed_amount), 0).label("spent"),
        )
        .join(models.FinancialEvent, models.FinancialEvent.id == models.EntityLedger.event_id)
        .outerjoin(models.Project, models.Project.id == models.EntityLedger.project_id)
        .filter(
            models.FinancialEvent.owner_id == owner_id,
            models.FinancialEvent.status == models.FinancialEventStatus.POSTED,
            models.EntityLedger.budget_id.isnot(None),
            models.FinancialEvent.event_type.in_(
                [models.TransactionType.EXPENSE, models.TransactionType.REFUND]
            ),
            *normal_monthly_budget_impact_filters(),
        )
        .group_by(models.EntityLedger.event_id, models.EntityLedger.budget_id)
        .all()
    )
    if not entity_rows:
        return {}

    wallet_rows = (
        db.query(
            models.WalletLedger.event_id,
            func.coalesce(func.sum(func.abs(models.WalletLedger.amount)), 0).label("event_total"),
            func.coalesce(
                func.sum(
                    case(
                        (
                            models.WalletLedger.owned_spend_amount.isnot(None),
                            models.WalletLedger.owned_spend_amount,
                        ),
                        (
                            and_(
                                models.Wallet.accounting_type == models.AccountingType.ASSET,
                                models.Wallet.wallet_type != models.WalletType.CREDIT,
                            ),
                            func.abs(models.WalletLedger.amount),
                        ),
                        else_=0,
                    )
                ),
                0,
            ).label("cash_total"),
        )
        .join(models.FinancialEvent, models.FinancialEvent.id == models.WalletLedger.event_id)
        .join(models.Wallet, models.Wallet.id == models.WalletLedger.wallet_id)
        .filter(
            models.FinancialEvent.owner_id == owner_id,
            models.FinancialEvent.status == models.FinancialEventStatus.POSTED,
            models.FinancialEvent.event_type.in_(
                [models.TransactionType.EXPENSE, models.TransactionType.REFUND]
            ),
        )
        .group_by(models.WalletLedger.event_id)
        .all()
    )
    wallet_totals_by_event = {
        int(row.event_id): (int(row.event_total or 0), int(row.cash_total or 0))
        for row in wallet_rows
        if row.event_id is not None
    }

    legs_by_event: dict[int, list[tuple[int, int]]] = defaultdict(list)
    for row in entity_rows:
        if row.budget_id is not None and row.event_id is not None:
            legs_by_event[int(row.event_id)].append((int(row.budget_id), int(row.spent or 0)))

    cash_spent_by_budget: dict[int, int] = {}
    for event_id, legs in legs_by_event.items():
        event_total, cash_total = wallet_totals_by_event.get(event_id, (0, 0))
        if event_total <= 0 or cash_total <= 0:
            continue
            
        allocations = []
        total_exact = 0.0
        total_base = 0
        for budget_id, spent in legs:
            exact = (spent * cash_total) / event_total
            base = int(exact)
            remainder = exact - base
            allocations.append({"budget_id": budget_id, "base": base, "remainder": remainder})
            total_exact += exact
            total_base += base
            
        unallocated_cash = int(total_exact + 0.5) - total_base
        
        allocations.sort(key=lambda x: x["remainder"], reverse=True)
        
        for i in range(unallocated_cash):
            if i < len(allocations):
                allocations[i]["base"] += 1
                
        for alloc in allocations:
            cash_spent_by_budget[alloc["budget_id"]] = (
                cash_spent_by_budget.get(alloc["budget_id"], 0) + alloc["base"]
            )
            
    return cash_spent_by_budget


def get_budget_ledger_effects(
    db: Session,
    owner_id: int,
) -> dict[tuple[str, int, int], dict[str, int]]:
    rows = (
        db.query(models.BudgetLedger)
        .filter(models.BudgetLedger.owner_id == owner_id)
        .all()
    )
    effects: dict[tuple[str, int, int], dict[str, int]] = {}
    for row in rows:
        key = (_enum_value(row.category), int(row.budget_year), int(row.budget_month))
        bucket = effects.setdefault(
            key,
            {
                "CAP_TRIM": 0,
            },
        )
        entry_type = _enum_value(row.entry_type)
        if entry_type != "CAP_TRIM":
            continue
        bucket[entry_type] = int(row.amount or 0)
    return effects


def get_overlay_project_reservation_rows(
    db: Session,
    owner_id: int,
    budget_year: int,
    budget_month: int,
    category: models.ExpenseCategory | None = None,
) -> list[models.ProjectCategoryMonthlyLimit]:
    query = (
        db.query(models.ProjectCategoryMonthlyLimit)
        .join(models.Project, models.Project.id == models.ProjectCategoryMonthlyLimit.project_id)
        .filter(
            models.Project.owner_id == owner_id,
            models.Project.project_type == models.ProjectType.OVERLAY,
            models.Project.status.in_(OVERLAY_RESERVATION_HOLDING_STATUSES),
            models.ProjectCategoryMonthlyLimit.budget_year == budget_year,
            models.ProjectCategoryMonthlyLimit.budget_month == budget_month,
        )
    )
    if category is not None:
        query = query.filter(models.ProjectCategoryMonthlyLimit.category == category)
    return (
        query.order_by(
            models.ProjectCategoryMonthlyLimit.category.asc(),
            models.Project.title.asc(),
            models.ProjectCategoryMonthlyLimit.id.asc(),
        )
        .all()
    )


def get_overlay_project_reservation_totals(
    db: Session,
    owner_id: int,
    budget_year: int,
    budget_month: int,
) -> dict[models.ExpenseCategory, int]:
    rows = (
        db.query(
            models.ProjectCategoryMonthlyLimit.category,
            func.coalesce(func.sum(models.ProjectCategoryMonthlyLimit.limit_amount), 0).label("reserved"),
        )
        .join(models.Project, models.Project.id == models.ProjectCategoryMonthlyLimit.project_id)
        .filter(
            models.Project.owner_id == owner_id,
            models.Project.project_type == models.ProjectType.OVERLAY,
            models.Project.status.in_(OVERLAY_RESERVATION_HOLDING_STATUSES),
            models.ProjectCategoryMonthlyLimit.budget_year == budget_year,
            models.ProjectCategoryMonthlyLimit.budget_month == budget_month,
        )
        .group_by(models.ProjectCategoryMonthlyLimit.category)
        .all()
    )
    return {category: int(reserved or 0) for category, reserved in rows if category is not None}


def get_overlay_project_spent_totals(
    db: Session,
    owner_id: int,
    budget_year: int,
    budget_month: int,
) -> dict[models.ExpenseCategory, int]:
    start, end = month_bounds(budget_year, budget_month)
    signed_amount = _signed_expense_amount()
    rows = (
        db.query(
            models.EntityLedger.category,
            func.coalesce(func.sum(signed_amount), 0).label("spent"),
        )
        .select_from(models.EntityLedger)
        .join(models.FinancialEvent, models.FinancialEvent.id == models.EntityLedger.event_id)
        .join(models.Project, models.Project.id == models.EntityLedger.project_id)
        .filter(
            models.FinancialEvent.owner_id == owner_id,
            models.FinancialEvent.status == models.FinancialEventStatus.POSTED,
            models.FinancialEvent.event_type.in_(
                [models.TransactionType.EXPENSE, models.TransactionType.REFUND]
            ),
            models.FinancialEvent.date >= start,
            models.FinancialEvent.date < end,
            models.Project.project_type == models.ProjectType.OVERLAY,
            models.EntityLedger.category.isnot(None),
        )
        .group_by(models.EntityLedger.category)
        .all()
    )
    return {category: int(spent or 0) for category, spent in rows if category is not None}


def get_overlay_project_spent_by_project_category(
    db: Session,
    owner_id: int,
    budget_year: int,
    budget_month: int,
) -> dict[tuple[int, models.ExpenseCategory], int]:
    start, end = month_bounds(budget_year, budget_month)
    signed_amount = _signed_expense_amount()
    rows = (
        db.query(
            models.EntityLedger.project_id,
            models.EntityLedger.category,
            func.coalesce(func.sum(signed_amount), 0).label("spent"),
        )
        .select_from(models.EntityLedger)
        .join(models.FinancialEvent, models.FinancialEvent.id == models.EntityLedger.event_id)
        .join(models.Project, models.Project.id == models.EntityLedger.project_id)
        .filter(
            models.FinancialEvent.owner_id == owner_id,
            models.FinancialEvent.status == models.FinancialEventStatus.POSTED,
            models.FinancialEvent.event_type.in_(
                [models.TransactionType.EXPENSE, models.TransactionType.REFUND]
            ),
            models.FinancialEvent.date >= start,
            models.FinancialEvent.date < end,
            models.Project.project_type == models.ProjectType.OVERLAY,
            models.EntityLedger.project_id.isnot(None),
            models.EntityLedger.category.isnot(None),
        )
        .group_by(models.EntityLedger.project_id, models.EntityLedger.category)
        .all()
    )
    return {
        (int(project_id), category): int(spent or 0)
        for project_id, category, spent in rows
        if project_id is not None and category is not None
    }


def get_overlay_project_spent_by_project_subcategory(
    db: Session,
    owner_id: int,
    budget_year: int,
    budget_month: int,
) -> dict[tuple[int, int], int]:
    start, end = month_bounds(budget_year, budget_month)
    signed_amount = _signed_expense_amount()
    rows = (
        db.query(
            models.EntityLedger.project_id,
            models.EntityLedger.subcategory_id,
            func.coalesce(func.sum(signed_amount), 0).label("spent"),
        )
        .select_from(models.EntityLedger)
        .join(models.FinancialEvent, models.FinancialEvent.id == models.EntityLedger.event_id)
        .join(models.Project, models.Project.id == models.EntityLedger.project_id)
        .filter(
            models.FinancialEvent.owner_id == owner_id,
            models.FinancialEvent.status == models.FinancialEventStatus.POSTED,
            models.FinancialEvent.event_type.in_(
                [models.TransactionType.EXPENSE, models.TransactionType.REFUND]
            ),
            models.FinancialEvent.date >= start,
            models.FinancialEvent.date < end,
            models.Project.project_type == models.ProjectType.OVERLAY,
            models.EntityLedger.project_id.isnot(None),
            models.EntityLedger.subcategory_id.isnot(None),
        )
        .group_by(models.EntityLedger.project_id, models.EntityLedger.subcategory_id)
        .all()
    )
    return {
        (int(project_id), int(subcategory_id)): int(spent or 0)
        for project_id, subcategory_id, spent in rows
        if project_id is not None and subcategory_id is not None
    }


def compute_budget_chain(
    db: Session,
    owner_id: int,
    budgets: list[models.Budget],
) -> list[BudgetComputation]:
    if not budgets:
        return []

    spent_by_budget_id = get_budget_spent_by_id(db, owner_id)
    cash_spent_by_budget_id = get_cash_backed_budget_spent_by_id(db, owner_id)
    effects_by_key = get_budget_ledger_effects(db, owner_id)
    month_keys = {(int(budget.budget_year), int(budget.budget_month)) for budget in budgets}
    reservation_totals_by_month = {
        month_key: get_overlay_project_reservation_totals(db, owner_id, *month_key)
        for month_key in month_keys
    }
    project_spent_totals_by_month = {
        month_key: get_overlay_project_spent_totals(db, owner_id, *month_key)
        for month_key in month_keys
    }
    computations: list[BudgetComputation] = []

    for budget in budgets:
        key = (_enum_value(budget.category), int(budget.budget_year), int(budget.budget_month))
        effects = effects_by_key.get(key, {})
        cap_trim_amount = int(abs(effects.get("CAP_TRIM", 0)))
        spent = int(spent_by_budget_id.get(int(budget.id), 0))
        cash_spent = int(cash_spent_by_budget_id.get(int(budget.id), 0))
        effective_limit = int(budget.monthly_limit or 0) - cap_trim_amount
        remaining = effective_limit - spent
        month_key = (int(budget.budget_year), int(budget.budget_month))
        project_reserved = int(reservation_totals_by_month.get(month_key, {}).get(budget.category, 0))
        project_spent = int(project_spent_totals_by_month.get(month_key, {}).get(budget.category, 0))
        general_spent = max(spent - project_spent, 0)
        project_overspend = max(project_spent - project_reserved, 0)
        free_general_limit = max(effective_limit - project_reserved, 0)
        free_general_remaining = free_general_limit - general_spent - project_overspend
        computations.append(
            BudgetComputation(
                budget=budget,
                spent=spent,
                cash_spent=cash_spent,
                cap_trim_amount=cap_trim_amount,
                reallocated_in=0,
                reallocated_out=0,
                effective_monthly_limit=effective_limit,
                remaining=remaining,
                effective_available=max(remaining, 0),
                is_over_limit=remaining < 0,
                project_reserved_amount=project_reserved,
                project_spent_amount=project_spent,
                free_general_limit=free_general_limit,
                free_general_remaining=free_general_remaining,
            )
        )
    return computations


def get_budget_month_computations(
    db: Session,
    owner_id: int,
    budget_year: int,
    budget_month: int,
) -> list[BudgetComputation]:
    budgets = (
        db.query(models.Budget)
        .filter(
            models.Budget.owner_id == owner_id,
            models.Budget.budget_year == budget_year,
            models.Budget.budget_month == budget_month,
        )
        .order_by(models.Budget.category.asc())
        .all()
    )

    grouped: dict[models.ExpenseCategory, list[models.Budget]] = {}
    for budget in budgets:
        grouped.setdefault(budget.category, []).append(budget)

    computed: list[BudgetComputation] = []
    for items in grouped.values():
        computed.extend(compute_budget_chain(db, owner_id, items))
    return computed


def get_budget_plan_status(
    monthly_effective_limit_total: int,
    cash_backing_total: int,
    expected_income_remaining: int,
) -> schemas.BudgetPlanStatus:
    if monthly_effective_limit_total < cash_backing_total:
        return schemas.BudgetPlanStatus.COVERED_WITH_CUSHION
    if monthly_effective_limit_total == cash_backing_total:
        return schemas.BudgetPlanStatus.COVERED_NO_CUSHION
    if monthly_effective_limit_total <= int(cash_backing_total) + int(expected_income_remaining):
        return schemas.BudgetPlanStatus.WAITING_ON_INCOME
    return schemas.BudgetPlanStatus.OVER_PLANNED


def get_total_valid_budget_spent(computed: list[BudgetComputation]) -> int:
    return sum(
        min(
            max(int(item.cash_spent or 0), 0),
            max(int(item.effective_monthly_limit or 0), 0),
        )
        for item in computed
    )


def get_budget_plan_capacity(
    db: Session,
    owner_id: int,
    budget_year: int,
    budget_month: int,
    computed: list[BudgetComputation] | None = None,
) -> BudgetPlanCapacity:
    backing = get_budget_plan_backing(db, owner_id, budget_year, budget_month)
    if computed is None:
        computed = get_budget_month_computations(db, owner_id, budget_year, budget_month)
    valid_budget_spent = get_total_valid_budget_spent(computed)
    cash_obligation_reserve_total = get_cash_obligation_reserve_total(db, owner_id, budget_year, budget_month)
    cash_backing_total = int(backing.free_money_now) + int(valid_budget_spent) - int(cash_obligation_reserve_total)
    return BudgetPlanCapacity(
        owned_money_now=backing.owned_money_now,
        protected_goal_money=backing.protected_goal_money,
        free_money_now=backing.free_money_now,
        expected_income_remaining=backing.expected_income_remaining,
        cash_obligation_reserve_total=cash_obligation_reserve_total,
        valid_budget_spent=valid_budget_spent,
        cash_backing_total=cash_backing_total,
        backing_total=int(cash_backing_total) + int(backing.expected_income_remaining),
    )


def validate_budget_plan_capacity(
    db: Session,
    owner_id: int,
    budget_year: int,
    budget_month: int,
) -> None:
    computed = get_budget_month_computations(db, owner_id, budget_year, budget_month)
    attempted_total = sum(int(item.effective_monthly_limit or 0) for item in computed)
    capacity = get_budget_plan_capacity(db, owner_id, budget_year, budget_month, computed)
    if attempted_total <= capacity.backing_total:
        return

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail={
            "code": "budgets.plan_exceeds_backing",
            "attempted_total": attempted_total,
            "backing_total": capacity.backing_total,
            "shortfall": attempted_total - capacity.backing_total,
            "free_money_now": capacity.free_money_now,
            "expected_income_remaining": capacity.expected_income_remaining,
            "cash_obligation_reserve_total": capacity.cash_obligation_reserve_total,
            "valid_budget_spent": capacity.valid_budget_spent,
        },
    )


def recompute_budget_chain(
    db: Session,
    owner_id: int,
    category: models.ExpenseCategory,
) -> None:
    budgets = (
        db.query(models.Budget)
        .filter(
            models.Budget.owner_id == owner_id,
            models.Budget.category == category,
        )
        .order_by(models.Budget.budget_year.asc(), models.Budget.budget_month.asc())
        .all()
    )
    if not budgets:
        return

    db.query(models.BudgetLedger).filter(
        models.BudgetLedger.owner_id == owner_id,
        models.BudgetLedger.category == category,
    ).delete(synchronize_session=False)
    db.flush()

    # Unused room returns to unallocated capacity until the user explicitly
    # plans the new month.
    return


def materialize_budget_for_month(
    db: Session,
    owner_id: int,
    category: models.ExpenseCategory,
    budget_year: int,
    budget_month: int,
) -> models.Budget | None:
    if budget_year < BUDGET_MATERIALIZE_MIN_YEAR:
        return None

    existing = (
        db.query(models.Budget)
        .filter(
            models.Budget.owner_id == owner_id,
            models.Budget.category == category,
            models.Budget.budget_year == budget_year,
            models.Budget.budget_month == budget_month,
        )
        .with_for_update()
        .first()
    )
    if existing:
        return existing

    prev_year, prev_month = previous_month(budget_year, budget_month)
    source = (
        db.query(models.Budget)
        .filter(
            models.Budget.owner_id == owner_id,
            models.Budget.category == category,
            models.Budget.budget_year == prev_year,
            models.Budget.budget_month == prev_month,
        )
        .first()
    )
    if not source:
        source = materialize_budget_for_month(db, owner_id, category, prev_year, prev_month)
        if not source:
            return None

    new_budget = models.Budget(
        owner_id=owner_id,
        category=category,
        budget_year=budget_year,
        budget_month=budget_month,
        monthly_limit=int(source.monthly_limit),
        auto_created=True,
        max_envelope_balance=source.max_envelope_balance,
    )
    db.add(new_budget)
    db.flush()
    source_limits = (
        db.query(models.BudgetSubcategoryLimit)
        .filter(models.BudgetSubcategoryLimit.budget_id == source.id)
        .all()
    )
    for source_limit in source_limits:
        db.add(
            models.BudgetSubcategoryLimit(
                owner_id=owner_id,
                budget_id=new_budget.id,
                subcategory_id=source_limit.subcategory_id,
                monthly_limit=int(source_limit.monthly_limit),
            )
        )
    recompute_budget_chain(db, owner_id, category)
    db.flush()
    validate_budget_plan_capacity(db, owner_id, budget_year, budget_month)
    return new_budget


def build_budget_out(computation: BudgetComputation) -> schemas.BudgetOut:
    budget_out = schemas.BudgetOut.model_validate(computation.budget)
    budget_out.spent = computation.spent
    budget_out.cap_trim_amount = computation.cap_trim_amount
    budget_out.reallocated_in = computation.reallocated_in
    budget_out.reallocated_out = computation.reallocated_out
    budget_out.effective_monthly_limit = computation.effective_monthly_limit
    budget_out.remaining = computation.remaining
    budget_out.effective_available = computation.effective_available
    budget_out.is_over_limit = computation.is_over_limit
    budget_out.project_reserved_amount = computation.project_reserved_amount
    budget_out.project_spent_amount = computation.project_spent_amount
    budget_out.free_general_limit = computation.free_general_limit
    budget_out.free_general_remaining = computation.free_general_remaining
    return budget_out


def build_budget_month_summary(
    db: Session,
    owner_id: int,
    budget_year: int,
    budget_month: int,
) -> schemas.BudgetMonthSummaryOut:
    start, end = month_bounds(budget_year, budget_month)
    computed = get_budget_month_computations(db, owner_id, budget_year, budget_month)

    monthly_budget_limit_total = sum(int(item.budget.monthly_limit or 0) for item in computed)
    monthly_effective_limit_total = sum(int(item.effective_monthly_limit or 0) for item in computed)
    normal_budget_spent = sum(int(item.spent or 0) for item in computed)
    normal_budget_remaining = sum(max(int(item.remaining or 0), 0) for item in computed)
    categories_over_limit = sum(1 for item in computed if item.is_over_limit)
    categories_close_to_limit = sum(
        1
        for item in computed
        if not item.is_over_limit
        and int(item.effective_monthly_limit or 0) > 0
        and (int(item.spent or 0) / int(item.effective_monthly_limit or 0)) >= 0.9
    )

    capacity = get_budget_plan_capacity(db, owner_id, budget_year, budget_month, computed)
    owned_money_now = capacity.owned_money_now
    protected_goal_money = capacity.protected_goal_money
    free_money_now = capacity.free_money_now
    expected_income_remaining = capacity.expected_income_remaining
    expected_income_totals, expected_income_items = get_expected_income_lifecycle_summary(
        db,
        owner_id,
        budget_year,
        budget_month,
    )
    cash_obligation_reserve_total = capacity.cash_obligation_reserve_total
    valid_budget_spent = capacity.valid_budget_spent
    backing_total = capacity.backing_total
    category_floors = get_budget_category_floors(db, owner_id, budget_year, budget_month, computed)
    category_floor_total = sum(int(item.floor_amount or 0) for item in category_floors)
    category_floor_shortfall = sum(int(item.shortfall or 0) for item in category_floors)
    plan_free_money_remaining = int(capacity.cash_backing_total) - int(monthly_effective_limit_total)
    plan_backing_remaining = int(backing_total) - int(monthly_effective_limit_total)
    cash_gap_to_budget_total = max(int(monthly_effective_limit_total) - int(capacity.cash_backing_total), 0)
    backing_shortfall = max(int(monthly_effective_limit_total) - int(backing_total), 0)
    plan_status = get_budget_plan_status(
        int(monthly_effective_limit_total),
        int(capacity.cash_backing_total),
        int(expected_income_remaining),
    )
    borrowing_survival = get_borrowing_survival_summary(
        db,
        owner_id,
        budget_year=budget_year,
        budget_month=budget_month,
        start=start,
        end=end,
    )
    plan_causes: list[schemas.BudgetPlanCauseOut] = []
    if protected_goal_money > 0:
        plan_causes.append(
            schemas.BudgetPlanCauseOut(code="GOAL_PROTECTION", amount=protected_goal_money)
        )
    if cash_obligation_reserve_total > 0:
        plan_causes.append(
            schemas.BudgetPlanCauseOut(
                code="CASH_OBLIGATION_RESERVE",
                amount=cash_obligation_reserve_total,
            )
        )
    for floor in category_floors:
        if floor.warning_gap > 0:
            plan_causes.append(
                schemas.BudgetPlanCauseOut(
                    code="CATEGORY_FLOOR_WARNING",
                    amount=floor.warning_gap,
                    category=floor.category,
                )
            )
    if backing_shortfall > 0:
        plan_causes.append(
            schemas.BudgetPlanCauseOut(code="BACKING_SHORTFALL", amount=backing_shortfall)
        )

    return schemas.BudgetMonthSummaryOut(
        budget_year=budget_year,
        budget_month=budget_month,
        owned_money_now=owned_money_now,
        protected_goal_money=protected_goal_money,
        free_money_now=free_money_now,
        expected_income_remaining=expected_income_remaining,
        expected_income_totals=expected_income_totals,
        expected_income_items=expected_income_items,
        cash_obligation_reserve_total=cash_obligation_reserve_total,
        cash_backing_total=int(capacity.cash_backing_total),
        backing_total=backing_total,
        monthly_budget_limit_total=monthly_budget_limit_total,
        monthly_effective_limit_total=monthly_effective_limit_total,
        monthly_budget_total=monthly_effective_limit_total,
        normal_budget_spent=normal_budget_spent,
        valid_budget_spent=valid_budget_spent,
        normal_budget_remaining=normal_budget_remaining,
        category_floor_total=category_floor_total,
        category_floor_shortfall=category_floor_shortfall,
        category_floors=[
            schemas.BudgetCategoryFloorOut(
                category=item.category,
                floor_amount=item.floor_amount,
                effective_monthly_limit=item.effective_monthly_limit,
                shortfall=item.shortfall,
                sources=item.sources,
                suggested_minimum=item.suggested_minimum,
                current_limit=item.current_limit,
                warning_gap=item.warning_gap,
                reasons=[
                    schemas.BudgetCategoryFloorReasonOut(
                        kind=reason.kind,
                        source_id=reason.source_id,
                        title=reason.title,
                        due_date=reason.due_date,
                        amount=reason.amount,
                    )
                    for reason in item.reasons
                ],
            )
            for item in category_floors
        ],
        plan_free_money_remaining=plan_free_money_remaining,
        plan_backing_remaining=plan_backing_remaining,
        cash_gap_to_budget_total=cash_gap_to_budget_total,
        backing_shortfall=backing_shortfall,
        plan_causes=plan_causes,
        plan_status=plan_status,
        categories_over_limit=categories_over_limit,
        categories_close_to_limit=categories_close_to_limit,
        borrowing_pressure=(
            borrowing_survival.borrowed_usage > 0
            or get_budgeted_wallet_borrowing_pressure(
                db,
                owner_id,
                start_date=start,
                end_date=end,
            )
        ),
        borrowing_survival=schemas.BorrowingSurvivalSummaryOut(
            enabled=borrowing_survival.enabled,
            monthly_cap=borrowing_survival.monthly_cap,
            borrowed_usage=borrowing_survival.borrowed_usage,
            remaining_cap=borrowing_survival.remaining_cap,
            exceeded_amount=borrowing_survival.exceeded_amount,
        ),
    )


def _active_budget_categories() -> list[models.ExpenseCategory]:
    return [
        category
        for category in models.ExpenseCategory
        if category != models.ExpenseCategory.PAYMENT_PLANS_DEBT
    ]


def _budget_by_category(
    db: Session,
    owner_id: int,
    budget_year: int,
    budget_month: int,
) -> dict[models.ExpenseCategory, models.Budget]:
    rows = (
        db.query(models.Budget)
        .filter(
            models.Budget.owner_id == owner_id,
            models.Budget.budget_year == budget_year,
            models.Budget.budget_month == budget_month,
        )
        .all()
    )
    return {row.category: row for row in rows}


def _setup_subcategory_limits(
    db: Session,
    owner_id: int,
    budget: models.Budget | None,
) -> list[schemas.BudgetMonthSetupSubcategoryLimitOut]:
    if budget is None:
        return []
    rows = (
        db.query(models.BudgetSubcategoryLimit, models.UserSubcategory)
        .join(models.UserSubcategory, models.UserSubcategory.id == models.BudgetSubcategoryLimit.subcategory_id)
        .filter(
            models.BudgetSubcategoryLimit.owner_id == owner_id,
            models.BudgetSubcategoryLimit.budget_id == budget.id,
        )
        .order_by(models.UserSubcategory.name.asc(), models.UserSubcategory.id.asc())
        .all()
    )
    return [
        schemas.BudgetMonthSetupSubcategoryLimitOut(
            subcategory_id=int(limit.subcategory_id),
            name=subcategory.name,
            monthly_limit=int(limit.monthly_limit),
        )
        for limit, subcategory in rows
    ]


def build_budget_month_setup_preview(
    db: Session,
    owner_id: int,
    budget_year: int,
    budget_month: int,
    mode: schemas.BudgetMonthSetupMode,
) -> schemas.BudgetMonthSetupPreviewOut:
    source_year, source_month = previous_month(budget_year, budget_month)
    existing_by_category = _budget_by_category(db, owner_id, budget_year, budget_month)
    previous_by_category = _budget_by_category(db, owner_id, source_year, source_month)
    summary = build_budget_month_summary(db, owner_id, budget_year, budget_month)
    floors_by_category = {item.category: item for item in get_budget_category_floors(db, owner_id, budget_year, budget_month)}

    categories = set(_active_budget_categories())
    categories.update(existing_by_category.keys())
    categories.update(previous_by_category.keys())
    categories.update(floors_by_category.keys())

    proposals: list[schemas.BudgetMonthSetupCategoryProposalOut] = []
    for category in sorted(categories, key=lambda item: item.value):
        existing = existing_by_category.get(category)
        previous = previous_by_category.get(category)
        floor_item = floors_by_category.get(category)
        floor_amount = int(floor_item.floor_amount) if floor_item is not None else 0

        copied_from_previous = False
        if existing is not None:
            proposed_limit = int(existing.monthly_limit)
        elif mode == schemas.BudgetMonthSetupMode.PLAN_FROM_SCRATCH:
            proposed_limit = 0
        else:
            proposed_limit = int(previous.monthly_limit) if previous is not None else 0
            copied_from_previous = previous is not None

        if mode == schemas.BudgetMonthSetupMode.SMART_AUTO_FILL:
            proposed_limit = max(proposed_limit, floor_amount)

        proposals.append(
            schemas.BudgetMonthSetupCategoryProposalOut(
                category=category,
                existing_budget_id=int(existing.id) if existing is not None else None,
                existing_monthly_limit=int(existing.monthly_limit) if existing is not None else None,
                previous_budget_id=int(previous.id) if previous is not None else None,
                previous_monthly_limit=int(previous.monthly_limit) if previous is not None else None,
                proposed_monthly_limit=int(proposed_limit),
                floor_amount=floor_amount,
                floor_shortfall=max(floor_amount - int(proposed_limit), 0),
                floor_sources=floor_item.sources if floor_item is not None else [],
                copied_from_previous=copied_from_previous,
                subcategory_limits=_setup_subcategory_limits(
                    db,
                    owner_id,
                    existing if existing is not None else (previous if copied_from_previous else None),
                ),
            )
        )

    proposed_total = sum(int(item.proposed_monthly_limit) for item in proposals)
    plan_status = get_budget_plan_status(
        proposed_total,
        int(summary.free_money_now) + int(summary.valid_budget_spent) - int(summary.cash_obligation_reserve_total),
        int(summary.expected_income_remaining),
    )
    return schemas.BudgetMonthSetupPreviewOut(
        budget_year=budget_year,
        budget_month=budget_month,
        mode=mode,
        source_budget_year=source_year,
        source_budget_month=source_month,
        category_proposals=proposals,
        proposed_monthly_limit_total=proposed_total,
        backing_total=int(summary.backing_total),
        backing_shortfall=max(proposed_total - int(summary.backing_total), 0),
        plan_status=plan_status,
        category_floor_total=int(summary.category_floor_total),
        category_floor_shortfall=sum(int(item.floor_shortfall) for item in proposals),
        cash_obligation_reserve_total=int(summary.cash_obligation_reserve_total),
        month_summary=summary,
    )


def apply_budget_month_setup(
    db: Session,
    owner_id: int,
    budget_year: int,
    budget_month: int,
    mode: schemas.BudgetMonthSetupMode,
) -> schemas.BudgetMonthSetupPreviewOut:
    if mode == schemas.BudgetMonthSetupMode.PLAN_FROM_SCRATCH:
        return build_budget_month_setup_preview(db, owner_id, budget_year, budget_month, mode)

    preview = build_budget_month_setup_preview(db, owner_id, budget_year, budget_month, mode)
    for proposal in preview.category_proposals:
        proposed_limit = int(proposal.proposed_monthly_limit)
        if proposed_limit <= 0:
            continue

        budget = (
            db.query(models.Budget)
            .filter(
                models.Budget.owner_id == owner_id,
                models.Budget.category == proposal.category,
                models.Budget.budget_year == budget_year,
                models.Budget.budget_month == budget_month,
            )
            .with_for_update()
            .first()
        )
        if budget is None:
            budget = models.Budget(
                owner_id=owner_id,
                category=proposal.category,
                budget_year=budget_year,
                budget_month=budget_month,
                monthly_limit=proposed_limit,
                auto_created=False,
            )
            db.add(budget)
            db.flush()
        elif mode == schemas.BudgetMonthSetupMode.SMART_AUTO_FILL and int(budget.monthly_limit) < proposed_limit:
            budget.monthly_limit = proposed_limit
            db.flush()

        for subcategory_limit in proposal.subcategory_limits:
            existing_limit = get_budget_subcategory_limit(
                db,
                owner_id,
                int(budget.id),
                int(subcategory_limit.subcategory_id),
            )
            if existing_limit is None:
                db.add(
                    models.BudgetSubcategoryLimit(
                        owner_id=owner_id,
                        budget_id=int(budget.id),
                        subcategory_id=int(subcategory_limit.subcategory_id),
                        monthly_limit=int(subcategory_limit.monthly_limit),
                    )
                )

    db.flush()
    for category in {proposal.category for proposal in preview.category_proposals}:
        recompute_budget_chain(db, owner_id, category)
    db.flush()
    return build_budget_month_setup_preview(db, owner_id, budget_year, budget_month, mode)


def get_budget_subcategory_limit_map(
    db: Session,
    owner_id: int,
    budget_id: int,
) -> dict[int, int | None]:
    rows = (
        db.query(models.BudgetSubcategoryLimit)
        .filter(
            models.BudgetSubcategoryLimit.owner_id == owner_id,
            models.BudgetSubcategoryLimit.budget_id == budget_id,
        )
        .all()
    )
    return {int(row.subcategory_id): (int(row.monthly_limit) if row.monthly_limit is not None else None) for row in rows}


def get_budget_subcategory_limit(
    db: Session,
    owner_id: int,
    budget_id: int,
    subcategory_id: int,
) -> models.BudgetSubcategoryLimit | None:
    return (
        db.query(models.BudgetSubcategoryLimit)
        .filter(
            models.BudgetSubcategoryLimit.owner_id == owner_id,
            models.BudgetSubcategoryLimit.budget_id == budget_id,
            models.BudgetSubcategoryLimit.subcategory_id == subcategory_id,
        )
        .first()
    )


def build_budget_subcategory_out(
    subcategory: models.UserSubcategory,
    monthly_limit: int | None,
    *,
    spent: int = 0,
) -> schemas.BudgetSubcategoryOut:
    remaining = int(monthly_limit) - int(spent) if monthly_limit is not None else None
    return schemas.BudgetSubcategoryOut(
        id=subcategory.id,
        owner_id=subcategory.owner_id,
        category=subcategory.category,
        name=subcategory.name,
        monthly_limit=monthly_limit,
        is_active=subcategory.is_active,
        created_at=subcategory.created_at,
        spent=int(spent),
        remaining=remaining,
        is_over_limit=remaining is not None and remaining < 0,
    )


def get_budget_detail(
    db: Session,
    owner_id: int,
    budget: models.Budget,
) -> schemas.BudgetDetailOut:
    computations = compute_budget_chain(db, owner_id, [budget])
    if not computations:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="budgets.not_found")

    budget_out = schemas.BudgetDetailOut(
        **build_budget_out(computations[0]).model_dump(),
        subcategories=[],
        recent_activity=[],
        project_spending=[],
        project_reservations=[],
        expense_count=0,
    )
    subcategories = (
        db.query(models.UserSubcategory)
        .filter(
            models.UserSubcategory.owner_id == owner_id,
            models.UserSubcategory.category == budget.category,
        )
        .order_by(models.UserSubcategory.name.asc())
        .all()
    )
    spent_by_subcategory = get_subcategory_spent_for_month(
        db,
        owner_id=owner_id,
        category=budget.category,
        budget_year=budget.budget_year,
        budget_month=budget.budget_month,
    )
    limits_by_subcategory = get_budget_subcategory_limit_map(db, owner_id, int(budget.id))

    sub_outs = []
    for subcategory in subcategories:
        limit = limits_by_subcategory.get(int(subcategory.id))
        spent = int(spent_by_subcategory.get(subcategory.id, 0))
        if int(subcategory.id) not in limits_by_subcategory and spent == 0:
            continue
        sub_outs.append(
            build_budget_subcategory_out(
                subcategory,
                limit,
                spent=spent,
            )
        )
    budget_out.subcategories = sub_outs

    activity_rows = (
        db.query(
            models.FinancialEvent.id.label("event_id"),
            models.FinancialEvent.title,
            models.FinancialEvent.event_type,
            models.FinancialEvent.date,
            models.FinancialEvent.is_session,
            models.FinancialEvent.merge_group_id,
            models.ExpenseMergeGroup.title.label("merge_group_title"),
            models.EntityLedger.amount,
            models.EntityLedger.subcategory_id,
            models.UserSubcategory.name.label("subcategory_name"),
            models.EntityLedger.project_id,
            models.Project.title.label("project_title"),
        )
        .join(models.EntityLedger, models.EntityLedger.event_id == models.FinancialEvent.id)
        .outerjoin(models.UserSubcategory, models.UserSubcategory.id == models.EntityLedger.subcategory_id)
        .outerjoin(models.Project, models.Project.id == models.EntityLedger.project_id)
        .outerjoin(models.ExpenseMergeGroup, models.ExpenseMergeGroup.id == models.FinancialEvent.merge_group_id)
        .filter(
            models.FinancialEvent.owner_id == owner_id,
            models.FinancialEvent.status == models.FinancialEventStatus.POSTED,
            models.EntityLedger.budget_id == budget.id,
            models.FinancialEvent.event_type.in_(
                [models.TransactionType.EXPENSE, models.TransactionType.REFUND]
            ),
            _isolated_project_spend_filter(),
            _normal_monthly_budget_impact_filter(),
        )
        .order_by(models.FinancialEvent.date.desc(), models.FinancialEvent.created_at.desc(), models.FinancialEvent.id.desc())
        .limit(12)
        .all()
    )
    budget_out.recent_activity = [
        schemas.BudgetActivityOut(
            event_id=int(row.event_id),
            title=str(row.title),
            amount=abs(int(row.amount or 0)),
            transaction_type=row.event_type,
            date=row.date,
            is_session=bool(row.is_session),
            subcategory_id=int(row.subcategory_id) if row.subcategory_id is not None else None,
            subcategory_name=row.subcategory_name,
            project_id=int(row.project_id) if row.project_id is not None else None,
            project_title=row.project_title,
            merge_group_id=int(row.merge_group_id) if row.merge_group_id is not None else None,
            merge_group_title=row.merge_group_title,
        )
        for row in activity_rows
    ]

    budget_out.expense_count = int(
        db.query(func.count(func.distinct(models.FinancialEvent.id)))
        .select_from(models.EntityLedger)
        .join(models.FinancialEvent, models.FinancialEvent.id == models.EntityLedger.event_id)
        .outerjoin(models.Project, models.Project.id == models.EntityLedger.project_id)
        .filter(
            models.FinancialEvent.owner_id == owner_id,
            models.FinancialEvent.status == models.FinancialEventStatus.POSTED,
            models.EntityLedger.budget_id == budget.id,
            models.FinancialEvent.event_type.in_(
                [models.TransactionType.EXPENSE, models.TransactionType.REFUND]
            ),
            _isolated_project_spend_filter(),
            _normal_monthly_budget_impact_filter(),
        )
        .scalar()
        or 0
    )

    signed_amount = _signed_expense_amount()
    project_rows = (
        db.query(
            models.Project.id,
            models.Project.title,
            models.Project.project_type,
            func.coalesce(func.sum(signed_amount), 0).label("spent"),
        )
        .select_from(models.EntityLedger)
        .join(models.FinancialEvent, models.FinancialEvent.id == models.EntityLedger.event_id)
        .join(models.Project, models.Project.id == models.EntityLedger.project_id)
        .filter(
            models.FinancialEvent.owner_id == owner_id,
            models.FinancialEvent.status == models.FinancialEventStatus.POSTED,
            models.EntityLedger.budget_id == budget.id,
            models.EntityLedger.project_id.isnot(None),
            models.FinancialEvent.event_type.in_(
                [models.TransactionType.EXPENSE, models.TransactionType.REFUND]
            ),
            _isolated_project_spend_filter(),
            _normal_monthly_budget_impact_filter(),
        )
        .group_by(models.Project.id, models.Project.title, models.Project.project_type)
        .order_by(func.coalesce(func.sum(signed_amount), 0).desc(), models.Project.title.asc())
        .all()
    )
    budget_out.project_spending = [
        schemas.BudgetProjectSpendOut(
            project_id=int(row.id),
            project_title=str(row.title),
            is_isolated=row.project_type == models.ProjectType.ISOLATED,
            spent=int(row.spent or 0),
        )
        for row in project_rows
    ]
    project_spent_by_category = get_overlay_project_spent_by_project_category(
        db,
        owner_id,
        int(budget.budget_year),
        int(budget.budget_month),
    )
    reservation_rows = get_overlay_project_reservation_rows(
        db,
        owner_id,
        int(budget.budget_year),
        int(budget.budget_month),
        category=budget.category,
    )
    budget_out.project_reservations = []
    for reservation in reservation_rows:
        spent = int(project_spent_by_category.get((int(reservation.project_id), reservation.category), 0))
        remaining = int(reservation.limit_amount) - spent
        budget_out.project_reservations.append(
            schemas.BudgetProjectReservationOut(
                project_id=int(reservation.project_id),
                project_title=str(reservation.project.title),
                category=reservation.category,
                budget_year=int(reservation.budget_year),
                budget_month=int(reservation.budget_month),
                reserved_amount=int(reservation.limit_amount),
                spent=spent,
                remaining=remaining,
                is_over_limit=remaining < 0,
            )
        )
    return budget_out


def get_subcategory_spent_for_month(
    db: Session,
    owner_id: int,
    category: models.ExpenseCategory,
    budget_year: int,
    budget_month: int,
) -> dict[int, int]:
    start, end = month_bounds(budget_year, budget_month)
    signed_amount = _signed_expense_amount()
    rows = (
        db.query(
            models.EntityLedger.subcategory_id,
            func.coalesce(func.sum(signed_amount), 0).label("spent"),
        )
        .join(models.FinancialEvent, models.FinancialEvent.id == models.EntityLedger.event_id)
        .outerjoin(models.Project, models.Project.id == models.EntityLedger.project_id)
        .filter(
            models.FinancialEvent.owner_id == owner_id,
            models.FinancialEvent.status == models.FinancialEventStatus.POSTED,
            models.EntityLedger.category == category,
            models.EntityLedger.subcategory_id.isnot(None),
            models.FinancialEvent.event_type.in_(
                [models.TransactionType.EXPENSE, models.TransactionType.REFUND]
            ),
            models.FinancialEvent.date >= start,
            models.FinancialEvent.date < end,
            *normal_monthly_budget_impact_filters(),
        )
        .group_by(models.EntityLedger.subcategory_id)
        .all()
    )
    return {int(row.subcategory_id): int(row.spent or 0) for row in rows if row.subcategory_id is not None}


def validate_subcategory_limit(
    db: Session,
    owner_id: int,
    subcategory: models.UserSubcategory,
    amount: int,
    expense_date: date,
    project: models.Project | None = None,
    exclude_event_id: int | None = None,
) -> None:
    if not subcategory.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="budgets.subcategory_inactive")
    if project is not None and is_isolated_project(project):
        return

    start, end = month_bounds(expense_date.year, expense_date.month)
    budget = (
        db.query(models.Budget)
        .filter(
            models.Budget.owner_id == owner_id,
            models.Budget.category == subcategory.category,
            models.Budget.budget_year == expense_date.year,
            models.Budget.budget_month == expense_date.month,
        )
        .first()
    )
    if budget is None:
        budget = materialize_budget_for_month(
            db,
            owner_id,
            subcategory.category,
            expense_date.year,
            expense_date.month,
        )
    if budget is None:
        return
    limit = get_budget_subcategory_limit(db, owner_id, int(budget.id), int(subcategory.id))
    if limit is None:
        return
    spent = get_budget_spent_amount(
        db,
        owner_id,
        start_date=start,
        end_date=end,
        subcategory_id=int(subcategory.id),
        exclude_event_id=exclude_event_id,
    )
    if spent + amount > int(limit.monthly_limit):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="budgets.subcategory_limit_exceeded")


def validate_budget_limit(
    db: Session,
    owner_id: int,
    budget: models.Budget,
    amount: int,
    exclude_event_id: int | None = None,
    project: models.Project | None = None,
) -> None:
    if amount <= 0:
        return
    if project is not None and is_isolated_project(project):
        return

    key = (str(budget.category), int(budget.budget_year), int(budget.budget_month))
    effects = get_budget_ledger_effects(db, owner_id).get(key, {})
    spent = get_budget_spent_amount(
        db,
        owner_id,
        budget_id=int(budget.id),
        exclude_event_id=exclude_event_id,
    )
    cap_trim_amount = int(abs(effects.get("CAP_TRIM", 0)))
    effective_limit = int(budget.monthly_limit or 0) - cap_trim_amount
    if spent + amount > effective_limit:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="budgets.limit_exceeded")


def validate_subcategory_total_limit(
    db: Session,
    owner_id: int,
    budget: models.Budget,
    incoming_limit: int | None,
    exclude_subcategory_id: int | None = None,
) -> None:
    if incoming_limit is None:
        return

    current_total = (
        db.query(func.coalesce(func.sum(models.BudgetSubcategoryLimit.monthly_limit), 0))
        .filter(
            models.BudgetSubcategoryLimit.owner_id == owner_id,
            models.BudgetSubcategoryLimit.budget_id == budget.id,
        )
    )
    if exclude_subcategory_id is not None:
        current_total = current_total.filter(models.BudgetSubcategoryLimit.subcategory_id != exclude_subcategory_id)
    total = int(current_total.scalar() or 0) + int(incoming_limit)
    if total > int(budget.monthly_limit):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="budgets.subcategory_total_exceeds_parent")


def get_budget_remaining_for_month(
    db: Session,
    owner_id: int,
    category: models.ExpenseCategory,
    year: int,
    month: int,
) -> int:
    budget = materialize_budget_for_month(db, owner_id, category, year, month)
    if budget is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="expenses.budget_required")
    computed = compute_budget_chain(db, owner_id, [budget])[0]
    return int(computed.remaining)


def get_project_budget_summaries(
    db: Session,
    owner_id: int,
    selected_budget_year: int | None = None,
    selected_budget_month: int | None = None,
    default_budget_date: date | None = None,
) -> list[schemas.ProjectBudgetOut]:
    if (selected_budget_year is None) != (selected_budget_month is None):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="projects.reservation_month_required")
    if selected_budget_year is None or selected_budget_month is None:
        if default_budget_date is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="projects.reservation_month_required")
        selected_budget_year = default_budget_date.year
        selected_budget_month = default_budget_date.month

    projects = (
        db.query(models.Project)
        .filter(models.Project.owner_id == owner_id)
        .order_by(models.Project.created_at.desc())
        .all()
    )
    if not projects:
        return []

    signed_amount = _signed_expense_amount()
    project_spend_rows = (
        db.query(
            models.EntityLedger.project_id,
            func.coalesce(func.sum(signed_amount), 0),
        )
        .join(models.FinancialEvent, models.FinancialEvent.id == models.EntityLedger.event_id)
        .filter(
            models.FinancialEvent.owner_id == owner_id,
            models.FinancialEvent.status == models.FinancialEventStatus.POSTED,
            models.EntityLedger.project_id.isnot(None),
            models.FinancialEvent.event_type.in_(
                [models.TransactionType.EXPENSE, models.TransactionType.REFUND]
            ),
        )
        .group_by(models.EntityLedger.project_id)
        .all()
    )
    spent_by_project = {int(project_id): int(amount or 0) for project_id, amount in project_spend_rows if project_id is not None}
    project_release_rows = (
        db.query(
            models.GoalProjectRelease.project_id,
            func.coalesce(func.sum(models.GoalProjectRelease.amount), 0),
        )
        .filter(
            models.GoalProjectRelease.owner_id == owner_id,
        )
        .group_by(models.GoalProjectRelease.project_id)
        .all()
    )
    released_by_project = {
        int(project_id): int(amount or 0)
        for project_id, amount in project_release_rows
        if project_id is not None
    }

    project_category_rows = (
        db.query(
            models.EntityLedger.project_id,
            models.EntityLedger.category,
            func.coalesce(func.sum(signed_amount), 0),
        )
        .join(models.FinancialEvent, models.FinancialEvent.id == models.EntityLedger.event_id)
        .filter(
            models.FinancialEvent.owner_id == owner_id,
            models.FinancialEvent.status == models.FinancialEventStatus.POSTED,
            models.EntityLedger.project_id.isnot(None),
            models.EntityLedger.category.isnot(None),
            models.FinancialEvent.event_type.in_(
                [models.TransactionType.EXPENSE, models.TransactionType.REFUND]
            ),
        )
        .group_by(models.EntityLedger.project_id, models.EntityLedger.category)
        .all()
    )
    category_spent: dict[tuple[int, models.ExpenseCategory], int] = {
        (int(project_id), category): int(amount or 0)
        for project_id, category, amount in project_category_rows
        if project_id is not None and category is not None
    }
    selected_overlay_category_spent = get_overlay_project_spent_by_project_category(
        db,
        owner_id,
        int(selected_budget_year),
        int(selected_budget_month),
    )
    selected_overlay_subcategory_spent = get_overlay_project_spent_by_project_subcategory(
        db,
        owner_id,
        int(selected_budget_year),
        int(selected_budget_month),
    )
    total_reserved_scope_by_project: dict[int, int] = {}
    for project in projects:
        if get_project_type(project) == models.ProjectType.ISOLATED:
            continue
        total_reserved_scope_by_project[int(project.id)] = sum(
            int(limit.limit_amount or 0)
            for limit in project.monthly_category_limits
        )
    overlay_subcategory_rows = (
        db.query(models.ProjectSubcategoryMonthlyLimit)
        .join(models.Project, models.Project.id == models.ProjectSubcategoryMonthlyLimit.project_id)
        .join(models.UserSubcategory, models.UserSubcategory.id == models.ProjectSubcategoryMonthlyLimit.user_subcategory_id)
        .filter(
            models.Project.owner_id == owner_id,
            models.Project.project_type == models.ProjectType.OVERLAY,
            models.ProjectSubcategoryMonthlyLimit.budget_year == int(selected_budget_year),
            models.ProjectSubcategoryMonthlyLimit.budget_month == int(selected_budget_month),
        )
        .order_by(models.ProjectSubcategoryMonthlyLimit.project_id.asc(), models.UserSubcategory.name.asc())
        .all()
    )
    overlay_subcategories_by_project: dict[int, list[models.ProjectSubcategoryMonthlyLimit]] = defaultdict(list)
    for row in overlay_subcategory_rows:
        overlay_subcategories_by_project[int(row.project_id)].append(row)
    project_subcategory_rows = (
        db.query(
            models.EntityLedger.project_subcategory_id,
            func.coalesce(func.sum(signed_amount), 0),
        )
        .join(models.FinancialEvent, models.FinancialEvent.id == models.EntityLedger.event_id)
        .filter(
            models.FinancialEvent.owner_id == owner_id,
            models.FinancialEvent.status == models.FinancialEventStatus.POSTED,
            models.EntityLedger.project_subcategory_id.isnot(None),
            models.FinancialEvent.event_type.in_(
                [models.TransactionType.EXPENSE, models.TransactionType.REFUND]
            ),
        )
        .group_by(models.EntityLedger.project_subcategory_id)
        .all()
    )
    spent_by_project_subcategory = {
        int(project_subcategory_id): int(amount or 0)
        for project_subcategory_id, amount in project_subcategory_rows
        if project_subcategory_id is not None
    }

    outputs: list[schemas.ProjectBudgetOut] = []
    for project in projects:
        project_type = get_project_type(project)
        is_isolated = project_type == models.ProjectType.ISOLATED
        spent = int(spent_by_project.get(project.id, 0))
        subcategories_by_category: dict[models.ExpenseCategory, list[schemas.ProjectSubcategoryOut]] = {}
        if is_isolated:
            for subcategory in project.subcategories:
                spent_subcategory = int(spent_by_project_subcategory.get(int(subcategory.id), 0))
                remaining_subcategory = (
                    int(subcategory.limit_amount) - spent_subcategory
                    if subcategory.limit_amount is not None
                    else None
                )
                subcategories_by_category.setdefault(subcategory.category, []).append(
                    schemas.ProjectSubcategoryOut(
                        id=subcategory.id,
                        project_id=subcategory.project_id,
                        category=subcategory.category,
                        name=subcategory.name,
                        is_active=bool(subcategory.is_active),
                        limit_amount=int(subcategory.limit_amount) if subcategory.limit_amount is not None else None,
                        spent=spent_subcategory,
                        remaining=remaining_subcategory,
                        is_over_limit=remaining_subcategory is not None and remaining_subcategory < 0,
                        created_at=subcategory.created_at,
                        updated_at=subcategory.updated_at,
                    )
                )
        else:
            for reservation in overlay_subcategories_by_project.get(int(project.id), []):
                global_subcategory = reservation.user_subcategory
                spent_subcategory = int(
                    selected_overlay_subcategory_spent.get(
                        (int(reservation.project_id), int(reservation.user_subcategory_id)),
                        0,
                    )
                )
                remaining_subcategory = int(reservation.limit_amount) - spent_subcategory
                subcategories_by_category.setdefault(reservation.category, []).append(
                    schemas.ProjectSubcategoryOut(
                        id=reservation.id,
                        project_id=reservation.project_id,
                        category=reservation.category,
                        name=global_subcategory.name,
                        is_active=bool(global_subcategory.is_active),
                        user_subcategory_id=int(reservation.user_subcategory_id),
                        budget_year=int(reservation.budget_year),
                        budget_month=int(reservation.budget_month),
                        limit_amount=int(reservation.limit_amount),
                        spent=spent_subcategory,
                        remaining=remaining_subcategory,
                        is_over_limit=remaining_subcategory < 0,
                        created_at=reservation.created_at,
                        updated_at=reservation.updated_at,
                    )
                )

        category_breakdown = []
        category_limits = (
            list(project.category_limits)
            if is_isolated
            else [
                item
                for item in project.monthly_category_limits
                if int(item.budget_year) == int(selected_budget_year)
                and int(item.budget_month) == int(selected_budget_month)
            ]
        )
        for limit in category_limits:
            if is_isolated:
                category_spent_amount = int(category_spent.get((project.id, limit.category), 0))
            else:
                category_spent_amount = int(selected_overlay_category_spent.get((project.id, limit.category), 0))
            remaining = int(limit.limit_amount) - category_spent_amount
            category_breakdown.append(
                schemas.ProjectBudgetCategoryDetailOut(
                    category=limit.category,
                    limit_amount=int(limit.limit_amount),
                    budget_year=int(limit.budget_year) if not is_isolated else None,
                    budget_month=int(limit.budget_month) if not is_isolated else None,
                    spent=category_spent_amount,
                    remaining=remaining,
                    is_over_limit=remaining < 0,
                    subcategories=sorted(
                        subcategories_by_category.get(limit.category, []),
                        key=lambda item: item.name.lower(),
                    ),
                )
            )
        funding_limit = get_project_funding_limit(project)
        target_estimate = get_project_target_estimate(project)
        wallet_allocated = get_project_wallet_allocated_amount(project) if is_isolated else 0
        remaining = funding_limit - spent if funding_limit is not None else None
        released_funding = (
            int(released_by_project.get(project.id, 0))
            if project.origin_goal_id is not None
            else None
        )
        if wallet_allocated > 0:
            remaining_funding = int(wallet_allocated) - spent
            funding_shortfall = max(int(spent) - int(wallet_allocated), 0)
        elif released_funding is not None:
            remaining_funding = int(released_funding) - spent
            funding_shortfall = max(int(spent) - int(released_funding), 0)
        else:
            remaining_funding = None
            funding_shortfall = 0
        progress_direction = "tick_down" if is_isolated else "tick_up"
        selected_month_reserved_amount = (
            0
            if is_isolated
            else sum(int(item.limit_amount or 0) for item in category_limits)
        )
        overlay = None
        isolated = None
        total_reserved_scope = 0 if is_isolated else int(total_reserved_scope_by_project.get(int(project.id), 0))
        if is_isolated:
            isolated = schemas.ProjectIsolatedFinancialOut(
                funding_limit=funding_limit,
                released_funding=released_funding,
                remaining_funding=remaining_funding,
                funding_shortfall=funding_shortfall,
                wallet_allocations=project_wallet_allocations_out(project),
            )
        else:
            overlay = schemas.ProjectOverlayFinancialOut(
                target_estimate=target_estimate,
                selected_month_reserved_amount=selected_month_reserved_amount,
                total_reserved_scope=total_reserved_scope,
            )
        outputs.append(
            schemas.ProjectBudgetOut(
                id=project.id,
                owner_id=project.owner_id,
                title=project.title,
                description=project.description,
                project_type=project_type,
                is_isolated=is_isolated,
                total_limit=funding_limit if is_isolated else None,
                target_estimate=target_estimate if not is_isolated else None,
                overlay=overlay,
                isolated=isolated,
                status=project.status,
                origin_goal_id=project.origin_goal_id,
                start_date=project.start_date,
                target_end_date=project.target_end_date,
                completed_at=project.completed_at,
                spent=spent,
                released_funding=released_funding,
                remaining_funding=remaining_funding,
                funding_shortfall=funding_shortfall,
                progress_direction=progress_direction,
                remaining=remaining,
                is_over_limit=remaining is not None and remaining < 0,
                selected_budget_year=int(selected_budget_year),
                selected_budget_month=int(selected_budget_month),
                selected_month_reserved_amount=selected_month_reserved_amount,
                total_reserved_scope=total_reserved_scope,
                category_breakdown=category_breakdown,
                created_at=project.created_at,
                updated_at=project.updated_at,
            )
        )
    return outputs


def get_owned_subcategory_or_404(
    db: Session,
    owner_id: int,
    subcategory_id: int,
) -> models.UserSubcategory:
    subcategory = (
        db.query(models.UserSubcategory)
        .filter(
            models.UserSubcategory.id == subcategory_id,
            models.UserSubcategory.owner_id == owner_id,
        )
        .first()
    )
    if not subcategory:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="budgets.subcategory_not_found")
    return subcategory


def get_owned_project_or_404(
    db: Session,
    owner_id: int,
    project_id: int,
) -> models.Project:
    project = (
        db.query(models.Project)
        .filter(models.Project.id == project_id, models.Project.owner_id == owner_id)
        .first()
    )
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="projects.not_found")
    return project


def get_owned_project_subcategory_or_404(
    db: Session,
    owner_id: int,
    project_id: int,
    project_subcategory_id: int,
) -> models.ProjectSubcategory:
    subcategory = (
        db.query(models.ProjectSubcategory)
        .join(models.Project, models.Project.id == models.ProjectSubcategory.project_id)
        .filter(
            models.ProjectSubcategory.id == project_subcategory_id,
            models.ProjectSubcategory.project_id == project_id,
            models.Project.owner_id == owner_id,
        )
        .first()
    )
    if not subcategory:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="projects.subcategory_not_found")
    return subcategory


def validate_project_budget(
    db: Session,
    owner_id: int,
    project: models.Project,
    category: models.ExpenseCategory,
    amount: int,
    expense_date: date,
    project_subcategory: models.ProjectSubcategory | None = None,
    exclude_event_id: int | None = None,
) -> None:
    if project.status != models.ProjectStatus.ACTIVE:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="projects.not_active")
    if expense_date < project.start_date:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="projects.expense_before_start")
    if project.target_end_date is not None and expense_date > project.target_end_date:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="projects.expense_after_end")
    if project.completed_at is not None and expense_date > project.completed_at:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="projects.expense_after_completion")

    if not is_isolated_project(project):
        if project_subcategory is not None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="projects.subcategories_isolated_only")
            
        limit_exists = (
            db.query(models.ProjectCategoryMonthlyLimit.id)
            .filter(
                models.ProjectCategoryMonthlyLimit.project_id == project.id,
                models.ProjectCategoryMonthlyLimit.category == category,
                models.ProjectCategoryMonthlyLimit.budget_year == expense_date.year,
                models.ProjectCategoryMonthlyLimit.budget_month == expense_date.month,
            )
            .first()
        )
        if limit_exists is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="budgets.project_category_not_part_of_project")
            
        return

    signed_amount = _signed_expense_amount()
    total_query = (
        db.query(func.coalesce(func.sum(signed_amount), 0))
        .select_from(models.EntityLedger)
        .join(models.FinancialEvent, models.FinancialEvent.id == models.EntityLedger.event_id)
        .filter(
            models.FinancialEvent.owner_id == owner_id,
            models.FinancialEvent.status == models.FinancialEventStatus.POSTED,
            models.EntityLedger.project_id == project.id,
            models.FinancialEvent.event_type.in_(
                [models.TransactionType.EXPENSE, models.TransactionType.REFUND]
            ),
        )
    )
    if exclude_event_id is not None:
        total_query = total_query.filter(models.FinancialEvent.id != exclude_event_id)
    spent_total = int(total_query.scalar() or 0)
    funding_limit = get_project_funding_limit(project)
    if funding_limit is not None and spent_total + amount > funding_limit:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="budgets.project_limit_exceeded")

    category_limit = next((item for item in project.category_limits if item.category == category), None)
    if category_limit is None:
        if project_subcategory is not None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="projects.category_limit_required_for_subcategories")
        return

    category_query = (
        db.query(func.coalesce(func.sum(signed_amount), 0))
        .select_from(models.EntityLedger)
        .join(models.FinancialEvent, models.FinancialEvent.id == models.EntityLedger.event_id)
        .filter(
            models.FinancialEvent.owner_id == owner_id,
            models.FinancialEvent.status == models.FinancialEventStatus.POSTED,
            models.EntityLedger.project_id == project.id,
            models.EntityLedger.category == category,
            models.FinancialEvent.event_type.in_(
                [models.TransactionType.EXPENSE, models.TransactionType.REFUND]
            ),
        )
    )
    if exclude_event_id is not None:
        category_query = category_query.filter(models.FinancialEvent.id != exclude_event_id)
    spent_category = int(category_query.scalar() or 0)
    if spent_category + amount > int(category_limit.limit_amount):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="budgets.project_category_limit_exceeded")

    if project_subcategory is None:
        return
    if project_subcategory.project_id != project.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="projects.subcategory_project_mismatch")
    if project_subcategory.category != category:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="projects.subcategory_category_mismatch")
    if not project_subcategory.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="projects.subcategory_inactive")
    if not is_isolated_project(project):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="projects.subcategories_isolated_only")
    if project_subcategory.limit_amount is None:
        return

    subcategory_query = (
        db.query(func.coalesce(func.sum(signed_amount), 0))
        .select_from(models.EntityLedger)
        .join(models.FinancialEvent, models.FinancialEvent.id == models.EntityLedger.event_id)
        .filter(
            models.FinancialEvent.owner_id == owner_id,
            models.FinancialEvent.status == models.FinancialEventStatus.POSTED,
            models.EntityLedger.project_id == project.id,
            models.EntityLedger.project_subcategory_id == project_subcategory.id,
            models.FinancialEvent.event_type.in_(
                [models.TransactionType.EXPENSE, models.TransactionType.REFUND]
            ),
        )
    )
    if exclude_event_id is not None:
        subcategory_query = subcategory_query.filter(models.FinancialEvent.id != exclude_event_id)
    spent_subcategory = int(subcategory_query.scalar() or 0)
    if spent_subcategory + amount > int(project_subcategory.limit_amount):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="projects.subcategory_limit_exceeded")
