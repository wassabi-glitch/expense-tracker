from __future__ import annotations

from datetime import date, datetime, timezone

from fastapi import HTTPException, status
# pyrefly: ignore [missing-import]
from sqlalchemy import and_, case, func, or_
# pyrefly: ignore [missing-import]
from sqlalchemy.orm import Session, selectinload

from .. import models, schemas
from .wallet_service import WalletService


def get_project_type(project: models.Project) -> models.ProjectType:
    return project.project_type or models.ProjectType.OVERLAY


def is_isolated_project(project: models.Project) -> bool:
    return get_project_type(project) == models.ProjectType.ISOLATED


def is_overlay_project(project: models.Project) -> bool:
    return get_project_type(project) == models.ProjectType.OVERLAY


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


def get_project_deletion_preview(db: Session, project: models.Project) -> schemas.ProjectDeletionPreviewOut:
    linked_event_count = count_project_linked_events(db, project.id)
    expense_summary = (
        db.query(
            func.count(func.distinct(models.FinancialEvent.id)).label("expense_count"),
            func.coalesce(func.sum(models.EntityLedger.amount), 0).label("expense_total"),
        )
        .join(models.EntityLedger, models.EntityLedger.event_id == models.FinancialEvent.id)
        .filter(
            models.FinancialEvent.owner_id == project.owner_id,
            models.FinancialEvent.event_type == models.TransactionType.EXPENSE,
            models.FinancialEvent.status == models.FinancialEventStatus.POSTED,
            models.EntityLedger.project_id == project.id,
        )
        .first()
    )
    return schemas.ProjectDeletionPreviewOut(
        project_id=int(project.id),
        is_pristine=linked_event_count == 0,
        linked_expense_count=int(expense_summary.expense_count or 0) if expense_summary else 0,
        linked_expense_total=int(expense_summary.expense_total or 0) if expense_summary else 0,
    )


def validate_overlay_project_deletion_target(project: models.Project) -> None:
    if not is_overlay_project(project):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="projects.overlay_delete_only")


def delete_pristine_overlay_project(db: Session, project: models.Project) -> None:
    validate_overlay_project_deletion_target(project)
    preview = get_project_deletion_preview(db, project)
    if not preview.is_pristine:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "projects.delete_resolution_required",
                "linked_expense_count": preview.linked_expense_count,
                "linked_expense_total": preview.linked_expense_total,
            },
        )
    db.delete(project)


def detach_project_expenses_and_delete(db: Session, project: models.Project) -> None:
    validate_overlay_project_deletion_target(project)
    project_subcategory_ids = (
        db.query(models.LegacyProjectSubcategory.id)
        .filter(models.LegacyProjectSubcategory.project_id == project.id)
    )
    (
        db.query(models.EntityLedger)
        .filter(
            or_(
                models.EntityLedger.project_id == project.id,
                models.EntityLedger.project_subcategory_id.in_(project_subcategory_ids),
            )
        )
        .update(
            {
                models.EntityLedger.project_id: None,
                models.EntityLedger.project_subcategory_id: None,
            },
            synchronize_session=False,
        )
    )
    (
        db.query(models.ExpenseSessionDraftItem)
        .filter(
            or_(
                models.ExpenseSessionDraftItem.project_id == project.id,
                models.ExpenseSessionDraftItem.project_subcategory_id.in_(project_subcategory_ids),
            )
        )
        .update(
            {
                models.ExpenseSessionDraftItem.project_id: None,
                models.ExpenseSessionDraftItem.project_subcategory_id: None,
            },
            synchronize_session=False,
        )
    )
    db.delete(project)


def _project_linked_posted_expense_events(
    db: Session,
    owner_id: int,
    project_id: int,
) -> list[models.FinancialEvent]:
    return (
        db.query(models.FinancialEvent)
        .options(
            selectinload(models.FinancialEvent.wallet_legs).selectinload(models.WalletLedger.wallet),
            selectinload(models.FinancialEvent.entity_legs),
        )
        .join(models.EntityLedger, models.EntityLedger.event_id == models.FinancialEvent.id)
        .filter(
            models.FinancialEvent.owner_id == owner_id,
            models.FinancialEvent.event_type == models.TransactionType.EXPENSE,
            models.FinancialEvent.status == models.FinancialEventStatus.POSTED,
            models.EntityLedger.project_id == project_id,
        )
        .distinct()
        .all()
    )


