from __future__ import annotations

from datetime import date

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from .. import models, schemas


def count_project_linked_events(db: Session, project_id: int) -> int:
    return int(
        db.query(func.count(func.distinct(models.EntityLedger.event_id)))
        .filter(models.EntityLedger.project_id == project_id)
        .scalar()
        or 0
    )


def earliest_project_event_date(db: Session, project_id: int) -> date | None:
    return (
        db.query(func.min(models.FinancialEvent.date))
        .join(models.EntityLedger, models.EntityLedger.event_id == models.FinancialEvent.id)
        .filter(models.EntityLedger.project_id == project_id)
        .scalar()
    )


def latest_project_event_date(db: Session, project_id: int) -> date | None:
    return (
        db.query(func.max(models.FinancialEvent.date))
        .join(models.EntityLedger, models.EntityLedger.event_id == models.FinancialEvent.id)
        .filter(models.EntityLedger.project_id == project_id)
        .scalar()
    )


def validate_project_limit_sum(
    total_limit: int | None,
    category_limits: list[models.ProjectCategoryLimit],
    incoming_limit: int | None = None,
    exclude_category: models.ExpenseCategory | None = None,
) -> None:
    if total_limit is None:
        return
    running_total = 0
    for item in category_limits:
        if exclude_category is not None and item.category == exclude_category:
            continue
        running_total += int(item.limit_amount)
    if incoming_limit is not None:
        running_total += int(incoming_limit)
    if running_total > int(total_limit):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="projects.category_limits_exceed_total")


def get_owned_project_subcategory_or_404(
    db: Session,
    owner_id: int,
    project_id: int,
    subcategory_id: int,
) -> models.ProjectSubcategory:
    subcategory = (
        db.query(models.ProjectSubcategory)
        .join(models.Project, models.Project.id == models.ProjectSubcategory.project_id)
        .filter(
            models.ProjectSubcategory.id == subcategory_id,
            models.ProjectSubcategory.project_id == project_id,
            models.Project.owner_id == owner_id,
        )
        .first()
    )
    if not subcategory:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="projects.subcategory_not_found")
    return subcategory


def get_owned_project_subcategory_monthly_limit_or_404(
    db: Session,
    owner_id: int,
    project_id: int,
    reservation_id: int,
) -> models.ProjectSubcategoryMonthlyLimit:
    reservation = (
        db.query(models.ProjectSubcategoryMonthlyLimit)
        .join(models.Project, models.Project.id == models.ProjectSubcategoryMonthlyLimit.project_id)
        .filter(
            models.ProjectSubcategoryMonthlyLimit.id == reservation_id,
            models.ProjectSubcategoryMonthlyLimit.project_id == project_id,
            models.Project.owner_id == owner_id,
            models.Project.is_isolated == False,  # noqa: E712
        )
        .first()
    )
    if not reservation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="projects.subcategory_not_found")
    return reservation


def validate_overlay_project_subcategory_reservation(
    db: Session,
    owner_id: int,
    project: models.Project,
    *,
    category: models.ExpenseCategory,
    user_subcategory_id: int,
    budget_year: int,
    budget_month: int,
    limit_amount: int,
    exclude_reservation_id: int | None = None,
) -> models.UserSubcategory:
    if project.is_isolated:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="projects.overlay_subcategories_only",
        )

    project_category_limit = (
        db.query(models.ProjectCategoryMonthlyLimit)
        .filter(
            models.ProjectCategoryMonthlyLimit.project_id == project.id,
            models.ProjectCategoryMonthlyLimit.category == category,
            models.ProjectCategoryMonthlyLimit.budget_year == budget_year,
            models.ProjectCategoryMonthlyLimit.budget_month == budget_month,
        )
        .first()
    )
    if project_category_limit is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="projects.category_limit_required_for_subcategories",
        )

    subcategory = (
        db.query(models.UserSubcategory)
        .filter(
            models.UserSubcategory.id == user_subcategory_id,
            models.UserSubcategory.owner_id == owner_id,
        )
        .first()
    )
    if subcategory is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="budgets.subcategory_not_found")
    if subcategory.category != category:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="projects.subcategory_category_mismatch")
    if not subcategory.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="projects.subcategory_inactive")

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
    if budget is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="projects.subcategory_monthly_lane_required")
    monthly_lane = (
        db.query(models.BudgetSubcategoryLimit)
        .filter(
            models.BudgetSubcategoryLimit.owner_id == owner_id,
            models.BudgetSubcategoryLimit.budget_id == budget.id,
            models.BudgetSubcategoryLimit.subcategory_id == subcategory.id,
        )
        .first()
    )
    if monthly_lane is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="projects.subcategory_monthly_lane_required")
    if int(limit_amount) > int(monthly_lane.monthly_limit):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="projects.subcategory_limit_exceeds_monthly_lane",
        )

    duplicate = (
        db.query(models.ProjectSubcategoryMonthlyLimit)
        .filter(
            models.ProjectSubcategoryMonthlyLimit.project_id == project.id,
            models.ProjectSubcategoryMonthlyLimit.user_subcategory_id == subcategory.id,
            models.ProjectSubcategoryMonthlyLimit.budget_year == budget_year,
            models.ProjectSubcategoryMonthlyLimit.budget_month == budget_month,
        )
    )
    if exclude_reservation_id is not None:
        duplicate = duplicate.filter(models.ProjectSubcategoryMonthlyLimit.id != exclude_reservation_id)
    if duplicate.first() is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="projects.subcategory_exists")

    return subcategory


