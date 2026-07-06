from datetime import date, timezone, tzinfo

from fastapi import APIRouter, Depends, HTTPException, Response, status
# pyrefly: ignore [missing-import]
from sqlalchemy import func
# pyrefly: ignore [missing-import]
from sqlalchemy.orm import Session, selectinload

from .. import models, oauth2, schemas
from ..services.budget_service import (
    get_project_budget_summaries,
)
from ..services.debt_payment_service import build_debt_transaction_out, create_debt_payment
from ..services.debt_policy import evaluate_debt_action
from ..services.debt_service import get_debt_total_charges, get_debt_total_paid, reconcile_debt
from ..services.expense_posting_service import post_expense_event
from ..services.goal_funding_service import (
    build_goal_funding_summary,
    build_goal_with_progress,
    get_next_payment_plan_goal_payment,
    get_goal_consumed_amount,
    get_goal_funded_amount,
    get_goal_funding_sources,
    get_goal_linked_project_id,
    get_goal_released_amount,
    get_goal_wallet_funded_amount,
    get_goal_wallet_released_amount,
    get_wallet_available_for_goal,
    record_goal_contribution,
    return_all_unreleased_goal_funding,
    sync_goal_status,
    sync_debt_goal_targets,
    validate_wallet_for_goal_allocation,
    validate_wallet_for_goal_release,
)
from ..services.isolated_project_service import get_project_funding_limit
from ..services.wallet_fee_service import (
    get_owned_fee_wallet_or_404,
    record_linked_bank_fee_event,
    resolve_or_create_bank_fee_budget,
    validate_linked_fee_goal_protection,
)
from ..services.wallet_service import WalletService
from ..redis_rate_limiter import consume_token_bucket
from ..savings_balances import ensure_premium_user
from ..session import get_db
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
MAX_PLANNED_PURCHASE_PAYMENT_WALLETS = 3


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


def _raise_if_goal_saving_phase_read_only(goal: models.Goals) -> None:
    if goal.status == models.GoalStatus.ARCHIVED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="goals.archived_read_only",
        )
    if goal.status == models.GoalStatus.GRADUATED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="goals.graduated_read_only",
        )


def _get_goal_with_progress(
    db: Session,
    user_id: int,
    goal: models.Goals,
    today: date | None = None,
) -> schemas.GoalWithProgressOut:
    funded_amount = get_goal_funded_amount(db, user_id, goal.id)
    sync_goal_status(goal, funded_amount)
    db.flush()
    return build_goal_with_progress(
        db,
        user_id,
        goal,
        funded_amount,
        released_amount=get_goal_released_amount(db, user_id, goal.id),
        linked_project_id=get_goal_linked_project_id(db, user_id, goal.id),
        today=today,
    )


def _goal_activity_date_from_created_at(created_at, user_tz: tzinfo) -> date:
    if not hasattr(created_at, "date"):
        return today_in_tz(user_tz)
    if hasattr(created_at, "astimezone"):
        timestamp = created_at
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=timezone.utc)
        return timestamp.astimezone(user_tz).date()
    return created_at.date()


def _goal_activity_time_from_created_at(created_at, user_tz: tzinfo) -> str | None:
    if not hasattr(created_at, "astimezone"):
        return None
    timestamp = created_at
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)
    return timestamp.astimezone(user_tz).strftime("%H:%M")


def _activity_wallet(
    *,
    role: str,
    wallet: models.Wallet | None,
    wallet_id: int,
    amount: int,
) -> schemas.GoalActivityWalletOut:
    return schemas.GoalActivityWalletOut(
        role=role,
        wallet_id=int(wallet.id if wallet is not None else wallet_id),
        wallet_name=wallet.name if wallet is not None else "Wallet",
        amount=int(amount),
    )


def _activity_event_description(event: models.FinancialEvent | None) -> str | None:
    if event is None:
        return None
    return event.description or event.title


def _build_goal_activity(
    db: Session,
    user_id: int,
    goal: models.Goals,
    user_tz: tzinfo,
) -> schemas.GoalActivityOut:
    contributions = (
        db.query(models.GoalContributions)
        .filter(
            models.GoalContributions.owner_id == user_id,
            models.GoalContributions.goal_id == goal.id,
        )
        .order_by(models.GoalContributions.created_at.desc(), models.GoalContributions.id.desc())
        .all()
    )
    project_releases = (
        db.query(models.GoalProjectRelease)
        .filter(
            models.GoalProjectRelease.owner_id == user_id,
            models.GoalProjectRelease.goal_id == goal.id,
        )
        .order_by(models.GoalProjectRelease.created_at.desc(), models.GoalProjectRelease.id.desc())
        .all()
    )

    linked_event_ids = {int(item.linked_event_id) for item in contributions if item.linked_event_id is not None}
    events_by_id: dict[int, models.FinancialEvent] = {}
    wallet_legs_by_event_id: dict[int, list[models.WalletLedger]] = {}
    if linked_event_ids:
        events = (
            db.query(models.FinancialEvent)
            .filter(
                models.FinancialEvent.owner_id == user_id,
                models.FinancialEvent.id.in_(linked_event_ids),
            )
            .all()
        )
        events_by_id = {int(event.id): event for event in events}
        wallet_legs = (
            db.query(models.WalletLedger)
            .filter(
                models.WalletLedger.owner_id == user_id,
                models.WalletLedger.event_id.in_(linked_event_ids),
            )
            .all()
        )
        for leg in wallet_legs:
            wallet_legs_by_event_id.setdefault(int(leg.event_id), []).append(leg)

    wallet_ids = {int(item.wallet_id) for item in contributions}
    wallet_ids.update(int(release.wallet_id) for release in project_releases if release.wallet_id is not None)
    for legs in wallet_legs_by_event_id.values():
        wallet_ids.update(int(leg.wallet_id) for leg in legs)
    wallets_by_id = {
        int(wallet.id): wallet
        for wallet in db.query(models.Wallet)
        .filter(models.Wallet.owner_id == user_id, models.Wallet.id.in_(wallet_ids))
        .all()
    } if wallet_ids else {}

    items: list[schemas.GoalActivityItemOut] = [
        schemas.GoalActivityItemOut(
            id=f"goal-created:{goal.id}",
            type="GOAL_CREATED",
            title="Goal created",
            description=goal.title,
            amount=0,
            currency=goal.currency,
            date=_goal_activity_date_from_created_at(goal.created_at, user_tz),
            time_label=_goal_activity_time_from_created_at(goal.created_at, user_tz),
            created_at=goal.created_at,
        )
    ]

    contributions_by_event_id: dict[int, list[models.GoalContributions]] = {}
    standalone_contributions: list[models.GoalContributions] = []
    for contribution in contributions:
        if contribution.linked_event_id is None:
            standalone_contributions.append(contribution)
        else:
            contributions_by_event_id.setdefault(int(contribution.linked_event_id), []).append(contribution)

    for event_id, rows in contributions_by_event_id.items():
        event = events_by_id.get(event_id)
        returns = [row for row in rows if row.contribution_type == models.GoalContributionType.RETURN]
        allocations = [row for row in rows if row.contribution_type == models.GoalContributionType.ALLOCATE]
        consumes = [row for row in rows if row.contribution_type == models.GoalContributionType.CONSUME]
        created_at = max((row.created_at for row in rows), default=event.created_at if event else goal.created_at)
        activity_date = event.date if event is not None else _goal_activity_date_from_created_at(created_at, user_tz)

        if event is not None and event.event_type == models.TransactionType.TRANSFER and returns and allocations:
            amount = max(sum(int(row.amount or 0) for row in returns), sum(int(row.amount or 0) for row in allocations))
            title = "Prepared reserve payment" if goal.intent == models.GoalIntent.RESERVE else "Prepared payment"
            description = _activity_event_description(event) or "Moved goal money to another wallet."
            wallets = [
                _activity_wallet(
                    role="from",
                    wallet=wallets_by_id.get(int(row.wallet_id)),
                    wallet_id=int(row.wallet_id),
                    amount=int(row.amount or 0),
                )
                for row in returns
            ] + [
                _activity_wallet(
                    role="to",
                    wallet=wallets_by_id.get(int(row.wallet_id)),
                    wallet_id=int(row.wallet_id),
                    amount=int(row.amount or 0),
                )
                for row in allocations
            ]
            items.append(
                schemas.GoalActivityItemOut(
                    id=f"prepared-payment:{event_id}",
                    type="PREPARED_PAYMENT",
                    title=title,
                    description=description,
                    amount=int(amount),
                    currency=goal.currency,
                    date=activity_date,
                    time_label=_goal_activity_time_from_created_at(created_at, user_tz),
                    created_at=created_at,
                    wallets=wallets,
                    linked_event_id=event_id,
                    event_type=event.event_type,
                    reference_type=event.reference_type,
                )
            )
            continue

        if consumes:
            amount = sum(int(row.amount or 0) for row in consumes)
            title = "Used from reserve" if goal.intent == models.GoalIntent.RESERVE else "Goal money used"
            payment_wallets = [
                _activity_wallet(
                    role="paid_from",
                    wallet=wallets_by_id.get(int(leg.wallet_id)),
                    wallet_id=int(leg.wallet_id),
                    amount=abs(int(leg.amount or 0)),
                )
                for leg in wallet_legs_by_event_id.get(event_id, [])
                if int(leg.amount or 0) < 0
            ]
            funding_wallets = [
                _activity_wallet(
                    role="released_from",
                    wallet=wallets_by_id.get(int(row.wallet_id)),
                    wallet_id=int(row.wallet_id),
                    amount=int(row.amount or 0),
                )
                for row in consumes
            ]
            items.append(
                schemas.GoalActivityItemOut(
                    id=f"goal-money-used:{event_id}",
                    type="GOAL_MONEY_USED",
                    title=title,
                    description=_activity_event_description(event),
                    amount=int(amount),
                    currency=goal.currency,
                    date=activity_date,
                    time_label=_goal_activity_time_from_created_at(created_at, user_tz),
                    created_at=created_at,
                    wallets=payment_wallets + funding_wallets,
                    linked_event_id=event_id,
                    event_type=event.event_type if event else None,
                    reference_type=event.reference_type if event else None,
                )
            )

        for row in returns:
            if event is not None and event.event_type == models.TransactionType.TRANSFER:
                title = "Unreserved after wallet transfer"
                activity_type = "UNRESERVED"
            else:
                title = "Unreserved money"
                activity_type = "UNRESERVED"
            items.append(
                schemas.GoalActivityItemOut(
                    id=f"goal-return:{row.id}",
                    type=activity_type,
                    title=title,
                    description=_activity_event_description(event),
                    amount=int(row.amount or 0),
                    currency=goal.currency,
                    date=activity_date,
                    time_label=_goal_activity_time_from_created_at(row.created_at, user_tz),
                    created_at=row.created_at,
                    wallets=[
                        _activity_wallet(
                            role="from",
                            wallet=wallets_by_id.get(int(row.wallet_id)),
                            wallet_id=int(row.wallet_id),
                            amount=int(row.amount or 0),
                        )
                    ],
                    linked_event_id=event_id,
                    event_type=event.event_type if event else None,
                    reference_type=event.reference_type if event else None,
                )
            )

        for row in allocations:
            items.append(
                schemas.GoalActivityItemOut(
                    id=f"goal-allocation:{row.id}",
                    type="RESERVED",
                    title="Reserved money",
                    description=_activity_event_description(event),
                    amount=int(row.amount or 0),
                    currency=goal.currency,
                    date=activity_date,
                    time_label=_goal_activity_time_from_created_at(row.created_at, user_tz),
                    created_at=row.created_at,
                    wallets=[
                        _activity_wallet(
                            role="wallet",
                            wallet=wallets_by_id.get(int(row.wallet_id)),
                            wallet_id=int(row.wallet_id),
                            amount=int(row.amount or 0),
                        )
                    ],
                    linked_event_id=event_id,
                    event_type=event.event_type if event else None,
                    reference_type=event.reference_type if event else None,
                )
            )

    for row in standalone_contributions:
        if row.contribution_type == models.GoalContributionType.ALLOCATE:
            activity_type = "RESERVED"
            title = "Reserved money"
            role = "wallet"
        elif row.contribution_type == models.GoalContributionType.RETURN:
            activity_type = "UNRESERVED"
            title = "Unreserved money"
            role = "from"
        else:
            activity_type = "GOAL_MONEY_USED"
            title = "Used from reserve" if goal.intent == models.GoalIntent.RESERVE else "Goal money used"
            role = "released_from"

        items.append(
            schemas.GoalActivityItemOut(
                id=f"goal-contribution:{row.id}",
                type=activity_type,
                title=title,
                amount=int(row.amount or 0),
                currency=goal.currency,
                date=_goal_activity_date_from_created_at(row.created_at, user_tz),
                time_label=_goal_activity_time_from_created_at(row.created_at, user_tz),
                created_at=row.created_at,
                wallets=[
                    _activity_wallet(
                        role=role,
                        wallet=wallets_by_id.get(int(row.wallet_id)),
                        wallet_id=int(row.wallet_id),
                        amount=int(row.amount or 0),
                    )
                ],
            )
        )

    for release in project_releases:
        items.append(
            schemas.GoalActivityItemOut(
                id=f"project-release:{release.id}",
                type="RELEASED_TO_PROJECT",
                title="Moved to project",
                description=release.note,
                amount=int(release.amount or 0),
                currency=goal.currency,
                date=release.released_at,
                time_label=_goal_activity_time_from_created_at(release.created_at, user_tz),
                created_at=release.created_at,
                wallets=[
                    _activity_wallet(
                        role="from",
                        wallet=wallets_by_id.get(int(release.wallet_id)) if release.wallet_id is not None else None,
                        wallet_id=int(release.wallet_id or 0),
                        amount=int(release.amount or 0),
                    )
                ] if release.wallet_id is not None else [],
            )
        )

    items.sort(key=lambda item: (item.created_at, item.id))
    return schemas.GoalActivityOut(goal_id=int(goal.id), items=items)


