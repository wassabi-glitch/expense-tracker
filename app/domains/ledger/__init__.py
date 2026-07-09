"""Ledger domain — immutable double-entry Financial Event records.

This package is a leaf in the domain dependency graph.  It owns the
low-level recording engine and has no domain dependencies of its own.

Public API
----------
- ``post_financial_event`` — create a posted FinancialEvent with wallet
  and entity ledger entries
- ``PostWalletLeg`` — a single wallet-leg line for the Wallet Ledger
- ``PostEntityLeg`` — a single entity-leg line for the Entity Ledger
"""

from app.domains.ledger._ledger_service import (
    PostEntityLeg,
    PostWalletLeg,
    post_financial_event,
)

__all__ = [
    "post_financial_event",
    "PostWalletLeg",
    "PostEntityLeg",
]
