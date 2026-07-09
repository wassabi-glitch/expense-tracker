"""Financial Event Ledger — low-level immutable money event construction.

This module is the lower seam for creating, linking, voiding, and reversing
Financial Events.  It handles the mechanical work of writing the three-pile
ledger (FinancialEvent → WalletLedger → EntityLedger) and adjusting wallet
balances atomically.

It does **not** enforce business rules such as:
- Budget permission (budget_required, monthly limits)
- Category validation (real-expense-category checks)
- Goal protection (wallet goal-funding protection)
- Project rules (isolated project, overlay project)
- Timezone-aware date validation (future dates)
- Budget chain recomputation

Those invariants belong in the higher-level Expense Posting service or in
the domain service that calls into this module.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app import models
from app.services.wallet_service import WalletService
from app.services.wallet_value_service import classify_outflow
from app.timezone import today_in_tz


# ---------------------------------------------------------------------------
# Domain exceptions
# ---------------------------------------------------------------------------


class LedgerError(Exception):
    """Base exception for ledger-domain invariants.

    Callers in the web layer can catch this and translate to an HTTPException.
    """

    def __init__(self, detail: str | dict[str, Any]) -> None:
        self.detail = detail
        super().__init__(detail if isinstance(detail, str) else detail.get("code", ""))


class EventNotPostedError(LedgerError):
    """Raised when an operation requires a POSTED event but the event has
    already been voided or is itself a reversal."""


class WalletEpochError(LedgerError):
    """Raised when a money-movement date is before the relevant wallet's
    creation date.

    The *detail* dict carries ``code``, ``wallet_id``, ``wallet_name``,
    ``wallet_epoch``, ``requested_date``, and ``message``.
    """


# ---------------------------------------------------------------------------
# Request data-classes
# ---------------------------------------------------------------------------


@dataclass
class PostWalletLeg:
    """A single wallet-leg line to write to the Wallet Ledger.

    For expense outflows the funding classification (owned vs borrowed) is
    computed automatically at posting time.  Callers may override it by setting
    *owned_spend_amount* / *borrowed_spend_amount* explicitly.
    """

    wallet_id: int
    amount: int  # negative = outflow, positive = inflow
    owned_spend_amount: int | None = None
    borrowed_spend_amount: int | None = None


@dataclass
class PostEntityLeg:
    """A single entity-leg line to write to the Entity Ledger."""

    label: str | None = None
    amount: int = 0
    original_amount: int | None = None
    category: models.ExpenseCategory | None = None
    budget_id: int | None = None
    subcategory_id: int | None = None
    project_id: int | None = None
    project_subcategory_id: int | None = None
    debt_id: int | None = None
    payment_plan_id: int | None = None
    payment_plan_payment_id: int | None = None
    income_source_id: int | None = None


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _is_bypass_category(category: models.ExpenseCategory | None) -> bool:
    if category is None:
        return False
    return category == models.ExpenseCategory.BANK_FEES_INTEREST


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def post_financial_event(
    db: Session,
    *,
    owner_id: int,
    title: str,
    event_type: models.TransactionType,
    date: date,
    status: models.FinancialEventStatus = models.FinancialEventStatus.POSTED,
    description: str | None = None,
    reference_type: str | None = None,
    is_session: bool = False,
    discount_amount: int | None = None,
    linked_event_id: int | None = None,
    reverses_event_id: int | None = None,
    entity_category: models.ExpenseCategory | None = None,
    wallet_legs: list[PostWalletLeg],
    entity_legs: list[PostEntityLeg],
) -> models.FinancialEvent:
    """Create a posted FinancialEvent with wallet and entity ledger entries.

    This is the low-level immutable event construction seam.  It:

    - Classifies expense outflows into owned / borrowed funding
    - Adjusts wallet balances
    - Creates the FinancialEvent row
    - Writes WalletLedger rows
    - Writes EntityLedger rows

    It does **not** validate business rules — callers are responsible for
    ensuring budget permission, goal protection, project rules, category
    validity, and timezone-aware dates are correct before calling.

    Parameters
    ----------
    entity_category:
        Used to decide whether the wallet-balance floor should be bypassed
        (BANK_FEES_INTEREST).  Not persisted by this function — the category
        on each entity leg controls the Entity Ledger link.
    """
    if not wallet_legs:
        raise ValueError("post_financial_event requires at least one wallet leg")
    if not entity_legs:
        raise ValueError("post_financial_event requires at least one entity leg")

    is_bypass = _is_bypass_category(entity_category)

    # ---- 1. FinancialEvent (Pile 1) ----------------------------------------
    event = models.FinancialEvent(
        owner_id=owner_id,
        title=title,
        description=description,
        event_type=event_type,
        status=status,
        reference_type=reference_type,
        is_session=is_session,
        discount_amount=discount_amount,
        linked_event_id=linked_event_id,
        reverses_event_id=reverses_event_id,
        date=date,
    )
    db.add(event)
    db.flush()

    # ---- 2. WalletLedger (Pile 2) + balance adjustment ---------------------
    for leg in wallet_legs:
        is_outflow = leg.amount < 0
        funding = None

        if is_outflow and event_type == models.TransactionType.EXPENSE:
            # Snapshot funding substance *before* balance changes.
            wallet_before = (
                db.query(models.Wallet)
                .filter(models.Wallet.id == leg.wallet_id)
                .with_for_update()
                .first()
            )
            if wallet_before is not None:
                funding = classify_outflow(wallet_before, abs(int(leg.amount)))

        WalletService.adjust_balance(
            db,
            leg.wallet_id,
            int(leg.amount),
            event_type,
            is_bypass=is_bypass,
        )

        db.add(
            models.WalletLedger(
                owner_id=owner_id,
                event_id=event.id,
                wallet_id=leg.wallet_id,
                amount=int(leg.amount),
                owned_spend_amount=(
                    funding.owned_amount
                    if funding is not None
                    else leg.owned_spend_amount
                ),
                borrowed_spend_amount=(
                    funding.borrowed_amount
                    if funding is not None
                    else leg.borrowed_spend_amount
                ),
            )
        )

    # ---- 3. EntityLedger (Pile 3) -------------------------------------------
    for leg in entity_legs:
        db.add(
            models.EntityLedger(
                event_id=event.id,
                label=leg.label,
                amount=int(leg.amount),
                original_amount=(
                    int(leg.original_amount)
                    if leg.original_amount is not None
                    else None
                ),
                category=leg.category,
                budget_id=leg.budget_id,
                subcategory_id=leg.subcategory_id,
                project_id=leg.project_id,
                project_subcategory_id=leg.project_subcategory_id,
                debt_id=leg.debt_id,
                payment_plan_id=leg.payment_plan_id,
                payment_plan_payment_id=leg.payment_plan_payment_id,
                income_source_id=leg.income_source_id,
            )
        )

    db.flush()
    return event


# ---------------------------------------------------------------------------
# Void / reversal
# ---------------------------------------------------------------------------


def void_financial_event(
    db: Session,
    *,
    event: models.FinancialEvent,
    owner_id: int,
    user_tz: tzinfo,
    void_reason: str = "Deleted by user",
) -> models.FinancialEvent:
    """Void a posted FinancialEvent by creating a counter-balancing reversal.

    This is the **single shared application-level seam** for voiding posted
    financial events.  It preserves the original event, creates a linked
    REVERSAL event with counter-balancing wallet and entity ledger legs, and
    marks the original as VOIDED.

    Callers are responsible for any domain-specific pre-checks (session
    eligibility, refund/asset/dependency locks, archived-wallet checks, etc.).

    Returns the newly created reversal FinancialEvent.

    Raises
    ------
    EventNotPostedError
        If *event* is not in POSTED status (second void attempt).
    """
    if event.status != models.FinancialEventStatus.POSTED:
        raise EventNotPostedError("ledger.event_not_posted")

    void_date = today_in_tz(user_tz)

    # Build counter-balancing wallet legs (negate every amount)
    reversal_wallet_legs: list[PostWalletLeg] = []
    for leg in event.wallet_legs:
        reversal_wallet_legs.append(
            PostWalletLeg(
                wallet_id=leg.wallet_id,
                amount=-int(leg.amount),
            )
        )

    # Build counter-balancing entity legs (negate amounts, preserve links)
    reversal_entity_legs: list[PostEntityLeg] = []
    for leg in event.entity_legs:
        reversal_entity_legs.append(
            PostEntityLeg(
                label=leg.label,
                amount=-int(leg.amount),
                original_amount=(
                    -int(leg.original_amount)
                    if leg.original_amount is not None
                    else None
                ),
                category=leg.category,
                budget_id=leg.budget_id,
                subcategory_id=leg.subcategory_id,
                project_id=leg.project_id,
                project_subcategory_id=leg.project_subcategory_id,
                debt_id=leg.debt_id,
                payment_plan_id=leg.payment_plan_id,
                payment_plan_payment_id=leg.payment_plan_payment_id,
                income_source_id=leg.income_source_id,
            )
        )

    reversal = post_financial_event(
        db,
        owner_id=owner_id,
        title=f"Void {event.title}",
        event_type=event.event_type,
        date=void_date,
        status=models.FinancialEventStatus.REVERSAL,
        description=f"Reversal for voided {event.event_type.value.lower()} #{event.id}",
        reference_type=models.ReferenceType.VOID_REVERSAL,
        linked_event_id=event.id,
        reverses_event_id=event.id,
        entity_category=None,
        wallet_legs=reversal_wallet_legs,
        entity_legs=reversal_entity_legs,
    )

    event.status = models.FinancialEventStatus.VOIDED
    event.voided_at = datetime.now(timezone.utc)
    event.void_reason = void_reason
    event.void_reversal_event_id = reversal.id

    return reversal


# ---------------------------------------------------------------------------
# Wallet epoch validation
# ---------------------------------------------------------------------------


def validate_wallet_epochs(
    db: Session,
    *,
    wallet_ids: set[int],
    event_date: date,
) -> None:
    """Validate that *event_date* is not before any wallet's creation date.

    Wallet epochs are per-wallet: each wallet's ``created_at`` date is the
    earliest allowed date for money movement touching that wallet.  Same-day
    activity is allowed.

    Raises
    ------
    WalletEpochError
        If any wallet's epoch is after *event_date*, with a user-facing
        message that names the wallet and explains the boundary.
    """
    if not wallet_ids:
        return

    wallets = (
        db.query(models.Wallet)
        .filter(models.Wallet.id.in_(wallet_ids))
        .all()
    )

    for wallet in wallets:
        if wallet.created_at is None:
            continue
        wallet_epoch = wallet.created_at.date()
        if event_date < wallet_epoch:
            raise WalletEpochError({
                "code": "wallets.date_before_epoch",
                "wallet_id": wallet.id,
                "wallet_name": wallet.name,
                "wallet_epoch": wallet_epoch.isoformat(),
                "requested_date": event_date.isoformat(),
                "message": (
                    f"The date {event_date.isoformat()} is before "
                    f"wallet '{wallet.name}' started tracking on "
                    f"{wallet_epoch.isoformat()}. "
                    f"Same-day activity is allowed."
                ),
            })
