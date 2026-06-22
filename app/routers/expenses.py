import csv
from datetime import date, datetime, timedelta, timezone, tzinfo
from io import StringIO
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Response, status
# pyrefly: ignore [missing-import]
from fastapi.responses import StreamingResponse
# pyrefly: ignore [missing-import]
from sqlalchemy import func
# pyrefly: ignore [missing-import]
from sqlalchemy.orm import Session, selectinload

from app.redis_rate_limiter import check_and_consume, consume_token_bucket
from app.services.recurring_schedule_service import calculate_next_due_date
from app.timezone import get_effective_user_timezone, now_in_tz, resolve_effective_timezone, today_in_tz
from app.utils import check_budget_alerts
from .. import models, oauth2, schemas
from ..services.budget_service import (
    build_budget_out,
    compute_budget_chain,
    get_owned_project_or_404,
    materialize_budget_for_month,
    validate_project_budget,
)
from ..services.debt_service import create_debt_ledger_entry, reconcile_debt
from ..services.expense_posting_service import post_expense_event, validate_real_expense_category
from ..services.session_draft_service import (
    build_session_draft_out,
    ensure_draft_editable,
    finalize_session_draft,
    get_owned_session_draft_item_or_404,
    get_owned_session_draft_or_404,
    get_owned_session_split_or_404,
    get_owned_session_wallet_allocation_or_404,
    validate_session_item_links,
)
from ..services.wallet_service import WalletService
from ..session import get_db
from .wallets import _get_owned_wallet_or_404

router = APIRouter(
    prefix="/expenses",
    tags=["Expenses"],
)

CSV_FORMULA_PREFIXES = ("=", "+", "-", "@")
EXPENSE_WRITE_BUCKET_CAPACITY = 10
EXPENSE_WRITE_REFILL_RATE = 10 / 60
EXPENSE_MONTH_LIMIT = 1000
EXPENSE_FEED_VIEWS = {"all", "quick", "sessions", "groups", "refunds", "linked"}


def sanitize_csv_cell(value: str) -> str:
    if value is None:
        return ""
    text = str(value)
    if text.startswith(CSV_FORMULA_PREFIXES):
        return f"'{text}"
    return text


def enforce_expense_write_rate_limit(user_id: int) -> dict[str, str]:
    rl = consume_token_bucket(
        scope="expenses_write",
        identifier=str(user_id),
        capacity=EXPENSE_WRITE_BUCKET_CAPACITY,
        refill_rate_per_second=EXPENSE_WRITE_REFILL_RATE,
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
            detail="expenses.write_rate_limited",
            headers=headers,
        )
    return headers


def enforce_export_rate_limit(user_id: int) -> dict[str, str]:
    rl = check_and_consume(scope="export_csv", identifier=str(user_id))
    headers = {
        "X-RateLimit-Limit": str(rl.limit),
        "X-RateLimit-Remaining": str(rl.remaining),
        "X-RateLimit-Reset": str(rl.reset_seconds),
    }
    if not rl.allowed:
        headers["Retry-After"] = str(rl.reset_seconds)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="export.too_many_requests",
            headers=headers,
        )
    return headers


def resolve_budget_for_expense_month(
    db: Session,
    user_id: int,
    category: models.ExpenseCategory,
    expense_date: date,
) -> models.Budget:
    budget = (
        db.query(models.Budget)
        .filter(
            models.Budget.owner_id == user_id,
            models.Budget.category == category,
            models.Budget.budget_year == expense_date.year,
            models.Budget.budget_month == expense_date.month,
        )
        .with_for_update()
        .first()
    )

    if not budget:
        budget = materialize_budget_for_month(db, user_id, category, expense_date.year, expense_date.month)
        if not budget:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="expenses.budget_required",
            )

    return budget


def _expense_event_query(db: Session, owner_id: int):
    return (
        db.query(models.FinancialEvent)
        .options(
            selectinload(models.FinancialEvent.owner),
            selectinload(models.FinancialEvent.merge_group),
            selectinload(models.FinancialEvent.wallet_legs).selectinload(models.WalletLedger.wallet),
            selectinload(models.FinancialEvent.entity_legs).selectinload(models.EntityLedger.budget),
        )
        .filter(
            models.FinancialEvent.owner_id == owner_id,
            models.FinancialEvent.event_type.in_([
                models.TransactionType.EXPENSE,
                models.TransactionType.REFUND,
            ]),
            models.FinancialEvent.status == models.FinancialEventStatus.POSTED,
        )
    )


def _event_amount(event: models.FinancialEvent) -> int:
    return abs(int(sum(int(leg.amount or 0) for leg in event.wallet_legs)))


def _primary_entity_leg(event: models.FinancialEvent) -> models.EntityLedger | None:
    for leg in event.entity_legs:
        if leg.category is not None:
            return leg
    return event.entity_legs[0] if event.entity_legs else None


def _single_wallet_for_event(event: models.FinancialEvent) -> models.Wallet | None:
    if len(event.wallet_legs) != 1:
        return None
    return event.wallet_legs[0].wallet


def _wallet_allocations_out(event: models.FinancialEvent) -> list[schemas.ExpenseWalletAllocationOut]:
    allocations: list[schemas.ExpenseWalletAllocationOut] = []
    for leg in event.wallet_legs:
        allocations.append(
            schemas.ExpenseWalletAllocationOut(
                wallet_id=leg.wallet_id,
                amount=abs(int(leg.amount)),
                wallet=schemas.WalletOut.model_validate(leg.wallet) if leg.wallet else None,
            )
        )
    return allocations


def _single_wallet_leg_or_400(event: models.FinancialEvent) -> models.WalletLedger:
    if len(event.wallet_legs) != 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="expenses.complex_event_not_supported",
        )
    return event.wallet_legs[0]


def _single_entity_leg_or_400(event: models.FinancialEvent) -> models.EntityLedger:
    leg = _primary_entity_leg(event)
    if leg is None or len(event.entity_legs) != 1 or leg.category is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="expenses.complex_event_not_supported",
        )
    return leg


def _refund_totals_by_parent(db: Session, owner_id: int) -> dict[int, int]:
    rows = (
        db.query(
            models.FinancialEvent.linked_event_id,
            func.coalesce(func.sum(models.EntityLedger.amount), 0).label("total_refunded"),
        )
        .join(models.EntityLedger, models.EntityLedger.event_id == models.FinancialEvent.id)
        .filter(
            models.FinancialEvent.owner_id == owner_id,
            models.FinancialEvent.status == models.FinancialEventStatus.POSTED,
            models.FinancialEvent.event_type == models.TransactionType.REFUND,
            models.FinancialEvent.linked_event_id.isnot(None),
        )
        .group_by(models.FinancialEvent.linked_event_id)
        .all()
    )
    return {
        int(row.linked_event_id): int(row.total_refunded or 0)
        for row in rows
        if row.linked_event_id is not None
    }


def _asset_ids_by_event(db: Session, owner_id: int) -> dict[int, int]:
    rows = (
        db.query(models.Asset.origin_event_id, models.Asset.id)
        .filter(
            models.Asset.owner_id == owner_id,
            models.Asset.origin_event_id.isnot(None),
        )
        .all()
    )
    return {int(origin_event_id): int(asset_id) for origin_event_id, asset_id in rows if origin_event_id is not None}


def _split_items_out(event: models.FinancialEvent) -> list[schemas.ExpenseSplitItemOut]:
    if len(event.entity_legs) <= 1:
        return []

    items: list[schemas.ExpenseSplitItemOut] = []
    for leg in event.entity_legs:
        if leg.category is None:
            continue
        items.append(
            schemas.ExpenseSplitItemOut(
                id=leg.id,
                label=leg.label,
                amount=int(leg.amount),
                category=leg.category,
                subcategory_id=leg.subcategory_id,
                project_id=leg.project_id,
                project_subcategory_id=leg.project_subcategory_id,
                budget_id=leg.budget_id,
            )
        )
    return items


def _build_expense_out(
    event: models.FinancialEvent,
    refund_totals: dict[int, int],
    asset_ids: dict[int, int] | None = None,
) -> schemas.ExpenseOut:
    entity_leg = _primary_entity_leg(event)
    if entity_leg is None or entity_leg.category is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="expenses.event_missing_category",
        )

    wallet = _single_wallet_for_event(event)
    amount = _event_amount(event)
    refunded_amount = int(refund_totals.get(event.id, 0)) if event.event_type == models.TransactionType.EXPENSE else 0

    return schemas.ExpenseOut(
        id=event.id,
        title=event.title,
        amount=amount,
        category=entity_leg.category,
        description=event.description,
        date=event.date,
        wallet_id=wallet.id if wallet else None,
        wallet=schemas.WalletOut.model_validate(wallet) if wallet else None,
        subcategory_id=entity_leg.subcategory_id,
        project_id=entity_leg.project_id,
        project_subcategory_id=entity_leg.project_subcategory_id,
        transaction_type=event.event_type,
        reference_type=event.reference_type,
        created_at=event.created_at,
        owner_id=event.owner_id,
        owner=schemas.UserOut.model_validate(event.owner),
        has_refund=refunded_amount > 0,
        refunded_amount=refunded_amount,
        is_partially_refunded=0 < refunded_amount < amount,
        is_fully_refunded=refunded_amount >= amount if amount > 0 else False,
        is_session=bool(event.is_session),
        discount_amount=int(event.discount_amount) if event.discount_amount is not None else None,
        merge_group_id=event.merge_group_id,
        merge_group_title=event.merge_group.title if event.merge_group else None,
        is_split=len(event.entity_legs) > 1,
        wallet_allocations=_wallet_allocations_out(event),
        split_items=_split_items_out(event),
        asset_id=int(asset_ids.get(event.id)) if asset_ids and event.id in asset_ids else None,
    )


