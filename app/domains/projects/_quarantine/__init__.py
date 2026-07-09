"""Frozen Isolated Project quarantine — compatibility surface only.

.. warning::

   **ADR-0022 IS ACTIVE.**  Isolated Projects and Fund Project work are
   FROZEN.  This module exposes the narrow compatibility surface that stable
   core modules are allowed to use.  Do NOT add new exports, new callers, or
   new isolated project behavior.

   See ``_contract.py`` for the full contract and ``docs/adr/0022-*.md``
   for the freeze decision.

Import Rule
-----------
Stable core modules (posting, budget_permission, budget_reporting, etc.)
import ONLY from this ``__init__.py`` — never from ``app.services.isolated_project_service``
directly.
"""

# ---------------------------------------------------------------------------
# Compatibility queries — read-only, stable core approved
# ---------------------------------------------------------------------------

from app.services.project_service import is_isolated_project  # noqa: F401

from app.services.isolated_project_service import (  # noqa: F401
    # Wallet-level allocation queries
    get_wallet_project_allocated_amount,
    get_project_wallet_allocated_amount,
    get_wallet_free_to_allocate_for_projects,
    # Project-level funding queries
    get_project_funding_limit,
    get_project_category_allocated_amount,
    get_project_unallocated_funding_amount,
    # Spending queries
    get_isolated_project_category_spent_amount,
    get_isolated_project_subcategory_spent_amount,
    get_isolated_project_total_spent,
    # Validation helpers
    validate_project_limit_sum,
    validate_isolated_project_category_allocation_covers_spending,
    # Serialization helpers
    project_wallet_allocations_out,
)

# ---------------------------------------------------------------------------
# Frozen write operations — existing route compatibility only
# ---------------------------------------------------------------------------
#
# These are re-exported for the existing projects router.  Do NOT add new
# callers.  Do NOT extend their behavior.
#

from app.services.isolated_project_service import (  # noqa: F401, E402
    apply_isolated_project_top_up,
    apply_isolated_project_category_allocation,
    apply_isolated_project_subcategory_allocation,
    apply_isolated_project_rebalance,
    sweep_isolated_project_wallet_allocations,
    validate_project_wallet_allocations,
    get_isolated_project_wrap_up_summary,
    get_isolated_project_total_top_ups,
)

__all__ = [
    # Compatibility queries
    "is_isolated_project",
    "get_wallet_project_allocated_amount",
    "get_project_wallet_allocated_amount",
    "get_wallet_free_to_allocate_for_projects",
    "get_project_funding_limit",
    "get_project_category_allocated_amount",
    "get_project_unallocated_funding_amount",
    "get_isolated_project_category_spent_amount",
    "get_isolated_project_subcategory_spent_amount",
    "get_isolated_project_total_spent",
    "validate_project_limit_sum",
    "validate_isolated_project_category_allocation_covers_spending",
    "project_wallet_allocations_out",
    # Frozen write operations
    "apply_isolated_project_top_up",
    "apply_isolated_project_category_allocation",
    "apply_isolated_project_subcategory_allocation",
    "apply_isolated_project_rebalance",
    "sweep_isolated_project_wallet_allocations",
    "validate_project_wallet_allocations",
    "get_isolated_project_wrap_up_summary",
    "get_isolated_project_total_top_ups",
]
