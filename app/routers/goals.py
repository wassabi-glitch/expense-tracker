from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import func
from sqlalchemy.orm import Session
from datetime import date
from datetime import tzinfo

from .. import models, oauth2, schemas
from ..redis_rate_limiter import consume_token_bucket
from ..session import get_db
from ..savings_balances import (
    build_goal_with_progress,
    build_savings_summary,
    ensure_premium_user,
    get_goal_funded_amount,
    sync_goal_status,
)
from ..timezone import get_effective_user_timezone, today_in_tz

router = APIRouter(
    prefix="/goals",
    tags=["Goals"],
)

GOALS_ACTIVE_LIMIT = 20
GOALS_ARCHIVED_LIMIT = 100
GOAL_LIFECYCLE_WRITE_BUCKET_CAPACITY = 10
GOAL_LIFECYCLE_WRITE_REFILL_RATE = 10 / 60
GOAL_MONEY_WRITE_BUCKET_CAPACITY = 20
GOAL_MONEY_WRITE_REFILL_RATE = 20 / 60


def enforce_goal_lifecycle_write_rate_limit(user_id: int) -> dict[str, str]:
    rl = consume_token_bucket(
        scope="goals_lifecycle_write",
        identifier=str(user_id),
        capacity=GOAL_LIFECYCLE_WRITE_BUCKET_CAPACITY,
        refill_rate_per_second=GOAL_LIFECYCLE_WRITE_REFILL_RATE,
    )
    headers = {
        "X-RateLimit-Limit": str(rl.limit),
        "X-RateLimit-Remaining": str(rl.remaining),
        "X-RateLimit-Reset": str(rl.reset_seconds),
    }
    if not rl.allowed:
        headers["Retry-After"] = str(rl.reset_seconds)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="goals.write_rate_limited",
            headers=headers,
        )
    return headers


def enforce_goal_money_write_rate_limit(user_id: int) -> dict[str, str]:
    rl = consume_token_bucket(
        scope="goals_money_write",
        identifier=str(user_id),
        capacity=GOAL_MONEY_WRITE_BUCKET_CAPACITY,
        refill_rate_per_second=GOAL_MONEY_WRITE_REFILL_RATE,
    )
    headers = {
        "X-RateLimit-Limit": str(rl.limit),
        "X-RateLimit-Remaining": str(rl.remaining),
        "X-RateLimit-Reset": str(rl.reset_seconds),
    }
    if not rl.allowed:
        headers["Retry-After"] = str(rl.reset_seconds)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="goals.write_rate_limited",
            headers=headers,
        )
    return headers


def _count_goals_by_status(db: Session, user_id: int, status_value: models.GoalStatus) -> int:
    return (
        db.query(func.count(models.Goals.id))
        .filter(
            models.Goals.owner_id == user_id,
            models.Goals.status == status_value,
        )
        .scalar()
        or 0
    )


def _ensure_active_goal_capacity(db: Session, user_id: int) -> None:
    if _count_goals_by_status(db, user_id, models.GoalStatus.ACTIVE) >= GOALS_ACTIVE_LIMIT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="goals.active_limit_reached",
        )


def _ensure_archived_goal_capacity(db: Session, user_id: int) -> None:
    if _count_goals_by_status(db, user_id, models.GoalStatus.ARCHIVED) >= GOALS_ARCHIVED_LIMIT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="goals.archived_limit_reached",
        )


def _get_owned_goal_or_404(db: Session, user_id: int, goal_id: int) -> models.Goals:
    goal = (
        db.query(models.Goals)
        .filter(
            models.Goals.id == goal_id,
            models.Goals.owner_id == user_id,
        )
        .first()
    )
    if not goal:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="goals.not_found")
    return goal


def _get_goal_with_progress(
    db: Session,
    user_id: int,
    goal: models.Goals,
    today: date | None = None,
) -> schemas.GoalWithProgressOut:
    funded_amount = get_goal_funded_amount(db, user_id, goal.id)
    sync_goal_status(goal, funded_amount)
    db.flush()
    return build_goal_with_progress(goal, funded_amount, today=today)


