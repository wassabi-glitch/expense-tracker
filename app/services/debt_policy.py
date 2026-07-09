"""Compatibility re-export shim — see ``app.domains.debt`` for the canonical
implementation.

This file exists so that existing ``from app.services.debt_policy
import ...`` statements continue to work during the package transition.
"""

from app.domains.debt import (
    DebtActionDecision,
    evaluate_debt_action,
    evaluate_debt_actions,
    evaluate_ledger_entry_reversal,
    is_archived_debt,
    is_closed_debt,
    is_formal_debt,
    is_informal_debt,
    is_open_debt,
    is_pristine_debt,
)

__all__ = [
    "DebtActionDecision",
    "evaluate_debt_action",
    "evaluate_debt_actions",
    "evaluate_ledger_entry_reversal",
    "is_archived_debt",
    "is_closed_debt",
    "is_formal_debt",
    "is_informal_debt",
    "is_open_debt",
    "is_pristine_debt",
]
