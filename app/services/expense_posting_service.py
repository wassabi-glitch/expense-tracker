from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Iterable

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app import models
from app.services.budget_service import (
    materialize_budget_for_month,
    recompute_budget_chain,
    validate_project_budget,
)
from app.services.category_policy import validate_active_expense_category
from app.services.goal_funding_service import validate_wallet_goal_protection_for_outflow
from app.services.isolated_project_service import validate_isolated_project_wallet_spend
from app.services.project_service import is_isolated_project
from app.services.session_draft_service import validate_session_item_links
from app.services.wallet_service import WalletService
from app.services.wallet_value_service import classify_outflow


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


def resolve_expense_budget(
    db: Session,
    user_id: int,
    category: models.ExpenseCategory,
    expense_date: date,
) -> models.Budget:
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
        budget = materialize_budget_for_month(db, user_id, category, expense_date.year, expense_date.month)
    if budget is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="expenses.budget_required")
    return budget


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
    legacy_project_subcategory = (
        project_subcategory
        if isinstance(project_subcategory, models.LegacyProjectSubcategory)
        else None
    )
    isolated_project_subcategory = (
        project_subcategory
        if isinstance(project_subcategory, models.IsolatedProjectSubcategoryAllocation)
        else None
    )

    budget = None
    if project is None or not is_isolated_project(project):
        budget = resolve_expense_budget(db, user_id, category, expense_date)

    if project is not None:
        validate_project_budget(
            db,
            user_id,
            project,
            category,
            int(amount),
            expense_date,
            project_subcategory=project_subcategory,
        )
        if is_isolated_project(project):
            validate_isolated_project_wallet_spend(
                db,
                user_id,
                project,
                resolved_wallet_allocations,
            )

    event = models.FinancialEvent(
        owner_id=user_id,
        title=title,
        description=description,
        event_type=models.TransactionType.EXPENSE,
        reference_type=reference_type,
        is_session=is_session,
        date=expense_date,
    )
    db.add(event)
    db.flush()

    is_bypass_category = category == models.ExpenseCategory.BANK_FEES_INTEREST
    for wallet, allocation_amount in resolved_wallet_allocations:
        funding = classify_outflow(wallet, int(allocation_amount))
        WalletService.adjust_balance(
            db,
            wallet.id,
            -int(allocation_amount),
            models.TransactionType.EXPENSE,
            is_bypass=is_bypass_category,
        )
        db.add(
            models.WalletLedger(
                owner_id=user_id,
                event_id=event.id,
                wallet_id=wallet.id,
                amount=-int(allocation_amount),
                owned_spend_amount=funding.owned_amount,
                borrowed_spend_amount=funding.borrowed_amount,
            )
        )

    db.add(
        models.EntityLedger(
            event_id=event.id,
            label=title,
            amount=int(amount),
            category=category,
            budget_id=budget.id if budget is not None else None,
            subcategory_id=subcategory.id if subcategory is not None else None,
            project_id=project.id if project is not None else None,
            project_subcategory_id=legacy_project_subcategory.id if legacy_project_subcategory is not None else None,
            isolated_project_subcategory_id=(
                isolated_project_subcategory.id
                if isolated_project_subcategory is not None
                else None
            ),
            debt_id=debt_id,
            payment_plan_id=payment_plan_id,
            payment_plan_payment_id=payment_plan_payment_id,
        )
    )
    db.flush()
    recompute_budget_chain(db, user_id, category)

    return ExpensePostingResult(
        event=event,
        budget=budget,
        wallet_allocations=resolved_wallet_allocations,
        subcategory=subcategory,
        project=project,
        project_subcategory=project_subcategory,
    )
