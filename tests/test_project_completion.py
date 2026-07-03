from app import models
from tests.helpers import create_budget, create_user_and_token, user_timezone_today


def _add_month(year: int, month: int) -> tuple[int, int]:
    if month == 12:
        return year + 1, 1
    return year, month + 1


def _previous_month(year: int, month: int) -> tuple[int, int]:
    if month == 1:
        return year - 1, 12
    return year, month - 1


def _category_limits_by_month(rows):
    return {
        (item["budget_year"], item["budget_month"], item["category"]): item["limit_amount"]
        for item in rows
    }


def test_completing_overlay_project_sweeps_current_and_future_category_reservations(client):
    headers = create_user_and_token(
        client,
        "overlaycompletecatsweep",
        "overlaycompletecatsweep@example.com",
        "Password123!",
    )
    today = user_timezone_today()
    current_year, current_month = today.year, today.month
    past_year, past_month = _previous_month(current_year, current_month)
    future_year, future_month = _add_month(current_year, current_month)

    for year, month in [
        (past_year, past_month),
        (current_year, current_month),
        (future_year, future_month),
    ]:
        budget = create_budget(
            client,
            headers,
            category="Travel",
            monthly_limit=1_000_000,
            budget_year=year,
            budget_month=month,
        )
        assert budget.status_code == 201, budget.text

    project = client.post(
        "/projects",
        json={
            "title": "Wrap trip",
            "is_isolated": False,
            "start_date": f"{past_year:04d}-{past_month:02d}-01",
            "target_end_date": f"{future_year:04d}-{future_month:02d}-28",
        },
        headers=headers,
    )
    assert project.status_code == 201, project.text
    project_id = project.json()["id"]

    for year, month in [
        (past_year, past_month),
        (current_year, current_month),
        (future_year, future_month),
    ]:
        reservation = client.post(
            f"/projects/{project_id}/category-limits",
            json={
                "category": "Travel",
                "limit_amount": 500_000,
                "budget_year": year,
                "budget_month": month,
            },
            headers=headers,
        )
        assert reservation.status_code == 201, reservation.text

    expense = client.post(
        "/expenses/",
        json={
            "title": "Current hotel",
            "amount": 120_000,
            "category": "Travel",
            "date": today.isoformat(),
            "project_id": project_id,
        },
        headers=headers,
    )
    assert expense.status_code == 201, expense.text

    completed = client.post(f"/projects/{project_id}/complete", json={}, headers=headers)
    assert completed.status_code == 200, completed.text
    assert completed.json()["status"] == "COMPLETED"
    assert completed.json()["completed_at"] == today.isoformat()

    limits = client.get(f"/projects/{project_id}/category-limits", headers=headers)
    assert limits.status_code == 200, limits.text
    limits_by_month = _category_limits_by_month(limits.json())
    assert limits_by_month[(past_year, past_month, "Travel")] == 500_000
    assert limits_by_month[(current_year, current_month, "Travel")] == 120_000
    assert (future_year, future_month, "Travel") not in limits_by_month

    detail = client.get(
        "/budgets/item/detail",
        params={"budget_year": current_year, "budget_month": current_month, "category": "Travel"},
        headers=headers,
    )
    assert detail.status_code == 200, detail.text
    assert detail.json()["project_reserved_amount"] == 0
    assert detail.json()["free_general_limit"] == 1_000_000


