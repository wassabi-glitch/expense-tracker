from typing import List
# pyrefly: ignore [missing-import]
from sqlalchemy.orm import Session
from app import models, schemas
from app.services.budget_service import month_bounds
from app.services.obligation_source_service import regular_debt_obligation_filters

def get_monthly_timeline(
    db: Session, owner_id: int, budget_year: int, budget_month: int
) -> schemas.TimelineEventList:
    start_date, end_date = month_bounds(budget_year, budget_month)
    events: List[schemas.TimelineEvent] = []

    # pyrefly: ignore [missing-import]
    from sqlalchemy.orm import contains_eager
    # 1. Expected Inflows (ExpectedIncome table represents the scheduled dates)
    inflows = (
        db.query(models.ExpectedIncome)
        .join(models.ExpectedInflowPromise)
        .options(contains_eager(models.ExpectedIncome.promise))
        .filter(
            models.ExpectedIncome.owner_id == owner_id,
            models.ExpectedIncome.due_date >= start_date,
            models.ExpectedIncome.due_date <= end_date,
        )
        .all()
    )
    for inflow in inflows:
        remaining = inflow.amount - (inflow.received_amount or 0)
        if remaining > 0 and inflow.status in [models.ExpectedIncomeStatus.EXPECTED, models.ExpectedIncomeStatus.PARTIALLY_RECEIVED]:
            title = inflow.promise.title if inflow.promise else "Expected Inflow"
            events.append(
                schemas.TimelineEvent(
                    id=f"inflow_{inflow.id}",
                    title=title,
                    amount=remaining,
                    direction=schemas.TimelineEventDirection.INFLOW,
                    event_type=schemas.TimelineEventType.EXPECTED_INFLOW,
                    date=inflow.due_date,
                    status="PENDING",
                    category_id=None,
                    source_id=inflow.id,
                    source_type=schemas.TimelineEventSourceType.EXPECTED_INCOME,
                )
            )

    # 2. Recurring Occurrences
    occurrences = (
        db.query(models.RecurringOccurrence)
        .filter(
            models.RecurringOccurrence.owner_id == owner_id,
            models.RecurringOccurrence.scheduled_due_date >= start_date,
            models.RecurringOccurrence.scheduled_due_date <= end_date,
        )
        .all()
    )
    for occ in occurrences:
        if occ.status in [
            models.RecurringOccurrenceStatus.PENDING_CONFIRMATION,
        ]:
            events.append(
                schemas.TimelineEvent(
                    id=f"recurring_{occ.id}",
                    title=occ.expected_title,
                    amount=occ.expected_amount,
                    direction=schemas.TimelineEventDirection.OUTFLOW,
                    event_type=schemas.TimelineEventType.RECURRING_EXPENSE,
                    date=occ.scheduled_due_date,
                    status="PENDING",
                    category_id=None,
                    source_id=occ.id,
                    source_type=schemas.TimelineEventSourceType.RECURRING_OCCURRENCE,
                )
            )

    # 3. Regular debt obligations. Receivables enter the timeline only through
    # explicit expected-income rows, not by auto-trusting every open debt owed to the user.
    debts = (
        db.query(models.Debt)
        .filter(
            models.Debt.owner_id == owner_id,
            models.Debt.debt_type == models.DebtType.OWING,
            *regular_debt_obligation_filters(owner_id),
            models.Debt.expected_return_date >= start_date,
            models.Debt.expected_return_date < end_date,
        )
        .all()
    )
    for debt in debts:
        remaining = debt.remaining_amount
        if remaining > 0 and debt.expected_return_date:
            events.append(
                schemas.TimelineEvent(
                    id=f"debt_{debt.id}",
                    title=f"Pay Debt: {debt.counterparty_name}",
                    amount=remaining,
                    direction=schemas.TimelineEventDirection.OUTFLOW,
                    event_type=schemas.TimelineEventType.DEBT_PAYMENT,
                    date=debt.expected_return_date,
                    status="PENDING",
                    category_id=None,
                    source_id=debt.id,
                    source_type=schemas.TimelineEventSourceType.DEBT,
                    debt_id=debt.id,
                )
            )

    # 4. Payment Plan Payments
    payment_plans = (
        db.query(models.PaymentPlanPayment)
        .join(models.PaymentPlan)
        .options(contains_eager(models.PaymentPlanPayment.plan))
        .filter(
            models.PaymentPlanPayment.owner_id == owner_id,
            models.PaymentPlan.owner_id == owner_id,
            models.PaymentPlan.status != models.PaymentPlanStatus.ARCHIVED,
            models.PaymentPlanPayment.due_date >= start_date,
            models.PaymentPlanPayment.due_date < end_date,
        )
        .all()
    )
    for inst in payment_plans:
        remaining = inst.amount - ((inst.paid_amount or 0) + (inst.written_off_amount or 0))
        if remaining > 0 and inst.status in [
            models.PaymentPlanPaymentStatus.PENDING,
            models.PaymentPlanPaymentStatus.PARTIAL,
        ]:
            title = f"Payment plan: {inst.plan.item_name}" if inst.plan else "Scheduled payment"
            events.append(
                schemas.TimelineEvent(
                    id=f"payment_plan_{inst.id}",
                    title=title,
                    amount=remaining,
                    direction=schemas.TimelineEventDirection.OUTFLOW,
                    event_type=schemas.TimelineEventType.PAYMENT_PLAN,
                    date=inst.due_date,
                    status="PENDING",
                    category_id=None,
                    source_id=inst.id,
                    source_type=schemas.TimelineEventSourceType.PAYMENT_PLAN_PAYMENT,
                    payment_plan_id=inst.plan_id,
                    payment_plan_payment_id=inst.id,
                )
            )

    def sort_key(e: schemas.TimelineEvent):
        return (e.date, e.direction.value)

    events.sort(key=sort_key)

    return schemas.TimelineEventList(items=events)