def _build_expense_detail_out(
    db: Session,
    owner_id: int,
    event: models.FinancialEvent,
    refund_totals: dict[int, int],
    asset_ids: dict[int, int] | None = None,
) -> schemas.ExpenseDetailOut:
    base = _build_expense_out(event, refund_totals, asset_ids)
    entity_leg = _primary_entity_leg(event)

    budget = entity_leg.budget if entity_leg is not None else None
    budget_out = None
    if budget is not None:
        budget_out = build_budget_out(compute_budget_chain(db, owner_id, [budget])[0])

    linked_asset = None
    if asset_ids and event.id in asset_ids:
        linked_asset_model = (
            db.query(models.Asset)
            .filter(models.Asset.owner_id == owner_id, models.Asset.id == int(asset_ids[event.id]))
            .first()
        )
        if linked_asset_model is not None:
            linked_asset = schemas.AssetOut.model_validate(linked_asset_model)

    refunds: list[schemas.ExpenseOut] = []
    refund_parent = None
    if event.event_type == models.TransactionType.EXPENSE:
        refund_events = (
            _expense_event_query(db, owner_id)
            .filter(
                models.FinancialEvent.event_type == models.TransactionType.REFUND,
                models.FinancialEvent.linked_event_id == event.id,
            )
            .order_by(models.FinancialEvent.date.desc(), models.FinancialEvent.created_at.desc(), models.FinancialEvent.id.desc())
            .all()
        )
        refunds = [_build_expense_out(item, refund_totals) for item in refund_events]
    elif event.linked_event_id is not None:
        parent_event = _get_owned_event_or_404(
            db,
            owner_id,
            event.linked_event_id,
            event_types=[models.TransactionType.EXPENSE],
        )
        refund_parent = _build_expense_out(parent_event, refund_totals, asset_ids)

    merge_group = None
    if event.merge_group_id is not None and event.merge_group is not None:
        merge_group = _build_merge_group_out(event.merge_group, refund_totals, asset_ids, include_items=False)

    related_debt_map: dict[int, models.Debt] = {}
    linked_event_debts = (
        db.query(models.Debt)
        .filter(
            models.Debt.owner_id == owner_id,
            models.Debt.linked_event_id == event.id,
        )
        .order_by(models.Debt.created_at.desc(), models.Debt.id.desc())
        .all()
    )
    for debt in linked_event_debts:
        related_debt_map[int(debt.id)] = debt

    entity_debt_ids = {
        int(leg.debt_id)
        for leg in event.entity_legs
        if leg.debt_id is not None
    }
    if entity_debt_ids:
        entity_linked_debts = (
            db.query(models.Debt)
            .filter(
                models.Debt.owner_id == owner_id,
                models.Debt.id.in_(entity_debt_ids),
            )
            .all()
        )
        for debt in entity_linked_debts:
            related_debt_map[int(debt.id)] = debt

    related_debts = sorted(
        related_debt_map.values(),
        key=lambda item: (item.created_at, item.id),
        reverse=True,
    )

    return schemas.ExpenseDetailOut(
        **base.model_dump(),
        subcategory_name=entity_leg.subcategory.name if entity_leg and entity_leg.subcategory else None,
        project_subcategory_name=entity_leg.project_subcategory.name if entity_leg and entity_leg.project_subcategory else None,
        project_title=entity_leg.project.title if entity_leg and entity_leg.project else None,
        budget_year=budget.budget_year if budget is not None else None,
        budget_month=budget.budget_month if budget is not None else None,
        budget_effective_limit=budget_out.effective_monthly_limit if budget_out is not None else None,
        budget_remaining=budget_out.remaining if budget_out is not None else None,
        item_count=len(_split_items_out(event)),
        wallet_count=len(event.wallet_legs),
        linked_asset=linked_asset,
        merge_group=merge_group,
        refund_parent=refund_parent,
        refunds=refunds,
        related_debts=[
            schemas.ExpenseRelatedDebtOut(
                id=item.id,
                debt_type=item.debt_type,
                counterparty_name=item.counterparty_name,
                remaining_amount=int(item.remaining_amount),
                status=item.status,
            )
            for item in related_debts
        ],
    )


def _get_owned_event_or_404(
    db: Session,
    user_id: int,
    event_id: int,
    *,
    event_types: list[models.TransactionType] | None = None,
) -> models.FinancialEvent:
    query = _expense_event_query(db, user_id).filter(models.FinancialEvent.id == event_id)
    if event_types:
        query = query.filter(models.FinancialEvent.event_type.in_(event_types))
    event = query.first()
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="expenses.not_found",
        )
    return event


def _get_owned_event_any_status_or_404(
    db: Session,
    user_id: int,
    event_id: int,
    *,
    event_types: list[models.TransactionType] | None = None,
) -> models.FinancialEvent:
    query = (
        db.query(models.FinancialEvent)
        .options(
            selectinload(models.FinancialEvent.owner),
            selectinload(models.FinancialEvent.merge_group),
            selectinload(models.FinancialEvent.wallet_legs).selectinload(models.WalletLedger.wallet),
            selectinload(models.FinancialEvent.entity_legs).selectinload(models.EntityLedger.budget),
        )
        .filter(
            models.FinancialEvent.owner_id == user_id,
            models.FinancialEvent.id == event_id,
        )
    )
    if event_types:
        query = query.filter(models.FinancialEvent.event_type.in_(event_types))
    event = query.first()
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="expenses.not_found",
        )
    return event


def _get_owned_merge_group_or_404(
    db: Session,
    user_id: int,
    group_id: int,
) -> models.ExpenseMergeGroup:
    group = (
        db.query(models.ExpenseMergeGroup)
        .options(
            selectinload(models.ExpenseMergeGroup.events).selectinload(models.FinancialEvent.owner),
            selectinload(models.ExpenseMergeGroup.events).selectinload(models.FinancialEvent.merge_group),
            selectinload(models.ExpenseMergeGroup.events).selectinload(models.FinancialEvent.wallet_legs).selectinload(models.WalletLedger.wallet),
            selectinload(models.ExpenseMergeGroup.events).selectinload(models.FinancialEvent.entity_legs).selectinload(models.EntityLedger.budget),
        )
        .filter(
            models.ExpenseMergeGroup.id == group_id,
            models.ExpenseMergeGroup.owner_id == user_id,
        )
        .first()
    )
    if not group:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="expenses.merge_group_not_found")
    return group


def _validate_merge_group_events(
    db: Session,
    user_id: int,
    expense_ids: list[int],
    *,
    allow_group_id: int | None = None,
) -> list[models.FinancialEvent]:
    deduped_ids = list(dict.fromkeys(expense_ids))
    if len(deduped_ids) < 2 and allow_group_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="expenses.merge_group_min_items")
    if not deduped_ids:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="expenses.merge_group_min_items")

    events = (
        _expense_event_query(db, user_id)
        .filter(
            models.FinancialEvent.id.in_(deduped_ids),
            models.FinancialEvent.event_type == models.TransactionType.EXPENSE,
        )
        .all()
    )
    if len(events) != len(deduped_ids):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="expenses.not_found")

    ordered = {event.id: event for event in events}
    validated = [ordered[event_id] for event_id in deduped_ids]
    for event in validated:
        if event.merge_group_id is not None and event.merge_group_id != allow_group_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="expenses.already_merged")
    return validated


def _build_merge_group_out(
    group: models.ExpenseMergeGroup,
    refund_totals: dict[int, int],
    asset_ids: dict[int, int] | None = None,
    *,
    include_items: bool = False,
) -> schemas.ExpenseMergeGroupOut | schemas.ExpenseMergeGroupDetailOut:
    child_events = sorted(
        [
            event for event in list(group.events or [])
            if event.status == models.FinancialEventStatus.POSTED
            and event.event_type == models.TransactionType.EXPENSE
        ],
        key=lambda event: (event.date, event.created_at, event.id),
    )
    total_amount = int(sum(_event_amount(event) for event in child_events))
    refunded_amount = int(sum(refund_totals.get(event.id, 0) for event in child_events))
    dates = [event.date for event in child_events if event.date is not None]
    base = dict(
        id=group.id,
        owner_id=group.owner_id,
        title=group.title,
        description=group.description,
        total_amount=total_amount,
        refunded_amount=refunded_amount,
        net_amount=max(total_amount - refunded_amount, 0),
        child_count=len(child_events),
        earliest_date=min(dates) if dates else None,
        latest_date=max(dates) if dates else None,
        created_at=group.created_at,
        updated_at=group.updated_at,
    )
    if include_items:
        return schemas.ExpenseMergeGroupDetailOut(
            **base,
            items=[_build_expense_out(event, refund_totals, asset_ids) for event in child_events],
        )
    return schemas.ExpenseMergeGroupOut(**base)


def _expense_matches_read_filters(
    item: schemas.ExpenseOut,
    *,
    search_lower: str | None,
    category: str | None,
    start_date: date | None,
    end_date: date | None,
) -> bool:
    if start_date and item.date < start_date:
        return False
    if end_date and item.date > end_date:
        return False
    if category and item.category.value != category:
        return False
    if search_lower:
        haystack = f"{item.title} {item.description or ''}".lower()
        if search_lower not in haystack:
            return False
    return True


