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
        db.query(func.coalesce(func.sum(models.IsolatedProjectWalletAllocation.amount), 0))
        .join(models.Project, models.Project.id == models.IsolatedProjectWalletAllocation.project_id)
        .filter(
            models.IsolatedProjectWalletAllocation.owner_id == owner_id,
            models.IsolatedProjectWalletAllocation.wallet_id == wallet_id,
            models.Project.status.in_(PROJECT_FUNDING_LOCK_STATUSES),
        )
    )
    if exclude_project_id is not None:
        query = query.filter(models.IsolatedProjectWalletAllocation.project_id != exclude_project_id)
    return int(query.scalar() or 0)


def get_isolated_project_wallet_funding_amount(
    db: Session,
    owner_id: int,
    project_id: int,
    wallet_id: int,
) -> int:
    return int(
        db.query(func.coalesce(func.sum(models.IsolatedProjectWalletAllocation.amount), 0))
        .filter(
            models.IsolatedProjectWalletAllocation.owner_id == owner_id,
            models.IsolatedProjectWalletAllocation.project_id == project_id,
            models.IsolatedProjectWalletAllocation.wallet_id == wallet_id,
        )
        .scalar()
        or 0
    )


def get_isolated_project_wallet_spent_amount(
    db: Session,
    owner_id: int,
    project_id: int,
    wallet_id: int,
    *,
    exclude_event_id: int | None = None,
) -> int:
    project_event_ids = (
        db.query(models.EntityLedger.event_id)
        .filter(models.EntityLedger.project_id == project_id)
        .distinct()
        .subquery()
    )
    query = (
        db.query(func.coalesce(func.sum(-models.WalletLedger.amount), 0))
        .join(models.FinancialEvent, models.FinancialEvent.id == models.WalletLedger.event_id)
        .join(project_event_ids, project_event_ids.c.event_id == models.FinancialEvent.id)
        .filter(
            models.FinancialEvent.owner_id == owner_id,
            models.FinancialEvent.status == models.FinancialEventStatus.POSTED,
            models.FinancialEvent.event_type.in_(
                [models.TransactionType.EXPENSE, models.TransactionType.REFUND]
            ),
            models.WalletLedger.owner_id == owner_id,
            models.WalletLedger.wallet_id == wallet_id,
        )
    )
    if exclude_event_id is not None:
        query = query.filter(models.FinancialEvent.id != exclude_event_id)
    return int(query.scalar() or 0)


def get_isolated_project_wallet_remaining_amount(
    db: Session,
    owner_id: int,
    project_id: int,
    wallet_id: int,
    *,
    exclude_event_id: int | None = None,
) -> tuple[int, int, int]:
    funded = get_isolated_project_wallet_funding_amount(db, owner_id, project_id, wallet_id)
    spent = get_isolated_project_wallet_spent_amount(
        db,
        owner_id,
        project_id,
        wallet_id,
        exclude_event_id=exclude_event_id,
    )
    return funded, spent, max(funded - spent, 0)


def validate_isolated_project_wallet_spend(
    db: Session,
    owner_id: int,
    project: models.Project,
    wallet_allocations: list[tuple[models.Wallet, int]],
    *,
    exclude_event_id: int | None = None,
) -> None:
    for wallet, amount in wallet_allocations:
        funded, spent, remaining = get_isolated_project_wallet_remaining_amount(
            db,
            owner_id,
            int(project.id),
            int(wallet.id),
            exclude_event_id=exclude_event_id,
        )
        if funded <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "code": "projects.wallet_funding_required",
                    "project_id": int(project.id),
                    "wallet_id": int(wallet.id),
                    "wallet_name": wallet.name,
                    "requested_amount": int(amount),
                    "funded_amount": funded,
                    "spent_amount": spent,
                    "remaining_amount": remaining,
                },
            )
        if int(amount) > remaining:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "code": "projects.wallet_funding_exceeded",
                    "project_id": int(project.id),
                    "wallet_id": int(wallet.id),
                    "wallet_name": wallet.name,
                    "requested_amount": int(amount),
                    "funded_amount": funded,
                    "spent_amount": spent,
                    "remaining_amount": remaining,
                },
            )


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
    allocation: models.IsolatedProjectWalletAllocation,
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
