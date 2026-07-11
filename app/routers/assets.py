from datetime import date, tzinfo
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.timezone import get_effective_user_timezone, today_in_tz

from .. import models, oauth2, schemas
from ..services.wallet_service import WalletService
from ..session import get_db
from .wallets import _get_owned_wallet_or_404

router = APIRouter(
    prefix="/assets",
    tags=["Assets"],
)


def _get_owned_asset_or_404(db: Session, user_id: int, asset_id: int) -> models.Asset:
    asset = (
        db.query(models.Asset)
        .filter(models.Asset.id == asset_id, models.Asset.owner_id == user_id)
        .first()
    )
    if not asset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="assets.not_found")
    return asset


def _get_owned_origin_event_or_404(
    db: Session,
    user_id: int,
    origin_event_id: int,
) -> models.FinancialEvent:
    event = (
        db.query(models.FinancialEvent)
        .filter(
            models.FinancialEvent.id == origin_event_id,
            models.FinancialEvent.owner_id == user_id,
            models.FinancialEvent.event_type == models.TransactionType.EXPENSE,
            models.FinancialEvent.status == models.FinancialEventStatus.POSTED,
        )
        .first()
    )
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="assets.origin_event_not_found")
    return event


def _origin_event_has_refund(db: Session, user_id: int, origin_event_id: int) -> bool:
    return (
        db.query(models.FinancialEvent.id)
        .filter(
            models.FinancialEvent.owner_id == user_id,
            models.FinancialEvent.status == models.FinancialEventStatus.POSTED,
            models.FinancialEvent.event_type == models.TransactionType.REFUND,
            models.FinancialEvent.linked_event_id == origin_event_id,
        )
        .first()
        is not None
    )


def _origin_event_has_split_allocations(event: models.FinancialEvent) -> bool:
    return len([leg for leg in event.entity_legs if leg.category is not None]) > 1


def _origin_event_has_linked_dependency(
    db: Session,
    user_id: int,
    event: models.FinancialEvent,
) -> bool:
    has_debt = (
        db.query(models.Debt.id)
        .filter(
            models.Debt.owner_id == user_id,
            models.Debt.linked_event_id == event.id,
        )
        .first()
    )
    if has_debt:
        return True
    return any(
        leg.debt_id or leg.payment_plan_id or leg.payment_plan_payment_id
        for leg in event.entity_legs
    )


def _assert_origin_event_asset_eligible(
    db: Session,
    user_id: int,
    event: models.FinancialEvent,
) -> None:
    if event.is_session:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="expenses.complex_event_not_supported")
    if _origin_event_has_split_allocations(event):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="expenses.split_parent_locked")
    if _origin_event_has_refund(db, user_id, event.id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="expenses.has_refund_lock")
    if _origin_event_has_linked_dependency(db, user_id, event):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="expenses.linked_dependency_lock")


def _assert_asset_sellable(asset: models.Asset) -> None:
    if asset.status in {"sold", "disposed", "gifted", "lost"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="assets.already_closed")


def _close_asset_without_money(
    asset: models.Asset,
    *,
    closed_date: date,
    final_status: str,
) -> None:
    asset.status = final_status
    asset.sold_date = closed_date
    asset.sale_value = None
    asset.sale_event_id = None


