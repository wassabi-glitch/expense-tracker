from __future__ import annotations

from datetime import date

from fastapi import HTTPException, status
from sqlalchemy import and_, case, func
from sqlalchemy.orm import Session

from .. import models
from .project_service import is_isolated_project, is_overlay_project


OVERLAY_RESERVATION_HOLDING_STATUSES = (
    models.ProjectStatus.ACTIVE,
    models.ProjectStatus.STOPPED,
)


def _signed_posted_expense_amount():
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


def get_project_target_estimate(project: models.Project) -> int | None:
    if project.overlay_detail is None or project.overlay_detail.target_estimate is None:
        return None
    return int(project.overlay_detail.target_estimate)


def _overlay_project_spent_by_category_month(
    db: Session,
    owner_id: int,
    project_id: int,
) -> dict[tuple[int, int, models.ExpenseCategory], int]:
    signed_amount = _signed_posted_expense_amount()
    rows = (
        db.query(
            func.extract("year", models.FinancialEvent.date).label("budget_year"),
            func.extract("month", models.FinancialEvent.date).label("budget_month"),
            models.EntityLedger.category,
            func.coalesce(func.sum(signed_amount), 0).label("spent"),
        )
        .select_from(models.EntityLedger)
        .join(models.FinancialEvent, models.FinancialEvent.id == models.EntityLedger.event_id)
        .filter(
            models.FinancialEvent.owner_id == owner_id,
            models.FinancialEvent.status == models.FinancialEventStatus.POSTED,
            models.FinancialEvent.event_type.in_(
                [models.TransactionType.EXPENSE, models.TransactionType.REFUND]
            ),
            models.EntityLedger.project_id == project_id,
            models.EntityLedger.category.isnot(None),
        )
        .group_by(
            func.extract("year", models.FinancialEvent.date),
            func.extract("month", models.FinancialEvent.date),
            models.EntityLedger.category,
        )
        .all()
    )
    return {
        (int(year), int(month), category): int(spent or 0)
        for year, month, category, spent in rows
        if category is not None
    }


def _overlay_project_spent_by_subcategory_month(
    db: Session,
    owner_id: int,
    project_id: int,
) -> dict[tuple[int, int, int], int]:
    signed_amount = _signed_posted_expense_amount()
    rows = (
        db.query(
            func.extract("year", models.FinancialEvent.date).label("budget_year"),
            func.extract("month", models.FinancialEvent.date).label("budget_month"),
            models.EntityLedger.subcategory_id,
            func.coalesce(func.sum(signed_amount), 0).label("spent"),
        )
        .select_from(models.EntityLedger)
        .join(models.FinancialEvent, models.FinancialEvent.id == models.EntityLedger.event_id)
        .filter(
            models.FinancialEvent.owner_id == owner_id,
            models.FinancialEvent.status == models.FinancialEventStatus.POSTED,
            models.FinancialEvent.event_type.in_(
                [models.TransactionType.EXPENSE, models.TransactionType.REFUND]
            ),
            models.EntityLedger.project_id == project_id,
            models.EntityLedger.subcategory_id.isnot(None),
        )
        .group_by(
            func.extract("year", models.FinancialEvent.date),
            func.extract("month", models.FinancialEvent.date),
            models.EntityLedger.subcategory_id,
        )
        .all()
    )
    return {
        (int(year), int(month), int(subcategory_id)): int(spent or 0)
        for year, month, subcategory_id, spent in rows
        if subcategory_id is not None
    }


def _is_current_or_future_month(row_year: int, row_month: int, anchor_date: date) -> bool:
    return (int(row_year), int(row_month)) >= (anchor_date.year, anchor_date.month)


def _swept_limit_amount(planned_amount: int, actual_spent: int) -> int:
    return min(int(planned_amount), max(int(actual_spent), 0))


def sweep_overlay_project_reservations(
    db: Session,
    owner_id: int,
    project: models.Project,
    *,
    anchor_date: date,
) -> None:
    if not is_overlay_project(project):
        return

    spent_by_category = _overlay_project_spent_by_category_month(db, owner_id, project.id)
    for reservation in list(project.overlay_category_reservations):
        if not _is_current_or_future_month(
            int(reservation.budget_year),
            int(reservation.budget_month),
            anchor_date,
        ):
            continue
        actual_spent = spent_by_category.get(
            (
                int(reservation.budget_year),
                int(reservation.budget_month),
                reservation.category,
            ),
            0,
        )
        swept_amount = _swept_limit_amount(int(reservation.limit_amount), actual_spent)
        if swept_amount <= 0:
            db.delete(reservation)
        else:
            reservation.limit_amount = swept_amount

    spent_by_subcategory = _overlay_project_spent_by_subcategory_month(db, owner_id, project.id)
    for reservation in list(project.overlay_subcategory_reservations):
        if not _is_current_or_future_month(
            int(reservation.budget_year),
            int(reservation.budget_month),
            anchor_date,
        ):
            continue
        actual_spent = spent_by_subcategory.get(
            (
                int(reservation.budget_year),
                int(reservation.budget_month),
                int(reservation.user_subcategory_id),
            ),
            0,
        )
        swept_amount = _swept_limit_amount(int(reservation.limit_amount), actual_spent)
        if swept_amount <= 0:
            db.delete(reservation)
        else:
            reservation.limit_amount = swept_amount


