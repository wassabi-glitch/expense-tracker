from datetime import date

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app import models, schemas
from app.domains.debt._debt_service import POSTED_DEBT_LEDGER_STATUS, create_debt_ledger_entry
from app.domains.ledger._ledger_service import (
    PostEntityLeg,
    PostWalletLeg,
    post_financial_event,
)
from app.services.goal_funding_service import validate_wallet_goal_protection_for_outflow
from app.utils import check_budget_alerts


def _get_owned_wallet_or_404(db: Session, user_id: int, wallet_id: int) -> models.Wallet:
    wallet = (
        db.query(models.Wallet)
        .filter(models.Wallet.id == wallet_id, models.Wallet.owner_id == user_id)
        .first()
    )
    if wallet is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="wallets.not_found")
    return wallet


def build_debt_transaction_out(transaction: models.DebtTransaction) -> schemas.DebtTransactionOut:
    wallet = schemas.WalletOut.model_validate(transaction.wallet) if transaction.wallet else None
    wallet_allocations = [
        schemas.DebtTransactionWalletAllocationOut.model_validate(allocation)
        for allocation in (transaction.wallet_allocations or [])
    ]
    return schemas.DebtTransactionOut(
        id=transaction.id,
        owner_id=transaction.owner_id,
        debt_id=transaction.debt_id,
        amount=int(transaction.amount),
        date=transaction.date,
        note=transaction.note,
        wallet_id=transaction.wallet_id,
        created_at=transaction.created_at,
        wallet=wallet,
        wallet_allocations=wallet_allocations,
    )


def _debt_txn_marker(transaction_id: int) -> str:
    return f"[debt_txn:{transaction_id}]"


def _append_marker(description: str, marker: str) -> str:
    return f"{description} {marker}".strip()


def posted_charge_balance(db: Session, debt_id: int) -> int:
    return int(
        db.query(func.coalesce(func.sum(models.DebtLedgerEntry.charge_delta), 0))
        .filter(
            models.DebtLedgerEntry.debt_id == debt_id,
            models.DebtLedgerEntry.status == POSTED_DEBT_LEDGER_STATUS,
        )
        .scalar()
        or 0
    )


def split_amount_between_charges_and_principal(
    db: Session,
    debt: models.Debt,
    amount: int,
) -> tuple[int, int]:
    charge_balance = posted_charge_balance(db, debt.id)
    principal_balance = max(0, int(debt.remaining_amount or 0) - int(charge_balance))
    principal_amount = min(int(amount), int(principal_balance))
    charge_amount = int(amount) - principal_amount
    return principal_amount, charge_amount


def _validate_payment_wallet_allocations(
    db: Session,
    debt: models.Debt,
    allocations: list[schemas.DebtTransactionWalletAllocationIn],
    expected_total: int,
    *,
    enforce_goal_protection: bool,
) -> list[tuple[models.Wallet, int]]:
    if expected_total <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="debts.payment.amount_required")
    if not allocations:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="debts.payment.wallet_allocations_required")

    total = sum(int(item.amount) for item in allocations)
    if total != int(expected_total):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="debts.payment.wallet_total_mismatch")

    seen_wallet_ids: set[int] = set()
    validated: list[tuple[models.Wallet, int]] = []
    is_outflow = debt.debt_type == models.DebtType.OWING
    for allocation in allocations:
        if allocation.wallet_id in seen_wallet_ids:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="debts.payment.wallet_duplicate")
        seen_wallet_ids.add(allocation.wallet_id)
        wallet = _get_owned_wallet_or_404(db, debt.owner_id, allocation.wallet_id)
        if not wallet.is_active:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="wallets.archived_locked")
        if is_outflow and enforce_goal_protection:
            validate_wallet_goal_protection_for_outflow(
                db,
                debt.owner_id,
                wallet,
                int(allocation.amount),
                outflow_type="debt_payment",
                error_code="wallets.goal_protection_conflict",
            )
        validated.append((wallet, int(allocation.amount)))
    return validated


