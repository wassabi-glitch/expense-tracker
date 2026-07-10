"""Ledger domain — immutable double-entry Financial Event records.

This package is a leaf in the domain dependency graph.  It owns the
low-level recording engine and has no domain dependencies of its own.

Public API
----------
- ``post_financial_event`` — create a posted FinancialEvent with wallet
  and entity ledger entries
- ``void_financial_event`` — void a posted FinancialEvent by creating a
  counter-balancing reversal (shared application-level seam)
- ``validate_wallet_epochs`` — enforce per-wallet epoch boundaries for
  money movement
- ``verify_wallet_projection`` — check that a wallet's balance matches
  its WalletLedger entries
- ``verify_all_wallet_projections`` — check all active wallets for an owner
- ``PostWalletLeg`` — a single wallet-leg line for the Wallet Ledger
- ``PostEntityLeg`` — a single entity-leg line for the Entity Ledger
- ``WalletProjection`` — dataclass returned by projection verification
"""

from app.domains.ledger._ledger_service import (
    EventNotPostedError,
    LedgerError,
    PostEntityLeg,
    PostWalletLeg,
    WalletEpochError,
    WalletProjection,
    post_financial_event,
    validate_wallet_epochs,
    verify_all_wallet_projections,
    verify_wallet_projection,
    void_financial_event,
)

__all__ = [
    "post_financial_event",
    "void_financial_event",
    "validate_wallet_epochs",
    "verify_wallet_projection",
    "verify_all_wallet_projections",
    "PostWalletLeg",
    "PostEntityLeg",
    "WalletProjection",
    "LedgerError",
    "EventNotPostedError",
    "WalletEpochError",
]
