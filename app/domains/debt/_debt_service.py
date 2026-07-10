from fastapi import HTTPException, status
from datetime import date

from sqlalchemy import and_, func, or_
from sqlalchemy.orm import Session, aliased

from app import models


POSTED_DEBT_LEDGER_STATUS = "POSTED"


def reverse_wallet_effect(db: Session, event: models.FinancialEvent) -> None:
    from app.services.wallet_service import WalletService

    wallet_legs = list(event.wallet_legs or [])
    for leg in wallet_legs:
        if leg.wallet_id is None:
            continue
        wallet = db.query(models.Wallet).filter(models.Wallet.id == leg.wallet_id).first()
        if wallet and not wallet.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="debts.transaction.wallet_archived",
            )
        WalletService.adjust_balance(db, leg.wallet_id, -int(leg.amount))


def create_debt_ledger_entry(
    db: Session,
    *,
    owner_id: int,
    debt_id: int,
    entry_type: models.DebtLedgerEntryType,
    amount_delta: int,
    entry_date: date,
    principal_delta: int = 0,
    charge_delta: int = 0,
    financial_event_id: int | None = None,
    source_debt_transaction_id: int | None = None,
    source_debt_charge_id: int | None = None,
    reverses_entry_id: int | None = None,
    wallet_id: int | None = None,
    asset_id: int | None = None,
    balance_after: int | None = None,
    event_subtype: str | None = None,
    source: models.DebtLedgerEntrySource = models.DebtLedgerEntrySource.USER,
    is_reversible: bool = True,
    note: str | None = None,
    extra_data: dict | None = None,
) -> models.DebtLedgerEntry:
    amount = int(amount_delta)
    if amount == 0:
        raise ValueError("debt_ledger.amount_delta_zero")
    if balance_after is None:
        previous_balance = (
            db.query(func.coalesce(func.sum(models.DebtLedgerEntry.amount_delta), 0))
            .filter(
                models.DebtLedgerEntry.debt_id == debt_id,
                models.DebtLedgerEntry.status == POSTED_DEBT_LEDGER_STATUS,
            )
            .scalar()
        ) or 0
        balance_after = int(previous_balance) + amount
    entry = models.DebtLedgerEntry(
        owner_id=owner_id,
        debt_id=debt_id,
        financial_event_id=financial_event_id,
        source_debt_transaction_id=source_debt_transaction_id,
        source_debt_charge_id=source_debt_charge_id,
        reverses_entry_id=reverses_entry_id,
        wallet_id=wallet_id,
        asset_id=asset_id,
        entry_type=entry_type,
        amount_delta=amount,
        principal_delta=int(principal_delta),
        charge_delta=int(charge_delta),
        balance_after=int(balance_after),
        event_subtype=event_subtype,
        source=source,
        is_reversible=is_reversible,
        status=POSTED_DEBT_LEDGER_STATUS,
        entry_date=entry_date,
        note=note,
        extra_data=extra_data,
    )
    db.add(entry)
    db.flush()
    return entry


def get_debt_total_charges(db: Session, debt_id: int) -> int:
    return max(
        0,
        int(
            db.query(func.coalesce(func.sum(models.DebtLedgerEntry.charge_delta), 0))
            .filter(
                models.DebtLedgerEntry.debt_id == debt_id,
                models.DebtLedgerEntry.status == POSTED_DEBT_LEDGER_STATUS,
            )
            .scalar()
            or 0
        ),
    )


def get_debt_total_charges_by_debt_ids(db: Session, debt_ids: list[int]) -> dict[int, int]:
    if not debt_ids:
        return {}
    rows = (
        db.query(func.coalesce(func.sum(models.DebtLedgerEntry.charge_delta), 0))
        .filter(
            models.DebtLedgerEntry.debt_id.in_(debt_ids),
            models.DebtLedgerEntry.status == POSTED_DEBT_LEDGER_STATUS,
        )
        .with_entities(
            models.DebtLedgerEntry.debt_id,
            func.coalesce(func.sum(models.DebtLedgerEntry.charge_delta), 0),
        )
        .group_by(models.DebtLedgerEntry.debt_id)
        .all()
    )
    return {int(debt_id): max(0, int(total_amount or 0)) for debt_id, total_amount in rows}