def _payment_direction_multiplier(debt: models.Debt) -> int:
    return 1 if debt.debt_type == models.DebtType.OWED else -1


def _principal_payment_event_classification(
    debt: models.Debt,
    income_source_id: int | None = None,
) -> tuple[models.TransactionType, models.ExpenseCategory | None, int | None, str | None]:
    transaction_type = models.TransactionType.DEBT_SETTLEMENT
    category = None
    effective_income_source_id = None
    reference_type = models.ReferenceType.DEBT_REPAYMENT

    if not debt.is_money_transferred:
        if debt.origin_kind == models.DebtOriginKind.DAMAGE_COMPENSATION:
            reference_type = models.ReferenceType.DAMAGE_COMPENSATION
            if debt.debt_type == models.DebtType.OWING:
                transaction_type = models.TransactionType.EXPENSE
                category = debt.expense_category
        elif debt.expense_category and debt.debt_type == models.DebtType.OWING:
            transaction_type = models.TransactionType.EXPENSE
            category = debt.expense_category
            reference_type = models.ReferenceType.DEBT_EXPENSE
        elif debt.income_source_id and debt.debt_type == models.DebtType.OWED:
            transaction_type = models.TransactionType.INCOME
            effective_income_source_id = income_source_id or debt.income_source_id
            reference_type = models.ReferenceType.DEBT_INCOME

    return transaction_type, category, effective_income_source_id, reference_type


def _charge_payment_event_classification(
    debt: models.Debt,
    income_source_id: int | None = None,
) -> tuple[models.TransactionType, models.ExpenseCategory | None, int | None, str]:
    if debt.debt_type == models.DebtType.OWING:
        return (
            models.TransactionType.EXPENSE,
            models.ExpenseCategory.DEBT_CHARGES,
            None,
            models.ReferenceType.DEBT_CHARGE,
        )
    return (
        models.TransactionType.INCOME,
        None,
        income_source_id or debt.income_source_id,
        models.ReferenceType.DEBT_CHARGE,
    )


def _split_wallet_allocations_principal_first(
    allocations: list[tuple[models.Wallet, int]],
    *,
    principal_amount: int,
    charge_amount: int,
) -> tuple[list[tuple[models.Wallet, int]], list[tuple[models.Wallet, int]]]:
    principal_remaining = int(principal_amount)
    charge_remaining = int(charge_amount)
    principal_allocations: list[tuple[models.Wallet, int]] = []
    charge_allocations: list[tuple[models.Wallet, int]] = []

    for wallet, allocation_amount in allocations:
        remaining = int(allocation_amount)
        if principal_remaining > 0:
            principal_part = min(remaining, principal_remaining)
            if principal_part > 0:
                principal_allocations.append((wallet, principal_part))
                remaining -= principal_part
                principal_remaining -= principal_part

        if remaining > 0 and charge_remaining > 0:
            charge_part = min(remaining, charge_remaining)
            if charge_part > 0:
                charge_allocations.append((wallet, charge_part))
                charge_remaining -= charge_part

    if principal_remaining != 0 or charge_remaining != 0:
        raise ValueError("debts.payment.wallet_component_allocation_mismatch")

    return principal_allocations, charge_allocations


