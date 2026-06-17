from fastapi import HTTPException, status

from app import models
from app.services.goal_funding_service import (
    build_goal_funding_summary,
    build_goal_with_progress,
    get_goal_funded_amount,
    get_goal_linked_project_id,
    get_goal_released_amount,
    get_total_balance,
    sync_goal_status,
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
            models.Debt.status == models.DebtStatus.ACTIVE,
        )
        .all()
    )
    total_i_owe = (
        db.query(models.Debt.remaining_amount)
        .filter(
            models.Debt.owner_id == user_id,
            models.Debt.debt_type == models.DebtType.OWING,
            models.Debt.status == models.DebtStatus.ACTIVE,
        )
        .all()
    )

    return (
        int(total_physical_balance)
        + sum(int(row[0] or 0) for row in total_owed_to_me)
        - sum(int(row[0] or 0) for row in total_i_owe)
    )