def _archive_goal_and_release_funds(
    db: Session,
    user_id: int,
    goal: models.Goals,
    funded_amount: int,
    today: date | None = None,
) -> schemas.GoalWithProgressOut:
    if funded_amount > 0:
        db.add(
            models.GoalContributions(
                owner_id=user_id,
                goal_id=goal.id,
                amount=funded_amount,
                contribution_type=models.GoalContributionType.RETURN,
            )
        )
        db.flush()
        funded_amount = 0

    goal.status = models.GoalStatus.ARCHIVED
    db.commit()
    db.refresh(goal)
    return build_goal_with_progress(goal, funded_amount, today=today)


@router.get("/", response_model=list[schemas.GoalWithProgressOut])
def list_goals(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
    user_tz: tzinfo = Depends(get_effective_user_timezone),
):
    ensure_premium_user(current_user)
    today = today_in_tz(user_tz)
    goals = (
        db.query(models.Goals)
        .filter(models.Goals.owner_id == current_user.id)
        .order_by(models.Goals.created_at.desc())
        .all()
    )
    return [_get_goal_with_progress(db, current_user.id, goal, today=today) for goal in goals]


@router.post("/", response_model=schemas.GoalWithProgressOut, status_code=status.HTTP_201_CREATED)
def create_goal(
    payload: schemas.GoalCreate,
    response: Response,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
    user_tz: tzinfo = Depends(get_effective_user_timezone),
):
    ensure_premium_user(current_user)
    rate_headers = enforce_goal_lifecycle_write_rate_limit(current_user.id)
    for k, v in rate_headers.items():
        response.headers[k] = v
    _ensure_active_goal_capacity(db, current_user.id)
    goal = models.Goals(
        owner_id=current_user.id,
        title=payload.title.strip(),
        target_amount=payload.target_amount,
        target_date=payload.target_date,
        status=models.GoalStatus.ACTIVE,
    )
    db.add(goal)
    db.commit()
    db.refresh(goal)
    return build_goal_with_progress(goal, 0, today=today_in_tz(user_tz))


@router.patch("/{goal_id}", response_model=schemas.GoalWithProgressOut)
def update_goal(
    goal_id: int,
    payload: schemas.GoalUpdate,
    response: Response,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
    user_tz: tzinfo = Depends(get_effective_user_timezone),
):
    ensure_premium_user(current_user)
    rate_headers = enforce_goal_lifecycle_write_rate_limit(current_user.id)
    for k, v in rate_headers.items():
        response.headers[k] = v
    today = today_in_tz(user_tz)
    goal = _get_owned_goal_or_404(db, current_user.id, goal_id)
    funded_amount = get_goal_funded_amount(db, current_user.id, goal.id)

    if "title" in payload.model_fields_set and payload.title is not None:
        goal.title = payload.title.strip()
    if "target_amount" in payload.model_fields_set and payload.target_amount is not None:
        if payload.target_amount < funded_amount:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="goals.target_below_funded_amount",
            )
        goal.target_amount = payload.target_amount
    if "target_date" in payload.model_fields_set:
        goal.target_date = payload.target_date
    if (
        "status" in payload.model_fields_set
        and payload.status is not None
        and payload.status == models.GoalStatus.ARCHIVED
    ):
        if goal.status != models.GoalStatus.ARCHIVED:
            _ensure_archived_goal_capacity(db, current_user.id)
        return _archive_goal_and_release_funds(db, current_user.id, goal, funded_amount, today=today)

    sync_goal_status(goal, funded_amount)
    db.commit()
    db.refresh(goal)
    return build_goal_with_progress(goal, funded_amount, today=today)


@router.post("/{goal_id}/archive", response_model=schemas.GoalWithProgressOut)
def archive_goal(
    goal_id: int,
    response: Response,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
    user_tz: tzinfo = Depends(get_effective_user_timezone),
):
    ensure_premium_user(current_user)
    rate_headers = enforce_goal_lifecycle_write_rate_limit(current_user.id)
    for k, v in rate_headers.items():
        response.headers[k] = v
    goal = _get_owned_goal_or_404(db, current_user.id, goal_id)
    if goal.status != models.GoalStatus.ARCHIVED:
        _ensure_archived_goal_capacity(db, current_user.id)
    funded_amount = get_goal_funded_amount(db, current_user.id, goal.id)
    return _archive_goal_and_release_funds(
        db,
        current_user.id,
        goal,
        funded_amount,
        today=today_in_tz(user_tz),
    )


