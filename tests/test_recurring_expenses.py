from datetime import date

from tests.helpers import create_user_and_token, create_budget
from app.main import app
from app.session import get_db
from app import models
from app.scheduler import process_due_recurring_expenses

def _make_user_premium(email: str):
    override_db_factory = app.dependency_overrides.get(get_db)
    if override_db_factory:
        db_gen = override_db_factory()
        db = next(db_gen)
        try:
            user = db.query(models.User).filter(models.User.email == email).first()
            if user:
                user.is_premium = True
                db.commit()
        finally:
            db.close()
            try:
                next(db_gen)
            except StopIteration:
                pass


def _get_test_db():
    override_db_factory = app.dependency_overrides.get(get_db)
    if override_db_factory is None:
        raise RuntimeError("Missing DB override in tests")
    db_gen = override_db_factory()
    db = next(db_gen)
    return db_gen, db

def test_create_recurring_expense_premium(client):
    email = "req_usr@example.com"
    headers = create_user_and_token(client, "req_usr", email, "Password123!")
    _make_user_premium(email)
    create_budget(client, headers, category="Entertainment", monthly_limit=500000)
    
    payload = {
        "title": "Netflix",
        "amount": 15000,
        "category": "Entertainment",
        "description": "Monthly subscription",
        "frequency": "MONTHLY",
        "start_date": date.today().isoformat()
    }
    
    res = client.post("/recurring/", json=payload, headers=headers)
    assert res.status_code == 201
    
    data = res.json()
    assert data["title"] == "Netflix"
    assert data["amount"] == 15000
    assert data["frequency"] == "MONTHLY"
    assert data["is_active"] is True
    assert isinstance(data["days_until_due"], int)

