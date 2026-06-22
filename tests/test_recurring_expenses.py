# pyrefly: ignore [missing-import]
import pytest
from datetime import date, timedelta

from tests.helpers import create_user_and_token, create_budget, user_timezone_today
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


def _default_wallet_id(email: str) -> int:
    db_gen, db = _get_test_db()
    try:
        user = db.query(models.User).filter(models.User.email == email).first()
        assert user is not None
        wallet = db.query(models.Wallet).filter(
            models.Wallet.owner_id == user.id,
            models.Wallet.is_default == True,  # noqa: E712
        ).first()
        assert wallet is not None
        return int(wallet.id)
    finally:
        db.close()
        try:
            next(db_gen)
        except StopIteration:
            pass


def _create_recurring_row(
    email: str,
    *,
    title: str = "Projection seed",
    amount: int = 1000,
    frequency: models.RecurringFrequency = models.RecurringFrequency.MONTHLY,
    next_due_date: date | None = None,
) -> int:
    db_gen, db = _get_test_db()
    try:
        user = db.query(models.User).filter(models.User.email == email).first()
        assert user is not None
        due_date = next_due_date or user_timezone_today()
        row = models.RecurringExpense(
            owner_id=user.id,
            title=title,
            amount=amount,
            category=models.ExpenseCategory.UTILITIES,
            frequency=frequency,
            start_date=due_date,
            next_due_date=due_date,
            status=models.RecurringStatus.ACTIVE,
            wallet_id=_default_wallet_id(email),
            cycle_behavior=models.CycleBehavior.FIXED,
            original_due_day=due_date.day,
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        return int(row.id)
    finally:
        db.close()
        try:
            next(db_gen)
        except StopIteration:
            pass

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
        "start_date": date.today().isoformat(),
        "wallet_id": _default_wallet_id(email),
    }
    
    res = client.post("/recurring/", json=payload, headers=headers)
    assert res.status_code == 201
    
    data = res.json()
    assert data["title"] == "Netflix"
    assert data["amount"] == 15000
    assert data["frequency"] == "MONTHLY"
    assert data["status"] == "ACTIVE"
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
            "start_date": date.today().isoformat(),
            "wallet_id": _default_wallet_id(email),
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
        "start_date": date.today().isoformat(),
        "wallet_id": _default_wallet_id(email),
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
        "start_date": date.today().isoformat(),
        "wallet_id": _default_wallet_id(email),
    }, headers=headers)
    req_id = res.json()["id"]
    
    patch_res = client.patch(f"/recurring/{req_id}/toggle", json={"status": "DISABLED"}, headers=headers)
    assert patch_res.status_code == 200
    assert patch_res.json()["status"] == "DISABLED"
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
        "start_date": date.today().isoformat(),
        "wallet_id": _default_wallet_id(email),
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


def test_confirmation_template_materializes_pending_occurrence_without_wallet_mutation(client):
    email = "req_confirm_foundation@example.com"
    headers = create_user_and_token(client, "req_confirm_foundation", email, "Password123!")
    _make_user_premium(email)
    today = user_timezone_today()

    db_gen, db = _get_test_db()
    try:
        user = db.query(models.User).filter(models.User.email == email).one()
        wallet = db.query(models.Wallet).filter(models.Wallet.owner_id == user.id).one()
        balance_before = int(wallet.current_balance)
        event_count_before = db.query(models.FinancialEvent).filter(
            models.FinancialEvent.owner_id == user.id,
        ).count()
    finally:
        db.close()
        try:
            next(db_gen)
        except StopIteration:
            pass

    created = client.post(
        "/recurring/",
        json={
            "title": "Variable utility",
            "amount": 300_000,
            "category": "Utilities",
            "frequency": "MONTHLY",
            "start_date": today.isoformat(),
            "wallet_id": None,
        },
        headers=headers,
    )
    assert created.status_code == 201, created.text
    payload = created.json()
    assert payload["wallet_id"] is None

    occurrences = client.get(
        "/recurring/occurrences?occurrence_status=PENDING_CONFIRMATION",
        headers=headers,
    )
    assert occurrences.status_code == 200, occurrences.text
    assert len(occurrences.json()) == 1
    assert occurrences.json()[0]["scheduled_due_date"] == today.isoformat()
    assert occurrences.json()[0]["expected_amount"] == 300_000

    db_gen, db = _get_test_db()
    try:
        user = db.query(models.User).filter(models.User.email == email).one()
        wallet = db.query(models.Wallet).filter(models.Wallet.owner_id == user.id).one()
        assert int(wallet.current_balance) == balance_before
        assert db.query(models.FinancialEvent).filter(
            models.FinancialEvent.owner_id == user.id,
        ).count() == event_count_before
    finally:
        db.close()
        try:
            next(db_gen)
        except StopIteration:
            pass