def get_debt_total_paid(db: Session, debt_id: int) -> int:
    original_entry = aliased(models.DebtLedgerEntry)
    total = (
        db.query(func.coalesce(func.sum(-models.DebtLedgerEntry.amount_delta), 0))
        .outerjoin(original_entry, models.DebtLedgerEntry.reverses_entry_id == original_entry.id)
        .filter(
            models.DebtLedgerEntry.debt_id == debt_id,
            models.DebtLedgerEntry.status == POSTED_DEBT_LEDGER_STATUS,
            or_(
                models.DebtLedgerEntry.entry_type == models.DebtLedgerEntryType.PAYMENT,
                and_(
                    models.DebtLedgerEntry.entry_type == models.DebtLedgerEntryType.REVERSAL,
                    original_entry.entry_type == models.DebtLedgerEntryType.PAYMENT,
                    original_entry.debt_id == models.DebtLedgerEntry.debt_id,
                    original_entry.status == POSTED_DEBT_LEDGER_STATUS,
                ),
            ),
        )
        .scalar()
        or 0
    )
    return max(0, int(total))


def get_debt_total_paid_by_debt_ids(db: Session, debt_ids: list[int]) -> dict[int, int]:
    if not debt_ids:
        return {}
    original_entry = aliased(models.DebtLedgerEntry)
    rows = (
        db.query(
            models.DebtLedgerEntry.debt_id,
            func.coalesce(func.sum(-models.DebtLedgerEntry.amount_delta), 0),
        )
        .outerjoin(original_entry, models.DebtLedgerEntry.reverses_entry_id == original_entry.id)
        .filter(
            models.DebtLedgerEntry.debt_id.in_(debt_ids),
            models.DebtLedgerEntry.status == POSTED_DEBT_LEDGER_STATUS,
            or_(
                models.DebtLedgerEntry.entry_type == models.DebtLedgerEntryType.PAYMENT,
                and_(
                    models.DebtLedgerEntry.entry_type == models.DebtLedgerEntryType.REVERSAL,
                    original_entry.entry_type == models.DebtLedgerEntryType.PAYMENT,
                    original_entry.debt_id == models.DebtLedgerEntry.debt_id,
                    original_entry.status == POSTED_DEBT_LEDGER_STATUS,
                ),
            ),
        )
        .group_by(models.DebtLedgerEntry.debt_id)
        .all()
    )
    return {int(debt_id): max(0, int(total_amount or 0)) for debt_id, total_amount in rows}


def reverse_debt_transaction_ledger(
    db: Session,
    *,
    owner_id: int,
    debt_id: int,
    transaction_id: int,
    entry_date: date,
    note: str | None = None,
) -> list[models.DebtLedgerEntry]:
    original_entries = (
        db.query(models.DebtLedgerEntry)
        .filter(
            models.DebtLedgerEntry.owner_id == owner_id,
            models.DebtLedgerEntry.debt_id == debt_id,
            models.DebtLedgerEntry.source_debt_transaction_id == transaction_id,
            models.DebtLedgerEntry.status == POSTED_DEBT_LEDGER_STATUS,
        )
        .order_by(models.DebtLedgerEntry.id.asc())
        .all()
    )
    reversals: list[models.DebtLedgerEntry] = []
    for original in original_entries:
        reversals.append(
            create_debt_ledger_entry(
                db,
                owner_id=owner_id,
                debt_id=debt_id,
                entry_type=models.DebtLedgerEntryType.REVERSAL,
                amount_delta=-int(original.amount_delta),
                principal_delta=-int(original.principal_delta or 0),
                charge_delta=-int(original.charge_delta or 0),
                financial_event_id=original.financial_event_id,
                source_debt_transaction_id=transaction_id,
                reverses_entry_id=original.id,
                wallet_id=original.wallet_id,
                asset_id=original.asset_id,
                entry_date=entry_date,
                note=note or "Debt payment reversed",
            )
        )
    return reversals


def reconcile_debt(db: Session, debt_id: int) -> models.Debt:
    """Recompute ``remaining_amount`` from posted ledger entries.

    Lifecycle is derived at read time (ADR 0026) — this function no longer
    touches the (now-removed) ``status`` column.
    """
    debt = (
        db.query(models.Debt)
        .filter(models.Debt.id == debt_id)
        .with_for_update()
        .first()
    )
    if not debt:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="debts.not_found")

    ledger_total = (
        db.query(func.coalesce(func.sum(models.DebtLedgerEntry.amount_delta), 0))
        .filter(
            models.DebtLedgerEntry.debt_id == debt.id,
            models.DebtLedgerEntry.status == POSTED_DEBT_LEDGER_STATUS,
        )
        .scalar()
    ) or 0

    debt.remaining_amount = max(0, int(ledger_total))
    db.flush()
    return debt