def _get_goal_project_or_none(db: Session, user_id: int, goal_id: int) -> models.Project | None:
    return (
        db.query(models.Project)
        .filter(
            models.Project.owner_id == user_id,
            models.Project.origin_goal_id == goal_id,
        )
        .first()
    )


def _get_goal_project_or_404(db: Session, user_id: int, goal_id: int) -> models.Project:
    project = _get_goal_project_or_none(db, user_id, goal_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="projects.not_found")
    return project


def _get_project_summary_or_404(
    db: Session,
    user_id: int,
    project_id: int,
    default_budget_date: date,
) -> schemas.ProjectBudgetOut:
    summary = next(
        (
            item
            for item in get_project_budget_summaries(
                db,
                user_id,
                default_budget_date=default_budget_date,
            )
            if item.id == project_id
        ),
        None,
    )
    if summary is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="projects.not_found")
    return summary


def _ensure_linked_goal_record(
    db: Session,
    model,
    user_id: int,
    record_id: int | None,
    detail: str,
) -> None:
    if record_id is None:
        return
    exists = (
        db.query(model.id)
        .filter(model.id == record_id, model.owner_id == user_id)
        .scalar()
    )
    if exists is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


def _ensure_linked_expense_event(db: Session, user_id: int, event_id: int | None) -> None:
    if event_id is None:
        return
    exists = (
        db.query(models.FinancialEvent.id)
        .filter(
            models.FinancialEvent.id == event_id,
            models.FinancialEvent.owner_id == user_id,
            models.FinancialEvent.event_type == models.TransactionType.EXPENSE,
        )
        .scalar()
    )
    if exists is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="expenses.not_found")


def _validate_goal_links(db: Session, user_id: int, payload) -> None:
    _ensure_linked_goal_record(db, models.Asset, user_id, payload.linked_asset_id, "assets.not_found")
    _ensure_linked_goal_record(db, models.Debt, user_id, payload.linked_debt_id, "debts.not_found")
    _ensure_linked_goal_record(
        db,
        models.PaymentPlan,
        user_id,
        payload.linked_payment_plan_id,
        "payment_plans.not_found",
    )
    _ensure_linked_expense_event(db, user_id, payload.linked_expense_event_id)
    linked_debt_id = getattr(payload, "linked_debt_id", None)
    linked_plan_id = getattr(payload, "linked_payment_plan_id", None)
    if linked_debt_id is not None and linked_plan_id is not None:
        plan_debt_id = (
            db.query(models.PaymentPlan.debt_id)
            .filter(
                models.PaymentPlan.id == linked_plan_id,
                models.PaymentPlan.owner_id == user_id,
            )
            .scalar()
        )
        if plan_debt_id is not None and int(plan_debt_id) != int(linked_debt_id):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="goals.payment_plan_link_mismatch")


def _build_goal_debt_out(db: Session, debt: models.Debt) -> schemas.DebtOut:
    debt_out = schemas.DebtOut.model_validate(debt)
    debt_out.total_charges = get_debt_total_charges(db, debt.id)
    debt_out.total_paid = get_debt_total_paid(db, debt.id)
    return debt_out


def _raise_debt_policy_denied(decision) -> None:
    if decision.allowed:
        return
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=decision.reason_code or "debts.policy.action_blocked",
    )


def _ensure_no_other_active_debt_goal(
    db: Session,
    user_id: int,
    debt_id: int,
    *,
    current_goal_id: int | None = None,
) -> None:
    query = db.query(models.Goals.id).filter(
        models.Goals.owner_id == user_id,
        models.Goals.intent == models.GoalIntent.PAY_OBLIGATION,
        models.Goals.linked_debt_id == debt_id,
        models.Goals.status == models.GoalStatus.ACTIVE,
    )
    if current_goal_id is not None:
        query = query.filter(models.Goals.id != current_goal_id)
    if query.first() is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="goals.debt_goal_already_open",
        )


def _ensure_no_other_active_payment_plan_goal(
    db: Session,
    user_id: int,
    plan_id: int,
    *,
    current_goal_id: int | None = None,
) -> None:
    query = db.query(models.Goals.id).filter(
        models.Goals.owner_id == user_id,
        models.Goals.intent == models.GoalIntent.PAY_OBLIGATION,
        models.Goals.linked_payment_plan_id == plan_id,
        models.Goals.status == models.GoalStatus.ACTIVE,
    )
    if current_goal_id is not None:
        query = query.filter(models.Goals.id != current_goal_id)
    if query.first() is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="goals.payment_plan_goal_already_open",
        )


def _safe_generated_goal_title(title: str) -> str:
    value = title.strip()
    if len(value) > 32:
        value = value[:32].rstrip()
    if len(value) < 3:
        return "Next payment"
    return value


def _create_next_payment_goal_for_payment_plan(
    db: Session,
    user_id: int,
    plan: models.PaymentPlan,
    bridge: schemas.GoalPurchasePaymentPlanCreate,
) -> models.Goals | None:
    if not bridge.create_next_payment_goal:
        return None
    next_payment = get_next_payment_plan_goal_payment(db, user_id, plan.id)
    if next_payment is None:
        return None

    _ensure_active_goal_capacity(db, user_id)
    _ensure_no_other_active_payment_plan_goal(db, user_id, int(plan.id))

    target_amount = max(
        0,
        int(next_payment.amount or 0)
        - int(next_payment.paid_amount or 0)
        - int(next_payment.written_off_amount or 0),
    )
    if target_amount <= 0:
        return None

    goal = models.Goals(
        owner_id=user_id,
        title=_safe_generated_goal_title(bridge.next_goal_title or f"{plan.item_name} payment"),
        target_amount=target_amount,
        currency=plan.currency or "UZS",
        intent=models.GoalIntent.PAY_OBLIGATION,
        debt_goal_tracking_mode=models.DebtGoalTrackingMode.FIXED_DEBT_AMOUNT,
        target_date=bridge.next_goal_target_date or next_payment.due_date,
        linked_debt_id=None,
        linked_payment_plan_id=plan.id,
        status=models.GoalStatus.ACTIVE,
    )
    db.add(goal)
    db.flush()
    return goal


def _create_payment_plan_bridge_from_goal_purchase(
    db: Session,
    user_id: int,
    *,
    goal: models.Goals,
    payload: schemas.GoalUsePlannedPurchaseCreate,
    event: models.FinancialEvent,
    asset: models.Asset | None,
    title: str,
    effective_date: date,
    user_tz: tzinfo,
) -> tuple[models.PaymentPlan | None, models.Goals | None]:
    bridge = payload.payment_plan
    if bridge is None:
        return None, None
    if int(bridge.total_price) <= int(payload.amount):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="goals.payment_plan_total_must_exceed_down_payment")
    if bridge.plan_type == models.PaymentPlanType.BANK_LOAN:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="goals.payment_plan_bridge_bank_loan_not_supported")

    from .payment_plans import _create_payment_plan_in_transaction

    plan_payload = schemas.PaymentPlanCreate(
        item_name=(bridge.item_name or title).strip(),
        store_or_bank_name=bridge.store_or_bank_name,
        plan_type=bridge.plan_type,
        total_price=int(bridge.total_price),
        down_payment=int(payload.amount),
        months=int(bridge.months),
        frequency=bridge.frequency,
        start_date=bridge.start_date or effective_date,
        expense_category=payload.category,
        expense_subcategory_id=payload.subcategory_id,
        project_id=payload.project_id,
        project_subcategory_id=payload.project_subcategory_id,
        wallet_allocations=[],
        track_as_asset=False,
    )
    plan = _create_payment_plan_in_transaction(
        db,
        user_id,
        plan_payload,
        user_tz=user_tz,
        existing_down_payment_event=event,
        linked_asset_id=asset.id if asset is not None else None,
    )
    goal.linked_payment_plan_id = plan.id
    next_goal = _create_next_payment_goal_for_payment_plan(db, user_id, plan, bridge)
    return plan, next_goal


