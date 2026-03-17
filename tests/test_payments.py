from config import settings
from tests.helpers import create_user_and_token


def test_create_invoice_creates_pending_transaction(client, session):
    headers = create_user_and_token(client, "payuser1", "payuser1@example.com", "Password123!")
    res = client.post("/payments/create-invoice", json={"plan_id": "BETA_MONTHLY"}, headers=headers)

    assert res.status_code == 201, res.text
    data = res.json()
    assert data["plan_id"] == "BETA_MONTHLY"
    assert data["amount"] == 11990
    assert data["currency"] == "UZS"
    assert data["order_code"].startswith("ORD-")


def test_create_invoice_rejects_invalid_plan(client):
    headers = create_user_and_token(client, "payuser2", "payuser2@example.com", "Password123!")
    res = client.post("/payments/create-invoice", json={"plan_id": "NOPE"}, headers=headers)
    assert res.status_code == 400
    assert res.json()["detail"] == "payments.invalid_plan_id"


def test_toggle_premium_is_disabled_in_production(client):
    headers = create_user_and_token(client, "payuser3", "payuser3@example.com", "Password123!")
    previous = settings.is_production
    settings.is_production = True
    try:
        res = client.post("/users/me/toggle-premium", headers=headers)
        assert res.status_code == 403
    finally:
        settings.is_production = previous