def _is_linked_expense(event: models.FinancialEvent, asset_ids: dict[int, int]) -> bool:
    if event.id in asset_ids:
        return True
    for leg in event.entity_legs:
        if (
            leg.project_id is not None
            or leg.debt_id is not None
            or leg.installment_plan_id is not None
            or leg.installment_payment_id is not None
        ):
            return True
    return False


def _has_multiple_entity_allocations(event: models.FinancialEvent) -> bool:
    return len([leg for leg in event.entity_legs if leg.category is not None]) > 1


def _raise_if_split_parent(event: models.FinancialEvent) -> None:
    if _has_multiple_entity_allocations(event):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="expenses.split_parent_locked")


def _event_has_refund(db: Session, owner_id: int, event_id: int) -> bool:
    return (
        db.query(models.FinancialEvent.id)
        .filter(
            models.FinancialEvent.owner_id == owner_id,
            models.FinancialEvent.status == models.FinancialEventStatus.POSTED,
            models.FinancialEvent.event_type == models.TransactionType.REFUND,
            models.FinancialEvent.linked_event_id == event_id,
        )
        .first()
        is not None
    )


def _event_has_asset(db: Session, owner_id: int, event_id: int) -> bool:
    return (
        db.query(models.Asset.id)
        .filter(
            models.Asset.owner_id == owner_id,
            models.Asset.origin_event_id == event_id,
        )
        .first()
        is not None
    )


def _event_has_debt_or_installment_dependency(
    db: Session,
    owner_id: int,
    event: models.FinancialEvent,
) -> bool:
    has_debt = (
        db.query(models.Debt.id)
        .filter(
            models.Debt.owner_id == owner_id,
            models.Debt.linked_event_id == event.id,
        )
        .first()
    )
    if has_debt:
        return True
    return any(
        leg.debt_id or leg.installment_plan_id or leg.installment_payment_id
        for leg in event.entity_legs
    )


def _raise_if_asset_origin_ineligible(
    db: Session,
    owner_id: int,
    event: models.FinancialEvent,
) -> None:
    if event.is_session:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="expenses.complex_event_not_supported")
    _raise_if_split_parent(event)
    if _event_has_refund(db, owner_id, event.id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="expenses.has_refund_lock")
    if _event_has_debt_or_installment_dependency(db, owner_id, event):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="expenses.linked_dependency_lock")


def _build_expense_feed(
    db: Session,
    owner_id: int,
    *,
    user_tz: tzinfo,
    view: str,
    search: str | None,
    sort: str,
    category: str | None,
    time_range: str | None,
    start_date: date | None,
    end_date: date | None,
) -> list[schemas.ExpenseFeedItemOut]:
    if view not in EXPENSE_FEED_VIEWS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="expenses.invalid_view")

    def feed_stable_id(item: schemas.ExpenseFeedItemOut) -> int:
        if item.expense is not None:
            return int(item.expense.id)
        if item.merge_group is not None:
            return int(item.merge_group.id)
        return 0

    def chronological_key(item: schemas.ExpenseFeedItemOut):
        return (
            item.sort_date or date.min,
            item.sort_created_at or datetime.min.replace(tzinfo=timezone.utc),
            feed_stable_id(item),
        )

    today = now_in_tz(user_tz)
    if time_range == "past_week":
        start_date = (today - timedelta(days=7)).date()
    elif time_range == "past_month":
        start_date = (today - timedelta(days=30)).date()
    elif time_range == "last_3_months":
        start_date = (today - timedelta(days=90)).date()

    refund_totals = _refund_totals_by_parent(db, owner_id)
    asset_ids = _asset_ids_by_event(db, owner_id)
    search_lower = search.lower().strip() if search else None
    feed_items: list[schemas.ExpenseFeedItemOut] = []

    if view in {"all", "groups"}:
        groups = (
            db.query(models.ExpenseMergeGroup)
            .options(
                selectinload(models.ExpenseMergeGroup.events).selectinload(models.FinancialEvent.owner),
                selectinload(models.ExpenseMergeGroup.events).selectinload(models.FinancialEvent.merge_group),
                selectinload(models.ExpenseMergeGroup.events).selectinload(models.FinancialEvent.wallet_legs).selectinload(models.WalletLedger.wallet),
                selectinload(models.ExpenseMergeGroup.events).selectinload(models.FinancialEvent.entity_legs).selectinload(models.EntityLedger.budget),
            )
            .filter(models.ExpenseMergeGroup.owner_id == owner_id)
            .all()
        )
        for group in groups:
            detail = _build_merge_group_out(group, refund_totals, asset_ids, include_items=True)
            matching_children = [
                child for child in detail.items
                if _expense_matches_read_filters(
                    child,
                    search_lower=search_lower,
                    category=category,
                    start_date=start_date,
                    end_date=end_date,
                )
            ]
            if not matching_children:
                continue
            feed_items.append(
                schemas.ExpenseFeedItemOut(
                    type=schemas.ExpenseFeedItemType.MERGE_GROUP,
                    amount=detail.total_amount,
                    sort_date=detail.latest_date,
                    sort_created_at=detail.updated_at,
                    matched_child_count=len(matching_children),
                    merge_group=detail,
                )
            )

    if view == "groups":
        if sort == "expensive":
            feed_items.sort(key=lambda item: item.amount, reverse=True)
        elif sort == "cheapest":
            feed_items.sort(key=lambda item: item.amount)
        elif sort == "oldest":
            feed_items.sort(key=chronological_key)
        else:
            feed_items.sort(key=chronological_key, reverse=True)
        return feed_items

    query = _expense_event_query(db, owner_id)
    if view == "quick":
        query = query.filter(
            models.FinancialEvent.event_type == models.TransactionType.EXPENSE,
            models.FinancialEvent.is_session.is_(False),
            models.FinancialEvent.merge_group_id.is_(None),
        )
    elif view == "sessions":
        query = query.filter(
            models.FinancialEvent.event_type == models.TransactionType.EXPENSE,
            models.FinancialEvent.is_session,
            models.FinancialEvent.merge_group_id.is_(None),
        )
    elif view == "refunds":
        query = query.filter(models.FinancialEvent.event_type == models.TransactionType.REFUND)
    else:
        query = query.filter(models.FinancialEvent.merge_group_id.is_(None))

    if start_date:
        query = query.filter(models.FinancialEvent.date >= start_date)
    if end_date:
        query = query.filter(models.FinancialEvent.date <= end_date)
    if search_lower:
        query = query.filter(
            (models.FinancialEvent.title.ilike(f"%{search_lower}%"))
            | (models.FinancialEvent.description.ilike(f"%{search_lower}%"))
        )

    for event in query.all():
        entity_leg = _primary_entity_leg(event)
        if entity_leg is None or entity_leg.category is None:
            continue

        expense_out = _build_expense_out(event, refund_totals, asset_ids)
        if view == "linked" and not _is_linked_expense(event, asset_ids):
            continue
        if not _expense_matches_read_filters(
            expense_out,
            search_lower=None,
            category=category,
            start_date=None,
            end_date=None,
        ):
            continue

        feed_items.append(
            schemas.ExpenseFeedItemOut(
                type=schemas.ExpenseFeedItemType.EXPENSE,
                amount=expense_out.amount,
                sort_date=expense_out.date,
                sort_created_at=expense_out.created_at,
                matched_child_count=1,
                expense=expense_out,
            )
        )

    if sort == "expensive":
        feed_items.sort(key=lambda item: item.amount, reverse=True)
    elif sort == "cheapest":
        feed_items.sort(key=lambda item: item.amount)
    elif sort == "oldest":
        feed_items.sort(key=chronological_key)
    else:
        feed_items.sort(key=chronological_key, reverse=True)
    return feed_items


