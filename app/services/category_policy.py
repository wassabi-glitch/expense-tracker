"""Compatibility re-export shim — see ``app.domains.posting`` for the canonical
implementation.

This file exists so that existing ``from app.services.category_policy
import ...`` statements continue to work during the package transition.
"""

from app.domains.posting import (
    validate_active_expense_category,
)

__all__ = [
    "validate_active_expense_category",
]
