from __future__ import annotations

from datetime import date

from fastapi import HTTPException, status
# pyrefly: ignore [missing-import]
from sqlalchemy import func
# pyrefly: ignore [missing-import]
from sqlalchemy.orm import Session

from .. import models, schemas


def get_project_type(project: models.Project) -> models.ProjectType:
    return project.project_type or models.ProjectType.OVERLAY


def is_isolated_project(project: models.Project) -> bool:
    return get_project_type(project) == models.ProjectType.ISOLATED


def is_overlay_project(project: models.Project) -> bool:
    return get_project_type(project) == models.ProjectType.OVERLAY


def get_project_funding_limit(project: models.Project) -> int | None:
    if project.isolated_detail is None or project.isolated_detail.funding_limit is None:
        return None
    return int(project.isolated_detail.funding_limit)


def get_project_target_estimate(project: models.Project) -> int | None:
    if project.overlay_detail is None or project.overlay_detail.target_estimate is None:
        return None
    return int(project.overlay_detail.target_estimate)


def ensure_project_typology_details(db: Session, project: models.Project) -> None:
    project_type = get_project_type(project)
    project.project_type = project_type
    if project_type == models.ProjectType.OVERLAY:
        if project.overlay_detail is None:
            project.overlay_detail = models.ProjectOverlayDetail(
                owner_id=project.owner_id,
                target_estimate=None,
            )
        if project.isolated_detail is not None:
            db.delete(project.isolated_detail)
        return

    if project.isolated_detail is None:
        project.isolated_detail = models.ProjectIsolatedDetail(
            owner_id=project.owner_id,
            funding_limit=None,
        )
    if project.overlay_detail is not None:
        db.delete(project.overlay_detail)


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
            models.Project.project_type == models.ProjectType.OVERLAY,
        )
        .first()
    )
    if not reservation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="projects.subcategory_not_found")
    return reservation


def get_overlay_parent_budget_or_400(
    db: Session,
    owner_id: int,
    *,
    category: models.ExpenseCategory,
    budget_year: int,
    budget_month: int,
) -> models.Budget:
    budget = (
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
    if budget is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="projects.category_budget_month_required")
    return budget