def test_completing_overlay_project_sweeps_subcategory_reservations_with_refunds(client, session):
    headers = create_user_and_token(
        client,
        "overlaycompletesubsweep",
        "overlaycompletesubsweep@example.com",
        "Password123!",
    )
    today = user_timezone_today()
    future_year, future_month = _add_month(today.year, today.month)
    budget = create_budget(
        client,
        headers,
        category="Travel",
        monthly_limit=1_000_000,
        budget_year=today.year,
        budget_month=today.month,
    )
    assert budget.status_code == 201, budget.text
    budget_id = budget.json()["id"]
    future_budget = create_budget(
        client,
        headers,
        category="Travel",
        monthly_limit=1_000_000,
        budget_year=future_year,
        budget_month=future_month,
    )
    assert future_budget.status_code == 201, future_budget.text
    future_budget_id = future_budget.json()["id"]

    subcategory = client.post(
        f"/budgets/{budget_id}/subcategories",
        json={"category": "Travel", "name": "Lodging", "monthly_limit": 300_000},
        headers=headers,
    )
    assert subcategory.status_code == 201, subcategory.text
    user_subcategory_id = subcategory.json()["id"]
    future_subcategory = client.post(
        f"/budgets/{future_budget_id}/subcategories",
        json={
            "category": "Travel",
            "name": "Lodging",
            "existing_id": user_subcategory_id,
            "monthly_limit": 300_000,
        },
        headers=headers,
    )
    assert future_subcategory.status_code == 201, future_subcategory.text

    project = client.post(
        "/projects",
        json={
            "title": "Refunded trip",
            "is_isolated": False,
            "start_date": today.isoformat(),
            "target_end_date": f"{future_year:04d}-{future_month:02d}-28",
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
            "budget_year": today.year,
            "budget_month": today.month,
        },
        headers=headers,
    )
    assert category_limit.status_code == 201, category_limit.text
    future_category_limit = client.post(
        f"/projects/{project_id}/category-limits",
        json={
            "category": "Travel",
            "limit_amount": 500_000,
            "budget_year": future_year,
            "budget_month": future_month,
        },
        headers=headers,
    )
    assert future_category_limit.status_code == 201, future_category_limit.text

    subcategory_limit = client.post(
        f"/projects/{project_id}/subcategories",
        json={
            "category": "Travel",
            "user_subcategory_id": user_subcategory_id,
            "limit_amount": 200_000,
            "budget_year": today.year,
            "budget_month": today.month,
        },
        headers=headers,
    )
    assert subcategory_limit.status_code == 201, subcategory_limit.text
    future_subcategory_limit = client.post(
        f"/projects/{project_id}/subcategories",
        json={
            "category": "Travel",
            "user_subcategory_id": user_subcategory_id,
            "limit_amount": 200_000,
            "budget_year": future_year,
            "budget_month": future_month,
        },
        headers=headers,
    )
    assert future_subcategory_limit.status_code == 201, future_subcategory_limit.text

    expense = client.post(
        "/expenses/",
        json={
            "title": "Hotel",
            "amount": 120_000,
            "category": "Travel",
            "subcategory_id": user_subcategory_id,
            "date": today.isoformat(),
            "project_id": project_id,
        },
        headers=headers,
    )
    assert expense.status_code == 201, expense.text
    expense_id = expense.json()["id"]

    refund = models.FinancialEvent(
        owner_id=expense.json()["owner_id"],
        title="Hotel refund",
        event_type=models.TransactionType.REFUND,
        status=models.FinancialEventStatus.POSTED,
        linked_event_id=expense_id,
        date=today,
    )
    session.add(refund)
    session.flush()
    session.add(
        models.EntityLedger(
            event_id=refund.id,
            amount=20_000,
            category=models.ExpenseCategory.TRAVEL,
            subcategory_id=user_subcategory_id,
            project_id=project_id,
            budget_id=budget_id,
        )
    )
    session.commit()

    completed = client.post(f"/projects/{project_id}/complete", json={}, headers=headers)
    assert completed.status_code == 200, completed.text
    assert completed.json()["status"] == "COMPLETED"

    category_limits = client.get(f"/projects/{project_id}/category-limits", headers=headers)
    assert category_limits.status_code == 200, category_limits.text
    category_limits_by_month = _category_limits_by_month(category_limits.json())
    assert category_limits_by_month[(today.year, today.month, "Travel")] == 100_000
    assert (future_year, future_month, "Travel") not in category_limits_by_month

    subcategories = client.get(
        f"/projects/{project_id}/subcategories",
        params={"budget_year": today.year, "budget_month": today.month},
        headers=headers,
    )
    assert subcategories.status_code == 200, subcategories.text
    assert len(subcategories.json()) == 1
    swept = subcategories.json()[0]
    assert swept["user_subcategory_id"] == user_subcategory_id
    assert swept["limit_amount"] == 100_000
    assert swept["spent"] == 100_000
    assert swept["remaining"] == 0

    future_subcategories = client.get(
        f"/projects/{project_id}/subcategories",
        params={"budget_year": future_year, "budget_month": future_month},
        headers=headers,
    )
    assert future_subcategories.status_code == 200, future_subcategories.text
    assert future_subcategories.json() == []