def test_get_recurring_expenses_premium(client):
    email = "req_get@example.com"
    headers = create_user_and_token(client, "req_get", email, "Password123!")
    _make_user_premium(email)
    create_budget(client, headers, category="Utilities", monthly_limit=500000)
    
    for i in range(3):
        client.post("/recurring/", json={
            "title": f"Sub {i}",
            "amount": 1000,
            "category": "Utilities",
            "frequency": "MONTHLY",
            "start_date": date.today().isoformat()
        }, headers=headers)
        
    res = client.get("/recurring/", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 3
    assert all(isinstance(item["days_until_due"], int) for item in data)

def test_update_recurring_expense(client):
    email = "req_upd@example.com"
    headers = create_user_and_token(client, "req_upd", email, "Password123!")
    _make_user_premium(email)
    create_budget(client, headers, category="Entertainment", monthly_limit=500000)
    
    res = client.post("/recurring/", json={
        "title": "Spotify",
        "amount": 1000,
        "category": "Entertainment",
        "frequency": "MONTHLY",
        "start_date": date.today().isoformat()
    }, headers=headers)
    req_id = res.json()["id"]
    
    updated = client.put(f"/recurring/{req_id}", json={
        "title": "Spotify Premium",
        "amount": 2000,
        "category": "Entertainment",
        "description": "Family plan"
    }, headers=headers)
    
    assert updated.status_code == 200
    assert updated.json()["title"] == "Spotify Premium"
    # Frequency cannot be checked against "YEARLY" since we didn't (and couldn't) update it.
    # The original frequency was "MONTHLY", so it should still be "MONTHLY".
    assert updated.json()["frequency"] == "MONTHLY"
    assert isinstance(updated.json()["days_until_due"], int)

def test_patch_recurring_expense_status(client):
    email = "req_patch@example.com"
    headers = create_user_and_token(client, "req_patch", email, "Password123!")
    _make_user_premium(email)
    create_budget(client, headers, category="Utilities", monthly_limit=500000)
    
    res = client.post("/recurring/", json={
        "title": "Gym",
        "amount": 5000,
        "category": "Utilities",
        "frequency": "MONTHLY",
        "start_date": date.today().isoformat()
    }, headers=headers)
    req_id = res.json()["id"]
    
    patch_res = client.patch(f"/recurring/{req_id}/active", json={"is_active": False}, headers=headers)
    assert patch_res.status_code == 200
    assert patch_res.json()["is_active"] is False
    assert isinstance(patch_res.json()["days_until_due"], int)

def test_delete_recurring_expense(client):
    email = "req_del@example.com"
    headers = create_user_and_token(client, "req_del", email, "Password123!")
    _make_user_premium(email)
    create_budget(client, headers, category="Utilities", monthly_limit=500000)
    
    res = client.post("/recurring/", json={
        "title": "To Delete",
        "amount": 5000,
        "category": "Utilities",
        "frequency": "MONTHLY",
        "start_date": date.today().isoformat()
    }, headers=headers)
    assert res.status_code == 201
    req_id = res.json()["id"]
    
    del_res = client.delete(f"/recurring/{req_id}", headers=headers)
    assert del_res.status_code == 204
    
    # We can't GET by ID directly since no endpoint exists for /recurring/{id}
    # We check if it is included in the list
    get_res = client.get("/recurring/", headers=headers)
    assert get_res.status_code == 200
    assert len(get_res.json()) == 0

def test_free_user_forbidden(client):
    email = "req_free@example.com"
    headers = create_user_and_token(client, "req_free", email, "Password123!")
    
    # User is intentionally NOT made premium
    res = client.post("/recurring/", json={
        "title": "Sub",
        "amount": 100,
        "category": "Utilities",
        "frequency": "MONTHLY",
        "start_date": date.today().isoformat()
    }, headers=headers)
    assert res.status_code == 403


def test_create_recurring_auto_creates_fallback_budget_when_no_history(client):
    email = "req_autobudget@example.com"
    headers = create_user_and_token(client, "req_autobudget", email, "Password123!")
    _make_user_premium(email)
    today = date.today()

    res = client.post("/recurring/", json={
        "title": "Auto Budget Seed",
        "amount": 12000,
        "category": "Utilities",
        "frequency": "MONTHLY",
        "start_date": today.isoformat(),
    }, headers=headers)
    assert res.status_code == 201

    db_gen, db = _get_test_db()
    try:
        user = db.query(models.User).filter(models.User.email == email).first()
        assert user is not None
        budget = db.query(models.Budget).filter(
            models.Budget.owner_id == user.id,
            models.Budget.category == models.ExpenseCategory.UTILITIES,
            models.Budget.budget_year == today.year,
            models.Budget.budget_month == today.month,
        ).first()
        assert budget is not None
        assert budget.auto_created is True
        assert budget.monthly_limit == 50000
    finally:
        db.close()
        try:
            next(db_gen)
        except StopIteration:
            pass


def test_scheduler_recreates_budget_after_manual_budget_and_expense_deletion(client):
    email = "req_recreate_after_delete@example.com"
    headers = create_user_and_token(client, "req_recreate_after_delete", email, "Password123!")
    _make_user_premium(email)
    today = date.today()

    res = client.post("/recurring/", json={
        "title": "Daily Auto Budget",
        "amount": 7000,
        "category": "Utilities",
        "frequency": "DAILY",
        "start_date": today.isoformat(),
    }, headers=headers)
    assert res.status_code == 201

    exp_list = client.get("/expenses/", headers=headers)
    assert exp_list.status_code == 200
    items = exp_list.json().get("items", [])
    assert len(items) >= 1
    expense_id = items[0]["id"]
    del_exp = client.delete(f"/expenses/{expense_id}", headers=headers)
    assert del_exp.status_code == 204

    del_budget = client.delete(f"/budgets/{today.year}/{today.month}/Utilities", headers=headers)
    assert del_budget.status_code == 204
    get_deleted_budget = client.get(f"/budgets/{today.year}/{today.month}/Utilities", headers=headers)
    assert get_deleted_budget.status_code == 404

    db_gen, db = _get_test_db()
    try:
        user = db.query(models.User).filter(models.User.email == email).first()
        assert user is not None
        recurring = db.query(models.RecurringExpense).filter(
            models.RecurringExpense.owner_id == user.id
        ).first()
        assert recurring is not None
        recurring.next_due_date = today
        db.commit()

        process_due_recurring_expenses(db)

        recreated_budget = db.query(models.Budget).filter(
            models.Budget.owner_id == user.id,
            models.Budget.category == models.ExpenseCategory.UTILITIES,
            models.Budget.budget_year == today.year,
            models.Budget.budget_month == today.month,
        ).first()
        assert recreated_budget is not None
        assert recreated_budget.auto_created is True
        assert recreated_budget.monthly_limit == 50000

        recreated_expense_count = db.query(models.Expense).filter(
            models.Expense.owner_id == user.id,
            models.Expense.category == models.ExpenseCategory.UTILITIES,
            models.Expense.date == today,
        ).count()
        assert recreated_expense_count == 1
    finally:
        db.close()
        try:
            next(db_gen)
        except StopIteration:
            pass
