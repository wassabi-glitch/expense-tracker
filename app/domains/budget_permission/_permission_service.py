"""Budget Permission — spend-time permission checks for money-posting flows.

This module is the write-time Budget Permission seam.  It answers one question:
"Is this proposed spend allowed to hit this Budget category this month?"

It does **not** own:
- Budget Month Summary (reporting / display)
- Project Budget View (reporting / display)
- Budget chain recomputation (a side-effect after posting)
- Ownership / linkage validation (that belongs in session_draft_service)

Callers (Expense Posting, Debt charge posting, Payment Plan charge posting)
depend on this small interface instead of broad Budget reporting behavior.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app import models
from app.domains.budget_reporting._budget_service import (
    materialize_budget_for_month,
    validate_project_budget,
)
from app.domains.projects._quarantine import is_isolated_project  # ADR-0022 quarantine — monthly-budget bypass


# ---------------------------------------------------------------------------
# Request / Result data-classes
# ---------------------------------------------------------------------------


@dataclass
class BudgetPermissionRequest:
    """All the data needed to check spend-time Budget Permission."""

    user_id: int
    category: models.ExpenseCategory
    amount: int
    expense_date: date
    subcategory: models.UserSubcategory | None = None
    project: models.Project | None = None
    project_subcategory: models.LegacyProjectSubcategory | None = None
    exclude_event_id: int | None = None
    enforce_monthly_budget_limits: bool = True


@dataclass
class BudgetPermissionResult:
    """The outcome of a successful Budget Permission check.

    Callers use the *budget* (for Entity Ledger linking) and may inspect
    *subcategory* / *project* / *project_subcategory* for their own linking.
    """

    budget: models.Budget | None
    subcategory: models.UserSubcategory | None
    project: models.Project | None
    project_subcategory: models.LegacyProjectSubcategory | None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def check_budget_permission(
    db: Session,
    request: BudgetPermissionRequest,
) -> BudgetPermissionResult:
    """Validate all spend-time Budget Permission rules for a proposed spend.

    On failure raises an HTTPException with a structured detail code
    (e.g. ``expenses.budget_required``, ``budgets.limit_exceeded``,
    ``budgets.subcategory_limit_exceeded``, ``budgets.project_category_not_part_of_project``).

    On success returns a :class:`BudgetPermissionResult` with the resolved
    *budget* row and the validated *subcategory* / *project* /
    *project_subcategory* references.
    """
    # ---- 1. Budget existence / materialization -------------------------------
    budget = _resolve_or_materialize_budget(
        db,
        request.user_id,
        request.category,
        request.expense_date,
        request.project,
        request.enforce_monthly_budget_limits,
    )

    # ---- 2. Project budget ---------------------------------------------------
    if request.project is not None:
        validate_project_budget(
            db,
            request.user_id,
            request.project,
            request.category,
            request.amount,
            request.expense_date,
            project_subcategory=request.project_subcategory,
            exclude_event_id=request.exclude_event_id,
        )

    return BudgetPermissionResult(
        budget=budget,
        subcategory=request.subcategory,
        project=request.project,
        project_subcategory=request.project_subcategory,
    )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _resolve_or_materialize_budget(
    db: Session,
    user_id: int,
    category: models.ExpenseCategory,
    expense_date: date,
    project: models.Project | None,
    enforce_monthly_budget_limits: bool,
) -> models.Budget | None:
    """Find or materialize the Budget row for the given category and month.

    Returns ``None`` when budget limits are not enforced (isolated projects
    or explicitly skipped).  Raises ``expenses.budget_required`` when no
    Budget can be found or materialized.
    """
    if not enforce_monthly_budget_limits:
        return None
    if project is not None and is_isolated_project(project):
        return None

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
    if budget is None:
        budget = materialize_budget_for_month(
            db, user_id, category, expense_date.year, expense_date.month
        )
    if budget is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="expenses.budget_required",
        )
    return budget