def _record_multi_wallet_sale_event(
    db: Session,
    owner_id: int,
    asset: models.Asset,
    *,
    sale_value: int,
    sold_date: date,
    note: str | None,
    wallet_allocations: list[schemas.AssetWalletAllocationCreate],
) -> int:
    if not wallet_allocations:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="assets.wallet_allocations_required")

    allocation_total = int(sum(int(item.amount) for item in wallet_allocations))
    if allocation_total != int(sale_value):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="assets.sale_wallet_total_mismatch")

    seen_wallet_ids: set[int] = set()
    validated_wallets: list[tuple[models.Wallet, int]] = []
    for allocation in wallet_allocations:
        if allocation.wallet_id in seen_wallet_ids:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="assets.sale_wallet_duplicate")
        seen_wallet_ids.add(allocation.wallet_id)
        wallet = _get_owned_wallet_or_404(db, owner_id, allocation.wallet_id)
        if not wallet.is_active:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="wallets.archived_locked")
        validated_wallets.append((wallet, int(allocation.amount)))

    # Ticket 4: Store the asset title without "Asset Sale:" prefix.
    # The sale type is communicated through reference_type, not the title.
    event = models.FinancialEvent(
        owner_id=owner_id,
        title=asset.title[:100],
        description=note or asset.description,
        event_type=models.TransactionType.INCOME,
        reference_type=models.ReferenceType.ASSET_SALE,
        linked_event_id=asset.origin_event_id,
        date=sold_date,
    )
    db.add(event)
    db.flush()

    for wallet, amount in validated_wallets:
        WalletService.adjust_balance(db, wallet.id, amount, models.TransactionType.INCOME)
        db.add(
            models.WalletLedger(
                owner_id=owner_id,
                event_id=event.id,
                wallet_id=wallet.id,
                amount=amount,
            )
        )

    db.add(
        models.EntityLedger(
            event_id=event.id,
            amount=int(sale_value),
        )
    )
    db.flush()
    return int(event.id)


@router.post("", response_model=schemas.AssetOut, status_code=status.HTTP_201_CREATED)
def create_asset(
    payload: schemas.AssetCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
):
    if payload.origin_event_id is not None:
        origin_event = _get_owned_origin_event_or_404(db, current_user.id, payload.origin_event_id)
        _assert_origin_event_asset_eligible(db, current_user.id, origin_event)
        existing = (
            db.query(models.Asset)
            .filter(
                models.Asset.owner_id == current_user.id,
                models.Asset.origin_event_id == payload.origin_event_id,
            )
            .first()
        )
        if existing:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="assets.already_exists_for_expense")

    asset = models.Asset(
        owner_id=current_user.id,
        title=payload.title,
        description=payload.description,
        origin_event_id=payload.origin_event_id,
        purchase_value=payload.purchase_value,
        current_value=payload.current_value,
        status=payload.status,
    )
    db.add(asset)
    db.commit()
    db.refresh(asset)
    return schemas.AssetOut.model_validate(asset)


@router.get("", response_model=schemas.PaginatedAssetsOut)
def list_assets(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
    limit: int = 20,
    skip: int = 0,
    search: Optional[str] = None,
    status_filter: Optional[str] = None,
):
    query = db.query(models.Asset).filter(models.Asset.owner_id == current_user.id)

    if search:
        needle = f"%{search.strip()}%"
        query = query.filter(
            (models.Asset.title.ilike(needle)) | (models.Asset.description.ilike(needle))
        )

    if status_filter:
        normalized = status_filter.strip().lower()
        if normalized not in schemas.ASSET_ALLOWED_STATUSES:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="assets.status_invalid")
        query = query.filter(models.Asset.status == normalized)

    total = int(query.with_entities(func.count(models.Asset.id)).scalar() or 0)
    items = (
        query.order_by(models.Asset.updated_at.desc(), models.Asset.id.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return schemas.PaginatedAssetsOut(
        total=total,
        items=[schemas.AssetOut.model_validate(item) for item in items],
    )


@router.get("/{asset_id}", response_model=schemas.AssetOut)
def get_asset(
    asset_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
):
    asset = _get_owned_asset_or_404(db, current_user.id, asset_id)
    return schemas.AssetOut.model_validate(asset)


@router.put("/{asset_id}", response_model=schemas.AssetOut)
def update_asset(
    asset_id: int,
    payload: schemas.AssetUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
):
    asset = _get_owned_asset_or_404(db, current_user.id, asset_id)
    update_data = payload.model_dump(exclude_unset=True)

    next_status = update_data.get("status", asset.status)
    if asset.sale_event_id is not None and next_status == "owned":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="assets.cannot_reopen_sold_asset")
    if asset.sold_date is not None and next_status == "owned":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="assets.cannot_reopen_sold_asset")

    for field, value in update_data.items():
        setattr(asset, field, value)

    db.commit()
    db.refresh(asset)
    return schemas.AssetOut.model_validate(asset)


