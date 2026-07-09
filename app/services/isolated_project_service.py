from __future__ import annotations

from fastapi import HTTPException, status
# pyrefly: ignore [missing-import]
from sqlalchemy import and_, case, func
# pyrefly: ignore [missing-import]
from sqlalchemy.orm import Session

from .. import models, schemas
from .goal_funding_service import get_wallet_goal_allocated_amount
from .wallet_value_service import owned_balance


PROJECT_FUNDING_LOCK_STATUSES = (
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


def get_project_wallet_allocated_amount(project: models.Project) -> int:
    return int(sum(int(item.amount or 0) for item in project.isolated_wallet_allocations))


def get_project_category_allocated_amount(project: models.Project) -> int:
    return int(sum(int(item.limit_amount or 0) for item in project.isolated_category_allocations))


def get_project_funding_limit(project: models.Project) -> int | None:
    wallet_allocated = get_project_wallet_allocated_amount(project)
    if wallet_allocated > 0:
        return wallet_allocated
    if project.isolated_detail is None or project.isolated_detail.funding_limit is None:
        return None
    return int(project.isolated_detail.funding_limit)


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
        db.query(func.coalesce(
            func.sum(models.IsolatedProjectWalletAllocation.amount), 0))
        .join(models.Project, models.Project.id == models.IsolatedProjectWalletAllocation.project_id)
        .filter(
            models.IsolatedProjectWalletAllocation.owner_id == owner_id,
            models.IsolatedProjectWalletAllocation.wallet_id == wallet_id,
            models.Project.status.in_(PROJECT_FUNDING_LOCK_STATUSES),
        )
    )
    if exclude_project_id is not None:
        query = query.filter(
            models.IsolatedProjectWalletAllocation.project_id != exclude_project_id)
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
    free_to_allocate = max(
        owned_amount - protected_for_goals - protected_for_projects, 0)
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
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="wallets.not_found")

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


def apply_isolated_project_top_up(
    db: Session,
    owner_id: int,
    project: models.Project,
    allocations: list[schemas.ProjectWalletAllocationCreate],
) -> None:
    if project.project_type != models.ProjectType.ISOLATED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="projects.isolated_required")
    if project.status != models.ProjectStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="projects.not_active")

    validated = validate_project_wallet_allocations(db, owner_id, allocations)
    requested_total = sum(amount for _, amount in validated)

    from .budget_service import get_free_money_now

    _, _, free_money_now = get_free_money_now(db, owner_id)
    if requested_total > free_money_now:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "projects.top_up_exceeds_free_money_now",
                "free_money_now": int(free_money_now),
                "requested_amount": int(requested_total),
            },
        )

    existing_by_wallet_id = {
        int(allocation.wallet_id): allocation
        for allocation in project.isolated_wallet_allocations
    }
    for wallet, amount in validated:
        existing = existing_by_wallet_id.get(int(wallet.id))
        if existing is None:
            db.add(
                models.IsolatedProjectWalletAllocation(
                    project_id=project.id,
                    owner_id=owner_id,
                    wallet_id=wallet.id,
                    amount=int(amount),
                )
            )
        else:
            existing.amount = int(existing.amount) + int(amount)


def apply_isolated_project_category_allocation(
    db: Session,
    project: models.Project,
    *,
    category: models.ExpenseCategory,
    allocated_amount: int,
) -> None:
    from app.domains.posting._category_policy import validate_active_expense_category  # lazy — avoids circular import

    if project.project_type != models.ProjectType.ISOLATED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="projects.isolated_required")
    if project.status != models.ProjectStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="projects.not_active")
    validate_active_expense_category(
        category,
        error_detail="projects.validation.real_expense_category_required",
    )

    unallocated = get_project_unallocated_funding_amount(project)
    if unallocated is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="projects.category_allocations_require_funding")
    if int(allocated_amount) > int(unallocated):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="projects.category_allocations_exceed_unassigned_funding",
        )

    existing = next(
        (item for item in project.isolated_category_allocations if item.category == category), None)
    if existing is None:
        db.add(
            models.IsolatedProjectCategoryAllocation(
                project_id=project.id,
                category=category,
                limit_amount=int(allocated_amount),
            )
        )
    else:
        existing.limit_amount = int(
            existing.limit_amount) + int(allocated_amount)