def validate_overlay_project_category_reservation(
    db: Session,
    owner_id: int,
    project: models.Project,
    *,
    category: models.ExpenseCategory,
    budget_year: int,
    budget_month: int,
    limit_amount: int,
    exclude_reservation_id: int | None = None,
) -> models.Budget:
    if is_isolated_project(project):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="projects.overlay_category_reservations_only",
        )

    budget = get_overlay_parent_budget_or_400(
        db,
        owner_id,
        category=category,
        budget_year=budget_year,
        budget_month=budget_month,
    )
    reserved_query = (
        db.query(func.coalesce(func.sum(models.ProjectCategoryMonthlyLimit.limit_amount), 0))
        .join(models.Project, models.Project.id == models.ProjectCategoryMonthlyLimit.project_id)
        .filter(
            models.Project.owner_id == owner_id,
            models.Project.project_type == models.ProjectType.OVERLAY,
            models.Project.status == models.ProjectStatus.ACTIVE,
            models.ProjectCategoryMonthlyLimit.category == category,
            models.ProjectCategoryMonthlyLimit.budget_year == budget_year,
            models.ProjectCategoryMonthlyLimit.budget_month == budget_month,
        )
    )
    if exclude_reservation_id is not None:
        reserved_query = reserved_query.filter(models.ProjectCategoryMonthlyLimit.id != exclude_reservation_id)
    existing_reserved = int(reserved_query.scalar() or 0)
    if existing_reserved + int(limit_amount) > int(budget.monthly_limit):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="projects.category_reservation_exceeds_parent_budget",
        )
    return budget


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
    if is_isolated_project(project):
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

    budget = get_overlay_parent_budget_or_400(
        db,
        owner_id,
        category=category,
        budget_year=budget_year,
        budget_month=budget_month,
    )
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

    reserved_query = (
        db.query(func.coalesce(func.sum(models.ProjectSubcategoryMonthlyLimit.limit_amount), 0))
        .join(models.Project, models.Project.id == models.ProjectSubcategoryMonthlyLimit.project_id)
        .filter(
            models.Project.owner_id == owner_id,
            models.Project.project_type == models.ProjectType.OVERLAY,
            models.Project.status == models.ProjectStatus.ACTIVE,
            models.ProjectSubcategoryMonthlyLimit.user_subcategory_id == subcategory.id,
            models.ProjectSubcategoryMonthlyLimit.budget_year == budget_year,
            models.ProjectSubcategoryMonthlyLimit.budget_month == budget_month,
        )
    )
    if exclude_reservation_id is not None:
        reserved_query = reserved_query.filter(models.ProjectSubcategoryMonthlyLimit.id != exclude_reservation_id)
    existing_reserved = int(reserved_query.scalar() or 0)
    if existing_reserved + int(limit_amount) > int(monthly_lane.monthly_limit):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="projects.subcategory_reservation_exceeds_monthly_lane",
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
    if not is_isolated_project(project):
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
    next_project_type: models.ProjectType,
    next_funding_limit: int | None,
    next_start_date: date,
    next_target_end_date: date | None,
) -> None:
    linked_count = count_project_linked_events(db, project.id)
    if linked_count > 0 and next_project_type != get_project_type(project):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="projects.isolation_locked")
    if next_project_type == models.ProjectType.OVERLAY and is_isolated_project(project) and len(project.subcategories) > 0:
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

    if next_project_type == models.ProjectType.ISOLATED:
        validate_project_limit_sum(next_funding_limit, list(project.category_limits))


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
    project_type = get_project_type(project)
    is_isolated = project_type == models.ProjectType.ISOLATED
    funding_limit = get_project_funding_limit(project)
    target_estimate = get_project_target_estimate(project)
    remaining = funding_limit - spent if funding_limit is not None else None
    remaining_funding = int(released_funding) - spent if released_funding is not None else None
    funding_shortfall = max(int(spent) - int(released_funding), 0) if released_funding is not None else 0
    progress_direction = "tick_down" if is_isolated else "tick_up"
    overlay = None
    isolated = None
    if is_isolated:
        isolated = schemas.ProjectIsolatedFinancialOut(
            funding_limit=funding_limit,
            released_funding=int(released_funding) if released_funding is not None else None,
            remaining_funding=remaining_funding,
            funding_shortfall=funding_shortfall,
        )
    else:
        overlay = schemas.ProjectOverlayFinancialOut(
            target_estimate=target_estimate,
            selected_month_reserved_amount=selected_month_reserved_amount,
            total_reserved_scope=total_reserved_scope,
        )
    return schemas.ProjectBudgetOut(
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


def migrate_overlay_project_slices(db: Session, project: models.Project, start_date: date, target_end_date: date | None) -> None:
    if is_isolated_project(project):
        return

    start_year = start_date.year
    start_month = start_date.month
    
    for limit in list(project.monthly_category_limits):
        is_before_start = (limit.budget_year < start_year) or (limit.budget_year == start_year and limit.budget_month < start_month)
        is_after_end = False
        if target_end_date is not None:
            end_year = target_end_date.year
            end_month = target_end_date.month
            is_after_end = (limit.budget_year > end_year) or (limit.budget_year == end_year and limit.budget_month > end_month)
            
        if is_before_start or is_after_end:
            db.delete(limit)
            
    for sub_limit in list(project.monthly_subcategory_limits):
        is_before_start = (sub_limit.budget_year < start_year) or (sub_limit.budget_year == start_year and sub_limit.budget_month < start_month)
        is_after_end = False
        if target_end_date is not None:
            end_year = target_end_date.year
            end_month = target_end_date.month
            is_after_end = (sub_limit.budget_year > end_year) or (sub_limit.budget_year == end_year and sub_limit.budget_month > end_month)
            
        if is_before_start or is_after_end:
            db.delete(sub_limit)

