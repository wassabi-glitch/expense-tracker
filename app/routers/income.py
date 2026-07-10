from datetime import date, tzinfo
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import func
from sqlalchemy.orm import Session, selectinload

from app.redis_rate_limiter import consume_token_bucket
from app.timezone import get_effective_user_timezone, today_in_tz
from .. import models, oauth2, schemas
from ..session import get_db
from ..services.debt_service import reconcile_debt
from ..services.financial_event_ledger_service import (
    PostEntityLeg,
    PostWalletLeg,
    post_financial_event,
    validate_wallet_epochs,
    void_financial_event,
)
from ..services.wallet_service import WalletService
from .wallets import _get_owned_wallet_or_404

INCOME_SOURCE_LIMIT = 20
INCOME_ENTRY_MONTH_LIMIT = 300
INCOME_SOURCE_WRITE_BUCKET_CAPACITY = 10
INCOME_SOURCE_WRITE_REFILL_RATE = 10 / 60
INCOME_ENTRY_WRITE_BUCKET_CAPACITY = 20
INCOME_ENTRY_WRITE_REFILL_RATE = 20 / 60

router = APIRouter(
    prefix="/income",
    tags=["Income"],
)

money_in_router = APIRouter(
    prefix="/money-in",
    tags=["Money In"],
)

MONEY_IN_EVENT_TYPES = (
    models.TransactionType.INCOME,
    models.TransactionType.REFUND,
    models.TransactionType.DEBT_SETTLEMENT,
    models.TransactionType.ADJUSTMENT,
    models.TransactionType.NEUTRAL_FLOW,
)


def _rate_limit_headers(rl) -> dict[str, str]:
    return {
        "X-RateLimit-Limit": str(rl.limit),
        "X-RateLimit-Remaining": str(rl.remaining),
        "X-RateLimit-Reset": str(rl.reset_seconds),
    }


def enforce_income_source_write_rate_limit(user_id: int) -> dict[str, str]:
    rl = consume_token_bucket(
        scope="income_sources_write",
        identifier=str(user_id),
        capacity=INCOME_SOURCE_WRITE_BUCKET_CAPACITY,
        refill_rate_per_second=INCOME_SOURCE_WRITE_REFILL_RATE,
    )
    headers = _rate_limit_headers(rl)
    if not rl.allowed:
        headers["Retry-After"] = str(rl.reset_seconds)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="income.sources_write_rate_limited",
            headers=headers,
        )
    return headers


def enforce_income_entry_write_rate_limit(user_id: int) -> dict[str, str]:
    rl = consume_token_bucket(
        scope="income_entries_write",
        identifier=str(user_id),
        capacity=INCOME_ENTRY_WRITE_BUCKET_CAPACITY,
        refill_rate_per_second=INCOME_ENTRY_WRITE_REFILL_RATE,
    )
    headers = _rate_limit_headers(rl)
    if not rl.allowed:
        headers["Retry-After"] = str(rl.reset_seconds)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="income.entries_write_rate_limited",
            headers=headers,
        )
    return headers


def _get_owned_source_or_404(db: Session, user_id: int, source_id: int) -> models.IncomeSource:
    source = (
        db.query(models.IncomeSource)
        .filter(
            models.IncomeSource.id == source_id,
            models.IncomeSource.owner_id == user_id,
        )
        .first()
    )
    if not source:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="income.source_not_found")
    return source


def _ensure_source_belongs_to_user(db: Session, user_id: int, source_id: int | None) -> None:
    if source_id is None:
        return
    source = _get_owned_source_or_404(db, user_id, source_id)
    if not source.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="income.source_inactive")


def _income_event_query(db: Session, user_id: int, *, statuses: list[models.FinancialEventStatus] | None = None):
    query = (
        db.query(models.FinancialEvent)
        .options(
            selectinload(models.FinancialEvent.wallet_legs).selectinload(models.WalletLedger.wallet),
            selectinload(models.FinancialEvent.entity_legs).selectinload(models.EntityLedger.income_source),
        )
        .filter(
            models.FinancialEvent.owner_id == user_id,
            models.FinancialEvent.event_type == models.TransactionType.INCOME,
        )
    )
    if statuses is not None:
        query = query.filter(models.FinancialEvent.status.in_(statuses))
    else:
        query = query.filter(models.FinancialEvent.status == models.FinancialEventStatus.POSTED)
    return query


