from app import models
from tests.helpers import create_budget, create_expense, create_user_and_token, user_timezone_today


def _user(session, email: str) -> models.User:
    return session.query(models.User).filter(models.User.email == email).one()


def test_positive_credit_balance_is_owned_and_goal_protection_reduces_free_money(client, session):
    email = "positivecreditvalue@example.com"
    headers = create_user_and_token(client, "positivecreditvalue", email, "Password123!")
    user = _user(session, email)
    today = user_timezone_today()

    credit = models.Wallet(
        owner_id=user.id,
        name="Overpaid card",
        wallet_type=models.WalletType.CREDIT,
        accounting_type=models.AccountingType.LIABILITY,
        initial_balance=500_000,
        current_balance=500_000,
        credit_limit=20_000_000,
        can_fund_goals=True,
        is_default=False,
    )
    goal = models.Goals(
        owner_id=user.id,
        title="Protected card credit",
        target_amount=200_000,
        status=models.GoalStatus.ACTIVE,
    )
    session.add_all([credit, goal])
    session.flush()
    session.add(
        models.GoalContributions(
            owner_id=user.id,
            goal_id=goal.id,
            wallet_id=credit.id,
            amount=200_000,
            contribution_type=models.GoalContributionType.ALLOCATE,
        )
    )
    session.commit()

    summary = client.get(
        f"/budgets/month-summary?budget_year={today.year}&budget_month={today.month}",
        headers=headers,
    )
    assert summary.status_code == 200, summary.text
    payload = summary.json()
    assert payload["owned_money_now"] == 10_500_000
    assert payload["protected_goal_money"] == 200_000
    assert payload["free_money_now"] == 10_300_000
    assert payload["backing_total"] == 10_300_000
    assert {cause["code"] for cause in payload["plan_causes"]} == {"GOAL_PROTECTION"}

    assert client.post("/users/me/toggle-premium", headers=headers).status_code == 200
    funding = client.get("/goals/funding-summary", headers=headers)
    assert funding.status_code == 200, funding.text
    credit_row = next(row for row in funding.json()["wallets"] if row["wallet_id"] == credit.id)
    assert credit_row["eligible_for_goal_funding"] is True
    assert credit_row["available_for_goals"] == 300_000


def test_credit_limit_and_negative_credit_balance_never_add_backing(client, session):
    email = "negativecreditvalue@example.com"
    headers = create_user_and_token(client, "negativecreditvalue", email, "Password123!")
    user = _user(session, email)
    today = user_timezone_today()
    session.add(
        models.Wallet(
            owner_id=user.id,
            name="Large credit line",
            wallet_type=models.WalletType.CREDIT,
            accounting_type=models.AccountingType.LIABILITY,
            initial_balance=-500_000,
            current_balance=-500_000,
            credit_limit=100_000_000,
            can_fund_goals=True,
            is_default=False,
        )
    )
    session.commit()

    summary = client.get(
        f"/budgets/month-summary?budget_year={today.year}&budget_month={today.month}",
        headers=headers,
    )
    assert summary.status_code == 200, summary.text
    assert summary.json()["owned_money_now"] == 10_000_000
    assert summary.json()["free_money_now"] == 10_000_000


def test_mixed_positive_credit_purchase_records_only_new_borrowing_as_survival_usage(client, session):
    email = "creditcrossing@example.com"
    headers = create_user_and_token(client, "creditcrossing", email, "Password123!")
    user = _user(session, email)
    today = user_timezone_today()
    credit = models.Wallet(
        owner_id=user.id,
        name="Credit balance card",
        wallet_type=models.WalletType.CREDIT,
        accounting_type=models.AccountingType.LIABILITY,
        initial_balance=500_000,
        current_balance=500_000,
        credit_limit=5_000_000,
        is_default=False,
    )
    session.add(credit)
    session.commit()
    session.refresh(credit)

    budget = create_budget(
        client,
        headers,
        category="Food",
        monthly_limit=10_000_000,
        budget_year=today.year,
        budget_month=today.month,
    )
    assert budget.status_code == 201, budget.text
    configured = client.put(
        "/budgets/borrowing-survival",
        json={
            "budget_year": today.year,
            "budget_month": today.month,
            "enabled": True,
            "monthly_cap": 1_000_000,
        },
        headers=headers,
    )
    assert configured.status_code == 200, configured.text

    expense = create_expense(
        client,
        headers,
        title="Emergency groceries",
        amount=800_000,
        category="Food",
        wallet_id=credit.id,
        expense_date=today,
    )
    assert expense.status_code == 201, expense.text

    summary = client.get(
        f"/budgets/month-summary?budget_year={today.year}&budget_month={today.month}",
        headers=headers,
    )
    assert summary.status_code == 200, summary.text
    payload = summary.json()
    assert payload["valid_budget_spent"] == 500_000
    assert payload["borrowing_pressure"] is True
    assert payload["borrowing_survival"] == {
        "enabled": True,
        "monthly_cap": 1_000_000,
        "borrowed_usage": 300_000,
        "remaining_cap": 700_000,
        "exceeded_amount": 0,
    }
    session.refresh(credit)
    assert credit.current_balance == -300_000


