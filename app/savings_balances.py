from datetime import date
from sqlalchemy import func
from sqlalchemy.orm import Session

from app import models, schemas
from fastapi import HTTPException, status


def ensure_premium_user(current_user: models.User) -> None:
    if not current_user.is_premium:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="users.premium_required",
        )


def get_total_balance(db: Session, user_id: int) -> int:
    total_income = (
        db.query(func.coalesce(func.sum(models.IncomeEntry.amount), 0))
        .filter(models.IncomeEntry.owner_id == user_id)
        .scalar()
    ) or 0
    total_expenses = (
        db.query(func.coalesce(func.sum(models.Expense.amount), 0))
        .filter(models.Expense.owner_id == user_id)
        .scalar()
    ) or 0
    user = db.query(models.User).filter(models.User.id == user_id).first()
    initial_balance = int(getattr(user.profile, "initial_balance", 0) or 0) if user else 0
    return initial_balance + int(total_income) - int(total_expenses)


def get_savings_balances(db: Session, user_id: int) -> tuple[int, int]:
    deposit_total = (
        db.query(func.coalesce(func.sum(models.SavingsTransactions.amount), 0))
        .filter(
            models.SavingsTransactions.owner_id == user_id,
            models.SavingsTransactions.transaction_type == models.SavingsTransactionType.DEPOSIT,
        )
        .scalar()
    ) or 0
    withdrawal_total = (
        db.query(func.coalesce(func.sum(models.SavingsTransactions.amount), 0))
        .filter(
            models.SavingsTransactions.owner_id == user_id,
            models.SavingsTransactions.transaction_type == models.SavingsTransactionType.WITHDRAWAL,
        )
        .scalar()
    ) or 0
    allocated_total = (
        db.query(func.coalesce(func.sum(models.GoalContributions.amount), 0))
        .filter(
            models.GoalContributions.owner_id == user_id,
            models.GoalContributions.contribution_type == models.GoalContributionType.ALLOCATE,
        )
        .scalar()
    ) or 0
    returned_total = (
        db.query(func.coalesce(func.sum(models.GoalContributions.amount), 0))
        .filter(
            models.GoalContributions.owner_id == user_id,
            models.GoalContributions.contribution_type == models.GoalContributionType.RETURN,
        )
        .scalar()
    ) or 0

    locked_in_goals = int(allocated_total) - int(returned_total)
    free_savings_balance = int(deposit_total) - int(withdrawal_total) - locked_in_goals
    return max(free_savings_balance, 0), max(locked_in_goals, 0)


def build_savings_summary(db: Session, user_id: int) -> schemas.SavingsSummaryOut:
    total_balance = get_total_balance(db, user_id)
    free_savings_balance, locked_in_goals = get_savings_balances(db, user_id)
    spendable_balance = total_balance - free_savings_balance - locked_in_goals
    return schemas.SavingsSummaryOut(
        total_balance=int(total_balance),
        free_savings_balance=int(free_savings_balance),
        locked_in_goals=int(locked_in_goals),
        spendable_balance=int(spendable_balance),
    )


def get_goal_funded_amount(db: Session, user_id: int, goal_id: int) -> int:
    allocated_total = (
        db.query(func.coalesce(func.sum(models.GoalContributions.amount), 0))
        .filter(
            models.GoalContributions.owner_id == user_id,
            models.GoalContributions.goal_id == goal_id,
            models.GoalContributions.contribution_type == models.GoalContributionType.ALLOCATE,
        )
        .scalar()
    ) or 0
    returned_total = (
        db.query(func.coalesce(func.sum(models.GoalContributions.amount), 0))
        .filter(
            models.GoalContributions.owner_id == user_id,
            models.GoalContributions.goal_id == goal_id,
            models.GoalContributions.contribution_type == models.GoalContributionType.RETURN,
        )
        .scalar()
    ) or 0
    return max(int(allocated_total) - int(returned_total), 0)


def build_goal_with_progress(
    goal: models.Goals,
    funded_amount: int,
    today: date | None = None,
) -> schemas.GoalWithProgressOut:
    target_amount = int(goal.target_amount or 0)
    remaining_amount = max(target_amount - int(funded_amount), 0)
    progress_percent = 0.0 if target_amount <= 0 else min((int(funded_amount) / target_amount) * 100, 100.0)
    goal_out = schemas.GoalWithProgressOut.model_validate(goal)
    days_until_target = None
    time_state = None
    effective_today = today or date.today()
    if goal.status == models.GoalStatus.ACTIVE and goal.target_date:
        days_until_target = (goal.target_date - effective_today).days
        if remaining_amount > 0:
            if days_until_target < 0:
                time_state = schemas.GoalTimeState.OVERDUE
            elif days_until_target <= 7:
                time_state = schemas.GoalTimeState.DUE_SOON
            else:
                time_state = schemas.GoalTimeState.ON_TRACK
    goal_out.funded_amount = int(funded_amount)
    goal_out.remaining_amount = int(remaining_amount)
    goal_out.progress_percent = round(progress_percent, 2)
    goal_out.time_state = time_state
    goal_out.days_until_target = days_until_target
    return goal_out


def sync_goal_status(goal: models.Goals, funded_amount: int) -> None:
    if goal.status == models.GoalStatus.ARCHIVED:
        return
    goal.status = (
        models.GoalStatus.COMPLETED
        if int(funded_amount) >= int(goal.target_amount or 0)
        else models.GoalStatus.ACTIVE
    )
