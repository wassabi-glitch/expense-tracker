from __future__ import annotations

from datetime import date, datetime, timezone

from fastapi import HTTPException, status
# pyrefly: ignore [missing-import]
from sqlalchemy import and_, case, func, or_
# pyrefly: ignore [missing-import]
from sqlalchemy.orm import Session, selectinload

from .. import models, schemas
from .goal_funding_service import get_wallet_goal_allocated_amount
from .wallet_service import WalletService
from .wallet_value_service import owned_balance


OVERLAY_RESERVATION_HOLDING_STATUSES = (
    models.ProjectStatus.ACTIVE,
    models.ProjectStatus.STOPPED,
)

PROJECT_FUNDING_LOCK_STATUSES = (
    models.ProjectStatus.ACTIVE,
    models.ProjectStatus.STOPPED,
)


def get_project_type(project: models.Project) -> models.ProjectType:
    return project.project_type or models.ProjectType.OVERLAY


def is_isolated_project(project: models.Project) -> bool:
    return get_project_type(project) == models.ProjectType.ISOLATED


def is_overlay_project(project: models.Project) -> bool:
    return get_project_type(project) == models.ProjectType.OVERLAY


def get_project_funding_limit(project: models.Project) -> int | None:
    wallet_allocated = get_project_wallet_allocated_amount(project)
    if wallet_allocated > 0:
        return wallet_allocated
    if project.isolated_detail is None or project.isolated_detail.funding_limit is None:
        return None
    return int(project.isolated_detail.funding_limit)


def get_project_wallet_allocated_amount(project: models.Project) -> int:
    return int(sum(int(item.amount or 0) for item in project.wallet_allocations))


def get_project_category_allocated_amount(project: models.Project) -> int:
    return int(sum(int(item.limit_amount or 0) for item in project.category_limits))


def get_project_unallocated_funding_amount(project: models.Project) -> int | None:
    funding_limit = get_project_funding_limit(project)
    if funding_limit is None:
        return None
    return max(int(funding_limit) - get_project_category_allocated_amount(project), 0)


def get_wallet_project_allocated_amount(
    db: Session,
    owner_id: int,
    wallet_id: int,
    *,
    exclude_project_id: int | None = None,
) -> int:
    query = (
        db.query(func.coalesce(func.sum(models.ProjectWalletAllocation.amount), 0))
        .join(models.Project, models.Project.id == models.ProjectWalletAllocation.project_id)
        .filter(
            models.ProjectWalletAllocation.owner_id == owner_id,
            models.ProjectWalletAllocation.wallet_id == wallet_id,
            models.Project.status.in_(PROJECT_FUNDING_LOCK_STATUSES),
        )
    )
    if exclude_project_id is not None:
        query = query.filter(models.ProjectWalletAllocation.project_id != exclude_project_id)
    return int(query.scalar() or 0)


def get_wallet_free_to_allocate_for_projects(
    db: Session,
    owner_id: int,
    wallet: models.Wallet,
    *,
    exclude_project_id: int | None = None,
) -> tuple[int, int, int, int]:
    owned_amount = owned_balance(wallet)
    protected_for_goals = min(
        get_wallet_goal_allocated_amount(db, owner_id, int(wallet.id)),
        owned_amount,
    )
    protected_for_projects = min(
        get_wallet_project_allocated_amount(
            db,
            owner_id,
            int(wallet.id),
            exclude_project_id=exclude_project_id,
        ),
        max(owned_amount - protected_for_goals, 0),
    )
    free_to_allocate = max(owned_amount - protected_for_goals - protected_for_projects, 0)
    return (
        int(owned_amount),
        int(protected_for_goals),
        int(protected_for_projects),
        int(free_to_allocate),
    )


