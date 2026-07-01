from datetime import date

from app import models
from app.redis_rate_limiter import redis_client
from tests.helpers import create_user_and_token, create_budget, create_expense, user_timezone_today


def _get_user(session, email: str) -> models.User:
    user = session.query(models.User).filter(models.User.email == email).first()
    assert user is not None
    return user


def _default_wallet(session, user_id: int) -> models.Wallet:
    wallet = (
        session.query(models.Wallet)
        .filter(models.Wallet.owner_id == user_id, models.Wallet.is_default)
        .first()
    )
    assert wallet is not None
    return wallet


def _record_budget_expense_directly(
    session,
    *,
    user_id: int,
    wallet: models.Wallet,
    budget: models.Budget,
    amount: int,
    expense_date: date,
    title: str = "Direct budget expense",
):
    event = models.FinancialEvent(
        owner_id=user_id,
        title=title,
        event_type=models.TransactionType.EXPENSE,
        status=models.FinancialEventStatus.POSTED,
        date=expense_date,
    )
    session.add(event)
    session.flush()
    wallet.current_balance = int(wallet.current_balance) - int(amount)
    session.add(
        models.WalletLedger(
            owner_id=user_id,
            event_id=event.id,
            wallet_id=wallet.id,
            amount=-int(amount),
        )
    )
    session.add(
        models.EntityLedger(
            event_id=event.id,
            label=title,
            amount=int(amount),
            category=budget.category,
            budget_id=budget.id,
        )
    )
    session.commit()
    return event


def _create_income_source(client, headers, name: str = "Salary"):
    res = client.post("/income/sources", json={"name": name}, headers=headers)
    assert res.status_code == 201, res.text
    return res.json()


def _next_month(value: date) -> tuple[int, int]:
    if value.month == 12:
        return value.year + 1, 1
    return value.year, value.month + 1


def _previous_month(value: date) -> tuple[int, int]:
    if value.month == 1:
        return value.year - 1, 12
    return value.year, value.month - 1


def _create_expected_income(
    client,
    headers,
    *,
    source_id: int,
    amount: int,
    due_date: date,
    note: str | None = None,
):
    res = client.post(
        "/budgets/expected-incomes",
        json={
            "source_id": source_id,
            "amount": amount,
            "due_date": due_date.isoformat(),
            "budget_year": due_date.year,
            "budget_month": due_date.month,
            "note": note,
        },
        headers=headers,
    )
    assert res.status_code == 201, res.text
    return res.json()


def test_create_budget_success(client):
    headers = create_user_and_token(
        client, "budgetuser", "budgetuser@example.com", "Password123!"
    )
    res = create_budget(client, headers, category="Food", monthly_limit=500)
    assert res.status_code == 201
    data = res.json()
    assert data["category"] == "Groceries"
    assert data["monthly_limit"] == 500
    assert "spent" in data
    assert "budget_year" in data
    assert "budget_month" in data


def test_create_budget_rejects_financing_context_category(client):
    headers = create_user_and_token(
        client, "budgetcatdeprecated", "budgetcatdeprecated@example.com", "Password123!"
    )

    res = create_budget(client, headers, category="Installments & Debt", monthly_limit=500)

    assert res.status_code == 400
    assert res.json()["detail"] == "budgets.validation.real_expense_category_required"


def test_budget_subcategory_rejects_financing_context_category(client, session):
    headers = create_user_and_token(
        client, "budgetsubcatdeprecated", "budgetsubcatdeprecated@example.com", "Password123!"
    )
    user = _get_user(session, "budgetsubcatdeprecated@example.com")
    today = user_timezone_today()
    legacy_budget = models.Budget(
        owner_id=user.id,
        category=models.ExpenseCategory.PAYMENT_PLANS_DEBT,
        monthly_limit=500,
        budget_year=today.year,
        budget_month=today.month,
    )
    session.add(legacy_budget)
    session.commit()
    session.refresh(legacy_budget)

    res = client.post(
        f"/budgets/{legacy_budget.id}/subcategories",
        json={
            "category": "Installments & Debt",
            "name": "Legacy lane",
            "monthly_limit": 100,
        },
        headers=headers,
    )

    assert res.status_code == 400
    assert res.json()["detail"] == "budgets.validation.real_expense_category_required"


def test_budget_subcategory_allows_user_created_real_category(client):
    headers = create_user_and_token(
        client, "budgetsubcatreal", "budgetsubcatreal@example.com", "Password123!"
    )
    budget = create_budget(client, headers, category="Groceries", monthly_limit=500)
    assert budget.status_code == 201, budget.text

    res = client.post(
        f"/budgets/{budget.json()['id']}/subcategories",
        json={
            "category": "Groceries",
            "name": "Market",
            "monthly_limit": 100,
        },
        headers=headers,
    )

    assert res.status_code == 201, res.text
    assert res.json()["category"] == "Groceries"
    assert res.json()["name"] == "Market"


def test_budget_subcategory_limit_changes_do_not_mutate_prior_month_detail(client):
    headers = create_user_and_token(
        client, "budgetsubcatmonth", "budgetsubcatmonth@example.com", "Password123!"
    )
    today = user_timezone_today()
    next_year, next_month = _next_month(today)
    current_budget = create_budget(
        client,
        headers,
        category="Transport",
        monthly_limit=1_000_000,
        budget_year=today.year,
        budget_month=today.month,
    )
    assert current_budget.status_code == 201, current_budget.text

    subcategory = client.post(
        f"/budgets/{current_budget.json()['id']}/subcategories",
        json={
            "category": "Transport",
            "name": "Taxi",
            "monthly_limit": 200_000,
        },
        headers=headers,
    )
    assert subcategory.status_code == 201, subcategory.text

    next_budget = create_budget(
        client,
        headers,
        category="Transport",
        monthly_limit=1_000_000,
        budget_year=next_year,
        budget_month=next_month,
    )
    assert next_budget.status_code == 201, next_budget.text

    changed = client.patch(
        f"/budgets/subcategories/{subcategory.json()['id']}",
        json={"monthly_limit": 500_000},
        headers=headers,
    )
    assert changed.status_code == 200, changed.text

    current_detail = client.get(
        f"/budgets/item/detail?budget_year={today.year}&budget_month={today.month}&category=Transport",
        headers=headers,
    )
    assert current_detail.status_code == 200, current_detail.text
    next_detail = client.get(
        f"/budgets/item/detail?budget_year={next_year}&budget_month={next_month}&category=Transport",
        headers=headers,
    )
    assert next_detail.status_code == 200, next_detail.text

    current_subcategory = current_detail.json()["subcategories"][0]
    next_subcategory = next_detail.json()["subcategories"][0]
    assert current_subcategory["id"] == subcategory.json()["id"]
    assert next_subcategory["id"] == subcategory.json()["id"]
    assert current_subcategory["monthly_limit"] == 200_000
    assert next_subcategory["monthly_limit"] == 500_000


def test_lazy_month_materialization_copies_subcategory_limits_without_linking_history(client):
    headers = create_user_and_token(
        client, "budgetsubcatlazy", "budgetsubcatlazy@example.com", "Password123!"
    )
    today = user_timezone_today()
    previous_year, previous_month = _previous_month(today)
    previous_budget = create_budget(
        client,
        headers,
        category="Transport",
        monthly_limit=1_000_000,
        budget_year=previous_year,
        budget_month=previous_month,
    )
    assert previous_budget.status_code == 201, previous_budget.text
    subcategory = client.post(
        f"/budgets/{previous_budget.json()['id']}/subcategories",
        json={
            "category": "Transport",
            "name": "Taxi",
            "monthly_limit": 200_000,
        },
        headers=headers,
    )
    assert subcategory.status_code == 201, subcategory.text

    expense = create_expense(
        client,
        headers,
        title="Next month taxi",
        amount=10_000,
        category="Transport",
        expense_date=today,
    )
    assert expense.status_code == 201, expense.text

    current_detail = client.get(
        f"/budgets/item/detail?budget_year={today.year}&budget_month={today.month}&category=Transport",
        headers=headers,
    )
    assert current_detail.status_code == 200, current_detail.text
    copied_subcategory = current_detail.json()["subcategories"][0]
    assert copied_subcategory["id"] == subcategory.json()["id"]
    assert copied_subcategory["monthly_limit"] == 200_000

    changed = client.patch(
        f"/budgets/subcategories/{subcategory.json()['id']}",
        json={"monthly_limit": 500_000},
        headers=headers,
    )
    assert changed.status_code == 200, changed.text

    previous_detail = client.get(
        f"/budgets/item/detail?budget_year={previous_year}&budget_month={previous_month}&category=Transport",
        headers=headers,
    )
    assert previous_detail.status_code == 200, previous_detail.text
    assert previous_detail.json()["subcategories"][0]["monthly_limit"] == 200_000





def test_parent_category_spending_without_subcategory_remains_valid(client):
    headers = create_user_and_token(
        client, "budgetparentspend", "budgetparentspend@example.com", "Password123!"
    )
    today = user_timezone_today()
    budget = create_budget(
        client,
        headers,
        category="Transport",
        monthly_limit=500_000,
        budget_year=today.year,
        budget_month=today.month,
    )
    assert budget.status_code == 201, budget.text
    subcategory = client.post(
        f"/budgets/{budget.json()['id']}/subcategories",
        json={
            "category": "Transport",
            "name": "Fuel",
            "monthly_limit": 500_000,
        },
        headers=headers,
    )
    assert subcategory.status_code == 201, subcategory.text

    expense = create_expense(
        client,
        headers,
        title="Parking",
        amount=50_000,
        category="Transport",
        expense_date=today,
    )
    assert expense.status_code == 201, expense.text
    assert expense.json()["subcategory_id"] is None

    detail = client.get(
        f"/budgets/item/detail?budget_year={today.year}&budget_month={today.month}&category=Transport",
        headers=headers,
    )
    assert detail.status_code == 200, detail.text
    assert detail.json()["spent"] == 50_000
    assert detail.json()["recent_activity"][0]["subcategory_id"] is None
    assert detail.json()["recent_activity"][0]["subcategory_name"] is None


def test_subcategory_overspend_saves_and_budget_detail_reports_red_state(client):
    headers = create_user_and_token(
        client, "budgetsubcatred", "budgetsubcatred@example.com", "Password123!"
    )
    today = user_timezone_today()
    budget = create_budget(
        client,
        headers,
        category="Transport",
        monthly_limit=500_000,
        budget_year=today.year,
        budget_month=today.month,
    )
    assert budget.status_code == 201, budget.text
    subcategory = client.post(
        f"/budgets/{budget.json()['id']}/subcategories",
        json={
            "category": "Transport",
            "name": "Taxi",
            "monthly_limit": 100_000,
        },
        headers=headers,
    )
    assert subcategory.status_code == 201, subcategory.text

    expense = client.post(
        "/expenses/",
        json={
            "title": "Airport taxi",
            "amount": 150_000,
            "category": "Transport",
            "date": today.isoformat(),
            "subcategory_id": subcategory.json()["id"],
        },
        headers=headers,
    )
    assert expense.status_code == 201, expense.text

    detail = client.get(
        f"/budgets/item/detail?budget_year={today.year}&budget_month={today.month}&category=Transport",
        headers=headers,
    )
    assert detail.status_code == 200, detail.text
    taxi = detail.json()["subcategories"][0]
    assert taxi["spent"] == 150_000
    assert taxi["remaining"] == -50_000
    assert taxi["is_over_limit"] is True


