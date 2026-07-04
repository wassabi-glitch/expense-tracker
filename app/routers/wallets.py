from typing import List, Literal
from fastapi import APIRouter, Depends, HTTPException, Query, status, Response
from sqlalchemy.orm import Session
from sqlalchemy import func

from .. import models, oauth2, schemas
from ..session import get_db
from ..services.goal_funding_service import (
    get_wallet_goal_allocated_amount,
    get_wallet_required_goal_resolution_for_outflow,
    move_wallet_goal_allocations,
    release_wallet_goal_allocations,
    validate_wallet_goal_protection_for_outflow,
)
from ..services.isolated_project_service import get_wallet_project_allocated_amount
from ..services.wallet_fee_service import (
    get_owned_fee_wallet_or_404,
    record_linked_bank_fee_event,
    resolve_or_create_bank_fee_budget,
    validate_linked_fee_goal_protection,
)
from ..services.wallet_service import WalletService
from ..services.wallet_value_service import owned_balance
from ..timezone import get_effective_user_timezone, today_in_tz
from datetime import tzinfo

router = APIRouter(
    prefix="/wallets",
    tags=["Wallets"],
)

def _get_owned_wallet_or_404(db: Session, user_id: int, wallet_id: int) -> models.Wallet:
    wallet = (
        db.query(models.Wallet)
        .filter(models.Wallet.id == wallet_id, models.Wallet.owner_id == user_id)
        .first()
    )
    if not wallet:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="wallets.not_found")
    return wallet


def _build_wallet_out(db: Session, user_id: int, wallet: models.Wallet) -> schemas.WalletOut:
    payload = schemas.WalletOut.model_validate(wallet)
    wallet_owned_balance = owned_balance(wallet)
    protected_for_goals = min(
        get_wallet_goal_allocated_amount(db, user_id, int(wallet.id)),
        wallet_owned_balance,
    )
    protected_for_projects = min(
        get_wallet_project_allocated_amount(db, user_id, int(wallet.id)),
        max(wallet_owned_balance - protected_for_goals, 0),
    )
    payload.owned_balance = int(wallet_owned_balance)
    payload.protected_for_goals = int(protected_for_goals)
    payload.protected_for_projects = int(protected_for_projects)
    payload.free_to_allocate = max(
        int(wallet_owned_balance) - int(protected_for_goals) - int(protected_for_projects),
        0,
    )
    return payload


def _resolve_can_fund_goals(payload_value: bool | None, wallet_type: models.WalletType, accounting_type: models.AccountingType) -> bool:
    if accounting_type != models.AccountingType.ASSET and wallet_type != models.WalletType.CREDIT:
        return False
    if payload_value is not None:
        return bool(payload_value)
    return wallet_type == models.WalletType.SAVINGS

def _resolve_or_create_budget(db: Session, user_id: int, category: models.ExpenseCategory, tz: tzinfo | None = None) -> tuple[models.Budget, bool]:
    today = today_in_tz(tz)
    budget = (
        db.query(models.Budget)
        .filter(
            models.Budget.owner_id == user_id,
            models.Budget.category == category,
            models.Budget.budget_year == today.year,
            models.Budget.budget_month == today.month
        )
        .first()
    )
    
    if budget:
        return budget, False
        
    # Auto-create budget for 50,000 UZS
    new_budget = models.Budget(
        owner_id=user_id,
        category=category,
        budget_year=today.year,
        budget_month=today.month,
        monthly_limit=50000,
        auto_created=True
    )
    db.add(new_budget)
    db.flush()
    return new_budget, True


def _build_transfer_out(
    event: models.FinancialEvent,
    payload: schemas.WalletTransferCreate,
    fee_event: models.FinancialEvent | None = None,
) -> schemas.WalletTransferOut:
    return schemas.WalletTransferOut(
        id=event.id,
        from_wallet_id=payload.from_wallet_id,
        to_wallet_id=payload.to_wallet_id,
        amount=payload.amount,
        note=payload.note,
        date=event.date,
        created_at=event.created_at,
        fee_event_id=fee_event.id if fee_event else None,
    )

@router.get("", response_model=List[schemas.WalletOut])
def list_wallets(
    include_archived: bool = True,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
):
    query = db.query(models.Wallet).filter(models.Wallet.owner_id == current_user.id)
    
    if not include_archived:
        # If someone explicitly wants ONLY active wallets
        query = query.filter(models.Wallet.is_active)
        
    wallets = query.order_by(models.Wallet.created_at.asc()).all()
    return [_build_wallet_out(db, current_user.id, wallet) for wallet in wallets]

