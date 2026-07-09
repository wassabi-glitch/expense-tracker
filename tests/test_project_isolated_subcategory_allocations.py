import pytest
from tests.helpers import create_user_and_token


@pytest.fixture
def test_user(client):
    return create_user_and_token(client, "testuser", "testuser@example.com", "Password123!")


@pytest.fixture
def secondary_user(client):
    return create_user_and_token(client, "other", "other@example.com", "Password123!")


def test_isolated_project_subcategory_create_and_link(client, test_user):
    headers = test_user

    # 1. Create a wallet
    wallet_resp = client.post("/wallets", json={"name": "Cash", "initial_balance": 1000}, headers=headers)
    assert wallet_resp.status_code == 201
    wallet_id = wallet_resp.json()["id"]

    # 2. Create isolated project with wallet and category allocation
    proj_resp = client.post("/projects", json={
        "title": "Kitchen",
        "is_isolated": True,
        "start_date": "2024-01-01",
        "wallet_allocations": [{"wallet_id": wallet_id, "amount": 1000}],
        "category_allocations": [
            {"category": "Housing", "limit_amount": 500}
        ]
    }, headers=headers)
    assert proj_resp.status_code == 201, proj_resp.text
    project_id = proj_resp.json()["id"]

    # 3. Add a micro-subcategory with a new name (creates UserSubcategory)
    subcat_resp1 = client.post(f"/projects/{project_id}/subcategories", json={
        "category": "Housing",
        "name": "Drywall",
        "limit_amount": 300,
        "is_active": True
    }, headers=headers)
    assert subcat_resp1.status_code == 201

    # 4. Try to add another subcategory that exceeds the $500 limit
    subcat_resp2 = client.post(f"/projects/{project_id}/subcategories", json={
        "category": "Housing",
        "name": "Plumbing",
        "limit_amount": 300,  # 300 + 300 = 600 > 500
        "is_active": True
    }, headers=headers)
    assert subcat_resp2.status_code == 400
    assert subcat_resp2.json()["detail"] == "projects.isolated_subcategory_limit_exceeds_category"

    # 5. Add it with $200 (exact limit)
    subcat_resp3 = client.post(f"/projects/{project_id}/subcategories", json={
        "category": "Housing",
        "name": "Plumbing",
        "limit_amount": 200,
        "is_active": True
    }, headers=headers)
    assert subcat_resp3.status_code == 201

    # 6. Verify they show up in list
    list_resp = client.get(f"/projects/{project_id}/subcategories", headers=headers)
    assert list_resp.status_code == 200
    items = list_resp.json()
    assert len(items) == 2
    assert items[0]["name"] == "Drywall"
    assert items[0]["limit_amount"] == 300
    assert items[1]["name"] == "Plumbing"
    assert items[1]["limit_amount"] == 200


def test_isolated_project_subcategory_requires_allocated_parent(client, test_user):
    headers = test_user

    wallet_resp = client.post("/wallets", json={"name": "Cash", "initial_balance": 1000}, headers=headers)
    wallet_id = wallet_resp.json()["id"]

    proj_resp = client.post("/projects", json={
        "title": "Kitchen",
        "is_isolated": True,
        "start_date": "2024-01-01",
        "wallet_allocations": [{"wallet_id": wallet_id, "amount": 1000}],
        "category_allocations": [
            {"category": "Housing", "limit_amount": 500}
        ]
    }, headers=headers)
    project_id = proj_resp.json()["id"]

    # Try to add subcategory for unallocated category
    subcat_resp = client.post(f"/projects/{project_id}/subcategories", json={
        "category": "Groceries",
        "name": "Supermarket",
        "limit_amount": 100,
        "is_active": True
    }, headers=headers)
    assert subcat_resp.status_code == 400
    assert subcat_resp.json()["detail"] == "projects.isolated_subcategory_parent_category_not_allocated"


def test_isolated_project_subcategory_archive_on_delete_if_spent(client, test_user, session):
    headers = test_user

    wallet_resp = client.post("/wallets", json={"name": "Cash", "initial_balance": 1000}, headers=headers)
    wallet_id = wallet_resp.json()["id"]

    # Backdate wallet epoch so the expense date 2024-01-02 is allowed
    from app import models as _models
    from tests.helpers import TEST_WALLET_EPOCH
    w = session.query(_models.Wallet).filter(_models.Wallet.id == wallet_id).first()
    w.created_at = TEST_WALLET_EPOCH
    session.commit()

    proj_resp = client.post("/projects", json={
        "title": "Kitchen",
        "is_isolated": True,
        "start_date": "2024-01-01",
        "wallet_allocations": [{"wallet_id": wallet_id, "amount": 1000}],
        "category_allocations": [
            {"category": "Housing", "limit_amount": 500}
        ]
    }, headers=headers)
    project_id = proj_resp.json()["id"]

    client.post(f"/projects/{project_id}/subcategories", json={
        "category": "Housing",
        "name": "Drywall",
        "limit_amount": 300,
        "is_active": True
    }, headers=headers)
    
    list_resp = client.get(f"/projects/{project_id}/subcategories", headers=headers)
    subcat_id = list_resp.json()[0]["id"]
    user_subcategory_id = list_resp.json()[0]["user_subcategory_id"]

    # Post expense
    exp_resp = client.post("/expenses", json={
        "title": "Materials",
        "amount": 100,
        "category": "Housing",
        "date": "2024-01-02",
        "wallet_id": wallet_id,
        "project_id": project_id,
        "subcategory_id": user_subcategory_id
    }, headers=headers)
    if exp_resp.status_code != 201:
        print("Expense creation failed:", exp_resp.text)
    assert exp_resp.status_code == 201

    # Try to reduce limit below spent
    upd_resp = client.put(f"/projects/{project_id}/subcategories/{subcat_id}", json={
        "limit_amount": 50,
        "category": "Housing"
    }, headers=headers)
    assert upd_resp.status_code == 400
    assert upd_resp.json()["detail"] == "projects.subcategory_allocation_below_spent"

    # Delete -> should archive
    del_resp = client.delete(f"/projects/{project_id}/subcategories/{subcat_id}", headers=headers)
    assert del_resp.status_code == 200
    
    # Verify it is archived (is_active = False)
    list_resp2 = client.get(f"/projects/{project_id}/subcategories", headers=headers)
    assert list_resp2.status_code == 200
    assert list_resp2.json()[0]["is_active"] is False

    # Create another one, no expense, delete -> should hard delete
    client.post(f"/projects/{project_id}/subcategories", json={
        "category": "Housing",
        "name": "Paint",
        "limit_amount": 100,
        "is_active": True
    }, headers=headers)
    list_resp3 = client.get(f"/projects/{project_id}/subcategories", headers=headers)
    paint_id = next(item["id"] for item in list_resp3.json() if item["name"] == "Paint")
    
    client.delete(f"/projects/{project_id}/subcategories/{paint_id}", headers=headers)
    list_resp4 = client.get(f"/projects/{project_id}/subcategories", headers=headers)
    assert len(list_resp4.json()) == 1  # Only the archived Drywall is left