def test_paused_overlay_project_can_be_completed(client):
    headers = create_user_and_token(
        client,
        "pausedoverlaycomplete",
        "pausedoverlaycomplete@example.com",
        "Password123!",
    )
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

    project = client.post(
        "/projects",
        json={
            "title": "Paused trip",
            "is_isolated": False,
            "start_date": today.isoformat(),
            "target_end_date": today.isoformat(),
        },
        headers=headers,
    )
    assert project.status_code == 201, project.text
    project_id = project.json()["id"]

    reservation = client.post(
        f"/projects/{project_id}/category-limits",
        json={
            "category": "Travel",
            "limit_amount": 400_000,
            "budget_year": today.year,
            "budget_month": today.month,
        },
        headers=headers,
    )
    assert reservation.status_code == 201, reservation.text

    stopped = client.post(f"/projects/{project_id}/stop", headers=headers)
    assert stopped.status_code == 200, stopped.text
    assert stopped.json()["status"] == "STOPPED"

    completed = client.post(f"/projects/{project_id}/complete", json={}, headers=headers)
    assert completed.status_code == 200, completed.text
    assert completed.json()["status"] == "COMPLETED"
    assert completed.json()["completed_at"] == today.isoformat()


def test_completed_or_archived_project_cannot_be_completed_again(client):
    completed_headers = create_user_and_token(
        client,
        "completeinvalidcompleted",
        "completeinvalidcompleted@example.com",
        "Password123!",
    )
    today = user_timezone_today()
    completed_project = client.post(
        "/projects",
        json={
            "title": "Already done",
            "is_isolated": False,
            "start_date": today.isoformat(),
            "target_end_date": today.isoformat(),
        },
        headers=completed_headers,
    )
    assert completed_project.status_code == 201, completed_project.text
    completed_project_id = completed_project.json()["id"]
    first_complete = client.post(f"/projects/{completed_project_id}/complete", json={}, headers=completed_headers)
    assert first_complete.status_code == 200, first_complete.text

    repeated_complete = client.post(f"/projects/{completed_project_id}/complete", json={}, headers=completed_headers)
    assert repeated_complete.status_code == 400
    assert repeated_complete.json()["detail"] == "projects.complete_invalid_state"

    archived_headers = create_user_and_token(
        client,
        "completeinvalidarchived",
        "completeinvalidarchived@example.com",
        "Password123!",
    )
    archived_project = client.post(
        "/projects",
        json={
            "title": "Archived trip",
            "is_isolated": False,
            "start_date": today.isoformat(),
            "target_end_date": today.isoformat(),
        },
        headers=archived_headers,
    )
    assert archived_project.status_code == 201, archived_project.text
    archived_project_id = archived_project.json()["id"]
    archived = client.post(f"/projects/{archived_project_id}/archive", headers=archived_headers)
    assert archived.status_code == 200, archived.text

    archived_complete = client.post(f"/projects/{archived_project_id}/complete", json={}, headers=archived_headers)
    assert archived_complete.status_code == 400
    assert archived_complete.json()["detail"] == "projects.complete_invalid_state"