def _primary_income_entity_leg(event: models.FinancialEvent) -> models.EntityLedger | None:
    for leg in event.entity_legs:
        if leg.income_source_id is not None:
            return leg
    return event.entity_legs[0] if event.entity_legs else None


def _income_amount(event: models.FinancialEvent) -> int:
    return int(sum(max(0, int(leg.amount or 0)) for leg in event.wallet_legs))


def _income_wallet_allocations_out(event: models.FinancialEvent) -> list[schemas.IncomeWalletAllocationOut]:
    return [
        schemas.IncomeWalletAllocationOut(
            wallet_id=int(leg.wallet_id),
            amount=int(leg.amount or 0),
            wallet=schemas.WalletOut.model_validate(leg.wallet) if leg.wallet else None,
        )
        for leg in event.wallet_legs
        if int(leg.amount or 0) > 0
    ]


def _income_primary_wallet_id(event: models.FinancialEvent) -> int | None:
    positive_legs = [leg for leg in event.wallet_legs if int(leg.amount or 0) > 0]
    return int(positive_legs[0].wallet_id) if len(positive_legs) == 1 else None


def _build_income_entry_out(event: models.FinancialEvent) -> schemas.IncomeEntryOut:
    entity_leg = _primary_income_entity_leg(event)
    return schemas.IncomeEntryOut(
        id=event.id,
        owner_id=event.owner_id,
        amount=_income_amount(event),
        date=event.date,
        note=event.description,
        source_id=entity_leg.income_source_id if entity_leg else None,
        wallet_id=_income_primary_wallet_id(event),
        wallet_allocations=_income_wallet_allocations_out(event),
        created_at=event.created_at,
        updated_at=event.created_at,
    )


def _default_wallet_or_400(db: Session, user_id: int) -> models.Wallet:
    wallet = (
        db.query(models.Wallet)
        .filter(
            models.Wallet.owner_id == user_id,
            models.Wallet.is_default,
        )
        .first()
    )
    if wallet is None:
        wallet = db.query(models.Wallet).filter(models.Wallet.owner_id == user_id).first()
    if wallet is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="wallets.at_least_one_required")
    return wallet


def _resolve_income_wallet_allocations(
    db: Session,
    user_id: int,
    *,
    amount: int,
    wallet_id: int | None,
    wallet_allocations: list[schemas.IncomeWalletAllocationIn],
    existing_event: models.FinancialEvent | None = None,
) -> list[tuple[models.Wallet, int]]:
    if wallet_allocations:
        requested = [(int(item.wallet_id), int(item.amount)) for item in wallet_allocations]
    elif wallet_id is not None:
        requested = [(int(wallet_id), int(amount))]
    elif existing_event is not None:
        existing_positive = [
            (int(leg.wallet_id), int(leg.amount or 0))
            for leg in existing_event.wallet_legs
            if int(leg.amount or 0) > 0
        ]
        if len(existing_positive) != 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="income.wallet_allocations_required_for_complex_entry",
            )
        requested = [(existing_positive[0][0], int(amount))]
    else:
        requested = [(int(_default_wallet_or_400(db, user_id).id), int(amount))]

    if not requested:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="income.wallet_allocations_required")

    allocation_total = sum(item_amount for _, item_amount in requested)
    if allocation_total != int(amount):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="income.wallet_allocation_total_mismatch")

    seen_wallet_ids: set[int] = set()
    resolved: list[tuple[models.Wallet, int]] = []
    for requested_wallet_id, requested_amount in requested:
        if requested_wallet_id in seen_wallet_ids:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="income.wallet_allocation_duplicate")
        seen_wallet_ids.add(requested_wallet_id)

        wallet = _get_owned_wallet_or_404(db, user_id, requested_wallet_id)
        if not wallet.is_active:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="wallets.archived_locked")
        resolved.append((wallet, int(requested_amount)))

    return resolved


def _record_income_event(
    db: Session,
    *,
    owner_id: int,
    amount: int,
    source_id: int | None,
    note: str | None,
    income_date: date,
    wallet_allocations: list[tuple[models.Wallet, int]],
    linked_event_id: int | None = None,
) -> models.FinancialEvent:
    """Create a posted INCOME FinancialEvent through the ledger seam."""
    return post_financial_event(
        db,
        owner_id=owner_id,
        title="Income",
        event_type=models.TransactionType.INCOME,
        date=income_date,
        description=note,
        entity_category=None,
        linked_event_id=linked_event_id,
        wallet_legs=[
            PostWalletLeg(wallet_id=wallet.id, amount=int(allocation_amount))
            for wallet, allocation_amount in wallet_allocations
        ],
        entity_legs=[
            PostEntityLeg(
                amount=int(amount),
                income_source_id=source_id,
            )
        ],
    )