def _record_wallet_allocated_debt_event(
    db: Session,
    debt: models.Debt,
    debt_transaction: models.DebtTransaction,
    allocations: list[tuple[models.Wallet, int]],
    *,
    transaction_type: models.TransactionType,
    reference_type: str,
    category: models.ExpenseCategory | None,
    income_source_id: int | None,
    description_suffix: str | None = None,
) -> models.FinancialEvent:
    direction_mult = _payment_direction_multiplier(debt)
    description = debt_transaction.note or f"Payment for {debt.counterparty_name}"
    if description_suffix:
        description = f"{description} - {description_suffix}"
    description = _append_marker(description, _debt_txn_marker(debt_transaction.id))
    event_amount = sum(int(allocation_amount) for _, allocation_amount in allocations)

    if transaction_type == models.TransactionType.EXPENSE:
        if category is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="expenses.category_required")
        use_debt_planning_links = category == debt.expense_category
        from app.domains.posting._posting_service import post_expense_event  # lazy — avoids circular import
        posted = post_expense_event(
            db,
            debt.owner_id,
            title=f"{debt.counterparty_name}"[:32],
            amount=int(event_amount),
            category=category,
            expense_date=debt_transaction.date,
            description=description,
            wallet_allocations=[
                {"wallet_id": wallet.id, "amount": int(allocation_amount)}
                for wallet, allocation_amount in allocations
            ],
            subcategory_id=debt.expense_subcategory_id if use_debt_planning_links else None,
            project_id=debt.project_id if use_debt_planning_links else None,
            project_subcategory_id=debt.project_subcategory_id if use_debt_planning_links else None,
            reference_type=reference_type,
            enforce_goal_protection=False,
            debt_id=debt.id,
        )
        check_budget_alerts(db, posted.budget)
        return posted.event

    # Route non-expense obligation events through the shared Financial Event
    # Ledger seam so that Wallet Ledger, Entity Ledger, and balance adjustment
    # all go through the canonical immutable event path.
    wallet_legs: list[PostWalletLeg] = []
    for wallet, allocation_amount in allocations:
        signed_amount = int(allocation_amount) * direction_mult
        wallet_legs.append(
            PostWalletLeg(
                wallet_id=wallet.id,
                amount=signed_amount,
            )
        )

    entity_legs: list[PostEntityLeg] = [
        PostEntityLeg(
            label=debt_transaction.note,
            amount=int(event_amount),
            category=category,
            subcategory_id=debt.expense_subcategory_id if category else None,
            project_id=debt.project_id if category else None,
            project_subcategory_id=debt.project_subcategory_id if category else None,
            debt_id=debt.id,
            income_source_id=income_source_id,
        )
    ]

    return post_financial_event(
        db,
        owner_id=debt.owner_id,
        # Ticket 4: Use the user's receipt note as the primary Money In title.
        # Counterparty name stays available as supporting context in description
        # and entity_legs, not as the primary title.
        title=(debt_transaction.note or "Debt payment received")[:100],
        event_type=transaction_type,
        date=debt_transaction.date,
        description=description,
        reference_type=reference_type,
        entity_category=category,
        wallet_legs=wallet_legs,
        entity_legs=entity_legs,
    )


def _record_debt_payment_financial_events(
    db: Session,
    debt: models.Debt,
    debt_transaction: models.DebtTransaction,
    allocations: list[tuple[models.Wallet, int]],
    *,
    principal_amount: int,
    charge_amount: int,
    income_source_id: int | None = None,
) -> dict[str, models.FinancialEvent]:
    principal_allocations, charge_allocations = _split_wallet_allocations_principal_first(
        allocations,
        principal_amount=principal_amount,
        charge_amount=charge_amount,
    )
    events: dict[str, models.FinancialEvent] = {}

    if principal_allocations:
        transaction_type, category, effective_income_source_id, reference_type = _principal_payment_event_classification(
            debt,
            income_source_id=income_source_id,
        )
        events["principal"] = _record_wallet_allocated_debt_event(
            db,
            debt,
            debt_transaction,
            principal_allocations,
            transaction_type=transaction_type,
            reference_type=reference_type,
            category=category,
            income_source_id=effective_income_source_id,
            description_suffix="principal",
        )

    if charge_allocations:
        transaction_type, category, effective_income_source_id, reference_type = _charge_payment_event_classification(
            debt,
            income_source_id=income_source_id,
        )
        events["charge"] = _record_wallet_allocated_debt_event(
            db,
            debt,
            debt_transaction,
            charge_allocations,
            transaction_type=transaction_type,
            reference_type=reference_type,
            category=category,
            income_source_id=effective_income_source_id,
            description_suffix="charge",
        )

    return events


