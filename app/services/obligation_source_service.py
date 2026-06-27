from __future__ import annotations

# pyrefly: ignore [missing-import]
from sqlalchemy import and_, exists, or_, select
# pyrefly: ignore [missing-import]
from sqlalchemy.orm import aliased

from app import models


def payment_plan_linked_debt_ids(owner_id: int):
    return select(models.PaymentPlan.debt_id).filter(
        models.PaymentPlan.owner_id == owner_id,
        models.PaymentPlan.debt_id.isnot(None),
    )


def open_unarchived_debt_filters():
    return (
        models.Debt.remaining_amount > 0,
        models.Debt.archived_at.is_(None),
    )


def regular_debt_obligation_filters(owner_id: int):
    return (
        *open_unarchived_debt_filters(),
        ~models.Debt.id.in_(payment_plan_linked_debt_ids(owner_id)),
    )


def exclude_legacy_payment_plan_debt_duplicate_filter():
    payment_plan_leg = aliased(models.EntityLedger)
    has_payment_plan_leg_for_event = exists().where(
        and_(
            payment_plan_leg.event_id == models.EntityLedger.event_id,
            payment_plan_leg.payment_plan_id.isnot(None),
        )
    )
    return or_(
        models.EntityLedger.debt_id.is_(None),
        ~has_payment_plan_leg_for_event,
    )
