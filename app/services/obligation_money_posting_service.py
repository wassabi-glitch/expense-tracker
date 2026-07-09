"""Obligation Money Posting — shared money-mechanic delegation for Debt and
Payment Plan flows.

This module is the **narrow delegation point** where Debt and Payment Plan
domain modules hand off shared money mechanics without coupling Debt and
Payment Plan into one entity.

Domain separation rule (the "no-merge" contract)
-------------------------------------------------
- **Debt domain** OWNS Debt rules: principal/charge split, running balance,
  receivable/payable direction, Dual Path classification, Debt Ledger entries,
  and Debt lifecycle (active → closed / overdue / defaulted / archived).
- **Payment Plan domain** OWNS Payment Plan rules: schedule rows, waterfall
  spillover, charge/premium rows, row statuses, Payment Plan Ledger entries,
  imported-path behaviour, and Payment Plan lifecycle.
- **This seam** OWNS shared money mechanics: Financial Event creation, Wallet
  Ledger entries, Entity Ledger links, Budget Permission checks (via the
  Budget Permission seam), wallet balance adjustment, and user-local date
  propagation.

What this module MUST NOT do
-----------------------------
- Introduce a generic "Obligation" table or enum value.
- Merge Debt and Payment Plan lifecycle, status, or persistence.
- Own Debt-specific or Payment Plan-specific domain logic.
- Bypass the Financial Event Ledger or Expense Posting seams.

Callers
-------
- ``debt_payment_service`` — for Debt payment / charge / settlement events.
- Payment Plan route adapter — for Payment Plan charge / payment events.

Implementation note
-------------------
At the time of writing (Issue 5 of PRD 2), the Payment Plan charge flow
already routes through ``post_expense_event``, and the Debt expense-shaped
flow already routes through the same seam.  This module provides the
explicit delegation point for **non-expense** obligation events (e.g. Debt
settlement / income events) so that those events also go through the
low-level ``post_financial_event`` seam instead of constructing
FinancialEvent / WalletLedger / EntityLedger rows manually.
"""

from __future__ import annotations

from datetime import date

from sqlalchemy.orm import Session

from app import models
from app.services.financial_event_ledger_service import (
    PostEntityLeg,
    PostWalletLeg,
    post_financial_event,
)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def post_obligation_event(
    db: Session,
    *,
    owner_id: int,
    title: str,
    event_type: models.TransactionType,
    date: date,
    description: str | None = None,
    reference_type: str | None = None,
    entity_category: models.ExpenseCategory | None = None,
    wallet_legs: list[PostWalletLeg],
    entity_legs: list[PostEntityLeg],
) -> models.FinancialEvent:
    """Create a posted FinancialEvent for an obligation (Debt or Payment Plan)
    money event through the shared Financial Event Ledger seam.

    This is a thin delegation wrapper.  It does **not** enforce:

    - Budget Permission (callers must check that separately via
      ``check_budget_permission`` before calling this function).
    - Domain-specific rules (Debt or Payment Plan modules must decide what
      the action means before calling this function).

    Parameters
    ----------
    entity_category:
        Forwarded to ``post_financial_event`` to control wallet-balance
        floor bypass (BANK_FEES_INTEREST).  For Debt settlements and
        income-type events this is typically ``None``.
    """
    return post_financial_event(
        db,
        owner_id=owner_id,
        title=title,
        event_type=event_type,
        date=date,
        description=description,
        reference_type=reference_type,
        entity_category=entity_category,
        wallet_legs=wallet_legs,
        entity_legs=entity_legs,
    )