@router.post("/", response_model=schemas.ExpenseOut, status_code=status.HTTP_201_CREATED)
def create_expense(
    expense: schemas.ExpenseCreate,
    response: Response,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
    user_tz: tzinfo = Depends(get_effective_user_timezone),
):
    local_today = today_in_tz(user_tz)
    rate_headers = enforce_expense_write_rate_limit(current_user.id)
    for k, v in rate_headers.items():
        response.headers[k] = v

    current_month_start = local_today.replace(day=1)
    month_expense_count = (
        db.query(func.count(models.FinancialEvent.id))
        .filter(
            models.FinancialEvent.owner_id == current_user.id,
            models.FinancialEvent.event_type == models.TransactionType.EXPENSE,
            models.FinancialEvent.status == models.FinancialEventStatus.POSTED,
            models.FinancialEvent.date >= current_month_start,
            models.FinancialEvent.date <= local_today,
        )
        .scalar()
        or 0
    )
    if int(month_expense_count) >= EXPENSE_MONTH_LIMIT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="expenses.month_limit_reached",
        )

    posted = post_expense_event(
        db,
        current_user.id,
        title=expense.title,
        amount=expense.amount,
        category=expense.category,
        expense_date=expense.date,
        description=expense.description,
        wallet_id=expense.wallet_id,
        wallet_allocations=expense.wallet_allocations,
        subcategory_id=expense.subcategory_id,
        project_id=expense.project_id,
        project_subcategory_id=expense.project_subcategory_id,
        local_today=local_today,
    )
    new_event = posted.event
    budget = posted.budget
    wallet_allocations = posted.wallet_allocations

    if expense.splits:
        split_total = sum(s.amount for s in expense.splits)
        if split_total > expense.amount:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="expenses.splits_exceed_total",
            )

        split_debts: list[models.Debt] = []
        for split in expense.splits:
            split_debt = models.Debt(
                owner_id=current_user.id,
                debt_type=models.DebtType.OWED,
                origin_kind=models.DebtOriginKind.SPLIT_REIMBURSEMENT,
                counterparty_kind=models.DebtCounterpartyKind.PERSON,
                product_kind=models.DebtProductKind.PERSONAL_REIMBURSEMENT,
                counterparty_name=split.contact_name,
                initial_amount=split.amount,
                remaining_amount=split.amount,
                currency=wallet_allocations[0][0].currency,
                description=expense.title,
                status=models.DebtStatus.ACTIVE,
                date=expense.date,
                linked_event_id=new_event.id,
                expense_category=expense.category,
                expense_subcategory_id=expense.subcategory_id,
                project_id=expense.project_id,
                project_subcategory_id=expense.project_subcategory_id,
            )
            db.add(split_debt)
            split_debts.append(split_debt)
        db.flush()
        for split_debt in split_debts:
            create_debt_ledger_entry(
                db,
                owner_id=current_user.id,
                debt_id=split_debt.id,
                entry_type=models.DebtLedgerEntryType.INITIAL,
                amount_delta=int(split_debt.initial_amount),
                principal_delta=int(split_debt.initial_amount),
                financial_event_id=new_event.id,
                entry_date=split_debt.date,
                note=f"Initial split debt for {split_debt.counterparty_name}",
            )

    if budget is not None:
        check_budget_alerts(db, budget)
    db.commit()

    created = _get_owned_event_or_404(
        db,
        current_user.id,
        new_event.id,
        event_types=[models.TransactionType.EXPENSE],
    )
    return _build_expense_out(created, {}, _asset_ids_by_event(db, current_user.id))


@router.get("/", response_model=schemas.PaginatedExpenseFeedOut)
def get_expenses(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
    user_tz: tzinfo = Depends(get_effective_user_timezone),
    limit: int = 10,
    skip: int = 0,
    view: str = "all",
    search: Optional[str] = None,
    sort: str = "newest",
    category: Optional[str] = None,
    time_range: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
):
    items = _build_expense_feed(
        db,
        current_user.id,
        user_tz=user_tz,
        view=view,
        search=search,
        sort=sort,
        category=category,
        time_range=time_range,
        start_date=start_date,
        end_date=end_date,
    )

    total = len(items)
    paginated = items[skip:skip + limit]
    return schemas.PaginatedExpenseFeedOut(total=total, items=paginated)


@router.get("/export")
def export_csv_expense(
    response: Response,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
    category: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    sort: str = "newest",
    lang: Optional[str] = None,
):
    rate_headers = enforce_export_rate_limit(current_user.id)
    for k, v in rate_headers.items():
        response.headers[k] = v

    CSV_TRANSLATIONS = {
        "uz": {
            "categories": {
                "Groceries": "Oziq-ovqat mahsulotlari",
                "Dining Out": "Ko'chada ovqatlanish",
                "Electronics": "Elektronika",
                "Housing": "Turar joy",
                "Utilities": "Kommunal xizmatlar",
                "Subscriptions": "Obunalar",
                "Transport": "Transport",
                "Health": "Sog'liqni saqlash",
                "Personal care": "Shaxsiy parvarish",
                "Education": "Ta'lim",
                "Clothing": "Kiyim-kechak",
                "Family & Events": "Oila & marosimlar",
                "Entertainment": "Ko'ngilochar",
                "Installments & Debt": "Muddatli to'lov / qarzlar",
                "Business / Work": "Biznes / ish",
                "Debt Charges": "Qarz to'lovlari",
            },
            "headers": ["sana", "nomi", "summa", "toifa", "tavsif"],
        },
        "ru": {
            "categories": {
                "Groceries": "Продукты",
                "Dining Out": "Питание вне дома",
                "Electronics": "Электроника",
                "Housing": "Жилье",
                "Utilities": "Коммунальные услуги",
                "Subscriptions": "Подписки",
                "Transport": "Транспорт",
                "Health": "Здоровье",
                "Personal care": "Личный уход",
                "Education": "Образование",
                "Clothing": "Одежда",
                "Family & Events": "Семья и мероприятия",
                "Entertainment": "Развлечения",
                "Installments & Debt": "Рассрочка и долги",
                "Business / Work": "Бизнес / работа",
                "Debt Charges": "Платежи по долгам",
            },
            "headers": ["дата", "название", "сумма", "категория", "описание"],
        },
        "en": {
            "categories": {
                "Groceries": "Groceries",
                "Dining Out": "Dining Out",
                "Electronics": "Electronics",
                "Housing": "Housing",
                "Utilities": "Utilities",
                "Subscriptions": "Subscriptions",
                "Transport": "Transport",
                "Health": "Health",
                "Personal care": "Personal care",
                "Education": "Education",
                "Clothing": "Clothing",
                "Family & Events": "Family & Events",
                "Entertainment": "Entertainment",
                "Installments & Debt": "Installments & Debt",
                "Business / Work": "Business / Work",
                "Debt Charges": "Debt Charges",
            },
            "headers": ["date", "title", "amount", "category", "description"],
        },
    }

    dict_lang = (lang or "en").lower()
    if dict_lang.startswith("uz"):
        trans_dict = CSV_TRANSLATIONS["uz"]["categories"]
        headers_row = CSV_TRANSLATIONS["uz"]["headers"]
    elif dict_lang.startswith("ru"):
        trans_dict = CSV_TRANSLATIONS["ru"]["categories"]
        headers_row = CSV_TRANSLATIONS["ru"]["headers"]
    else:
        trans_dict = CSV_TRANSLATIONS["en"]["categories"]
        headers_row = CSV_TRANSLATIONS["en"]["headers"]

    feed_items = _build_expense_feed(
        db,
        current_user.id,
        user_tz=resolve_effective_timezone(user_timezone=getattr(current_user, "timezone", None)),
        view="all",
        search=None,
        sort=sort,
        category=category,
        time_range=None,
        start_date=start_date,
        end_date=end_date,
    )
    items: list[schemas.ExpenseOut] = []
    for item in feed_items:
        if item.expense is not None:
            items.append(item.expense)
        elif item.merge_group is not None:
            items.extend(
                child for child in item.merge_group.items
                if _expense_matches_read_filters(
                    child,
                    search_lower=None,
                    category=category,
                    start_date=start_date,
                    end_date=end_date,
                )
            )

    output = StringIO()
    output.write("\ufeff")
    writer = csv.writer(output)
    writer.writerow(headers_row)

    for exp in items:
        translated_cat = trans_dict.get(exp.category.value, exp.category.value)
        writer.writerow([
            exp.date.strftime("%d.%m.%Y"),
            sanitize_csv_cell(exp.title),
            exp.amount,
            translated_cat,
            sanitize_csv_cell(exp.description),
        ])

    output.seek(0)
    headers = {"Content-Disposition": "attachment; filename=expenses.csv"}
    return StreamingResponse(output, media_type="text/csv; charset=utf-8", headers=headers)


@router.post("/session-drafts", response_model=schemas.SessionDraftOut, status_code=status.HTTP_201_CREATED)
def create_session_draft(
    payload: schemas.SessionDraftCreate,
    response: Response,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
    user_tz: tzinfo = Depends(get_effective_user_timezone),
):
    if payload.date > today_in_tz(user_tz):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="expenses.date_in_future")

    rate_headers = enforce_expense_write_rate_limit(current_user.id)
    for k, v in rate_headers.items():
        response.headers[k] = v

    draft = models.ExpenseSessionDraft(
        owner_id=current_user.id,
        title=payload.title.strip(),
        description=payload.description,
        date=payload.date,
        amount_paid=payload.amount_paid,
        status=models.ExpenseSessionDraftStatus.ACTIVE,
        source_type=payload.source_type,
    )
    db.add(draft)
    db.commit()
    return build_session_draft_out(get_owned_session_draft_or_404(db, current_user.id, draft.id))


@router.get("/session-drafts", response_model=list[schemas.SessionDraftOut])
def list_session_drafts(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
):
    drafts = (
        db.query(models.ExpenseSessionDraft)
        .options(
            selectinload(models.ExpenseSessionDraft.items),
            selectinload(models.ExpenseSessionDraft.wallet_allocations).selectinload(
                models.ExpenseSessionDraftWalletAllocation.wallet
            ),
            selectinload(models.ExpenseSessionDraft.splits),
        )
        .filter(models.ExpenseSessionDraft.owner_id == current_user.id)
        .order_by(models.ExpenseSessionDraft.updated_at.desc(), models.ExpenseSessionDraft.id.desc())
        .all()
    )
    return [build_session_draft_out(draft) for draft in drafts]