def get_owned_project_subcategory_reservation_or_404(
    db: Session,
    owner_id: int,
    project_id: int,
    reservation_id: int,
) -> models.OverlayProjectSubcategoryReservation:
    reservation = (
        db.query(models.OverlayProjectSubcategoryReservation)
        .join(models.Project, models.Project.id == models.OverlayProjectSubcategoryReservation.project_id)
        .filter(
            models.OverlayProjectSubcategoryReservation.id == reservation_id,
            models.OverlayProjectSubcategoryReservation.project_id == project_id,
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
        db.query(func.coalesce(func.sum(models.OverlayProjectCategoryReservation.limit_amount), 0))
        .join(models.Project, models.Project.id == models.OverlayProjectCategoryReservation.project_id)
        .filter(
            models.Project.owner_id == owner_id,
            models.Project.project_type == models.ProjectType.OVERLAY,
            models.Project.status.in_(OVERLAY_RESERVATION_HOLDING_STATUSES),
            models.OverlayProjectCategoryReservation.category == category,
            models.OverlayProjectCategoryReservation.budget_year == budget_year,
            models.OverlayProjectCategoryReservation.budget_month == budget_month,
        )
    )
    if exclude_reservation_id is not None:
        reserved_query = reserved_query.filter(models.OverlayProjectCategoryReservation.id != exclude_reservation_id)
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

    project_category_reservation = (
        db.query(models.OverlayProjectCategoryReservation)
        .filter(
            models.OverlayProjectCategoryReservation.project_id == project.id,
            models.OverlayProjectCategoryReservation.category == category,
            models.OverlayProjectCategoryReservation.budget_year == budget_year,
            models.OverlayProjectCategoryReservation.budget_month == budget_month,
        )
        .first()
    )
    if project_category_reservation is None:
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
        db.query(func.coalesce(func.sum(models.OverlayProjectSubcategoryReservation.limit_amount), 0))
        .join(models.Project, models.Project.id == models.OverlayProjectSubcategoryReservation.project_id)
        .filter(
            models.Project.owner_id == owner_id,
            models.Project.project_type == models.ProjectType.OVERLAY,
            models.Project.status.in_(OVERLAY_RESERVATION_HOLDING_STATUSES),
            models.OverlayProjectSubcategoryReservation.user_subcategory_id == subcategory.id,
            models.OverlayProjectSubcategoryReservation.budget_year == budget_year,
            models.OverlayProjectSubcategoryReservation.budget_month == budget_month,
        )
    )
    if exclude_reservation_id is not None:
        reserved_query = reserved_query.filter(models.OverlayProjectSubcategoryReservation.id != exclude_reservation_id)
    existing_reserved = int(reserved_query.scalar() or 0)
    if existing_reserved + int(limit_amount) > int(monthly_lane.monthly_limit):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="projects.subcategory_reservation_exceeds_monthly_lane",
        )

    duplicate = (
        db.query(models.OverlayProjectSubcategoryReservation)
        .filter(
            models.OverlayProjectSubcategoryReservation.project_id == project.id,
            models.OverlayProjectSubcategoryReservation.user_subcategory_id == subcategory.id,
            models.OverlayProjectSubcategoryReservation.budget_year == budget_year,
            models.OverlayProjectSubcategoryReservation.budget_month == budget_month,
        )
    )
    if exclude_reservation_id is not None:
        duplicate = duplicate.filter(models.OverlayProjectSubcategoryReservation.id != exclude_reservation_id)
    if duplicate.first() is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="projects.subcategory_exists")

    return subcategory


def migrate_overlay_project_slices(db: Session, project: models.Project, start_date: date, target_end_date: date | None) -> None:
    if is_isolated_project(project):
        return

    start_year = start_date.year
    start_month = start_date.month

    for reservation in list(project.overlay_category_reservations):
        is_before_start = (reservation.budget_year < start_year) or (
            reservation.budget_year == start_year and reservation.budget_month < start_month
        )
        is_after_end = False
        if target_end_date is not None:
            end_year = target_end_date.year
            end_month = target_end_date.month
            is_after_end = (reservation.budget_year > end_year) or (
                reservation.budget_year == end_year and reservation.budget_month > end_month
            )

        if is_before_start or is_after_end:
            db.delete(reservation)

    for reservation in list(project.overlay_subcategory_reservations):
        is_before_start = (reservation.budget_year < start_year) or (
            reservation.budget_year == start_year and reservation.budget_month < start_month
        )
        is_after_end = False
        if target_end_date is not None:
            end_year = target_end_date.year
            end_month = target_end_date.month
            is_after_end = (reservation.budget_year > end_year) or (
                reservation.budget_year == end_year and reservation.budget_month > end_month
            )

        if is_before_start or is_after_end:
            db.delete(reservation)