def _normalize_pay_obligation_goal(
    db: Session,
    user_id: int,
    *,
    debt_id: int | None,
    payment_plan_id: int | None = None,
    target_amount: int,
    currency: str,
    tracking_mode: models.DebtGoalTrackingMode | None,
    current_goal_id: int | None = None,
) -> tuple[models.Debt | None, models.DebtGoalTrackingMode, int, int | None]:
    if debt_id is None and payment_plan_id is not None:
        plan = (
            db.query(models.PaymentPlan)
            .filter(models.PaymentPlan.id == payment_plan_id, models.PaymentPlan.owner_id == user_id)
            .first()
        )
        if plan is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="payment_plans.not_found")
        if plan.currency != currency:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="goals.currency_mismatch")

        earliest_pending = get_next_payment_plan_goal_payment(db, user_id, plan.id)
        if earliest_pending is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="goals.payment_plan_fully_paid")

        normalized_target = (
            int(earliest_pending.amount)
            - int(earliest_pending.paid_amount)
            - int(earliest_pending.written_off_amount or 0)
        )
        if normalized_target <= 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="goals.payment_plan_fully_paid")

        _ensure_no_other_active_payment_plan_goal(
            db,
            user_id,
            int(plan.id),
            current_goal_id=current_goal_id,
        )
        return None, models.DebtGoalTrackingMode.FIXED_DEBT_AMOUNT, normalized_target, plan.id

    if debt_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="goals.debt_goal_requires_debt")

    debt = (
        db.query(models.Debt)
        .filter(models.Debt.id == debt_id, models.Debt.owner_id == user_id)
        .first()
    )
    if debt is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="debts.not_found")
    if debt.debt_type != models.DebtType.OWING:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="goals.debt_goal_requires_i_owe_debt")
    if debt.archived_at is not None or int(debt.remaining_amount or 0) <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="goals.debt_goal_requires_open_debt")
    if debt.currency != currency:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="goals.currency_mismatch")

    _ensure_no_other_active_debt_goal(db, user_id, debt.id, current_goal_id=current_goal_id)

    remaining_debt = int(debt.remaining_amount or 0)
    mode = tracking_mode
    if mode is None:
        mode = (
            models.DebtGoalTrackingMode.FULL_REMAINING_DEBT
            if int(target_amount) == remaining_debt
            else models.DebtGoalTrackingMode.FIXED_DEBT_AMOUNT
        )

    if mode == models.DebtGoalTrackingMode.FULL_REMAINING_DEBT:
        normalized_target = remaining_debt
    else:
        normalized_target = int(target_amount)
        if normalized_target > remaining_debt:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="goals.debt_goal_target_exceeds_debt")

    return debt, mode, normalized_target, None


def _create_goal_expense_event(
    db: Session,
    user_id: int,
    *,
    wallet_allocations: list[tuple[models.Wallet, int]],
    amount: int,
    category: models.ExpenseCategory,
    expense_date: date,
    local_today: date,
    title: str,
    description: str | None,
    subcategory_id: int | None = None,
    project_id: int | None = None,
    project_subcategory_id: int | None = None,
    reference_type: str = models.ReferenceType.GOAL_CONSUME,
    enforce_goal_protection: bool = False,
    enforce_monthly_budget_limits: bool = True,
) -> models.FinancialEvent:
    try:
        posted = post_expense_event(
            db,
            user_id,
            title=title,
            amount=int(amount),
            category=category,
            expense_date=expense_date,
            description=description,
            wallet_allocations=[
                {"wallet_id": wallet.id, "amount": int(allocation_amount)}
                for wallet, allocation_amount in wallet_allocations
            ],
            subcategory_id=subcategory_id,
            project_id=project_id,
            project_subcategory_id=project_subcategory_id,
            reference_type=reference_type,
            local_today=local_today,
            enforce_goal_protection=enforce_goal_protection,
            enforce_monthly_budget_limits=enforce_monthly_budget_limits,
        )
    except HTTPException as exc:
        if exc.detail == "expenses.wallet_allocation_total_mismatch":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="goals.payment_allocation_total_mismatch") from exc
        raise
    return posted.event


def _resolve_goal_payment_allocations(
    db: Session,
    user_id: int,
    goal: models.Goals,
    payment_allocations: list[schemas.GoalPaymentAllocationCreate],
    amount: int,
) -> list[tuple[models.Wallet, int]]:
    total_allocated = int(sum(int(item.amount) for item in payment_allocations))
    if total_allocated != int(amount):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="goals.payment_allocation_total_mismatch")

    seen_wallet_ids: set[int] = set()
    resolved: list[tuple[models.Wallet, int]] = []
    for allocation in payment_allocations:
        if allocation.wallet_id in seen_wallet_ids:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="goals.payment_allocation_duplicate")
        seen_wallet_ids.add(allocation.wallet_id)

        wallet = validate_wallet_for_goal_release(db, user_id, goal, allocation.wallet_id)
        if not wallet.is_active:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="wallets.archived_locked")
        resolved.append((wallet, int(allocation.amount)))
    return resolved


def _validate_planned_purchase_payment_row_limit(
    payment_allocations: list[schemas.GoalPaymentAllocationCreate],
) -> None:
    if len(payment_allocations) > MAX_PLANNED_PURCHASE_PAYMENT_WALLETS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="goals.payment_allocation_limit_exceeded",
        )


def _validate_goal_funded_payment_wallets_are_owned_money(
    payment_allocations: list[tuple[models.Wallet, int]],
) -> None:
    for wallet, amount in payment_allocations:
        if (
            wallet.wallet_type == models.WalletType.CREDIT
            or wallet.accounting_type != models.AccountingType.ASSET
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="goals.goal_funded_payment_wallet_must_be_owned_money",
            )
        if int(amount) > max(int(wallet.current_balance or 0), 0):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="goals.goal_funded_payment_wallet_insufficient_owned_balance",
            )


def _validate_prepare_payment_target_wallet(
    db: Session,
    user_id: int,
    goal: models.Goals,
    wallet_id: int,
) -> models.Wallet:
    wallet = (
        db.query(models.Wallet)
        .filter(models.Wallet.id == wallet_id, models.Wallet.owner_id == user_id)
        .with_for_update()
        .first()
    )
    if wallet is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="wallets.not_found")
    if not wallet.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="wallets.archived_locked")
    if wallet.currency != goal.currency:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="goals.currency_mismatch")
    if wallet.accounting_type != models.AccountingType.ASSET or wallet.wallet_type == models.WalletType.CREDIT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="goals.prepare_payment_target_must_be_owned_money",
        )
    return wallet


def _get_goal_unreleased_sources(
    db: Session,
    user_id: int,
    goal_id: int,
) -> list[schemas.GoalFundingSourceOut]:
    goal = _get_owned_goal_or_404(db, user_id, goal_id)
    return [
        source
        for source in build_goal_with_progress(
            db,
            user_id,
            goal,
            get_goal_funded_amount(db, user_id, goal_id),
            released_amount=get_goal_released_amount(db, user_id, goal_id),
            linked_project_id=get_goal_linked_project_id(db, user_id, goal_id),
        ).funding_sources
        if int(source.unreleased_amount or 0) > 0
    ]


def _build_goal_funding_plan(
    db: Session,
    user_id: int,
    goal: models.Goals,
    amount: int,
    *,
    preferred_wallet_id: int | None = None,
    preferred_wallet_ids: list[int] | None = None,
    require_full_coverage: bool = True,
) -> list[tuple[int, int]]:
    sources = _get_goal_unreleased_sources(db, user_id, goal.id)
    if preferred_wallet_ids:
        preferred_order = {wallet_id: index for index, wallet_id in enumerate(preferred_wallet_ids)}
        sources = sorted(
            sources,
            key=lambda source: (preferred_order.get(source.wallet_id, len(preferred_order)), source.wallet_id),
        )
    elif preferred_wallet_id is not None:
        sources = sorted(
            sources,
            key=lambda source: (source.wallet_id != preferred_wallet_id, source.wallet_id),
        )
    else:
        sources = sorted(sources, key=lambda source: source.wallet_id)

    remaining = int(amount)
    plan: list[tuple[int, int]] = []
    for source in sources:
        if remaining <= 0:
            break
        use_amount = min(int(source.unreleased_amount), remaining)
        if use_amount > 0:
            plan.append((int(source.wallet_id), int(use_amount)))
            remaining -= use_amount

    if remaining > 0 and require_full_coverage:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="goals.insufficient_unreleased_balance")
    return plan


def _build_direct_payment_funding_plan(
    db: Session,
    user_id: int,
    goal: models.Goals,
    payment_plan: list[tuple[int, int]],
    *,
    require_full_coverage: bool,
) -> list[tuple[int, int]]:
    sources_by_wallet = {
        int(source.wallet_id): int(source.unreleased_amount)
        for source in _get_goal_unreleased_sources(db, user_id, goal.id)
    }

    plan: list[tuple[int, int]] = []
    for wallet_id, payment_amount in payment_plan:
        available = int(sources_by_wallet.get(int(wallet_id), 0))
        if available <= 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="goals.payment_wallet_not_funding_source")
        use_amount = min(int(payment_amount), available)
        if require_full_coverage and use_amount < int(payment_amount):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="goals.insufficient_wallet_goal_balance")
        if use_amount > 0:
            plan.append((int(wallet_id), int(use_amount)))
    return plan


def _consume_goal_funding_plan(
    db: Session,
    user_id: int,
    goal: models.Goals,
    plan: list[tuple[int, int]],
    *,
    linked_event_id: int,
) -> int:
    total = 0
    for wallet_id, amount in plan:
        if amount <= 0:
            continue
        validate_wallet_for_goal_release(db, user_id, goal, wallet_id)
        record_goal_contribution(
            db=db,
            user_id=user_id,
            goal_id=goal.id,
            wallet_id=wallet_id,
            amount=amount,
            contribution_type=models.GoalContributionType.CONSUME,
            linked_event_id=linked_event_id,
        )
        total += int(amount)
    return total