def get_isolated_project_subcategory_spent_amount(
    db: Session,
    owner_id: int,
    project_id: int,
    user_subcategory_id: int,
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
            models.EntityLedger.subcategory_id == user_subcategory_id,
            models.FinancialEvent.event_type.in_(
                [models.TransactionType.EXPENSE, models.TransactionType.REFUND]
            ),
        )
    )
    if exclude_event_id is not None:
        query = query.filter(models.FinancialEvent.id != exclude_event_id)
    return int(query.scalar() or 0)


def _resolve_user_subcategory(
    db: Session,
    owner_id: int,
    *,
    category: models.ExpenseCategory,
    name: str | None,
    user_subcategory_id: int | None,
) -> models.UserSubcategory:
    if user_subcategory_id is not None:
        user_subcategory = (
            db.query(models.UserSubcategory)
            .filter(
                models.UserSubcategory.id == int(user_subcategory_id),
                models.UserSubcategory.owner_id == owner_id,
                models.UserSubcategory.category == category,
            )
            .first()
        )
        if user_subcategory is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="projects.subcategory_not_found")
        return user_subcategory

    if name is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="projects.subcategory_identity_required")
    name_clean = name.strip()
    user_subcategory = (
        db.query(models.UserSubcategory)
        .filter(
            models.UserSubcategory.owner_id == owner_id,
            models.UserSubcategory.category == category,
            func.lower(models.UserSubcategory.name) == name_clean.lower(),
        )
        .first()
    )
    if user_subcategory is not None:
        return user_subcategory

    user_subcategory = models.UserSubcategory(
        owner_id=owner_id,
        category=category,
        name=name_clean,
        is_active=True,
    )
    db.add(user_subcategory)
    db.flush()
    return user_subcategory


def apply_isolated_project_subcategory_allocation(
    db: Session,
    owner_id: int,
    project: models.Project,
    *,
    category: models.ExpenseCategory,
    allocated_amount: int,
    name: str | None = None,
    user_subcategory_id: int | None = None,
) -> None:
    from app.domains.posting._category_policy import validate_active_expense_category  # lazy — avoids circular import

    if project.project_type != models.ProjectType.ISOLATED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="projects.isolated_required")
    if project.status != models.ProjectStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="projects.not_active")
    validate_active_expense_category(
        category,
        error_detail="projects.validation.real_expense_category_required",
    )

    parent_alloc = next(
        (item for item in project.isolated_category_allocations if item.category == category), None)
    if parent_alloc is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="projects.isolated_subcategory_parent_category_not_allocated",
        )

    user_subcategory = _resolve_user_subcategory(
        db,
        owner_id,
        category=category,
        name=name,
        user_subcategory_id=user_subcategory_id,
    )
    existing = (
        db.query(models.IsolatedProjectSubcategoryAllocation)
        .filter(
            models.IsolatedProjectSubcategoryAllocation.project_id == project.id,
            models.IsolatedProjectSubcategoryAllocation.user_subcategory_id == user_subcategory.id,
            models.IsolatedProjectSubcategoryAllocation.archived_at.is_(None),
        )
        .first()
    )
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="projects.subcategory_already_exists")

    current_allocated = (
        db.query(func.coalesce(
            func.sum(models.IsolatedProjectSubcategoryAllocation.allocated_amount), 0))
        .filter(
            models.IsolatedProjectSubcategoryAllocation.project_id == project.id,
            models.IsolatedProjectSubcategoryAllocation.category == category,
            models.IsolatedProjectSubcategoryAllocation.archived_at.is_(None),
        )
        .scalar()
    )
    if int(current_allocated or 0) + int(allocated_amount) > int(parent_alloc.limit_amount):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="projects.isolated_subcategory_limit_exceeds_category",
        )

    db.add(
        models.IsolatedProjectSubcategoryAllocation(
            project_id=project.id,
            category_allocation_id=parent_alloc.id,
            category=category,
            user_subcategory_id=user_subcategory.id,
            allocated_amount=int(allocated_amount),
            is_active=True,
        )
    )