@router.post("", response_model=schemas.WalletOut, status_code=status.HTTP_201_CREATED)
def create_wallet(
    payload: schemas.WalletCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
):
    wallet_count = db.query(func.count(models.Wallet.id)).filter(models.Wallet.owner_id == current_user.id).scalar()
    if wallet_count >= 200:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="wallets.limit_reached")

    new_wallet = models.Wallet(
        owner_id=current_user.id,
        name=payload.name,
        wallet_type=payload.wallet_type,
        accounting_type=payload.accounting_type,
        initial_balance=payload.initial_balance,
        current_balance=payload.initial_balance,
        has_overdraft=payload.has_overdraft,
        overdraft_limit=payload.overdraft_limit,
        credit_limit=payload.credit_limit,
        allow_overlimit=payload.allow_overlimit,
        color=payload.color,
        currency=payload.currency,
        can_fund_goals=_resolve_can_fund_goals(
            payload.can_fund_goals,
            payload.wallet_type,
            payload.accounting_type,
        ),
        is_default=(wallet_count == 0)
    )
    db.add(new_wallet)
    db.commit()
    db.refresh(new_wallet)
    return new_wallet

@router.patch("/{wallet_id}", response_model=schemas.WalletOut)
def update_wallet(
    wallet_id: int,
    payload: schemas.WalletUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
):
    wallet = _get_owned_wallet_or_404(db, current_user.id, wallet_id)
    
    # Generic update logic
    update_data = payload.model_dump(exclude_unset=True)
    
    if not wallet.is_active:
        is_restore_only = update_data.get("is_active") is True and set(update_data.keys()) == {"is_active"}
        if not is_restore_only:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="wallets.archived_immutable",
            )
    requested_can_fund_goals = update_data.pop("can_fund_goals", None)

    for key, value in update_data.items():
        if key == "is_default" and value is True:
            db.query(models.Wallet).filter(
                models.Wallet.owner_id == current_user.id, 
                models.Wallet.is_default
            ).update({"is_default": False})

        setattr(wallet, key, value)

    if requested_can_fund_goals is not None:
        wallet.can_fund_goals = _resolve_can_fund_goals(
            requested_can_fund_goals,
            wallet.wallet_type,
            wallet.accounting_type,
        )

    db.commit()
    db.refresh(wallet)
    return wallet

@router.post("/{wallet_id}/set-default", response_model=schemas.WalletOut)
def set_wallet_default(
    wallet_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
):
    wallet = _get_owned_wallet_or_404(db, current_user.id, wallet_id)
    
    db.query(models.Wallet).filter(
        models.Wallet.owner_id == current_user.id, 
        models.Wallet.is_default
    ).update({"is_default": False})
    
    wallet.is_default = True
    db.commit()
    db.refresh(wallet)
    return wallet


