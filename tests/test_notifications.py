import pytest
from app import models
from tests.helpers import create_user_and_token, create_budget, create_expense

def test_notification_creation_flow(client, session):
    # 1. Setup user and budget
    headers = create_user_and_token(client, "testnotify", "testnotify@example.com", "Password123!")
    create_budget(client, headers, category="Food", monthly_limit=1000)
    
    # 2. Add expense to cross 50% threshold (600/1000 = 60%)
    response = create_expense(client, headers, title="Lunch", amount=600, category="Food")
    assert response.status_code == 201
    
    # 3. Check notifications via API
    response = client.get("/notifications", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["type"] == models.NotificationType.BUDGET_WARNING.value
    assert "50%" in data["items"][0]["message"]
    assert data["items"][0]["is_read"] is False

    # 4. Add another expense to cross 90% threshold
    create_expense(client, headers, title="Dinner", amount=350, category="Food")
    
    response = client.get("/notifications", headers=headers)
    data = response.json()
    assert data["total"] == 2
    # Newest should be first
    assert "90%" in data["items"][0]["message"]

def test_notification_reset_on_delete(client, session):
    headers = create_user_and_token(client, "testreset", "testreset@example.com", "Password123!")
    create_budget(client, headers, category="Food", monthly_limit=1000)
    
    # Cross 50%
    resp = create_expense(client, headers, title="Exp1", amount=600, category="Food")
    expense_id = resp.json()["id"]
    
    response = client.get("/notifications", headers=headers)
    assert response.json()["total"] == 1
    
    # Delete expense
    response = client.delete(f"/expenses/{expense_id}", headers=headers)
    assert response.status_code == 204
    
    # Threshold should be reset in the budget row
    user = session.query(models.User).filter(models.User.email == "testreset@example.com").first()
    budget = session.query(models.Budget).filter(models.Budget.owner_id == user.id).first()
    # We must refresh from DB because we performed an API call (which has its own session)
    session.refresh(budget)
    assert budget.last_notified_threshold == 0
    
    # Adding expense again should trigger a NEW notification
    create_expense(client, headers, title="Exp1-retry", amount=600, category="Food")
    response = client.get("/notifications", headers=headers)
    assert response.json()["total"] == 2 # One old one, one new one

def test_mark_as_read(client, session):
    headers = create_user_and_token(client, "testread", "testread@example.com", "Password123!")
    create_budget(client, headers, category="Food", monthly_limit=1000)
    create_expense(client, headers, title="Exp1", amount=600, category="Food")
    
    response = client.get("/notifications", headers=headers)
    notification_id = response.json()["items"][0]["id"]
    
    # Mark as read
    # Note: /notifications/mark-read expects a list of ids in payload
    response = client.post("/notifications/mark-read", json={"notification_ids": [notification_id]}, headers=headers)
    assert response.status_code == 204
    
    # Verify
    response = client.get("/notifications", headers=headers)
    assert response.json()["items"][0]["is_read"] is True

def test_delete_notification(client, session):
    headers = create_user_and_token(client, "testdel", "testdel@example.com", "Password123!")
    create_budget(client, headers, category="Food", monthly_limit=1000)
    create_expense(client, headers, title="Exp1", amount=600, category="Food")
    
    response = client.get("/notifications", headers=headers)
    notification_id = response.json()["items"][0]["id"]
    
    # Delete
    response = client.delete(f"/notifications/{notification_id}", headers=headers)
    assert response.status_code == 204
    
    # Verify
    response = client.get("/notifications", headers=headers)
    assert response.json()["total"] == 0
