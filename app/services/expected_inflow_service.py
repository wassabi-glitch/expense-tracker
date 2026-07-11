from __future__ import annotations

from datetime import date, datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session, selectinload

from app import models, schemas
from app.services.debt_payment_service import create_debt_payment
from app.services.debt_service import create_debt_ledger_entry, reconcile_debt
from app.services.financial_event_ledger_service import (
    PostEntityLeg,
    PostWalletLeg,
    post_financial_event,
    void_financial_event,
)
from app.services.goal_funding_service import sync_debt_goal_targets
from app.services.wallet_service import WalletService
from app.utils import check_budget_alerts


ACTIVE_STATUSES = {
    models.ExpectedIncomeStatus.EXPECTED,
    models.ExpectedIncomeStatus.PARTIALLY_RECEIVED,
}
TERMINAL_STATUSES = {
    models.ExpectedIncomeStatus.RESOLVED,
    models.ExpectedIncomeStatus.SUPERSEDED,
    models.ExpectedIncomeStatus.WRITTEN_OFF,
    models.ExpectedIncomeStatus.CANCELLED,
    models.ExpectedIncomeStatus.RECEIVED,
    models.ExpectedIncomeStatus.MISSED,
}


def _kind(row: models.ExpectedIncome) -> models.ExpectedInflowKind:
    if row.kind:
        return models.ExpectedInflowKind(row.kind)
    return (
        models.ExpectedInflowKind.RECEIVABLE
        if row.debt_id is not None
        else models.ExpectedInflowKind.EARNED
    )


def _source_key(row: models.ExpectedIncome) -> tuple[str, int]:
    kind = _kind(row)
    source_ids = {
        models.ExpectedInflowKind.EARNED: row.source_id,
        models.ExpectedInflowKind.RECEIVABLE: row.debt_id,
        models.ExpectedInflowKind.REFUND: row.refund_event_id,
        models.ExpectedInflowKind.ASSET_SALE: row.asset_id,
    }
    source_id = source_ids[kind]
    if source_id is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="expected_inflow.source_missing")
    return kind.value, int(source_id)


def _valid_realization(realization: models.ExpectedInflowRealization) -> bool:
    if realization.reversed_at is not None:
        return False
    links = list(realization.event_links or [])
    return bool(links) and all(
        link.financial_event is not None
        and link.financial_event.status == models.FinancialEventStatus.POSTED
        for link in links
    )


def received_amount(row: models.ExpectedIncome) -> int:
    allocations = list(row.realization_allocations or [])
    if not allocations:
        return int(row.received_amount or 0)
    return int(
        sum(
            int(allocation.amount)
            for allocation in allocations
            if allocation.realization is not None and _valid_realization(allocation.realization)
        )
    )


def written_off_amount(row: models.ExpectedIncome) -> int:
    return int(sum(
        int(write_off.amount)
        for write_off in row.write_offs or []
        if write_off.reversed_at is None
    ))


def remaining_amount(row: models.ExpectedIncome) -> int:
    return max(int(row.amount) - received_amount(row) - written_off_amount(row), 0)


def normalized_status(row: models.ExpectedIncome) -> models.ExpectedIncomeStatus:
    if row.status == models.ExpectedIncomeStatus.RECEIVED:
        return models.ExpectedIncomeStatus.RESOLVED
    if row.status == models.ExpectedIncomeStatus.MISSED:
        return models.ExpectedIncomeStatus.CANCELLED
    return row.status


def active_backing_amount(row: models.ExpectedIncome) -> int:
    if not bool(row.backing_eligible):
        return 0
    if normalized_status(row) not in ACTIVE_STATUSES:
        return 0
    kind = _kind(row)
    if kind == models.ExpectedInflowKind.EARNED and (row.source is None or not row.source.is_active):
        return 0
    if kind == models.ExpectedInflowKind.RECEIVABLE and (
        row.debt is None
        or row.debt.debt_type != models.DebtType.OWED
        or row.debt.archived_at is not None
        or int(row.debt.remaining_amount or 0) <= 0
    ):
        return 0
    if kind == models.ExpectedInflowKind.REFUND and (
        row.refund_event is None
        or row.refund_event.status != models.FinancialEventStatus.POSTED
        or row.refund_event.event_type != models.TransactionType.EXPENSE
    ):
        return 0
    if kind == models.ExpectedInflowKind.ASSET_SALE and (
        row.asset is None or row.asset.status != "owned"
    ):
        return 0
    return remaining_amount(row)


def _source_label(row: models.ExpectedIncome) -> str:
    kind = _kind(row)
    if kind == models.ExpectedInflowKind.EARNED:
        return row.source.name if row.source else "Income source removed"
    if kind == models.ExpectedInflowKind.RECEIVABLE:
        return row.debt.counterparty_name if row.debt else "Receivable removed"
    if kind == models.ExpectedInflowKind.ASSET_SALE:
        return row.asset.title if row.asset else "Asset removed"
    if row.refund_event:
        return f"Refund: {row.refund_event.title}"
    return "Expense refund"


def _event_ids(row: models.ExpectedIncome) -> list[int]:
    ids: set[int] = set()
    for allocation in row.realization_allocations or []:
        if allocation.realization is None:
            continue
        ids.update(
            int(link.financial_event_id)
            for link in allocation.realization.event_links or []
        )
    if row.linked_transaction_id is not None:
        ids.add(int(row.linked_transaction_id))
    return sorted(ids)


def serialize_inflow(row: models.ExpectedIncome, *, today: date) -> schemas.ExpectedInflowOut:
    received = received_amount(row)
    remaining = remaining_amount(row)
    state = normalized_status(row)
    return schemas.ExpectedInflowOut(
        id=int(row.id),
        owner_id=int(row.owner_id),
        kind=_kind(row),
        source_id=row.source_id,
        debt_id=row.debt_id,
        asset_id=row.asset_id,
        refund_event_id=row.refund_event_id,
        parent_id=row.parent_id,
        source_label=_source_label(row),
        amount=int(row.amount),
        received_amount=received,
        remaining_amount=remaining,
        due_date=row.due_date,
        budget_year=int(row.budget_year),
        budget_month=int(row.budget_month),
        status=state,
        backing_eligible=bool(row.backing_eligible),
        backing_amount=active_backing_amount(row),
        close_reason=row.close_reason,
        closed_at=row.closed_at,
        note=row.note,
        is_overdue=state in ACTIVE_STATUSES and remaining > 0 and row.due_date < today,
        realization_event_ids=_event_ids(row),
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def inflow_query(db: Session):
    return db.query(models.ExpectedIncome).options(
        selectinload(models.ExpectedIncome.promise),
        selectinload(models.ExpectedIncome.source),
        selectinload(models.ExpectedIncome.debt),
        selectinload(models.ExpectedIncome.asset),
        selectinload(models.ExpectedIncome.refund_event),
        selectinload(models.ExpectedIncome.realization_allocations)
        .selectinload(models.ExpectedInflowRealizationAllocation.realization)
        .selectinload(models.ExpectedInflowRealization.event_links)
        .selectinload(models.ExpectedInflowRealizationEvent.financial_event),
        selectinload(models.ExpectedIncome.write_offs),
    )


def get_inflow_or_404(
    db: Session,
    owner_id: int,
    inflow_id: int,
    *,
    lock: bool = False,
) -> models.ExpectedIncome:
    query = inflow_query(db).filter(
        models.ExpectedIncome.id == inflow_id,
        models.ExpectedIncome.owner_id == owner_id,
    )
    if lock:
        query = query.with_for_update()
    row = query.first()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="expected_inflow.not_found")
    return row


def validate_planning_date(due_date: date, *, today: date) -> None:
    if due_date.year < schemas.MIN_BUDGET_YEAR:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="income.date_too_early")
    if due_date.year > today.year + schemas.MAX_BUDGET_YEARS_AHEAD:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="budgets.month_too_far_in_future")