@router.get("/{wallet_id}/transactions", response_model=schemas.PaginatedWalletTransactionsOut)
def list_wallet_transactions(
    wallet_id: int,
    direction: Literal["all", "in", "out"] = Query("all"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
):
    wallet = _get_owned_wallet_or_404(db, current_user.id, wallet_id)
    query = (
        db.query(models.WalletLedger, models.FinancialEvent)
        .join(models.FinancialEvent, models.FinancialEvent.id == models.WalletLedger.event_id)
        .filter(
            models.WalletLedger.owner_id == current_user.id,
            models.WalletLedger.wallet_id == wallet.id,
            models.FinancialEvent.owner_id == current_user.id,
            models.FinancialEvent.status == models.FinancialEventStatus.POSTED,
        )
    )
    if direction == "in":
        query = query.filter(models.WalletLedger.amount > 0)
    elif direction == "out":
        query = query.filter(models.WalletLedger.amount < 0)

    total = query.count()
    rows = (
        query
        .order_by(
            models.FinancialEvent.date.desc(),
            models.FinancialEvent.created_at.desc(),
            models.WalletLedger.id.desc(),
        )
        .offset(offset)
        .limit(limit)
        .all()
    )
    return schemas.PaginatedWalletTransactionsOut(
        total=total,
        items=[
            schemas.WalletTransactionOut(
                id=ledger.id,
                amount=ledger.amount,
                title=event.title,
                event_type=event.event_type,
                date=event.date,
                created_at=event.created_at,
            )
            for ledger, event in rows
        ],
    )


@router.post("/{wallet_id}/fee", response_model=schemas.WalletOut)
def record_fee(
    wallet_id: int,
    payload: schemas.WalletQuickActionRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
    user_tz: tzinfo = Depends(get_effective_user_timezone),
):
    """
    Deducts a Bank Fee from the wallet and ensures a corresponding budget exists.
    """
    wallet = _get_owned_wallet_or_404(db, current_user.id, wallet_id)
    
    if wallet.wallet_type == models.WalletType.CASH:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="wallets.action_not_supported_for_cash"
        )
    
    category = models.ExpenseCategory.BANK_FEES_INTEREST
    budget, was_autocreated = _resolve_or_create_budget(db, current_user.id, category, user_tz)
    validate_wallet_goal_protection_for_outflow(
        db,
        current_user.id,
        wallet,
        payload.amount,
        outflow_type="bank_fee",
        error_code="wallets.goal_protection_conflict",
    )
    
    WalletService.record_transaction(
        db=db,
        owner_id=current_user.id,
        wallet_id=wallet.id,
        transaction_type=models.TransactionType.EXPENSE,
        amount_delta=-payload.amount,
        category=category,
        title="Bank Fee",
        description=payload.note or "Bank Fee",
        budget_id=budget.id,
        reference_type=models.ReferenceType.BANK_FEE
    )
    db.commit()
    db.refresh(wallet)
    
    # Return wallet with the warning if it was auto-created
    wallet_data = schemas.WalletOut.model_validate(wallet)
    if was_autocreated:
        wallet_data.warning = "wallets.budget_autocreated"
    return wallet_data

@router.post("/{wallet_id}/interest", response_model=schemas.WalletOut)
def record_interest(
    wallet_id: int,
    payload: schemas.WalletQuickActionRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
    user_tz: tzinfo = Depends(get_effective_user_timezone),
):
    """
    Deducts Bank Interest from the wallet and ensures a corresponding budget exists.
    """
    wallet = _get_owned_wallet_or_404(db, current_user.id, wallet_id)
    
    if wallet.wallet_type == models.WalletType.CASH:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="wallets.action_not_supported_for_cash"
        )
    
    category = models.ExpenseCategory.BANK_FEES_INTEREST
    budget, was_autocreated = _resolve_or_create_budget(db, current_user.id, category, user_tz)
    validate_wallet_goal_protection_for_outflow(
        db,
        current_user.id,
        wallet,
        payload.amount,
        outflow_type="bank_interest",
        error_code="wallets.goal_protection_conflict",
    )
    
    WalletService.record_transaction(
        db=db,
        owner_id=current_user.id,
        wallet_id=wallet.id,
        transaction_type=models.TransactionType.EXPENSE,
        amount_delta=-payload.amount,
        category=category,
        title="Bank Interest",
        description=payload.note or "Bank Interest",
        budget_id=budget.id,
        reference_type=models.ReferenceType.BANK_INTEREST
    )
    db.commit()
    db.refresh(wallet)
    
    # Return wallet with the warning if it was auto-created
    wallet_data = schemas.WalletOut.model_validate(wallet)
    if was_autocreated:
        wallet_data.warning = "wallets.budget_autocreated"
    return wallet_data

@router.post("/{wallet_id}/reconcile", response_model=schemas.WalletOut)
def reconcile_wallet_balance(
    wallet_id: int,
    payload: schemas.WalletReconciliationRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
):
    """
    Reconciles physical balance via an Adjustment transaction.
    """
    wallet = _get_owned_wallet_or_404(db, current_user.id, wallet_id)
    if payload.target_balance < int(wallet.current_balance or 0):
        validate_wallet_goal_protection_for_outflow(
            db,
            current_user.id,
            wallet,
            int(wallet.current_balance or 0) - int(payload.target_balance),
            outflow_type="wallet_reconciliation",
            error_code="wallets.goal_protection_conflict",
        )
    
    try:
        WalletService.reconcile_balance(
            db=db,
            owner_id=current_user.id,
            wallet_id=wallet.id,
            target_balance=payload.target_balance,
            note=payload.note
        )
        db.commit()
        db.refresh(wallet)
        return wallet
    except HTTPException as e:
        raise e
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.delete("/{wallet_id}", status_code=status.HTTP_204_NO_CONTENT)
def archive_wallet(
    wallet_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
):
    """Refactored Deletion: We move to Archive mode to preserve history."""
    wallet = _get_owned_wallet_or_404(db, current_user.id, wallet_id)

    active_goal_allocations = get_wallet_goal_allocated_amount(db, current_user.id, wallet.id)
    if active_goal_allocations > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "wallets.archive_has_goal_allocations",
                "wallet_id": int(wallet.id),
                "wallet_name": wallet.name,
                "protected_for_goals": int(active_goal_allocations),
            },
        )
    
    # Allow archiving only if the user has handled the balance!
    if wallet.current_balance != 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="wallets.archive_not_empty"
        )
    
    wallet.is_active = False
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)

