from datetime import date

from app import models
from app.services.category_backfill_service import backfill_deprecated_financing_category_rows
from tests.helpers import create_budget, create_user_and_token


def _user(session, email):
    user = session.query(models.User).filter(models.User.email == email).first()
    assert user is not None
    return user


def _default_wallet(session, user_id):
    wallet = session.query(models.Wallet).filter(
        models.Wallet.owner_id == user_id,
        models.Wallet.is_default == True,
    ).first()
    assert wallet is not None
    return wallet


def _budget_id(client, headers, *, category, budget_year, budget_month):
    response = create_budget(
        client,
        headers,
        category=category,
        monthly_limit=1_000_000,
        budget_year=budget_year,
        budget_month=budget_month,
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def _legacy_budget(session, *, owner_id, category, budget_year, budget_month, monthly_limit=1_000_000):
    budget = models.Budget(
        owner_id=owner_id,
        category=category,
        monthly_limit=monthly_limit,
        budget_year=budget_year,
        budget_month=budget_month,
    )
    session.add(budget)
    session.flush()
    return budget.id


def _legacy_expense_event(
    session,
    *,
    owner_id,
    wallet_id,
    title,
    reference_type,
    event_date,
    amount,
    old_budget_id=None,
    debt_id=None,
    installment_plan_id=None,
    installment_payment_id=None,
):
    event = models.FinancialEvent(
        owner_id=owner_id,
        title=title,
        event_type=models.TransactionType.EXPENSE,
        reference_type=reference_type,
        date=event_date,
    )
    event.wallet_legs.append(
        models.WalletLedger(
            owner_id=owner_id,
            wallet_id=wallet_id,
            amount=-amount,
        )
    )
    event.entity_legs.append(
        models.EntityLedger(
            label=title,
            amount=amount,
            category=models.ExpenseCategory.INSTALLMENTS_DEBT,
            budget_id=old_budget_id,
            debt_id=debt_id,
            installment_plan_id=installment_plan_id,
            installment_payment_id=installment_payment_id,
        )
    )
    session.add(event)
    session.flush()
    return event


def test_backfill_migrates_linked_legacy_financing_category_rows(client, session):
    headers = create_user_and_token(client, "catbackfill1", "catbackfill1@example.com", "Password123!")
    user = _user(session, "catbackfill1@example.com")
    wallet = _default_wallet(session, user.id)
    event_date = date(2026, 6, 12)
    old_budget_id = _legacy_budget(
        session,
        owner_id=user.id,
        category=models.ExpenseCategory.INSTALLMENTS_DEBT,
        budget_year=2026,
        budget_month=6,
    )
    electronics_budget_id = _budget_id(client, headers, category="Electronics", budget_year=2026, budget_month=6)
    dining_budget_id = _budget_id(client, headers, category="Dining Out", budget_year=2026, budget_month=6)
    charge_budget_id = _budget_id(client, headers, category="Debt Charges", budget_year=2026, budget_month=6)

    plan = models.InstallmentPlan(
        owner_id=user.id,
        item_name="Legacy phone",
        store_or_bank_name="Phone Store",
        plan_type=models.PaymentPlanType.STORE_INSTALLMENT,
        total_price=300_000,
        down_payment=0,
        remaining_amount=200_000,
        months=3,
        payment_count=3,
        frequency=models.InstallmentFrequency.MONTHLY,
        monthly_payment_amount=100_000,
        regular_payment_amount=100_000,
        status=models.InstallmentStatus.ACTIVE,
        start_date=event_date,
        expense_category=models.ExpenseCategory.ELECTRONICS,
    )
    debt = models.Debt(
        owner_id=user.id,
        debt_type=models.DebtType.OWING,
        origin_kind=models.DebtOriginKind.DEFERRED_EXPENSE,
        counterparty_kind=models.DebtCounterpartyKind.PERSON,
        product_kind=models.DebtProductKind.INFORMAL_DEBT,
        counterparty_name="Restaurant",
        initial_amount=200_000,
        remaining_amount=200_000,
        currency="UZS",
        status=models.DebtStatus.ACTIVE,
        date=event_date,
        is_money_transferred=False,
        expense_category=models.ExpenseCategory.DINING_OUT,
    )
    session.add_all([plan, debt])
    session.flush()
    principal_payment = models.InstallmentPayment(
        owner_id=user.id,
        plan_id=plan.id,
        amount=100_000,
        paid_amount=100_000,
        due_date=event_date,
        paid_date=event_date,
        component_type=models.InstallmentPaymentComponentType.PRINCIPAL,
        status=models.InstallmentPaymentStatus.PAID,
    )
    session.add(principal_payment)
    session.flush()

    plan_event = _legacy_expense_event(
        session,
        owner_id=user.id,
        wallet_id=wallet.id,
        title="Legacy phone installment",
        reference_type=models.ReferenceType.INSTALLMENT_PAYMENT,
        event_date=event_date,
        amount=100_000,
        old_budget_id=old_budget_id,
        installment_plan_id=plan.id,
        installment_payment_id=principal_payment.id,
    )
    debt_event = _legacy_expense_event(
        session,
        owner_id=user.id,
        wallet_id=wallet.id,
        title="Legacy dinner debt",
        reference_type=models.ReferenceType.DEBT_EXPENSE,
        event_date=event_date,
        amount=80_000,
        old_budget_id=old_budget_id,
        debt_id=debt.id,
    )
    charge_event = _legacy_expense_event(
        session,
        owner_id=user.id,
        wallet_id=wallet.id,
        title="Legacy debt charge",
        reference_type=models.ReferenceType.DEBT_CHARGE,
        event_date=event_date,
        amount=20_000,
        old_budget_id=old_budget_id,
        debt_id=debt.id,
    )
    manual_event = _legacy_expense_event(
        session,
        owner_id=user.id,
        wallet_id=wallet.id,
        title="Legacy unknown row",
        reference_type=None,
        event_date=event_date,
        amount=10_000,
        old_budget_id=old_budget_id,
    )
    session.commit()

    result = backfill_deprecated_financing_category_rows(session, owner_id=user.id)
    session.commit()

    assert result.migrated_count == 3
    assert result.manual_review_count == 1
    assert [item.entity_ledger_id for item in result.manual_review] == [manual_event.entity_legs[0].id]

    session.expire_all()
    assert plan_event.entity_legs[0].category == models.ExpenseCategory.ELECTRONICS
    assert plan_event.entity_legs[0].budget_id == electronics_budget_id
    assert debt_event.entity_legs[0].category == models.ExpenseCategory.DINING_OUT
    assert debt_event.entity_legs[0].budget_id == dining_budget_id
    assert charge_event.entity_legs[0].category == models.ExpenseCategory.DEBT_CHARGES
    assert charge_event.entity_legs[0].budget_id == charge_budget_id
    assert manual_event.entity_legs[0].category == models.ExpenseCategory.INSTALLMENTS_DEBT
    assert manual_event.entity_legs[0].budget_id == old_budget_id

    second_result = backfill_deprecated_financing_category_rows(session, owner_id=user.id)
    assert second_result.migrated_count == 0
    assert second_result.manual_review_count == 1