def test_overdraft_crossing_counts_only_below_zero_portion(client, session):
    email = "overdraftcrossing@example.com"
    headers = create_user_and_token(client, "overdraftcrossing", email, "Password123!")
    user = _user(session, email)
    today = user_timezone_today()
    overdraft = models.Wallet(
        owner_id=user.id,
        name="Overdraft debit",
        wallet_type=models.WalletType.DEBIT,
        accounting_type=models.AccountingType.ASSET,
        initial_balance=200_000,
        current_balance=200_000,
        has_overdraft=True,
        overdraft_limit=2_000_000,
        is_default=False,
    )
    session.add(overdraft)
    session.commit()
    session.refresh(overdraft)

    assert create_budget(
        client,
        headers,
        category="Food",
        monthly_limit=10_000_000,
        budget_year=today.year,
        budget_month=today.month,
    ).status_code == 201
    assert create_expense(
        client,
        headers,
        title="Overdraft groceries",
        amount=500_000,
        category="Food",
        wallet_id=overdraft.id,
        expense_date=today,
    ).status_code == 201

    summary = client.get(
        f"/budgets/month-summary?budget_year={today.year}&budget_month={today.month}",
        headers=headers,
    )
    assert summary.status_code == 200, summary.text
    assert summary.json()["valid_budget_spent"] == 200_000
    assert summary.json()["borrowing_survival"]["borrowed_usage"] == 300_000


def test_survival_cap_does_not_expand_normal_budget_backing(client):
    headers = create_user_and_token(
        client,
        "survivalnotbacking",
        "survivalnotbacking@example.com",
        "Password123!",
    )
    today = user_timezone_today()
    assert create_budget(
        client,
        headers,
        category="Food",
        monthly_limit=10_000_000,
        budget_year=today.year,
        budget_month=today.month,
    ).status_code == 201
    assert client.put(
        "/budgets/borrowing-survival",
        json={
            "budget_year": today.year,
            "budget_month": today.month,
            "enabled": True,
            "monthly_cap": 5_000_000,
        },
        headers=headers,
    ).status_code == 200

    rejected = create_budget(
        client,
        headers,
        category="Transport",
        monthly_limit=1_000,
        budget_year=today.year,
        budget_month=today.month,
    )
    assert rejected.status_code == 400
    assert rejected.json()["detail"]["code"] == "budgets.plan_exceeds_backing"


def test_category_floor_warning_returns_multiple_structured_reasons(client, session):
    email = "floorreasons@example.com"
    headers = create_user_and_token(client, "floorreasons", email, "Password123!")
    user = _user(session, email)
    today = user_timezone_today()
    plan = models.InstallmentPlan(
        owner_id=user.id,
        item_name="Phone",
        plan_type=models.PaymentPlanType.STORE_INSTALLMENT,
        total_price=500_000,
        down_payment=0,
        remaining_amount=500_000,
        months=1,
        payment_count=1,
        frequency=models.InstallmentFrequency.MONTHLY,
        monthly_payment_amount=500_000,
        regular_payment_amount=500_000,
        status=models.InstallmentStatus.ACTIVE,
        start_date=today,
        expense_category=models.ExpenseCategory.ELECTRONICS,
    )
    debt = models.Debt(
        owner_id=user.id,
        debt_type=models.DebtType.OWING,
        origin_kind=models.DebtOriginKind.DEFERRED_EXPENSE,
        counterparty_kind=models.DebtCounterpartyKind.COMPANY,
        counterparty_name="Laptop store",
        initial_amount=350_000,
        remaining_amount=350_000,
        status=models.DebtStatus.ACTIVE,
        date=today,
        expected_return_date=today,
        expense_category=models.ExpenseCategory.ELECTRONICS,
    )
    session.add_all([plan, debt])
    session.flush()
    session.add(
        models.InstallmentPayment(
            owner_id=user.id,
            plan_id=plan.id,
            amount=500_000,
            paid_amount=0,
            written_off_amount=0,
            status=models.InstallmentPaymentStatus.PENDING,
            due_date=today,
        )
    )
    session.commit()
    assert create_budget(
        client,
        headers,
        category="Electronics",
        monthly_limit=700_000,
        budget_year=today.year,
        budget_month=today.month,
    ).status_code == 201

    summary = client.get(
        f"/budgets/month-summary?budget_year={today.year}&budget_month={today.month}",
        headers=headers,
    )
    assert summary.status_code == 200, summary.text
    warning = next(
        item for item in summary.json()["category_floors"]
        if item["category"] == "Electronics"
    )
    assert warning["suggested_minimum"] == 850_000
    assert warning["current_limit"] == 700_000
    assert warning["warning_gap"] == 150_000
    assert {reason["kind"] for reason in warning["reasons"]} == {
        "INSTALLMENT",
        "DEFERRED_EXPENSE",
    }
