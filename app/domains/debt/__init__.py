"""Debt domain — open-ended running-balance obligations.

Owns debt CRUD, charges, payments, ledger entries, reconciliation,
forgiveness, and policy decisions.

**Domain separation rule:** This package MUST NOT be merged with
``app.domains.payment_plans``.  Debt is an open-ended running-balance
obligation domain; Payment Plan is a scheduled obligation domain with
rows and waterfall behavior.  They share money-posting mechanics through
the Posting and Ledger seams but remain separate domains.

Public API
----------
Debt service:
- ``create_debt_ledger_entry`` — create a Debt Ledger entry
- ``reconcile_debt`` — reconcile a debt's remaining amount from the ledger
- ``get_debt_total_charges`` — total charges for a debt
- ``get_debt_total_paid`` — total paid for a debt
- ``reverse_wallet_effect`` — reverse wallet effects of a financial event
- ``reverse_debt_transaction_ledger`` — create reversal entries for a transaction

Debt payment service:
- ``create_debt_payment`` — create a debt payment with wallet allocation
- ``build_debt_transaction_out`` — build a DebtTransactionOut schema

Debt policy:
- ``evaluate_debt_action`` — evaluate if a debt action is allowed
- ``evaluate_debt_actions`` — evaluate all debt actions
- ``evaluate_ledger_entry_reversal`` — evaluate if a ledger entry can be reversed
- ``is_pristine_debt`` — check if a debt has no non-initial ledger entries
- ``is_formal_debt`` / ``is_informal_debt`` / ``is_open_debt`` / ``is_closed_debt``
"""

from app.domains.debt._debt_service import (
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
from app.domains.debt._payment_service import (
    build_debt_transaction_out,
    create_debt_payment,
)
from app.domains.debt._policy import (
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
    # debt_service
    "POSTED_DEBT_LEDGER_STATUS",
    "create_debt_ledger_entry",
    "get_debt_total_charges",
    "get_debt_total_charges_by_debt_ids",
    "get_debt_total_paid",
    "get_debt_total_paid_by_debt_ids",
    "reconcile_debt",
    "reverse_debt_transaction_ledger",
    "reverse_wallet_effect",
    # debt_payment_service
    "build_debt_transaction_out",
    "create_debt_payment",
    # debt_policy
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