@router.post("/{asset_id}/sell", response_model=schemas.AssetOut)
def sell_asset(
    asset_id: int,
    payload: schemas.AssetSellRequest,
    response: Response,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
    user_tz: tzinfo = Depends(get_effective_user_timezone),
):
    asset = _get_owned_asset_or_404(db, current_user.id, asset_id)
    _assert_asset_sellable(asset)

    sold_date = payload.sold_date or today_in_tz(user_tz)
    if sold_date > today_in_tz(user_tz):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="assets.sold_date_in_future")

    sale_event_id = None
    wallet_allocations = payload.wallet_allocations or []
    if payload.destination_wallet_id is not None:
        if wallet_allocations:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="assets.sale_wallet_mode_conflict")
        wallet_allocations = [
            schemas.AssetWalletAllocationCreate(
                wallet_id=payload.destination_wallet_id,
                amount=int(payload.sale_value),
            )
        ]
    if wallet_allocations:
        sale_event_id = _record_multi_wallet_sale_event(
            db,
            current_user.id,
            asset,
            sale_value=int(payload.sale_value),
            sold_date=sold_date,
            note=payload.note,
            wallet_allocations=wallet_allocations,
        )

    asset.status = payload.status
    asset.sold_date = sold_date
    asset.sale_value = int(payload.sale_value)
    asset.sale_event_id = sale_event_id
    asset.current_value = int(payload.sale_value)

    db.commit()
    db.refresh(asset)
    response.status_code = status.HTTP_200_OK
    return schemas.AssetOut.model_validate(asset)


@router.post("/{asset_id}/gift", response_model=schemas.AssetOut)
def gift_asset(
    asset_id: int,
    payload: schemas.AssetCloseRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
    user_tz: tzinfo = Depends(get_effective_user_timezone),
):
    asset = _get_owned_asset_or_404(db, current_user.id, asset_id)
    _assert_asset_sellable(asset)
    closed_date = payload.closed_date or today_in_tz(user_tz)
    if closed_date > today_in_tz(user_tz):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="assets.closed_date_in_future")
    _close_asset_without_money(asset, closed_date=closed_date, final_status="gifted")
    db.commit()
    db.refresh(asset)
    return schemas.AssetOut.model_validate(asset)


@router.post("/{asset_id}/dispose", response_model=schemas.AssetOut)
def dispose_asset(
    asset_id: int,
    payload: schemas.AssetCloseRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
    user_tz: tzinfo = Depends(get_effective_user_timezone),
):
    asset = _get_owned_asset_or_404(db, current_user.id, asset_id)
    _assert_asset_sellable(asset)
    closed_date = payload.closed_date or today_in_tz(user_tz)
    if closed_date > today_in_tz(user_tz):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="assets.closed_date_in_future")
    _close_asset_without_money(asset, closed_date=closed_date, final_status="disposed")
    db.commit()
    db.refresh(asset)
    return schemas.AssetOut.model_validate(asset)


@router.post("/{asset_id}/lost", response_model=schemas.AssetOut)
def mark_asset_lost(
    asset_id: int,
    payload: schemas.AssetCloseRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
    user_tz: tzinfo = Depends(get_effective_user_timezone),
):
    asset = _get_owned_asset_or_404(db, current_user.id, asset_id)
    _assert_asset_sellable(asset)
    closed_date = payload.closed_date or today_in_tz(user_tz)
    if closed_date > today_in_tz(user_tz):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="assets.closed_date_in_future")
    _close_asset_without_money(asset, closed_date=closed_date, final_status="lost")
    db.commit()
    db.refresh(asset)
    return schemas.AssetOut.model_validate(asset)