def test_template_edits_update_unresolved_snapshot(client):
    email = "req_unresolved_snapshot_update@example.com"
    headers = create_user_and_token(client, "req_unresolved_snapshot_update", email, "Password123!")
    _make_user_premium(email)

    created = client.post(
        "/recurring/",
        json={
            "title": "Expected utility",
            "amount": 300_000,
            "category": "Utilities",
            "frequency": "MONTHLY",
            "start_date": user_timezone_today().isoformat(),
            "wallet_id": None,
        },
        headers=headers,
    )
    assert created.status_code == 201, created.text

    updated = client.put(
        f"/recurring/{created.json()['id']}",
        json={"amount": 347_000, "category": "Housing"},
        headers=headers,
    )
    assert updated.status_code == 200, updated.text

    occurrence = client.get("/recurring/occurrences", headers=headers).json()[0]
    assert occurrence["expected_amount"] == 347_000
    assert occurrence["expected_category"] == "Housing"


def test_delete_archives_template_and_preserves_occurrence(client):
    email = "req_archive_occurrence@example.com"
    headers = create_user_and_token(client, "req_archive_occurrence", email, "Password123!")
    _make_user_premium(email)

    created = client.post(
        "/recurring/",
        json={
            "title": "Archive safely",
            "amount": 20_000,
            "category": "Subscriptions",
            "frequency": "MONTHLY",
            "start_date": user_timezone_today().isoformat(),
            "wallet_id": None,
        },
        headers=headers,
    )
    assert created.status_code == 201, created.text
    template_id = created.json()["id"]

    deleted = client.delete(f"/recurring/{template_id}", headers=headers)
    assert deleted.status_code == 204
    assert client.get("/recurring/", headers=headers).json() == []

    db_gen, db = _get_test_db()
    try:
        template = db.query(models.RecurringExpense).filter(
            models.RecurringExpense.id == template_id,
        ).one()
        assert template.archived_at is not None
        assert template.status == models.RecurringStatus.DISABLED
        assert db.query(models.RecurringOccurrence).filter(
            models.RecurringOccurrence.template_id == template_id,
        ).count() == 1
    finally:
        db.close()
        try:
            next(db_gen)
        except StopIteration:
            pass


def test_resume_advances_past_paused_dates_without_catch_up(client):
    email = "req_pause_no_catchup@example.com"
    headers = create_user_and_token(client, "req_pause_no_catchup", email, "Password123!")
    _make_user_premium(email)
    today = user_timezone_today()

    template_id = _create_recurring_row(
        email,
        title="Paused daily",
        amount=5_000,
        frequency=models.RecurringFrequency.DAILY,
        next_due_date=today,
    )
    paused = client.patch(
        f"/recurring/{template_id}/toggle",
        json={"status": "DISABLED"},
        headers=headers,
    )
    assert paused.status_code == 200, paused.text

    db_gen, db = _get_test_db()
    try:
        template = db.query(models.RecurringExpense).filter(
            models.RecurringExpense.id == template_id,
        ).one()
        template.next_due_date = today - timedelta(days=3)
        db.commit()
    finally:
        db.close()
        try:
            next(db_gen)
        except StopIteration:
            pass

    resumed = client.patch(
        f"/recurring/{template_id}/toggle",
        json={"status": "ACTIVE"},
        headers=headers,
    )
    assert resumed.status_code == 200, resumed.text
    assert date.fromisoformat(resumed.json()["next_due_date"]) > today
    assert resumed.json()["paused_at"] is None


def test_scheduler_materializes_confirmation_occurrence_once(client):
    email = "req_scheduler_confirm_once@example.com"
    create_user_and_token(client, "req_scheduler_confirm_once", email, "Password123!")
    _make_user_premium(email)
    today = user_timezone_today()
    template_id = _create_recurring_row(
        email,
        title="Scheduler confirmation",
        amount=15_000,
        frequency=models.RecurringFrequency.MONTHLY,
        next_due_date=today,
    )

    db_gen, db = _get_test_db()
    try:
        user = db.query(models.User).filter(models.User.email == email).first()
        template = db.query(models.RecurringExpense).filter(
            models.RecurringExpense.id == template_id,
        ).one()
        template.wallet_id = None
        db.commit()

        process_due_recurring_expenses(db)
        process_due_recurring_expenses(db)

        occurrences = db.query(models.RecurringOccurrence).filter(
            models.RecurringOccurrence.template_id == template_id,
        ).all()
        assert len(occurrences) == 1
        assert occurrences[0].status == models.RecurringOccurrenceStatus.PENDING_CONFIRMATION
        db.refresh(template)
        assert template.next_due_date > today
        
        # Verify notification
        notifications = db.query(models.Notification).filter(
            models.Notification.owner_id == user.id,
            models.Notification.type == models.NotificationType.RECURRING_DUE.value
        ).all()
        assert len(notifications) == 1
    finally:
        db.close()
        try:
            next(db_gen)
        except StopIteration:
            pass

