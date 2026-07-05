from datetime import date

from fastapi import HTTPException, status
# pyrefly: ignore [missing-import]
from sqlalchemy.orm import Session

from .wallet_value_service import can_hold_goal_funds

from app import models, schemas

PAYMENT_PLAN_GOAL_TARGET_STATUSES = (
    models.PaymentPlanPaymentStatus.PENDING,
    models.PaymentPlanPaymentStatus.PARTIAL,
)


def _payment_plan_payment_remaining(payment: models.PaymentPlanPayment) -> int:
    return max(
        0,
        int(payment.amount or 0)
        - int(payment.paid_amount or 0)
        - int(payment.written_off_amount or 0),
    )


def _contribution_delta(contribution: models.GoalContributions) -> int:
    amount = int(contribution.amount or 0)
    if contribution.contribution_type == models.GoalContributionType.ALLOCATE:
        return amount
    if contribution.contribution_type in (
        models.GoalContributionType.RETURN,
        models.GoalContributionType.CONSUME,
    ):
        return -amount
    return 0


def _goal_contributions(
    db: Session,
    user_id: int,
    goal_id: int | None = None,
    wallet_id: int | None = None,
) -> list[models.GoalContributions]:
    query = db.query(models.GoalContributions).filter(models.GoalContributions.owner_id == user_id)
    if goal_id is not None:
        query = query.filter(models.GoalContributions.goal_id == goal_id)
    if wallet_id is not None:
        query = query.filter(models.GoalContributions.wallet_id == wallet_id)
    return query.all()


def is_wallet_goal_funding_eligible(wallet: models.Wallet) -> bool:
    return can_hold_goal_funds(wallet)


def get_total_balance(db: Session, user_id: int) -> int:
    wallets = db.query(models.Wallet).filter(models.Wallet.owner_id == user_id).all()
    return sum(int(wallet.current_balance or 0) for wallet in wallets)


def get_goal_funded_amount(db: Session, user_id: int, goal_id: int) -> int:
    total = sum(_contribution_delta(item) for item in _goal_contributions(db, user_id, goal_id=goal_id))
    return max(int(total), 0)


def get_goal_wallet_funded_amount(db: Session, user_id: int, goal_id: int, wallet_id: int) -> int:
    total = sum(
        _contribution_delta(item)
        for item in _goal_contributions(db, user_id, goal_id=goal_id, wallet_id=wallet_id)
    )
    return max(int(total), 0)


def get_goal_consumed_amount(db: Session, user_id: int, goal_id: int) -> int:
    total = sum(
        int(item.amount or 0)
        for item in _goal_contributions(db, user_id, goal_id=goal_id)
        if item.contribution_type == models.GoalContributionType.CONSUME
    )
    return max(int(total), 0)


def get_next_payment_plan_goal_payment(
    db: Session,
    user_id: int,
    plan_id: int,
) -> models.PaymentPlanPayment | None:
    return (
        db.query(models.PaymentPlanPayment)
        .filter(
            models.PaymentPlanPayment.owner_id == user_id,
            models.PaymentPlanPayment.plan_id == plan_id,
            models.PaymentPlanPayment.status.in_(PAYMENT_PLAN_GOAL_TARGET_STATUSES),
            (
                models.PaymentPlanPayment.amount
                > models.PaymentPlanPayment.paid_amount + models.PaymentPlanPayment.written_off_amount
            ),
        )
        .order_by(models.PaymentPlanPayment.due_date.asc(), models.PaymentPlanPayment.id.asc())
        .first()
    )


def get_goal_payment_plan_target(
    db: Session,
    user_id: int,
    goal: models.Goals,
) -> schemas.GoalPaymentPlanTargetOut | None:
    if goal.intent != models.GoalIntent.PAY_OBLIGATION or goal.linked_payment_plan_id is None:
        return None

    plan = (
        db.query(models.PaymentPlan)
        .filter(
            models.PaymentPlan.id == goal.linked_payment_plan_id,
            models.PaymentPlan.owner_id == user_id,
        )
        .first()
    )
    if plan is None:
        return None

    payments = (
        db.query(models.PaymentPlanPayment)
        .filter(
            models.PaymentPlanPayment.owner_id == user_id,
            models.PaymentPlanPayment.plan_id == plan.id,
        )
        .order_by(models.PaymentPlanPayment.due_date.asc(), models.PaymentPlanPayment.id.asc())
        .all()
    )
    target = next(
        (
            payment
            for payment in payments
            if payment.status in PAYMENT_PLAN_GOAL_TARGET_STATUSES
            and _payment_plan_payment_remaining(payment) > 0
        ),
        None,
    )
    if target is None:
        return None

    return schemas.GoalPaymentPlanTargetOut(
        plan_id=int(plan.id),
        payment_id=int(target.id),
        payment_number=payments.index(target) + 1,
        total_payments=len(payments),
        due_date=target.due_date,
        amount=int(target.amount or 0),
        paid_amount=int(target.paid_amount or 0),
        remaining_amount=_payment_plan_payment_remaining(target),
        status=target.status,
        item_name=plan.item_name,
    )


