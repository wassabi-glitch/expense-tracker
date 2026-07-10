"""Payment Plan domain service — scheduled obligation helpers.

This module provides shared payment-plan functions that were previously
inline in the router.  The router remains the owner of HTTP-level logic
(rate limiting, request parsing, response building); this module owns
pure domain helpers.

Domain separation rule
----------------------
- **Payment Plan domain** OWNS Payment Plan rules: schedule rows, waterfall
  spillover, charge/premium rows, row statuses, Payment Plan Ledger entries,
  imported-path behaviour, and Payment Plan lifecycle.
- **Debt domain** is a SEPARATE domain — open-ended running-balance obligations.
- Shared money-posting mechanics stay in ``app.domains.posting`` (expense
  posting) and ``app.domains.ledger`` (event recording).
"""

import calendar
from datetime import date, timedelta, tzinfo

from sqlalchemy.orm import Session

from app import models, schemas
from app.services.budget_service import (
    validate_budget_limit,
    validate_subcategory_limit,
)
from app.services.expense_posting_service import post_expense_event
from app.timezone import today_in_tz
from app.utils import check_budget_alerts


# ---------------------------------------------------------------------------
# Date helpers
# ---------------------------------------------------------------------------


def _add_months(sourcedate: date, months: int) -> date:
    month = sourcedate.month - 1 + months
    year = sourcedate.year + month // 12
    month = month % 12 + 1
    day = min(sourcedate.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def _add_years(sourcedate: date, years: int) -> date:
    try:
        return sourcedate.replace(year=sourcedate.year + years)
    except ValueError:
        return sourcedate.replace(year=sourcedate.year + years, day=28)


def _scheduled_due_date(start_date: date, frequency: models.PaymentPlanFrequency, index: int) -> date:
    if frequency == models.PaymentPlanFrequency.WEEKLY:
        return start_date + timedelta(weeks=index)
    if frequency == models.PaymentPlanFrequency.BIWEEKLY:
        return start_date + timedelta(weeks=index * 2)
    if frequency == models.PaymentPlanFrequency.QUARTERLY:
        return _add_months(start_date, index * 3)
    if frequency == models.PaymentPlanFrequency.YEARLY:
        return _add_years(start_date, index)
    return _add_months(start_date, index)


# ---------------------------------------------------------------------------
# Expense event creation
# ---------------------------------------------------------------------------


def _create_payment_plan_expense_event(
    db: Session,
    owner_id: int,
    *,
    title: str,
    amount: int,
    category: models.ExpenseCategory,
    expense_date: date,
    wallet_allocations: list[schemas.PaymentPlanWalletAllocationIn],
    reference_type: str,
    payment_plan_id: int,
    payment_plan_payment_id: int | None = None,
    subcategory_id: int | None = None,
    project_id: int | None = None,
    project_subcategory_id: int | None = None,
    note: str | None = None,
    user_tz: tzinfo,
) -> models.FinancialEvent:
    """Create an expense-shaped FinancialEvent for a payment plan payment.

    Delegates to the shared Expense Posting seam so that wallet ledger
    classification, entity ledger links, budget permission, project rules,
    goal protection, and user-local date validation all go through the
    canonical path.

    Payment-plan-specific extras (budget-limit check, subcategory-limit
    check, budget alerts) are still applied by this adapter.
    """
    local_today = today_in_tz(user_tz)

    # Convert PaymentPlanWalletAllocationIn → dict form for Expense Posting
    wallet_allocs = [
        {"wallet_id": int(a.wallet_id), "amount": int(a.amount)}
        for a in wallet_allocations
    ]

    result = post_expense_event(
        db,
        owner_id,
        title=title,
        amount=int(amount),
        category=category,
        expense_date=expense_date,
        description=note,
        wallet_allocations=wallet_allocs,
        subcategory_id=subcategory_id,
        project_id=project_id,
        project_subcategory_id=project_subcategory_id,
        reference_type=reference_type,
        local_today=local_today,
        payment_plan_id=payment_plan_id,
        payment_plan_payment_id=payment_plan_payment_id,
    )

    # Payment-plan-specific validations retained by this adapter
    if result.budget is not None:
        validate_budget_limit(db, owner_id, result.budget, amount, project=result.project)
    if result.subcategory is not None:
        validate_subcategory_limit(
            db, owner_id, result.subcategory, amount, expense_date, project=result.project,
        )

    check_budget_alerts(db, result.budget)
    return result.event


# ---------------------------------------------------------------------------
# Schedule model resolution
# ---------------------------------------------------------------------------


def _default_schedule_model(plan_type: models.PaymentPlanType) -> models.ScheduleModel:
    """Return the default schedule model for a given plan type."""
    if plan_type in {
        models.PaymentPlanType.STORE_INSTALLMENT,
        models.PaymentPlanType.PRODUCT_FINANCING,
    }:
        return models.ScheduleModel.FLAT_TOTAL
    if plan_type in {
        models.PaymentPlanType.BANK_LOAN,
        models.PaymentPlanType.MORTGAGE,
        models.PaymentPlanType.AUTO_LOAN,
    }:
        return models.ScheduleModel.AMORTIZED_LOAN
    # EDUCATION_LOAN, SERVICE_CONTRACT, OTHER — default to FLAT_TOTAL
    return models.ScheduleModel.FLAT_TOTAL


def _resolve_schedule_model(
    plan_type: models.PaymentPlanType,
    schedule_model_override: models.ScheduleModel | None = None,
) -> models.ScheduleModel:
    """Resolve the effective schedule model, allowing explicit override."""
    if schedule_model_override is not None:
        return schedule_model_override
    return _default_schedule_model(plan_type)


# ---------------------------------------------------------------------------
# Flat-total schedule generation
# ---------------------------------------------------------------------------


def _generate_flat_total_rows(
    total_price: int,
    down_payment: int,
    payment_count: int,
    frequency: models.PaymentPlanFrequency,
    first_due_date: date,
) -> list[dict]:
    """Generate flat-total schedule rows.

    Returns a list of dicts with: due_date, component_type, amount,
    installment_number.
    """
    remaining = int(total_price) - int(down_payment)
    if remaining <= 0:
        return []

    base_payment = remaining // payment_count
    remainder = remaining % payment_count
    rows: list[dict] = []

    for idx in range(1, payment_count + 1):
        amount = base_payment + (remainder if idx == payment_count else 0)
        if amount <= 0:
            continue
        rows.append({
            "due_date": _scheduled_due_date(first_due_date, frequency, idx),
            "component_type": models.PaymentPlanPaymentComponentType.PRINCIPAL.value,
            "amount": amount,
            "installment_number": idx,
        })

    return rows


# ---------------------------------------------------------------------------
# Amortized schedule generation
# ---------------------------------------------------------------------------


def _periodic_rate(annual_rate_percent: float, frequency: models.PaymentPlanFrequency) -> float:
    """Convert annual interest rate (percentage, e.g. 19.9 = 19.9%) to periodic
    decimal rate based on frequency."""
    periods_per_year = {
        models.PaymentPlanFrequency.WEEKLY: 52,
        models.PaymentPlanFrequency.BIWEEKLY: 26,
        models.PaymentPlanFrequency.MONTHLY: 12,
        models.PaymentPlanFrequency.QUARTERLY: 4,
        models.PaymentPlanFrequency.YEARLY: 1,
    }
    n = periods_per_year.get(frequency, 12)
    annual_decimal = annual_rate_percent / 100.0
    return annual_decimal / n


def _pmt(principal: float, periodic_rate: float, payment_count: int) -> int:
    """Compute the fixed payment amount for an amortized loan (integer UZS).

    Uses the standard PMT formula: P * r * (1+r)^n / ((1+r)^n - 1)
    """
    if periodic_rate == 0:
        return round(principal / payment_count)
    r = periodic_rate
    n = payment_count
    factor = (1 + r) ** n
    payment = principal * r * factor / (factor - 1)
    return round(payment)


def _generate_amortized_rows(
    principal: int,
    annual_interest_rate: float,
    payment_count: int,
    frequency: models.PaymentPlanFrequency,
    first_due_date: date,
) -> list[dict]:
    """Generate amortized schedule rows with CHARGE and PRINCIPAL per installment.

    Returns a list of dicts with: due_date, component_type, amount,
    installment_number. CHARGE rows come before PRINCIPAL within each
    installment.
    """
    if principal <= 0 or payment_count <= 0:
        return []

    p_rate = _periodic_rate(annual_interest_rate, frequency)
    payment_amount = _pmt(float(principal), p_rate, payment_count)
    remaining_principal = principal
    rows: list[dict] = []

    for inst_num in range(1, payment_count + 1):
        interest = round(remaining_principal * p_rate)
        # Last payment: adjust principal to zero out
        if inst_num == payment_count:
            principal_part = remaining_principal
            payment_amount = principal_part + interest
        else:
            principal_part = payment_amount - interest
            if principal_part > remaining_principal:
                principal_part = remaining_principal
                payment_amount = principal_part + interest

        # Amortized: first payment falls on first_due_date itself
        # (idx - 1) so that idx=1 returns first_due_date, idx=2 returns 1 period later
        due = _scheduled_due_date(first_due_date, frequency, inst_num - 1)

        if interest > 0:
            rows.append({
                "due_date": due,
                "component_type": models.PaymentPlanPaymentComponentType.CHARGE.value,
                "amount": max(interest, 0),
                "installment_number": inst_num,
            })
        if principal_part > 0:
            rows.append({
                "due_date": due,
                "component_type": models.PaymentPlanPaymentComponentType.PRINCIPAL.value,
                "amount": max(principal_part, 0),
                "installment_number": inst_num,
            })
        remaining_principal -= principal_part

    return rows


# ---------------------------------------------------------------------------
# Schedule preview dispatcher
# ---------------------------------------------------------------------------


def generate_schedule_preview(
    *,
    schedule_model: models.ScheduleModel,
    # Flat-total params
    total_price: int | None = None,
    down_payment: int = 0,
    # Amortized params
    principal: int | None = None,
    annual_interest_rate: float | None = None,
    # Shared params
    payment_count: int,
    frequency: models.PaymentPlanFrequency,
    first_due_date: date,
) -> dict:
    """Generate a schedule preview without persisting anything.

    Returns a dict with schedule_model, total_principal, total_charges,
    total_to_pay, final_due_date, payment_count, frequency, and rows.
    """
    if schedule_model == models.ScheduleModel.AMORTIZED_LOAN:
        if principal is None:
            raise ValueError("amortized schedule requires principal")
        if annual_interest_rate is None:
            raise ValueError("amortized schedule requires annual_interest_rate")
        rows = _generate_amortized_rows(
            principal=int(principal),
            annual_interest_rate=float(annual_interest_rate),
            payment_count=payment_count,
            frequency=frequency,
            first_due_date=first_due_date,
        )
    else:
        # FLAT_TOTAL (and MANUAL_CONTRACT_SCHEDULE fallback)
        if total_price is None:
            raise ValueError("flat-total schedule requires total_price")
        rows = _generate_flat_total_rows(
            total_price=int(total_price),
            down_payment=int(down_payment),
            payment_count=payment_count,
            frequency=frequency,
            first_due_date=first_due_date,
        )

    total_principal = sum(r["amount"] for r in rows if r["component_type"] == "PRINCIPAL")
    total_charges = sum(r["amount"] for r in rows if r["component_type"] == "CHARGE")
    final_due_date = rows[-1]["due_date"] if rows else first_due_date

    return {
        "schedule_model": schedule_model.value,
        "total_principal": total_principal,
        "total_charges": total_charges,
        "total_to_pay": total_principal + total_charges,
        "final_due_date": final_due_date,
        "payment_count": payment_count,
        "frequency": frequency.value,
        "rows": rows,
    }


# ---------------------------------------------------------------------------
# Manual contract schedule
# ---------------------------------------------------------------------------


def _generate_manual_rows(
    manual_rows: list[dict],
) -> list[dict]:
    """Validate and return user-provided manual schedule rows.

    Each row dict must have: due_date, component_type, amount.
    Optional: installment_number.

    Raises ValueError for validation failures.
    """
    if not manual_rows:
        raise ValueError("manual schedule requires at least one row")

    validated: list[dict] = []
    seen_installments: set[int] = set()
    total_amount = 0

    for i, row in enumerate(manual_rows):
        due_date = row.get("due_date")
        component_type = row.get("component_type", "PRINCIPAL")
        amount = row.get("amount", 0)
        inst_num = row.get("installment_number")

        if due_date is None:
            raise ValueError(f"row {i}: due_date is required")
        if not isinstance(due_date, date):
            raise ValueError(f"row {i}: due_date must be a date, got {type(due_date).__name__}")

        if component_type not in ("PRINCIPAL", "CHARGE"):
            raise ValueError(
                f"row {i}: component_type must be PRINCIPAL or CHARGE, got {component_type}"
            )

        amount_int = int(amount)
        if amount_int <= 0:
            raise ValueError(f"row {i}: amount must be positive, got {amount_int}")

        total_amount += amount_int

        if inst_num is not None:
            seen_installments.add(int(inst_num))

        validated.append({
            "due_date": due_date,
            "component_type": component_type,
            "amount": amount_int,
            "installment_number": int(inst_num) if inst_num is not None else None,
        })

    # Sort by due_date, then by component (CHARGE before PRINCIPAL)
    validated.sort(key=lambda r: (
        r["due_date"],
        0 if r["component_type"] == "CHARGE" else 1,
    ))

    # Re-assign installment numbers if none provided, based on due_date groups
    if not seen_installments:
        inst_counter = 1
        prev_due = None
        for row in validated:
            if row["due_date"] != prev_due:
                inst_counter += 1 if prev_due is not None else 0
                prev_due = row["due_date"]
            row["installment_number"] = inst_counter

    return validated


# ---------------------------------------------------------------------------
# Row settlement state and time status (derived, not stored)
# ---------------------------------------------------------------------------


def _row_settlement_state(
    amount: int,
    paid_amount: int,
    written_off_amount: int,
) -> str:
    """Derive the settlement state of a payment plan row from its amounts.

    Returns one of: UNPAID, PARTIAL, SETTLED.
    """
    remaining = max(0, int(amount) - int(paid_amount or 0) - int(written_off_amount or 0))
    paid = int(paid_amount or 0)
    written_off = int(written_off_amount or 0)

    if remaining == 0:
        return "SETTLED"
    if paid == 0 and written_off == 0:
        return "UNPAID"
    return "PARTIAL"


def _row_settlement_label(
    amount: int,
    paid_amount: int,
    written_off_amount: int,
) -> str:
    """A human-readable label for the row's settlement state.

    Returns one of: unpaid, partial, paid, written_off, settled.
    """
    paid = int(paid_amount or 0)
    written_off = int(written_off_amount or 0)
    amount_int = int(amount)

    if paid == amount_int:
        return "paid"
    if written_off == amount_int:
        return "written_off"
    if paid > 0 and written_off > 0:
        return "settled"
    if paid > 0:
        return "partial"
    if written_off > 0:
        return "partial"
    return "unpaid"


def _row_time_status(
    due_date: date,
    settlement_state: str,
    user_tz: tzinfo,
) -> str | None:
    """Derive the time status of a payment plan row.

    Returns one of: ON_TRACK, OVERDUE, or None (for settled rows).
    Uses the user's effective timezone for "today".
    """
    if settlement_state == "SETTLED":
        return None
    local_today = today_in_tz(user_tz)
    if due_date < local_today:
        return "OVERDUE"
    return "ON_TRACK"