@router.get("/session-drafts/active", response_model=schemas.SessionDraftOut)
def get_active_session_draft(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
):
    draft = (
        db.query(models.ExpenseSessionDraft)
        .options(
            selectinload(models.ExpenseSessionDraft.items),
            selectinload(models.ExpenseSessionDraft.wallet_allocations).selectinload(
                models.ExpenseSessionDraftWalletAllocation.wallet
            ),
            selectinload(models.ExpenseSessionDraft.splits),
        )
        .filter(
            models.ExpenseSessionDraft.owner_id == current_user.id,
            models.ExpenseSessionDraft.status.in_(
                [
                    models.ExpenseSessionDraftStatus.ACTIVE,
                    models.ExpenseSessionDraftStatus.PAUSED,
                ]
            ),
        )
        .order_by(models.ExpenseSessionDraft.updated_at.desc(), models.ExpenseSessionDraft.id.desc())
        .first()
    )
    if not draft:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="expenses.session_draft_not_found")
    return build_session_draft_out(draft)


@router.get("/session-drafts/{draft_id}", response_model=schemas.SessionDraftOut)
def get_session_draft(
    draft_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
):
    return build_session_draft_out(get_owned_session_draft_or_404(db, current_user.id, draft_id))


@router.put("/session-drafts/{draft_id}", response_model=schemas.SessionDraftOut)
def update_session_draft(
    draft_id: int,
    payload: schemas.SessionDraftUpdate,
    response: Response,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
    user_tz: tzinfo = Depends(get_effective_user_timezone),
):
    rate_headers = enforce_expense_write_rate_limit(current_user.id)
    for k, v in rate_headers.items():
        response.headers[k] = v

    draft = get_owned_session_draft_or_404(db, current_user.id, draft_id)
    ensure_draft_editable(draft)

    update_data = payload.model_dump(exclude_unset=True)
    if "date" in update_data and update_data["date"] > today_in_tz(user_tz):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="expenses.date_in_future")
    if "status" in update_data and update_data["status"] not in {
        models.ExpenseSessionDraftStatus.ACTIVE,
        models.ExpenseSessionDraftStatus.PAUSED,
    }:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="expenses.session_draft_status_invalid")

    for field, value in update_data.items():
        setattr(draft, field, value)

    db.commit()
    return build_session_draft_out(get_owned_session_draft_or_404(db, current_user.id, draft.id))


@router.post("/session-drafts/{draft_id}/pause", response_model=schemas.SessionDraftOut)
def pause_session_draft(
    draft_id: int,
    response: Response,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
):
    rate_headers = enforce_expense_write_rate_limit(current_user.id)
    for k, v in rate_headers.items():
        response.headers[k] = v

    draft = get_owned_session_draft_or_404(db, current_user.id, draft_id)
    ensure_draft_editable(draft)
    draft.status = models.ExpenseSessionDraftStatus.PAUSED
    db.commit()
    return build_session_draft_out(get_owned_session_draft_or_404(db, current_user.id, draft.id))


@router.post("/session-drafts/{draft_id}/resume", response_model=schemas.SessionDraftOut)
def resume_session_draft(
    draft_id: int,
    response: Response,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
):
    rate_headers = enforce_expense_write_rate_limit(current_user.id)
    for k, v in rate_headers.items():
        response.headers[k] = v

    draft = get_owned_session_draft_or_404(db, current_user.id, draft_id)
    ensure_draft_editable(draft)
    draft.status = models.ExpenseSessionDraftStatus.ACTIVE
    db.commit()
    return build_session_draft_out(get_owned_session_draft_or_404(db, current_user.id, draft.id))


@router.post("/session-drafts/{draft_id}/abandon", response_model=schemas.SessionDraftOut)
def abandon_session_draft(
    draft_id: int,
    response: Response,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
):
    rate_headers = enforce_expense_write_rate_limit(current_user.id)
    for k, v in rate_headers.items():
        response.headers[k] = v

    draft = get_owned_session_draft_or_404(db, current_user.id, draft_id)
    ensure_draft_editable(draft)
    draft.status = models.ExpenseSessionDraftStatus.ABANDONED
    db.commit()
    return build_session_draft_out(get_owned_session_draft_or_404(db, current_user.id, draft.id))


@router.delete("/session-drafts/{draft_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_session_draft(
    draft_id: int,
    response: Response,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
):
    rate_headers = enforce_expense_write_rate_limit(current_user.id)
    for k, v in rate_headers.items():
        response.headers[k] = v

    draft = get_owned_session_draft_or_404(db, current_user.id, draft_id)
    if draft.status == models.ExpenseSessionDraftStatus.FINALIZED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="expenses.session_draft_finalized")
    db.delete(draft)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/session-drafts/{draft_id}/items", response_model=schemas.SessionDraftOut, status_code=status.HTTP_201_CREATED)
def add_session_draft_item(
    draft_id: int,
    payload: schemas.SessionDraftItemCreate,
    response: Response,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
):
    rate_headers = enforce_expense_write_rate_limit(current_user.id)
    for k, v in rate_headers.items():
        response.headers[k] = v

    draft = get_owned_session_draft_or_404(db, current_user.id, draft_id)
    ensure_draft_editable(draft)
    validate_session_item_links(
        db,
        current_user.id,
        payload.category,
        payload.subcategory_id,
        payload.project_id,
        payload.project_subcategory_id,
    )

    db.add(
        models.ExpenseSessionDraftItem(
            draft_id=draft.id,
            owner_id=current_user.id,
            label=payload.label.strip(),
            original_amount=payload.original_amount,
            category=payload.category,
            subcategory_id=payload.subcategory_id,
            project_id=payload.project_id,
            project_subcategory_id=payload.project_subcategory_id,
            sort_order=payload.sort_order,
        )
    )
    db.commit()
    return build_session_draft_out(get_owned_session_draft_or_404(db, current_user.id, draft.id))


@router.put("/session-drafts/{draft_id}/items/{item_id}", response_model=schemas.SessionDraftOut)
def update_session_draft_item(
    draft_id: int,
    item_id: int,
    payload: schemas.SessionDraftItemUpdate,
    response: Response,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
):
    rate_headers = enforce_expense_write_rate_limit(current_user.id)
    for k, v in rate_headers.items():
        response.headers[k] = v

    draft = get_owned_session_draft_or_404(db, current_user.id, draft_id)
    ensure_draft_editable(draft)
    item = get_owned_session_draft_item_or_404(db, current_user.id, draft_id, item_id)

    category = payload.category or item.category
    subcategory_id = payload.subcategory_id if "subcategory_id" in payload.model_fields_set else item.subcategory_id
    project_id = payload.project_id if "project_id" in payload.model_fields_set else item.project_id
    project_subcategory_id = (
        payload.project_subcategory_id
        if "project_subcategory_id" in payload.model_fields_set
        else item.project_subcategory_id
    )
    validate_session_item_links(
        db,
        current_user.id,
        category,
        subcategory_id,
        project_id,
        project_subcategory_id,
    )

    update_data = payload.model_dump(exclude_unset=True)
    if "label" in update_data and update_data["label"] is not None:
        update_data["label"] = update_data["label"].strip()
    for field, value in update_data.items():
        setattr(item, field, value)

    db.commit()
    return build_session_draft_out(get_owned_session_draft_or_404(db, current_user.id, draft.id))


@router.delete("/session-drafts/{draft_id}/items/{item_id}", response_model=schemas.SessionDraftOut)
def delete_session_draft_item(
    draft_id: int,
    item_id: int,
    response: Response,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
):
    rate_headers = enforce_expense_write_rate_limit(current_user.id)
    for k, v in rate_headers.items():
        response.headers[k] = v

    draft = get_owned_session_draft_or_404(db, current_user.id, draft_id)
    ensure_draft_editable(draft)
    item = get_owned_session_draft_item_or_404(db, current_user.id, draft_id, item_id)
    db.delete(item)
    db.commit()
    return build_session_draft_out(get_owned_session_draft_or_404(db, current_user.id, draft.id))


@router.post(
    "/session-drafts/{draft_id}/wallet-allocations",
    response_model=schemas.SessionDraftOut,
    status_code=status.HTTP_201_CREATED,
)
def add_session_wallet_allocation(
    draft_id: int,
    payload: schemas.SessionDraftWalletAllocationCreate,
    response: Response,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
):
    rate_headers = enforce_expense_write_rate_limit(current_user.id)
    for k, v in rate_headers.items():
        response.headers[k] = v

    draft = get_owned_session_draft_or_404(db, current_user.id, draft_id)
    ensure_draft_editable(draft)
    wallet = _get_owned_wallet_or_404(db, current_user.id, payload.wallet_id)
    if not wallet.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="wallets.archived_locked")
    existing = (
        db.query(models.ExpenseSessionDraftWalletAllocation)
        .filter(
            models.ExpenseSessionDraftWalletAllocation.draft_id == draft.id,
            models.ExpenseSessionDraftWalletAllocation.wallet_id == wallet.id,
        )
        .first()
    )
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="expenses.session_wallet_duplicate")

    db.add(
        models.ExpenseSessionDraftWalletAllocation(
            draft_id=draft.id,
            owner_id=current_user.id,
            wallet_id=wallet.id,
            amount=payload.amount,
        )
    )
    db.commit()
    return build_session_draft_out(get_owned_session_draft_or_404(db, current_user.id, draft.id))


@router.put("/session-drafts/{draft_id}/wallet-allocations/{allocation_id}", response_model=schemas.SessionDraftOut)
def update_session_wallet_allocation(
    draft_id: int,
    allocation_id: int,
    payload: schemas.SessionDraftWalletAllocationUpdate,
    response: Response,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
):
    rate_headers = enforce_expense_write_rate_limit(current_user.id)
    for k, v in rate_headers.items():
        response.headers[k] = v

    draft = get_owned_session_draft_or_404(db, current_user.id, draft_id)
    ensure_draft_editable(draft)
    allocation = get_owned_session_wallet_allocation_or_404(db, current_user.id, draft_id, allocation_id)
    if allocation.wallet and not allocation.wallet.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="wallets.archived_locked")
    allocation.amount = payload.amount
    db.commit()
    return build_session_draft_out(get_owned_session_draft_or_404(db, current_user.id, draft.id))


