"""Budget Reporting domain — read-time budget display.

Owns budget chain computation, month summaries, project budget views,
and budget-related display/output functions.

This package is the **display-time read interface**.  Write-time spending
permission belongs to ``app.domains.budget_permission``.

Public API
----------
All public symbols from ``_budget_service`` are re-exported, including:

- ``compute_budget_chain`` — compute the budget chain for a set of budgets
- ``build_budget_out`` — build the display output for a single budget
- ``materialize_budget_for_month`` — create a Budget row for a given month
- ``recompute_budget_chain`` — recompute the chain after a posting event
- ``validate_budget_limit`` — validate monthly budget limit
- ``validate_subcategory_limit`` — validate subcategory-level budget limit
- ``validate_project_budget`` — validate project budget constraints
- ``get_budget_spent_amount`` — get total spent amount for a budget
- ``month_bounds`` — compute month start/end dates
"""

from app.domains.budget_reporting._budget_service import *  # noqa: F401,F403
from app.domains.budget_reporting._budget_service import _signed_expense_amount  # private but imported externally
