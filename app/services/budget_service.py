"""Compatibility re-export shim — see ``app.domains.budget_reporting`` for the
canonical implementation.

This file exists so that existing ``from app.services.budget_service
import ...`` statements continue to work during the package transition.
"""

from app.domains.budget_reporting import *  # noqa: F401,F403
from app.domains.budget_reporting._budget_service import _signed_expense_amount  # private but imported externally
