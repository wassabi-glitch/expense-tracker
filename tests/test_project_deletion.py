from datetime import date

from app import models
from tests.helpers import create_budget, create_user_and_token


def _create_overlay_project_with_reservations(client, headers):
    budget = create_budget(
        client,
        headers,
        category="Travel",
        monthly_limit=1_000_000,
        budget_year=2026,
        budget_month=6,
    )
    assert budget.status_code == 201, budget.text

    subcategory = client.post(
        f"/budgets/{budget.json()['id']}/subcategories",
        json={"category": "Travel", "name": "Lodging", "monthly_limit": 300_000},
        headers=headers,
    )
    assert subcategory.status_code == 201, subcategory.text

    project = client.post(
        "/projects",
        json={
            "title": "June trip",
            "is_isolated": False,
            "start_date": "2026-06-01",
            "target_end_date": "2026-06-30",
        },
        headers=headers,
    )
    assert project.status_code == 201, project.text
    project_id = project.json()["id"]

    category_limit = client.post(
        f"/projects/{project_id}/category-limits",
        json={
            "category": "Travel",
            "limit_amount": 500_000,
            "budget_year": 2026,
            "budget_month": 6,
        },
        headers=headers,
    )
    assert category_limit.status_code == 201, category_limit.text

    subcategory_limit = client.post(
        f"/projects/{project_id}/subcategories",
        json={
            "category": "Travel",
            "user_subcategory_id": subcategory.json()["id"],
            "limit_amount": 200_000,
            "budget_year": 2026,
            "budget_month": 6,
        },
        headers=headers,
    )
    assert subcategory_limit.status_code == 201, subcategory_limit.text
    return budget.json(), subcategory.json(), project.json()


def _linked_overlay_expense(client, headers, project_id, *, amount=120_000):
    expense = client.post(
        "/expenses/",
        json={
            "title": "Hotel",
            "amount": amount,
            "category": "Travel",
            "description": "test",
            "date": date(2026, 6, 10).isoformat(),
            "project_id": project_id,
        },
        headers=headers,
    )
    assert expense.status_code == 201, expense.text
    return expense.json()


def test_pristine_overlay_project_delete_hard_deletes_reservations_and_releases_budget_room(client, session):
    headers = create_user_and_token(
        client,
        "projectdeletepristine",
        "projectdeletepristine@example.com",
        "Password123!",
    )
    _, _, project = _create_overlay_project_with_reservations(client, headers)
    project_id = project["id"]

    before = client.get(
        "/budgets/",
        params={"budget_year": 2026, "budget_month": 6},
        headers=headers,
    )
    assert before.status_code == 200, before.text
    travel_before = next(item for item in before.json() if item["category"] == "Travel")
    assert travel_before["project_reserved_amount"] == 500_000
    assert travel_before["free_general_limit"] == 500_000

    deleted = client.delete(f"/projects/{project_id}", headers=headers)
    assert deleted.status_code == 204, deleted.text

    missing = client.get(f"/projects/{project_id}", headers=headers)
    assert missing.status_code == 404

    after = client.get(
        "/budgets/",
        params={"budget_year": 2026, "budget_month": 6},
        headers=headers,
    )
    assert after.status_code == 200, after.text
    travel_after = next(item for item in after.json() if item["category"] == "Travel")
    assert travel_after["project_reserved_amount"] == 0
    assert travel_after["free_general_limit"] == 1_000_000

    session.expire_all()
    assert session.query(models.ProjectCategoryMonthlyLimit).filter_by(project_id=project_id).count() == 0
    assert session.query(models.ProjectSubcategoryMonthlyLimit).filter_by(project_id=project_id).count() == 0


def test_non_pristine_overlay_delete_requires_resolution_and_archive_keeps_ledger_links(client, session):
    headers = create_user_and_token(
        client,
        "projectdeletearchive",
        "projectdeletearchive@example.com",
        "Password123!",
    )
    _, _, project = _create_overlay_project_with_reservations(client, headers)
    expense = _linked_overlay_expense(client, headers, project["id"], amount=120_000)

    preview = client.get(f"/projects/{project['id']}/delete-preview", headers=headers)
    assert preview.status_code == 200, preview.text
    assert preview.json()["is_pristine"] is False
    assert preview.json()["linked_expense_count"] == 1
    assert preview.json()["linked_expense_total"] == 120_000

    direct_delete = client.delete(f"/projects/{project['id']}", headers=headers)
    assert direct_delete.status_code == 409
    assert direct_delete.json()["detail"]["code"] == "projects.delete_resolution_required"
    assert direct_delete.json()["detail"]["linked_expense_count"] == 1

    archived = client.post(
        f"/projects/{project['id']}/delete-resolution",
        json={"action": "ARCHIVE"},
        headers=headers,
    )
    assert archived.status_code == 200, archived.text
    assert archived.json()["status"] == "ARCHIVED"

    session.expire_all()
    leg = session.query(models.EntityLedger).filter(models.EntityLedger.event_id == expense["id"]).first()
    assert leg.project_id == project["id"]