def validate_project_subcategory_rules(
    project: models.Project,
    category: models.ExpenseCategory,
) -> None:
    if not project.is_isolated:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="projects.subcategories_isolated_only",
        )
    category_limit = next((item for item in project.category_limits if item.category == category), None)
    if category_limit is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="projects.category_limit_required_for_subcategories",
        )


def validate_project_subcategory_limit_sum(
    project: models.Project,
    category: models.ExpenseCategory,
    incoming_limit: int | None = None,
    exclude_subcategory_id: int | None = None,
) -> None:
    category_limit = next((item for item in project.category_limits if item.category == category), None)
    if category_limit is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="projects.category_limit_required_for_subcategories",
        )
    running_total = 0
    for item in project.subcategories:
        if item.category != category:
            continue
        if exclude_subcategory_id is not None and int(item.id) == int(exclude_subcategory_id):
            continue
        if item.limit_amount is not None:
            running_total += int(item.limit_amount)
    if incoming_limit is not None:
        running_total += int(incoming_limit)
    if running_total > int(category_limit.limit_amount):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="projects.subcategory_limits_exceed_category",
        )


def validate_project_editable(project: models.Project) -> None:
    if project.status == models.ProjectStatus.COMPLETED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="projects.completed_read_only")
    if project.status == models.ProjectStatus.ARCHIVED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="projects.archived_read_only")


def validate_project_update_rules(
    db: Session,
    project: models.Project,
    *,
    next_is_isolated: bool,
    next_total_limit: int | None,
    next_start_date: date,
    next_target_end_date: date | None,
) -> None:
    linked_count = count_project_linked_events(db, project.id)
    if linked_count > 0 and next_is_isolated != bool(project.is_isolated):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="projects.isolation_locked")
    if not next_is_isolated and project.is_isolated and len(project.subcategories) > 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="projects.subcategories_isolated_only")

    earliest_linked_date = earliest_project_event_date(db, project.id)
    if earliest_linked_date is not None and next_start_date > earliest_linked_date:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="projects.start_after_linked_expense")

    if next_target_end_date is not None and next_target_end_date < next_start_date:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="projects.target_end_before_start")

    latest_linked_date = latest_project_event_date(db, project.id)
    if (
        latest_linked_date is not None
        and next_target_end_date is not None
        and next_target_end_date < latest_linked_date
    ):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="projects.end_before_linked_expense")

    if next_is_isolated:
        validate_project_limit_sum(next_total_limit, list(project.category_limits))


def validate_project_completion_date(project: models.Project, completion_date: date) -> None:
    if completion_date < project.start_date:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="projects.completed_before_start")


def build_project_detail(
    project: models.Project,
    spent: int,
    category_breakdown: list[schemas.ProjectBudgetCategoryDetailOut],
    released_funding: int | None = None,
    selected_budget_year: int | None = None,
    selected_budget_month: int | None = None,
    selected_month_reserved_amount: int = 0,
    total_reserved_scope: int = 0,
) -> schemas.ProjectBudgetOut:
    remaining = int(project.total_limit) - spent if project.total_limit is not None else None
    remaining_funding = int(released_funding) - spent if released_funding is not None else None
    funding_shortfall = max(int(spent) - int(released_funding), 0) if released_funding is not None else 0
    progress_direction = "tick_down" if project.is_isolated else "tick_up"
    return schemas.ProjectBudgetOut(
        id=project.id,
        owner_id=project.owner_id,
        title=project.title,
        description=project.description,
        is_isolated=project.is_isolated,
        total_limit=int(project.total_limit) if project.total_limit is not None else None,
        status=project.status,
        origin_goal_id=project.origin_goal_id,
        start_date=project.start_date,
        target_end_date=project.target_end_date,
        completed_at=project.completed_at,
        spent=spent,
        released_funding=int(released_funding) if released_funding is not None else None,
        remaining_funding=remaining_funding,
        funding_shortfall=funding_shortfall,
        progress_direction=progress_direction,
        remaining=remaining,
        is_over_limit=remaining is not None and remaining < 0,
        selected_budget_year=selected_budget_year,
        selected_budget_month=selected_budget_month,
        selected_month_reserved_amount=selected_month_reserved_amount,
        total_reserved_scope=total_reserved_scope,
        category_breakdown=category_breakdown,
        created_at=project.created_at,
        updated_at=project.updated_at,
    )
