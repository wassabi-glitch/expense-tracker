from app import models
from tests.helpers import create_budget, create_user_and_token, user_timezone_today


def _default_wallet_id(client, headers):
    wallets = client.get("/wallets", headers=headers)
    assert wallets.status_code == 200, wallets.text
    return wallets.json()[0]["id"]


def test_isolated_project_creation_persists_parent_category_allocations_without_overlay_rows(client, session):
    headers = create_user_and_token(
        client,
        "isolatedcategoriescreate",
        "isolatedcategoriescreate@example.com",
        "Password123!",
    )
    today = user_timezone_today()
    wallet_id = _default_wallet_id(client, headers)

    created = client.post(
        "/projects",
        json={
            "title": "Wedding stash",
            "description": "Pooled vault",
            "is_isolated": True,
            "start_date": today.isoformat(),
            "target_end_date": None,
            "wallet_allocations": [{"wallet_id": wallet_id, "amount": 1_000_000}],
            "category_allocations": [
                {"category": "Family & Events", "limit_amount": 650_000},
                {"category": "Travel", "limit_amount": 250_000},
            ],
        },
        headers=headers,
    )

    assert created.status_code == 201, created.text
    body = created.json()
    assert body["project_type"] == "ISOLATED"
    assert body["isolated"]["funding_limit"] == 1_000_000
    assert body["isolated"]["allocated_funding"] == 900_000
    assert body["isolated"]["unallocated_funding"] == 100_000
    assert [
        {
            "category": item["category"],
            "limit_amount": item["limit_amount"],
            "spent": item["spent"],
            "remaining": item["remaining"],
        }
        for item in body["category_breakdown"]
    ] == [
        {
            "category": "Family & Events",
            "limit_amount": 650_000,
            "spent": 0,
            "remaining": 650_000,
        },
        {
            "category": "Travel",
            "limit_amount": 250_000,
            "spent": 0,
            "remaining": 250_000,
        },
    ]

    monthly_rows = (
        session.query(models.ProjectCategoryMonthlyLimit)
        .filter(models.ProjectCategoryMonthlyLimit.project_id == body["id"])
        .all()
    )
    assert monthly_rows == []


def test_isolated_project_creation_rejects_parent_category_allocations_above_stash_without_partial_project(client, session):
    headers = create_user_and_token(
        client,
        "isolatedcategoriesover",
        "isolatedcategoriesover@example.com",
        "Password123!",
    )
    today = user_timezone_today()
    wallet_id = _default_wallet_id(client, headers)

    created = client.post(
        "/projects",
        json={
            "title": "Overfilled stash",
            "is_isolated": True,
            "start_date": today.isoformat(),
            "target_end_date": None,
            "wallet_allocations": [{"wallet_id": wallet_id, "amount": 1_000_000}],
            "category_allocations": [
                {"category": "Family & Events", "limit_amount": 700_000},
                {"category": "Travel", "limit_amount": 400_000},
            ],
        },
        headers=headers,
    )

    assert created.status_code == 400
    assert created.json()["detail"] == "projects.category_limits_exceed_total"

    projects = client.get("/projects", headers=headers)
    assert projects.status_code == 200, projects.text
    assert all(project["title"] != "Overfilled stash" for project in projects.json())

    assert session.query(models.ProjectCategoryLimit).count() == 0
    assert session.query(models.ProjectWalletAllocation).count() == 0


