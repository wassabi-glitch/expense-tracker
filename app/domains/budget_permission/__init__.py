"""Budget Permission domain — write-time spending permission.

This package answers one question: "Is this proposed spend allowed to hit
this Budget category this month?"  It is the write-time permission interface
that money-posting callers depend on.

It does **not** own Budget Month Summary or Project Budget View — those
belong to ``app.domains.budget_reporting``.

Public API
----------
- ``check_budget_permission`` — validate spend-time Budget Permission rules
- ``BudgetPermissionRequest`` — input dataclass for the permission check
- ``BudgetPermissionResult`` — outcome dataclass with resolved budget row
"""

from app.domains.budget_permission._permission_service import (
    BudgetPermissionRequest,
    BudgetPermissionResult,
    check_budget_permission,
)

__all__ = [
    "check_budget_permission",
    "BudgetPermissionRequest",
    "BudgetPermissionResult",
]
