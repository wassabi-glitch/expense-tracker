
from app import models
from app.utils import check_budget_alerts
from tests.helpers import create_user_and_token, create_budget, create_expense


def _get_budget(session, user_id, category):
    return session.query(models.Budget).filter(
        models.Budget.owner_id == user_id,
        models.Budget.category == category,
    ).first()


def _get_user_id(session, email):
    user = session.query(models.User).filter(models.User.email == email).first()
    return user.id


def test_budget_alerts_thresholds(client, session):
    headers = create_user_and_token(
        client, "alertuser", "alertuser@example.com", "Password123!"
    )
    create_budget(client, headers, category="Food", monthly_limit=100)

    # 40% -> no alert
    create_expense(client, headers, title="Exp1", amount=40, category="Food")
    user_id = _get_user_id(session, "alertuser@example.com")
    budget = _get_budget(session, user_id, models.ExpenseCategory.GROCERIES)
    check_budget_alerts(session, budget)
    session.refresh(budget)
    assert budget.last_notified_threshold == 0

    # 50% -> alert
    create_expense(client, headers, title="Exp2", amount=10, category="Food")
    budget = _get_budget(session, user_id, models.ExpenseCategory.GROCERIES)
    check_budget_alerts(session, budget)
    session.refresh(budget)
    assert budget.last_notified_threshold == 50

    # 90% -> alert
    create_expense(client, headers, title="Exp3", amount=40, category="Food")
    budget = _get_budget(session, user_id, models.ExpenseCategory.GROCERIES)
    check_budget_alerts(session, budget)
    session.refresh(budget)
    assert budget.last_notified_threshold == 90

    # 100% -> alert
    create_expense(client, headers, title="Exp4", amount=20, category="Food")
    budget = _get_budget(session, user_id, models.ExpenseCategory.GROCERIES)
    check_budget_alerts(session, budget)
    session.refresh(budget)
    assert budget.last_notified_threshold == 100


def test_budget_alerts_reset_below_50(client, session):
    headers = create_user_and_token(
        client, "alertuser2", "alertuser2@example.com", "Password123!"
    )
    create_budget(client, headers, category="Food", monthly_limit=100)

    create_expense(client, headers, title="Exp1", amount=60, category="Food")
    user_id = _get_user_id(session, "alertuser2@example.com")
    budget = _get_budget(session, user_id, models.ExpenseCategory.GROCERIES)
    check_budget_alerts(session, budget)
    session.refresh(budget)
    assert budget.last_notified_threshold == 50

    # Delete expense -> total 0, should reset to 0
    expense = session.query(models.Expense).filter(
        models.Expense.owner_id == user_id,
        models.Expense.category == models.ExpenseCategory.GROCERIES,
    ).first()
    session.delete(expense)
    session.commit()

    budget = _get_budget(session, user_id, models.ExpenseCategory.GROCERIES)
    check_budget_alerts(session, budget)
    session.refresh(budget)
    assert budget.last_notified_threshold == 0