def test_isolated_project_category_allocation_update_cannot_drop_below_actual_spending(client):
    headers = create_user_and_token(
        client,
        "isolatedcategoriesspent",
        "isolatedcategoriesspent@example.com",
        "Password123!",
    )
    today = user_timezone_today()
    wallet_id = _default_wallet_id(client, headers)

    created = client.post(
        "/projects",
        json={
            "title": "Venue stash",
            "is_isolated": True,
            "start_date": today.isoformat(),
            "target_end_date": None,
            "wallet_allocations": [{"wallet_id": wallet_id, "amount": 1_000_000}],
            "category_allocations": [
                {"category": "Family & Events", "limit_amount": 600_000},
            ],
        },
        headers=headers,
    )
    assert created.status_code == 201, created.text
    project_id = created.json()["id"]

    expense = client.post(
        "/expenses/",
        json={
            "title": "Venue deposit",
            "amount": 300_000,
            "category": "Family & Events",
            "date": today.isoformat(),
            "project_id": project_id,
        },
        headers=headers,
    )
    assert expense.status_code == 201, expense.text

    lowered = client.put(
        f"/projects/{project_id}/category-limits/Family%20%26%20Events",
        json={"limit_amount": 250_000},
        headers=headers,
    )

    assert lowered.status_code == 400
    assert lowered.json()["detail"] == "projects.category_allocation_below_spent"

    unchanged = client.get(f"/projects/{project_id}", headers=headers)
    assert unchanged.status_code == 200, unchanged.text
    category = unchanged.json()["category_breakdown"][0]
    assert category["limit_amount"] == 600_000
    assert category["spent"] == 300_000
    assert category["remaining"] == 300_000


def test_isolated_project_category_allocation_delete_cannot_drop_below_actual_spending(client):
    headers = create_user_and_token(
        client,
        "isolatedcategoriesdelete",
        "isolatedcategoriesdelete@example.com",
        "Password123!",
    )
    today = user_timezone_today()
    wallet_id = _default_wallet_id(client, headers)

    created = client.post(
        "/projects",
        json={
            "title": "Trip stash",
            "is_isolated": True,
            "start_date": today.isoformat(),
            "target_end_date": None,
            "wallet_allocations": [{"wallet_id": wallet_id, "amount": 1_000_000}],
            "category_allocations": [
                {"category": "Travel", "limit_amount": 600_000},
            ],
        },
        headers=headers,
    )
    assert created.status_code == 201, created.text
    project_id = created.json()["id"]

    expense = client.post(
        "/expenses/",
        json={
            "title": "Hotel deposit",
            "amount": 300_000,
            "category": "Travel",
            "date": today.isoformat(),
            "project_id": project_id,
        },
        headers=headers,
    )
    assert expense.status_code == 201, expense.text

    deleted = client.delete(
        f"/projects/{project_id}/category-limits/Travel",
        headers=headers,
    )

    assert deleted.status_code == 400
    assert deleted.json()["detail"] == "projects.category_allocation_below_spent"


def test_isolated_project_category_funding_does_not_create_monthly_budget_reservation(client):
    headers = create_user_and_token(
        client,
        "isolatedcategoriesbudget",
        "isolatedcategoriesbudget@example.com",
        "Password123!",
    )
    today = user_timezone_today()
    wallet_id = _default_wallet_id(client, headers)
    budget = create_budget(
        client,
        headers,
        category="Travel",
        monthly_limit=100_000,
        budget_year=today.year,
        budget_month=today.month,
    )
    assert budget.status_code == 201, budget.text

    created = client.post(
        "/projects",
        json={
            "title": "Vacation stash",
            "is_isolated": True,
            "start_date": today.isoformat(),
            "target_end_date": None,
            "wallet_allocations": [{"wallet_id": wallet_id, "amount": 1_000_000}],
            "category_allocations": [
                {"category": "Travel", "limit_amount": 600_000},
            ],
        },
        headers=headers,
    )
    assert created.status_code == 201, created.text
    assert created.json()["selected_month_reserved_amount"] == 0

    detail = client.get(
        "/budgets/item/detail",
        params={
            "budget_year": today.year,
            "budget_month": today.month,
            "category": "Travel",
        },
        headers=headers,
    )

    assert detail.status_code == 200, detail.text
    body = detail.json()
    assert body["project_reserved_amount"] == 0
    assert body["project_reservations"] == []