def _get_refundable_event(
    db: Session,
    owner_id: int,
    event_id: int,
) -> tuple[models.FinancialEvent, models.EntityLedger, int]:
    event = (
        db.query(models.FinancialEvent)
        .options(
            selectinload(models.FinancialEvent.wallet_legs),
            selectinload(models.FinancialEvent.entity_legs),
        )
        .filter(
            models.FinancialEvent.id == event_id,
            models.FinancialEvent.owner_id == owner_id,
            models.FinancialEvent.event_type == models.TransactionType.EXPENSE,
            models.FinancialEvent.status == models.FinancialEventStatus.POSTED,
        )
        .first()
    )
    if event is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="expenses.not_found")
    if len(event.entity_legs or []) != 1:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="expenses.complex_event_not_supported")
    has_asset = db.query(models.Asset.id).filter(
        models.Asset.owner_id == owner_id,
        models.Asset.origin_event_id == event.id,
    ).first()
    if has_asset:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="expenses.asset_link_lock")
    refunded = int(
        db.query(func.coalesce(func.sum(models.EntityLedger.amount), 0))
        .join(models.FinancialEvent, models.FinancialEvent.id == models.EntityLedger.event_id)
        .filter(
            models.FinancialEvent.owner_id == owner_id,
            models.FinancialEvent.status == models.FinancialEventStatus.POSTED,
            models.FinancialEvent.event_type == models.TransactionType.REFUND,
            models.FinancialEvent.linked_event_id == event.id,
        )
        .scalar()
        or 0
    )
    original_amount = abs(sum(int(leg.amount or 0) for leg in event.wallet_legs or []))
    return event, event.entity_legs[0], max(original_amount - refunded, 0)


def validate_source(
    db: Session,
    owner_id: int,
    payload: schemas.ExpectedInflowCreate,
) -> tuple[bool, object]:
    if payload.kind == models.ExpectedInflowKind.EARNED:
        source = db.query(models.IncomeSource).filter(
            models.IncomeSource.id == payload.source_id,
            models.IncomeSource.owner_id == owner_id,
            models.IncomeSource.is_active == True,  # noqa: E712
        ).first()
        if source is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="income.source_not_found")
        return True, source

    if payload.kind == models.ExpectedInflowKind.RECEIVABLE:
        debt = db.query(models.Debt).filter(
            models.Debt.id == payload.debt_id,
            models.Debt.owner_id == owner_id,
            models.Debt.debt_type == models.DebtType.OWED,
            models.Debt.archived_at.is_(None),
            models.Debt.remaining_amount > 0,
        ).first()
        if debt is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="debts.not_found")
        if int(payload.amount) > int(debt.remaining_amount):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="expected_inflow.exceeds_source_amount")
        return True, debt

    if payload.kind == models.ExpectedInflowKind.REFUND:
        event, _, refundable = _get_refundable_event(db, owner_id, int(payload.refund_event_id))
        if int(payload.amount) > refundable:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="expenses.refund_exceeds_total")
        return True, event

    asset = db.query(models.Asset).filter(
        models.Asset.id == payload.asset_id,
        models.Asset.owner_id == owner_id,
        models.Asset.status == "owned",
    ).first()
    if asset is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="assets.not_found")
    duplicate = db.query(models.ExpectedIncome.id).filter(
        models.ExpectedIncome.owner_id == owner_id,
        models.ExpectedIncome.asset_id == asset.id,
        models.ExpectedIncome.status.in_(list(ACTIVE_STATUSES)),
    ).first()
    if duplicate:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="expected_inflow.asset_already_planned")
    return True, asset


def create_inflow(
    db: Session,
    owner_id: int,
    payload: schemas.ExpectedInflowCreate,
    *,
    today: date,
) -> models.ExpectedIncome:
    _, schedule = create_promise(db, owner_id, payload, today=today)
    return schedule


def update_inflow(
    db: Session,
    row: models.ExpectedIncome,
    payload: schemas.ExpectedInflowUpdate,
    *,
    today: date,
) -> None:
    if normalized_status(row) not in ACTIVE_STATUSES:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="expected_inflow.terminal_locked")
    if payload.amount is not None:
        if received_amount(row) > 0 or row.children:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="expected_inflow.amount_locked")
        row.amount = int(payload.amount)
    if payload.due_date is not None:
        validate_planning_date(payload.due_date, today=today)
        if (
            payload.due_date.year != row.budget_year
            or payload.due_date.month != row.budget_month
        ):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="expected_inflow.use_reschedule")
        row.due_date = payload.due_date
    if "note" in payload.model_fields_set:
        row.note = payload.note.strip() if payload.note else None
    db.flush()


def _resolve_wallets(
    db: Session,
    owner_id: int,
    allocations: list[schemas.IncomeWalletAllocationIn],
    expected_total: int,
) -> list[tuple[models.Wallet, int]]:
    if not allocations:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="income.wallet_required")
    if sum(int(item.amount) for item in allocations) != int(expected_total):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="income.wallet_allocation_total_mismatch")
    seen: set[int] = set()
    wallets: list[tuple[models.Wallet, int]] = []
    for allocation in sorted(allocations, key=lambda item: item.wallet_id):
        if allocation.wallet_id in seen:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="income.wallet_allocation_duplicate")
        seen.add(allocation.wallet_id)
        wallet = db.query(models.Wallet).filter(
            models.Wallet.id == allocation.wallet_id,
            models.Wallet.owner_id == owner_id,
        ).with_for_update().first()
        if wallet is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="wallets.not_found")
        if not wallet.is_active:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="wallets.archived_locked")
        wallets.append((wallet, int(allocation.amount)))
    return wallets


def _post_earned(
    db: Session,
    owner_id: int,
    row: models.ExpectedIncome,
    amount: int,
    received_date: date,
    note: str | None,
    wallets: list[tuple[models.Wallet, int]],
) -> list[models.FinancialEvent]:
    """Create a posted INCOME FinancialEvent for earned income through the
    ledger seam."""
    event = post_financial_event(
        db,
        owner_id=owner_id,
        title=f"{_source_label(row)} received"[:100],
        event_type=models.TransactionType.INCOME,
        date=received_date,
        description=note or row.note,
        entity_category=None,
        wallet_legs=[
            PostWalletLeg(wallet_id=wallet.id, amount=wallet_amount)
            for wallet, wallet_amount in wallets
        ],
        entity_legs=[
            PostEntityLeg(
                amount=int(amount),
                income_source_id=row.source_id,
            )
        ],
    )
    return [event]


def _post_receivable(
    db: Session,
    owner_id: int,
    row: models.ExpectedIncome,
    amount: int,
    received_date: date,
    note: str | None,
    wallets: list[tuple[models.Wallet, int]],
) -> list[models.FinancialEvent]:
    debt = db.query(models.Debt).filter(
        models.Debt.id == row.debt_id,
        models.Debt.owner_id == owner_id,
        models.Debt.debt_type == models.DebtType.OWED,
    ).first()
    if debt is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="debts.not_found")
    transaction, _ = create_debt_payment(
        db,
        debt,
        amount=int(amount),
        transaction_date=received_date,
        wallet_allocations=[
            schemas.DebtTransactionWalletAllocationIn(wallet_id=wallet.id, amount=wallet_amount)
            for wallet, wallet_amount in wallets
        ],
        note=note or row.note,
        income_source_id=debt.income_source_id,
    )
    reconcile_debt(db, debt.id)
    sync_debt_goal_targets(db, owner_id, debt.id)
    event_ids = [
        int(event_id)
        for (event_id,) in db.query(models.DebtLedgerEntry.financial_event_id)
        .filter(
            models.DebtLedgerEntry.source_debt_transaction_id == transaction.id,
            models.DebtLedgerEntry.financial_event_id.isnot(None),
        )
        .distinct()
        .all()
    ]
    return db.query(models.FinancialEvent).filter(models.FinancialEvent.id.in_(event_ids)).all()


def _post_refund(
    db: Session,
    owner_id: int,
    row: models.ExpectedIncome,
    amount: int,
    received_date: date,
    note: str | None,
    wallets: list[tuple[models.Wallet, int]],
) -> list[models.FinancialEvent]:
    original, original_leg, refundable = _get_refundable_event(db, owner_id, int(row.refund_event_id))
    if amount > refundable:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="expenses.refund_exceeds_total")

    event = post_financial_event(
        db,
        owner_id=owner_id,
        title="Partial Refund" if amount < refundable else "Refund",
        event_type=models.TransactionType.REFUND,
        date=received_date,
        description=note or original.title,
        linked_event_id=original.id,
        entity_category=original_leg.category,
        wallet_legs=[
            PostWalletLeg(wallet_id=wallet.id, amount=wallet_amount)
            for wallet, wallet_amount in wallets
        ],
        entity_legs=[
            PostEntityLeg(
                amount=int(amount),
                category=original_leg.category,
                subcategory_id=original_leg.subcategory_id,
                project_id=original_leg.project_id,
                project_subcategory_id=original_leg.project_subcategory_id,
                budget_id=original_leg.budget_id,
                debt_id=original_leg.debt_id,
            )
        ],
    )

    if original_leg.debt_id:
        create_debt_ledger_entry(
            db,
            owner_id=owner_id,
            debt_id=original_leg.debt_id,
            entry_type=models.DebtLedgerEntryType.REVERSAL,
            amount_delta=int(amount),
            financial_event_id=event.id,
            entry_date=received_date,
            note="Debt-linked expense refund",
        )
        reconcile_debt(db, original_leg.debt_id)
    if original_leg.budget_id:
        budget = db.query(models.Budget).filter(models.Budget.id == original_leg.budget_id).first()
        if budget:
            check_budget_alerts(db, budget)
    db.flush()
    return [event]


