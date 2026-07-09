from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Iterable

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app import models
from app.domains.budget_permission._permission_service import (
    BudgetPermissionRequest,
    check_budget_permission,
)
from app.domains.budget_reporting._budget_service import recompute_budget_chain
from app.domains.posting._category_policy import validate_active_expense_category
from app.domains.ledger._ledger_service import (
    PostEntityLeg,
    PostWalletLeg,
    post_financial_event,
)
from app.services.goal_funding_service import validate_wallet_goal_protection_for_outflow
from app.services.session_draft_service import validate_session_item_links


@dataclass
class ExpensePostingResult:
    event: models.FinancialEvent
    budget: models.Budget | None
    wallet_allocations: list[tuple[models.Wallet, int]]
    subcategory: models.UserSubcategory | None
    project: models.Project | None
    project_subcategory: models.LegacyProjectSubcategory | None


def validate_real_expense_category(category: models.ExpenseCategory) -> None:
    validate_active_expense_category(
        category,
        error_detail="expenses.validation.real_expense_category_required",
    )


def _get_owned_wallet_or_404(db: Session, user_id: int, wallet_id: int) -> models.Wallet:
    wallet = (
        db.query(models.Wallet)
        .filter(models.Wallet.id == wallet_id, models.Wallet.owner_id == user_id)
        .with_for_update()
        .first()
    )
    if wallet is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="wallets.not_found")
    return wallet


def _allocation_value(allocation, key: str):
    if hasattr(allocation, key):
        return getattr(allocation, key)
    return allocation[key]


def resolve_expense_wallet_allocations(
    db: Session,
    user_id: int,
    *,
    amount: int,
    wallet_id: int | None = None,
    wallet_allocations: Iterable | None = None,
) -> list[tuple[models.Wallet, int]]:
    raw_allocations = list(wallet_allocations or [])

    if not raw_allocations:
        if wallet_id is not None:
            raw_allocations = [{"wallet_id": wallet_id, "amount": amount}]
        else:
            wallet = (
                db.query(models.Wallet)
                .filter(models.Wallet.owner_id == user_id, models.Wallet.is_default)
                .with_for_update()
                .first()
            )
            if wallet is None:
                wallet = (
                    db.query(models.Wallet)
                    .filter(models.Wallet.owner_id == user_id)
                    .with_for_update()
                    .first()
                )
            if wallet is None:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="wallets.at_least_one_required")
            raw_allocations = [{"wallet_id": wallet.id, "amount": amount}]

    total_allocated = int(sum(int(_allocation_value(item, "amount")) for item in raw_allocations))
    if total_allocated != int(amount):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="expenses.wallet_allocation_total_mismatch")

    seen_wallet_ids: set[int] = set()
    resolved: list[tuple[models.Wallet, int]] = []
    for allocation in raw_allocations:
        allocation_wallet_id = int(_allocation_value(allocation, "wallet_id"))
        allocation_amount = int(_allocation_value(allocation, "amount"))
        if allocation_wallet_id in seen_wallet_ids:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="expenses.wallet_allocation_duplicate")
        seen_wallet_ids.add(allocation_wallet_id)

        wallet = _get_owned_wallet_or_404(db, user_id, allocation_wallet_id)
        if not wallet.is_active:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="wallets.archived_locked")
        resolved.append((wallet, allocation_amount))

    return resolved


def post_expense_event(
    db: Session,
    user_id: int,
    *,
    title: str,
    amount: int,
    category: models.ExpenseCategory,
    expense_date: date,
    description: str | None = None,
    wallet_id: int | None = None,
    wallet_allocations: Iterable | None = None,
    subcategory_id: int | None = None,
    project_id: int | None = None,
    project_subcategory_id: int | None = None,
    reference_type: str | None = None,
    is_session: bool = False,
    local_today: date | None = None,
    enforce_goal_protection: bool = True,
    enforce_monthly_budget_limits: bool = True,
    debt_id: int | None = None,
    payment_plan_id: int | None = None,
    payment_plan_payment_id: int | None = None,
) -> ExpensePostingResult:
    if local_today is not None and expense_date > local_today:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="expenses.date_in_future")

    validate_real_expense_category(category)

    resolved_wallet_allocations = resolve_expense_wallet_allocations(
        db,
        user_id,
        amount=int(amount),
        wallet_id=wallet_id,
        wallet_allocations=wallet_allocations,
    )

    if enforce_goal_protection:
        for wallet, allocation_amount in resolved_wallet_allocations:
            validate_wallet_goal_protection_for_outflow(
                db,
                user_id,
                wallet,
                allocation_amount,
                outflow_type="expense",
            )

    subcategory, project, project_subcategory = validate_session_item_links(
        db,
        user_id,
        category,
        subcategory_id,
        project_id,
        project_subcategory_id,
    )

    permission = check_budget_permission(
        db,
        BudgetPermissionRequest(
            user_id=user_id,
            category=category,
            amount=int(amount),
            expense_date=expense_date,
            subcategory=subcategory,
            project=project,
            project_subcategory=project_subcategory,
            enforce_monthly_budget_limits=enforce_monthly_budget_limits,
        ),
    )
    budget = permission.budget

    wallet_legs: list[PostWalletLeg] = []
    for wallet, allocation_amount in resolved_wallet_allocations:
        wallet_legs.append(
            PostWalletLeg(
                wallet_id=wallet.id,
                amount=-int(allocation_amount),
            )
        )

    entity_legs: list[PostEntityLeg] = [
        PostEntityLeg(
            label=title,
            amount=int(amount),
            category=category,
            budget_id=budget.id if budget is not None else None,
            subcategory_id=subcategory.id if subcategory is not None else None,
            project_id=project.id if project is not None else None,
            project_subcategory_id=project_subcategory.id if project_subcategory is not None else None,
            debt_id=debt_id,
            payment_plan_id=payment_plan_id,
            payment_plan_payment_id=payment_plan_payment_id,
        )
    ]

    event = post_financial_event(
        db,
        owner_id=user_id,
        title=title,
        event_type=models.TransactionType.EXPENSE,
        date=expense_date,
        description=description,
        reference_type=reference_type,
        is_session=is_session,
        entity_category=category,
        wallet_legs=wallet_legs,
        entity_legs=entity_legs,
    )

    recompute_budget_chain(db, user_id, category)

    return ExpensePostingResult(
        event=event,
        budget=budget,
        wallet_allocations=resolved_wallet_allocations,
        subcategory=subcategory,
        project=project,
        project_subcategory=project_subcategory,
    )