def apply_isolated_project_rebalance(
    db: Session,
    owner_id: int,
    project: models.Project,
    payload: schemas.ProjectRebalanceRequest,
) -> None:
    from app.domains.posting._category_policy import validate_active_expense_category  # lazy — avoids circular import

    if project.project_type != models.ProjectType.ISOLATED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="projects.isolated_required")
    if project.status != models.ProjectStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="projects.not_active")

    amount = int(payload.amount)
    if payload.scope == "CATEGORY":
        validate_active_expense_category(
            payload.from_category,
            error_detail="projects.validation.real_expense_category_required",
        )
        validate_active_expense_category(
            payload.to_category,
            error_detail="projects.validation.real_expense_category_required",
        )
        source = next(
            (item for item in project.isolated_category_allocations if item.category ==
             payload.from_category),
            None,
        )
        if source is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail="projects.category_limit_not_found")
        destination = next(
            (item for item in project.isolated_category_allocations if item.category ==
             payload.to_category),
            None,
        )
        if amount > int(source.limit_amount):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail="projects.rebalance_amount_exceeds_source")
        next_source_amount = int(source.limit_amount) - amount
        validate_isolated_project_category_allocation_covers_spending(
            db,
            owner_id,
            project,
            payload.from_category,
            next_source_amount,
        )
        active_micro_allocated = int(
            db.query(func.coalesce(
                func.sum(models.IsolatedProjectSubcategoryAllocation.allocated_amount), 0))
            .filter(
                models.IsolatedProjectSubcategoryAllocation.project_id == project.id,
                models.IsolatedProjectSubcategoryAllocation.category == payload.from_category,
                models.IsolatedProjectSubcategoryAllocation.archived_at.is_(
                    None),
            )
            .scalar()
            or 0
        )
        if next_source_amount < active_micro_allocated:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="projects.subcategory_allocations_exceed_category",
            )
        if destination is None:
            db.add(
                models.IsolatedProjectCategoryAllocation(
                    project_id=project.id,
                    category=payload.to_category,
                    limit_amount=amount,
                )
            )
        else:
            destination.limit_amount = int(destination.limit_amount) + amount
        if next_source_amount == 0:
            db.delete(source)
        else:
            source.limit_amount = next_source_amount
        return

    source_subcategory = (
        db.query(models.IsolatedProjectSubcategoryAllocation)
        .filter(
            models.IsolatedProjectSubcategoryAllocation.id == payload.from_subcategory_allocation_id,
            models.IsolatedProjectSubcategoryAllocation.project_id == project.id,
            models.IsolatedProjectSubcategoryAllocation.archived_at.is_(None),
        )
        .first()
    )
    destination_subcategory = (
        db.query(models.IsolatedProjectSubcategoryAllocation)
        .filter(
            models.IsolatedProjectSubcategoryAllocation.id == payload.to_subcategory_allocation_id,
            models.IsolatedProjectSubcategoryAllocation.project_id == project.id,
            models.IsolatedProjectSubcategoryAllocation.archived_at.is_(None),
        )
        .first()
    )
    if source_subcategory is None or destination_subcategory is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="projects.subcategory_not_found")
    if source_subcategory.category != destination_subcategory.category:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="projects.subcategory_category_mismatch")
    if amount > int(source_subcategory.allocated_amount):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="projects.rebalance_amount_exceeds_source")

    next_source_amount = int(source_subcategory.allocated_amount) - amount
    spent = get_isolated_project_subcategory_spent_amount(
        db,
        owner_id,
        int(project.id),
        int(source_subcategory.user_subcategory_id),
    )
    if next_source_amount < spent:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="projects.subcategory_allocation_below_spent")

    destination_subcategory.allocated_amount = int(
        destination_subcategory.allocated_amount) + amount
    if next_source_amount == 0:
        db.delete(source_subcategory)
    else:
        source_subcategory.allocated_amount = next_source_amount


def project_wallet_allocation_out(
    allocation: models.IsolatedProjectWalletAllocation,
) -> schemas.ProjectWalletAllocationOut:
    return schemas.ProjectWalletAllocationOut(
        id=int(allocation.id),
        project_id=int(allocation.project_id),
        wallet_id=int(allocation.wallet_id),
        amount=int(allocation.amount),
        wallet=schemas.WalletOut.model_validate(
            allocation.wallet) if allocation.wallet else None,
        created_at=allocation.created_at,
        updated_at=allocation.updated_at,
    )


def project_wallet_allocations_out(
    project: models.Project,
) -> list[schemas.ProjectWalletAllocationOut]:
    return [
        project_wallet_allocation_out(item)
        for item in sorted(
            project.isolated_wallet_allocations,
            key=lambda allocation: (
                allocation.created_at,
                int(allocation.id or 0),
            ),
        )
    ]