def _post_asset_sale(
    db: Session,
    owner_id: int,
    row: models.ExpectedIncome,
    amount: int,
    received_date: date,
    note: str | None,
    wallets: list[tuple[models.Wallet, int]],
) -> list[models.FinancialEvent]:
    asset = db.query(models.Asset).filter(
        models.Asset.id == row.asset_id,
        models.Asset.owner_id == owner_id,
    ).with_for_update().first()
    if asset is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="assets.not_found")
    if asset.status != "owned":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="assets.already_closed")
    event = models.FinancialEvent(
        owner_id=owner_id,
        title=f"Asset Sale: {asset.title}"[:100],
        description=note or asset.description,
        event_type=models.TransactionType.INCOME,
        reference_type=models.ReferenceType.ASSET_SALE,
        linked_event_id=asset.origin_event_id,
        date=received_date,
    )
    db.add(event)
    db.flush()
    for wallet, wallet_amount in wallets:
        WalletService.adjust_balance(db, wallet.id, wallet_amount, models.TransactionType.INCOME)
        db.add(models.WalletLedger(
            owner_id=owner_id,
            event_id=event.id,
            wallet_id=wallet.id,
            amount=wallet_amount,
        ))
    db.add(models.EntityLedger(event_id=event.id, amount=int(amount)))
    asset.status = "sold"
    asset.sold_date = received_date
    asset.sale_value = int(amount)
    asset.sale_event_id = event.id
    asset.current_value = int(amount)
    db.flush()
    return [event]


def _post_source(
    db: Session,
    owner_id: int,
    row: models.ExpectedIncome,
    amount: int,
    received_date: date,
    note: str | None,
    wallets: list[tuple[models.Wallet, int]],
) -> list[models.FinancialEvent]:
    kind = _kind(row)
    if kind == models.ExpectedInflowKind.EARNED:
        return _post_earned(db, owner_id, row, amount, received_date, note, wallets)
    if kind == models.ExpectedInflowKind.RECEIVABLE:
        return _post_receivable(db, owner_id, row, amount, received_date, note, wallets)
    if kind == models.ExpectedInflowKind.REFUND:
        return _post_refund(db, owner_id, row, amount, received_date, note, wallets)
    return _post_asset_sale(db, owner_id, row, amount, received_date, note, wallets)


def _sync_lifecycle(row: models.ExpectedIncome) -> None:
    received = received_amount(row)
    row.received_amount = received
    if row.close_reason in {"CANCELLED", "WRITTEN_OFF", "RESCHEDULED", "SOURCE_CLOSED"}:
        return
    if received <= 0:
        row.status = models.ExpectedIncomeStatus.EXPECTED
        row.close_reason = None
        row.closed_at = None
    elif received < int(row.amount):
        row.status = models.ExpectedIncomeStatus.PARTIALLY_RECEIVED
        row.close_reason = None
        row.closed_at = None
    else:
        row.status = models.ExpectedIncomeStatus.RESOLVED
        row.close_reason = "FULLY_RECEIVED"
        row.closed_at = datetime.now(timezone.utc)


def realize_inflow(
    db: Session,
    owner_id: int,
    route_inflow_id: int,
    payload: schemas.ExpectedInflowRealizeCreate,
    *,
    today: date,
) -> tuple[models.ExpectedInflowRealization, list[models.ExpectedIncome]]:
    if payload.received_date is not None and payload.received_date > today:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="expected_inflow.received_date_in_future")
    if payload.idempotency_key:
        existing = inflow_query(db).join(
            models.ExpectedInflowRealizationAllocation,
            models.ExpectedInflowRealizationAllocation.expected_inflow_id == models.ExpectedIncome.id,
        ).join(
            models.ExpectedInflowRealization,
            models.ExpectedInflowRealization.id == models.ExpectedInflowRealizationAllocation.realization_id,
        ).filter(
            models.ExpectedInflowRealization.owner_id == owner_id,
            models.ExpectedInflowRealization.idempotency_key == payload.idempotency_key,
        ).all()
        if existing:
            realization = next(
                allocation.realization
                for row in existing
                for allocation in row.realization_allocations
                if allocation.realization.idempotency_key == payload.idempotency_key
            )
            return realization, existing

    requested_allocations = payload.expectation_allocations or [
        schemas.ExpectedInflowExpectationAllocationCreate(
            expected_inflow_id=route_inflow_id,
            amount=int(payload.actual_amount),
        )
    ]
    if route_inflow_id not in {item.expected_inflow_id for item in requested_allocations}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="expected_inflow.route_allocation_required")
    if sum(int(item.amount) for item in requested_allocations) != int(payload.actual_amount):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="expected_inflow.allocation_total_mismatch")
    if len({item.expected_inflow_id for item in requested_allocations}) != len(requested_allocations):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="expected_inflow.duplicate_allocation")

    inflow_ids = sorted(item.expected_inflow_id for item in requested_allocations)
    rows = inflow_query(db).filter(
        models.ExpectedIncome.owner_id == owner_id,
        models.ExpectedIncome.id.in_(inflow_ids),
    ).order_by(models.ExpectedIncome.id.asc()).with_for_update().all()
    if len(rows) != len(inflow_ids):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="expected_inflow.not_found")
    source_keys = {_source_key(row) for row in rows}
    if len(source_keys) != 1:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="expected_inflow.incompatible_sources")
    allocation_by_id = {item.expected_inflow_id: int(item.amount) for item in requested_allocations}
    for row in rows:
        if normalized_status(row) not in ACTIVE_STATUSES:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="expected_inflow.not_active")
        if allocation_by_id[row.id] > remaining_amount(row):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="expected_inflow.exceeds_remaining")

    wallets = _resolve_wallets(db, owner_id, payload.wallet_allocations, int(payload.actual_amount))
    received_date = payload.received_date or today
    realization = models.ExpectedInflowRealization(
        owner_id=owner_id,
        actual_amount=int(payload.actual_amount),
        received_date=received_date,
        note=payload.note.strip() if payload.note else None,
        idempotency_key=payload.idempotency_key,
    )
    db.add(realization)
    db.flush()

    events = _post_source(
        db,
        owner_id,
        rows[0],
        int(payload.actual_amount),
        received_date,
        payload.note,
        wallets,
    )
    if not events:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="expected_inflow.posting_failed")
    for row in rows:
        db.add(models.ExpectedInflowRealizationAllocation(
            realization_id=realization.id,
            expected_inflow_id=row.id,
            amount=allocation_by_id[row.id],
        ))
    for event in events:
        db.add(models.ExpectedInflowRealizationEvent(
            realization_id=realization.id,
            financial_event_id=event.id,
        ))
    db.flush()

    for row in rows:
        db.refresh(row, attribute_names=["realization_allocations"])
        _sync_lifecycle(row)
        row.linked_transaction_id = events[0].id
        if _kind(row) == models.ExpectedInflowKind.ASSET_SALE:
            row.status = models.ExpectedIncomeStatus.RESOLVED
            row.close_reason = "SOURCE_CLOSED"
            row.closed_at = datetime.now(timezone.utc)
    db.flush()
    return realization, rows