def _validate_project_cascade_void_event(
    db: Session,
    owner_id: int,
    project_id: int,
    event: models.FinancialEvent,
) -> None:
    if event.is_session:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="projects.cascade_void_session_not_supported")
    if not event.entity_legs or any(leg.project_id != project_id for leg in event.entity_legs):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="projects.cascade_void_split_event_not_supported")
    for wallet_leg in event.wallet_legs:
        if wallet_leg.wallet and not wallet_leg.wallet.is_active:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="wallets.archived_locked")

    has_refund = (
        db.query(models.FinancialEvent.id)
        .filter(
            models.FinancialEvent.owner_id == owner_id,
            models.FinancialEvent.status == models.FinancialEventStatus.POSTED,
            models.FinancialEvent.event_type == models.TransactionType.REFUND,
            models.FinancialEvent.linked_event_id == event.id,
        )
        .first()
    )
    if has_refund:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="expenses.has_refund_lock")

    has_asset = (
        db.query(models.Asset.id)
        .filter(
            models.Asset.owner_id == owner_id,
            models.Asset.origin_event_id == event.id,
        )
        .first()
    )
    if has_asset:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="expenses.asset_link_lock")

    has_debt = (
        db.query(models.Debt.id)
        .filter(
            models.Debt.owner_id == owner_id,
            models.Debt.linked_event_id == event.id,
        )
        .first()
    )
    linked_entity_dependency = any(
        leg.debt_id or leg.payment_plan_id or leg.payment_plan_payment_id
        for leg in event.entity_legs
    )
    if has_debt or linked_entity_dependency:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="expenses.linked_dependency_lock")


def _append_expense_void_reversal(
    db: Session,
    owner_id: int,
    event: models.FinancialEvent,
    void_date: date,
) -> None:
    reversal = models.FinancialEvent(
        owner_id=owner_id,
        title=f"Void {event.title}",
        description=f"Reversal for cascade-voided project expense #{event.id}",
        event_type=event.event_type,
        status=models.FinancialEventStatus.REVERSAL,
        reference_type=models.ReferenceType.VOID_REVERSAL,
        is_session=False,
        linked_event_id=event.id,
        reverses_event_id=event.id,
        date=void_date,
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
            )
        )

    event.status = models.FinancialEventStatus.VOIDED
    event.voided_at = datetime.now(timezone.utc)
    event.void_reason = "Project cascade void"
    event.void_reversal_event_id = reversal.id


def cascade_void_project_expenses_and_delete(
    db: Session,
    owner_id: int,
    project: models.Project,
    *,
    void_date: date,
) -> None:
    validate_overlay_project_deletion_target(project)
    events = _project_linked_posted_expense_events(db, owner_id, project.id)
    for event in events:
        _validate_project_cascade_void_event(db, owner_id, project.id, event)
    for event in events:
        _append_expense_void_reversal(db, owner_id, event, void_date)
    db.flush()
    detach_project_expenses_and_delete(db, project)


def get_owned_project_subcategory_or_404(
    db: Session,
    owner_id: int,
    project_id: int,
    subcategory_id: int,
) -> models.LegacyProjectSubcategory:
    subcategory = (
        db.query(models.LegacyProjectSubcategory)
        .join(models.Project, models.Project.id == models.LegacyProjectSubcategory.project_id)
        .filter(
            models.LegacyProjectSubcategory.id == subcategory_id,
            models.LegacyProjectSubcategory.project_id == project_id,
            models.Project.owner_id == owner_id,
        )
        .first()
    )
    if not subcategory:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="projects.subcategory_not_found")
    return subcategory


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
    if next_project_type == models.ProjectType.OVERLAY and is_isolated_project(project) and len(project.legacy_subcategories) > 0:
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
        from .isolated_project_service import validate_project_limit_sum

        validate_project_limit_sum(next_funding_limit, list(project.isolated_category_allocations))


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
    from .isolated_project_service import (
        get_project_category_allocated_amount,
        get_project_funding_limit,
        get_project_wallet_allocated_amount,
        project_wallet_allocations_out,
    )
    from .overlay_project_service import get_project_target_estimate

    funding_limit = get_project_funding_limit(project)
    target_estimate = get_project_target_estimate(project)
    wallet_allocated = get_project_wallet_allocated_amount(project) if is_isolated else 0
    remaining = funding_limit - spent if funding_limit is not None else None
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
    overlay = None
    isolated = None
    if is_isolated:
        allocated_funding = get_project_category_allocated_amount(project)
        isolated = schemas.ProjectIsolatedFinancialOut(
            funding_limit=funding_limit,
            allocated_funding=allocated_funding,
            unallocated_funding=(
                max(int(funding_limit) - allocated_funding, 0)
                if funding_limit is not None
                else None
            ),
            released_funding=int(released_funding) if released_funding is not None else None,
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