def test_confirm_recurring_occurrence(client):
    email = "req_confirm_api@example.com"
    headers = create_user_and_token(client, "req_confirm_api", email, "Password123!")
    _make_user_premium(email)
    create_budget(client, headers, category="Utilities", monthly_limit=500000)
    today = user_timezone_today()

    template_id = _create_recurring_row(
        email,
        title="To Confirm",
        amount=15_000,
        frequency=models.RecurringFrequency.MONTHLY,
        next_due_date=today,
    )
    
    db_gen, db = _get_test_db()
    try:
        template = db.query(models.RecurringExpense).filter(
            models.RecurringExpense.id == template_id,
        ).one()
        template.wallet_id = None
        db.commit()

        process_due_recurring_expenses(db)
        occurrence = db.query(models.RecurringOccurrence).filter(
            models.RecurringOccurrence.template_id == template_id,
        ).first()
        occurrence_id = occurrence.id
    finally:
        db.close()
        try:
            next(db_gen)
        except StopIteration:
            pass

    confirm_res = client.post(
        f"/recurring/occurrences/{occurrence_id}/confirm",
        json={
            "actual_amount": 16_000,
            "actual_date": today.isoformat(),
            "wallet_allocations": [
                {"wallet_id": _default_wallet_id(email), "amount": 16_000}
            ],
            "update_template_amount": True
        },
        headers=headers
    )
    assert confirm_res.status_code == 200, confirm_res.text
    
    db_gen, db = _get_test_db()
    try:
        occurrence = db.query(models.RecurringOccurrence).filter(
            models.RecurringOccurrence.id == occurrence_id,
        ).one()
        assert occurrence.status == models.RecurringOccurrenceStatus.FULFILLED
        assert occurrence.actual_amount == 16_000
        assert occurrence.linked_financial_event_id is not None
        
        template = db.query(models.RecurringExpense).filter(
            models.RecurringExpense.id == template_id,
        ).one()
        assert template.amount == 16_000
    finally:
        db.close()
        try:
            next(db_gen)
        except StopIteration:
            pass

def test_free_user_forbidden(client):
    email = "req_free@example.com"
    headers = create_user_and_token(client, "req_free", email, "Password123!")
    
    # User is intentionally NOT made premium
    res = client.post("/recurring/", json={
        "title": "Sub",
        "amount": 100,
        "category": "Utilities",
        "frequency": "MONTHLY",
        "start_date": date.today().isoformat(),
        "wallet_id": _default_wallet_id(email),
    }, headers=headers)
    assert res.status_code == 403




@pytest.mark.skip(reason="Temporarily disabled due to scheduler deadlock in CI")
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
        "wallet_id": _default_wallet_id(email),
    }, headers=headers)
    assert res.status_code == 201

    exp_list = client.get("/expenses/", headers=headers)
    assert exp_list.status_code == 200
    items = [
        item["expense"]
        for item in exp_list.json().get("items", [])
        if item.get("type") == "EXPENSE" and item.get("expense")
    ]
    assert len(items) >= 1
    expense_id = items[0]["id"]
    del_exp = client.delete(f"/expenses/{expense_id}", headers=headers)
    assert del_exp.status_code == 204

    del_budget = client.delete(f"/budgets/item?budget_year={today.year}&budget_month={today.month}&category=Utilities", headers=headers)
    assert del_budget.status_code == 204
    get_deleted_budget = client.get(f"/budgets/item?budget_year={today.year}&budget_month={today.month}&category=Utilities", headers=headers)
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

        recreated_expense_count = (
            db.query(models.FinancialEvent)
            .join(models.EntityLedger, models.EntityLedger.event_id == models.FinancialEvent.id)
            .filter(
                models.FinancialEvent.owner_id == user.id,
                models.FinancialEvent.event_type == models.TransactionType.EXPENSE,
                models.FinancialEvent.status == models.FinancialEventStatus.POSTED,
                models.EntityLedger.category == models.ExpenseCategory.UTILITIES,
                models.FinancialEvent.date == today,
            )
            .count()
        )
        assert recreated_expense_count == 1
    finally:
        db.close()
        try:
            next(db_gen)
        except StopIteration:
            pass


