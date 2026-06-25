from datetime import date
from tests.helpers import create_user_and_token, create_budget, user_timezone_today

def test_taxonomy_hub_returns_empty_when_no_tags(client):
    headers = create_user_and_token(client, "tax_empty", "tax_empty@example.com", "Password123!")
    res = client.get("/subcategories/taxonomy", headers=headers)
    assert res.status_code == 200
    assert len(res.json()) == 0

def test_taxonomy_hub_scorecard_calculations(client, session):
    headers = create_user_and_token(client, "tax_stats", "tax_stats@example.com", "Password123!")
    today = user_timezone_today()
    
    # create budget and tags
    budget = create_budget(client, headers, category="Food", monthly_limit=5000, budget_year=today.year, budget_month=today.month)
    budget_id = budget.json()["id"]
    
    # Tag 1: has spending
    tag1_res = client.post(f"/budgets/{budget_id}/subcategories", json={"category": "Groceries", "name": "Market", "monthly_limit": 1000}, headers=headers)
    assert tag1_res.status_code == 201
    tag1_id = tag1_res.json()["id"]

    # Tag 2: no spending
    tag2_res = client.post(f"/budgets/{budget_id}/subcategories", json={"category": "Groceries", "name": "Never Used", "monthly_limit": 1000}, headers=headers)
    assert tag2_res.status_code == 201
    tag2_id = tag2_res.json()["id"]

    # Create expenses for Tag 1
    res1 = client.post("/expenses/", json={
        "title": "Market trip 1",
        "amount": 100,
        "category": "Groceries",
        "date": today.isoformat(),
        "subcategory_id": tag1_id,
    }, headers=headers)
    assert res1.status_code == 201
    
    res2 = client.post("/expenses/", json={
        "title": "Market trip 2",
        "amount": 250,
        "category": "Groceries",
        "date": today.isoformat(),
        "subcategory_id": tag1_id,
    }, headers=headers)
    assert res2.status_code == 201

    # A voided expense for Tag 1
    voided_res = client.post("/expenses/", json={
        "title": "Market trip voided",
        "amount": 50,
        "category": "Groceries",
        "date": today.isoformat(),
        "subcategory_id": tag1_id,
    }, headers=headers)
    assert voided_res.status_code == 201
    voided_id = voided_res.json()["id"]
    client.delete(f"/expenses/{voided_id}", headers=headers)

    # Fetch Taxonomy Hub
    res = client.get("/subcategories/taxonomy", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 2
    
    # Sort or find by name
    market_tag = next(x for x in data if x["name"] == "Market")
    never_used_tag = next(x for x in data if x["name"] == "Never Used")

    assert market_tag["scorecard"]["tx_count"] == 2
    assert market_tag["scorecard"]["lifetime_spent"] == 350
    assert market_tag["scorecard"]["first_used"] is not None
    assert market_tag["scorecard"]["last_used"] is not None

    assert never_used_tag["scorecard"]["tx_count"] == 0
    assert never_used_tag["scorecard"]["lifetime_spent"] == 0
    assert never_used_tag["scorecard"]["first_used"] is None
    assert never_used_tag["scorecard"]["last_used"] is None

def test_update_subcategory_rename_and_archive(client, session):
    headers = create_user_and_token(client, "tax_patch", "tax_patch@example.com", "Password123!")
    today = user_timezone_today()
    
    # create budget and tags
    budget = create_budget(client, headers, category="Food", monthly_limit=5000, budget_year=today.year, budget_month=today.month)
    budget_id = budget.json()["id"]
    
    tag1_res = client.post(f"/budgets/{budget_id}/subcategories", json={"category": "Groceries", "name": "Burger", "monthly_limit": 1000}, headers=headers)
    tag1_id = tag1_res.json()["id"]

    tag2_res = client.post(f"/budgets/{budget_id}/subcategories", json={"category": "Groceries", "name": "Pizza", "monthly_limit": 1000}, headers=headers)
    tag2_id = tag2_res.json()["id"]

    # 1. Rename success
    res = client.patch(f"/subcategories/{tag1_id}", json={"name": "Burgers & Fries"}, headers=headers)
    assert res.status_code == 200
    assert res.json()["name"] == "Burgers & Fries"

    # 2. Rename collision
    res = client.patch(f"/subcategories/{tag1_id}", json={"name": "pizza"}, headers=headers)
    assert res.status_code == 409
    assert "already exists" in res.json()["detail"]

    # 3. Archive success
    res = client.patch(f"/subcategories/{tag1_id}", json={"is_active": False}, headers=headers)
    assert res.status_code == 200
    assert res.json()["is_active"] is False

    # 4. Ownership protection (another user)
    headers_other = create_user_and_token(client, "tax_patch_other", "tax_other@example.com", "Password123!")
    res = client.patch(f"/subcategories/{tag1_id}", json={"name": "Hacked"}, headers=headers_other)
    assert res.status_code == 404

def test_delete_subcategory(client, session):
    headers = create_user_and_token(client, "tax_delete", "tax_delete@example.com", "Password123!")
    today = user_timezone_today()
    
    # create budget and tags
    budget = create_budget(client, headers, category="Food", monthly_limit=5000, budget_year=today.year, budget_month=today.month)
    budget_id = budget.json()["id"]
    
    # Tag 1: will have spending
    tag1_res = client.post(f"/budgets/{budget_id}/subcategories", json={"category": "Groceries", "name": "Used", "monthly_limit": 1000}, headers=headers)
    tag1_id = tag1_res.json()["id"]

    # Tag 2: pristine
    tag2_res = client.post(f"/budgets/{budget_id}/subcategories", json={"category": "Groceries", "name": "Pristine", "monthly_limit": 1000}, headers=headers)
    tag2_id = tag2_res.json()["id"]

    # Create expense for Tag 1
    client.post("/expenses/", json={
        "title": "Milk",
        "amount": 10,
        "category": "Groceries",
        "date": today.isoformat(),
        "subcategory_id": tag1_id,
    }, headers=headers)

    # 1. Delete used tag -> Success 204 (Soft Delete)
    res1 = client.delete(f"/subcategories/{tag1_id}", headers=headers)
    assert res1.status_code == 204

    # 2. Delete pristine tag -> Success 204
    res2 = client.delete(f"/subcategories/{tag2_id}", headers=headers)
    assert res2.status_code == 204

    # 3. Ownership protection
    headers_other = create_user_and_token(client, "tax_delete_other", "tax_other_del@example.com", "Password123!")
    res3 = client.delete(f"/subcategories/{tag1_id}", headers=headers_other)
    assert res3.status_code == 404

def test_merge_subcategories(client, session):
    headers = create_user_and_token(client, "tax_merge", "tax_merge@example.com", "Password123!")
    today = user_timezone_today()
    
    budget = create_budget(client, headers, category="Food", monthly_limit=5000, budget_year=today.year, budget_month=today.month)
    budget_id = budget.json()["id"]
    
    # Target tag
    t1_res = client.post(f"/budgets/{budget_id}/subcategories", json={"category": "Groceries", "name": "Burger", "monthly_limit": 1000}, headers=headers)
    target_id = t1_res.json()["id"]

    # Source tag
    s1_res = client.post(f"/budgets/{budget_id}/subcategories", json={"category": "Groceries", "name": "Pizza", "monthly_limit": 1000}, headers=headers)
    source_id = s1_res.json()["id"]

    # Different category tag
    budget2 = create_budget(client, headers, category="Housing", monthly_limit=5000, budget_year=today.year, budget_month=today.month)
    budget2_id = budget2.json()["id"]
    c1_res = client.post(f"/budgets/{budget2_id}/subcategories", json={"category": "Housing", "name": "Rent", "monthly_limit": 1000}, headers=headers)
    diff_cat_id = c1_res.json()["id"]

    # Create expense for Source tag
    res_exp = client.post("/expenses/", json={
        "title": "Pizza Party",
        "amount": 50,
        "category": "Groceries",
        "date": today.isoformat(),
        "subcategory_id": source_id,
    }, headers=headers)
    exp_id = res_exp.json()["id"]

    # 1. Validation: target in sources
    res_val1 = client.post("/subcategories/merge", json={"target_id": target_id, "source_ids": [target_id]}, headers=headers)
    assert res_val1.status_code == 400

    # 2. Validation: cross-category
    res_val2 = client.post("/subcategories/merge", json={"target_id": target_id, "source_ids": [diff_cat_id]}, headers=headers)
    assert res_val2.status_code == 400

    # 3. Success Merge
    res_merge = client.post("/subcategories/merge", json={"target_id": target_id, "source_ids": [source_id]}, headers=headers)
    assert res_merge.status_code == 200

    # Verify source tag is deleted
    res_get_source = client.get("/subcategories/taxonomy", headers=headers)
    assert not any(x["id"] == source_id for x in res_get_source.json())

    # Verify expense is moved to target tag
    from app.models import EntityLedger
    ledger = session.query(EntityLedger).filter(EntityLedger.event_id == exp_id).first()
    assert ledger.subcategory_id == target_id