@router.post("/{goal_id}/restore", response_model=schemas.GoalWithProgressOut)
def restore_goal(
    goal_id: int,
    response: Response,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
    user_tz: tzinfo = Depends(get_effective_user_timezone),
):
    ensure_premium_user(current_user)
    rate_headers = enforce_goal_lifecycle_write_rate_limit(current_user.id)
    for k, v in rate_headers.items():
        response.headers[k] = v
    goal = _get_owned_goal_or_404(db, current_user.id, goal_id)
    funded_amount = get_goal_funded_amount(db, current_user.id, goal.id)
    if goal.status != models.GoalStatus.ARCHIVED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="goals.restore_requires_archived",
        )
    _ensure_active_goal_capacity(db, current_user.id)
    goal.status = models.GoalStatus.ACTIVE
    sync_goal_status(goal, funded_amount)
    db.commit()
    db.refresh(goal)
    return build_goal_with_progress(goal, funded_amount, today=today_in_tz(user_tz))


@router.delete("/{goal_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_goal(
    goal_id: int,
    response: Response,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
):
    ensure_premium_user(current_user)
    rate_headers = enforce_goal_lifecycle_write_rate_limit(current_user.id)
    for k, v in rate_headers.items():
        response.headers[k] = v
    goal = _get_owned_goal_or_404(db, current_user.id, goal_id)
    funded_amount = get_goal_funded_amount(db, current_user.id, goal.id)
    if goal.status != models.GoalStatus.ARCHIVED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="goals.delete_requires_archived",
        )
    if funded_amount > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="goals.delete_requires_zero_funded",
        )
    db.delete(goal)
    db.commit()


@router.post("/{goal_id}/contribute", response_model=schemas.GoalWithProgressOut)
def contribute_to_goal(
    goal_id: int,
    payload: schemas.GoalContributionCreate,
    response: Response,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
    user_tz: tzinfo = Depends(get_effective_user_timezone),
):
    ensure_premium_user(current_user)
    rate_headers = enforce_goal_money_write_rate_limit(current_user.id)
    for k, v in rate_headers.items():
        response.headers[k] = v
    goal = _get_owned_goal_or_404(db, current_user.id, goal_id)
    if goal.status == models.GoalStatus.ARCHIVED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="goals.archived_read_only",
        )
    summary = build_savings_summary(db, current_user.id)
    if payload.amount > summary.free_savings_balance:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="goals.insufficient_free_savings_balance",
        )

    contribution = models.GoalContributions(
        owner_id=current_user.id,
        goal_id=goal.id,
        amount=payload.amount,
        contribution_type=models.GoalContributionType.ALLOCATE,
    )
    db.add(contribution)
    db.flush()

    funded_amount = get_goal_funded_amount(db, current_user.id, goal.id)
    sync_goal_status(goal, funded_amount)

    from app.routers.notifications import create_goal_milestone_notification
    is_completed = goal.status == models.GoalStatus.COMPLETED
    notification = create_goal_milestone_notification(
        db=db,
        owner_id=current_user.id,
        goal_title=goal.title,
        funded_amount=funded_amount,
        target_amount=goal.target_amount,
        is_completed=is_completed,
    )
    if notification:
        db.add(notification)

    db.commit()
    db.refresh(goal)
    return build_goal_with_progress(goal, funded_amount, today=today_in_tz(user_tz))


@router.post("/{goal_id}/return", response_model=schemas.GoalWithProgressOut)
def return_from_goal(
    goal_id: int,
    payload: schemas.GoalContributionCreate,
    response: Response,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
    user_tz: tzinfo = Depends(get_effective_user_timezone),
):
    ensure_premium_user(current_user)
    rate_headers = enforce_goal_money_write_rate_limit(current_user.id)
    for k, v in rate_headers.items():
        response.headers[k] = v
    goal = _get_owned_goal_or_404(db, current_user.id, goal_id)
    if goal.status == models.GoalStatus.ARCHIVED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="goals.archived_read_only",
        )
    funded_amount = get_goal_funded_amount(db, current_user.id, goal.id)
    if payload.amount > funded_amount:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="goals.insufficient_goal_balance",
        )

    contribution = models.GoalContributions(
        owner_id=current_user.id,
        goal_id=goal.id,
        amount=payload.amount,
        contribution_type=models.GoalContributionType.RETURN,
    )
    db.add(contribution)
    db.flush()

    funded_amount = get_goal_funded_amount(db, current_user.id, goal.id)
    sync_goal_status(goal, funded_amount)
    db.commit()
    db.refresh(goal)
    return build_goal_with_progress(goal, funded_amount, today=today_in_tz(user_tz))
