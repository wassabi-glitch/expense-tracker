"""Compatibility re-export shim — see ``app.domains.ledger`` for the canonical
implementation.

This file exists so that existing ``from app.services.financial_event_ledger_service
import ...`` statements continue to work during the package transition.
"""

from app.domains.ledger import (
    PostEntityLeg,
    PostWalletLeg,
    post_financial_event,
    validate_wallet_epochs,
    void_financial_event,
)

__all__ = [
    "post_financial_event",
    "void_financial_event",
    "validate_wallet_epochs",
    "PostWalletLeg",
    "PostEntityLeg",
]