def _pay_linked_payment_plan_from_goal(
    *,
    db: Session,
    user_id: int,
    goal: models.Goals,
    payload: schemas.GoalDebtPaymentCreate,
    user_tz: tzinfo,
) -> schemas.GoalDebtPaymentResultOut:
    if goal.linked_payment_plan_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="goals.debt_goal_requires_debt")

    from .payment_plans import (
        _apply_amount_to_payment_plan_payment,
        _build_schedule_allocation_plan,
        _create_payment_plan_expense_event,
        _payment_component_type,
        _remaining_payment_amount,
        _resolve_existing_plan_category,
        _take_wallet_allocations,
        _unpaid_schedule_total,
    )

    plan = (
        db.query(models.PaymentPlan)
        .options(
            selectinload(models.PaymentPlan.payments).selectinload(models.PaymentPlanPayment.allocations),
        )
        .filter(
            models.PaymentPlan.id == goal.linked_payment_plan_id,
            models.PaymentPlan.owner_id == user_id,
        )
        .with_for_update()
        .first()
    )
    if plan is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="payment_plans.not_found")
    if plan.status == models.PaymentPlanStatus.ARCHIVED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="payment_plans.archived_locked")

    amount = int(payload.amount)
    if amount <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="debts.payment.amount_required")
    if amount > _unpaid_schedule_total(plan):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="payment_plans.payment.amount_exceeds_schedule")

    next_payment = get_next_payment_plan_goal_payment(db, user_id, plan.id)
    if next_payment is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="goals.payment_plan_fully_paid")
    if amount > _remaining_payment_amount(next_payment):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="goals.payment_plan_payment_exceeds_next_payment")

    payment_allocations = _resolve_goal_payment_allocations(
        db,
        user_id,
        goal,
        payload.payment_allocations,
        amount,
    )
    _validate_goal_funded_payment_wallets_are_owned_money(payment_allocations)
    payment_plan = [(int(wallet.id), int(payment_amount)) for wallet, payment_amount in payment_allocations]
    funding_plan = _build_direct_payment_funding_plan(
        db=db,
        user_id=user_id,
        goal=goal,
        payment_plan=payment_plan,
        require_full_coverage=True,
    )

    schedule_allocations = _build_schedule_allocation_plan(plan, amount)
    paid_date = payload.date or today_in_tz(user_tz)
    payment_category = _resolve_existing_plan_category(plan, None)
    if plan.expense_category is None:
        plan.expense_category = payment_category

    component_totals: dict[models.PaymentPlanPaymentComponentType, int] = {}
    component_order: list[models.PaymentPlanPaymentComponentType] = []
    for payment, allocation_amount in schedule_allocations:
        component_type = _payment_component_type(payment)
        if component_type not in component_totals:
            component_order.append(component_type)
            component_totals[component_type] = 0
        component_totals[component_type] += int(allocation_amount)

    remaining_wallet_allocations = [
        {"wallet_id": int(wallet.id), "amount": int(payment_amount)}
        for wallet, payment_amount in payment_allocations
    ]
    financial_events_by_component: dict[models.PaymentPlanPaymentComponentType, models.FinancialEvent] = {}
    for component_type in component_order:
        component_amount = int(component_totals[component_type])
        component_allocations = _take_wallet_allocations(remaining_wallet_allocations, component_amount)
        is_charge = component_type == models.PaymentPlanPaymentComponentType.CHARGE
        financial_events_by_component[component_type] = _create_payment_plan_expense_event(
            db,
            user_id,
            title=f"{plan.item_name} {'charge ' if is_charge else ''}payment",
            amount=component_amount,
            category=models.ExpenseCategory.DEBT_CHARGES if is_charge else plan.expense_category,
            expense_date=paid_date,
            wallet_allocations=component_allocations,
            reference_type=(
                models.ReferenceType.PAYMENT_PLAN_FEE
                if is_charge
                else models.ReferenceType.PAYMENT_PLAN_PAYMENT
            ),
            payment_plan_id=plan.id,
            subcategory_id=None if is_charge else plan.expense_subcategory_id,
            project_id=None if is_charge else plan.project_id,
            project_subcategory_id=None if is_charge else plan.project_subcategory_id,
            note=payload.note or f"{plan.item_name} payment_plan payment",
            user_tz=user_tz,
        )

    payment_plan_transaction = models.PaymentPlanTransaction(
        owner_id=user_id,
        plan_id=plan.id,
        amount=amount,
        date=paid_date,
        note=payload.note or f"Goal payment for {plan.item_name}",
    )
    db.add(payment_plan_transaction)
    db.flush()

    for wallet, payment_amount in payment_allocations:
        db.add(models.PaymentPlanTransactionWalletAllocation(
            owner_id=user_id,
            plan_id=plan.id,
            payment_plan_transaction_id=payment_plan_transaction.id,
            wallet_id=wallet.id,
            amount=int(payment_amount),
        ))

    plan.remaining_amount = int(plan.remaining_amount or 0) - amount
    ledger_entries_by_component: dict[models.PaymentPlanPaymentComponentType, models.PaymentPlanLedgerEntry] = {}
    linked_event_id: int | None = None
    for component_type in component_order:
        component_amount = int(component_totals[component_type])
        is_charge = component_type == models.PaymentPlanPaymentComponentType.CHARGE
        financial_event = financial_events_by_component.get(component_type)
        if linked_event_id is None and financial_event is not None:
            linked_event_id = financial_event.id
        ledger_entry = models.PaymentPlanLedgerEntry(
            owner_id=user_id,
            plan_id=plan.id,
            financial_event_id=financial_event.id if financial_event is not None else None,
            source_transaction_id=payment_plan_transaction.id,
            entry_type=models.PaymentPlanLedgerEntryType.PAYMENT,
            amount_delta=-component_amount,
            principal_delta=0 if is_charge else -component_amount,
            charge_delta=-component_amount if is_charge else 0,
            balance_after=int(plan.remaining_amount or 0),
            entry_date=paid_date,
            source=models.PaymentPlanLedgerEntrySource.USER,
            note=payment_plan_transaction.note,
        )
        db.add(ledger_entry)
        db.flush()
        ledger_entries_by_component[component_type] = ledger_entry

    for payment, allocation_amount in schedule_allocations:
        component_type = _payment_component_type(payment)
        _apply_amount_to_payment_plan_payment(
            db,
            owner_id=user_id,
            payment=payment,
            amount=allocation_amount,
            paid_date=paid_date,
            debt_transaction=payment_plan_transaction,
            debt_ledger_entry=ledger_entries_by_component[component_type],
            note=payload.note,
        )

    if linked_event_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="goals.payment_plan_payment_missing_event")
    consumed_amount = _consume_goal_funding_plan(
        db,
        user_id,
        goal,
        funding_plan,
        linked_event_id=linked_event_id,
    )

    if plan.status != models.PaymentPlanStatus.ARCHIVED:
        plan.status = (
            models.PaymentPlanStatus.PAID
            if int(plan.remaining_amount or 0) <= 0 and _unpaid_schedule_total(plan) <= 0
            else models.PaymentPlanStatus.ACTIVE
        )

    reserved_after = get_goal_funded_amount(db, user_id, goal.id)
    if plan.status == models.PaymentPlanStatus.PAID:
        goal.status = models.GoalStatus.COMPLETED
    else:
        sync_goal_status(goal, reserved_after)

    db.commit()
    db.refresh(goal)
    db.refresh(plan)
    db.refresh(payment_plan_transaction)
    return schemas.GoalDebtPaymentResultOut(
        goal=build_goal_with_progress(
            db,
            user_id,
            goal,
            get_goal_funded_amount(db, user_id, goal.id),
            released_amount=get_goal_released_amount(db, user_id, goal.id),
            linked_project_id=get_goal_linked_project_id(db, user_id, goal.id),
            today=today_in_tz(user_tz),
        ),
        payment_plan=schemas.PaymentPlanWithPaymentsOut.model_validate(plan),
        payment_plan_transaction_id=payment_plan_transaction.id,
        consumed_amount=consumed_amount,
    )


def _return_goal_funding_plan_entries(
    db: Session,
    user_id: int,
    goal: models.Goals,
    plan: list[tuple[int, int]],
    *,
    linked_event_id: int | None = None,
) -> tuple[int, list[models.GoalContributions]]:
    total = 0
    entries: list[models.GoalContributions] = []
    for wallet_id, amount in plan:
        if amount <= 0:
            continue
        validate_wallet_for_goal_release(db, user_id, goal, wallet_id)
        contribution = record_goal_contribution(
            db=db,
            user_id=user_id,
            goal_id=goal.id,
            wallet_id=wallet_id,
            amount=amount,
            contribution_type=models.GoalContributionType.RETURN,
            linked_event_id=linked_event_id,
        )
        entries.append(contribution)
        total += int(amount)
    return total, entries


def _return_goal_funding_plan(
    db: Session,
    user_id: int,
    goal: models.Goals,
    plan: list[tuple[int, int]],
    *,
    linked_event_id: int | None = None,
) -> int:
    total, _ = _return_goal_funding_plan_entries(
        db,
        user_id,
        goal,
        plan,
        linked_event_id=linked_event_id,
    )
    return total


def _archive_goal_and_release_funds(
    db: Session,
    user_id: int,
    goal: models.Goals,
    funded_amount: int,
    released_amount: int,
    today: date | None = None,
) -> schemas.GoalWithProgressOut:
    unreleased_amount = max(int(funded_amount) - int(released_amount), 0)
    if unreleased_amount > 0:
        return_all_unreleased_goal_funding(db=db, user_id=user_id, goal_id=goal.id)
        funded_amount = get_goal_funded_amount(db, user_id, goal.id)

    goal.status = models.GoalStatus.ARCHIVED
    db.commit()
    db.refresh(goal)
    return build_goal_with_progress(
        db,
        user_id,
        goal,
        funded_amount,
        released_amount=released_amount,
        linked_project_id=get_goal_linked_project_id(db, user_id, goal.id),
        today=today,
    )


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


@router.get("/funding-summary", response_model=schemas.GoalFundingSummaryOut)
def get_goal_funding_summary(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
):
    ensure_premium_user(current_user)
    return build_goal_funding_summary(db, current_user.id)


