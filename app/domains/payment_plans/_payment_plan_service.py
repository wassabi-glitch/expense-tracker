"""Payment Plan domain service — scheduled obligation helpers.

This module provides shared payment-plan functions that were previously
inline in the router.  The router remains the owner of HTTP-level logic
(rate limiting, request parsing, response building); this module owns
pure domain helpers.

Domain separation rule
----------------------
- **Payment Plan domain** OWNS Payment Plan rules: schedule rows, waterfall
  spillover, charge/premium rows, row statuses, Payment Plan Ledger entries,
  imported-path behaviour, and Payment Plan lifecycle.
- **Debt domain** is a SEPARATE domain — open-ended running-balance obligations.
- Shared money-posting mechanics stay in ``app.domains.posting`` (expense
  posting) and ``app.domains.ledger`` (event recording).
"""

import calendar
from datetime import date, timedelta, tzinfo

from sqlalchemy.orm import Session

from app import models, schemas
from app.services.budget_service import (
    validate_budget_limit,
    validate_subcategory_limit,
)
from app.services.expense_posting_service import post_expense_event
from app.timezone import today_in_tz
from app.utils import check_budget_alerts


# ---------------------------------------------------------------------------
# Date helpers
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Expense event creation
# ---------------------------------------------------------------------------


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
    """Create an expense-shaped FinancialEvent for a payment plan payment.

    Delegates to the shared Expense Posting seam so that wallet ledger
    classification, entity ledger links, budget permission, project rules,
    goal protection, and user-local date validation all go through the
    canonical path.

    Payment-plan-specific extras (budget-limit check, subcategory-limit
    check, budget alerts) are still applied by this adapter.
    """
    local_today = today_in_tz(user_tz)

    # Convert PaymentPlanWalletAllocationIn → dict form for Expense Posting
    wallet_allocs = [
        {"wallet_id": int(a.wallet_id), "amount": int(a.amount)}
        for a in wallet_allocations
    ]

    result = post_expense_event(
        db,
        owner_id,
        title=title,
        amount=int(amount),
        category=category,
        expense_date=expense_date,
        description=note,
        wallet_allocations=wallet_allocs,
        subcategory_id=subcategory_id,
        project_id=project_id,
        project_subcategory_id=project_subcategory_id,
        reference_type=reference_type,
        local_today=local_today,
        payment_plan_id=payment_plan_id,
        payment_plan_payment_id=payment_plan_payment_id,
    )

    # Payment-plan-specific validations retained by this adapter
    if result.budget is not None:
        validate_budget_limit(db, owner_id, result.budget, amount, project=result.project)
    if result.subcategory is not None:
        validate_subcategory_limit(
            db, owner_id, result.subcategory, amount, expense_date, project=result.project,
        )

    check_budget_alerts(db, result.budget)
    return result.event