def _execute_wallet_transfer(
    payload: schemas.WalletTransferCreate,
    db: Session,
    current_user: models.User,
    *,
    reference_type: str | None = None,
) -> schemas.WalletTransferOut:
    if payload.from_wallet_id == payload.to_wallet_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="wallets.transfer_to_same")

    from_wallet = _get_owned_wallet_or_404(db, current_user.id, payload.from_wallet_id)
    to_wallet = _get_owned_wallet_or_404(db, current_user.id, payload.to_wallet_id)
    fee_amount = int(payload.fee_amount or 0)
    fee_wallet = None
    if fee_amount > 0:
        fee_wallet = get_owned_fee_wallet_or_404(
            db,
            current_user.id,
            int(payload.fee_wallet_id or payload.from_wallet_id),
        )
    required_goal_resolution = get_wallet_required_goal_resolution_for_outflow(
        db,
        current_user.id,
        from_wallet,
        payload.amount,
    )

    try:
        if required_goal_resolution > 0 and payload.goal_resolution is None:
            validate_wallet_goal_protection_for_outflow(
                db,
                current_user.id,
                from_wallet,
                payload.amount,
                outflow_type="transfer",
                error_code="wallets.goal_protection_conflict",
            )

        if fee_amount > 0 and fee_wallet is not None:
            validate_linked_fee_goal_protection(
                db,
                current_user.id,
                fee_wallet,
                fee_amount,
                primary_outflow_amount=payload.amount if fee_wallet.id == from_wallet.id else 0,
                allowed_goal_resolution_amount=required_goal_resolution if fee_wallet.id == from_wallet.id else 0,
            )

        transfer = WalletService.transfer_funds(
            db=db, 
            owner_id=current_user.id,
            from_wallet_id=payload.from_wallet_id, 
            to_wallet_id=payload.to_wallet_id, 
            amount=payload.amount,
            description=payload.note,
            transaction_date=payload.date
        )
        transfer.reference_type = reference_type
        if required_goal_resolution > 0:
            if payload.goal_resolution == schemas.WalletTransferCreate.GoalResolution.MOVE_TO_DESTINATION:
                move_wallet_goal_allocations(
                    db,
                    current_user.id,
                    source_wallet=from_wallet,
                    target_wallet=to_wallet,
                    amount=required_goal_resolution,
                    linked_event_id=transfer.id,
                )
            elif payload.goal_resolution == schemas.WalletTransferCreate.GoalResolution.RELEASE:
                release_wallet_goal_allocations(
                    db,
                    current_user.id,
                    source_wallet=from_wallet,
                    amount=required_goal_resolution,
                    linked_event_id=transfer.id,
                )
            else:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="wallets.goal_resolution_required")
        fee_event = None
        if fee_amount > 0 and fee_wallet is not None:
            budget, _ = resolve_or_create_bank_fee_budget(db, current_user.id, payload.date)
            fee_event = record_linked_bank_fee_event(
                db,
                user_id=current_user.id,
                wallet=fee_wallet,
                amount=fee_amount,
                fee_date=payload.date,
                budget_id=budget.id,
                linked_event_id=transfer.id,
                note=payload.fee_note or payload.note or "Transfer fee",
            )
        db.commit()
        db.refresh(transfer)
        if fee_event is not None:
            db.refresh(fee_event)
        return _build_transfer_out(transfer, payload, fee_event)
        
    except HTTPException as e:
        db.rollback()
        raise e
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/transfer", response_model=schemas.WalletTransferOut)
def transfer_funds(
    payload: schemas.WalletTransferCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
):
    return _execute_wallet_transfer(payload, db, current_user)