def get_wallet_goal_allocated_amount(db: Session, user_id: int, wallet_id: int) -> int:
    total = sum(_contribution_delta(item) for item in _goal_contributions(db, user_id, wallet_id=wallet_id))
    released_amount = get_wallet_goal_released_amount(db, user_id, wallet_id)
    return max(int(total) - int(released_amount), 0)


def get_wallet_free_to_spend(db: Session, user_id: int, wallet: models.Wallet) -> int:
    protected_amount = get_wallet_goal_allocated_amount(db, user_id, wallet.id)
    owned_balance = max(int(wallet.current_balance or 0), 0)
    return max(owned_balance - protected_amount, 0)


def get_wallet_required_goal_resolution_for_outflow(
    db: Session,
    user_id: int,
    wallet: models.Wallet,
    amount: int,
) -> int:
    protected_amount = get_wallet_goal_allocated_amount(db, user_id, wallet.id)
    owned_balance = max(int(wallet.current_balance or 0), 0)
    owned_balance_after_outflow = max(owned_balance - int(amount), 0)
    return max(protected_amount - owned_balance_after_outflow, 0)


def validate_wallet_goal_protection_for_outflow(
    db: Session,
    user_id: int,
    wallet: models.Wallet,
    amount: int,
    *,
    outflow_type: str,
    error_code: str = "expenses.goal_protection_conflict",
) -> None:
    requested_amount = int(amount)
    protected_amount = get_wallet_goal_allocated_amount(db, user_id, wallet.id)
    owned_balance = max(int(wallet.current_balance or 0), 0)
    free_to_spend = max(owned_balance - protected_amount, 0)
    if requested_amount <= free_to_spend:
        return
    required_goal_resolution = get_wallet_required_goal_resolution_for_outflow(
        db,
        user_id,
        wallet,
        requested_amount,
    )
    if required_goal_resolution <= 0:
        return

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail={
            "code": error_code,
            "outflow_type": outflow_type,
            "wallet_id": int(wallet.id),
            "wallet_name": wallet.name,
            "currency": wallet.currency,
            "wallet_balance": int(wallet.current_balance or 0),
            "protected_for_goals": int(protected_amount),
            "free_to_spend": int(free_to_spend),
            "requested_amount": int(requested_amount),
            "protected_amount_touched": int(required_goal_resolution),
            "required_goal_resolution_amount": int(required_goal_resolution),
        },
    )


def _wallet_goal_amounts_ordered(
    db: Session,
    user_id: int,
    wallet_id: int,
) -> list[tuple[models.Goals, int]]:
    goals = (
        db.query(models.Goals)
        .filter(models.Goals.owner_id == user_id)
        .order_by(models.Goals.created_at.asc(), models.Goals.id.asc())
        .all()
    )
    rows: list[tuple[models.Goals, int]] = []
    for goal in goals:
        amount = get_goal_wallet_funded_amount(db, user_id, goal.id, wallet_id)
        if amount > 0:
            rows.append((goal, amount))
    return rows


def _resolve_wallet_goal_amount(
    db: Session,
    user_id: int,
    source_wallet_id: int,
    amount: int,
    *,
    linked_event_id: int | None,
    target_wallet_id: int | None = None,
) -> list[int]:
    remaining = int(amount)
    affected_goal_ids: list[int] = []
    for goal, wallet_goal_amount in _wallet_goal_amounts_ordered(db, user_id, source_wallet_id):
        if remaining <= 0:
            break
        chunk = min(int(wallet_goal_amount), remaining)
        if chunk <= 0:
            continue
        record_goal_contribution(
            db=db,
            user_id=user_id,
            goal_id=goal.id,
            wallet_id=source_wallet_id,
            amount=chunk,
            contribution_type=models.GoalContributionType.RETURN,
            linked_event_id=linked_event_id,
        )
        if target_wallet_id is not None:
            record_goal_contribution(
                db=db,
                user_id=user_id,
                goal_id=goal.id,
                wallet_id=target_wallet_id,
                amount=chunk,
                contribution_type=models.GoalContributionType.ALLOCATE,
                linked_event_id=linked_event_id,
            )
        sync_goal_status(goal, get_goal_funded_amount(db, user_id, goal.id))
        affected_goal_ids.append(int(goal.id))
        remaining -= chunk

    if remaining > 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="wallets.goal_resolution_amount_unavailable")
    return affected_goal_ids


