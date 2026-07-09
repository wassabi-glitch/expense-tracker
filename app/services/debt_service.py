"""Compatibility re-export shim — see ``app.domains.debt`` for the canonical
implementation.

This file exists so that existing ``from app.services.debt_service
import ...`` statements continue to work during the package transition.
"""

from app.domains.debt import (
    LOCKED_DEBT_STATUSES,
    POSTED_DEBT_LEDGER_STATUS,
    create_debt_ledger_entry,
    get_debt_total_charges,
    get_debt_total_charges_by_debt_ids,
    get_debt_total_paid,
    get_debt_total_paid_by_debt_ids,
    reconcile_debt,
    reverse_debt_transaction_ledger,
    reverse_wallet_effect,
)

__all__ = [
    "POSTED_DEBT_LEDGER_STATUS",
    "LOCKED_DEBT_STATUSES",
    "create_debt_ledger_entry",
    "get_debt_total_charges",
    "get_debt_total_charges_by_debt_ids",
    "get_debt_total_paid",
    "get_debt_total_paid_by_debt_ids",
    "reconcile_debt",
    "reverse_debt_transaction_ledger",
    "reverse_wallet_effect",
]
