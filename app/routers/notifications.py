import logging
from sqlalchemy import func
from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends, HTTPException, Query, status, Response
from typing import Optional

from .. import oauth2, models, schemas
from ..session import get_db
from app.redis_rate_limiter import consume_token_bucket

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/notifications",
    tags=["Notifications"]
)

NOTIFICATION_READ_BUCKET_CAPACITY = 30
NOTIFICATION_READ_REFILL_RATE = 30 / 60


def enforce_notification_rate_limit(user_id: int) -> dict[str, str]:
    rl = consume_token_bucket(
        scope="notifications_read",
        identifier=str(user_id),
        capacity=NOTIFICATION_READ_BUCKET_CAPACITY,
        refill_rate_per_second=NOTIFICATION_READ_REFILL_RATE,
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
            detail="notifications.rate_limited",
            headers=headers,
        )
    return headers


@router.get("/", response_model=schemas.NotificationListOut)
def get_notifications(
    response: Response,
    is_read: Optional[bool] = Query(None, description="Filter by read status"),
    limit: int = Query(20, ge=1, le=100, description="Number of notifications to return"),
    offset: int = Query(0, ge=0, description="Number of notifications to skip"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
):
    rate_headers = enforce_notification_rate_limit(current_user.id)
    for k, v in rate_headers.items():
        response.headers[k] = v

    query = db.query(models.Notification).filter(
        models.Notification.owner_id == current_user.id
    )

    if is_read is not None:
        query = query.filter(models.Notification.is_read == is_read)

    total = query.count()

    unread_count = db.query(func.count(models.Notification.id)).filter(
        models.Notification.owner_id == current_user.id,
        models.Notification.is_read.is_(False),
    ).scalar() or 0

    notifications = (
        query
        .order_by(models.Notification.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    return schemas.NotificationListOut(
        total=total,
        unread_count=unread_count,
        items=notifications,
    )


@router.get("/unread-count", response_model=dict)
def get_unread_count(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
):
    count = db.query(func.count(models.Notification.id)).filter(
        models.Notification.owner_id == current_user.id,
        models.Notification.is_read.is_(False),
    ).scalar() or 0

    return {"unread_count": count}


@router.post("/mark-read", status_code=status.HTTP_204_NO_CONTENT)
def mark_notifications_read(
    payload: schemas.NotificationMarkRead,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
):
    db.query(models.Notification).filter(
        models.Notification.owner_id == current_user.id,
        models.Notification.id.in_(payload.notification_ids),
    ).update({"is_read": True}, synchronize_session=False)

    db.commit()
    return None


@router.post("/mark-all-read", status_code=status.HTTP_204_NO_CONTENT)
def mark_all_notifications_read(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
):
    db.query(models.Notification).filter(
        models.Notification.owner_id == current_user.id,
        models.Notification.is_read.is_(False),
    ).update({"is_read": True}, synchronize_session=False)

    db.commit()
    return None


@router.delete("/{notification_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_notification(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
):
    notification = db.query(models.Notification).filter(
        models.Notification.id == notification_id,
        models.Notification.owner_id == current_user.id,
    ).first()

    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="notifications.not_found",
        )

    db.delete(notification)
    db.commit()
    return None


@router.delete("/", status_code=status.HTTP_204_NO_CONTENT)
def delete_all_notifications(
    is_read: bool = Query(False, description="Delete only read notifications"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
):
    query = db.query(models.Notification).filter(
        models.Notification.owner_id == current_user.id
    )

    if is_read:
        query = query.filter(models.Notification.is_read)

    query.delete(synchronize_session=False)
    db.commit()
    return None


def create_notification(
    db: Session,
    owner_id: int,
    notification_type: str,
    title: str,
    message: str,
    priority: str = "info",
    extra_data: Optional[dict] = None,
) -> models.Notification:
    notification = models.Notification(
        owner_id=owner_id,
        type=notification_type,
        title=title,
        message=message,
        priority=priority,
        extra_data=extra_data,
    )
    db.add(notification)
    return notification


def create_budget_notification(
    db: Session,
    budget: models.Budget,
    threshold: int,
    spent: int,
    limit: int,
) -> Optional[models.Notification]:
    category = str(budget.category.value if hasattr(budget.category, 'value') else budget.category)
    percentage = int((spent / limit) * 100) if limit > 0 else 0

    if percentage >= 100:
        over_amount = spent - limit
        title = f"Budget Exceeded: {category}"
        message = f"You've exceeded your {category} budget by {over_amount:,} UZS"
        priority = "critical"
        notification_type = models.NotificationType.BUDGET_EXCEEDED.value
    elif percentage >= 90:
        remaining = limit - spent
        title = f"High Risk: {category}"
        message = f"Only {remaining:,} UZS remaining in your {category} budget (90% spent)"
        priority = "high"
        notification_type = models.NotificationType.BUDGET_WARNING.value
    elif percentage >= 70:
        remaining = limit - spent
        title = f"Warning: {category}"
        message = f"You've used 70% of your {category} budget. {remaining:,} UZS remaining"
        priority = "medium"
        notification_type = models.NotificationType.BUDGET_WARNING.value
    elif percentage >= 50:
        title = f"Alert: {category}"
        message = f"You've used 50% of your {category} budget (reached {spent:,} UZS)"
        priority = "low"
        notification_type = models.NotificationType.BUDGET_WARNING.value
    else:
        return None

    extra_data = {
        "budget_id": budget.id,
        "category": category,
        "threshold": threshold,
        "spent": spent,
        "limit": limit,
        "percentage": percentage,
    }

    return create_notification(
        db=db,
        owner_id=budget.owner_id,
        notification_type=notification_type,
        title=title,
        message=message,
        priority=priority,
        extra_data=extra_data,
    )


def create_goal_milestone_notification(
    db: Session,
    owner_id: int,
    goal_title: str,
    funded_amount: int,
    target_amount: int,
    is_completed: bool = False,
) -> Optional[models.Notification]:
    percentage = int((funded_amount / target_amount) * 100) if target_amount > 0 else 0

    if is_completed:
        title = f"Goal Reached: {goal_title}"
        message = f"Congratulations! You've reached your {goal_title} goal!"
        priority = "high"
        notification_type = models.NotificationType.GOAL_COMPLETED.value
    elif percentage >= 75:
        title = f"Almost there: {goal_title}"
        message = f"You're 75% to your {goal_title} goal! Only {(target_amount - funded_amount):,} UZS left"
        priority = "medium"
        notification_type = models.NotificationType.GOAL_MILESTONE.value
    elif percentage >= 50:
        title = f"Halfway: {goal_title}"
        message = f"You're halfway to your {goal_title} goal! Keep going!"
        priority = "medium"
        notification_type = models.NotificationType.GOAL_MILESTONE.value
    elif percentage >= 25:
        title = f"Great start: {goal_title}"
        message = f"25% of your {goal_title} goal reached!"
        priority = "low"
        notification_type = models.NotificationType.GOAL_MILESTONE.value
    else:
        return None

    extra_data = {
        "goal_title": goal_title,
        "funded_amount": funded_amount,
        "target_amount": target_amount,
        "percentage": percentage,
        "is_completed": is_completed,
    }

    return create_notification(
        db=db,
        owner_id=owner_id,
        notification_type=notification_type,
        title=title,
        message=message,
        priority=priority,
        extra_data=extra_data,
    )
