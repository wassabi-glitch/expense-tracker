"""Payment Plans domain — scheduled obligations with rows and waterfall
behavior.

Owns Payment Plan CRUD, payment schedules, charge rows, payment marking,
and write-offs.

**Domain separation rule:** This package MUST NOT be merged with
``app.domains.debt``.  Payment Plan is a scheduled obligation domain with
rows and waterfall behavior; Debt is an open-ended running-balance
obligation domain.  They share money-posting mechanics through the Posting
and Ledger seams but remain separate domains.

Public API
----------
- ``_create_payment_plan_expense_event`` — create an expense-shaped
  FinancialEvent for a payment plan payment, delegating to the shared
  Expense Posting seam
- ``_scheduled_due_date`` — compute the due date for a schedule index
- ``_add_months`` / ``_add_years`` — date arithmetic helpers
- ``_default_schedule_model`` — resolve default schedule model for a plan type
- ``_resolve_schedule_model`` — resolve effective schedule model with override
- ``generate_schedule_preview`` — generate preview rows for FLAT_TOTAL or
  AMORTIZED_LOAN without persisting
- ``_generate_flat_total_rows`` — flat division schedule rows
- ``_generate_amortized_rows`` — PMT-based amortized schedule rows
"""

from app.domains.payment_plans._payment_plan_service import (
    _add_months,
    _add_years,
    _create_payment_plan_expense_event,
    _default_schedule_model,
    _generate_amortized_rows,
    _generate_flat_total_rows,
    _resolve_schedule_model,
    _scheduled_due_date,
    generate_schedule_preview,
)

__all__ = [
    "_add_months",
    "_add_years",
    "_create_payment_plan_expense_event",
    "_default_schedule_model",
    "_generate_amortized_rows",
    "_generate_flat_total_rows",
    "_resolve_schedule_model",
    "_scheduled_due_date",
    "generate_schedule_preview",
]