def reschedule_inflow(
    db: Session,
    owner_id: int,
    inflow_id: int,
    payload: schemas.ExpectedInflowRescheduleCreate,
    *,
    today: date,
) -> tuple[models.ExpectedIncome, list[models.ExpectedIncome]]:
    row = get_inflow_or_404(db, owner_id, inflow_id, lock=True)
    if normalized_status(row) not in ACTIVE_STATUSES:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="expected_inflow.not_active")
    outstanding = remaining_amount(row)
    if outstanding <= 0:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="expected_inflow.no_remaining")
    if sum(int(item.amount) for item in payload.allocations) != outstanding:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="expected_inflow.reschedule_total_mismatch")
    if all(item.due_date == row.due_date for item in payload.allocations):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="expected_inflow.reschedule_no_change")
    source_month = date(row.budget_year, row.budget_month, 1)
    replacements: list[models.ExpectedIncome] = []
    for allocation in payload.allocations:
        validate_planning_date(allocation.due_date, today=today)
        if allocation.due_date < today and allocation.due_date != row.due_date:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="expected_inflow.reschedule_date_in_past")
        target_month = date(allocation.due_date.year, allocation.due_date.month, 1)
        if target_month < source_month:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="expected_inflow.reschedule_cannot_move_backward")
        replacement = models.ExpectedIncome(
            owner_id=owner_id,
            promise_id=int(row.promise_id),
            kind=_kind(row).value,
            source_id=row.source_id,
            debt_id=row.debt_id,
            asset_id=row.asset_id,
            refund_event_id=row.refund_event_id,
            parent_id=row.id,
            amount=int(allocation.amount),
            received_amount=0,
            due_date=allocation.due_date,
            budget_year=allocation.due_date.year,
            budget_month=allocation.due_date.month,
            status=models.ExpectedIncomeStatus.EXPECTED,
            backing_eligible=bool(row.backing_eligible),
            note=(allocation.note or payload.note or row.note),
        )
        db.add(replacement)
        replacements.append(replacement)
    row.status = models.ExpectedIncomeStatus.SUPERSEDED
    row.close_reason = "RESCHEDULED"
    row.closed_at = datetime.now(timezone.utc)
    db.flush()
    return row, replacements


def cancel_inflow(row: models.ExpectedIncome, payload: schemas.ExpectedInflowCloseCreate) -> None:
    if normalized_status(row) not in ACTIVE_STATUSES or received_amount(row) != 0:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="expected_inflow.cancel_not_allowed")
    row.status = models.ExpectedIncomeStatus.CANCELLED
    row.close_reason = "CANCELLED"
    row.closed_at = datetime.now(timezone.utc)
    if payload.note:
        row.note = payload.note.strip()


def write_off_inflow(row: models.ExpectedIncome, payload: schemas.ExpectedInflowCloseCreate) -> None:
    received = received_amount(row)
    if normalized_status(row) not in ACTIVE_STATUSES or received <= 0 or remaining_amount(row) <= 0:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="expected_inflow.write_off_not_allowed")
    row.status = models.ExpectedIncomeStatus.RESOLVED
    row.close_reason = "WRITTEN_OFF"
    row.closed_at = datetime.now(timezone.utc)
    if payload.note:
        row.note = payload.note.strip()


def reopen_inflow(row: models.ExpectedIncome) -> None:
    if row.close_reason not in {"CANCELLED", "WRITTEN_OFF"}:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="expected_inflow.reopen_not_allowed")
    row.close_reason = None
    row.closed_at = None
    _sync_lifecycle(row)


def reconcile_inflow(row: models.ExpectedIncome) -> None:
    if row.close_reason in {"RESCHEDULED", "SOURCE_CLOSED"}:
        return
    if row.close_reason in {"CANCELLED", "WRITTEN_OFF"}:
        return
    _sync_lifecycle(row)


def delete_inflow(db: Session, row: models.ExpectedIncome) -> None:
    if received_amount(row) > 0 or row.realization_allocations or row.children or row.parent_id is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="expected_inflow.delete_locked")
    db.delete(row)


# Promise aggregate API. `ExpectedIncome` remains the physical legacy schedule table.

def promise_query(db: Session):
    schedule_realizations = (
        selectinload(models.ExpectedInflowPromise.schedules)
        .selectinload(models.ExpectedIncome.realization_allocations)
        .selectinload(models.ExpectedInflowRealizationAllocation.realization)
        .selectinload(models.ExpectedInflowRealization.event_links)
        .selectinload(models.ExpectedInflowRealizationEvent.financial_event)
    )
    return db.query(models.ExpectedInflowPromise).options(
        selectinload(models.ExpectedInflowPromise.source),
        selectinload(models.ExpectedInflowPromise.debt),
        selectinload(models.ExpectedInflowPromise.asset),
        selectinload(models.ExpectedInflowPromise.refund_event),
        selectinload(models.ExpectedInflowPromise.schedules).selectinload(models.ExpectedIncome.write_offs),
        selectinload(models.ExpectedInflowPromise.schedules).selectinload(models.ExpectedIncome.children),
        schedule_realizations,
        selectinload(models.ExpectedInflowPromise.realizations)
        .selectinload(models.ExpectedInflowRealization.event_links)
        .selectinload(models.ExpectedInflowRealizationEvent.financial_event),
        selectinload(models.ExpectedInflowPromise.write_offs),
    )


def get_promise_or_404(
    db: Session,
    owner_id: int,
    promise_id: int,
    *,
    lock: bool = False,
) -> models.ExpectedInflowPromise:
    query = promise_query(db).filter(
        models.ExpectedInflowPromise.id == promise_id,
        models.ExpectedInflowPromise.owner_id == owner_id,
    )
    if lock:
        query = query.with_for_update()
    promise = query.first()
    if promise is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="expected_inflow.not_found")
    return promise


def _promise_kind(promise: models.ExpectedInflowPromise) -> models.ExpectedInflowKind:
    return models.ExpectedInflowKind(promise.kind)


def _promise_source_label(promise: models.ExpectedInflowPromise) -> str:
    kind = _promise_kind(promise)
    if kind == models.ExpectedInflowKind.EARNED:
        return promise.source.name if promise.source else "Income source removed"
    if kind == models.ExpectedInflowKind.RECEIVABLE:
        return promise.debt.counterparty_name if promise.debt else "Receivable removed"
    if kind == models.ExpectedInflowKind.ASSET_SALE:
        return promise.asset.title if promise.asset else "Asset removed"
    if promise.refund_event:
        return f"Refund: {promise.refund_event.title}"
    return "Expense refund"


def _schedule_structural_state(schedule: models.ExpectedIncome) -> models.ExpectedIncomeStatus:
    """Structural lifecycle only: active, superseded, or cancelled.
    Does NOT encode settlement/read labels."""
    if schedule.close_reason == "RESCHEDULED":
        return models.ExpectedIncomeStatus.SUPERSEDED
    if schedule.close_reason == "CANCELLED":
        return models.ExpectedIncomeStatus.CANCELLED
    return models.ExpectedIncomeStatus.EXPECTED


def schedule_read_state(schedule: models.ExpectedIncome, *, today: date) -> models.ScheduleReadState:
    """Derived schedule settlement/read label — never stored as source of truth."""
    structural = _schedule_structural_state(schedule)
    if structural == models.ExpectedIncomeStatus.SUPERSEDED:
        return models.ScheduleReadState.SUPERSEDED
    if structural == models.ExpectedIncomeStatus.CANCELLED:
        return models.ScheduleReadState.CANCELLED
    received = received_amount(schedule)
    written_off = written_off_amount(schedule)
    remaining = max(int(schedule.amount) - received - written_off, 0)
    if remaining == 0:
        if written_off > 0 and received > 0:
            return models.ScheduleReadState.SETTLED
        if written_off > 0:
            return models.ScheduleReadState.WRITTEN_OFF
        return models.ScheduleReadState.FULLY_RECEIVED
    is_overdue = schedule.due_date < today
    if received > 0:
        return models.ScheduleReadState.OVERDUE if is_overdue else models.ScheduleReadState.PARTIAL
    return models.ScheduleReadState.OVERDUE if is_overdue else models.ScheduleReadState.OUTSTANDING


def _schedule_state(schedule: models.ExpectedIncome) -> models.ExpectedIncomeStatus:
    """Stored schedule status (rebuildable projection) — legacy compat.
    Prefer schedule_read_state() for user-facing labels."""
    if schedule.close_reason == "RESCHEDULED":
        return models.ExpectedIncomeStatus.SUPERSEDED
    if schedule.close_reason == "WRITTEN_OFF" and remaining_amount(schedule) == 0:
        return models.ExpectedIncomeStatus.WRITTEN_OFF
    return normalized_status(schedule)


def _schedule_is_active(schedule: models.ExpectedIncome) -> bool:
    return _schedule_state(schedule) in ACTIVE_STATUSES and remaining_amount(schedule) > 0


def promise_received_amount(promise: models.ExpectedInflowPromise) -> int:
    return int(sum(received_amount(schedule) for schedule in promise.schedules or []))


def promise_written_off_amount(promise: models.ExpectedInflowPromise) -> int:
    return int(sum(
        int(write_off.amount)
        for write_off in promise.write_offs or []
        if write_off.reversed_at is None
    ))