@router.delete("/session-drafts/{draft_id}/wallet-allocations/{allocation_id}", response_model=schemas.SessionDraftOut)
def delete_session_wallet_allocation(
    draft_id: int,
    allocation_id: int,
    response: Response,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
):
    rate_headers = enforce_expense_write_rate_limit(current_user.id)
    for k, v in rate_headers.items():
        response.headers[k] = v

    draft = get_owned_session_draft_or_404(db, current_user.id, draft_id)
    ensure_draft_editable(draft)
    allocation = get_owned_session_wallet_allocation_or_404(db, current_user.id, draft_id, allocation_id)
    db.delete(allocation)
    db.commit()
    return build_session_draft_out(get_owned_session_draft_or_404(db, current_user.id, draft.id))


@router.post("/session-drafts/{draft_id}/splits", response_model=schemas.SessionDraftOut, status_code=status.HTTP_201_CREATED)
def add_session_split(
    draft_id: int,
    payload: schemas.SessionDraftSplitCreate,
    response: Response,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
):
    rate_headers = enforce_expense_write_rate_limit(current_user.id)
    for k, v in rate_headers.items():
        response.headers[k] = v

    draft = get_owned_session_draft_or_404(db, current_user.id, draft_id)
    ensure_draft_editable(draft)
    db.add(
        models.ExpenseSessionDraftSplit(
            draft_id=draft.id,
            owner_id=current_user.id,
            contact_name=payload.contact_name.strip(),
            amount=payload.amount,
        )
    )
    db.commit()
    return build_session_draft_out(get_owned_session_draft_or_404(db, current_user.id, draft.id))


@router.put("/session-drafts/{draft_id}/splits/{split_id}", response_model=schemas.SessionDraftOut)
def update_session_split(
    draft_id: int,
    split_id: int,
    payload: schemas.SessionDraftSplitUpdate,
    response: Response,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
):
    rate_headers = enforce_expense_write_rate_limit(current_user.id)
    for k, v in rate_headers.items():
        response.headers[k] = v

    draft = get_owned_session_draft_or_404(db, current_user.id, draft_id)
    ensure_draft_editable(draft)
    split = get_owned_session_split_or_404(db, current_user.id, draft_id, split_id)
    update_data = payload.model_dump(exclude_unset=True)
    if "contact_name" in update_data and update_data["contact_name"] is not None:
        update_data["contact_name"] = update_data["contact_name"].strip()
    for field, value in update_data.items():
        setattr(split, field, value)
    db.commit()
    return build_session_draft_out(get_owned_session_draft_or_404(db, current_user.id, draft.id))


@router.delete("/session-drafts/{draft_id}/splits/{split_id}", response_model=schemas.SessionDraftOut)
def delete_session_split(
    draft_id: int,
    split_id: int,
    response: Response,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
):
    rate_headers = enforce_expense_write_rate_limit(current_user.id)
    for k, v in rate_headers.items():
        response.headers[k] = v

    draft = get_owned_session_draft_or_404(db, current_user.id, draft_id)
    ensure_draft_editable(draft)
    split = get_owned_session_split_or_404(db, current_user.id, draft_id, split_id)
    db.delete(split)
    db.commit()
    return build_session_draft_out(get_owned_session_draft_or_404(db, current_user.id, draft.id))


@router.post("/session-drafts/{draft_id}/finalize", response_model=schemas.ExpenseOut, status_code=status.HTTP_201_CREATED)
def finalize_expense_session_draft(
    draft_id: int,
    response: Response,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
    user_tz: tzinfo = Depends(get_effective_user_timezone),
):
    rate_headers = enforce_expense_write_rate_limit(current_user.id)
    for k, v in rate_headers.items():
        response.headers[k] = v

    draft = get_owned_session_draft_or_404(db, current_user.id, draft_id)
    if draft.date > today_in_tz(user_tz):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="expenses.date_in_future")

    result = finalize_session_draft(db, current_user.id, draft_id)
    db.commit()

    for budget_id in result.budget_ids:
        budget = db.query(models.Budget).filter(models.Budget.id == budget_id).first()
        if budget:
            check_budget_alerts(db, budget)
    if result.budget_ids:
        db.commit()

    created = _get_owned_event_or_404(
        db,
        current_user.id,
        result.event.id,
        event_types=[models.TransactionType.EXPENSE],
    )
    return _build_expense_out(created, _refund_totals_by_parent(db, current_user.id), _asset_ids_by_event(db, current_user.id))


@router.post("/merge-groups", response_model=schemas.ExpenseMergeGroupDetailOut, status_code=status.HTTP_201_CREATED)
def create_expense_merge_group(
    payload: schemas.ExpenseMergeGroupCreate,
    response: Response,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
):
    rate_headers = enforce_expense_write_rate_limit(current_user.id)
    for k, v in rate_headers.items():
        response.headers[k] = v

    events = _validate_merge_group_events(db, current_user.id, payload.expense_ids)
    group = models.ExpenseMergeGroup(
        owner_id=current_user.id,
        title=payload.title,
        description=payload.description,
    )
    db.add(group)
    db.flush()
    for event in events:
        event.merge_group_id = group.id
    db.commit()
    return _build_merge_group_out(
        _get_owned_merge_group_or_404(db, current_user.id, group.id),
        _refund_totals_by_parent(db, current_user.id),
        _asset_ids_by_event(db, current_user.id),
        include_items=True,
    )


@router.get("/merge-groups", response_model=list[schemas.ExpenseMergeGroupOut])
def list_expense_merge_groups(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
):
    groups = (
        db.query(models.ExpenseMergeGroup)
        .options(selectinload(models.ExpenseMergeGroup.events).selectinload(models.FinancialEvent.wallet_legs))
        .filter(models.ExpenseMergeGroup.owner_id == current_user.id)
        .order_by(models.ExpenseMergeGroup.updated_at.desc(), models.ExpenseMergeGroup.id.desc())
        .all()
    )
    refund_totals = _refund_totals_by_parent(db, current_user.id)
    return [_build_merge_group_out(group, refund_totals) for group in groups]


@router.get("/merge-groups/{group_id}", response_model=schemas.ExpenseMergeGroupDetailOut)
def get_expense_merge_group(
    group_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
):
    return _build_merge_group_out(
        _get_owned_merge_group_or_404(db, current_user.id, group_id),
        _refund_totals_by_parent(db, current_user.id),
        _asset_ids_by_event(db, current_user.id),
        include_items=True,
    )


@router.put("/merge-groups/{group_id}", response_model=schemas.ExpenseMergeGroupDetailOut)
def update_expense_merge_group(
    group_id: int,
    payload: schemas.ExpenseMergeGroupUpdate,
    response: Response,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
):
    rate_headers = enforce_expense_write_rate_limit(current_user.id)
    for k, v in rate_headers.items():
        response.headers[k] = v

    group = _get_owned_merge_group_or_404(db, current_user.id, group_id)
    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(group, field, value)
    db.commit()
    return _build_merge_group_out(
        _get_owned_merge_group_or_404(db, current_user.id, group_id),
        _refund_totals_by_parent(db, current_user.id),
        _asset_ids_by_event(db, current_user.id),
        include_items=True,
    )


@router.post("/merge-groups/{group_id}/items", response_model=schemas.ExpenseMergeGroupDetailOut)
def add_expenses_to_merge_group(
    group_id: int,
    payload: schemas.ExpenseMergeGroupItemsRequest,
    response: Response,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
):
    rate_headers = enforce_expense_write_rate_limit(current_user.id)
    for k, v in rate_headers.items():
        response.headers[k] = v

    group = _get_owned_merge_group_or_404(db, current_user.id, group_id)
    events = _validate_merge_group_events(db, current_user.id, payload.expense_ids, allow_group_id=group.id)
    for event in events:
        event.merge_group_id = group.id
    db.commit()
    return _build_merge_group_out(
        _get_owned_merge_group_or_404(db, current_user.id, group.id),
        _refund_totals_by_parent(db, current_user.id),
        _asset_ids_by_event(db, current_user.id),
        include_items=True,
    )


@router.delete("/merge-groups/{group_id}/items/{expense_id}", response_model=schemas.ExpenseMergeGroupDetailOut | None)
def remove_expense_from_merge_group(
    group_id: int,
    expense_id: int,
    response: Response,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
):
    rate_headers = enforce_expense_write_rate_limit(current_user.id)
    for k, v in rate_headers.items():
        response.headers[k] = v

    group = _get_owned_merge_group_or_404(db, current_user.id, group_id)
    event = _get_owned_event_or_404(
        db,
        current_user.id,
        expense_id,
        event_types=[models.TransactionType.EXPENSE],
    )
    if event.merge_group_id != group.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="expenses.not_in_merge_group")

    event.merge_group_id = None
    db.flush()
    remaining = (
        db.query(models.FinancialEvent)
        .filter(models.FinancialEvent.merge_group_id == group.id)
        .all()
    )
    if len(remaining) < 2:
        for child in remaining:
            child.merge_group_id = None
        db.delete(group)
        db.commit()
        response.status_code = status.HTTP_204_NO_CONTENT
        return None

    db.commit()
    return _build_merge_group_out(
        _get_owned_merge_group_or_404(db, current_user.id, group_id),
        _refund_totals_by_parent(db, current_user.id),
        _asset_ids_by_event(db, current_user.id),
        include_items=True,
    )


