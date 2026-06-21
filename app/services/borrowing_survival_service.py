from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from sqlalchemy import func
from sqlalchemy.orm import Session

from app import models


@dataclass(frozen=True)
class BorrowingSurvivalSummary:
    enabled: bool
    monthly_cap: int
    borrowed_usage: int
    remaining_cap: int
    exceeded_amount: int


def get_or_build_summary(
    db: Session,
    owner_id: int,
    *,
    budget_year: int,
    budget_month: int,
    start: date,
    end: date,
) -> BorrowingSurvivalSummary:
    plan = (
        db.query(models.BorrowingSurvivalPlan)
        .filter(
            models.BorrowingSurvivalPlan.owner_id == owner_id,
            models.BorrowingSurvivalPlan.budget_year == budget_year,
            models.BorrowingSurvivalPlan.budget_month == budget_month,
        )
        .first()
    )
    borrowed_usage = int(
        db.query(func.coalesce(func.sum(models.WalletLedger.borrowed_spend_amount), 0))
        .join(models.FinancialEvent, models.FinancialEvent.id == models.WalletLedger.event_id)
        .filter(
            models.WalletLedger.owner_id == owner_id,
            models.FinancialEvent.owner_id == owner_id,
            models.FinancialEvent.status == models.FinancialEventStatus.POSTED,
            models.FinancialEvent.event_type == models.TransactionType.EXPENSE,
            models.FinancialEvent.date >= start,
            models.FinancialEvent.date < end,
        )
        .scalar()
        or 0
    )
    enabled = bool(plan.enabled) if plan is not None else False
    monthly_cap = int(plan.monthly_cap or 0) if plan is not None else 0
    remaining_cap = max(monthly_cap - borrowed_usage, 0) if enabled else 0
    exceeded_amount = max(borrowed_usage - monthly_cap, 0) if enabled else 0
    return BorrowingSurvivalSummary(
        enabled=enabled,
        monthly_cap=monthly_cap,
        borrowed_usage=borrowed_usage,
        remaining_cap=remaining_cap,
        exceeded_amount=exceeded_amount,
    )


def upsert_plan(
    db: Session,
    owner_id: int,
    *,
    budget_year: int,
    budget_month: int,
    enabled: bool,
    monthly_cap: int,
) -> models.BorrowingSurvivalPlan:
    plan = (
        db.query(models.BorrowingSurvivalPlan)
        .filter(
            models.BorrowingSurvivalPlan.owner_id == owner_id,
            models.BorrowingSurvivalPlan.budget_year == budget_year,
            models.BorrowingSurvivalPlan.budget_month == budget_month,
        )
        .with_for_update()
        .first()
    )
    if plan is None:
        plan = models.BorrowingSurvivalPlan(
            owner_id=owner_id,
            budget_year=budget_year,
            budget_month=budget_month,
        )
        db.add(plan)
    plan.enabled = bool(enabled)
    plan.monthly_cap = int(monthly_cap)
    db.flush()
    return plan