def _replace_income_event_legs(
    db: Session,
    event: models.FinancialEvent,
    *,
    amount: int,
    source_id: int | None,
    wallet_allocations: list[tuple[models.Wallet, int]],
) -> None:
    for leg in list(event.wallet_legs):
        WalletService.adjust_balance(db, leg.wallet_id, -int(leg.amount or 0), models.TransactionType.INCOME)
        db.delete(leg)
    for leg in list(event.entity_legs):
        db.delete(leg)
    db.flush()

    for wallet, allocation_amount in wallet_allocations:
        WalletService.adjust_balance(db, wallet.id, int(allocation_amount), models.TransactionType.INCOME)
        db.add(
            models.WalletLedger(
                owner_id=event.owner_id,
                event_id=event.id,
                wallet_id=wallet.id,
                amount=int(allocation_amount),
            )
        )

    db.add(
        models.EntityLedger(
            event_id=event.id,
            amount=int(amount),
            income_source_id=source_id,
        )
    )


def _get_owned_entry_or_404(db: Session, user_id: int, entry_id: int) -> models.FinancialEvent:
    entry = _income_event_query(db, user_id).filter(models.FinancialEvent.id == entry_id).first()
    if not entry:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="income.entry_not_found")
    return entry


def _get_owned_entry_any_status_or_404(db: Session, user_id: int, entry_id: int) -> models.FinancialEvent:
    """Fetch an income FinancialEvent regardless of status.

    Used by delete to give a clearer error message for already-voided
    entries rather than a misleading 404.
    """
    entry = (
        _income_event_query(db, user_id, statuses=[models.FinancialEventStatus.POSTED, models.FinancialEventStatus.VOIDED])
        .filter(models.FinancialEvent.id == entry_id)
        .first()
    )
    if not entry:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="income.entry_not_found")
    return entry


def _income_wallet_allocation_changed(
    entry: models.FinancialEvent,
    payload: schemas.IncomeEntryUpdate,
) -> bool:
    """Return True if the wallet allocation in *payload* differs from *entry*."""
    existing_positive = sorted(
        (int(leg.wallet_id), int(leg.amount or 0))
        for leg in entry.wallet_legs
        if int(leg.amount or 0) > 0
    )

    if payload.wallet_allocations:
        requested = sorted(
            (int(item.wallet_id), int(item.amount))
            for item in payload.wallet_allocations
        )
    elif payload.wallet_id is not None:
        requested = [(int(payload.wallet_id), int(payload.amount))]
    else:
        # No wallet info in payload — default to the existing single-wallet
        # allocation.  If the entry has multiple wallets this will be caught
        # by _resolve_income_wallet_allocations later.
        return False

    return existing_positive != requested


def _validate_entry_date_in_current_month(entry_date: date, today: date) -> None:
    """Enforce user-timezone normal logging boundary for income entries.

    Delegates to the shared ``validate_normal_logging_date`` helper so
    expense and income date rules stay in sync.
    """
    from app.timezone import validate_normal_logging_date

    validate_normal_logging_date(
        entry_date,
        today,
        future_detail="income.date_in_future",
        closed_detail="income.date_closed_period",
    )


def _money_in_event_query(db: Session, user_id: int):
    return (
        db.query(models.FinancialEvent)
        .options(
            selectinload(models.FinancialEvent.wallet_legs).selectinload(models.WalletLedger.wallet),
            selectinload(models.FinancialEvent.entity_legs).selectinload(models.EntityLedger.income_source),
        )
        .filter(
            models.FinancialEvent.owner_id == user_id,
            models.FinancialEvent.status == models.FinancialEventStatus.POSTED,
            models.FinancialEvent.event_type.in_(MONEY_IN_EVENT_TYPES),
        )
    )


def _positive_wallet_legs(event: models.FinancialEvent) -> list[models.WalletLedger]:
    return [leg for leg in event.wallet_legs if int(leg.amount or 0) > 0]


def _money_in_amount(event: models.FinancialEvent) -> int:
    return int(sum(int(leg.amount or 0) for leg in _positive_wallet_legs(event)))