@router.delete("/merge-groups/{group_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_expense_merge_group(
    group_id: int,
    response: Response,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
):
    rate_headers = enforce_expense_write_rate_limit(current_user.id)
    for k, v in rate_headers.items():
        response.headers[k] = v

    group = _get_owned_merge_group_or_404(db, current_user.id, group_id)
    for event in list(group.events):
        event.merge_group_id = None
    db.delete(group)
    db.commit()
    response.status_code = status.HTTP_204_NO_CONTENT
    return None


@router.get("/{id}", response_model=schemas.ExpenseOut)
def get_expense(
    id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
):
    event = _get_owned_event_or_404(db, current_user.id, id)
    return _build_expense_out(
        event,
        _refund_totals_by_parent(db, current_user.id),
        _asset_ids_by_event(db, current_user.id),
    )


@router.get("/{id}/detail", response_model=schemas.ExpenseDetailOut)
def get_expense_detail(
    id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
):
    refund_totals = _refund_totals_by_parent(db, current_user.id)
    asset_ids = _asset_ids_by_event(db, current_user.id)
    event = _get_owned_event_or_404(db, current_user.id, id)
    return _build_expense_detail_out(db, current_user.id, event, refund_totals, asset_ids)


@router.put("/{id}", response_model=schemas.ExpenseOut)
def update_expense(
    id: int,
    expense: schemas.ExpenseUpdate,
    response: Response,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
):
    rate_headers = enforce_expense_write_rate_limit(current_user.id)
    for k, v in rate_headers.items():
        response.headers[k] = v

    event = _get_owned_event_or_404(
        db,
        current_user.id,
        id,
        event_types=[models.TransactionType.EXPENSE, models.TransactionType.REFUND],
    )

    for wallet_leg in event.wallet_legs:
        if wallet_leg.wallet and not wallet_leg.wallet.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="wallets.archived_locked",
            )

    has_refund = (
        db.query(models.FinancialEvent.id)
        .filter(
            models.FinancialEvent.owner_id == current_user.id,
            models.FinancialEvent.event_type == models.TransactionType.REFUND,
            models.FinancialEvent.linked_event_id == event.id,
        )
        .first()
    )
    if has_refund:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="expenses.has_refund_lock",
        )

    event.title = expense.title
    event.description = expense.description

    db.commit()

    updated = _get_owned_event_or_404(db, current_user.id, event.id)
    return _build_expense_out(
        updated,
        _refund_totals_by_parent(db, current_user.id),
        _asset_ids_by_event(db, current_user.id),
    )


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_expense(
    id: int,
    response: Response,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
    user_tz: tzinfo = Depends(get_effective_user_timezone),
):
    rate_headers = enforce_expense_write_rate_limit(current_user.id)
    for k, v in rate_headers.items():
        response.headers[k] = v

    event = _get_owned_event_any_status_or_404(
        db,
        current_user.id,
        id,
        event_types=[models.TransactionType.EXPENSE],
    )

    if event.status != models.FinancialEventStatus.POSTED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="expenses.not_posted",
        )
    if event.is_session:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="expenses.session_void_not_supported",
        )

    for wallet_leg in event.wallet_legs:
        if wallet_leg.wallet and not wallet_leg.wallet.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="wallets.archived_locked",
            )

    has_refund = (
        db.query(models.FinancialEvent.id)
        .filter(
            models.FinancialEvent.owner_id == current_user.id,
            models.FinancialEvent.status == models.FinancialEventStatus.POSTED,
            models.FinancialEvent.event_type == models.TransactionType.REFUND,
            models.FinancialEvent.linked_event_id == event.id,
        )
        .first()
    )
    if has_refund:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="expenses.has_refund_lock",
        )

    has_asset = (
        db.query(models.Asset.id)
        .filter(
            models.Asset.owner_id == current_user.id,
            models.Asset.origin_event_id == event.id,
        )
        .first()
    )
    if has_asset:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="expenses.asset_link_lock",
        )

    has_debt = (
        db.query(models.Debt.id)
        .filter(
            models.Debt.owner_id == current_user.id,
            models.Debt.linked_event_id == event.id,
        )
        .first()
    )
    linked_entity_dependency = any(
        leg.debt_id or leg.installment_plan_id or leg.installment_payment_id
        for leg in event.entity_legs
    )
    if has_debt or linked_entity_dependency:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="expenses.linked_dependency_lock",
        )

    budget_ids = {leg.budget_id for leg in event.entity_legs if leg.budget_id}

    void_date = today_in_tz(user_tz)
    reversal = models.FinancialEvent(
        owner_id=current_user.id,
        title=f"Void {event.title}",
        description=f"Reversal for voided expense #{event.id}",
        event_type=event.event_type,
        status=models.FinancialEventStatus.REVERSAL,
        reference_type=models.ReferenceType.VOID_REVERSAL,
        is_session=False,
        linked_event_id=event.id,
        reverses_event_id=event.id,
        date=void_date,
    )
    db.add(reversal)
    db.flush()

    for wallet_leg in event.wallet_legs:
        reversal_amount = -int(wallet_leg.amount)
        WalletService.adjust_balance(db, wallet_leg.wallet_id, reversal_amount)
        db.add(
            models.WalletLedger(
                owner_id=current_user.id,
                event_id=reversal.id,
                wallet_id=wallet_leg.wallet_id,
                amount=reversal_amount,
            )
        )

    for entity_leg in event.entity_legs:
        db.add(
            models.EntityLedger(
                event_id=reversal.id,
                label=entity_leg.label,
                amount=-int(entity_leg.amount),
                original_amount=(
                    -int(entity_leg.original_amount)
                    if entity_leg.original_amount is not None
                    else None
                ),
                category=entity_leg.category,
                subcategory_id=entity_leg.subcategory_id,
                project_id=entity_leg.project_id,
                project_subcategory_id=entity_leg.project_subcategory_id,
                budget_id=entity_leg.budget_id,
            )
        )

    event.status = models.FinancialEventStatus.VOIDED
    event.voided_at = datetime.now(timezone.utc)
    event.void_reason = "Deleted by user"
    event.void_reversal_event_id = reversal.id

    db.commit()

    for budget_id in budget_ids:
        budget = db.query(models.Budget).filter(models.Budget.id == budget_id).first()
        if budget:
            check_budget_alerts(db, budget)
    if budget_ids:
        db.commit()

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{id}/mark-as-asset", response_model=schemas.AssetOut, status_code=status.HTTP_201_CREATED)
def mark_expense_as_asset(
    id: int,
    payload: schemas.ExpenseMarkAssetRequest,
    response: Response,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
):
    rate_headers = enforce_expense_write_rate_limit(current_user.id)
    for k, v in rate_headers.items():
        response.headers[k] = v

    event = _get_owned_event_or_404(
        db,
        current_user.id,
        id,
        event_types=[models.TransactionType.EXPENSE],
    )
    _raise_if_asset_origin_ineligible(db, current_user.id, event)
    existing_asset = (
        db.query(models.Asset)
        .filter(
            models.Asset.owner_id == current_user.id,
            models.Asset.origin_event_id == event.id,
        )
        .first()
    )
    if existing_asset:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="assets.already_exists_for_expense")

    asset = models.Asset(
        owner_id=current_user.id,
        title=(payload.title or event.title).strip(),
        description=payload.description if payload.description is not None else event.description,
        origin_event_id=event.id,
        purchase_value=_event_amount(event),
        current_value=int(payload.current_value) if payload.current_value is not None else _event_amount(event),
        status="owned",
    )
    db.add(asset)
    db.commit()
    db.refresh(asset)
    return schemas.AssetOut.model_validate(asset)


