from app import models
from tests.helpers import create_user_and_token, create_budget

def _create_overlay_context(client, headers):
    budget = create_budget(
        client,
        headers,
        category="Travel",
        monthly_limit=1_000_000,
        budget_year=2026,
        budget_month=6,
    )
    assert budget.status_code == 201, budget.text
    
    budget7 = create_budget(
        client,
        headers,
        category="Travel",
        monthly_limit=1_000_000,
        budget_year=2026,
        budget_month=7,
    )
    assert budget7.status_code == 201, budget7.text

    subcategory = client.post(
        f"/budgets/{budget.json()['id']}/subcategories",
        json={"category": "Travel", "name": "Lodging", "monthly_limit": 300_000},
        headers=headers,
    )
    assert subcategory.status_code == 201, subcategory.text
    
    subcategory7 = client.post(
        f"/budgets/{budget7.json()['id']}/subcategories",
        json={"category": "Travel", "name": "Lodging", "monthly_limit": 300_000},
        headers=headers,
    )
    assert subcategory7.status_code == 201, subcategory7.text
    
    project = client.post(
        "/projects",
        json={
            "title": "Summer trip",
            "is_isolated": False,
            "start_date": "2026-06-01",
            "target_end_date": "2026-07-31",
        },
        headers=headers,
    )
    assert project.status_code == 201, project.text
    
    # June slices
    cat_limit_6 = client.post(
        f"/projects/{project.json()['id']}/category-limits",
        json={
            "category": "Travel",
            "limit_amount": 500_000,
            "budget_year": 2026,
            "budget_month": 6,
        },
        headers=headers,
    )
    assert cat_limit_6.status_code == 201, cat_limit_6.text
    
    sub_limit_6 = client.post(
        f"/projects/{project.json()['id']}/subcategories",
        json={
            "category": "Travel",
            "user_subcategory_id": subcategory.json()["id"],
            "limit_amount": 200_000,
            "budget_year": 2026,
            "budget_month": 6,
        },
        headers=headers,
    )
    assert sub_limit_6.status_code == 201, sub_limit_6.text

    # July slices
    cat_limit_7 = client.post(
        f"/projects/{project.json()['id']}/category-limits",
        json={
            "category": "Travel",
            "limit_amount": 500_000,
            "budget_year": 2026,
            "budget_month": 7,
        },
        headers=headers,
    )
    assert cat_limit_7.status_code == 201, cat_limit_7.text
    
    sub_limit_7 = client.post(
        f"/projects/{project.json()['id']}/subcategories",
        json={
            "category": "Travel",
            "user_subcategory_id": subcategory7.json()["id"],
            "limit_amount": 200_000,
            "budget_year": 2026,
            "budget_month": 7,
        },
        headers=headers,
    )
    assert sub_limit_7.status_code == 201, sub_limit_7.text
    
    return budget.json(), subcategory.json(), project.json()

def test_project_date_update_prunes_empty_slices(client, session):
    headers = create_user_and_token(
        client, "pruneempty", "pruneempty@example.com", "Password123!"
    )
    _, _, project = _create_overlay_context(client, headers)
    
    # Narrow window to June only (so July slices should be pruned)
    update = client.put(
        f"/projects/{project['id']}",
        json={
            "target_end_date": "2026-06-30",
        },
        headers=headers,
    )
    assert update.status_code == 200, update.text
    
    # Verify July slices are gone from DB
    cat_limits = session.query(models.OverlayProjectCategoryReservation).filter(
        models.OverlayProjectCategoryReservation.project_id == project["id"]
    ).all()
    assert len(cat_limits) == 1
    assert cat_limits[0].budget_month == 6
    
    sub_limits = session.query(models.OverlayProjectSubcategoryReservation).filter(
        models.OverlayProjectSubcategoryReservation.project_id == project["id"]
    ).all()
    assert len(sub_limits) == 1
    assert sub_limits[0].budget_month == 6


def test_project_date_update_rejects_if_spent_slice_stranded(client, session):
    headers = create_user_and_token(
        client, "strand", "strand@example.com", "Password123!"
    )
    _, subcategory, project = _create_overlay_context(client, headers)
    
    # Add an expense in July
    expense = client.post(
        "/expenses/",
        json={
            "title": "July hotel",
            "amount": 50_000,
            "category": "Travel",
            "date": "2026-07-01",
            "project_id": project["id"],
            "subcategory_id": subcategory["id"],
        },
        headers=headers,
    )
    assert expense.status_code == 201, expense.text
    
    # Narrow window to June only
    update = client.put(
        f"/projects/{project['id']}",
        json={
            "target_end_date": "2026-06-30",
        },
        headers=headers,
    )
    assert update.status_code == 400
    assert update.json()["detail"] == "projects.end_before_linked_expense"


def test_project_date_update_removes_target_end_date(client, session):
    headers = create_user_and_token(
        client, "removetarget", "removetarget@example.com", "Password123!"
    )
    _, _, project = _create_overlay_context(client, headers)
    
    update = client.put(
        f"/projects/{project['id']}",
        json={
            "target_end_date": None,
        },
        headers=headers,
    )
    assert update.status_code == 200
    
    # Verify both June and July slices remain
    cat_limits = session.query(models.OverlayProjectCategoryReservation).filter(
        models.OverlayProjectCategoryReservation.project_id == project["id"]
    ).all()
    assert len(cat_limits) == 2


def test_project_date_update_adds_target_end_date_prunes_future(client, session):
    headers = create_user_and_token(
        client, "addtarget", "addtarget@example.com", "Password123!"
    )
    budget, subcategory, project = _create_overlay_context(client, headers)
    
    # First remove target_end_date
    client.put(
        f"/projects/{project['id']}",
        json={"target_end_date": None},
        headers=headers,
    )
    
    # Add an August budget and slice (which is valid when there is no target_end_date)
    budget8 = create_budget(client, headers, category="Travel", monthly_limit=1_000_000, budget_year=2026, budget_month=8)
    sub8 = client.post(f"/budgets/{budget8.json()['id']}/subcategories", json={"category": "Travel", "name": "Lodging", "monthly_limit": 300_000}, headers=headers)
    
    client.post(f"/projects/{project['id']}/category-limits", json={"category": "Travel", "limit_amount": 100_000, "budget_year": 2026, "budget_month": 8}, headers=headers)
    client.post(f"/projects/{project['id']}/subcategories", json={"category": "Travel", "user_subcategory_id": sub8.json()["id"], "limit_amount": 50_000, "budget_year": 2026, "budget_month": 8}, headers=headers)
    
    # Now add target_end_date back to July
    update = client.put(
        f"/projects/{project['id']}",
        json={"target_end_date": "2026-07-31"},
        headers=headers,
    )
    assert update.status_code == 200
    
    # Verify August slices are pruned, June and July remain
    cat_limits = session.query(models.OverlayProjectCategoryReservation).filter(
        models.OverlayProjectCategoryReservation.project_id == project["id"]
    ).order_by(models.OverlayProjectCategoryReservation.budget_month).all()
    assert len(cat_limits) == 2
    assert cat_limits[0].budget_month == 6
    assert cat_limits[1].budget_month == 7
    
    sub_limits = session.query(models.OverlayProjectSubcategoryReservation).filter(
        models.OverlayProjectSubcategoryReservation.project_id == project["id"]
    ).order_by(models.OverlayProjectSubcategoryReservation.budget_month).all()
    assert len(sub_limits) == 2
    assert sub_limits[0].budget_month == 6
    assert sub_limits[1].budget_month == 7