def _money_in_wallets_out(event: models.FinancialEvent) -> list[schemas.MoneyInWalletOut]:
    return [
        schemas.MoneyInWalletOut(
            wallet_id=int(leg.wallet_id),
            wallet_name=leg.wallet.name if leg.wallet else "Wallet",
            amount=int(leg.amount or 0),
        )
        for leg in _positive_wallet_legs(event)
    ]


def _money_in_primary_entity(event: models.FinancialEvent) -> models.EntityLedger | None:
    for leg in event.entity_legs:
        if leg.income_source_id is not None or leg.debt_id is not None or leg.payment_plan_id is not None:
            return leg
    return event.entity_legs[0] if event.entity_legs else None


def _money_in_debt_id(event: models.FinancialEvent) -> int | None:
    for leg in event.entity_legs:
        if leg.debt_id is not None:
            return int(leg.debt_id)
    return None


def _classify_money_in_event(
    event: models.FinancialEvent,
    *,
    asset: models.Asset | None,
    debt: models.Debt | None,
) -> tuple[schemas.MoneyInKind, bool, str | None]:
    if event.event_type == models.TransactionType.REFUND:
        return schemas.MoneyInKind.RETURNED, False, "expense_refund"

    if event.event_type == models.TransactionType.ADJUSTMENT:
        return schemas.MoneyInKind.ADJUSTMENT, False, "wallet_adjustment"

    if event.event_type == models.TransactionType.NEUTRAL_FLOW:
        return schemas.MoneyInKind.RETURNED, False, "neutral_flow"

    if event.event_type == models.TransactionType.DEBT_SETTLEMENT:
        if event.reference_type == models.ReferenceType.LOAN_DISBURSEMENT:
            return schemas.MoneyInKind.BORROWED, False, "debt"
        if debt is not None and debt.debt_type == models.DebtType.OWING and _money_in_amount(event) > 0:
            return schemas.MoneyInKind.BORROWED, False, "debt"
        if event.reference_type in (models.ReferenceType.DEBT_INCOME, models.ReferenceType.DEBT_CHARGE):
            return schemas.MoneyInKind.INCOME, True, "debt"
        return schemas.MoneyInKind.RETURNED, False, "debt"

    if asset is not None or event.reference_type == models.ReferenceType.ASSET_SALE:
        return schemas.MoneyInKind.SOLD, False, "asset"

    return schemas.MoneyInKind.INCOME, True, "income"


def _build_money_in_item(
    event: models.FinancialEvent,
    *,
    asset: models.Asset | None,
    debt: models.Debt | None,
) -> schemas.MoneyInItemOut | None:
    amount = _money_in_amount(event)
    if amount <= 0:
        return None

    entity = _money_in_primary_entity(event)
    kind, counts_as_income, domain = _classify_money_in_event(event, asset=asset, debt=debt)
    source_id = int(entity.income_source_id) if entity and entity.income_source_id else None
    source_name = None
    if entity and entity.income_source is not None:
        source_name = entity.income_source.name
    elif debt is not None:
        source_name = debt.counterparty_name
    elif asset is not None:
        source_name = asset.title

    return schemas.MoneyInItemOut(
        id=int(event.id),
        title=event.title,
        description=event.description,
        amount=amount,
        currency="UZS",
        date=event.date,
        created_at=event.created_at,
        kind=kind,
        counts_as_income=counts_as_income,
        event_type=event.event_type,
        reference_type=event.reference_type,
        source_id=source_id,
        source_name=source_name,
        debt_id=int(debt.id) if debt is not None else None,
        asset_id=int(asset.id) if asset is not None else None,
        linked_event_id=int(event.linked_event_id) if event.linked_event_id is not None else None,
        wallet_allocations=_money_in_wallets_out(event),
        read_only=True,
        original_domain=domain,
    )


def _money_in_matches_search(item: schemas.MoneyInItemOut, search: str | None) -> bool:
    needle = (search or "").strip().casefold()
    if not needle:
        return True

    haystack = [
        item.title,
        item.description,
        item.source_name,
        item.kind.value,
        item.event_type.value if item.event_type else None,
        str(item.reference_type) if item.reference_type else None,
        item.original_domain.replace("_", " ") if item.original_domain else None,
        f"debt {item.debt_id}" if item.debt_id else None,
        f"asset {item.asset_id}" if item.asset_id else None,
    ]
    haystack.extend(wallet.wallet_name for wallet in item.wallet_allocations)
    return any(needle in str(value).casefold() for value in haystack if value)