def promise_outstanding_amount(promise: models.ExpectedInflowPromise) -> int:
    return int(sum(
        remaining_amount(schedule)
        for schedule in promise.schedules or []
        if _schedule_is_active(schedule)
    ))


def promise_lifecycle(promise: models.ExpectedInflowPromise) -> models.ExpectedInflowPromiseStatus:
    """Stored lifecycle: OPEN when outstanding > 0; CLOSED otherwise.
    Derived from immutable financial facts."""
    outstanding = promise_outstanding_amount(promise)
    return (
        models.ExpectedInflowPromiseStatus.OPEN
        if outstanding > 0
        else models.ExpectedInflowPromiseStatus.CLOSED
    )


def _is_cancelled(promise: models.ExpectedInflowPromise) -> bool:
    """True when every non-superseded schedule has been explicitly cancelled."""
    current = [
        s for s in (promise.schedules or [])
        if s.close_reason != "RESCHEDULED"
    ]
    return bool(current) and all(s.close_reason == "CANCELLED" for s in current)


def promise_display_state(promise: models.ExpectedInflowPromise) -> models.PromiseDisplayState:
    """Derived Promise display state from immutable financial facts.
    Never stored — always computed from received, written-off, and outstanding."""
    received = promise_received_amount(promise)
    written_off = promise_written_off_amount(promise)
    outstanding = promise_outstanding_amount(promise)
    if outstanding > 0:
        return models.PromiseDisplayState.EXPECTED
    if received >= int(promise.original_amount) and written_off == 0:
        return models.PromiseDisplayState.FULLY_RECEIVED
    if written_off >= int(promise.original_amount) and received == 0:
        return models.PromiseDisplayState.WRITTEN_OFF
    # Mixed settlement: some received, some written off, zero outstanding
    return models.PromiseDisplayState.SETTLED


# Backward-compat alias — callers should migrate to promise_display_state or promise_lifecycle
def promise_status(promise: models.ExpectedInflowPromise) -> models.PromiseDisplayState:
    return promise_display_state(promise)


def promise_is_pristine(promise: models.ExpectedInflowPromise) -> bool:
    schedules = list(promise.schedules or [])
    return (
        len(schedules) == 1
        and schedules[0].parent_id is None
        and not schedules[0].children
        and received_amount(schedules[0]) == 0
        and written_off_amount(schedules[0]) == 0
        and _schedule_is_active(schedules[0])
    )


def _sync_schedule(schedule: models.ExpectedIncome) -> None:
    if schedule.close_reason == "RESCHEDULED":
        schedule.status = models.ExpectedIncomeStatus.SUPERSEDED
        return
    if schedule.close_reason == "CANCELLED":
        schedule.status = models.ExpectedIncomeStatus.CANCELLED
        return
    received = received_amount(schedule)
    written_off = written_off_amount(schedule)
    remaining = max(int(schedule.amount) - received - written_off, 0)
    schedule.received_amount = received
    if remaining == 0:
        if written_off > 0:
            schedule.status = models.ExpectedIncomeStatus.WRITTEN_OFF
            schedule.close_reason = "WRITTEN_OFF"
        else:
            schedule.status = models.ExpectedIncomeStatus.RESOLVED
            schedule.close_reason = "FULLY_RECEIVED"
        schedule.closed_at = schedule.closed_at or datetime.now(timezone.utc)
    elif received > 0:
        schedule.status = models.ExpectedIncomeStatus.PARTIALLY_RECEIVED
        schedule.close_reason = None
        schedule.closed_at = None
    else:
        schedule.status = models.ExpectedIncomeStatus.EXPECTED
        schedule.close_reason = None
        schedule.closed_at = None


def _sync_promise(promise: models.ExpectedInflowPromise) -> None:
    lifecycle = promise_lifecycle(promise)
    promise.status = lifecycle.value
    if lifecycle == models.ExpectedInflowPromiseStatus.CLOSED:
        promise.closed_at = promise.closed_at or datetime.now(timezone.utc)
    else:
        promise.closed_at = None


def _serialize_schedule(schedule: models.ExpectedIncome, *, today: date) -> schemas.ExpectedInflowScheduleOut:
    stored_status = _schedule_state(schedule)
    remaining = remaining_amount(schedule)
    read_state = schedule_read_state(schedule, today=today)
    structural = _schedule_structural_state(schedule)
    return schemas.ExpectedInflowScheduleOut(
        id=int(schedule.id),
        promise_id=int(schedule.promise_id),
        parent_id=schedule.parent_id,
        amount=int(schedule.amount),
        received_amount=received_amount(schedule),
        written_off_amount=written_off_amount(schedule),
        remaining_amount=remaining,
        due_date=schedule.due_date,
        budget_year=int(schedule.budget_year),
        budget_month=int(schedule.budget_month),
        status=stored_status,
        structural_lifecycle=structural,
        read_state=read_state,
        close_reason=schedule.close_reason,
        is_active=_schedule_is_active(schedule),
        is_overdue=_schedule_is_active(schedule) and schedule.due_date < today,
        note=schedule.note,
        created_at=schedule.created_at,
        updated_at=schedule.updated_at,
    )


def _promise_event_ids(promise: models.ExpectedInflowPromise) -> list[int]:
    return sorted({
        int(link.financial_event_id)
        for realization in promise.realizations or []
        for link in realization.event_links or []
    })


