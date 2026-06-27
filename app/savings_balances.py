from fastapi import HTTPException, status

from app import models
from app.services.obligation_source_service import regular_debt_obligation_filters
from app.services.goal_funding_service import (
    build_goal_funding_summary,
    get_total_balance,
)


def ensure_premium_user(current_user: models.User) -> None:
    if not current_user.is_premium:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="users.premium_required",
        )


def build_savings_summary(db, user_id: int):
    return build_goal_funding_summary(db, user_id)


def get_net_position(db, user_id: int) -> int:
    total_physical_balance = get_total_balance(db, user_id)

    total_owed_to_me = (
        db.query(models.Debt.remaining_amount)
        .filter(
            models.Debt.owner_id == user_id,
            models.Debt.debt_type == models.DebtType.OWED,
            *regular_debt_obligation_filters(user_id),
        )
        .all()
    )
    total_i_owe = (
        db.query(models.Debt.remaining_amount)
        .filter(
            models.Debt.owner_id == user_id,
            models.Debt.debt_type == models.DebtType.OWING,
            *regular_debt_obligation_filters(user_id),
        )
        .all()
    )
    payment_plan_remaining = (
        db.query(models.PaymentPlan.remaining_amount)
        .filter(
            models.PaymentPlan.owner_id == user_id,
            models.PaymentPlan.status != models.PaymentPlanStatus.ARCHIVED,
            models.PaymentPlan.remaining_amount > 0,
        )
        .all()
    )

    return (
        int(total_physical_balance)
        + sum(int(row[0] or 0) for row in total_owed_to_me)
        - sum(int(row[0] or 0) for row in total_i_owe)
        - sum(int(row[0] or 0) for row in payment_plan_remaining)
    )