def move_wallet_goal_allocations(
    db: Session,
    user_id: int,
    *,
    source_wallet: models.Wallet,
    target_wallet: models.Wallet,
    amount: int,
    incoming_amount_to_target: int = 0,
    linked_event_id: int | None = None,
) -> list[int]:
    if amount <= 0:
        return []
    if not is_wallet_goal_funding_eligible(target_wallet):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="wallets.goal_resolution_target_not_eligible")
    if source_wallet.currency != target_wallet.currency:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="wallets.goal_resolution_currency_mismatch")

    target_protected = get_wallet_goal_allocated_amount(db, user_id, target_wallet.id)
    projected_target_owned_balance = max(int(target_wallet.current_balance or 0), 0) + int(incoming_amount_to_target)
    projected_target_available = max(projected_target_owned_balance - target_protected, 0)
    if int(amount) > projected_target_available:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="wallets.goal_resolution_target_unavailable")

    return _resolve_wallet_goal_amount(
        db,
        user_id,
        source_wallet.id,
        int(amount),
        linked_event_id=linked_event_id,
        target_wallet_id=target_wallet.id,
    )


def release_wallet_goal_allocations(
    db: Session,
    user_id: int,
    *,
    source_wallet: models.Wallet,
    amount: int,
    linked_event_id: int | None = None,
) -> list[int]:
    if amount <= 0:
        return []
    return _resolve_wallet_goal_amount(
        db,
        user_id,
        source_wallet.id,
        int(amount),
        linked_event_id=linked_event_id,
        target_wallet_id=None,
    )


def get_goal_released_amount(db: Session, user_id: int, goal_id: int) -> int:
    released_total = sum(
        int(item.amount or 0)
        for item in db.query(models.GoalProjectRelease)
        .filter(
            models.GoalProjectRelease.owner_id == user_id,
            models.GoalProjectRelease.goal_id == goal_id,
        )
        .all()
    )
    return max(int(released_total), 0)


def get_goal_wallet_released_amount(db: Session, user_id: int, goal_id: int, wallet_id: int) -> int:
    released_total = sum(
        int(item.amount or 0)
        for item in db.query(models.GoalProjectRelease)
        .filter(
            models.GoalProjectRelease.owner_id == user_id,
            models.GoalProjectRelease.goal_id == goal_id,
            models.GoalProjectRelease.wallet_id == wallet_id,
        )
        .all()
    )
    return max(int(released_total), 0)


def get_wallet_goal_released_amount(db: Session, user_id: int, wallet_id: int) -> int:
    released_total = sum(
        int(item.amount or 0)
        for item in db.query(models.GoalProjectRelease)
        .filter(
            models.GoalProjectRelease.owner_id == user_id,
            models.GoalProjectRelease.wallet_id == wallet_id,
        )
        .all()
    )
    return max(int(released_total), 0)


def get_goal_linked_project_id(db: Session, user_id: int, goal_id: int) -> int | None:
    project_id = (
        db.query(models.Project.id)
        .filter(
            models.Project.owner_id == user_id,
            models.Project.origin_goal_id == goal_id,
        )
        .scalar()
    )
    return int(project_id) if project_id is not None else None


def get_goal_funding_sources(db: Session, user_id: int, goal_id: int) -> list[schemas.GoalFundingSourceOut]:
    totals_by_wallet: dict[int, int] = {}
    for contribution in _goal_contributions(db, user_id, goal_id=goal_id):
        totals_by_wallet[contribution.wallet_id] = totals_by_wallet.get(contribution.wallet_id, 0) + _contribution_delta(contribution)

    sources: list[schemas.GoalFundingSourceOut] = []
    for wallet_id, allocated_amount in totals_by_wallet.items():
        if allocated_amount <= 0:
            continue
        wallet = (
            db.query(models.Wallet)
            .filter(models.Wallet.id == wallet_id, models.Wallet.owner_id == user_id)
            .first()
        )
        if wallet is None:
            continue
        released_amount = get_goal_wallet_released_amount(db, user_id, goal_id, wallet_id)
        sources.append(
            schemas.GoalFundingSourceOut(
                wallet_id=wallet.id,
                wallet_name=wallet.name,
                wallet_type=wallet.wallet_type,
                currency=wallet.currency,
                allocated_amount=int(allocated_amount),
                released_amount=int(released_amount),
                unreleased_amount=max(int(allocated_amount) - int(released_amount), 0),
            )
        )
    return sorted(sources, key=lambda item: item.wallet_name.lower())