def validate_project_limit_sum(
    total_limit: int | None,
    category_allocations: list[models.IsolatedProjectCategoryAllocation],
    incoming_limit: int | None = None,
    exclude_category: models.ExpenseCategory | None = None,
) -> None:
    if total_limit is None:
        return
    running_total = 0
    for item in category_allocations:
        if exclude_category is not None and item.category == exclude_category:
            continue
        running_total += int(item.limit_amount)
    if incoming_limit is not None:
        running_total += int(incoming_limit)
    if running_total > int(total_limit):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="projects.category_limits_exceed_total")


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
    spent = get_isolated_project_category_spent_amount(
        db, owner_id, int(project.id), category)
    if int(limit_amount) < spent:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="projects.category_allocation_below_spent",
        )


def get_isolated_project_total_spent(
    db: Session,
    owner_id: int,
    project_id: int,
) -> int:
    signed_amount = _signed_posted_expense_amount()
    return int(
        db.query(func.coalesce(func.sum(signed_amount), 0))
        .select_from(models.EntityLedger)
        .join(models.FinancialEvent, models.FinancialEvent.id == models.EntityLedger.event_id)
        .filter(
            models.FinancialEvent.owner_id == owner_id,
            models.FinancialEvent.status == models.FinancialEventStatus.POSTED,
            models.EntityLedger.project_id == project_id,
            models.FinancialEvent.event_type.in_(
                [models.TransactionType.EXPENSE, models.TransactionType.REFUND]
            ),
        )
        .scalar()
    )


def get_isolated_project_total_top_ups(
    db: Session,
    project: models.Project,
) -> int:
    initial = int(
        project.isolated_detail.funding_limit or 0) if project.isolated_detail else 0
    current = get_project_wallet_allocated_amount(project)
    return max(0, current - initial)


def sweep_isolated_project_wallet_allocations(
    db: Session,
    owner_id: int,
    project: models.Project,
) -> int:
    project_id = int(project.id)
    total_funding = get_project_wallet_allocated_amount(project)
    total_spent = get_isolated_project_total_spent(db, owner_id, project_id)
    sweep_amount = max(total_funding - total_spent, 0)
    for allocation in list(project.isolated_wallet_allocations):
        db.delete(allocation)
    project.isolated_wallet_allocations = []
    db.flush()
    return int(sweep_amount)


def get_isolated_project_wrap_up_summary(
    db: Session,
    owner_id: int,
    project: models.Project,
) -> dict:
    project_id = int(project.id)
    total_funding = get_project_wallet_allocated_amount(project)
    total_top_ups = get_isolated_project_total_top_ups(db, project)
    total_spent = get_isolated_project_total_spent(db, owner_id, project_id)
    sweep_amount = max(total_funding - total_spent, 0)
    overrun = max(total_spent - total_funding, 0)

    category_rows = []
    for alloc in sorted(project.isolated_category_allocations, key=lambda a: a.category.value):
        cat_spent = get_isolated_project_category_spent_amount(
            db, owner_id, project_id, alloc.category
        )
        category_rows.append({
            "category": alloc.category.value,
            "allocated_amount": int(alloc.limit_amount or 0),
            "spent_amount": cat_spent,
            "remaining": max(int(alloc.limit_amount or 0) - cat_spent, 0),
        })

    category_rows.sort(key=lambda r: r["allocated_amount"], reverse=True)

    subcategory_rows = []
    for sub in sorted(
        project.isolated_subcategory_allocations,
        key=lambda s: (s.category.value if s.category else "",
                       int(s.allocated_amount or 0)),
        reverse=True,
    ):
        sub_spent = get_isolated_project_subcategory_spent_amount(
            db, owner_id, project_id, int(sub.user_subcategory_id)
        )
        subcategory_rows.append({
            "id": int(sub.id),
            "category": sub.category.value if sub.category else "",
            "name": sub.user_subcategory.name if sub.user_subcategory else "",
            "allocated_amount": int(sub.allocated_amount or 0),
            "spent_amount": sub_spent,
        })
    subcategory_rows.sort(key=lambda r: r["spent_amount"], reverse=True)

    return {
        "project_id": project_id,
        "project_title": project.title,
        "total_funding": total_funding,
        "total_top_ups": total_top_ups,
        "total_spent": total_spent,
        "remaining_funding": max(total_funding - total_spent, 0),
        "overrun_amount": overrun,
        "sweep_amount": sweep_amount if overrun == 0 else 0,
        "is_overrun": overrun > 0,
        "top_categories": category_rows,
        "top_subcategories": subcategory_rows,
    }