@router.get("/{goal_id}/activity", response_model=schemas.GoalActivityOut)
def get_goal_activity(
    goal_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
    user_tz: tzinfo = Depends(get_effective_user_timezone),
):
    ensure_premium_user(current_user)
    goal = _get_owned_goal_or_404(db, current_user.id, goal_id)
    return _build_goal_activity(db, current_user.id, goal, user_tz)


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
    for key, value in rate_headers.items():
        response.headers[key] = value
    _ensure_active_goal_capacity(db, current_user.id)
    _validate_goal_links(db, current_user.id, payload)
    target_amount = int(payload.target_amount)
    debt_goal_tracking_mode = (
        payload.debt_goal_tracking_mode
        if payload.intent == models.GoalIntent.PAY_OBLIGATION
        else None
    )
    if payload.intent == models.GoalIntent.PAY_OBLIGATION:
        _debt, debt_goal_tracking_mode, target_amount, linked_plan_id = _normalize_pay_obligation_goal(
            db,
            current_user.id,
            debt_id=payload.linked_debt_id,
            payment_plan_id=payload.linked_payment_plan_id,
            target_amount=target_amount,
            currency=payload.currency,
            tracking_mode=debt_goal_tracking_mode,
        )
        payload.linked_payment_plan_id = linked_plan_id

    goal = models.Goals(
        owner_id=current_user.id,
        title=payload.title.strip(),
        target_amount=target_amount,
        currency=payload.currency,
        intent=payload.intent,
        debt_goal_tracking_mode=debt_goal_tracking_mode,
        template=payload.template,
        target_date=payload.target_date,
        linked_asset_id=payload.linked_asset_id,
        linked_debt_id=payload.linked_debt_id,
        linked_payment_plan_id=payload.linked_payment_plan_id,
        linked_expense_event_id=payload.linked_expense_event_id,
        status=models.GoalStatus.ACTIVE,
    )
    db.add(goal)
    db.commit()
    db.refresh(goal)
    return build_goal_with_progress(
        db,
        current_user.id,
        goal,
        0,
        released_amount=0,
        linked_project_id=None,
        today=today_in_tz(user_tz),
    )


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
    for key, value in rate_headers.items():
        response.headers[key] = value

    today = today_in_tz(user_tz)
    goal = _get_owned_goal_or_404(db, current_user.id, goal_id)
    if goal.status == models.GoalStatus.GRADUATED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="goals.graduated_read_only")
    funded_amount = get_goal_funded_amount(db, current_user.id, goal.id)
    normalized_debt_goal_mode = (
        payload.debt_goal_tracking_mode
        if "debt_goal_tracking_mode" in payload.model_fields_set
        else goal.debt_goal_tracking_mode
    )
    normalized_target_amount = (
        int(payload.target_amount)
        if "target_amount" in payload.model_fields_set and payload.target_amount is not None
        else int(goal.target_amount)
    )
    next_currency = (
        payload.currency
        if "currency" in payload.model_fields_set and payload.currency is not None
        else goal.currency
    )
    next_intent = (
        payload.intent
        if "intent" in payload.model_fields_set and payload.intent is not None
        else goal.intent
    )
    if (
        "status" in payload.model_fields_set
        and payload.status == models.GoalStatus.COMPLETED
        and next_intent == models.GoalIntent.FUND_PROJECT
    ):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="goals.fund_project_cannot_complete")
    next_debt_id = (
        payload.linked_debt_id
        if "linked_debt_id" in payload.model_fields_set
        else goal.linked_debt_id
    )
    next_plan_id = (
        payload.linked_payment_plan_id
        if "linked_payment_plan_id" in payload.model_fields_set
        else goal.linked_payment_plan_id
    )
    if next_intent == models.GoalIntent.PAY_OBLIGATION:
        _debt, normalized_debt_goal_mode, normalized_target_amount, linked_plan_id = _normalize_pay_obligation_goal(
            db,
            current_user.id,
            debt_id=next_debt_id,
            payment_plan_id=next_plan_id,
            target_amount=normalized_target_amount,
            currency=next_currency,
            tracking_mode=normalized_debt_goal_mode,
            current_goal_id=goal.id,
        )
        goal.linked_payment_plan_id = linked_plan_id
        debt_progress_amount = (
            int(funded_amount)
            if linked_plan_id is not None
            else get_goal_consumed_amount(db, current_user.id, goal.id) + int(funded_amount)
        )
        if normalized_target_amount < debt_progress_amount:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="goals.target_below_funded_amount",
            )

    if "title" in payload.model_fields_set and payload.title is not None:
        goal.title = payload.title.strip()
    if "target_amount" in payload.model_fields_set and payload.target_amount is not None:
        if normalized_target_amount < funded_amount:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="goals.target_below_funded_amount",
            )
        goal.target_amount = normalized_target_amount
    elif next_intent == models.GoalIntent.PAY_OBLIGATION and int(goal.target_amount) != int(normalized_target_amount):
        goal.target_amount = normalized_target_amount
    if "currency" in payload.model_fields_set and payload.currency is not None:
        if funded_amount > 0 and payload.currency != goal.currency:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="goals.currency_change_requires_zero_funding",
            )
        goal.currency = payload.currency
    if "intent" in payload.model_fields_set and payload.intent is not None:
        goal.intent = payload.intent
    if "debt_goal_tracking_mode" in payload.model_fields_set or next_intent == models.GoalIntent.PAY_OBLIGATION:
        goal.debt_goal_tracking_mode = normalized_debt_goal_mode if next_intent == models.GoalIntent.PAY_OBLIGATION else None
    if "template" in payload.model_fields_set:
        goal.template = payload.template
    link_fields = {
        "linked_asset_id",
        "linked_debt_id",
        "linked_payment_plan_id",
        "linked_expense_event_id",
    }
    if any(field in payload.model_fields_set for field in link_fields):
        _validate_goal_links(db, current_user.id, payload)
        if "linked_asset_id" in payload.model_fields_set:
            goal.linked_asset_id = payload.linked_asset_id
        if "linked_debt_id" in payload.model_fields_set:
            goal.linked_debt_id = payload.linked_debt_id
        if "linked_payment_plan_id" in payload.model_fields_set:
            goal.linked_payment_plan_id = payload.linked_payment_plan_id
        if "linked_expense_event_id" in payload.model_fields_set:
            goal.linked_expense_event_id = payload.linked_expense_event_id
    if "target_date" in payload.model_fields_set:
        goal.target_date = payload.target_date
    if (
        "status" in payload.model_fields_set
        and payload.status is not None
        and payload.status == models.GoalStatus.ARCHIVED
    ):
        if goal.status != models.GoalStatus.ARCHIVED:
            _ensure_archived_goal_capacity(db, current_user.id)
        return _archive_goal_and_release_funds(
            db,
            current_user.id,
            goal,
            funded_amount,
            get_goal_released_amount(db, current_user.id, goal.id),
            today=today,
        )

    sync_goal_status(goal, funded_amount)
    db.commit()
    db.refresh(goal)
    return build_goal_with_progress(
        db,
        current_user.id,
        goal,
        funded_amount,
        released_amount=get_goal_released_amount(db, current_user.id, goal.id),
        linked_project_id=get_goal_linked_project_id(db, current_user.id, goal.id),
        today=today,
    )


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
    for key, value in rate_headers.items():
        response.headers[key] = value

    goal = _get_owned_goal_or_404(db, current_user.id, goal_id)
    if goal.status != models.GoalStatus.ARCHIVED:
        _ensure_archived_goal_capacity(db, current_user.id)
    funded_amount = get_goal_funded_amount(db, current_user.id, goal.id)
    released_amount = get_goal_released_amount(db, current_user.id, goal.id)
    return _archive_goal_and_release_funds(
        db,
        current_user.id,
        goal,
        funded_amount,
        released_amount,
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
    for key, value in rate_headers.items():
        response.headers[key] = value

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
    return build_goal_with_progress(
        db,
        current_user.id,
        goal,
        funded_amount,
        released_amount=get_goal_released_amount(db, current_user.id, goal.id),
        linked_project_id=get_goal_linked_project_id(db, current_user.id, goal.id),
        today=today_in_tz(user_tz),
    )


@router.delete("/{goal_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_goal(
    goal_id: int,
    response: Response,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
):
    ensure_premium_user(current_user)
    rate_headers = enforce_goal_lifecycle_write_rate_limit(current_user.id)
    for key, value in rate_headers.items():
        response.headers[key] = value

    goal = _get_owned_goal_or_404(db, current_user.id, goal_id)
    funded_amount = get_goal_funded_amount(db, current_user.id, goal.id)
    released_amount = get_goal_released_amount(db, current_user.id, goal.id)
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
    if released_amount > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="goals.delete_requires_zero_released",
        )
    db.delete(goal)
    db.commit()


@router.post("/{goal_id}/allocations", response_model=schemas.GoalWithProgressOut)
def allocate_to_goal(
    goal_id: int,
    payload: schemas.GoalAllocationCreate,
    response: Response,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
    user_tz: tzinfo = Depends(get_effective_user_timezone),
):
    ensure_premium_user(current_user)
    rate_headers = enforce_goal_money_write_rate_limit(current_user.id)
    for key, value in rate_headers.items():
        response.headers[key] = value

    goal = _get_owned_goal_or_404(db, current_user.id, goal_id)
    _raise_if_goal_saving_phase_read_only(goal)

    funded_before = get_goal_funded_amount(db, current_user.id, goal.id)
    allocation_total = sum(int(item.amount) for item in payload.allocations)
    if int(funded_before) + int(allocation_total) > int(goal.target_amount):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="goals.allocation_exceeds_target",
        )

    validated_allocations: list[schemas.GoalAllocationItemCreate] = []
    for allocation in payload.allocations:
        validate_wallet_for_goal_allocation(db, current_user.id, goal, allocation.wallet_id)
        available = get_wallet_available_for_goal(db, current_user.id, allocation.wallet_id)
        if allocation.amount > available:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="goals.insufficient_wallet_available_for_goal",
            )
        validated_allocations.append(allocation)

    for allocation in validated_allocations:
        record_goal_contribution(
            db=db,
            user_id=current_user.id,
            goal_id=goal.id,
            wallet_id=allocation.wallet_id,
            amount=allocation.amount,
            contribution_type=models.GoalContributionType.ALLOCATE,
        )

    funded_amount = get_goal_funded_amount(db, current_user.id, goal.id)
    sync_goal_status(goal, funded_amount)

    from app.routers.notifications import create_goal_milestone_notification

    notification = create_goal_milestone_notification(
        db=db,
        owner_id=current_user.id,
        goal_title=goal.title,
        funded_amount=funded_amount,
        target_amount=goal.target_amount,
        is_completed=goal.status == models.GoalStatus.COMPLETED,
    )
    if notification:
        db.add(notification)

    db.commit()
    db.refresh(goal)
    return build_goal_with_progress(
        db,
        current_user.id,
        goal,
        funded_amount,
        released_amount=get_goal_released_amount(db, current_user.id, goal.id),
        linked_project_id=get_goal_linked_project_id(db, current_user.id, goal.id),
        today=today_in_tz(user_tz),
    )


@router.post("/{goal_id}/contribute", response_model=schemas.GoalWithProgressOut)
def contribute_to_goal(
    goal_id: int,
    payload: schemas.GoalAllocationCreate,
    response: Response,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
    user_tz: tzinfo = Depends(get_effective_user_timezone),
):
    return allocate_to_goal(goal_id, payload, response, db, current_user, user_tz)