def build_goal_funding_summary(db: Session, user_id: int) -> schemas.GoalFundingSummaryOut:
    wallets = (
        db.query(models.Wallet)
        .filter(models.Wallet.owner_id == user_id)
        .order_by(models.Wallet.created_at.asc(), models.Wallet.id.asc())
        .all()
    )

    wallet_rows: list[schemas.WalletGoalFundingOut] = []
    total_wallet_balance = 0
    total_allocated = 0
    total_available = 0
    total_over_allocated = 0

    for wallet in wallets:
        balance = int(wallet.current_balance or 0)
        allocated = get_wallet_goal_allocated_amount(db, user_id, wallet.id)
        available_raw = balance - allocated
        over_allocated = max(-available_raw, 0)
        eligible = is_wallet_goal_funding_eligible(wallet)
        available = max(available_raw, 0) if eligible else 0

        total_wallet_balance += balance
        total_allocated += allocated
        total_available += available
        total_over_allocated += over_allocated

        wallet_rows.append(
            schemas.WalletGoalFundingOut(
                wallet_id=wallet.id,
                wallet_name=wallet.name,
                wallet_type=wallet.wallet_type,
                currency=wallet.currency,
                is_active=bool(wallet.is_active),
                balance=balance,
                allocated_to_goals=allocated,
                available_for_goals=available,
                over_allocated_amount=over_allocated,
                can_fund_goals=bool(wallet.can_fund_goals),
                eligible_for_goal_funding=eligible,
            )
        )

    return schemas.GoalFundingSummaryOut(
        total_wallet_balance=int(total_wallet_balance),
        allocated_to_goals=int(total_allocated),
        available_for_goals=int(total_available),
        over_allocated_amount=int(total_over_allocated),
        wallets=wallet_rows,
    )


def get_wallet_available_for_goal(db: Session, user_id: int, wallet_id: int) -> int:
    wallet = (
        db.query(models.Wallet)
        .filter(models.Wallet.id == wallet_id, models.Wallet.owner_id == user_id)
        .first()
    )
    if wallet is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="wallets.not_found")
    allocated = get_wallet_goal_allocated_amount(db, user_id, wallet.id)
    return max(int(wallet.current_balance or 0) - int(allocated), 0)


def validate_wallet_for_goal_allocation(
    db: Session,
    user_id: int,
    goal: models.Goals,
    wallet_id: int,
) -> models.Wallet:
    wallet = (
        db.query(models.Wallet)
        .filter(models.Wallet.id == wallet_id, models.Wallet.owner_id == user_id)
        .first()
    )
    if wallet is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="wallets.not_found")
    if not is_wallet_goal_funding_eligible(wallet):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="goals.wallet_not_eligible")
    if wallet.currency != goal.currency:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="goals.currency_mismatch")
    return wallet


def validate_wallet_for_goal_release(
    db: Session,
    user_id: int,
    goal: models.Goals,
    wallet_id: int,
) -> models.Wallet:
    wallet = (
        db.query(models.Wallet)
        .filter(models.Wallet.id == wallet_id, models.Wallet.owner_id == user_id)
        .first()
    )
    if wallet is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="wallets.not_found")
    if wallet.currency != goal.currency:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="goals.currency_mismatch")
    return wallet


def record_goal_contribution(
    db: Session,
    user_id: int,
    goal_id: int,
    wallet_id: int,
    amount: int,
    contribution_type: models.GoalContributionType,
    linked_event_id: int | None = None,
) -> models.GoalContributions:
    contribution = models.GoalContributions(
        owner_id=user_id,
        goal_id=goal_id,
        wallet_id=wallet_id,
        linked_event_id=linked_event_id,
        amount=amount,
        contribution_type=contribution_type,
    )
    db.add(contribution)
    db.flush()
    return contribution


def return_all_unreleased_goal_funding(
    db: Session,
    user_id: int,
    goal_id: int,
) -> None:
    for source in get_goal_funding_sources(db, user_id, goal_id):
        if source.unreleased_amount <= 0:
            continue
        record_goal_contribution(
            db=db,
            user_id=user_id,
            goal_id=goal_id,
            wallet_id=source.wallet_id,
            amount=source.unreleased_amount,
            contribution_type=models.GoalContributionType.RETURN,
        )