def test_parent_category_overspend_leaks_to_global_plan_backing(client):
    headers = create_user_and_token(
        client, "budgetparentleak", "budgetparentleak@example.com", "Password123!"
    )
    today = user_timezone_today()
    groceries = create_budget(
        client,
        headers,
        category="Groceries",
        monthly_limit=9_800_000,
        budget_year=today.year,
        budget_month=today.month,
    )
    assert groceries.status_code == 201, groceries.text
    transport = create_budget(
        client,
        headers,
        category="Transport",
        monthly_limit=200_000,
        budget_year=today.year,
        budget_month=today.month,
    )
    assert transport.status_code == 201, transport.text

    expense = create_expense(
        client,
        headers,
        title="Bulk groceries",
        amount=9_900_000,
        category="Groceries",
        expense_date=today,
    )
    assert expense.status_code == 201, expense.text

    summary = client.get(
        f"/budgets/month-summary?budget_year={today.year}&budget_month={today.month}",
        headers=headers,
    )
    assert summary.status_code == 200, summary.text
    payload = summary.json()
    assert payload["valid_budget_spent"] == 9_800_000
    assert payload["backing_total"] == 9_900_000
    assert payload["monthly_effective_limit_total"] == 10_000_000
    assert payload["plan_status"] == "over_planned"
    assert payload["backing_shortfall"] == 100_000


def test_parent_category_overspend_can_be_repaired_by_reallocation(client):
    headers = create_user_and_token(
        client, "budgetparentrepair", "budgetparentrepair@example.com", "Password123!"
    )
    today = user_timezone_today()
    groceries = create_budget(
        client,
        headers,
        category="Groceries",
        monthly_limit=500_000,
        budget_year=today.year,
        budget_month=today.month,
    )
    assert groceries.status_code == 201, groceries.text
    transport = create_budget(
        client,
        headers,
        category="Transport",
        monthly_limit=500_000,
        budget_year=today.year,
        budget_month=today.month,
    )
    assert transport.status_code == 201, transport.text

    expense = create_expense(
        client,
        headers,
        title="Grocery repair target",
        amount=700_000,
        category="Groceries",
        expense_date=today,
    )
    assert expense.status_code == 201, expense.text

    groceries_before = client.get(
        f"/budgets/item?budget_year={today.year}&budget_month={today.month}&category=Groceries",
        headers=headers,
    )
    assert groceries_before.status_code == 200, groceries_before.text
    assert groceries_before.json()["remaining"] == -200_000
    assert groceries_before.json()["is_over_limit"] is True

    repaired = client.post(
        "/budgets/reallocate",
        json={
            "budget_year": today.year,
            "budget_month": today.month,
            "from_category": "Transport",
            "to_category": "Groceries",
            "amount": 200_000,
        },
        headers=headers,
    )
    assert repaired.status_code == 200, repaired.text

    groceries_after = client.get(
        f"/budgets/item?budget_year={today.year}&budget_month={today.month}&category=Groceries",
        headers=headers,
    )
    assert groceries_after.status_code == 200, groceries_after.text
    assert groceries_after.json()["monthly_limit"] == 700_000
    assert groceries_after.json()["remaining"] == 0
    assert groceries_after.json()["is_over_limit"] is False


def test_subcategory_reallocation_from_buffer_and_sibling_stays_inside_parent(client):
    headers = create_user_and_token(
        client, "budgetsubcatrealloc", "budgetsubcatrealloc@example.com", "Password123!"
    )
    today = user_timezone_today()
    budget = create_budget(
        client,
        headers,
        category="Transport",
        monthly_limit=1_000_000,
        budget_year=today.year,
        budget_month=today.month,
    )
    assert budget.status_code == 201, budget.text
    fuel = client.post(
        f"/budgets/{budget.json()['id']}/subcategories",
        json={"category": "Transport", "name": "Fuel", "monthly_limit": 400_000},
        headers=headers,
    )
    assert fuel.status_code == 201, fuel.text
    taxi = client.post(
        f"/budgets/{budget.json()['id']}/subcategories",
        json={"category": "Transport", "name": "Taxi", "monthly_limit": 200_000},
        headers=headers,
    )
    assert taxi.status_code == 201, taxi.text

    from_buffer = client.post(
        f"/budgets/{budget.json()['id']}/subcategories/reallocate",
        json={
            "from_subcategory_id": None,
            "to_subcategory_id": taxi.json()["id"],
            "amount": 100_000,
        },
        headers=headers,
    )
    assert from_buffer.status_code == 200, from_buffer.text
    after_buffer = {item["name"]: item for item in from_buffer.json()}
    assert after_buffer["Taxi"]["monthly_limit"] == 300_000
    assert after_buffer["Fuel"]["monthly_limit"] == 400_000

    from_sibling = client.post(
        f"/budgets/{budget.json()['id']}/subcategories/reallocate",
        json={
            "from_subcategory_id": fuel.json()["id"],
            "to_subcategory_id": taxi.json()["id"],
            "amount": 150_000,
        },
        headers=headers,
    )
    assert from_sibling.status_code == 200, from_sibling.text
    after_sibling = {item["name"]: item for item in from_sibling.json()}
    assert after_sibling["Taxi"]["monthly_limit"] == 450_000
    assert after_sibling["Fuel"]["monthly_limit"] == 250_000


def test_subcategory_reallocation_rejects_cross_parent_and_overcommitted_moves(client):
    headers = create_user_and_token(
        client, "budgetsubcatreallocreject", "budgetsubcatreallocreject@example.com", "Password123!"
    )
    today = user_timezone_today()
    transport = create_budget(
        client,
        headers,
        category="Transport",
        monthly_limit=500_000,
        budget_year=today.year,
        budget_month=today.month,
    )
    assert transport.status_code == 201, transport.text
    groceries = create_budget(
        client,
        headers,
        category="Groceries",
        monthly_limit=500_000,
        budget_year=today.year,
        budget_month=today.month,
    )
    assert groceries.status_code == 201, groceries.text
    taxi = client.post(
        f"/budgets/{transport.json()['id']}/subcategories",
        json={"category": "Transport", "name": "Taxi", "monthly_limit": 400_000},
        headers=headers,
    )
    assert taxi.status_code == 201, taxi.text
    fuel = client.post(
        f"/budgets/{transport.json()['id']}/subcategories",
        json={"category": "Transport", "name": "Fuel", "monthly_limit": 100_000},
        headers=headers,
    )
    assert fuel.status_code == 201, fuel.text
    meat = client.post(
        f"/budgets/{groceries.json()['id']}/subcategories",
        json={"category": "Groceries", "name": "Meat", "monthly_limit": 100_000},
        headers=headers,
    )
    assert meat.status_code == 201, meat.text

    cross_parent = client.post(
        f"/budgets/{transport.json()['id']}/subcategories/reallocate",
        json={
            "from_subcategory_id": meat.json()["id"],
            "to_subcategory_id": taxi.json()["id"],
            "amount": 50_000,
        },
        headers=headers,
    )
    assert cross_parent.status_code == 400
    assert cross_parent.json()["detail"] == "budgets.subcategory_category_mismatch"

    no_buffer = client.post(
        f"/budgets/{transport.json()['id']}/subcategories/reallocate",
        json={
            "from_subcategory_id": None,
            "to_subcategory_id": taxi.json()["id"],
            "amount": 1,
        },
        headers=headers,
    )
    assert no_buffer.status_code == 400
    assert no_buffer.json()["detail"] == "budgets.subcategory_reallocate_insufficient_buffer"

    spend = client.post(
        "/expenses/",
        json={
            "title": "Fuel fill",
            "amount": 80_000,
            "category": "Transport",
            "date": today.isoformat(),
            "subcategory_id": fuel.json()["id"],
        },
        headers=headers,
    )
    assert spend.status_code == 201, spend.text
    spent_source = client.post(
        f"/budgets/{transport.json()['id']}/subcategories/reallocate",
        json={
            "from_subcategory_id": fuel.json()["id"],
            "to_subcategory_id": taxi.json()["id"],
            "amount": 50_000,
        },
        headers=headers,
    )
    assert spent_source.status_code == 400
    assert spent_source.json()["detail"] == "budgets.subcategory_reallocate_insufficient_remaining"


def test_project_category_structures_reject_financing_context_category(client):
    headers = create_user_and_token(
        client, "projectcatdeprecated", "projectcatdeprecated@example.com", "Password123!"
    )
    today = user_timezone_today()
    project = client.post(
        "/projects",
        json={
            "title": "Legacy cleanup project",
            "is_isolated": True,
            "total_limit": 500_000,
            "start_date": today.isoformat(),
        },
        headers=headers,
    )
    assert project.status_code == 201, project.text
    project_id = project.json()["id"]

    category_limit = client.post(
        f"/projects/{project_id}/category-limits",
        json={"category": "Installments & Debt", "limit_amount": 100_000},
        headers=headers,
    )
    assert category_limit.status_code == 400
    assert category_limit.json()["detail"] == "projects.validation.real_expense_category_required"

    subcategory = client.post(
        f"/projects/{project_id}/subcategories",
        json={
            "category": "Installments & Debt",
            "name": "Legacy project lane",
            "limit_amount": 50_000,
        },
        headers=headers,
    )
    assert subcategory.status_code == 400
    assert subcategory.json()["detail"] == "projects.validation.real_expense_category_required"


def test_create_budget_duplicate(client):
    headers = create_user_and_token(
        client, "dupbudget", "dupbudget@example.com", "Password123!"
    )
    res1 = create_budget(client, headers, category="Food", monthly_limit=300)
    assert res1.status_code == 201
    res2 = create_budget(client, headers, category="Food", monthly_limit=300)
    assert res2.status_code == 409


