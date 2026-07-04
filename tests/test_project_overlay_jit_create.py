from sqlalchemy import inspect

from app import models
from tests.helpers import create_budget, create_user_and_token, user_timezone_today


def _create_monthly_subcategory(client, headers, *, budget_id, category, name, monthly_limit):
    response = client.post(
        f"/budgets/{budget_id}/subcategories",
        json={
            "category": category,
            "name": name,
            "monthly_limit": monthly_limit,
        },
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_overlay_jit_create_allocates_only_selected_month(client, session):
    headers = create_user_and_token(client, "jitcreate", "jitcreate@example.com", "Password123!")
    today = user_timezone_today()
    next_year = today.year + 1 if today.month == 12 else today.year
    next_month = 1 if today.month == 12 else today.month + 1

    current_budget = create_budget(
        client,
        headers,
        category="Travel",
        monthly_limit=1_000_000,
        budget_year=today.year,
        budget_month=today.month,
    )
    assert current_budget.status_code == 201, current_budget.text
    future_budget = create_budget(
        client,
        headers,
        category="Travel",
        monthly_limit=1_000_000,
        budget_year=next_year,
        budget_month=next_month,
    )
    assert future_budget.status_code == 201, future_budget.text
    lodging = _create_monthly_subcategory(
        client,
        headers,
        budget_id=current_budget.json()["id"],
        category="Travel",
        name="Lodging",
        monthly_limit=300_000,
    )

    response = client.post(
        "/projects/overlay",
        json={
            "title": "Summer trip",
            "description": "Cross-month overlay",
            "target_estimate": 5_000_000,
            "start_date": today.replace(day=1).isoformat(),
            "target_end_date": f"{next_year}-{next_month:02d}-28",
            "budget_year": today.year,
            "budget_month": today.month,
            "category_reservations": [
                {"category": "Travel", "limit_amount": 500_000},
            ],
            "subcategory_reservations": [
                {
                    "category": "Travel",
                    "user_subcategory_id": lodging["id"],
                    "limit_amount": 200_000,
                },
            ],
        },
        headers=headers,
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["is_isolated"] is False
    assert body["total_limit"] is None
    assert body["target_estimate"] == 5_000_000
    assert body["selected_budget_year"] == today.year
    assert body["selected_budget_month"] == today.month
    assert body["selected_month_reserved_amount"] == 500_000
    assert body["total_reserved_scope"] == 500_000
    assert len(body["category_breakdown"]) == 1
    assert body["category_breakdown"][0]["budget_year"] == today.year
    assert body["category_breakdown"][0]["budget_month"] == today.month
    assert body["category_breakdown"][0]["subcategories"][0]["user_subcategory_id"] == lodging["id"]

    project_id = body["id"]
    category_limits = (
        session.query(models.OverlayProjectCategoryReservation)
        .filter(models.OverlayProjectCategoryReservation.project_id == project_id)
        .all()
    )
    assert [(row.budget_year, row.budget_month, row.limit_amount) for row in category_limits] == [
        (today.year, today.month, 500_000)
    ]
    subcategory_limits = (
        session.query(models.OverlayProjectSubcategoryReservation)
        .filter(models.OverlayProjectSubcategoryReservation.project_id == project_id)
        .all()
    )
    assert [(row.budget_year, row.budget_month, row.limit_amount) for row in subcategory_limits] == [
        (today.year, today.month, 200_000)
    ]


def test_project_api_exposes_typology_specific_financial_contracts(client, session):
    headers = create_user_and_token(client, "typologyapi", "typologyapi@example.com", "Password123!")
    today = user_timezone_today()
    budget = create_budget(
        client,
        headers,
        category="Travel",
        monthly_limit=1_000_000,
        budget_year=today.year,
        budget_month=today.month,
    )
    assert budget.status_code == 201, budget.text

    overlay = client.post(
        "/projects/overlay",
        json={
            "title": "Typology-safe trip",
            "target_estimate": 2_000_000,
            "start_date": today.replace(day=1).isoformat(),
            "target_end_date": None,
            "budget_year": today.year,
            "budget_month": today.month,
            "category_reservations": [
                {"category": "Travel", "limit_amount": 300_000},
            ],
            "subcategory_reservations": [],
        },
        headers=headers,
    )
    assert overlay.status_code == 201, overlay.text
    overlay_body = overlay.json()
    assert overlay_body["project_type"] == "OVERLAY"
    assert overlay_body["total_limit"] is None
    assert overlay_body["isolated"] is None
    assert overlay_body["overlay"] == {
        "target_estimate": 2_000_000,
        "selected_month_reserved_amount": 300_000,
        "total_reserved_scope": 300_000,
    }

    isolated = client.post(
        "/projects",
        json={
            "title": "Typology-safe renovation",
            "is_isolated": True,
            "total_limit": 900_000,
            "start_date": today.replace(day=1).isoformat(),
            "target_end_date": None,
        },
        headers=headers,
    )
    assert isolated.status_code == 201, isolated.text
    isolated_body = isolated.json()
    assert isolated_body["project_type"] == "ISOLATED"
    assert isolated_body["overlay"] is None
    assert isolated_body["isolated"] == {
        "funding_limit": 900_000,
        "allocated_funding": 0,
        "unallocated_funding": 900_000,
        "released_funding": None,
        "remaining_funding": None,
        "funding_shortfall": 0,
        "wallet_allocations": [],
    }
    project_columns = {column["name"] for column in inspect(session.bind).get_columns("projects")}
    assert "project_type" in project_columns
    assert {"is_isolated", "total_limit", "target_estimate"}.isdisjoint(project_columns)


def test_overlay_paths_reject_isolated_total_limit_payloads(client):
    headers = create_user_and_token(client, "typologyreject", "typologyreject@example.com", "Password123!")
    today = user_timezone_today()

    create_overlay_with_total = client.post(
        "/projects",
        json={
            "title": "Stale overlay payload",
            "is_isolated": False,
            "total_limit": 1_000_000,
            "start_date": today.replace(day=1).isoformat(),
            "target_end_date": None,
        },
        headers=headers,
    )
    assert create_overlay_with_total.status_code == 400
    assert create_overlay_with_total.json()["detail"] == "projects.overlay_total_limit_not_allowed"

    create_budget(
        client,
        headers,
        category="Travel",
        monthly_limit=1_000_000,
        budget_year=today.year,
        budget_month=today.month,
    )
    overlay = client.post(
        "/projects/overlay",
        json={
            "title": "Valid overlay",
            "start_date": today.replace(day=1).isoformat(),
            "target_end_date": None,
            "budget_year": today.year,
            "budget_month": today.month,
            "category_reservations": [
                {"category": "Travel", "limit_amount": 300_000},
            ],
            "subcategory_reservations": [],
        },
        headers=headers,
    )
    assert overlay.status_code == 201, overlay.text

    update_overlay_with_total = client.put(
        f"/projects/{overlay.json()['id']}",
        json={"total_limit": 2_000_000},
        headers=headers,
    )
    assert update_overlay_with_total.status_code == 400
    assert update_overlay_with_total.json()["detail"] == "projects.overlay_total_limit_not_allowed"


def test_overlay_jit_create_overbooking_leaves_no_partial_project(client, session):
    headers = create_user_and_token(client, "jitoverbook", "jitoverbook@example.com", "Password123!")
    today = user_timezone_today()
    budget = create_budget(
        client,
        headers,
        category="Travel",
        monthly_limit=100_000,
        budget_year=today.year,
        budget_month=today.month,
    )
    assert budget.status_code == 201, budget.text

    response = client.post(
        "/projects/overlay",
        json={
            "title": "Impossible trip",
            "start_date": today.replace(day=1).isoformat(),
            "target_end_date": None,
            "budget_year": today.year,
            "budget_month": today.month,
            "category_reservations": [
                {"category": "Travel", "limit_amount": 200_000},
            ],
            "subcategory_reservations": [],
        },
        headers=headers,
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "projects.category_reservation_exceeds_parent_budget"
    assert (
        session.query(models.Project)
        .filter(models.Project.title == "Impossible trip")
        .first()
        is None
    )