def serialize_promise(
    promise: models.ExpectedInflowPromise,
    *,
    today: date,
    period_year: int | None = None,
    period_month: int | None = None,
    include_detail: bool = True,
) -> schemas.ExpectedInflowPromiseOut:
    schedules = sorted(promise.schedules or [], key=lambda row: (row.due_date, row.id))
    active_schedules = [schedule for schedule in schedules if _schedule_is_active(schedule)]
    current_schedules = [
        schedule for schedule in schedules
        if _schedule_state(schedule) != models.ExpectedIncomeStatus.SUPERSEDED
    ]
    period_schedules = current_schedules
    if period_year is not None and period_month is not None:
        period_schedules = [
            schedule for schedule in current_schedules
            if schedule.budget_year == period_year and schedule.budget_month == period_month
        ]
    received = promise_received_amount(promise)
    written_off = promise_written_off_amount(promise)
    outstanding = promise_outstanding_amount(promise)
    lifecycle = promise_lifecycle(promise)
    display_state = promise_display_state(promise)
    next_due = min((schedule.due_date for schedule in active_schedules), default=None)
    # Derive close_reason from facts, not stored state
    close_reason = None
    if lifecycle == models.ExpectedInflowPromiseStatus.CLOSED:
        if written_off > 0 and received > 0:
            close_reason = "SETTLED"
        elif written_off > 0:
            close_reason = "WRITTEN_OFF"
        elif received > 0:
            close_reason = "FULLY_RECEIVED"
        elif _is_cancelled(promise):
            close_reason = "CANCELLED"
    realization_outputs: list[schemas.ExpectedInflowRealizationOut] = []
    activity: list[schemas.ExpectedInflowActivityOut] = [
        schemas.ExpectedInflowActivityOut(
            id=f"created-{promise.id}",
            activity_type="CREATED",
            activity_date=promise.created_at.date(),
            amount=int(promise.original_amount),
            note=promise.note,
        )
    ]
    if include_detail:
        for realization in sorted(promise.realizations or [], key=lambda item: (item.received_date, item.id)):
            event_ids = sorted(int(link.financial_event_id) for link in realization.event_links or [])
            realization_outputs.append(schemas.ExpectedInflowRealizationOut(
                id=int(realization.id),
                actual_amount=int(realization.actual_amount),
                received_date=realization.received_date,
                note=realization.note,
                event_ids=event_ids,
                reversed_at=realization.reversed_at,
                reversal_note=realization.reversal_note,
                created_at=realization.created_at,
            ))
            activity.append(schemas.ExpectedInflowActivityOut(
                id=f"receipt-{realization.id}",
                activity_type="RECEIVED",
                activity_date=realization.received_date,
                amount=int(realization.actual_amount),
                note=realization.note,
            ))
            # Ticket 7: Emit receipt reversal activity when the realization was reversed.
            if realization.reversed_at is not None:
                activity.append(schemas.ExpectedInflowActivityOut(
                    id=f"receipt-reversed-{realization.id}",
                    activity_type="RECEIPT_REVERSED",
                    activity_date=realization.reversed_at.date(),
                    amount=int(realization.actual_amount),
                    note=realization.reversal_note,
                ))
        for schedule in schedules:
            if schedule.close_reason == "RESCHEDULED" and schedule.closed_at:
                activity.append(schemas.ExpectedInflowActivityOut(
                    id=f"rescheduled-{schedule.id}",
                    activity_type="RESCHEDULED",
                    activity_date=schedule.closed_at.date(),
                    amount=remaining_amount(schedule),
                    schedule_id=int(schedule.id),
                    note=schedule.note,
                ))
        for write_off in promise.write_offs or []:
            activity.append(schemas.ExpectedInflowActivityOut(
                id=f"write-off-{write_off.id}",
                activity_type="WRITTEN_OFF",
                activity_date=write_off.written_off_date,
                amount=int(write_off.amount),
                schedule_id=int(write_off.schedule_id),
                note=write_off.reason,
            ))
            # Ticket 8: Emit reversal as a separate activity entry so the
            # timeline shows both the original write-off AND its reversal.
            if write_off.reversed_at is not None:
                activity.append(schemas.ExpectedInflowActivityOut(
                    id=f"write-off-reversed-{write_off.id}",
                    activity_type="WRITE_OFF_REVERSED",
                    activity_date=write_off.reversed_at.date(),
                    amount=int(write_off.amount),
                    schedule_id=int(write_off.schedule_id),
                    note=write_off.reversal_note,
                ))
    return schemas.ExpectedInflowPromiseOut(
        id=int(promise.id),
        owner_id=int(promise.owner_id),
        kind=_promise_kind(promise),
        source_id=promise.source_id,
        debt_id=promise.debt_id,
        asset_id=promise.asset_id,
        refund_event_id=promise.refund_event_id,
        title=promise.title,
        source_label=_promise_source_label(promise),
        amount=int(promise.original_amount),
        original_amount=int(promise.original_amount),
        received_amount=received,
        written_off_amount=written_off,
        remaining_amount=outstanding,
        outstanding_amount=outstanding,
        due_date=next_due,
        next_due_date=next_due,
        budget_year=(next_due.year if next_due else None),
        budget_month=(next_due.month if next_due else None),
        status=lifecycle,
        display_state=display_state,
        backing_eligible=bool(promise.backing_eligible),
        backing_amount=(outstanding if promise.backing_eligible else 0),
        period_scheduled_amount=sum(int(schedule.amount) for schedule in period_schedules),
        period_backing_amount=sum(active_backing_amount(schedule) for schedule in period_schedules),
        is_pristine=promise_is_pristine(promise),
        is_rescheduled=any(schedule.parent_id is not None or schedule.close_reason == "RESCHEDULED" for schedule in schedules),
        is_partially_written_off=written_off > 0 and outstanding > 0,
        is_overdue=any(schedule.due_date < today for schedule in active_schedules),
        close_reason=close_reason,
        closed_at=promise.closed_at,
        note=promise.note,
        realization_event_ids=_promise_event_ids(promise),
        schedules=[_serialize_schedule(schedule, today=today) for schedule in schedules],
        realizations=realization_outputs,
        write_offs=[schemas.ExpectedInflowWriteOffOut(
            id=int(write_off.id),
            schedule_id=int(write_off.schedule_id),
            amount=int(write_off.amount),
            reason=write_off.reason,
            written_off_date=write_off.written_off_date,
            reversed_at=write_off.reversed_at,
            reversal_note=write_off.reversal_note,
            created_at=write_off.created_at,
        ) for write_off in promise.write_offs or []] if include_detail else [],
        activity=sorted(activity, key=lambda item: (item.activity_date, item.id), reverse=True) if include_detail else [],
        created_at=promise.created_at,
        updated_at=promise.updated_at,
    )


def list_promises(
    db: Session,
    owner_id: int,
    *,
    today: date,
    budget_year: int | None = None,
    budget_month: int | None = None,
    view: str = "all",
    kind: models.ExpectedInflowKind | None = None,
    search: str | None = None,
    display_state: models.PromiseDisplayState | None = None,
) -> list[schemas.ExpectedInflowPromiseOut]:
    query = promise_query(db).filter(models.ExpectedInflowPromise.owner_id == owner_id)
    if kind is not None:
        query = query.filter(models.ExpectedInflowPromise.kind == kind.value)
    if search:
        pattern = f"%{search.strip()}%"
        query = query.filter(
            models.ExpectedInflowPromise.title.ilike(pattern)
        )
    promises = query.order_by(models.ExpectedInflowPromise.created_at.desc()).all()
    outputs: list[schemas.ExpectedInflowPromiseOut] = []
    for promise in promises:
        output = serialize_promise(
            promise,
            today=today,
            period_year=budget_year,
            period_month=budget_month,
            include_detail=False,
        )
        # Agreements mode: no month filtering, optional display_state filter
        if budget_year is None and budget_month is None:
            if display_state is not None and output.display_state != display_state:
                continue
        else:
            # Cashflow mode: month filtering
            has_period_schedule = any(
                schedule.budget_year == budget_year and schedule.budget_month == budget_month
                for schedule in promise.schedules or []
            )
            if not has_period_schedule:
                continue
        is_active = output.status == models.ExpectedInflowPromiseStatus.OPEN
        if view == "active" and not is_active:
            continue
        if view == "history" and is_active:
            continue
        outputs.append(output)
    return outputs


def list_cashflow(
    db: Session,
    owner_id: int,
    *,
    today: date,
    budget_year: int,
    budget_month: int,
    kind: models.ExpectedInflowKind | None = None,
) -> list[schemas.ExpectedInflowCashflowRowOut]:
    """Return schedule chunks due in the selected month with parent Promise context."""
    query = promise_query(db).filter(models.ExpectedInflowPromise.owner_id == owner_id)
    if kind is not None:
        query = query.filter(models.ExpectedInflowPromise.kind == kind.value)
    promises = query.order_by(models.ExpectedInflowPromise.created_at.desc()).all()
    rows: list[schemas.ExpectedInflowCashflowRowOut] = []
    for promise in promises:
        for schedule in promise.schedules or []:
            if schedule.budget_year != budget_year or schedule.budget_month != budget_month:
                continue
            # Omit superseded schedules (they're part of reschedule history)
            if _schedule_structural_state(schedule) == models.ExpectedIncomeStatus.SUPERSEDED:
                continue
            read_state = schedule_read_state(schedule, today=today)
            rows.append(schemas.ExpectedInflowCashflowRowOut(
                schedule_id=int(schedule.id),
                promise_id=int(promise.id),
                promise_title=promise.title,
                source_label=_promise_source_label(promise),
                kind=_promise_kind(promise),
                amount=int(schedule.amount),
                received_amount=received_amount(schedule),
                remaining_amount=remaining_amount(schedule),
                due_date=schedule.due_date,
                budget_year=int(schedule.budget_year),
                budget_month=int(schedule.budget_month),
                read_state=read_state,
                is_overdue=_schedule_is_active(schedule) and schedule.due_date < today,
                promise_is_open=promise_lifecycle(promise) == models.ExpectedInflowPromiseStatus.OPEN,
            ))
    return sorted(rows, key=lambda r: (r.due_date, r.schedule_id))


def _source_title(kind: models.ExpectedInflowKind, source_object) -> str:
    if kind == models.ExpectedInflowKind.EARNED:
        return source_object.name
    if kind == models.ExpectedInflowKind.RECEIVABLE:
        return source_object.counterparty_name
    if kind == models.ExpectedInflowKind.ASSET_SALE:
        return source_object.title
    return f"Refund: {source_object.title}"


def create_promise(
    db: Session,
    owner_id: int,
    payload: schemas.ExpectedInflowCreate,
    *,
    today: date,
) -> tuple[models.ExpectedInflowPromise, models.ExpectedIncome]:
    validate_planning_date(payload.due_date, today=today)
    backing_eligible, source_object = validate_source(db, owner_id, payload)
    promise = models.ExpectedInflowPromise(
        owner_id=owner_id,
        kind=payload.kind.value,
        source_id=payload.source_id,
        debt_id=payload.debt_id,
        asset_id=payload.asset_id,
        refund_event_id=payload.refund_event_id,
        title=(payload.title.strip() if payload.title else _source_title(payload.kind, source_object))[:100],
        original_amount=int(payload.amount),
        status=models.ExpectedInflowPromiseStatus.OPEN.value,
        backing_eligible=bool(backing_eligible),
        note=payload.note.strip() if payload.note else None,
    )
    db.add(promise)
    db.flush()
    schedule = models.ExpectedIncome(
        owner_id=owner_id,
        promise_id=int(promise.id),
        kind=payload.kind.value,
        source_id=payload.source_id,
        debt_id=payload.debt_id,
        asset_id=payload.asset_id,
        refund_event_id=payload.refund_event_id,
        amount=int(payload.amount),
        received_amount=0,
        due_date=payload.due_date,
        budget_year=payload.due_date.year,
        budget_month=payload.due_date.month,
        status=models.ExpectedIncomeStatus.EXPECTED,
        backing_eligible=bool(backing_eligible),
        note=promise.note,
    )
    promise.schedules.append(schedule)
    db.flush()
    return promise, schedule


