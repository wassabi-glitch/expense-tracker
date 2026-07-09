"""Compatibility re-export shim — see ``app.domains.budget_permission`` for the
canonical implementation.

This file exists so that existing ``from app.services.budget_permission_service
import ...`` statements continue to work during the package transition.
"""

from app.domains.budget_permission import (
    BudgetPermissionRequest,
    BudgetPermissionResult,
    check_budget_permission,
)

__all__ = [
    "check_budget_permission",
    "BudgetPermissionRequest",
    "BudgetPermissionResult",
]
