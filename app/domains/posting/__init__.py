"""Posting domain — expense posting orchestration.

Owns wallet allocation resolution, budget permission checks, goal protection,
subcategory/project link validation, and the ``post_expense_event`` service.

Public API
----------
- ``post_expense_event`` — the main expense posting orchestration function
- ``ExpensePostingResult`` — result dataclass returned by post_expense_event
- ``resolve_expense_wallet_allocations`` — resolve and validate wallet allocations
- ``validate_real_expense_category`` — ensure the category is a real expense category
- ``validate_active_expense_category`` — re-exported from category_policy
"""

from app.domains.posting._category_policy import (
    validate_active_expense_category,
)
from app.domains.posting._posting_service import (
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
    "validate_active_expense_category",
]
