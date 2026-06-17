from __future__ import annotations

from datetime import date

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app import models
from app.services.goal_funding_service import (
    get_wallet_goal_allocated_amount,
    get_wallet_required_goal_resolution_for_outflow,
    validate_wallet_goal_protection_for_outflow,
)
from app.services.wallet_service import WalletService


DEFAULT_BANK_FEE_BUDGET_LIMIT = 50_000


def resolve_or_create_bank_fee_budget(
    db: Session,
    user_id: int,
    fee_date: date,
) -> tuple[models.Budget, bool]:
    category = models.ExpenseCategory.BANK_FEES_INTEREST
    budget = (
        db.query(models.Budget)
        .filter(
            models.Budget.owner_id == user_id,
            models.Budget.category == category,
            models.Budget.budget_year == fee_date.year,
            models.Budget.budget_month == fee_date.month,
        )
        .with_for_update()
        .first()
    )
    if budget is not None:
        return budget, False

    budget = models.Budget(
        owner_id=user_id,
        category=category,
        budget_year=fee_date.year,
        budget_month=fee_date.month,
        monthly_limit=DEFAULT_BANK_FEE_BUDGET_LIMIT,
        auto_created=True,
    )
    db.add(budget)
    db.flush()
    return budget, True


def get_owned_fee_wallet_or_404(
    db: Session,
    user_id: int,
    wallet_id: int,
) -> models.Wallet:
    wallet = (
        db.query(models.Wallet)
        .filter(models.Wallet.id == wallet_id, models.Wallet.owner_id == user_id)
        .with_for_update()
        .first()
    )
    if wallet is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="wallets.not_found")
    if not wallet.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="wallets.archived_locked")
    if wallet.wallet_type == models.WalletType.CASH:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="wallets.action_not_supported_for_cash")
    return wallet


def validate_linked_fee_goal_protection(
    db: Session,
    user_id: int,
    fee_wallet: models.Wallet,
    fee_amount: int,
    *,
    primary_outflow_amount: int = 0,
    allowed_goal_resolution_amount: int = 0,
) -> None:
    if int(fee_amount or 0) <= 0:
        return

    if int(primary_outflow_amount or 0) > 0:
        protected_amount = get_wallet_goal_allocated_amount(db, user_id, fee_wallet.id)
        owned_balance = max(int(fee_wallet.current_balance or 0), 0)
        owned_after_primary = max(owned_balance - int(primary_outflow_amount or 0), 0)
        protected_after_allowed_resolution = max(
            int(protected_amount) - int(allowed_goal_resolution_amount or 0),
            0,
        )
        free_after_primary = max(owned_after_primary - protected_after_allowed_resolution, 0)
        if int(fee_amount) <= free_after_primary:
            return
        validate_wallet_goal_protection_for_outflow(
            db,
            user_id,
            fee_wallet,
            int(primary_outflow_amount or 0) + int(fee_amount),
            outflow_type="fee",
            error_code="wallets.fee_goal_protection_conflict",
        )
        return

    validate_wallet_goal_protection_for_outflow(
        db,
        user_id,
        fee_wallet,
        int(fee_amount),
        outflow_type="fee",
        error_code="wallets.fee_goal_protection_conflict",
    )


def record_linked_bank_fee_event(
    db: Session,
    *,
    user_id: int,
    wallet: models.Wallet,
    amount: int,
    fee_date: date,
    budget_id: int,
    linked_event_id: int,
    note: str | None = None,
) -> models.FinancialEvent:
    return WalletService.record_transaction(
        db=db,
        owner_id=user_id,
        wallet_id=wallet.id,
        transaction_type=models.TransactionType.EXPENSE,
        amount_delta=-int(amount),
        category=models.ExpenseCategory.BANK_FEES_INTEREST,
        title="Fee",
        description=note or "Fee",
        budget_id=budget_id,
        transaction_date=fee_date,
        linked_event_id=linked_event_id,
        reference_type=models.ReferenceType.BANK_FEE,
    )