def create_debt_payment(
    db: Session,
    debt: models.Debt,
    *,
    amount: int,
    transaction_date: date,
    wallet_allocations: list[schemas.DebtTransactionWalletAllocationIn],
    note: str | None = None,
    income_source_id: int | None = None,
    enforce_goal_protection: bool = True,
    principal_amount_override: int | None = None,
    charge_amount_override: int | None = None,
) -> tuple[models.DebtTransaction, models.DebtLedgerEntry]:
    debt = (
        db.query(models.Debt)
        .filter(models.Debt.id == debt.id, models.Debt.owner_id == debt.owner_id)
        .with_for_update()
        .first()
    )
    if not debt:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="debts.not_found")
    if int(debt.remaining_amount or 0) < int(amount):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="debts.transaction.amount_too_high")

    validated_allocations = _validate_payment_wallet_allocations(
        db,
        debt,
        wallet_allocations,
        amount,
        enforce_goal_protection=enforce_goal_protection,
    )
    primary_wallet = validated_allocations[0][0]
    debt_transaction = models.DebtTransaction(
        owner_id=debt.owner_id,
        wallet_id=primary_wallet.id,
        debt_id=debt.id,
        amount=int(amount),
        date=transaction_date,
        note=note,
    )
    db.add(debt_transaction)
    db.flush()

    for wallet, allocation_amount in validated_allocations:
        db.add(
            models.DebtTransactionWalletAllocation(
                owner_id=debt.owner_id,
                debt_id=debt.id,
                debt_transaction_id=debt_transaction.id,
                wallet_id=wallet.id,
                amount=int(allocation_amount),
            )
        )

    if principal_amount_override is None and charge_amount_override is None:
        principal_amount, charge_amount = split_amount_between_charges_and_principal(db, debt, amount)
    else:
        principal_amount = int(principal_amount_override or 0)
        charge_amount = int(charge_amount_override or 0)
        if principal_amount < 0 or charge_amount < 0 or principal_amount + charge_amount != int(amount):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="debts.payment.invalid_component_split")

        charge_balance = posted_charge_balance(db, debt.id)
        principal_balance = max(0, int(debt.remaining_amount or 0) - int(charge_balance))
        if principal_amount > principal_balance or charge_amount > charge_balance:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="debts.transaction.amount_too_high")

    payment_events = _record_debt_payment_financial_events(
        db,
        debt,
        debt_transaction,
        validated_allocations,
        principal_amount=principal_amount,
        charge_amount=charge_amount,
        income_source_id=income_source_id,
    )
    ledger_entries: list[models.DebtLedgerEntry] = []
    if principal_amount > 0:
        ledger_entries.append(
            create_debt_ledger_entry(
                db,
                owner_id=debt.owner_id,
                debt_id=debt.id,
                entry_type=models.DebtLedgerEntryType.PAYMENT,
                amount_delta=-int(principal_amount),
                principal_delta=-int(principal_amount),
                source_debt_transaction_id=debt_transaction.id,
                financial_event_id=payment_events.get("principal").id if payment_events.get("principal") else None,
                wallet_id=primary_wallet.id,
                event_subtype="PRINCIPAL_PAYMENT",
                entry_date=transaction_date,
                note=note or f"Payment for {debt.counterparty_name}",
            )
        )
    if charge_amount > 0:
        ledger_entries.append(
            create_debt_ledger_entry(
                db,
                owner_id=debt.owner_id,
                debt_id=debt.id,
                entry_type=models.DebtLedgerEntryType.PAYMENT,
                amount_delta=-int(charge_amount),
                charge_delta=-int(charge_amount),
                source_debt_transaction_id=debt_transaction.id,
                financial_event_id=payment_events.get("charge").id if payment_events.get("charge") else None,
                wallet_id=primary_wallet.id,
                event_subtype="CHARGE_PAYMENT",
                entry_date=transaction_date,
                note=note or f"Payment for {debt.counterparty_name}",
            )
        )
    if not ledger_entries:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="debts.payment.amount_required")
    return debt_transaction, ledger_entries[0]
