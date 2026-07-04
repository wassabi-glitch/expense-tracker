from pathlib import Path

from sqlalchemy import inspect

from app import models
from tests.helpers import create_budget, create_user_and_token, user_timezone_today


def _default_wallet_id(client, headers):
    wallets = client.get("/wallets", headers=headers)
    assert wallets.status_code == 200, wallets.text
    return wallets.json()[0]["id"]


def test_project_money_mechanics_use_type_specific_storage_without_splitting_project_identity(client, session):
    headers = create_user_and_token(client, "moneymechanics", "moneymechanics@example.com", "Password123!")
    today = user_timezone_today()
    wallet_id = _default_wallet_id(client, headers)
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
            "title": "Overlay trip",
            "start_date": today.isoformat(),
            "target_end_date": None,
            "budget_year": today.year,
            "budget_month": today.month,
            "category_reservations": [{"category": "Travel", "limit_amount": 300_000}],
            "subcategory_reservations": [],
        },
        headers=headers,
    )
    assert overlay.status_code == 201, overlay.text
    isolated = client.post(
        "/projects",
        json={
            "title": "Isolated vault",
            "is_isolated": True,
            "start_date": today.isoformat(),
            "target_end_date": None,
            "wallet_allocations": [{"wallet_id": wallet_id, "amount": 800_000}],
            "category_allocations": [{"category": "Travel", "limit_amount": 500_000}],
        },
        headers=headers,
    )
    assert isolated.status_code == 201, isolated.text

    tables = set(models.Base.metadata.tables)
    assert {
        "projects",
        "overlay_project_category_reservations",
        "overlay_project_subcategory_reservations",
        "isolated_project_wallet_allocations",
        "isolated_project_category_allocations",
    }.issubset(tables)
    assert {
        "project_category_limits",
        "project_category_monthly_limits",
        "project_subcategory_monthly_limits",
        "project_wallet_allocations",
    }.isdisjoint(tables)

    overlay_id = overlay.json()["id"]
    isolated_id = isolated.json()["id"]
    assert session.get(models.Project, overlay_id).id == overlay_id
    assert session.get(models.Project, isolated_id).id == isolated_id
    assert (
        session.query(models.OverlayProjectCategoryReservation)
        .filter_by(project_id=overlay_id)
        .count()
        == 1
    )
    assert (
        session.query(models.IsolatedProjectCategoryAllocation)
        .filter_by(project_id=isolated_id)
        .count()
        == 1
    )
    assert (
        session.query(models.IsolatedProjectWalletAllocation)
        .filter_by(project_id=isolated_id)
        .count()
        == 1
    )
    assert (
        session.query(models.OverlayProjectCategoryReservation)
        .filter_by(project_id=isolated_id)
        .count()
        == 0
    )
    assert (
        session.query(models.IsolatedProjectCategoryAllocation)
        .filter_by(project_id=overlay_id)
        .count()
        == 0
    )

    expense = client.post(
        "/expenses/",
        json={
            "title": "Vault spend",
            "amount": 100_000,
            "category": "Travel",
            "date": today.isoformat(),
            "project_id": isolated_id,
        },
        headers=headers,
    )
    assert expense.status_code == 201, expense.text
    ledger_project_ids = {
        row.project_id
        for row in session.query(models.EntityLedger)
        .filter(models.EntityLedger.project_id == isolated_id)
        .all()
    }
    assert ledger_project_ids == {isolated_id}


def test_project_responses_expose_overlay_reserved_and_isolated_allocated_amounts(client):
    headers = create_user_and_token(client, "moneycontracts", "moneycontracts@example.com", "Password123!")
    today = user_timezone_today()
    wallet_id = _default_wallet_id(client, headers)
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
            "title": "Reserved trip",
            "start_date": today.isoformat(),
            "target_end_date": None,
            "budget_year": today.year,
            "budget_month": today.month,
            "category_reservations": [{"category": "Travel", "limit_amount": 300_000}],
            "subcategory_reservations": [],
        },
        headers=headers,
    )
    assert overlay.status_code == 201, overlay.text
    overlay_category = overlay.json()["category_breakdown"][0]
    assert overlay_category["reserved_amount"] == 300_000
    assert overlay_category["allocated_amount"] is None
    assert overlay_category["limit_amount"] == 300_000

    isolated = client.post(
        "/projects",
        json={
            "title": "Allocated vault",
            "is_isolated": True,
            "start_date": today.isoformat(),
            "target_end_date": None,
            "wallet_allocations": [{"wallet_id": wallet_id, "amount": 800_000}],
            "category_allocations": [{"category": "Travel", "limit_amount": 500_000}],
        },
        headers=headers,
    )
    assert isolated.status_code == 201, isolated.text
    isolated_category = isolated.json()["category_breakdown"][0]
    assert isolated_category["allocated_amount"] == 500_000
    assert isolated_category["reserved_amount"] is None
    assert isolated_category["limit_amount"] == 500_000


def test_project_money_mechanics_architecture_rejects_legacy_forward_names(session):
    old_alias_names = [
        "ProjectWalletAllocation",
        "ProjectCategoryLimit",
        "ProjectCategoryMonthlyLimit",
        "ProjectSubcategoryMonthlyLimit",
    ]
    assert [name for name in old_alias_names if hasattr(models, name)] == []

    old_relationship_names = [
        "category_limits",
        "monthly_category_limits",
        "monthly_subcategory_limits",
        "wallet_allocations",
    ]
    assert [name for name in old_relationship_names if hasattr(models.Project, name)] == []

    tables = set(models.Base.metadata.tables)
    assert "project_subcategories" not in tables
    assert "legacy_project_subcategories" in tables
    assert "isolated_project_subcategory_allocations" in tables

    assert not hasattr(models, "ProjectSubcategory")
    assert hasattr(models, "LegacyProjectSubcategory")
    assert hasattr(models, "IsolatedProjectSubcategoryAllocation")


def test_project_money_mechanics_service_boundaries_are_type_specific():
    root = Path(__file__).resolve().parents[1]
    shared_service = (root / "app" / "services" / "project_service.py").read_text()
    overlay_service = (root / "app" / "services" / "overlay_project_service.py").read_text()
    isolated_service = (root / "app" / "services" / "isolated_project_service.py").read_text()

    assert "def validate_overlay_project_category_reservation" not in shared_service
    assert "def validate_overlay_project_subcategory_reservation" not in shared_service
    assert "def validate_project_wallet_allocations" not in shared_service
    assert "def validate_project_limit_sum" not in shared_service
    assert "def get_isolated_project_category_spent_amount" not in shared_service

    assert "def validate_overlay_project_category_reservation" in overlay_service
    assert "def validate_overlay_project_subcategory_reservation" in overlay_service
    assert "def sweep_overlay_project_reservations" in overlay_service

    assert "def validate_project_wallet_allocations" in isolated_service
    assert "def validate_project_limit_sum" in isolated_service
    assert "def get_isolated_project_category_spent_amount" in isolated_service