@money_in_router.get("", response_model=schemas.PaginatedMoneyInOut)
def list_money_in(
    limit: int = Query(default=20, ge=1, le=100),
    skip: int = Query(default=0, ge=0),
    kind: schemas.MoneyInKind = Query(default=schemas.MoneyInKind.ALL),
    search: str | None = Query(default=None, max_length=100),
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
):
    if (start_date is None) ^ (end_date is None):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="money_in.date_range_both_required")
    if start_date and end_date and start_date > end_date:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="money_in.start_after_end")

    query = _money_in_event_query(db, current_user.id)
    if start_date is not None:
        query = query.filter(models.FinancialEvent.date >= start_date)
    if end_date is not None:
        query = query.filter(models.FinancialEvent.date <= end_date)

    events = query.order_by(models.FinancialEvent.date.desc(), models.FinancialEvent.id.desc()).all()

    sale_event_ids = {int(event.id) for event in events if event.event_type == models.TransactionType.INCOME}
    assets_by_sale_event_id: dict[int, models.Asset] = {}
    if sale_event_ids:
        assets_by_sale_event_id = {
            int(asset.sale_event_id): asset
            for asset in db.query(models.Asset)
            .filter(
                models.Asset.owner_id == current_user.id,
                models.Asset.sale_event_id.in_(sale_event_ids),
            )
            .all()
            if asset.sale_event_id is not None
        }

    debt_ids = {
        debt_id
        for event in events
        for debt_id in [_money_in_debt_id(event)]
        if debt_id is not None
    }
    debts_by_id: dict[int, models.Debt] = {}
    if debt_ids:
        debts_by_id = {
            int(debt.id): debt
            for debt in db.query(models.Debt)
            .filter(
                models.Debt.owner_id == current_user.id,
                models.Debt.id.in_(debt_ids),
            )
            .all()
        }

    items: list[schemas.MoneyInItemOut] = []
    for event in events:
        item = _build_money_in_item(
            event,
            asset=assets_by_sale_event_id.get(int(event.id)),
            debt=debts_by_id.get(_money_in_debt_id(event)),
        )
        if item is None:
            continue
        if kind != schemas.MoneyInKind.ALL and item.kind != kind:
            continue
        if not _money_in_matches_search(item, search):
            continue
        items.append(item)

    items.sort(key=lambda item: (item.date, item.created_at, item.id), reverse=True)
    total = len(items)
    return schemas.PaginatedMoneyInOut(total=total, items=items[skip:skip + limit])


@router.get("/sources", response_model=List[schemas.IncomeSourceOut])
def list_income_sources(
    include_inactive: bool = Query(default=False),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
):
    query = db.query(models.IncomeSource).filter(models.IncomeSource.owner_id == current_user.id)
    if not include_inactive:
        query = query.filter(models.IncomeSource.is_active.is_(True))
    return query.order_by(models.IncomeSource.created_at.desc(), models.IncomeSource.id.desc()).all()


@router.post("/sources", response_model=schemas.IncomeSourceOut, status_code=status.HTTP_201_CREATED)
def create_income_source(
    payload: schemas.IncomeSourceCreate,
    response: Response,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
):
    rate_headers = enforce_income_source_write_rate_limit(current_user.id)
    for k, v in rate_headers.items():
        response.headers[k] = v

    source_count = (
        db.query(func.count(models.IncomeSource.id))
        .filter(models.IncomeSource.owner_id == current_user.id)
        .scalar()
        or 0
    )
    if int(source_count) >= INCOME_SOURCE_LIMIT:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="income.source_limit_reached")

    existing = (
        db.query(models.IncomeSource)
        .filter(
            models.IncomeSource.owner_id == current_user.id,
            func.lower(models.IncomeSource.name) == payload.name.lower(),
        )
        .first()
    )
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="income.source_exists")

    source = models.IncomeSource(owner_id=current_user.id, name=payload.name, is_active=True)
    db.add(source)
    db.commit()
    db.refresh(source)
    return source