@router.post("/{id}/mark-as-recurring", response_model=schemas.RecurringExpenseOut, status_code=status.HTTP_201_CREATED)
def mark_expense_as_recurring(
    id: int,
    payload: schemas.ExpenseMarkRecurringRequest,
    response: Response,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
    user_tz: tzinfo = Depends(get_effective_user_timezone),
):
    if not current_user.is_premium:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="recurring_expenses.premium_required")

    rate_headers = enforce_expense_write_rate_limit(current_user.id)
    for k, v in rate_headers.items():
        response.headers[k] = v

    event = _get_owned_event_or_404(
        db,
        current_user.id,
        id,
        event_types=[models.TransactionType.EXPENSE],
    )
    _raise_if_split_parent(event)
    wallet = _single_wallet_for_event(event)
    wallet_id = payload.wallet_id or (wallet.id if wallet else None)
    if payload.recording_mode == models.RecurringRecordingMode.AUTO_RECORD and wallet_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="recurring_expenses.auto_wallet_required")

    recurring_wallet = None
    if wallet_id is not None:
        recurring_wallet = _get_owned_wallet_or_404(db, current_user.id, wallet_id)
        if not recurring_wallet.is_active:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="recurring_expenses.wallet_archived")

    seed_date = payload.start_date or event.date
    if seed_date.year < 2020:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="expenses.date_too_early")

    next_due_date = calculate_next_due_date(seed_date, payload.frequency, seed_date.day)
    today = today_in_tz(user_tz)
    while next_due_date <= today:
        advanced = calculate_next_due_date(next_due_date, payload.frequency, seed_date.day)
        if advanced == next_due_date:
            break
        next_due_date = advanced

    recurring = models.RecurringExpense(
        owner_id=current_user.id,
        title=event.title,
        amount=_event_amount(event),
        category=_primary_entity_leg(event).category,
        description=event.description,
        frequency=payload.frequency,
        start_date=seed_date,
        next_due_date=next_due_date,
        wallet_id=recurring_wallet.id if recurring_wallet is not None else None,
        cycle_behavior=payload.cycle_behavior,
        recording_mode=payload.recording_mode,
        status=models.RecurringStatus.ACTIVE,
        original_due_day=seed_date.day,
    )
    db.add(recurring)
    db.flush()
    db.add(
        models.RecurringEvent(
            recurring_expense_id=recurring.id,
            event_type=models.RecurringEventType.CREATED,
            target_due_date=seed_date,
            new_next_due_date=next_due_date,
            metadata_notes=f"Seeded from expense {event.id}",
        )
    )
    db.commit()
    db.refresh(recurring)

    days_until_due = (recurring.next_due_date - today).days
    return schemas.RecurringExpenseOut(
        id=recurring.id,
        owner_id=recurring.owner_id,
        title=recurring.title,
        amount=int(recurring.amount),
        category=recurring.category,
        description=recurring.description,
        frequency=recurring.frequency,
        start_date=recurring.start_date,
        next_due_date=recurring.next_due_date,
        days_until_due=days_until_due,
        status=recurring.status,
        wallet_id=recurring.wallet_id,
        cycle_behavior=recurring.cycle_behavior,
        recording_mode=recurring.recording_mode,
        retry_count=recurring.retry_count,
        created_at=recurring.created_at,
        owner=schemas.UserOut.model_validate(current_user),
    )


@router.post("/{id}/split", response_model=schemas.ExpenseOut)
def split_expense(
    id: int,
    payload: schemas.ExpenseSplitRequest,
    response: Response,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
):
    rate_headers = enforce_expense_write_rate_limit(current_user.id)
    for k, v in rate_headers.items():
        response.headers[k] = v

    event = _get_owned_event_or_404(
        db,
        current_user.id,
        id,
        event_types=[models.TransactionType.EXPENSE],
    )
    if event.is_session:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="expenses.complex_event_not_supported")

    entity_leg = _primary_entity_leg(event)
    if entity_leg is None or entity_leg.category is None or entity_leg.budget_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="expenses.complex_event_not_supported")
    _raise_if_split_parent(event)
    parent_project_id = entity_leg.project_id

    if event.id in _asset_ids_by_event(db, current_user.id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="expenses.asset_split_lock")
    if any(leg.debt_id or leg.installment_plan_id or leg.installment_payment_id for leg in event.entity_legs):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="expenses.linked_dependency_lock")

    has_refund = (
        db.query(models.FinancialEvent.id)
        .filter(
            models.FinancialEvent.owner_id == current_user.id,
            models.FinancialEvent.event_type == models.TransactionType.REFUND,
            models.FinancialEvent.linked_event_id == event.id,
        )
        .first()
    )
    if has_refund:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="expenses.has_refund_lock")

    total_amount = _event_amount(event)
    split_total = sum(item.amount for item in payload.items)
    if split_total != total_amount:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="expenses.split_total_mismatch")

    current_project = None
    if parent_project_id is not None:
        current_project = get_owned_project_or_404(db, current_user.id, parent_project_id)

    validated_items: list[
        tuple[
            schemas.ExpenseSplitItemCreate,
            models.ExpenseCategory,
            models.Budget,
            models.UserSubcategory | None,
            models.ProjectSubcategory | None,
        ]
    ] = []
    requested_by_budget: dict[int, int] = {}
    requested_by_subcategory: dict[int, int] = {}
    validated_subcategories: dict[int, models.UserSubcategory] = {}
    requested_by_project_category: dict[models.ExpenseCategory, int] = {}
    requested_by_project_subcategory: dict[int, int] = {}
    validated_project_subcategories: dict[int, models.ProjectSubcategory] = {}
    for item in payload.items:
        line_category = item.category or entity_leg.category
        validate_real_expense_category(line_category)
        subcategory, _, project_subcategory = validate_session_item_links(
            db,
            current_user.id,
            line_category,
            item.subcategory_id,
            parent_project_id,
            item.project_subcategory_id,
        )
        budget = resolve_budget_for_expense_month(db, current_user.id, line_category, event.date)
        requested_by_budget[budget.id] = requested_by_budget.get(budget.id, 0) + int(item.amount)
        if subcategory is not None:
            validated_subcategories[subcategory.id] = subcategory
            requested_by_subcategory[subcategory.id] = requested_by_subcategory.get(subcategory.id, 0) + int(item.amount)
        if current_project is not None:
            requested_by_project_category[line_category] = requested_by_project_category.get(line_category, 0) + int(item.amount)
        if project_subcategory is not None:
            validated_project_subcategories[project_subcategory.id] = project_subcategory
            requested_by_project_subcategory[project_subcategory.id] = (
                requested_by_project_subcategory.get(project_subcategory.id, 0) + int(item.amount)
            )
        validated_items.append((item, line_category, budget, subcategory, project_subcategory))

    if current_project is not None:
        for line_category, requested_amount in requested_by_project_category.items():
            validate_project_budget(
                db,
                current_user.id,
                current_project,
                line_category,
                requested_amount,
                event.date,
                exclude_event_id=event.id,
            )
        for project_subcategory_id, requested_amount in requested_by_project_subcategory.items():
            project_subcategory = validated_project_subcategories[project_subcategory_id]
            validate_project_budget(
                db,
                current_user.id,
                current_project,
                project_subcategory.category,
                requested_amount,
                event.date,
                project_subcategory=project_subcategory,
                exclude_event_id=event.id,
            )

    for existing_leg in list(event.entity_legs):
        db.delete(existing_leg)
    db.flush()

    for item, line_category, budget, _, project_subcategory in validated_items:
        db.add(
            models.EntityLedger(
                event_id=event.id,
                label=item.label.strip(),
                amount=item.amount,
                category=line_category,
                subcategory_id=item.subcategory_id,
                project_id=parent_project_id,
                project_subcategory_id=item.project_subcategory_id,
                budget_id=budget.id,
            )
        )

    db.commit()
    updated = _get_owned_event_or_404(db, current_user.id, event.id)
    return _build_expense_out(
        updated,
        _refund_totals_by_parent(db, current_user.id),
        _asset_ids_by_event(db, current_user.id),
    )


@router.post("/{id}/refund", status_code=status.HTTP_201_CREATED, response_model=schemas.ExpenseOut)
def refund_expense(
    id: int,
    refund_data: schemas.RefundRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
    user_tz: tzinfo = Depends(get_effective_user_timezone),
):
    original_event = _get_owned_event_or_404(
        db,
        current_user.id,
        id,
        event_types=[models.TransactionType.EXPENSE],
    )
    if _event_has_asset(db, current_user.id, original_event.id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="expenses.asset_link_lock")
    entity_leg = _single_entity_leg_or_400(original_event)
    original_wallet_leg = _single_wallet_leg_or_400(original_event)

    total_already_refunded = int(_refund_totals_by_parent(db, current_user.id).get(original_event.id, 0))
    max_allowable = _event_amount(original_event) - total_already_refunded
    refund_amount = refund_data.amount

    if refund_amount is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="expenses.amount_required",
        )
    if refund_amount <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="expenses.already_fully_refunded",
        )
    if refund_amount > max_allowable:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="expenses.refund_exceeds_total",
        )

    target_wallet_id = refund_data.destination_wallet_id or original_wallet_leg.wallet_id
    target_wallet = _get_owned_wallet_or_404(db, current_user.id, target_wallet_id)
    if not target_wallet.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="wallets.archived_locked",
        )

    is_partial = refund_amount < max_allowable or total_already_refunded > 0
    refund_title = "Partial Refund" if is_partial else "Refund"

    refund_event = WalletService.record_transaction(
        db=db,
        owner_id=current_user.id,
        wallet_id=target_wallet_id,
        transaction_type=models.TransactionType.REFUND,
        amount_delta=refund_amount,
        category=entity_leg.category,
        title=refund_title,
        description=original_event.title,
        budget_id=entity_leg.budget_id,
        debt_id=entity_leg.debt_id,
        transaction_date=now_in_tz(user_tz).date(),
        linked_event_id=original_event.id,
    )

    if entity_leg.debt_id:
        create_debt_ledger_entry(
            db,
            owner_id=current_user.id,
            debt_id=entity_leg.debt_id,
            entry_type=models.DebtLedgerEntryType.REVERSAL,
            amount_delta=refund_amount,
            financial_event_id=refund_event.id,
            entry_date=refund_event.date,
            note="Debt-linked expense refund",
        )
        reconcile_debt(db, entity_leg.debt_id)

    db.commit()

    if entity_leg.budget_id:
        budget = db.query(models.Budget).filter(models.Budget.id == entity_leg.budget_id).first()
        if budget:
            check_budget_alerts(db, budget)
            db.commit()

    created = _get_owned_event_or_404(
        db,
        current_user.id,
        refund_event.id,
        event_types=[models.TransactionType.REFUND],
    )
    return _build_expense_out(created, _refund_totals_by_parent(db, current_user.id))