@router.post("/{goal_id}/allocations/move", response_model=schemas.GoalFundingMoveOut)
def move_goal_funding_to_wallet(
    goal_id: int,
    payload: schemas.GoalFundingMoveCreate,
    response: Response,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
    user_tz: tzinfo = Depends(get_effective_user_timezone),
):
    ensure_premium_user(current_user)
    rate_headers = enforce_goal_money_write_rate_limit(current_user.id)
    for key, value in rate_headers.items():
        response.headers[key] = value

    goal = _get_owned_goal_or_404(db, current_user.id, goal_id)
    _raise_if_goal_saving_phase_read_only(goal)
    if goal.status == models.GoalStatus.COMPLETED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="goals.completed_read_only")
    if goal.intent not in (
        models.GoalIntent.PLANNED_PURCHASE,
        models.GoalIntent.PAY_OBLIGATION,
        models.GoalIntent.RESERVE,
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="goals.prepare_payment_intent_not_supported",
        )

    try:
        move_records = []
        source_totals: dict[int, int] = {}
        target_wallet_ids: set[int] = set()
        primary_outflow_by_wallet: dict[int, int] = {}
        allowed_goal_resolution_by_wallet: dict[int, int] = {}
        fee_amount_by_wallet: dict[int, int] = {}
        fee_wallets_by_id: dict[int, models.Wallet] = {}

        for move in payload.moves or []:
            if move.source_wallet_id == move.target_wallet_id:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="wallets.transfer_to_same")

            source_wallet = validate_wallet_for_goal_release(db, current_user.id, goal, move.source_wallet_id)
            if not source_wallet.is_active:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="wallets.archived_locked")
            target_wallet = _validate_prepare_payment_target_wallet(
                db,
                current_user.id,
                goal,
                move.target_wallet_id,
            )

            amount = int(move.amount)
            source_totals[source_wallet.id] = source_totals.get(source_wallet.id, 0) + amount
            source_unreleased = get_goal_wallet_funded_amount(db, current_user.id, goal.id, source_wallet.id)
            if source_totals[source_wallet.id] > int(source_unreleased):
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="goals.release_exceeds_wallet_unreleased")

            primary_outflow_by_wallet[source_wallet.id] = primary_outflow_by_wallet.get(source_wallet.id, 0) + amount
            allowed_goal_resolution_by_wallet[source_wallet.id] = allowed_goal_resolution_by_wallet.get(source_wallet.id, 0) + amount
            target_wallet_ids.add(target_wallet.id)

            fee_amount = int(move.fee_amount or 0)
            fee_wallet = None
            if fee_amount > 0:
                fee_wallet = get_owned_fee_wallet_or_404(
                    db,
                    current_user.id,
                    int(move.fee_wallet_id or source_wallet.id),
                )
                if fee_wallet.currency != goal.currency:
                    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="goals.currency_mismatch")
                fee_amount_by_wallet[fee_wallet.id] = fee_amount_by_wallet.get(fee_wallet.id, 0) + fee_amount
                fee_wallets_by_id[fee_wallet.id] = fee_wallet

            move_records.append(
                {
                    "source_wallet": source_wallet,
                    "target_wallet": target_wallet,
                    "amount": amount,
                    "fee_amount": fee_amount,
                    "fee_wallet": fee_wallet,
                    "fee_note": move.fee_note,
                }
            )

        if len(target_wallet_ids) > schemas.MAX_GOAL_PAYMENT_PREPARATION_TARGET_WALLETS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="goals.prepare_payment_target_wallet_limit_exceeded",
            )

        for fee_wallet_id, fee_total in fee_amount_by_wallet.items():
            validate_linked_fee_goal_protection(
                db,
                current_user.id,
                fee_wallets_by_id[fee_wallet_id],
                fee_total,
                primary_outflow_amount=primary_outflow_by_wallet.get(fee_wallet_id, 0),
                allowed_goal_resolution_amount=allowed_goal_resolution_by_wallet.get(fee_wallet_id, 0),
            )

        transfer_outputs: list[schemas.WalletTransferOut] = []
        moved_amount = 0
        for record in move_records:
            source_wallet = record["source_wallet"]
            target_wallet = record["target_wallet"]
            amount = int(record["amount"])
            transfer = WalletService.transfer_funds(
                db=db,
                owner_id=current_user.id,
                from_wallet_id=source_wallet.id,
                to_wallet_id=target_wallet.id,
                amount=amount,
                description=payload.note or f"Prepare {goal.title} payment",
                transaction_date=payload.date,
            )
            record_goal_contribution(
                db=db,
                user_id=current_user.id,
                goal_id=goal.id,
                wallet_id=source_wallet.id,
                amount=amount,
                contribution_type=models.GoalContributionType.RETURN,
                linked_event_id=transfer.id,
            )
            record_goal_contribution(
                db=db,
                user_id=current_user.id,
                goal_id=goal.id,
                wallet_id=target_wallet.id,
                amount=amount,
                contribution_type=models.GoalContributionType.ALLOCATE,
                linked_event_id=transfer.id,
            )

            fee_event = None
            if int(record["fee_amount"]) > 0 and record["fee_wallet"] is not None:
                budget, _ = resolve_or_create_bank_fee_budget(db, current_user.id, payload.date)
                fee_event = record_linked_bank_fee_event(
                    db,
                    user_id=current_user.id,
                    wallet=record["fee_wallet"],
                    amount=int(record["fee_amount"]),
                    fee_date=payload.date,
                    budget_id=budget.id,
                    linked_event_id=transfer.id,
                    note=record["fee_note"] or payload.note or f"Prepare {goal.title} payment fee",
                )

            db.flush()
            db.refresh(transfer)
            if fee_event is not None:
                db.refresh(fee_event)
            transfer_outputs.append(
                schemas.WalletTransferOut(
                    id=transfer.id,
                    from_wallet_id=source_wallet.id,
                    to_wallet_id=target_wallet.id,
                    amount=amount,
                    note=payload.note,
                    date=transfer.date,
                    created_at=transfer.created_at,
                    fee_event_id=fee_event.id if fee_event else None,
                )
            )
            moved_amount += amount

        sync_goal_status(goal, get_goal_funded_amount(db, current_user.id, goal.id))
        db.commit()
        db.refresh(goal)
        return schemas.GoalFundingMoveOut(
            goal=build_goal_with_progress(
                db,
                current_user.id,
                goal,
                get_goal_funded_amount(db, current_user.id, goal.id),
                released_amount=get_goal_released_amount(db, current_user.id, goal.id),
                linked_project_id=get_goal_linked_project_id(db, current_user.id, goal.id),
                today=today_in_tz(user_tz),
            ),
            transfer=transfer_outputs[0] if transfer_outputs else None,
            transfers=transfer_outputs,
            moved_amount=int(moved_amount),
        )
    except HTTPException as exc:
        db.rollback()
        raise exc


@router.post("/{goal_id}/use-reserve", response_model=schemas.GoalUseResultOut)
def use_reserve_goal(
    goal_id: int,
    payload: schemas.GoalUseReserveCreate,
    response: Response,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
    user_tz: tzinfo = Depends(get_effective_user_timezone),
):
    ensure_premium_user(current_user)
    rate_headers = enforce_goal_money_write_rate_limit(current_user.id)
    for key, value in rate_headers.items():
        response.headers[key] = value

    goal = _get_owned_goal_or_404(db, current_user.id, goal_id)
    if goal.intent != models.GoalIntent.RESERVE:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="goals.intent_mismatch")
    if goal.status == models.GoalStatus.ARCHIVED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="goals.archived_read_only")

    payment_allocations = _resolve_goal_payment_allocations(
        db,
        current_user.id,
        goal,
        payload.payment_allocations,
        payload.amount,
    )
    payment_plan = [(int(wallet.id), int(amount)) for wallet, amount in payment_allocations]

    local_today = today_in_tz(user_tz)
    effective_date = payload.date or local_today
    title = payload.title or goal.title
    event = _create_goal_expense_event(
        db,
        current_user.id,
        wallet_allocations=payment_allocations,
        amount=payload.amount,
        category=payload.category,
        expense_date=effective_date,
        local_today=local_today,
        title=title,
        description=payload.description,
        subcategory_id=payload.subcategory_id,
        project_id=payload.project_id,
        project_subcategory_id=payload.project_subcategory_id,
        enforce_monthly_budget_limits=payload.enforce_monthly_budget_limits,
    )

    transfer_event_ids: list[int] = []
    consumed_amount = 0
    if payload.settlement_mode == schemas.GoalSettlementMode.DIRECT:
        plan = _build_direct_payment_funding_plan(
            db=db,
            user_id=current_user.id,
            goal=goal,
            payment_plan=payment_plan,
            require_full_coverage=True,
        )
        consumed_amount = _consume_goal_funding_plan(
            db,
            current_user.id,
            goal,
            plan,
            linked_event_id=event.id,
        )
    elif payload.settlement_mode == schemas.GoalSettlementMode.GOAL_BACKED_OFF_WALLET_PAYMENT:
        plan = _build_goal_funding_plan(
            db,
            current_user.id,
            goal,
            payload.amount,
            preferred_wallet_ids=[wallet_id for wallet_id, _ in payment_plan],
            require_full_coverage=True,
        )
        consumed_amount = _consume_goal_funding_plan(
            db,
            current_user.id,
            goal,
            plan,
            linked_event_id=event.id,
        )
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="goals.settlement_mode_invalid")

    funded_amount = get_goal_funded_amount(db, current_user.id, goal.id)
    sync_goal_status(goal, funded_amount)
    db.commit()
    db.refresh(goal)
    return schemas.GoalUseResultOut(
        goal=build_goal_with_progress(
            db,
            current_user.id,
            goal,
            get_goal_funded_amount(db, current_user.id, goal.id),
            released_amount=get_goal_released_amount(db, current_user.id, goal.id),
            linked_project_id=get_goal_linked_project_id(db, current_user.id, goal.id),
            today=today_in_tz(user_tz),
        ),
        expense_event_id=event.id,
        transfer_event_ids=transfer_event_ids,
        consumed_amount=consumed_amount,
        released_amount=0,
        outside_goal_amount=max(int(payload.amount) - int(consumed_amount), 0),
    )