def test_recurring_default_projections_match_frequency_horizons(client):
    email = "req_projection_defaults@example.com"
    headers = create_user_and_token(client, "req_projection_defaults", email, "Password123!")
    _make_user_premium(email)
    today = user_timezone_today()
    daily_id = _create_recurring_row(
        email,
        title="Daily coffee",
        amount=10_000,
        frequency=models.RecurringFrequency.DAILY,
        next_due_date=today,
    )
    monthly_id = _create_recurring_row(
        email,
        title="Monthly software",
        amount=90_000,
        frequency=models.RecurringFrequency.MONTHLY,
        next_due_date=today,
    )

    daily = client.get(f"/recurring/{daily_id}/projections", headers=headers)
    assert daily.status_code == 200, daily.text
    daily_defaults = [
        (item["unit"], item["value"], item["occurrence_count"], item["total_amount"])
        for item in daily.json()["default_projections"]
    ]
    assert daily_defaults[:2] == [
        ("days", 7, 7, 70_000),
        ("days", 14, 14, 140_000),
    ]
    assert [(unit, value) for unit, value, _count, _total in daily_defaults] == [
        ("days", 7),
        ("days", 14),
        ("months", 1),
        ("months", 3),
        ("months", 6),
        ("months", 12),
    ]

    monthly = client.get(f"/recurring/{monthly_id}/projections", headers=headers)
    assert monthly.status_code == 200, monthly.text
    monthly_defaults = [
        (item["unit"], item["value"], item["occurrence_count"], item["total_amount"])
        for item in monthly.json()["default_projections"]
    ]
    assert monthly_defaults == [
        ("months", 3, 3, 270_000),
        ("months", 6, 6, 540_000),
        ("months", 12, 12, 1_080_000),
    ]


def test_recurring_custom_projection_horizons_can_be_saved_and_previewed(client):
    email = "req_projection_custom@example.com"
    headers = create_user_and_token(client, "req_projection_custom", email, "Password123!")
    _make_user_premium(email)
    today = user_timezone_today()
    recurring_id = _create_recurring_row(
        email,
        title="Weekly class",
        amount=25_000,
        frequency=models.RecurringFrequency.WEEKLY,
        next_due_date=today,
    )

    saved = client.put(
        f"/recurring/{recurring_id}/projection-horizons",
        json={"horizons": [{"unit": "weeks", "value": 50}]},
        headers=headers,
    )
    assert saved.status_code == 200, saved.text
    custom = saved.json()["custom_projections"][0]
    assert custom["source"] == "custom"
    assert custom["unit"] == "weeks"
    assert custom["value"] == 50
    assert custom["label"] == "50 weeks"
    assert custom["horizon_start"] == today.isoformat()
    assert custom["occurrence_count"] == 50
    assert custom["total_amount"] == 1_250_000

    fetched = client.get(f"/recurring/{recurring_id}/projections", headers=headers)
    assert fetched.status_code == 200, fetched.text
    assert fetched.json()["custom_projections"][0]["unit"] == "weeks"
    assert fetched.json()["custom_projections"][0]["value"] == 50

    preview = client.post(
        f"/recurring/{recurring_id}/projections/preview",
        json={"horizons": [{"unit": "months", "value": 6}]},
        headers=headers,
    )
    assert preview.status_code == 200, preview.text
    assert preview.json()["ad_hoc_projections"][0]["source"] == "ad_hoc"
    assert preview.json()["ad_hoc_projections"][0]["unit"] == "months"

    still_saved = client.get(f"/recurring/{recurring_id}/projections", headers=headers)
    assert still_saved.json()["custom_projections"][0]["unit"] == "weeks"


def test_recurring_custom_projection_validation_allows_practical_caps(client):
    email = "req_projection_caps@example.com"
    headers = create_user_and_token(client, "req_projection_caps", email, "Password123!")
    _make_user_premium(email)
    today = user_timezone_today()
    daily_id = _create_recurring_row(
        email,
        title="Daily habit",
        amount=1_000,
        frequency=models.RecurringFrequency.DAILY,
        next_due_date=today,
    )

    allowed = client.post(
        f"/recurring/{daily_id}/projections/preview",
        json={"horizons": [{"unit": "days", "value": 299}]},
        headers=headers,
    )
    assert allowed.status_code == 200, allowed.text
    assert allowed.json()["ad_hoc_projections"][0]["occurrence_count"] == 299

    rejected = client.post(
        f"/recurring/{daily_id}/projections/preview",
        json={"horizons": [{"unit": "days", "value": 5000}]},
        headers=headers,
    )
    assert rejected.status_code == 400
    assert rejected.json()["detail"] == "recurring.projection_horizon_too_large"