def test_archived_overlay_project_rejects_repeated_archive_actions(client):
    headers = create_user_and_token(
        client,
        "projectdeletealreadyarchived",
        "projectdeletealreadyarchived@example.com",
        "Password123!",
    )
    _, _, project = _create_overlay_project_with_reservations(client, headers)
    _linked_overlay_expense(client, headers, project["id"], amount=120_000)

    archived = client.post(f"/projects/{project['id']}/archive", headers=headers)
    assert archived.status_code == 200, archived.text
    assert archived.json()["status"] == "ARCHIVED"

    archive_again = client.post(f"/projects/{project['id']}/archive", headers=headers)
    assert archive_again.status_code == 400
    assert archive_again.json()["detail"] == "projects.already_archived"

    resolution_archive_again = client.post(
        f"/projects/{project['id']}/delete-resolution",
        json={"action": "ARCHIVE"},
        headers=headers,
    )
    assert resolution_archive_again.status_code == 400
    assert resolution_archive_again.json()["detail"] == "projects.already_archived"


def test_detach_resolution_strips_project_links_then_hard_deletes_overlay_project(client, session):
    headers = create_user_and_token(
        client,
        "projectdeletedetach",
        "projectdeletedetach@example.com",
        "Password123!",
    )
    _, _, project = _create_overlay_project_with_reservations(client, headers)
    expense = _linked_overlay_expense(client, headers, project["id"], amount=80_000)

    detached = client.post(
        f"/projects/{project['id']}/delete-resolution",
        json={"action": "DETACH_EXPENSES"},
        headers=headers,
    )
    assert detached.status_code == 204, detached.text

    missing = client.get(f"/projects/{project['id']}", headers=headers)
    assert missing.status_code == 404

    refreshed_expense = client.get(f"/expenses/{expense['id']}", headers=headers)
    assert refreshed_expense.status_code == 200, refreshed_expense.text
    assert refreshed_expense.json()["project_id"] is None
    assert refreshed_expense.json()["project_subcategory_id"] is None

    session.expire_all()
    legs = session.query(models.EntityLedger).filter(models.EntityLedger.event_id == expense["id"]).all()
    assert legs
    assert all(leg.project_id is None and leg.project_subcategory_id is None for leg in legs)


def test_cascade_void_resolution_requires_title_and_appends_reversal_before_hard_delete(client, session):
    headers = create_user_and_token(
        client,
        "projectdeletecascade",
        "projectdeletecascade@example.com",
        "Password123!",
    )
    _, _, project = _create_overlay_project_with_reservations(client, headers)
    expense = _linked_overlay_expense(client, headers, project["id"], amount=90_000)

    rejected = client.post(
        f"/projects/{project['id']}/delete-resolution",
        json={"action": "CASCADE_VOID", "confirm_title": "Wrong title"},
        headers=headers,
    )
    assert rejected.status_code == 400
    assert rejected.json()["detail"] == "projects.confirm_title_mismatch"

    resolved = client.post(
        f"/projects/{project['id']}/delete-resolution",
        json={"action": "CASCADE_VOID", "confirm_title": "June trip"},
        headers=headers,
    )
    assert resolved.status_code == 204, resolved.text

    session.expire_all()
    original = session.query(models.FinancialEvent).filter(models.FinancialEvent.id == expense["id"]).first()
    assert original.status == models.FinancialEventStatus.VOIDED
    assert original.void_reversal_event_id is not None

    reversal = (
        session.query(models.FinancialEvent)
        .filter(models.FinancialEvent.id == original.void_reversal_event_id)
        .first()
    )
    assert reversal.status == models.FinancialEventStatus.REVERSAL
    assert reversal.reverses_event_id == original.id
    assert reversal.reference_type == models.ReferenceType.VOID_REVERSAL
    assert [leg.amount for leg in reversal.entity_legs] == [-90_000]
    assert session.query(models.Project).filter(models.Project.id == project["id"]).first() is None