@router.patch("/sources/{source_id}", response_model=schemas.IncomeSourceOut)
def update_income_source(
    source_id: int,
    payload: schemas.IncomeSourceUpdate,
    response: Response,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
):
    rate_headers = enforce_income_source_write_rate_limit(current_user.id)
    for k, v in rate_headers.items():
        response.headers[k] = v
    source = _get_owned_source_or_404(db, current_user.id, source_id)

    duplicate = (
        db.query(models.IncomeSource)
        .filter(
            models.IncomeSource.owner_id == current_user.id,
            models.IncomeSource.id != source.id,
            func.lower(models.IncomeSource.name) == payload.name.lower(),
        )
        .first()
    )
    if duplicate:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="income.source_exists")

    source.name = payload.name
    source.is_active = True
    db.commit()
    db.refresh(source)
    return source


@router.delete("/sources/{source_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_income_source(
    source_id: int,
    response: Response,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
):
    rate_headers = enforce_income_source_write_rate_limit(current_user.id)
    for k, v in rate_headers.items():
        response.headers[k] = v
    source = _get_owned_source_or_404(db, current_user.id, source_id)
    db.delete(source)
    db.commit()
    response.status_code = status.HTTP_204_NO_CONTENT
    return None


@router.patch("/sources/{source_id}/active", response_model=schemas.IncomeSourceOut)
def update_income_source_active_state(
    source_id: int,
    payload: schemas.IncomeSourceStatusUpdate,
    response: Response,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
):
    rate_headers = enforce_income_source_write_rate_limit(current_user.id)
    for k, v in rate_headers.items():
        response.headers[k] = v
    source = _get_owned_source_or_404(db, current_user.id, source_id)
    source.is_active = payload.is_active
    db.commit()
    db.refresh(source)
    return source


@router.get("/entries", response_model=schemas.PaginatedIncomeEntriesOut)
def list_income_entries(
    limit: int = Query(default=20, ge=1, le=100),
    skip: int = Query(default=0, ge=0),
    source_id: int | None = Query(default=None),
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
):
    if (start_date is None) ^ (end_date is None):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="income.date_range_both_required")
    if start_date and end_date and start_date > end_date:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="income.start_after_end")

    events = _income_event_query(db, current_user.id).all()
    items: list[schemas.IncomeEntryOut] = []

    if source_id is not None:
        _get_owned_source_or_404(db, current_user.id, source_id)

    for event in events:
        entry = _build_income_entry_out(event)
        if source_id is not None and entry.source_id != source_id:
            continue
        if start_date is not None and entry.date < start_date:
            continue
        if end_date is not None and entry.date > end_date:
            continue
        items.append(entry)

    items.sort(key=lambda item: (item.date, item.created_at), reverse=True)
    total = len(items)
    return {"total": total, "items": items[skip:skip + limit]}


@router.post("/entries", response_model=schemas.IncomeEntryOut, status_code=status.HTTP_201_CREATED)
def create_income_entry(
    payload: schemas.IncomeEntryCreate,
    response: Response,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
    user_tz: tzinfo = Depends(get_effective_user_timezone),
):
    today = today_in_tz(user_tz)
    current_month_start = today.replace(day=1)
    rate_headers = enforce_income_entry_write_rate_limit(current_user.id)
    for k, v in rate_headers.items():
        response.headers[k] = v

    _validate_entry_date_in_current_month(payload.date, today)
    _ensure_source_belongs_to_user(db, current_user.id, payload.source_id)

    month_entry_count = (
        db.query(func.count(models.FinancialEvent.id))
        .filter(
            models.FinancialEvent.owner_id == current_user.id,
            models.FinancialEvent.event_type == models.TransactionType.INCOME,
            models.FinancialEvent.date >= current_month_start,
            models.FinancialEvent.date <= today,
        )
        .scalar()
        or 0
    )
    if int(month_entry_count) >= INCOME_ENTRY_MONTH_LIMIT:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="income.entry_month_limit_reached")

    wallet_allocations = _resolve_income_wallet_allocations(
        db=db,
        user_id=current_user.id,
        amount=int(payload.amount),
        wallet_id=payload.wallet_id,
        wallet_allocations=payload.wallet_allocations,
    )

    # Enforce per-wallet epoch boundaries
    touched_wallet_ids = {wallet.id for wallet, _ in wallet_allocations}
    validate_wallet_epochs(
        db,
        wallet_ids=touched_wallet_ids,
        event_date=payload.date,
    )

    entry = _record_income_event(
        db,
        owner_id=current_user.id,
        amount=int(payload.amount),
        source_id=payload.source_id,
        note=payload.note,
        income_date=payload.date,
        wallet_allocations=wallet_allocations,
    )

    db.commit()
    created = _get_owned_entry_or_404(db, current_user.id, entry.id)
    return _build_income_entry_out(created)