def update_promise(
    db: Session,
    promise: models.ExpectedInflowPromise,
    payload: schemas.ExpectedInflowUpdate,
    *,
    today: date,
) -> None:
    fields = payload.model_fields_set
    if "title" in fields:
        if not payload.title or not payload.title.strip():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="expected_inflow.title_required")
        promise.title = payload.title.strip()
    protected_changes = fields.intersection({"amount", "due_date", "note"})
    if protected_changes and not promise_is_pristine(promise):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="expected_inflow.non_pristine_locked")
    if not protected_changes:
        db.flush()
        return
    schedule = next(schedule for schedule in promise.schedules if _schedule_is_active(schedule))
    if payload.amount is not None:
        promise.original_amount = int(payload.amount)
        schedule.amount = int(payload.amount)
    if payload.due_date is not None:
        validate_planning_date(payload.due_date, today=today)
        schedule.due_date = payload.due_date
        schedule.budget_year = payload.due_date.year
        schedule.budget_month = payload.due_date.month
    if "note" in fields:
        promise.note = payload.note.strip() if payload.note else None
        schedule.note = promise.note
    db.flush()


def _active_schedules(promise: models.ExpectedInflowPromise) -> list[models.ExpectedIncome]:
    return sorted(
        [schedule for schedule in promise.schedules or [] if _schedule_is_active(schedule)],
        key=lambda row: (row.due_date, row.id),
    )


def _allocate_to_schedules(
    schedules: list[models.ExpectedIncome],
    amount: int,
    explicit: list[tuple[int, int]],
) -> list[tuple[models.ExpectedIncome, int]]:
    by_id = {int(schedule.id): schedule for schedule in schedules}
    allocation_total = min(
        int(amount),
        sum(remaining_amount(schedule) for schedule in schedules),
    )
    if explicit:
        if len({schedule_id for schedule_id, _ in explicit}) != len(explicit):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="expected_inflow.duplicate_allocation")
        if sum(value for _, value in explicit) != allocation_total:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="expected_inflow.allocation_total_mismatch")
        allocations: list[tuple[models.ExpectedIncome, int]] = []
        for schedule_id, value in explicit:
            schedule = by_id.get(schedule_id)
            if schedule is None:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="expected_inflow.schedule_not_active")
            if value <= 0 or value > remaining_amount(schedule):
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="expected_inflow.exceeds_remaining")
            allocations.append((schedule, value))
        return allocations
    unallocated = allocation_total
    allocations = []
    for schedule in schedules:
        value = min(unallocated, remaining_amount(schedule))
        if value > 0:
            allocations.append((schedule, value))
            unallocated -= value
        if unallocated == 0:
            break
    if unallocated > 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="expected_inflow.exceeds_remaining")
    return allocations


def realize_promise(
    db: Session,
    owner_id: int,
    promise_id: int,
    payload: schemas.ExpectedInflowRealizeCreate,
    *,
    today: date,
) -> tuple[models.ExpectedInflowRealization, models.ExpectedInflowPromise]:
    received_date = payload.received_date or today
    if received_date > today:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="expected_inflow.received_date_in_future")
    if payload.idempotency_key:
        existing = db.query(models.ExpectedInflowRealization).filter(
            models.ExpectedInflowRealization.owner_id == owner_id,
            models.ExpectedInflowRealization.promise_id == promise_id,
            models.ExpectedInflowRealization.idempotency_key == payload.idempotency_key,
        ).first()
        if existing is not None:
            return existing, get_promise_or_404(db, owner_id, promise_id)
    promise = get_promise_or_404(db, owner_id, promise_id, lock=True)
    # Ticket 2: Closed Promises reject financial commands
    if promise_lifecycle(promise) == models.ExpectedInflowPromiseStatus.CLOSED:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="expected_inflow.promise_is_closed")
    schedules = _active_schedules(promise)
    if not schedules:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="expected_inflow.not_active")
    # Ticket 2: Reject over-receipt above Promise original_amount
    total_settled = promise_received_amount(promise) + promise_written_off_amount(promise)
    if total_settled + int(payload.actual_amount) > int(promise.original_amount):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="expected_inflow.over_cap",
        )
    schedule_ids = [int(schedule.id) for schedule in schedules]
    db.query(models.ExpectedIncome).filter(models.ExpectedIncome.id.in_(schedule_ids)).order_by(
        models.ExpectedIncome.id.asc()
    ).with_for_update().all()
    explicit = [
        (int(item.schedule_id), int(item.amount))
        for item in payload.schedule_allocations
    ] or [
        (int(item.expected_inflow_id), int(item.amount))
        for item in payload.expectation_allocations
    ]
    allocations = _allocate_to_schedules(schedules, int(payload.actual_amount), explicit)
    wallets = _resolve_wallets(db, owner_id, payload.wallet_allocations, int(payload.actual_amount))
    events = _post_source(
        db,
        owner_id,
        schedules[0],
        int(payload.actual_amount),
        received_date,
        payload.note,
        wallets,
    )
    if not events:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="expected_inflow.posting_failed")
    realization = models.ExpectedInflowRealization(
        owner_id=owner_id,
        promise_id=int(promise.id),
        actual_amount=int(payload.actual_amount),
        received_date=received_date,
        note=payload.note.strip() if payload.note else None,
        idempotency_key=payload.idempotency_key,
    )
    db.add(realization)
    for schedule, value in allocations:
        realization.allocations.append(models.ExpectedInflowRealizationAllocation(
            expected_inflow=schedule,
            amount=value,
        ))
    for event in events:
        realization.event_links.append(models.ExpectedInflowRealizationEvent(financial_event=event))
    db.flush()
    if _promise_kind(promise) == models.ExpectedInflowKind.ASSET_SALE:
        for schedule in schedules:
            remainder = remaining_amount(schedule)
            if remainder > 0:
                schedule.write_offs.append(models.ExpectedInflowWriteOff(
                    owner_id=owner_id,
                    promise_id=int(promise.id),
                    amount=remainder,
                    reason="Actual sale proceeds were below the expected amount",
                    written_off_date=received_date,
                ))
    db.flush()
    for schedule in schedules:
        _sync_schedule(schedule)
    _sync_promise(promise)
    db.flush()
    return realization, promise


def reschedule_promise(
    db: Session,
    owner_id: int,
    promise_id: int,
    payload: schemas.ExpectedInflowRescheduleCreate,
    *,
    today: date,
) -> tuple[models.ExpectedInflowPromise, list[models.ExpectedIncome]]:
    promise = get_promise_or_404(db, owner_id, promise_id, lock=True)
    # Ticket 2: Closed Promises reject financial commands
    if promise_lifecycle(promise) == models.ExpectedInflowPromiseStatus.CLOSED:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="expected_inflow.promise_is_closed")
    active = _active_schedules(promise)
    if not active:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="expected_inflow.not_active")
    source = next(
        (schedule for schedule in active if int(schedule.id) == payload.source_schedule_id),
        None,
    ) if payload.source_schedule_id is not None else active[0]
    if source is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="expected_inflow.schedule_not_active")
    source = db.query(models.ExpectedIncome).filter(
        models.ExpectedIncome.id == source.id,
        models.ExpectedIncome.promise_id == promise.id,
    ).with_for_update().one()
    outstanding = remaining_amount(source)
    if sum(int(item.amount) for item in payload.allocations) != outstanding:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="expected_inflow.reschedule_total_mismatch")
    if all(item.due_date == source.due_date for item in payload.allocations):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="expected_inflow.reschedule_no_change")
    replacements: list[models.ExpectedIncome] = []
    for allocation in payload.allocations:
        validate_planning_date(allocation.due_date, today=today)
        if allocation.due_date < today and allocation.due_date != source.due_date:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="expected_inflow.reschedule_date_in_past")
        replacement = models.ExpectedIncome(
            owner_id=owner_id,
            promise_id=int(promise.id),
            kind=promise.kind,
            source_id=promise.source_id,
            debt_id=promise.debt_id,
            asset_id=promise.asset_id,
            refund_event_id=promise.refund_event_id,
            parent_id=int(source.id),
            amount=int(allocation.amount),
            received_amount=0,
            due_date=allocation.due_date,
            budget_year=allocation.due_date.year,
            budget_month=allocation.due_date.month,
            status=models.ExpectedIncomeStatus.EXPECTED,
            backing_eligible=bool(promise.backing_eligible),
            note=allocation.note or payload.note or source.note,
        )
        db.add(replacement)
        replacements.append(replacement)
    source.status = models.ExpectedIncomeStatus.SUPERSEDED
    source.close_reason = "RESCHEDULED"
    source.closed_at = datetime.now(timezone.utc)
    db.flush()
    _sync_promise(promise)
    db.flush()
    return promise, replacements


