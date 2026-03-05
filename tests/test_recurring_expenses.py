from datetime import date, timedelta
from app.redis_rate_limiter import redis_client
from tests.helpers import create_user_and_token
from app.main import app
from app.session import get_db
from app import models

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

def test_create_recurring_expense_premium(client):
    email = "req_usr@example.com"
    headers = create_user_and_token(client, "req_usr", email, "Password123!")
    _make_user_premium(email)
    
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

def test_get_recurring_expenses_premium(client):
    email = "req_get@example.com"
    headers = create_user_and_token(client, "req_get", email, "Password123!")
    _make_user_premium(email)
    
    for i in range(3):
        client.post("/recurring/", json={
            "title": f"Sub {i}",
            "amount": 1000,
            "category": "Other",
            "frequency": "MONTHLY",
            "start_date": date.today().isoformat()
        }, headers=headers)
        
    res = client.get("/recurring/", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 3

def test_update_recurring_expense(client):
    email = "req_upd@example.com"
    headers = create_user_and_token(client, "req_upd", email, "Password123!")
    _make_user_premium(email)
    
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

def test_patch_recurring_expense_status(client):
    email = "req_patch@example.com"
    headers = create_user_and_token(client, "req_patch", email, "Password123!")
    _make_user_premium(email)
    
    res = client.post("/recurring/", json={
        "title": "Gym",
        "amount": 5000,
        "category": "Other",
        "frequency": "MONTHLY",
        "start_date": date.today().isoformat()
    }, headers=headers)
    req_id = res.json()["id"]
    
    patch_res = client.patch(f"/recurring/{req_id}/active", json={"is_active": False}, headers=headers)
    assert patch_res.status_code == 200
    assert patch_res.json()["is_active"] is False

def test_delete_recurring_expense(client):
    email = "req_del@example.com"
    headers = create_user_and_token(client, "req_del", email, "Password123!")
    _make_user_premium(email)
    
    res = client.post("/recurring/", json={
        "title": "To Delete",
        "amount": 5000,
        "category": "Other",
        "frequency": "MONTHLY",
        "start_date": date.today().isoformat()
    }, headers=headers)
    assert res.status_code == 201
    req_id = res.json()["id"]
    
    del_res = client.delete(f"/recurring/{req_id}", headers=headers)
    assert del_res.status_code == 204
    
    # We can't GET by ID directly since no endpoint exists for /recurring/{id}
    # We check if it is included in the list
    get_res = client.get(f"/recurring/", headers=headers)
    assert get_res.status_code == 200
    assert len(get_res.json()) == 0

def test_free_user_forbidden(client):
    email = "req_free@example.com"
    headers = create_user_and_token(client, "req_free", email, "Password123!")
    
    # User is intentionally NOT made premium
    res = client.post("/recurring/", json={
        "title": "Sub",
        "amount": 100,
        "category": "Other",
        "frequency": "MONTHLY",
        "start_date": date.today().isoformat()
    }, headers=headers)
    assert res.status_code == 403