@router.put("/entries/{entry_id}", response_model=schemas.IncomeEntryOut)
def update_income_entry(
    entry_id: int,
    payload: schemas.IncomeEntryUpdate,
    response: Response,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
    user_tz: tzinfo = Depends(get_effective_user_timezone),
):
    rate_headers = enforce_income_entry_write_rate_limit(current_user.id)
    for k, v in rate_headers.items():
        response.headers[k] = v
    _validate_entry_date_in_current_month(payload.date, today_in_tz(user_tz))
    _ensure_source_belongs_to_user(db, current_user.id, payload.source_id)
    entry = _get_owned_entry_or_404(db, current_user.id, entry_id)

    entity_leg = _primary_income_entity_leg(entry)
    old_source = entity_leg.income_source_id if entity_leg else None

    # Determine which fields changed
    amount_changed = int(payload.amount) != _income_amount(entry)
    date_changed = payload.date != entry.date
    source_changed = payload.source_id != old_source
    wallet_changed = _income_wallet_allocation_changed(entry, payload)
    note_only = not (amount_changed or date_changed or source_changed or wallet_changed)

    if note_only:
        # Metadata-only edit — update in place, no reversal needed
        entry.description = payload.note
        db.commit()
        updated = _get_owned_entry_or_404(db, current_user.id, entry.id)
        return _build_income_entry_out(updated)

    # ── Financial edit → correction repost ──────────────────────────────
    # Void the original (preserves it, appends a reversal), then post a
    # new corrected event linked to the original.  Wallet effects net to
    # the corrected values — no double-counting.

    debt_ids_to_reconcile = {int(leg.debt_id) for leg in entry.entity_legs if leg.debt_id}

    void_financial_event(
        db,
        event=entry,
        owner_id=current_user.id,
        user_tz=user_tz,
        void_reason="Corrected by user",
    )

    wallet_allocations = _resolve_income_wallet_allocations(
        db=db,
        user_id=current_user.id,
        amount=int(payload.amount),
        wallet_id=payload.wallet_id,
        wallet_allocations=payload.wallet_allocations,
    )

    # Validate wallet epochs for the corrected date
    touched_wallet_ids = {wallet.id for wallet, _ in wallet_allocations}
    validate_wallet_epochs(db, wallet_ids=touched_wallet_ids, event_date=payload.date)

    corrected = _record_income_event(
        db,
        owner_id=current_user.id,
        amount=int(payload.amount),
        source_id=payload.source_id,
        note=payload.note,
        income_date=payload.date,
        wallet_allocations=wallet_allocations,
        linked_event_id=entry.id,
    )

    for debt_id in debt_ids_to_reconcile:
        reconcile_debt(db, debt_id)

    db.commit()
    created = _get_owned_entry_or_404(db, current_user.id, corrected.id)
    return _build_income_entry_out(created)


@router.delete("/entries/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_income_entry(
    entry_id: int,
    response: Response,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
    user_tz: tzinfo = Depends(get_effective_user_timezone),
):
    rate_headers = enforce_income_entry_write_rate_limit(current_user.id)
    for k, v in rate_headers.items():
        response.headers[k] = v

    # Look up the event regardless of status so we can distinguish
    # "not found" from "already voided".
    entry = _get_owned_entry_any_status_or_404(db, current_user.id, entry_id)

    if entry.status != models.FinancialEventStatus.POSTED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="income.entry_not_posted",
        )

    # Reject if any touched wallet is archived.
    for wallet_leg in entry.wallet_legs:
        if wallet_leg.wallet and not wallet_leg.wallet.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="wallets.archived_locked",
            )

    # Collect linked debts before voiding — they need reconciliation after.
    debt_ids_to_reconcile = {int(leg.debt_id) for leg in entry.entity_legs if leg.debt_id}

    # Use the shared void/reversal seam (Ticket 1) instead of hard-deleting.
    # This preserves the original financial fact, appends a counter-balancing
    # reversal, and marks the original event as VOIDED.
    void_financial_event(
        db,
        event=entry,
        owner_id=current_user.id,
        user_tz=user_tz,
        void_reason="Deleted by user",
    )

    for debt_id in debt_ids_to_reconcile:
        reconcile_debt(db, debt_id)

    db.commit()
    response.status_code = status.HTTP_204_NO_CONTENT
    return None