def _return_excess_goal_funding(db: Session, user_id: int, goal_id: int, excess: int) -> None:
    remaining = excess
    for source in get_goal_funding_sources(db, user_id, goal_id):
        if remaining <= 0:
            break
        if source.unreleased_amount <= 0:
            continue
        chunk = min(source.unreleased_amount, remaining)
        record_goal_contribution(
            db=db,
            user_id=user_id,
            goal_id=goal_id,
            wallet_id=source.wallet_id,
            amount=chunk,
            contribution_type=models.GoalContributionType.RETURN,
        )
        remaining -= chunk


def sync_debt_goal_targets(db: Session, user_id: int, debt_id: int) -> None:
    debt = (
        db.query(models.Debt)
        .filter(models.Debt.id == debt_id, models.Debt.owner_id == user_id)
        .first()
    )
    if debt is None:
        return
        
    goal_statuses = [models.GoalStatus.ACTIVE]
    goals = (
        db.query(models.Goals)
        .filter(
            models.Goals.owner_id == user_id,
            models.Goals.intent == models.GoalIntent.PAY_OBLIGATION,
            models.Goals.linked_debt_id == debt_id,
            models.Goals.status.in_(goal_statuses),
        )
        .all()
    )
    for goal in goals:
        consumed_amount = get_goal_consumed_amount(db, user_id, goal.id)

        payable_through_goal = int(consumed_amount) + int(debt.remaining_amount or 0)
        if goal.debt_goal_tracking_mode == models.DebtGoalTrackingMode.FULL_REMAINING_DEBT:
            if payable_through_goal > 0:
                goal.target_amount = payable_through_goal
            else:
                return_all_unreleased_goal_funding(db, user_id, goal.id)
                goal.target_amount = max(int(consumed_amount), 1)
                goal.status = models.GoalStatus.COMPLETED
        elif goal.debt_goal_tracking_mode == models.DebtGoalTrackingMode.FIXED_DEBT_AMOUNT:
            if payable_through_goal > 0 and int(goal.target_amount or 0) > payable_through_goal:
                goal.target_amount = payable_through_goal
            elif payable_through_goal <= 0:
                return_all_unreleased_goal_funding(db, user_id, goal.id)
                goal.target_amount = max(int(consumed_amount), 1)
                goal.status = models.GoalStatus.COMPLETED


def build_goal_with_progress(
    db: Session,
    user_id: int,
    goal: models.Goals,
    funded_amount: int,
    released_amount: int = 0,
    linked_project_id: int | None = None,
    today: date | None = None,
) -> schemas.GoalWithProgressOut:
    target_amount = int(goal.target_amount or 0)
    consumed_amount = get_goal_consumed_amount(db, user_id, goal.id)
    is_payment_plan_goal = goal.intent == models.GoalIntent.PAY_OBLIGATION and goal.linked_payment_plan_id is not None
    is_real_world_completed = (
        goal.status == models.GoalStatus.COMPLETED
        and (
            goal.linked_expense_event_id is not None
            or goal.linked_debt_transaction_id is not None
            or is_payment_plan_goal
        )
    )
    unreleased_amount = max(int(funded_amount) - int(released_amount), 0)
    if is_payment_plan_goal:
        progress_amount = int(unreleased_amount)
    elif goal.intent == models.GoalIntent.PAY_OBLIGATION:
        progress_amount = int(consumed_amount) + int(unreleased_amount)
    else:
        progress_amount = int(funded_amount)
    remaining_amount = 0 if is_real_world_completed else max(target_amount - int(progress_amount), 0)
    if is_real_world_completed:
        progress_percent = 100.0
    else:
        progress_percent = (
            0.0 if target_amount <= 0 else min((int(progress_amount) / target_amount) * 100, 100.0)
        )
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
    goal_out.consumed_amount = int(consumed_amount)
    goal_out.released_amount = int(released_amount)
    goal_out.unreleased_amount = int(unreleased_amount)
    goal_out.remaining_amount = int(remaining_amount)
    goal_out.progress_percent = round(progress_percent, 2)
    goal_out.linked_project_id = int(linked_project_id) if linked_project_id is not None else None
    goal_out.funding_sources = get_goal_funding_sources(db, user_id, goal.id)
    goal_out.time_state = time_state
    goal_out.days_until_target = days_until_target
    goal_out.payment_plan_target = get_goal_payment_plan_target(db, user_id, goal)
    return goal_out


def sync_goal_status(goal: models.Goals, funded_amount: int) -> None:
    if goal.status in (models.GoalStatus.ARCHIVED, models.GoalStatus.GRADUATED):
        return
    if goal.status == models.GoalStatus.COMPLETED and (
        goal.linked_expense_event_id is not None
        or goal.linked_debt_transaction_id is not None
    ):
        return
    goal.status = models.GoalStatus.ACTIVE