def write_off_promise(
    db: Session,
    owner_id: int,
    promise_id: int,
    payload: schemas.ExpectedInflowWriteOffCreate,
    *,
    today: date,
) -> tuple[models.ExpectedInflowPromise, list[models.ExpectedInflowWriteOff]]:
    written_off_date = payload.written_off_date or today
    if written_off_date > today:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="expected_inflow.write_off_date_in_future")
    promise = get_promise_or_404(db, owner_id, promise_id, lock=True)
    # Ticket 2: Closed Promises reject financial commands
    if promise_lifecycle(promise) == models.ExpectedInflowPromiseStatus.CLOSED:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="expected_inflow.promise_is_closed")
    schedules = _active_schedules(promise)
    if not schedules:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="expected_inflow.not_active")
    explicit = [(int(item.schedule_id), int(item.amount)) for item in payload.schedule_allocations]
    allocations = _allocate_to_schedules(schedules, int(payload.amount), explicit)
    write_offs: list[models.ExpectedInflowWriteOff] = []
    for schedule, value in allocations:
        write_off = models.ExpectedInflowWriteOff(
            owner_id=owner_id,
            promise_id=int(promise.id),
            schedule_id=int(schedule.id),
            amount=value,
            reason=payload.reason.strip(),
            written_off_date=written_off_date,
        )
        schedule.write_offs.append(write_off)
        write_offs.append(write_off)
    db.flush()
    for schedule, _ in allocations:
        _sync_schedule(schedule)
    _sync_promise(promise)
    db.flush()
    return promise, write_offs


def reverse_write_off(
    db: Session,
    owner_id: int,
    promise_id: int,
    write_off_id: int,
    payload: schemas.ExpectedInflowWriteOffReverseCreate,
) -> models.ExpectedInflowPromise:
    promise = get_promise_or_404(db, owner_id, promise_id, lock=True)
    write_off = db.query(models.ExpectedInflowWriteOff).filter(
        models.ExpectedInflowWriteOff.id == write_off_id,
        models.ExpectedInflowWriteOff.promise_id == promise_id,
        models.ExpectedInflowWriteOff.owner_id == owner_id,
    ).with_for_update().first()
    if write_off is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="expected_inflow.write_off_not_found")
    if write_off.reversed_at is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="expected_inflow.write_off_already_reversed")
    note = payload.note.strip() if payload.note else None
    # Ticket 8: Append-only reversal — create a dedicated reversal record
    # rather than silently mutating the write-off. The original write-off
    # row remains an immutable historical fact; the reversal is a new row.
    reversal = models.ExpectedInflowWriteOffReversal(
        owner_id=owner_id,
        write_off_id=int(write_off.id),
        promise_id=int(promise.id),
        note=note,
    )
    db.add(reversal)
    # Denormalised convenience columns so math queries stay simple.
    write_off.reversed_at = datetime.now(timezone.utc)
    write_off.reversal_note = note
    _sync_schedule(write_off.schedule)
    _sync_promise(promise)
    db.flush()
    return promise


def reverse_realization(
    db: Session,
    owner_id: int,
    promise_id: int,
    realization_id: int,
    payload: schemas.ExpectedInflowRealizationReverseCreate,
    *,
    user_tz: object = None,
) -> models.ExpectedInflowPromise:
    """Reverse a receipt (realization) while preserving the original history.

    Ticket 7: First-class receipt reversal. The original realization is
    preserved as an immutable historical fact. The linked financial events
    are voided through the shared ledger reversal seam, wallet/entity
    ledger correctness is maintained, and schedule/Promise math is
    recalculated.
    """
    if user_tz is None:
        from datetime import timezone as tz_mod
        from zoneinfo import ZoneInfo
        user_tz = ZoneInfo("UTC")
    promise = get_promise_or_404(db, owner_id, promise_id, lock=True)
    realization = db.query(models.ExpectedInflowRealization).filter(
        models.ExpectedInflowRealization.id == realization_id,
        models.ExpectedInflowRealization.promise_id == promise_id,
        models.ExpectedInflowRealization.owner_id == owner_id,
    ).with_for_update().first()
    if realization is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="expected_inflow.realization_not_found")
    if realization.reversed_at is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="expected_inflow.realization_already_reversed")
    # Void every linked financial event through the shared ledger seam.
    for link in realization.event_links or []:
        event = link.financial_event
        if event is not None and event.status == models.FinancialEventStatus.POSTED:
            void_financial_event(
                db,
                event=event,
                owner_id=owner_id,
                user_tz=user_tz,
                void_reason="Receipt reversed",
            )
    # Mark the realization as reversed — original row stays as history.
    realization.reversed_at = datetime.now(timezone.utc)
    realization.reversal_note = payload.note.strip() if payload.note else None
    # Recalculate every schedule that received money from this realization.
    allocated_schedule_ids = {
        int(allocation.expected_inflow_id)
        for allocation in realization.allocations or []
    }
    for schedule in promise.schedules or []:
        if int(schedule.id) in allocated_schedule_ids:
            _sync_schedule(schedule)
    _sync_promise(promise)
    db.flush()
    return promise


def cancel_promise(
    promise: models.ExpectedInflowPromise,
    payload: schemas.ExpectedInflowCloseCreate,
) -> None:
    # Ticket 2: Closed Promises reject financial commands
    if promise_lifecycle(promise) == models.ExpectedInflowPromiseStatus.CLOSED:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="expected_inflow.promise_is_closed")
    if promise_received_amount(promise) > 0 or promise_written_off_amount(promise) > 0:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="expected_inflow.cancel_not_allowed")
    active = _active_schedules(promise)
    if not active:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="expected_inflow.not_active")
    for schedule in active:
        schedule.status = models.ExpectedIncomeStatus.CANCELLED
        schedule.close_reason = "CANCELLED"
        schedule.closed_at = datetime.now(timezone.utc)
    if payload.note:
        promise.note = payload.note.strip()
    _sync_promise(promise)


def reopen_promise(promise: models.ExpectedInflowPromise) -> None:
    lifecycle = promise_lifecycle(promise)
    if lifecycle != models.ExpectedInflowPromiseStatus.CLOSED:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="expected_inflow.reopen_not_allowed")
    display = promise_display_state(promise)
    if display == models.PromiseDisplayState.FULLY_RECEIVED:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="expected_inflow.reopen_not_allowed")
    if _is_cancelled(promise):
        leaves = [schedule for schedule in promise.schedules if not schedule.children and schedule.close_reason == "CANCELLED"]
        for schedule in leaves:
            schedule.close_reason = None
            schedule.closed_at = None
            _sync_schedule(schedule)
    elif display in {models.PromiseDisplayState.WRITTEN_OFF, models.PromiseDisplayState.SETTLED}:
        for write_off in promise.write_offs:
            if write_off.reversed_at is None:
                write_off.reversed_at = datetime.now(timezone.utc)
                write_off.reversal_note = "Expected inflow reopened"
        for schedule in promise.schedules:
            if not schedule.children and schedule.close_reason == "WRITTEN_OFF":
                schedule.close_reason = None
                schedule.closed_at = None
                _sync_schedule(schedule)
    else:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="expected_inflow.reopen_not_allowed")
    _sync_promise(promise)


def reconcile_promise(promise: models.ExpectedInflowPromise) -> None:
    for schedule in promise.schedules:
        if schedule.close_reason not in {"RESCHEDULED", "CANCELLED"}:
            _sync_schedule(schedule)
    _sync_promise(promise)


def delete_promise(db: Session, promise: models.ExpectedInflowPromise) -> None:
    if not promise_is_pristine(promise):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="expected_inflow.delete_locked")
    db.delete(promise)
