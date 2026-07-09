"""Compatibility re-export shim — see ``app.domains.posting`` for the canonical
implementation.

This file exists so that existing ``from app.services.expense_posting_service
import ...`` statements continue to work during the package transition.
"""

from app.domains.posting import (
    ExpensePostingResult,
    post_expense_event,
    resolve_expense_wallet_allocations,
    validate_real_expense_category,
)

__all__ = [
    "post_expense_event",
    "ExpensePostingResult",
    "resolve_expense_wallet_allocations",
    "validate_real_expense_category",
]
