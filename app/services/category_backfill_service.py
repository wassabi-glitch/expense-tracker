from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session, selectinload

from app import models
from app.services.budget_service import recompute_budget_chain


@dataclass(frozen=True)
class LegacyCategoryManualReviewItem:
    entity_ledger_id: int
    event_id: int
    reason: str


@dataclass(frozen=True)
class LegacyCategoryBackfillResult:
    scanned_count: int
    migrated_count: int
    budget_rebound_count: int
    manual_review: list[LegacyCategoryManualReviewItem]

    @property
    def manual_review_count(self) -> int:
        return len(self.manual_review)


CHARGE_REFERENCE_TYPES = {
    models.ReferenceType.DEBT_CHARGE,
    models.ReferenceType.PAYMENT_PLAN_FEE,
    models.ReferenceType.PAYMENT_PLAN_PENALTY,
}


def _is_real_expense_category(category: models.ExpenseCategory | None) -> bool:
    return category is not None and category != models.ExpenseCategory.PAYMENT_PLANS_DEBT


def _matching_budget_id(
    db: Session,
    *,
    owner_id: int,
    category: models.ExpenseCategory,
    event_date,
) -> int | None:
    budget = (
        db.query(models.Budget)
        .filter(
            models.Budget.owner_id == owner_id,
            models.Budget.category == category,
            models.Budget.budget_year == event_date.year,
            models.Budget.budget_month == event_date.month,
        )
        .first()
    )
    return int(budget.id) if budget is not None else None


def _payment_plan_payment_target_category(
    payment: models.PaymentPlanPayment | None,
) -> models.ExpenseCategory | None:
    if payment is None:
        return None
    if payment.component_type == models.PaymentPlanPaymentComponentType.CHARGE:
        return models.ExpenseCategory.DEBT_CHARGES
    if payment.plan is not None and _is_real_expense_category(payment.plan.expense_category):
        return payment.plan.expense_category
    return None


def _target_category_for_legacy_row(
    leg: models.EntityLedger,
    event: models.FinancialEvent,
) -> tuple[models.ExpenseCategory | None, str | None]:
    if event.reference_type in CHARGE_REFERENCE_TYPES:
        return models.ExpenseCategory.DEBT_CHARGES, None

    payment_category = _payment_plan_payment_target_category(leg.payment_plan_payment)
    if payment_category is not None:
        return payment_category, None

    if leg.payment_plan is not None:
        if _is_real_expense_category(leg.payment_plan.expense_category):
            return leg.payment_plan.expense_category, None
        return None, "linked_payment_plan_has_no_real_category"

    if leg.debt is not None:
        if _is_real_expense_category(leg.debt.expense_category):
            return leg.debt.expense_category, None
        return None, "linked_debt_has_no_real_category"

    return None, "no_safe_category_source"


def backfill_deprecated_financing_category_rows(
    db: Session,
    *,
    owner_id: int | None = None,
) -> LegacyCategoryBackfillResult:
    query = (
        db.query(models.EntityLedger)
        .options(
            selectinload(models.EntityLedger.event),
            selectinload(models.EntityLedger.debt),
            selectinload(models.EntityLedger.payment_plan),
            selectinload(models.EntityLedger.payment_plan_payment).selectinload(models.PaymentPlanPayment.plan),
        )
        .join(models.FinancialEvent, models.FinancialEvent.id == models.EntityLedger.event_id)
        .filter(models.EntityLedger.category == models.ExpenseCategory.PAYMENT_PLANS_DEBT)
        .order_by(models.EntityLedger.id.asc())
    )
    if owner_id is not None:
        query = query.filter(models.FinancialEvent.owner_id == owner_id)

    rows = query.all()
    migrated_count = 0
    budget_rebound_count = 0
    manual_review: list[LegacyCategoryManualReviewItem] = []
    touched_categories_by_owner: set[tuple[int, models.ExpenseCategory]] = set()

    for leg in rows:
        event = leg.event
        if event is None:
            manual_review.append(
                LegacyCategoryManualReviewItem(
                    entity_ledger_id=int(leg.id),
                    event_id=int(leg.event_id),
                    reason="missing_financial_event",
                )
            )
            continue

        target_category, reason = _target_category_for_legacy_row(leg, event)
        if target_category is None:
            manual_review.append(
                LegacyCategoryManualReviewItem(
                    entity_ledger_id=int(leg.id),
                    event_id=int(event.id),
                    reason=reason or "no_safe_category_source",
                )
            )
            continue

        new_budget_id = _matching_budget_id(
            db,
            owner_id=int(event.owner_id),
            category=target_category,
            event_date=event.date,
        )
        if leg.budget_id != new_budget_id:
            budget_rebound_count += 1

        leg.category = target_category
        leg.budget_id = new_budget_id
        migrated_count += 1
        touched_categories_by_owner.add((int(event.owner_id), models.ExpenseCategory.PAYMENT_PLANS_DEBT))
        touched_categories_by_owner.add((int(event.owner_id), target_category))

    db.flush()
    for touched_owner_id, category in touched_categories_by_owner:
        recompute_budget_chain(db, touched_owner_id, category)

    return LegacyCategoryBackfillResult(
        scanned_count=len(rows),
        migrated_count=migrated_count,
        budget_rebound_count=budget_rebound_count,
        manual_review=manual_review,
    )