@router.post("/{goal_id}/record-purchase", response_model=schemas.GoalUseResultOut)
def record_planned_purchase_goal(
    goal_id: int,
    payload: schemas.GoalUsePlannedPurchaseCreate,
    response: Response,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
    user_tz: tzinfo = Depends(get_effective_user_timezone),
):
    ensure_premium_user(current_user)
    rate_headers = enforce_goal_money_write_rate_limit(current_user.id)
    for key, value in rate_headers.items():
        response.headers[key] = value

    goal = _get_owned_goal_or_404(db, current_user.id, goal_id)
    if goal.intent != models.GoalIntent.PLANNED_PURCHASE:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="goals.intent_mismatch")
    if goal.status == models.GoalStatus.ARCHIVED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="goals.archived_read_only")
    if goal.linked_expense_event_id is not None or (
        goal.status == models.GoalStatus.COMPLETED and goal.linked_expense_event_id is not None
    ):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="goals.purchase_already_recorded")
    _validate_planned_purchase_payment_row_limit(payload.payment_allocations)

    unreleased_sources = _get_goal_unreleased_sources(db, current_user.id, goal.id)
    goal_funding_wallet_ids = {
        int(source.wallet_id)
        for source in unreleased_sources
        if int(source.unreleased_amount or 0) > 0
    }
    unreleased_total = sum(
        int(source.unreleased_amount or 0)
        for source in unreleased_sources
    )
    if int(payload.amount) != int(goal.target_amount) and not payload.adjust_target_to_purchase_amount:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="goals.purchase_target_adjustment_required")
    if payload.adjust_target_to_purchase_amount and int(payload.amount) != int(goal.target_amount):
        goal.target_amount = int(payload.amount)
        db.flush()

    payment_allocations = _resolve_goal_payment_allocations(
        db,
        current_user.id,
        goal,
        payload.payment_allocations,
        payload.amount,
    )
    payment_plan = [(int(wallet.id), int(amount)) for wallet, amount in payment_allocations]

    local_today = today_in_tz(user_tz)
    effective_date = payload.date or local_today
    title = payload.title or goal.title

    if int(payload.amount) > unreleased_total:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="goals.insufficient_unreleased_balance")

    if payload.settlement_mode == schemas.GoalSettlementMode.DIRECT:
        payment_wallet_ids = {int(wallet.id) for wallet, _amount in payment_allocations}
        if not payment_wallet_ids.issubset(goal_funding_wallet_ids):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="goals.payment_wallet_not_funding_source")
        _validate_goal_funded_payment_wallets_are_owned_money(payment_allocations)
    elif payload.settlement_mode == schemas.GoalSettlementMode.GOAL_BACKED_OFF_WALLET_PAYMENT:
        payment_wallet_ids = {int(wallet.id) for wallet, _amount in payment_allocations}
        if payment_wallet_ids & goal_funding_wallet_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="goals.goal_backed_off_wallet_requires_non_funding_wallet",
            )
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="goals.settlement_mode_invalid")

    event = _create_goal_expense_event(
        db,
        current_user.id,
        wallet_allocations=payment_allocations,
        amount=payload.amount,
        category=payload.category,
        expense_date=effective_date,
        local_today=local_today,
        title=title,
        description=payload.description,
        subcategory_id=payload.subcategory_id,
        project_id=payload.project_id,
        project_subcategory_id=payload.project_subcategory_id,
        reference_type=models.ReferenceType.GOAL_PLANNED_PURCHASE,
        enforce_goal_protection=False,
        enforce_monthly_budget_limits=False,
    )

    transfer_event_ids: list[int] = []
    consumed_amount = 0
    released_amount = 0
    if payload.settlement_mode == schemas.GoalSettlementMode.DIRECT:
        plan = _build_direct_payment_funding_plan(
            db=db,
            user_id=current_user.id,
            goal=goal,
            payment_plan=payment_plan,
            require_full_coverage=True,
        )
        consumed_amount = _consume_goal_funding_plan(
            db,
            current_user.id,
            goal,
            plan,
            linked_event_id=event.id,
        )
    else:
        plan = _build_goal_funding_plan(
            db,
            current_user.id,
            goal,
            payload.amount,
            require_full_coverage=True,
        )
        consumed_amount = _consume_goal_funding_plan(
            db,
            current_user.id,
            goal,
            plan,
            linked_event_id=event.id,
        )

    remaining_plan = _build_goal_funding_plan(
        db,
        current_user.id,
        goal,
        amount=999_999_999_999,
        require_full_coverage=False,
    )
    released_amount += _return_goal_funding_plan(
        db,
        current_user.id,
        goal,
        remaining_plan,
        linked_event_id=event.id,
    )

    asset = None
    asset_purchase_value = int(payload.payment_plan.total_price) if payload.payment_plan else int(payload.amount)
    if payload.result_type == schemas.PlannedPurchaseResultType.ASSET_PURCHASE:
        asset = models.Asset(
            owner_id=current_user.id,
            title=(payload.asset_title or title).strip(),
            description=payload.asset_description if payload.asset_description is not None else payload.description,
            origin_event_id=event.id,
            purchase_value=asset_purchase_value,
            current_value=int(payload.asset_current_value) if payload.asset_current_value is not None else asset_purchase_value,
            status="owned",
        )
        db.add(asset)
        db.flush()

    goal.linked_expense_event_id = event.id
    if asset is not None:
        goal.linked_asset_id = asset.id
    goal.status = models.GoalStatus.COMPLETED
    db.flush()

    payment_plan, next_payment_goal = _create_payment_plan_bridge_from_goal_purchase(
        db,
        current_user.id,
        goal=goal,
        payload=payload,
        event=event,
        asset=asset,
        title=title,
        effective_date=effective_date,
        user_tz=user_tz,
    )

    db.commit()
    db.refresh(goal)
    if payment_plan is not None:
        db.refresh(payment_plan)
    if next_payment_goal is not None:
        db.refresh(next_payment_goal)
    return schemas.GoalUseResultOut(
        goal=build_goal_with_progress(
            db,
            current_user.id,
            goal,
            get_goal_funded_amount(db, current_user.id, goal.id),
            released_amount=get_goal_released_amount(db, current_user.id, goal.id),
            linked_project_id=get_goal_linked_project_id(db, current_user.id, goal.id),
            today=today_in_tz(user_tz),
        ),
        expense_event_id=event.id,
        asset_id=asset.id if asset is not None else None,
        transfer_event_ids=transfer_event_ids,
        consumed_amount=consumed_amount,
        released_amount=released_amount,
        outside_goal_amount=max(int(payload.amount) - int(consumed_amount), 0),
        payment_plan=(
            schemas.PaymentPlanWithPaymentsOut.model_validate(payment_plan)
            if payment_plan is not None
            else None
        ),
        next_payment_goal=(
            build_goal_with_progress(
                db,
                current_user.id,
                next_payment_goal,
                get_goal_funded_amount(db, current_user.id, next_payment_goal.id),
                released_amount=get_goal_released_amount(db, current_user.id, next_payment_goal.id),
                linked_project_id=get_goal_linked_project_id(db, current_user.id, next_payment_goal.id),
                today=today_in_tz(user_tz),
            )
            if next_payment_goal is not None
            else None
        ),
    )


@router.post("/{goal_id}/pay-debt", response_model=schemas.GoalDebtPaymentResultOut)
def pay_linked_debt_from_goal(
    goal_id: int,
    payload: schemas.GoalDebtPaymentCreate,
    response: Response,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
    user_tz: tzinfo = Depends(get_effective_user_timezone),
):
    ensure_premium_user(current_user)
    rate_headers = enforce_goal_money_write_rate_limit(current_user.id)
    for key, value in rate_headers.items():
        response.headers[key] = value

    goal = (
        db.query(models.Goals)
        .filter(models.Goals.id == goal_id, models.Goals.owner_id == current_user.id)
        .with_for_update()
        .first()
    )
    if goal is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="goals.not_found")
    if goal.intent != models.GoalIntent.PAY_OBLIGATION:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="goals.intent_mismatch")
    if goal.status == models.GoalStatus.ARCHIVED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="goals.archived_read_only")
    if goal.status == models.GoalStatus.COMPLETED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="goals.completed_read_only")
    if goal.linked_debt_id is None and goal.linked_payment_plan_id is not None:
        return _pay_linked_payment_plan_from_goal(
            db=db,
            user_id=current_user.id,
            goal=goal,
            payload=payload,
            user_tz=user_tz,
        )
    if goal.linked_debt_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="goals.debt_goal_requires_debt")

    debt = (
        db.query(models.Debt)
        .filter(models.Debt.id == goal.linked_debt_id, models.Debt.owner_id == current_user.id)
        .with_for_update()
        .first()
    )
    if debt is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="debts.not_found")
    if debt.debt_type != models.DebtType.OWING:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="goals.debt_goal_requires_i_owe_debt")
    if debt.archived_at is not None or int(debt.remaining_amount or 0) <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="goals.debt_goal_requires_open_debt")

    _raise_debt_policy_denied(evaluate_debt_action(db, debt, models.DebtActionKind.RECORD_PAYMENT))

    amount = int(payload.amount)
    if amount > int(debt.remaining_amount or 0):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="debts.transaction.amount_too_high")

    consumed_before = get_goal_consumed_amount(db, current_user.id, goal.id)
    remaining_goal_payment = max(int(goal.target_amount or 0) - int(consumed_before), 0)
    if amount > remaining_goal_payment:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="goals.debt_payment_exceeds_goal_remaining")

    payment_allocations = _resolve_goal_payment_allocations(
        db,
        current_user.id,
        goal,
        payload.payment_allocations,
        amount,
    )
    _validate_goal_funded_payment_wallets_are_owned_money(payment_allocations)
    payment_plan = [(int(wallet.id), int(payment_amount)) for wallet, payment_amount in payment_allocations]
    funding_plan = _build_direct_payment_funding_plan(
        db=db,
        user_id=current_user.id,
        goal=goal,
        payment_plan=payment_plan,
        require_full_coverage=True,
    )

    debt_transaction, ledger_entry = create_debt_payment(
        db,
        debt,
        amount=amount,
        transaction_date=payload.date or today_in_tz(user_tz),
        wallet_allocations=[
            schemas.DebtTransactionWalletAllocationIn(
                wallet_id=wallet.id,
                amount=int(payment_amount),
            )
            for wallet, payment_amount in payment_allocations
        ],
        note=payload.note or f"Goal payment for {debt.counterparty_name}",
        income_source_id=payload.income_source_id,
        enforce_goal_protection=False,
    )
    if ledger_entry.financial_event_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="goals.debt_payment_missing_event")

    consumed_amount = _consume_goal_funding_plan(
        db,
        current_user.id,
        goal,
        funding_plan,
        linked_event_id=ledger_entry.financial_event_id,
    )
    debt = reconcile_debt(db, debt.id)
    sync_debt_goal_targets(db, current_user.id, debt.id)

    consumed_after = get_goal_consumed_amount(db, current_user.id, goal.id)
    reserved_after = get_goal_funded_amount(db, current_user.id, goal.id)
    if int(consumed_after) >= int(goal.target_amount or 0) or int(debt.remaining_amount or 0) == 0:
        goal.status = models.GoalStatus.COMPLETED
        goal.linked_debt_transaction_id = debt_transaction.id
    else:
        sync_goal_status(goal, reserved_after)

    db.commit()
    db.refresh(goal)
    db.refresh(debt)
    db.refresh(debt_transaction)
    return schemas.GoalDebtPaymentResultOut(
        goal=build_goal_with_progress(
            db,
            current_user.id,
            goal,
            get_goal_funded_amount(db, current_user.id, goal.id),
            released_amount=get_goal_released_amount(db, current_user.id, goal.id),
            linked_project_id=get_goal_linked_project_id(db, current_user.id, goal.id),
            today=today_in_tz(user_tz),
        ),
        debt=_build_goal_debt_out(db, debt),
        debt_transaction=build_debt_transaction_out(debt_transaction),
        consumed_amount=consumed_amount,
    )