def test_get_budgets_list(client):
    headers = create_user_and_token(
        client, "listbudget", "listbudget@example.com", "Password123!"
    )
    today = date.today()
    create_budget(client, headers, category="Food", monthly_limit=300, budget_year=today.year, budget_month=today.month)
    create_budget(client, headers, category="Transport", monthly_limit=200, budget_year=today.year, budget_month=today.month)

    client.post(
        "/expenses/",
        json={
            "title": "Burger",
            "amount": 50,
            "category": "Groceries",
            "date": today.isoformat(),
        },
        headers=headers,
    )

    res = client.get("/budgets/", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 2

    food_budget = next(b for b in data if b["category"] == "Groceries")
    transport_budget = next(b for b in data if b["category"] == "Transport")

    assert food_budget["spent"] == 50
    assert transport_budget["spent"] == 0


def test_budget_spend_refunds_and_analytics_share_budget_impact_rules(client, session):
    headers = create_user_and_token(
        client, "budgetimpact", "budgetimpact@example.com", "Password123!"
    )
    today = user_timezone_today()
    budget = create_budget(
        client,
        headers,
        category="Food",
        monthly_limit=500,
        budget_year=today.year,
        budget_month=today.month,
    )
    assert budget.status_code == 201, budget.text

    expense = create_expense(
        client,
        headers,
        title="Groceries",
        amount=400,
        category="Food",
        expense_date=today,
    )
    assert expense.status_code == 201, expense.text

    refund = client.post(
        f"/expenses/{expense.json()['id']}/refund",
        json={"amount": 150},
        headers=headers,
    )
    assert refund.status_code == 201, refund.text

    budget_after = client.get(
        f"/budgets/item?budget_year={today.year}&budget_month={today.month}&category=Groceries",
        headers=headers,
    )
    assert budget_after.status_code == 200, budget_after.text
    assert budget_after.json()["spent"] == 250
    assert budget_after.json()["remaining"] == 250

    stats = client.get("/analytics/this-month-stats", headers=headers)
    assert stats.status_code == 200, stats.text
    food = next(item for item in stats.json()["category_breakdown"] if item["category"] == "Groceries")
    assert food["total"] == 250
    assert food["remaining"] == 250

    stored_budget = session.query(models.Budget).filter(models.Budget.id == budget.json()["id"]).first()
    assert stored_budget.last_notified_threshold == 50


def test_budget_month_summary_uses_free_money_not_credit_or_overdraft(client, session):
    email = "budgetsummary@example.com"
    headers = create_user_and_token(client, "budgetsummary", email, "Password123!")
    today = user_timezone_today()
    user = _get_user(session, email)
    default_wallet = _default_wallet(session, user.id)

    session.add(
        models.Wallet(
            owner_id=user.id,
            name="Credit Line",
            wallet_type=models.WalletType.CREDIT,
            accounting_type=models.AccountingType.LIABILITY,
            initial_balance=0,
            current_balance=0,
            credit_limit=50_000_000,
            is_default=False,
        )
    )
    session.add(
        models.Wallet(
            owner_id=user.id,
            name="Overdraft Debit",
            wallet_type=models.WalletType.DEBIT,
            accounting_type=models.AccountingType.ASSET,
            initial_balance=0,
            current_balance=0,
            has_overdraft=True,
            overdraft_limit=20_000_000,
            is_default=False,
        )
    )
    goal = models.Goals(
        owner_id=user.id,
        title="Protected",
        target_amount=2_000_000,
        status=models.GoalStatus.ACTIVE,
    )
    session.add(goal)
    session.flush()
    session.add(
        models.GoalContributions(
            owner_id=user.id,
            goal_id=goal.id,
            wallet_id=default_wallet.id,
            amount=2_000_000,
            contribution_type=models.GoalContributionType.ALLOCATE,
        )
    )
    session.commit()

    created = create_budget(
        client,
        headers,
        category="Food",
        monthly_limit=8_000_000,
        budget_year=today.year,
        budget_month=today.month,
    )
    assert created.status_code == 201, created.text

    summary = client.get(
        f"/budgets/month-summary?budget_year={today.year}&budget_month={today.month}",
        headers=headers,
    )
    assert summary.status_code == 200, summary.text
    payload = summary.json()
    assert payload["owned_money_now"] == 10_000_000
    assert payload["protected_goal_money"] == 2_000_000
    assert payload["free_money_now"] == 8_000_000
    assert payload["monthly_effective_limit_total"] == 8_000_000
    assert payload["plan_free_money_remaining"] == 0
    assert payload["plan_status"] == "covered_no_cushion"


def test_budget_month_summary_valid_budget_spent_keeps_in_limit_plan_covered(client):
    headers = create_user_and_token(
        client, "budgetvalidspent", "budgetvalidspent@example.com", "Password123!"
    )
    today = user_timezone_today()

    created = create_budget(
        client,
        headers,
        category="Food",
        monthly_limit=8_000_000,
        budget_year=today.year,
        budget_month=today.month,
    )
    assert created.status_code == 201, created.text

    expense = create_expense(
        client,
        headers,
        title="Planned groceries",
        amount=2_000_000,
        category="Food",
        expense_date=today,
    )
    assert expense.status_code == 201, expense.text

    summary = client.get(
        f"/budgets/month-summary?budget_year={today.year}&budget_month={today.month}",
        headers=headers,
    )

    assert summary.status_code == 200, summary.text
    payload = summary.json()
    assert payload["free_money_now"] == 8_000_000
    assert payload["normal_budget_spent"] == 2_000_000
    assert payload["valid_budget_spent"] == 2_000_000
    assert payload["backing_total"] == 10_000_000
    assert payload["plan_backing_remaining"] == 2_000_000
    assert payload["backing_shortfall"] == 0
    assert payload["plan_status"] == "covered_with_cushion"


def test_create_budget_capacity_counts_valid_budget_spent(client):
    headers = create_user_and_token(
        client, "budgetvalidspentcreate", "budgetvalidspentcreate@example.com", "Password123!"
    )
    today = user_timezone_today()

    food_budget = create_budget(
        client,
        headers,
        category="Food",
        monthly_limit=8_000_000,
        budget_year=today.year,
        budget_month=today.month,
    )
    assert food_budget.status_code == 201, food_budget.text

    expense = create_expense(
        client,
        headers,
        title="Planned groceries",
        amount=2_000_000,
        category="Food",
        expense_date=today,
    )
    assert expense.status_code == 201, expense.text

    transport_budget = create_budget(
        client,
        headers,
        category="Transport",
        monthly_limit=2_000_000,
        budget_year=today.year,
        budget_month=today.month,
    )

    assert transport_budget.status_code == 201, transport_budget.text


def test_budget_month_summary_overspending_leaks_out_of_global_backing(client, session):
    email = "budgetoverspendleak@example.com"
    headers = create_user_and_token(client, "budgetoverspendleak", email, "Password123!")
    today = user_timezone_today()
    user = _get_user(session, email)
    default_wallet = _default_wallet(session, user.id)

    food = create_budget(
        client,
        headers,
        category="Food",
        monthly_limit=5_000_000,
        budget_year=today.year,
        budget_month=today.month,
    )
    assert food.status_code == 201, food.text
    transport = create_budget(
        client,
        headers,
        category="Transport",
        monthly_limit=5_000_000,
        budget_year=today.year,
        budget_month=today.month,
    )
    assert transport.status_code == 201, transport.text

    food_budget = session.get(models.Budget, food.json()["id"])
    assert food_budget is not None
    _record_budget_expense_directly(
        session,
        user_id=user.id,
        wallet=default_wallet,
        budget=food_budget,
        amount=6_000_000,
        expense_date=today,
        title="Imported overspend",
    )

    summary = client.get(
        f"/budgets/month-summary?budget_year={today.year}&budget_month={today.month}",
        headers=headers,
    )

    assert summary.status_code == 200, summary.text
    payload = summary.json()
    assert payload["free_money_now"] == 4_000_000
    assert payload["normal_budget_spent"] == 6_000_000
    assert payload["valid_budget_spent"] == 5_000_000
    assert payload["backing_total"] == 9_000_000
    assert payload["monthly_effective_limit_total"] == 10_000_000
    assert payload["plan_free_money_remaining"] == -1_000_000
    assert payload["cash_gap_to_budget_total"] == 1_000_000
    assert payload["backing_shortfall"] == 1_000_000
    assert payload["categories_over_limit"] == 1
    assert payload["plan_status"] == "over_planned"


def test_budget_plan_capacity_keeps_goal_money_protected_after_valid_spend(client, session):
    email = "budgetgoalprotected@example.com"
    headers = create_user_and_token(client, "budgetgoalprotected", email, "Password123!")
    today = user_timezone_today()
    user = _get_user(session, email)
    default_wallet = _default_wallet(session, user.id)

    goal = models.Goals(
        owner_id=user.id,
        title="Protected goal money",
        target_amount=2_000_000,
        status=models.GoalStatus.ACTIVE,
    )
    session.add(goal)
    session.flush()
    session.add(
        models.GoalContributions(
            owner_id=user.id,
            goal_id=goal.id,
            wallet_id=default_wallet.id,
            amount=2_000_000,
            contribution_type=models.GoalContributionType.ALLOCATE,
        )
    )
    session.commit()

    food = create_budget(
        client,
        headers,
        category="Food",
        monthly_limit=8_000_000,
        budget_year=today.year,
        budget_month=today.month,
    )
    assert food.status_code == 201, food.text

    expense = create_expense(
        client,
        headers,
        title="Cash-backed groceries",
        amount=2_000_000,
        category="Food",
        expense_date=today,
    )
    assert expense.status_code == 201, expense.text

    summary = client.get(
        f"/budgets/month-summary?budget_year={today.year}&budget_month={today.month}",
        headers=headers,
    )
    assert summary.status_code == 200, summary.text
    payload = summary.json()
    assert payload["owned_money_now"] == 8_000_000
    assert payload["protected_goal_money"] == 2_000_000
    assert payload["free_money_now"] == 6_000_000
    assert payload["valid_budget_spent"] == 2_000_000
    assert payload["backing_total"] == 8_000_000
    assert payload["plan_status"] == "covered_no_cushion"

    extra_budget = create_budget(
        client,
        headers,
        category="Transport",
        monthly_limit=1_000_000,
        budget_year=today.year,
        budget_month=today.month,
    )
    assert extra_budget.status_code == 400
    assert extra_budget.json()["detail"]["code"] == "budgets.plan_exceeds_backing"


def test_budget_plan_capacity_prorates_mixed_cash_and_credit_spending(client, session):
    email = "budgetmixedcredit@example.com"
    headers = create_user_and_token(client, "budgetmixedcredit", email, "Password123!")
    today = user_timezone_today()
    user = _get_user(session, email)
    default_wallet = _default_wallet(session, user.id)
    credit_wallet = models.Wallet(
        owner_id=user.id,
        name="Mixed Card",
        wallet_type=models.WalletType.CREDIT,
        accounting_type=models.AccountingType.LIABILITY,
        initial_balance=0,
        current_balance=0,
        credit_limit=5_000_000,
        is_default=False,
    )
    session.add(credit_wallet)
    session.commit()
    session.refresh(credit_wallet)

    food = create_budget(
        client,
        headers,
        category="Food",
        monthly_limit=10_000_000,
        budget_year=today.year,
        budget_month=today.month,
    )
    assert food.status_code == 201, food.text

    expense = client.post(
        "/expenses/",
        json={
            "title": "Split tender groceries",
            "amount": 4_000_000,
            "category": "Groceries",
            "date": today.isoformat(),
            "wallet_allocations": [
                {"wallet_id": default_wallet.id, "amount": 2_000_000},
                {"wallet_id": credit_wallet.id, "amount": 2_000_000},
            ],
        },
        headers=headers,
    )
    assert expense.status_code == 201, expense.text

    summary = client.get(
        f"/budgets/month-summary?budget_year={today.year}&budget_month={today.month}",
        headers=headers,
    )
    assert summary.status_code == 200, summary.text
    payload = summary.json()
    assert payload["free_money_now"] == 8_000_000
    assert payload["normal_budget_spent"] == 4_000_000
    assert payload["valid_budget_spent"] == 2_000_000
    assert payload["backing_total"] == 10_000_000
    assert payload["plan_status"] == "covered_no_cushion"
    assert payload["borrowing_pressure"] is True

    extra_budget = create_budget(
        client,
        headers,
        category="Transport",
        monthly_limit=1_000_000,
        budget_year=today.year,
        budget_month=today.month,
    )
    assert extra_budget.status_code == 400
    assert extra_budget.json()["detail"]["code"] == "budgets.plan_exceeds_backing"


def test_budget_month_summary_reports_category_obligation_floors_without_global_subtraction(client, session):
    email = "budgetcategoryfloors@example.com"
    headers = create_user_and_token(client, "budgetcategoryfloors", email, "Password123!")
    today = user_timezone_today()
    user = _get_user(session, email)

    food = create_budget(
        client,
        headers,
        category="Food",
        monthly_limit=100_000,
        budget_year=today.year,
        budget_month=today.month,
    )
    assert food.status_code == 201, food.text
    session.add(
        models.RecurringExpense(
            owner_id=user.id,
            title="Groceries box",
            amount=300_000,
            category=models.ExpenseCategory.GROCERIES,
            frequency=models.RecurringFrequency.MONTHLY,
            start_date=today,
            next_due_date=today,
            status=models.RecurringStatus.ACTIVE,
            cycle_behavior=models.CycleBehavior.FIXED,
            original_due_day=today.day,
        )
    )
    plan = models.PaymentPlan(
        owner_id=user.id,
        item_name="Phone",
        plan_type=models.PaymentPlanType.STORE_INSTALLMENT,
        total_price=1_000_000,
        down_payment=0,
        remaining_amount=1_000_000,
        months=5,
        payment_count=5,
        frequency=models.PaymentPlanFrequency.MONTHLY,
        monthly_payment_amount=200_000,
        regular_payment_amount=200_000,
        status=models.PaymentPlanStatus.ACTIVE,
        start_date=today,
        expense_category=models.ExpenseCategory.ELECTRONICS,
    )
    session.add(plan)
    session.flush()
    session.add(
        models.PaymentPlanPayment(
            owner_id=user.id,
            plan_id=plan.id,
            amount=200_000,
            paid_amount=0,
            written_off_amount=0,
            component_type=models.PaymentPlanPaymentComponentType.PRINCIPAL,
            status=models.PaymentPlanPaymentStatus.PENDING,
            due_date=today,
        )
    )
    session.add(
        models.Debt(
            owner_id=user.id,
            debt_type=models.DebtType.OWING,
            origin_kind=models.DebtOriginKind.DEFERRED_EXPENSE,
            counterparty_kind=models.DebtCounterpartyKind.COMPANY,
            counterparty_name="Clinic",
            initial_amount=400_000,
            remaining_amount=400_000,
            status=models.DebtStatus.ACTIVE,
            date=today,
            expected_return_date=today,
            expense_category=models.ExpenseCategory.HEALTH,
        )
    )
    session.commit()

    summary = client.get(
        f"/budgets/month-summary?budget_year={today.year}&budget_month={today.month}",
        headers=headers,
    )

    assert summary.status_code == 200, summary.text
    payload = summary.json()
    assert payload["category_floor_total"] == 900_000
    assert payload["category_floor_shortfall"] == 800_000
    assert payload["backing_total"] == 10_000_000
    floors = {item["category"]: item for item in payload["category_floors"]}
    assert floors["Groceries"]["floor_amount"] == 300_000
    assert floors["Groceries"]["effective_monthly_limit"] == 100_000
    assert floors["Groceries"]["shortfall"] == 200_000
    assert floors["Groceries"]["sources"] == ["recurring"]
    assert floors["Electronics"]["floor_amount"] == 200_000
    assert floors["Electronics"]["sources"] == ["payment_plan"]
    assert floors["Health"]["floor_amount"] == 400_000
    assert floors["Health"]["sources"] == ["debt"]


def test_budget_month_summary_classifies_payable_debt_floor_by_expense_route(client, session):
    email = "budgetdebtfloorroute@example.com"
    headers = create_user_and_token(client, "budgetdebtfloorroute", email, "Password123!")
    today = user_timezone_today()
    user = _get_user(session, email)

    session.add_all(
        [
            models.Debt(
                owner_id=user.id,
                debt_type=models.DebtType.OWING,
                origin_kind=models.DebtOriginKind.IMPORTED_BALANCE,
                product_kind=models.DebtProductKind.STORE_INSTALLMENT,
                counterparty_kind=models.DebtCounterpartyKind.STORE,
                counterparty_name="Appliance store",
                initial_amount=700_000,
                remaining_amount=700_000,
                status=models.DebtStatus.ACTIVE,
                date=today,
                expected_return_date=today,
                expense_category=models.ExpenseCategory.HOUSING,
            ),
            models.Debt(
                owner_id=user.id,
                debt_type=models.DebtType.OWING,
                origin_kind=models.DebtOriginKind.CASH_BORROWED,
                product_kind=models.DebtProductKind.INFORMAL_DEBT,
                counterparty_kind=models.DebtCounterpartyKind.PERSON,
                counterparty_name="Neighbor",
                initial_amount=300_000,
                remaining_amount=300_000,
                status=models.DebtStatus.ACTIVE,
                date=today,
                expected_return_date=today,
                expense_category=None,
            ),
        ]
    )
    session.commit()

    summary = client.get(
        f"/budgets/month-summary?budget_year={today.year}&budget_month={today.month}",
        headers=headers,
    )

    assert summary.status_code == 200, summary.text
    payload = summary.json()
    floors = {item["category"]: item for item in payload["category_floors"]}
    assert floors["Housing"]["floor_amount"] == 700_000
    assert floors["Housing"]["sources"] == ["debt"]
    assert payload["cash_obligation_reserve_total"] == 300_000

    smart = client.post(
        "/budgets/month-setup/preview",
        json={
            "budget_year": today.year,
            "budget_month": today.month,
            "mode": "SMART_AUTO_FILL",
        },
        headers=headers,
    )
    assert smart.status_code == 200, smart.text
    housing = next(item for item in smart.json()["category_proposals"] if item["category"] == "Housing")
    assert housing["proposed_monthly_limit"] == 700_000
    assert housing["floor_sources"] == ["debt"]


def test_budget_summary_does_not_double_count_linked_payment_plan_debt(client, session):
    email = "budgetlinkedplandebt@example.com"
    headers = create_user_and_token(client, "budgetlinkedplandebt", email, "Password123!")
    today = user_timezone_today()
    user = _get_user(session, email)

    linked_debt = models.Debt(
        owner_id=user.id,
        debt_type=models.DebtType.OWING,
        origin_kind=models.DebtOriginKind.FINANCED_ASSET_PURCHASE,
        counterparty_kind=models.DebtCounterpartyKind.STORE,
        counterparty_name="Legacy store",
        initial_amount=500_000,
        remaining_amount=500_000,
        status=models.DebtStatus.ACTIVE,
        date=today,
        expected_return_date=today,
        expense_category=None,
    )
    session.add(linked_debt)
    session.flush()
    plan = models.PaymentPlan(
        owner_id=user.id,
        debt_id=linked_debt.id,
        item_name="Phone",
        plan_type=models.PaymentPlanType.STORE_INSTALLMENT,
        total_price=500_000,
        down_payment=0,
        remaining_amount=500_000,
        months=1,
        payment_count=1,
        frequency=models.PaymentPlanFrequency.MONTHLY,
        monthly_payment_amount=500_000,
        regular_payment_amount=500_000,
        status=models.PaymentPlanStatus.ACTIVE,
        start_date=today,
        expense_category=models.ExpenseCategory.ELECTRONICS,
    )
    session.add(plan)
    session.flush()
    session.add(
        models.PaymentPlanPayment(
            owner_id=user.id,
            plan_id=plan.id,
            amount=500_000,
            paid_amount=0,
            written_off_amount=0,
            component_type=models.PaymentPlanPaymentComponentType.PRINCIPAL,
            status=models.PaymentPlanPaymentStatus.PENDING,
            due_date=today,
        )
    )
    session.commit()

    summary = client.get(
        f"/budgets/month-summary?budget_year={today.year}&budget_month={today.month}",
        headers=headers,
    )

    assert summary.status_code == 200, summary.text
    payload = summary.json()
    assert payload["cash_obligation_reserve_total"] == 0
    floors = {item["category"]: item for item in payload["category_floors"]}
    assert floors["Electronics"]["floor_amount"] == 500_000
    assert floors["Electronics"]["sources"] == ["payment_plan"]


def test_budget_month_summary_reserves_cash_only_debt_from_plan_backing(client, session):
    email = "budgetcashreserve@example.com"
    headers = create_user_and_token(client, "budgetcashreserve", email, "Password123!")
    today = user_timezone_today()
    user = _get_user(session, email)

    planned = create_budget(
        client,
        headers,
        category="Food",
        monthly_limit=9_000_000,
        budget_year=today.year,
        budget_month=today.month,
    )
    assert planned.status_code == 201, planned.text
    session.add(
        models.Debt(
            owner_id=user.id,
            debt_type=models.DebtType.OWING,
            origin_kind=models.DebtOriginKind.CASH_BORROWED,
            product_kind=models.DebtProductKind.INFORMAL_DEBT,
            counterparty_kind=models.DebtCounterpartyKind.PERSON,
            counterparty_name="Friend",
            initial_amount=2_000_000,
            remaining_amount=2_000_000,
            status=models.DebtStatus.ACTIVE,
            date=today,
            expected_return_date=today,
        )
    )
    session.commit()

    summary = client.get(
        f"/budgets/month-summary?budget_year={today.year}&budget_month={today.month}",
        headers=headers,
    )
    assert summary.status_code == 200, summary.text
    payload = summary.json()
    assert payload["free_money_now"] == 10_000_000
    assert payload["cash_obligation_reserve_total"] == 2_000_000
    assert payload["backing_total"] == 8_000_000
    assert payload["plan_backing_remaining"] == -1_000_000
    assert payload["backing_shortfall"] == 1_000_000
    assert payload["plan_status"] == "over_planned"

    blocked = create_budget(
        client,
        headers,
        category="Transport",
        monthly_limit=1_000,
        budget_year=today.year,
        budget_month=today.month,
    )
    assert blocked.status_code == 400
    assert blocked.json()["detail"]["cash_obligation_reserve_total"] == 2_000_000


def test_over_budget_expense_save_records_reality_and_turns_plan_over_planned(client):
    headers = create_user_and_token(
        client, "budgetoverreal", "budgetoverreal@example.com", "Password123!"
    )
    today = user_timezone_today()
    food = create_budget(
        client,
        headers,
        category="Food",
        monthly_limit=500_000,
        budget_year=today.year,
        budget_month=today.month,
    )
    assert food.status_code == 201, food.text
    transport = create_budget(
        client,
        headers,
        category="Transport",
        monthly_limit=9_500_000,
        budget_year=today.year,
        budget_month=today.month,
    )
    assert transport.status_code == 201, transport.text

    expense = create_expense(
        client,
        headers,
        title="Real grocery overspend",
        amount=700_000,
        category="Food",
        expense_date=today,
    )
    assert expense.status_code == 201, expense.text

    food_after = client.get(
        f"/budgets/item?budget_year={today.year}&budget_month={today.month}&category=Groceries",
        headers=headers,
    )
    assert food_after.status_code == 200, food_after.text
    assert food_after.json()["spent"] == 700_000
    assert food_after.json()["is_over_limit"] is True

    summary = client.get(
        f"/budgets/month-summary?budget_year={today.year}&budget_month={today.month}",
        headers=headers,
    )
    assert summary.status_code == 200, summary.text
    payload = summary.json()
    assert payload["normal_budget_spent"] == 700_000
    assert payload["valid_budget_spent"] == 500_000
    assert payload["backing_total"] == 9_800_000
    assert payload["backing_shortfall"] == 200_000
    assert payload["plan_status"] == "over_planned"


def test_create_budget_rejects_plan_above_free_money_without_expected_income(client):
    headers = create_user_and_token(
        client, "budgetcap", "budgetcap@example.com", "Password123!"
    )
    today = user_timezone_today()

    res = create_budget(
        client,
        headers,
        category="Food",
        monthly_limit=10_000_001,
        budget_year=today.year,
        budget_month=today.month,
    )

    assert res.status_code == 400
    detail = res.json()["detail"]
    assert detail["code"] == "budgets.plan_exceeds_backing"
    assert detail["attempted_total"] == 10_000_001
    assert detail["backing_total"] == 10_000_000
    assert detail["shortfall"] == 1
    assert detail["expected_income_remaining"] == 0


def test_expected_income_allows_waiting_on_income_status(client):
    headers = create_user_and_token(
        client, "budgetexpected", "budgetexpected@example.com", "Password123!"
    )
    today = user_timezone_today()
    source = _create_income_source(client, headers, "Salary")
    expected = _create_expected_income(
        client,
        headers,
        source_id=source["id"],
        amount=5_000_000,
        due_date=today,
        note="June salary",
    )
    assert expected["status"] == "EXPECTED"

    created = create_budget(
        client,
        headers,
        category="Food",
        monthly_limit=12_000_000,
        budget_year=today.year,
        budget_month=today.month,
    )
    assert created.status_code == 201, created.text

    summary = client.get(
        f"/budgets/month-summary?budget_year={today.year}&budget_month={today.month}",
        headers=headers,
    )
    assert summary.status_code == 200, summary.text
    payload = summary.json()
    assert payload["free_money_now"] == 10_000_000
    assert payload["expected_income_remaining"] == 5_000_000
    assert payload["backing_total"] == 15_000_000
    assert payload["monthly_effective_limit_total"] == 12_000_000
    assert payload["plan_status"] == "waiting_on_income"
    assert payload["plan_free_money_remaining"] == -2_000_000
    assert payload["plan_backing_remaining"] == 3_000_000
    assert payload["cash_gap_to_budget_total"] == 2_000_000
    assert payload["backing_shortfall"] == 0


def test_receivable_debt_requires_explicit_expected_payment_before_budget_backing(client):
    headers = create_user_and_token(
        client, "budgetreceivable", "budgetreceivable@example.com", "Password123!"
    )
    today = user_timezone_today()

    debt = client.post(
        "/debts",
        json={
            "debt_type": "OWED",
            "counterparty_name": "Ali",
            "initial_amount": 3_000_000,
            "currency": "UZS",
            "date": today.isoformat(),
            "expected_return_date": today.isoformat(),
            "is_money_transferred": False,
        },
        headers=headers,
    )
    assert debt.status_code == 201, debt.text
    assert "debts.warning.receivable_expected_payment_requires_explicit_plan" in debt.json()["workflow_warnings"]

    summary_before = client.get(
        f"/budgets/month-summary?budget_year={today.year}&budget_month={today.month}",
        headers=headers,
    )
    assert summary_before.status_code == 200, summary_before.text
    assert summary_before.json()["expected_income_remaining"] == 0

    expected = client.post(
        "/budgets/expected-incomes",
        json={
            "debt_id": debt.json()["id"],
            "amount": 3_000_000,
            "due_date": today.isoformat(),
            "budget_year": today.year,
            "budget_month": today.month,
            "note": "Ali payback",
        },
        headers=headers,
    )
    assert expected.status_code == 201, expected.text
    expected_payload = expected.json()
    assert expected_payload["source_id"] is None
    assert expected_payload["debt_id"] == debt.json()["id"]
    assert expected_payload["status"] == "EXPECTED"

    listed = client.get(
        f"/budgets/expected-incomes?budget_year={today.year}&budget_month={today.month}",
        headers=headers,
    )
    assert listed.status_code == 200, listed.text
    assert [item["debt_id"] for item in listed.json()] == [debt.json()["id"]]

    summary_after = client.get(
        f"/budgets/month-summary?budget_year={today.year}&budget_month={today.month}",
        headers=headers,
    )
    assert summary_after.status_code == 200, summary_after.text
    payload = summary_after.json()
    assert payload["expected_income_remaining"] == 3_000_000
    assert payload["backing_total"] == 13_000_000

    wallets = client.get("/wallets", headers=headers)
    wallet = wallets.json()[0]

    received = client.post(
        f"/budgets/expected-incomes/{expected_payload['id']}/mark-received",
        json={
            "received_amount": 3_000_000,
            "date": today.isoformat(),
            "wallet_allocations": [{"wallet_id": wallet["id"], "amount": 3_000_000}],
        },
        headers=headers,
    )
    assert received.status_code == 200, received.text
    assert received.json()["debt_id"] == debt.json()["id"]
    assert received.json()["status"] == "RESOLVED"

    summary_received = client.get(
        f"/budgets/month-summary?budget_year={today.year}&budget_month={today.month}",
        headers=headers,
    )
    assert summary_received.status_code == 200, summary_received.text
    received_payload = summary_received.json()
    assert received_payload["expected_income_remaining"] == 0
    assert received_payload["backing_total"] == 13_000_000


def test_expected_income_mark_received_preserves_expectation_and_links_wallet_event(client):
    headers = create_user_and_token(
        client, "budgetexpectedrealize", "budgetexpectedrealize@example.com", "Password123!"
    )
    today = user_timezone_today()
    source = _create_income_source(client, headers, "Client work")
    expected = _create_expected_income(
        client,
        headers,
        source_id=source["id"],
        amount=2_000_000,
        due_date=today,
        note="Expected invoice",
    )
    wallets = client.get("/wallets", headers=headers)
    assert wallets.status_code == 200, wallets.text
    wallet = wallets.json()[0]

    received = client.post(
        f"/budgets/expected-incomes/{expected['id']}/mark-received",
        json={
            "received_amount": 2_500_000,
            "date": today.isoformat(),
            "note": "Client paid extra",
            "wallet_allocations": [
                {"wallet_id": wallet["id"], "amount": 2_500_000},
            ],
        },
        headers=headers,
    )

    assert received.status_code == 200, received.text
    payload = received.json()
    assert payload["status"] == "RESOLVED"
    assert payload["amount"] == 2_000_000
    assert payload["received_amount"] == 2_000_000
    assert payload["linked_transaction_id"] is not None

    summary = client.get(
        f"/budgets/month-summary?budget_year={today.year}&budget_month={today.month}",
        headers=headers,
    )
    assert summary.status_code == 200, summary.text
    assert summary.json()["expected_income_remaining"] == 0
    assert summary.json()["backing_total"] == 12_500_000

    entries = client.get("/income/entries", headers=headers)
    assert entries.status_code == 200, entries.text
    linked_entry = next(item for item in entries.json()["items"] if item["id"] == payload["linked_transaction_id"])
    assert linked_entry["amount"] == 2_500_000
    assert linked_entry["source_id"] == source["id"]


def test_debt_linked_expected_payment_mark_received_reduces_receivable_balance(client):
    headers = create_user_and_token(
        client, "budgetdebtpayrealize", "budgetdebtpayrealize@example.com", "Password123!"
    )
    today = user_timezone_today()
    debt = client.post(
        "/debts",
        json={
            "debt_type": "OWED",
            "counterparty_name": "Ali",
            "initial_amount": 500_000,
            "currency": "UZS",
            "date": today.isoformat(),
            "expected_return_date": today.isoformat(),
            "is_money_transferred": False,
        },
        headers=headers,
    )
    assert debt.status_code == 201, debt.text
    expected = client.post(
        "/budgets/expected-incomes",
        json={
            "debt_id": debt.json()["id"],
            "amount": 400_000,
            "due_date": today.isoformat(),
            "budget_year": today.year,
            "budget_month": today.month,
            "note": "Partial payback expected",
        },
        headers=headers,
    )
    assert expected.status_code == 201, expected.text
    wallets = client.get("/wallets", headers=headers)
    assert wallets.status_code == 200, wallets.text
    wallet = wallets.json()[0]

    received = client.post(
        f"/budgets/expected-incomes/{expected.json()['id']}/mark-received",
        json={
            "received_amount": 300_000,
            "date": today.isoformat(),
            "wallet_allocations": [{"wallet_id": wallet["id"], "amount": 300_000}],
        },
        headers=headers,
    )
    assert received.status_code == 200, received.text
    payload = received.json()
    assert payload["status"] == "PARTIALLY_RECEIVED"
    assert payload["amount"] == 400_000
    assert payload["received_amount"] == 300_000
    assert payload["linked_transaction_id"] is not None

    debt_after = client.get(f"/debts/{debt.json()['id']}", headers=headers)
    assert debt_after.status_code == 200, debt_after.text
    assert debt_after.json()["remaining_amount"] == 200_000

    summary = client.get(
        f"/budgets/month-summary?budget_year={today.year}&budget_month={today.month}",
        headers=headers,
    )
    assert summary.status_code == 200, summary.text
    assert summary.json()["expected_income_remaining"] == 100_000
    assert summary.json()["backing_total"] == 10_400_000


def test_budget_month_summary_exposes_expected_income_lifecycle_totals_and_items(client):
    headers = create_user_and_token(
        client, "budgetlifecyclesummary", "budgetlifecyclesummary@example.com", "Password123!"
    )
    today = user_timezone_today()
    source = _create_income_source(client, headers, "Salary")

    expected_source = _create_expected_income(
        client,
        headers,
        source_id=source["id"],
        amount=1_500_000,
        due_date=today,
        note="Still expected",
    )
    received_source = _create_expected_income(
        client,
        headers,
        source_id=source["id"],
        amount=2_000_000,
        due_date=today,
        note="Received salary",
    )
    wallets = client.get("/wallets", headers=headers)
    assert wallets.status_code == 200, wallets.text
    wallet = wallets.json()[0]
    received = client.post(
        f"/budgets/expected-incomes/{received_source['id']}/mark-received",
        json={
            "received_amount": 2_500_000,
            "date": today.isoformat(),
            "wallet_id": wallet["id"],
        },
        headers=headers,
    )
    assert received.status_code == 200, received.text

    debt = client.post(
        "/debts",
        json={
            "debt_type": "OWED",
            "counterparty_name": "Ali",
            "initial_amount": 400_000,
            "currency": "UZS",
            "date": today.isoformat(),
            "expected_return_date": today.isoformat(),
            "is_money_transferred": False,
        },
        headers=headers,
    )
    assert debt.status_code == 201, debt.text
    missed_debt = client.post(
        "/budgets/expected-incomes",
        json={
            "debt_id": debt.json()["id"],
            "amount": 400_000,
            "due_date": today.isoformat(),
            "budget_year": today.year,
            "budget_month": today.month,
        },
        headers=headers,
    )
    assert missed_debt.status_code == 201, missed_debt.text
    listed_missed = client.get(
        f"/expected-inflows?budget_year={today.year}&budget_month={today.month}",
        headers=headers,
    )
    missed_promise_id = next(item["id"] for item in listed_missed.json() if item["amount"] == 400_000)

    missed = client.post(
        f"/expected-inflows/{missed_promise_id}/write-off",
        json={"amount": 400_000, "reason": "MISSED"},
        headers=headers,
    )
    assert missed.status_code == 200, missed.text

    _create_expected_income(
        client,
        headers,
        source_id=source["id"],
        amount=700_000,
        due_date=today,
        note="Cancelled side job",
    )
    listed_cancelled = client.get(
        f"/expected-inflows?budget_year={today.year}&budget_month={today.month}",
        headers=headers,
    )
    cancelled_promise_id = next(item["id"] for item in listed_cancelled.json() if item["amount"] == 700_000)

    cancelled = client.post(
        f"/expected-inflows/{cancelled_promise_id}/cancel",
        json={"note": "Cancelled side job"},
        headers=headers,
    )
    assert cancelled.status_code == 200, cancelled.text

    summary = client.get(
        f"/budgets/month-summary?budget_year={today.year}&budget_month={today.month}",
        headers=headers,
    )
    assert summary.status_code == 200, summary.text
    payload = summary.json()
    assert payload["expected_income_remaining"] == 1_500_000
    assert payload["backing_total"] == 14_000_000

    totals = {item["status"]: item for item in payload["expected_income_totals"]}
    assert totals["EXPECTED"] == {"status": "EXPECTED", "count": 1, "amount": 1_500_000, "received_amount": 0}
    assert totals["RESOLVED"] == {"status": "RESOLVED", "count": 1, "amount": 2_000_000, "received_amount": 2_000_000}
    assert totals["WRITTEN_OFF"] == {"status": "WRITTEN_OFF", "count": 1, "amount": 400_000, "received_amount": 0}
    assert totals["CANCELLED"] == {"status": "CANCELLED", "count": 1, "amount": 700_000, "received_amount": 0}

    items = {item["id"]: item for item in payload["expected_income_items"]}
    assert items[expected_source["id"]]["source_id"] == source["id"]
    assert items[expected_source["id"]]["debt_id"] is None
    assert items[missed_debt.json()["id"]]["source_id"] is None
    assert items[missed_debt.json()["id"]]["debt_id"] == debt.json()["id"]


def test_create_budget_rejects_plan_above_free_money_plus_expected_income(client):
    headers = create_user_and_token(
        client, "budgetexpectedcap", "budgetexpectedcap@example.com", "Password123!"
    )
    today = user_timezone_today()
    source = _create_income_source(client, headers, "Salary")
    _create_expected_income(
        client,
        headers,
        source_id=source["id"],
        amount=2_000_000,
        due_date=today,
    )

    res = create_budget(
        client,
        headers,
        category="Food",
        monthly_limit=13_000_000,
        budget_year=today.year,
        budget_month=today.month,
    )

    assert res.status_code == 400
    detail = res.json()["detail"]
    assert detail["code"] == "budgets.plan_exceeds_backing"
    assert detail["attempted_total"] == 13_000_000
    assert detail["backing_total"] == 12_000_000
    assert detail["shortfall"] == 1_000_000
    assert detail["expected_income_remaining"] == 2_000_000


def test_expected_income_status_cannot_bypass_lifecycle_commands(client):
    headers = create_user_and_token(
        client, "budgetexpectedstatus", "budgetexpectedstatus@example.com", "Password123!"
    )
    today = user_timezone_today()
    source = _create_income_source(client, headers, "Salary")
    expected = _create_expected_income(
        client,
        headers,
        source_id=source["id"],
        amount=5_000_000,
        due_date=today,
    )
    created = create_budget(
        client,
        headers,
        category="Food",
        monthly_limit=12_000_000,
        budget_year=today.year,
        budget_month=today.month,
    )
    assert created.status_code == 201, created.text

    status_update = client.patch(
        f"/budgets/expected-incomes/{expected['id']}",
        json={"status": "RECEIVED"},
        headers=headers,
    )
    assert status_update.status_code == 409, status_update.text
    assert status_update.json()["detail"] == "expected_inflow.use_lifecycle_command"

    summary = client.get(
        f"/budgets/month-summary?budget_year={today.year}&budget_month={today.month}",
        headers=headers,
    )
    assert summary.status_code == 200, summary.text
    payload = summary.json()
    assert payload["expected_income_remaining"] == 5_000_000
    assert payload["plan_status"] == "waiting_on_income"
    assert payload["backing_shortfall"] == 0

    reduce = client.patch(
        f"/budgets/item?budget_year={today.year}&budget_month={today.month}&category=Groceries",
        json={"monthly_limit": 9_000_000},
        headers=headers,
    )
    assert reduce.status_code == 200, reduce.text
    assert reduce.json()["monthly_limit"] == 9_000_000


def test_budget_month_summary_reports_over_planned_and_borrowing_pressure(client, session):
    email = "budgetpressure@example.com"
    headers = create_user_and_token(client, "budgetpressure", email, "Password123!")
    today = user_timezone_today()
    user = _get_user(session, email)
    credit_wallet = models.Wallet(
        owner_id=user.id,
        name="Card",
        wallet_type=models.WalletType.CREDIT,
        accounting_type=models.AccountingType.LIABILITY,
        initial_balance=0,
        current_balance=0,
        credit_limit=5_000_000,
        is_default=False,
    )
    session.add(credit_wallet)
    session.commit()
    session.refresh(credit_wallet)

    budget = create_budget(
        client,
        headers,
        category="Food",
        monthly_limit=9_500_000,
        budget_year=today.year,
        budget_month=today.month,
    )
    assert budget.status_code == 201, budget.text

    default_wallet = _default_wallet(session, user.id)
    goal = models.Goals(
        owner_id=user.id,
        title="Protected after plan",
        target_amount=2_000_000,
        status=models.GoalStatus.ACTIVE,
    )
    session.add(goal)
    session.flush()
    session.add(
        models.GoalContributions(
            owner_id=user.id,
            goal_id=goal.id,
            wallet_id=default_wallet.id,
            amount=2_000_000,
            contribution_type=models.GoalContributionType.ALLOCATE,
        )
    )
    session.commit()

    expense = client.post(
        "/expenses/",
        json={
            "title": "Card groceries",
            "amount": 100_000,
            "category": "Groceries",
            "date": today.isoformat(),
            "wallet_id": credit_wallet.id,
        },
        headers=headers,
    )
    assert expense.status_code == 201, expense.text

    summary = client.get(
        f"/budgets/month-summary?budget_year={today.year}&budget_month={today.month}",
        headers=headers,
    )
    assert summary.status_code == 200, summary.text
    payload = summary.json()
    assert payload["plan_status"] == "over_planned"
    assert payload["plan_free_money_remaining"] == -1_500_000
    assert payload["backing_shortfall"] == 1_500_000
    assert payload["borrowing_pressure"] is True


def test_isolated_project_expense_does_not_require_or_hit_monthly_budget(client, session):
    email = "budgetisolated@example.com"
    headers = create_user_and_token(client, "budgetisolated", email, "Password123!")
    today = user_timezone_today()

    project = client.post(
        "/projects",
        json={
            "title": "Home renovation",
            "is_isolated": True,
            "total_limit": 1_000_000,
            "start_date": today.isoformat(),
        },
        headers=headers,
    )
    assert project.status_code == 201, project.text

    expense = client.post(
        "/expenses/",
        json={
            "title": "Project paint",
            "amount": 200_000,
            "category": "Housing",
            "date": today.isoformat(),
            "project_id": project.json()["id"],
        },
        headers=headers,
    )
    assert expense.status_code == 201, expense.text
    event = session.get(models.FinancialEvent, expense.json()["id"])
    assert event.entity_legs[0].budget_id is None

    missing_budget = client.get(
        f"/budgets/item?budget_year={today.year}&budget_month={today.month}&category=Housing",
        headers=headers,
    )
    assert missing_budget.status_code == 404

    projects = client.get("/budgets/projects", headers=headers)
    assert projects.status_code == 200, projects.text
    project_row = next(item for item in projects.json() if item["id"] == project.json()["id"])
    assert project_row["spent"] == 200_000


def test_overlay_project_expense_still_requires_and_hits_monthly_budget(client):
    headers = create_user_and_token(
        client, "budgetoverlay", "budgetoverlay@example.com", "Password123!"
    )
    today = user_timezone_today()
    project = client.post(
        "/projects",
        json={
            "title": "Work trip",
            "is_isolated": False,
            "total_limit": 1_000_000,
            "start_date": today.isoformat(),
        },
        headers=headers,
    )
    assert project.status_code == 201, project.text

    missing_budget = client.post(
        "/expenses/",
        json={
            "title": "Trip taxi",
            "amount": 100_000,
            "category": "Transport",
            "date": today.isoformat(),
            "project_id": project.json()["id"],
        },
        headers=headers,
    )
    assert missing_budget.status_code == 400
    assert missing_budget.json()["detail"] == "expenses.budget_required"

    budget = create_budget(
        client,
        headers,
        category="Transport",
        monthly_limit=500_000,
        budget_year=today.year,
        budget_month=today.month,
    )
    assert budget.status_code == 201, budget.text

    expense = client.post(
        "/expenses/",
        json={
            "title": "Trip taxi",
            "amount": 100_000,
            "category": "Transport",
            "date": today.isoformat(),
            "project_id": project.json()["id"],
        },
        headers=headers,
    )
    assert expense.status_code == 201, expense.text

    budget_after = client.get(
        f"/budgets/item?budget_year={today.year}&budget_month={today.month}&category=Transport",
        headers=headers,
    )
    assert budget_after.status_code == 200, budget_after.text
    assert budget_after.json()["spent"] == 100_000


def test_overlay_project_reservations_are_month_scoped_and_reduce_general_bucket(client):
    headers = create_user_and_token(
        client, "overlaymonth", "overlaymonth@example.com", "Password123!"
    )
    other_headers = create_user_and_token(
        client, "overlayother", "overlayother@example.com", "Password123!"
    )

    june_budget = create_budget(
        client,
        headers,
        category="Travel",
        monthly_limit=1_000_000,
        budget_year=2026,
        budget_month=6,
    )
    assert june_budget.status_code == 201, june_budget.text
    july_budget = create_budget(
        client,
        headers,
        category="Travel",
        monthly_limit=1_000_000,
        budget_year=2026,
        budget_month=7,
    )
    assert july_budget.status_code == 201, july_budget.text

    project = client.post(
        "/projects",
        json={
            "title": "Conference",
            "is_isolated": False,
            "start_date": "2026-06-01",
            "target_end_date": "2026-07-31",
        },
        headers=headers,
    )
    assert project.status_code == 201, project.text
    project_id = project.json()["id"]

    reservation = client.post(
        f"/projects/{project_id}/category-limits",
        json={
            "category": "Travel",
            "limit_amount": 400_000,
            "budget_year": 2026,
            "budget_month": 6,
        },
        headers=headers,
    )
    assert reservation.status_code == 201, reservation.text
    assert reservation.json()["selected_month_reserved_amount"] == 400_000
    assert reservation.json()["category_breakdown"][0]["budget_year"] == 2026
    assert reservation.json()["category_breakdown"][0]["budget_month"] == 6

    duplicate = client.post(
        f"/projects/{project_id}/category-limits",
        json={
            "category": "Travel",
            "limit_amount": 100_000,
            "budget_year": 2026,
            "budget_month": 6,
        },
        headers=headers,
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["detail"] == "projects.category_limit_exists"

    other_budget = create_budget(
        client,
        other_headers,
        category="Travel",
        monthly_limit=2_000_000,
        budget_year=2026,
        budget_month=6,
    )
    assert other_budget.status_code == 201, other_budget.text
    other_project = client.post(
        "/projects",
        json={
            "title": "Other conference",
            "is_isolated": False,
            "start_date": "2026-06-01",
        },
        headers=other_headers,
    )
    assert other_project.status_code == 201, other_project.text
    other_reservation = client.post(
        f"/projects/{other_project.json()['id']}/category-limits",
        json={
            "category": "Travel",
            "limit_amount": 900_000,
            "budget_year": 2026,
            "budget_month": 6,
        },
        headers=other_headers,
    )
    assert other_reservation.status_code == 201, other_reservation.text

    june_detail = client.get(
        "/budgets/item/detail",
        params={"budget_year": 2026, "budget_month": 6, "category": "Travel"},
        headers=headers,
    )
    assert june_detail.status_code == 200, june_detail.text
    assert june_detail.json()["project_reserved_amount"] == 400_000
    assert june_detail.json()["free_general_limit"] == 600_000
    assert june_detail.json()["project_reservations"][0]["reserved_amount"] == 400_000

    july_detail = client.get(
        "/budgets/item/detail",
        params={"budget_year": 2026, "budget_month": 7, "category": "Travel"},
        headers=headers,
    )
    assert july_detail.status_code == 200, july_detail.text
    assert july_detail.json()["project_reserved_amount"] == 0
    assert july_detail.json()["free_general_limit"] == 1_000_000


def test_overlay_project_can_overspend_local_reservation_without_blocking_parent_budget(client):
    headers = create_user_and_token(
        client, "overlayoverspend", "overlayoverspend@example.com", "Password123!"
    )
    budget = create_budget(
        client,
        headers,
        category="Travel",
        monthly_limit=1_000_000,
        budget_year=2026,
        budget_month=6,
    )
    assert budget.status_code == 201, budget.text

    project = client.post(
        "/projects",
        json={
            "title": "June trip",
            "is_isolated": False,
            "start_date": "2026-06-01",
            "target_end_date": "2026-06-30",
        },
        headers=headers,
    )
    assert project.status_code == 201, project.text
    project_id = project.json()["id"]

    reservation = client.post(
        f"/projects/{project_id}/category-limits",
        json={
            "category": "Travel",
            "limit_amount": 400_000,
            "budget_year": 2026,
            "budget_month": 6,
        },
        headers=headers,
    )
    assert reservation.status_code == 201, reservation.text

    expense = client.post(
        "/expenses/",
        json={
            "title": "Hotel",
            "amount": 500_000,
            "category": "Travel",
            "date": "2026-06-10",
            "project_id": project_id,
        },
        headers=headers,
    )
    assert expense.status_code == 201, expense.text

    detail = client.get(
        "/budgets/item/detail",
        params={"budget_year": 2026, "budget_month": 6, "category": "Travel"},
        headers=headers,
    )
    assert detail.status_code == 200, detail.text
    payload = detail.json()
    assert payload["spent"] == 500_000
    assert payload["project_reserved_amount"] == 400_000
    assert payload["project_spent_amount"] == 500_000
    assert payload["free_general_limit"] == 600_000
    assert payload["free_general_remaining"] == 500_000
    assert payload["project_reservations"][0]["remaining"] == -100_000
    assert payload["project_reservations"][0]["is_over_limit"] is True

    projects = client.get(
        "/projects",
        params={"budget_year": 2026, "budget_month": 6},
        headers=headers,
    )
    assert projects.status_code == 200, projects.text
    project_row = next(item for item in projects.json() if item["id"] == project_id)
    assert project_row["selected_month_reserved_amount"] == 400_000
    assert project_row["total_reserved_scope"] == 400_000
    assert project_row["category_breakdown"][0]["remaining"] == -100_000


def test_get_budgets_does_not_auto_rollover_unused_room(client):
    email = "norolloverbudget@example.com"
    headers = create_user_and_token(
        client, "norolloverbudget", email, "Password123!"
    )

    create_budget(client, headers, category="Food", monthly_limit=300, budget_year=2026, budget_month=1)
    create_budget(client, headers, category="Food", monthly_limit=300, budget_year=2026, budget_month=2)

    jan_expense = client.post(
        "/expenses/",
        json={
            "title": "Jan food",
            "amount": 200,
            "category": "Groceries",
            "date": "2026-01-10",
        },
        headers=headers,
    )
    assert jan_expense.status_code == 201, jan_expense.text

    res = client.get("/budgets/", headers=headers)
    assert res.status_code == 200
    data = res.json()

    jan = next(b for b in data if b["category"] == "Groceries" and b["budget_year"] == 2026 and b["budget_month"] == 1)
    feb = next(b for b in data if b["category"] == "Groceries" and b["budget_year"] == 2026 and b["budget_month"] == 2)

    assert jan["monthly_limit"] == 300
    assert "rollover_amount" not in jan
    assert jan["effective_monthly_limit"] == 300
    assert jan["spent"] == 200

    assert feb["monthly_limit"] == 300
    assert "rollover_amount" not in feb
    assert feb["effective_monthly_limit"] == 300


def test_month_setup_preview_modes_are_read_only_and_show_floor_repair(client, session):
    email = "monthsetuppreview@example.com"
    headers = create_user_and_token(
        client, "monthsetuppreview", email, "Password123!"
    )
    today = user_timezone_today()
    target_year, target_month = _next_month(today)
    user = _get_user(session, email)

    source_budget = create_budget(
        client,
        headers,
        category="Food",
        monthly_limit=100_000,
        budget_year=today.year,
        budget_month=today.month,
    )
    assert source_budget.status_code == 201, source_budget.text
    source_budget_id = source_budget.json()["id"]

    subcategory = client.post(
        f"/budgets/{source_budget_id}/subcategories",
        json={
            "category": "Groceries",
            "name": "Staples",
            "monthly_limit": 40_000,
            "is_active": True,
        },
        headers=headers,
    )
    assert subcategory.status_code == 201, subcategory.text

    session.add(
        models.RecurringExpense(
            owner_id=user.id,
            title="Grocery box",
            amount=250_000,
            category=models.ExpenseCategory.GROCERIES,
            frequency=models.RecurringFrequency.MONTHLY,
            start_date=date(target_year, target_month, 5),
            next_due_date=date(target_year, target_month, 5),
            status=models.RecurringStatus.ACTIVE,
            cycle_behavior=models.CycleBehavior.FIXED,
            original_due_day=5,
        )
    )
    session.commit()

    scratch = client.post(
        "/budgets/month-setup/preview",
        json={
            "budget_year": target_year,
            "budget_month": target_month,
            "mode": "PLAN_FROM_SCRATCH",
        },
        headers=headers,
    )
    assert scratch.status_code == 200, scratch.text
    scratch_groceries = next(
        item for item in scratch.json()["category_proposals"] if item["category"] == "Groceries"
    )
    assert scratch_groceries["proposed_monthly_limit"] == 0
    assert scratch_groceries["floor_amount"] == 250_000
    assert scratch_groceries["copied_from_previous"] is False

    copy = client.post(
        "/budgets/month-setup/preview",
        json={
            "budget_year": target_year,
            "budget_month": target_month,
            "mode": "COPY_PREVIOUS_MONTH",
        },
        headers=headers,
    )
    assert copy.status_code == 200, copy.text
    copy_groceries = next(
        item for item in copy.json()["category_proposals"] if item["category"] == "Groceries"
    )
    assert copy_groceries["proposed_monthly_limit"] == 100_000
    assert copy_groceries["floor_shortfall"] == 150_000
    assert copy_groceries["copied_from_previous"] is True
    assert copy_groceries["subcategory_limits"] == [
        {"subcategory_id": subcategory.json()["id"], "name": "Staples", "monthly_limit": 40_000}
    ]

    smart = client.post(
        "/budgets/month-setup/preview",
        json={
            "budget_year": target_year,
            "budget_month": target_month,
            "mode": "SMART_AUTO_FILL",
        },
        headers=headers,
    )
    assert smart.status_code == 200, smart.text
    smart_groceries = next(
        item for item in smart.json()["category_proposals"] if item["category"] == "Groceries"
    )
    assert smart_groceries["proposed_monthly_limit"] == 250_000
    assert smart_groceries["floor_shortfall"] == 0
    assert smart_groceries["floor_sources"] == ["recurring"]

    target_budget = client.get(
        f"/budgets/item?budget_year={target_year}&budget_month={target_month}&category=Groceries",
        headers=headers,
    )
    assert target_budget.status_code == 404


def test_month_setup_apply_copies_previous_month_and_smart_fills_floors(client, session):
    email = "monthsetupapply@example.com"
    headers = create_user_and_token(
        client, "monthsetupapply", email, "Password123!"
    )
    today = user_timezone_today()
    target_year, target_month = _next_month(today)
    _get_user(session, email)

    source_budget = create_budget(
        client,
        headers,
        category="Food",
        monthly_limit=100_000,
        budget_year=today.year,
        budget_month=today.month,
    )
    assert source_budget.status_code == 201, source_budget.text
    source_budget_id = source_budget.json()["id"]
    subcategory = client.post(
        f"/budgets/{source_budget_id}/subcategories",
        json={
            "category": "Groceries",
            "name": "Staples",
            "monthly_limit": 40_000,
            "is_active": True,
        },
        headers=headers,
    )
    assert subcategory.status_code == 201, subcategory.text

    copy_apply = client.post(
        "/budgets/month-setup/apply",
        json={
            "budget_year": target_year,
            "budget_month": target_month,
            "mode": "COPY_PREVIOUS_MONTH",
        },
        headers=headers,
    )
    assert copy_apply.status_code == 200, copy_apply.text

    copied_detail = client.get(
        f"/budgets/item/detail?budget_year={target_year}&budget_month={target_month}&category=Groceries",
        headers=headers,
    )
    assert copied_detail.status_code == 200, copied_detail.text
    copied_payload = copied_detail.json()
    assert copied_payload["monthly_limit"] == 100_000
    assert copied_payload["subcategories"][0]["id"] == subcategory.json()["id"]
    assert copied_payload["subcategories"][0]["monthly_limit"] == 40_000

    copy_apply_again = client.post(
        "/budgets/month-setup/apply",
        json={
            "budget_year": target_year,
            "budget_month": target_month,
            "mode": "COPY_PREVIOUS_MONTH",
        },
        headers=headers,
    )
    assert copy_apply_again.status_code == 200, copy_apply_again.text
    budgets_after_reapply = client.get("/budgets/", headers=headers)
    matching = [
        item
        for item in budgets_after_reapply.json()
        if item["category"] == "Groceries"
        and item["budget_year"] == target_year
        and item["budget_month"] == target_month
    ]
    assert len(matching) == 1

    smart_email = "monthsetupsmart@example.com"
    smart_headers = create_user_and_token(
        client, "monthsetupsmart", smart_email, "Password123!"
    )
    smart_user = _get_user(session, smart_email)
    smart_source = create_budget(
        client,
        smart_headers,
        category="Food",
        monthly_limit=100_000,
        budget_year=today.year,
        budget_month=today.month,
    )
    assert smart_source.status_code == 201, smart_source.text
    session.add(
        models.RecurringExpense(
            owner_id=smart_user.id,
            title="Grocery box",
            amount=250_000,
            category=models.ExpenseCategory.GROCERIES,
            frequency=models.RecurringFrequency.MONTHLY,
            start_date=date(target_year, target_month, 5),
            next_due_date=date(target_year, target_month, 5),
            status=models.RecurringStatus.ACTIVE,
            cycle_behavior=models.CycleBehavior.FIXED,
            original_due_day=5,
        )
    )
    session.commit()

    smart_apply = client.post(
        "/budgets/month-setup/apply",
        json={
            "budget_year": target_year,
            "budget_month": target_month,
            "mode": "SMART_AUTO_FILL",
        },
        headers=smart_headers,
    )
    assert smart_apply.status_code == 200, smart_apply.text
    smart_detail = client.get(
        f"/budgets/item/detail?budget_year={target_year}&budget_month={target_month}&category=Groceries",
        headers=smart_headers,
    )
    assert smart_detail.status_code == 200, smart_detail.text
    assert smart_detail.json()["monthly_limit"] == 250_000


def test_get_budget_by_category(client):
    headers = create_user_and_token(
        client, "getbudget", "getbudget@example.com", "Password123!"
    )
    today = date.today()
    create_budget(client, headers, category="Food", monthly_limit=300, budget_year=today.year, budget_month=today.month)
    res = client.get(f"/budgets/item?budget_year={today.year}&budget_month={today.month}&category=Groceries", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["category"] == "Groceries"
    assert "spent" in data


def test_update_budget(client):
    headers = create_user_and_token(
        client, "updatebudget", "updatebudget@example.com", "Password123!"
    )
    today = date.today()
    create_budget(client, headers, category="Food", monthly_limit=300, budget_year=today.year, budget_month=today.month)
    res = client.patch(f"/budgets/item?budget_year={today.year}&budget_month={today.month}&category=Groceries", json={"monthly_limit": 800}, headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["monthly_limit"] == 800
    assert "spent" in data


def test_budget_sweep_fields_are_removed_from_api_contract(client):
    headers = create_user_and_token(
        client, "budgetsweepremoved", "budgetsweepremoved@example.com", "Password123!"
    )
    today = user_timezone_today()

    created = client.post(
        "/budgets/",
        json={
            "category": "Groceries",
            "monthly_limit": 300,
            "budget_year": today.year,
            "budget_month": today.month,
            "sweep_target_goal_id": 123,
        },
        headers=headers,
    )
    assert created.status_code == 201, created.text
    payload = created.json()
    assert "sweep_target_goal_id" not in payload
    assert "sweep_amount" not in payload

    updated = client.patch(
        f"/budgets/item?budget_year={today.year}&budget_month={today.month}&category=Groceries",
        json={"sweep_target_goal_id": 456},
        headers=headers,
    )
    assert updated.status_code == 422
    assert "budgets.sweep_removed" not in updated.text


def test_budget_rollover_fields_are_removed_from_api_contract(client):
    headers = create_user_and_token(
        client, "budgetrolloverremoved", "budgetrolloverremoved@example.com", "Password123!"
    )
    today = user_timezone_today()

    created = client.post(
        "/budgets/",
        json={
            "category": "Groceries",
            "monthly_limit": 300,
            "budget_year": today.year,
            "budget_month": today.month,
            "max_rollover_amount": 100,
            "rollover_mode": "FIXED",
        },
        headers=headers,
    )
    assert created.status_code == 201, created.text
    payload = created.json()
    assert "max_rollover_amount" not in payload
    assert "rollover_mode" not in payload
    assert "rollover_amount" not in payload

    updated = client.patch(
        f"/budgets/item?budget_year={today.year}&budget_month={today.month}&category=Groceries",
        json={"max_rollover_amount": 100, "rollover_mode": "FIXED"},
        headers=headers,
    )
    assert updated.status_code == 422
    assert "budgets.rollover_mode_invalid" not in updated.text
    assert "budgets.rollover_percent_invalid" not in updated.text


def test_budget_effective_limit_ignores_historical_rollover_ledger(client, session):
    email = "historicalrollover@example.com"
    headers = create_user_and_token(client, "historicalrollover", email, "Password123!")
    today = user_timezone_today()
    created = create_budget(
        client,
        headers,
        category="Food",
        monthly_limit=1_000,
        budget_year=today.year,
        budget_month=today.month,
    )
    assert created.status_code == 201, created.text

    user = _get_user(session, email)
    session.add(
        models.BudgetLedger(
            owner_id=user.id,
            category=models.ExpenseCategory.GROCERIES,
            budget_year=today.year,
            budget_month=today.month,
            entry_type="ROLLOVER",
            amount=250,
        )
    )
    session.commit()

    budget = client.get(
        f"/budgets/item?budget_year={today.year}&budget_month={today.month}&category=Groceries",
        headers=headers,
    )
    assert budget.status_code == 200, budget.text
    payload = budget.json()
    assert payload["effective_monthly_limit"] == 1_000
    assert "rollover_amount" not in payload


def test_budget_effective_limit_ignores_historical_sweep_ledger(client, session):
    email = "historicalsweep@example.com"
    headers = create_user_and_token(client, "historicalsweep", email, "Password123!")
    today = user_timezone_today()
    created = create_budget(
        client,
        headers,
        category="Food",
        monthly_limit=1_000,
        budget_year=today.year,
        budget_month=today.month,
    )
    assert created.status_code == 201, created.text

    user = _get_user(session, email)
    session.add(
        models.BudgetLedger(
            owner_id=user.id,
            category=models.ExpenseCategory.GROCERIES,
            budget_year=today.year,
            budget_month=today.month,
            entry_type="SWEEP",
            amount=-250,
        )
    )
    session.commit()

    budget = client.get(
        f"/budgets/item?budget_year={today.year}&budget_month={today.month}&category=Groceries",
        headers=headers,
    )
    assert budget.status_code == 200, budget.text
    payload = budget.json()
    assert payload["effective_monthly_limit"] == 1_000
    assert "sweep_amount" not in payload


def test_delete_budget(client):
    headers = create_user_and_token(
        client, "deletebudget", "deletebudget@example.com", "Password123!"
    )
    today = date.today()
    create_budget(client, headers, category="Food", monthly_limit=300, budget_year=today.year, budget_month=today.month)
    res = client.delete(f"/budgets/item?budget_year={today.year}&budget_month={today.month}&category=Groceries", headers=headers)
    assert res.status_code == 204
    res_list = client.get("/budgets/", headers=headers)
    assert res_list.status_code == 200
    assert res_list.json() == []


def test_delete_budget_blocks_when_linked_expenses_exist(client):
    headers = create_user_and_token(
        client, "deletebudgetlinked", "deletebudgetlinked@example.com", "Password123!"
    )
    today = date.today()
    create_budget(
        client,
        headers,
        category="Food",
        monthly_limit=300,
        budget_year=today.year,
        budget_month=today.month,
    )
    expense_res = client.post(
        "/expenses/",
        json={
            "title": "Linked expense",
            "amount": 10,
            "category": "Groceries",
            "description": "test",
            "date": today.isoformat(),
        },
        headers=headers,
    )
    assert expense_res.status_code == 201, expense_res.text

    res = client.delete(f"/budgets/item?budget_year={today.year}&budget_month={today.month}&category=Groceries", headers=headers)
    assert res.status_code == 409
    assert res.json()["detail"] == "budgets.has_linked_expenses"

    still_exists = client.get(f"/budgets/item?budget_year={today.year}&budget_month={today.month}&category=Groceries", headers=headers)
    assert still_exists.status_code == 200


def test_budget_write_rate_limit_blocks_burst(client):
    for key in redis_client.scan_iter("tb:budgets_write:*"):
        redis_client.delete(key)

    headers = create_user_and_token(
        client, "budgetrtlim", "budgetrtlim@example.com", "Password123!"
    )
    
    blocked = None
    # BUDGET_WRITE_BUCKET_CAPACITY is 10, so 15 requests should trigger it
    for i in range(15):
        res = client.post(
            "/budgets/",
            json={"category": "Groceries", "monthly_limit": 500 + i, "budget_year": 2026, "budget_month": i % 12 + 1},
            headers=headers
        )
        if res.status_code == 429:
            blocked = res
            break

    assert blocked is not None
    assert blocked.status_code == 429
    assert "Retry-After" in blocked.headers
    assert blocked.json()["detail"] == "budgets.write_rate_limited"


def test_budget_cash_allocation_uses_hamilton_method(client, session):
    email = "budgethamilton@example.com"
    headers = create_user_and_token(client, "budgethamilton", email, "Password123!")
    today = user_timezone_today()
    user = _get_user(session, email)
    default_wallet = _default_wallet(session, user.id)
    
    credit_wallet = models.Wallet(
        owner_id=user.id,
        name="Credit Card",
        wallet_type=models.WalletType.CREDIT,
        accounting_type=models.AccountingType.LIABILITY,
        initial_balance=0,
        current_balance=0,
        credit_limit=10_000_000,
        is_default=False,
    )
    session.add(credit_wallet)
    session.commit()
    session.refresh(credit_wallet)

    _ = create_budget(
        client, headers, category="Groceries", monthly_limit=5_000_000, budget_year=today.year, budget_month=today.month
    )
    _ = create_budget(
        client, headers, category="Transport", monthly_limit=5_000_000, budget_year=today.year, budget_month=today.month
    )

    # 100 total spent. 33 cash, 67 credit.
    # Split: 50 Food, 50 Transport.
    # Base allocation: (50 * 33) / 100 = 16.5
    # Integer division would give 16 to both (total 32, losing 1).
    # Hamilton method should give 17 to one, 16 to the other.
    expense = client.post(
        "/expenses/",
        json={
            "title": "Split uneven",
            "amount": 100,
            "category": "Groceries",
            "date": today.isoformat(),
            "wallet_allocations": [
                {"wallet_id": default_wallet.id, "amount": 33},
                {"wallet_id": credit_wallet.id, "amount": 67},
            ]
        },
        headers=headers,
    )
    assert expense.status_code == 201, expense.text
    expense_id = expense.json()["id"]

    split = client.post(
        f"/expenses/{expense_id}/split",
        json={
            "items": [
                {"amount": 50, "category": "Groceries", "label": "Food portion"},
                {"amount": 50, "category": "Transport", "label": "Transport portion"},
            ]
        },
        headers=headers,
    )
    assert split.status_code == 200 or split.status_code == 201, split.text

    summary = client.get(f"/budgets/month-summary?budget_year={today.year}&budget_month={today.month}", headers=headers)
    assert summary.status_code == 200, summary.text
    payload = summary.json()
    
    # Check that exactly 33 cash was allocated
    assert payload["valid_budget_spent"] == 33
