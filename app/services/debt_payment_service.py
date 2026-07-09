"""Compatibility re-export shim — see ``app.domains.debt`` for the canonical
implementation.

This file exists so that existing ``from app.services.debt_payment_service
import ...`` statements continue to work during the package transition.
"""

from app.domains.debt import (
    build_debt_transaction_out,
    create_debt_payment,
)

__all__ = [
    "build_debt_transaction_out",
    "create_debt_payment",
]