@router.post("/{goal_id}/graduate", response_model=schemas.ProjectBudgetOut, status_code=status.HTTP_201_CREATED)
def graduate_goal_to_project(
    goal_id: int,
    payload: schemas.GoalGraduateCreate,
    response: Response,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
    user_tz: tzinfo = Depends(get_effective_user_timezone),
):
    ensure_premium_user(current_user)
    rate_headers = enforce_goal_money_write_rate_limit(current_user.id)
    for key, value in rate_headers.items():
        response.headers[key] = value

    goal = _get_owned_goal_or_404(db, current_user.id, goal_id)
    if goal.status == models.GoalStatus.ARCHIVED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="goals.archived_read_only")
    if goal.status == models.GoalStatus.GRADUATED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="goals.graduated_read_only")
    if goal.intent != models.GoalIntent.FUND_PROJECT:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="goals.graduation_requires_fund_project")
    if _get_goal_project_or_none(db, current_user.id, goal.id) is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="goals.project_already_exists")
    if not payload.is_isolated:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="projects.isolated_required")
    if payload.total_limit is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="projects.isolated_wallet_funded_total_limit_not_allowed")

    release_sources = [
        source
        for source in get_goal_funding_sources(db, current_user.id, goal.id)
        if int(source.unreleased_amount) > 0
    ]
    project_type = models.ProjectType.ISOLATED
    project = models.Project(
        owner_id=current_user.id,
        title=(payload.project_title or goal.title).strip(),
        description=payload.description,
        project_type=project_type,
        origin_goal_id=goal.id,
        status=models.ProjectStatus.ACTIVE,
        start_date=payload.start_date,
        target_end_date=payload.target_end_date if payload.target_end_date is not None else goal.target_date,
    )
    db.add(project)
    db.flush()
    if project_type == models.ProjectType.ISOLATED:
        db.add(
            models.ProjectIsolatedDetail(
                project_id=project.id,
                owner_id=current_user.id,
                funding_limit=None,
            )
        )

    funded_amount = get_goal_funded_amount(db, current_user.id, goal.id)
    released_amount = get_goal_released_amount(db, current_user.id, goal.id)
    available_to_release = max(int(funded_amount) - int(released_amount), 0)
    if sum(int(source.unreleased_amount) for source in release_sources) != available_to_release:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="goals.release_source_mismatch")

    for source in release_sources:
        release_amount = int(source.unreleased_amount)
        validate_wallet_for_goal_release(db, current_user.id, goal, source.wallet_id)
        db.add(
            models.GoalProjectRelease(
                owner_id=current_user.id,
                goal_id=goal.id,
                project_id=project.id,
                wallet_id=source.wallet_id,
                amount=release_amount,
                released_at=payload.start_date,
                note="Initial release on project graduation",
            )
        )
        db.add(
            models.IsolatedProjectWalletAllocation(
                project_id=project.id,
                owner_id=current_user.id,
                wallet_id=source.wallet_id,
                amount=release_amount,
            )
        )
    goal.status = models.GoalStatus.GRADUATED

    db.commit()
    return _get_project_summary_or_404(
        db,
        current_user.id,
        project.id,
        today_in_tz(user_tz),
    )


@router.post("/{goal_id}/release-to-project", response_model=schemas.GoalWithProgressOut)
def release_goal_to_project(
    goal_id: int,
    payload: schemas.GoalProjectReleaseCreate,
    response: Response,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
    user_tz: tzinfo = Depends(get_effective_user_timezone),
):
    ensure_premium_user(current_user)
    rate_headers = enforce_goal_money_write_rate_limit(current_user.id)
    for key, value in rate_headers.items():
        response.headers[key] = value

    goal = _get_owned_goal_or_404(db, current_user.id, goal_id)
    _raise_if_goal_saving_phase_read_only(goal)
    project = _get_goal_project_or_404(db, current_user.id, goal.id)
    if project.status != models.ProjectStatus.ACTIVE:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="projects.not_active")
    validate_wallet_for_goal_release(db, current_user.id, goal, payload.wallet_id)

    funded_amount = get_goal_funded_amount(db, current_user.id, goal.id)
    released_amount = get_goal_released_amount(db, current_user.id, goal.id)
    available_to_release = max(int(funded_amount) - int(released_amount), 0)
    if payload.amount > available_to_release:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="goals.release_exceeds_unreleased")
    wallet_funded_amount = get_goal_wallet_funded_amount(db, current_user.id, goal.id, payload.wallet_id)
    wallet_released_amount = get_goal_wallet_released_amount(db, current_user.id, goal.id, payload.wallet_id)
    if payload.amount > max(wallet_funded_amount - wallet_released_amount, 0):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="goals.release_exceeds_wallet_unreleased")

    funding_limit = get_project_funding_limit(project)
    if funding_limit is not None and released_amount + payload.amount > funding_limit:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="projects.release_exceeds_total_limit")

    effective_date = payload.released_at or today_in_tz(user_tz)
    if effective_date < project.start_date:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="projects.release_before_start")
    if project.completed_at is not None and effective_date > project.completed_at:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="projects.release_after_completion")

    db.add(
        models.GoalProjectRelease(
            owner_id=current_user.id,
            goal_id=goal.id,
            project_id=project.id,
            wallet_id=payload.wallet_id,
            amount=payload.amount,
            released_at=effective_date,
            note=payload.note,
        )
    )
    db.commit()
    db.refresh(goal)
    return build_goal_with_progress(
        db,
        current_user.id,
        goal,
        funded_amount,
        released_amount=released_amount + int(payload.amount),
        linked_project_id=project.id,
        today=today_in_tz(user_tz),
    )


@router.post("/{goal_id}/allocations/return", response_model=schemas.GoalWithProgressOut)
def return_goal_allocation(
    goal_id: int,
    payload: schemas.GoalAllocationReturnCreate,
    response: Response,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
    user_tz: tzinfo = Depends(get_effective_user_timezone),
):
    ensure_premium_user(current_user)
    rate_headers = enforce_goal_money_write_rate_limit(current_user.id)
    for key, value in rate_headers.items():
        response.headers[key] = value

    goal = _get_owned_goal_or_404(db, current_user.id, goal_id)
    _raise_if_goal_saving_phase_read_only(goal)

    funded_amount = get_goal_funded_amount(db, current_user.id, goal.id)
    released_amount = get_goal_released_amount(db, current_user.id, goal.id)
    unreleased_amount = max(int(funded_amount) - int(released_amount), 0)
    if payload.amount > unreleased_amount:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="goals.insufficient_unreleased_balance",
        )
    validate_wallet_for_goal_release(db, current_user.id, goal, payload.wallet_id)
    wallet_funded_amount = get_goal_wallet_funded_amount(db, current_user.id, goal.id, payload.wallet_id)
    wallet_released_amount = get_goal_wallet_released_amount(db, current_user.id, goal.id, payload.wallet_id)
    wallet_unreleased_amount = max(wallet_funded_amount - wallet_released_amount, 0)
    if payload.amount > wallet_unreleased_amount:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="goals.insufficient_wallet_goal_balance",
        )

    record_goal_contribution(
        db=db,
        user_id=current_user.id,
        goal_id=goal.id,
        wallet_id=payload.wallet_id,
        amount=payload.amount,
        contribution_type=models.GoalContributionType.RETURN,
    )

    funded_amount = get_goal_funded_amount(db, current_user.id, goal.id)
    sync_goal_status(goal, funded_amount)
    db.commit()
    db.refresh(goal)
    return build_goal_with_progress(
        db,
        current_user.id,
        goal,
        funded_amount,
        released_amount=released_amount,
        linked_project_id=get_goal_linked_project_id(db, current_user.id, goal.id),
        today=today_in_tz(user_tz),
    )


@router.post("/{goal_id}/return", response_model=schemas.GoalWithProgressOut)
def return_from_goal(
    goal_id: int,
    payload: schemas.GoalAllocationReturnCreate,
    response: Response,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
    user_tz: tzinfo = Depends(get_effective_user_timezone),
):
    return return_goal_allocation(goal_id, payload, response, db, current_user, user_tz)


@router.post("/{goal_id}/allocations/consume", response_model=schemas.GoalWithProgressOut)
def consume_goal_allocation(
    goal_id: int,
    payload: schemas.GoalAllocationConsumeCreate,
    response: Response,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
    user_tz: tzinfo = Depends(get_effective_user_timezone),
):
    ensure_premium_user(current_user)
    rate_headers = enforce_goal_money_write_rate_limit(current_user.id)
    for key, value in rate_headers.items():
        response.headers[key] = value

    goal = _get_owned_goal_or_404(db, current_user.id, goal_id)
    _raise_if_goal_saving_phase_read_only(goal)
    if goal.intent == models.GoalIntent.PLANNED_PURCHASE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="goals.planned_purchase_requires_record_purchase",
        )
    if goal.intent == models.GoalIntent.RESERVE and payload.linked_event_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="goals.reserve_consume_requires_real_event",
        )
    validate_wallet_for_goal_release(db, current_user.id, goal, payload.wallet_id)

    wallet_funded_amount = get_goal_wallet_funded_amount(db, current_user.id, goal.id, payload.wallet_id)
    if payload.amount > wallet_funded_amount:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="goals.insufficient_wallet_goal_balance",
        )

    if payload.linked_event_id is not None:
        linked_event = (
            db.query(models.FinancialEvent)
            .filter(
                models.FinancialEvent.id == payload.linked_event_id,
                models.FinancialEvent.owner_id == current_user.id,
            )
            .first()
        )
        if linked_event is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="transactions.not_found")
        if (
            goal.intent == models.GoalIntent.RESERVE
            and linked_event.event_type
            not in (models.TransactionType.EXPENSE, models.TransactionType.DEBT_SETTLEMENT)
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="goals.reserve_consume_requires_real_event",
            )

    record_goal_contribution(
        db=db,
        user_id=current_user.id,
        goal_id=goal.id,
        wallet_id=payload.wallet_id,
        amount=payload.amount,
        contribution_type=models.GoalContributionType.CONSUME,
        linked_event_id=payload.linked_event_id,
    )

    funded_amount = get_goal_funded_amount(db, current_user.id, goal.id)
    sync_goal_status(goal, funded_amount)
    db.commit()
    db.refresh(goal)
    return build_goal_with_progress(
        db,
        current_user.id,
        goal,
        funded_amount,
        released_amount=get_goal_released_amount(db, current_user.id, goal.id),
        linked_project_id=get_goal_linked_project_id(db, current_user.id, goal.id),
        today=today_in_tz(user_tz),
    )
