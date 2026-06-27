from __future__ import annotations

from dataclasses import dataclass
from datetime import date

# pyrefly: ignore [missing-import]
from sqlalchemy import and_, or_, select
# pyrefly: ignore [missing-import]
from sqlalchemy.orm import Session

from app import models
from app.services.obligation_source_service import regular_debt_obligation_filters


@dataclass(frozen=True)
class CategoryFloorReason:
    kind: str
    source_id: int
    title: str
    due_date: date
    amount: int


@dataclass(frozen=True)
class CategoryFloorWarning:
    category: models.ExpenseCategory
    suggested_minimum: int
    current_limit: int
    warning_gap: int
    reasons: list[CategoryFloorReason]

    # Compatibility names retained while Issue 5 migrates the frontend.
    @property
    def floor_amount(self) -> int:
        return self.suggested_minimum

    @property
    def effective_monthly_limit(self) -> int:
        return self.current_limit

    @property
    def shortfall(self) -> int:
        return self.warning_gap

    @property
    def sources(self) -> list[str]:
        legacy_names = {
            "DEFERRED_EXPENSE": "debt",
        }
        return sorted(
            {legacy_names.get(reason.kind, reason.kind.lower()) for reason in self.reasons}
        )


def build_category_floor_warnings(
    db: Session,
    owner_id: int,
    *,
    start: date,
    end: date,
    effective_limits: dict[models.ExpenseCategory, int],
    include_recurring: bool = True,
) -> list[CategoryFloorWarning]:
    """
    Build non-binding monthly category warnings from authoritative obligations.

    Issue 4 will replace the narrow recurring preview with the shared recurring
    occurrence projector. Keeping that adapter isolated prevents schedule rules
    from leaking into budget summary orchestration.
    """

    reasons_by_category: dict[models.ExpenseCategory, list[CategoryFloorReason]] = {}
    seen: set[tuple[str, int, date]] = set()

    def add_reason(
        category: models.ExpenseCategory | None,
        *,
        kind: str,
        source_id: int,
        title: str,
        due_date: date,
        amount: int,
    ) -> None:
        contribution = max(int(amount), 0)
        if category is None or contribution <= 0:
            return
        key = (kind, int(source_id), due_date)
        if key in seen:
            return
        seen.add(key)
        reasons_by_category.setdefault(category, []).append(
            CategoryFloorReason(
                kind=kind,
                source_id=int(source_id),
                title=title,
                due_date=due_date,
                amount=contribution,
            )
        )

    if include_recurring:
        from app.services.recurring_projection_service import project_occurrences_for_range
        from datetime import timedelta
        recurring_rows = (
            db.query(models.RecurringExpense)
            .filter(
                models.RecurringExpense.owner_id == owner_id,
                models.RecurringExpense.status == models.RecurringStatus.ACTIVE,
            )
            .all()
        )
        inclusive_end = end - timedelta(days=1)
        for recurring in recurring_rows:
            projected = project_occurrences_for_range(db, recurring, start, inclusive_end)
            for occ in projected:
                add_reason(
                    occ.category,
                    kind="RECURRING",
                    source_id=occ.source_id,
                    title=occ.title,
                    due_date=occ.due_date,
                    amount=occ.amount,
                )

    payment_plan_rows = (
        db.query(models.PaymentPlanPayment)
        .join(models.PaymentPlan, models.PaymentPlan.id == models.PaymentPlanPayment.plan_id)
        .filter(
            models.PaymentPlanPayment.owner_id == owner_id,
            models.PaymentPlan.owner_id == owner_id,
            models.PaymentPlan.status == models.PaymentPlanStatus.ACTIVE,
            models.PaymentPlanPayment.status.in_(
                [
                    models.PaymentPlanPaymentStatus.PENDING,
                    models.PaymentPlanPaymentStatus.PARTIAL,
                ]
            ),
            models.PaymentPlanPayment.due_date >= start,
            models.PaymentPlanPayment.due_date < end,
        )
        .all()
    )
    payment_plan_debt_ids = {
        int(payment.plan.debt_id)
        for payment in payment_plan_rows
        if payment.plan.debt_id is not None
    }
    for payment in payment_plan_rows:
        remaining = (
            int(payment.amount or 0)
            - int(payment.paid_amount or 0)
            - int(payment.written_off_amount or 0)
        )
        category = (
            models.ExpenseCategory.DEBT_CHARGES
            if payment.component_type == models.PaymentPlanPaymentComponentType.CHARGE
            else payment.plan.expense_category
        )
        add_reason(
            category,
            kind="PAYMENT_PLAN",
            source_id=payment.id,
            title=payment.plan.item_name,
            due_date=payment.due_date,
            amount=remaining,
        )

    formal_due_debt_ids = select(models.DebtFormalDetails.debt_id).filter(
        models.DebtFormalDetails.owner_id == owner_id,
        models.DebtFormalDetails.next_due_date >= start,
        models.DebtFormalDetails.next_due_date < end,
    )
    debt_rows = (
        db.query(models.Debt)
        .filter(
            models.Debt.owner_id == owner_id,
            models.Debt.debt_type == models.DebtType.OWING,
            *regular_debt_obligation_filters(owner_id),
            models.Debt.expense_category.isnot(None),
            or_(
                and_(models.Debt.expected_return_date >= start, models.Debt.expected_return_date < end),
                models.Debt.id.in_(formal_due_debt_ids),
            ),
        )
        .all()
    )
    for debt in debt_rows:
        if int(debt.id) in payment_plan_debt_ids:
            continue
        due_date = debt.expected_return_date
        if debt.formal_details is not None and debt.formal_details.next_due_date is not None:
            formal_due = debt.formal_details.next_due_date
            if start <= formal_due < end:
                due_date = formal_due
        if due_date is None:
            continue
        add_reason(
            debt.expense_category,
            kind=(
                "DEFERRED_EXPENSE"
                if debt.origin_kind == models.DebtOriginKind.DEFERRED_EXPENSE
                else "DEBT"
            ),
            source_id=debt.id,
            title=debt.counterparty_name,
            due_date=due_date,
            amount=int(debt.remaining_amount or 0),
        )

    warnings: list[CategoryFloorWarning] = []
    for category, reasons in sorted(reasons_by_category.items(), key=lambda item: str(item[0])):
        ordered_reasons = sorted(reasons, key=lambda reason: (reason.due_date, reason.kind, reason.source_id))
        suggested_minimum = sum(reason.amount for reason in ordered_reasons)
        current_limit = int(effective_limits.get(category, 0))
        warnings.append(
            CategoryFloorWarning(
                category=category,
                suggested_minimum=suggested_minimum,
                current_limit=current_limit,
                warning_gap=max(suggested_minimum - current_limit, 0),
                reasons=ordered_reasons,
            )
        )
    return warnings