def validate_project_wallet_allocations(
    db: Session,
    owner_id: int,
    allocations: list[schemas.ProjectWalletAllocationCreate],
    *,
    exclude_project_id: int | None = None,
) -> list[tuple[models.Wallet, int]]:
    seen_wallet_ids: set[int] = set()
    validated: list[tuple[models.Wallet, int]] = []
    for item in allocations:
        wallet_id = int(item.wallet_id)
        amount = int(item.amount)
        if wallet_id in seen_wallet_ids:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="projects.wallet_allocation_duplicate",
            )
        seen_wallet_ids.add(wallet_id)
        wallet = (
            db.query(models.Wallet)
            .filter(
                models.Wallet.id == wallet_id,
                models.Wallet.owner_id == owner_id,
                models.Wallet.is_active == True,  # noqa: E712
            )
            .first()
        )
        if wallet is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="wallets.not_found")

        (
            owned_amount,
            protected_for_goals,
            protected_for_projects,
            free_to_allocate,
        ) = get_wallet_free_to_allocate_for_projects(
            db,
            owner_id,
            wallet,
            exclude_project_id=exclude_project_id,
        )
        if amount > free_to_allocate:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "code": "projects.wallet_allocation_exceeds_free_money",
                    "wallet_id": wallet_id,
                    "wallet_name": wallet.name,
                    "currency": wallet.currency,
                    "wallet_balance": int(wallet.current_balance or 0),
                    "owned_balance": owned_amount,
                    "protected_for_goals": protected_for_goals,
                    "protected_for_projects": protected_for_projects,
                    "free_to_allocate": free_to_allocate,
                    "requested_amount": amount,
                },
            )
        validated.append((wallet, amount))
    return validated


def project_wallet_allocation_out(
    allocation: models.ProjectWalletAllocation,
) -> schemas.ProjectWalletAllocationOut:
    return schemas.ProjectWalletAllocationOut(
        id=int(allocation.id),
        project_id=int(allocation.project_id),
        wallet_id=int(allocation.wallet_id),
        amount=int(allocation.amount),
        wallet=schemas.WalletOut.model_validate(allocation.wallet) if allocation.wallet else None,
        created_at=allocation.created_at,
        updated_at=allocation.updated_at,
    )


def project_wallet_allocations_out(
    project: models.Project,
) -> list[schemas.ProjectWalletAllocationOut]:
    return [
        project_wallet_allocation_out(item)
        for item in sorted(
            project.wallet_allocations,
            key=lambda allocation: (
                allocation.created_at,
                int(allocation.id or 0),
            ),
        )
    ]


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
    for reservation in list(project.monthly_category_limits):
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
    for reservation in list(project.monthly_subcategory_limits):
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
        db.query(models.ProjectSubcategory.id)
        .filter(models.ProjectSubcategory.project_id == project.id)
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


def get_isolated_project_category_spent_amount(
    db: Session,
    owner_id: int,
    project_id: int,
    category: models.ExpenseCategory,
    *,
    exclude_event_id: int | None = None,
) -> int:
    signed_amount = _signed_posted_expense_amount()
    query = (
        db.query(func.coalesce(func.sum(signed_amount), 0))
        .select_from(models.EntityLedger)
        .join(models.FinancialEvent, models.FinancialEvent.id == models.EntityLedger.event_id)
        .filter(
            models.FinancialEvent.owner_id == owner_id,
            models.FinancialEvent.status == models.FinancialEventStatus.POSTED,
            models.EntityLedger.project_id == project_id,
            models.EntityLedger.category == category,
            models.FinancialEvent.event_type.in_(
                [models.TransactionType.EXPENSE, models.TransactionType.REFUND]
            ),
        )
    )
    if exclude_event_id is not None:
        query = query.filter(models.FinancialEvent.id != exclude_event_id)
    return int(query.scalar() or 0)


def validate_isolated_project_category_allocation_covers_spending(
    db: Session,
    owner_id: int,
    project: models.Project,
    category: models.ExpenseCategory,
    limit_amount: int,
) -> None:
    spent = get_isolated_project_category_spent_amount(db, owner_id, int(project.id), category)
    if int(limit_amount) < spent:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="projects.category_allocation_below_spent",
        )


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
            models.Project.status.in_(OVERLAY_RESERVATION_HOLDING_STATUSES),
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
            models.Project.status.in_(OVERLAY_RESERVATION_HOLDING_STATUSES),
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

