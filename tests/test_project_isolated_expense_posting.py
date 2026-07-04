from app import models
from tests.helpers import create_user_and_token, user_timezone_today


def _default_wallet_id(client, headers):
    wallets = client.get("/wallets", headers=headers)
    assert wallets.status_code == 200, wallets.text
    return wallets.json()[0]["id"]


def _create_wallet(client, headers, name, amount=1_000_000):
    response = client.post(
        "/wallets",
        json={"name": name, "initial_balance": amount},
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def _create_isolated_project(client, headers, wallet_id, *, amount=1_000_000, category_amount=None):
    return _create_isolated_project_with_wallets(
        client,
        headers,
        [{"wallet_id": wallet_id, "amount": amount}],
        amount=amount,
        category_amount=category_amount,
    )


def _create_isolated_project_with_wallets(client, headers, wallet_allocations, *, amount, category_amount=None):
    today = user_timezone_today()
    response = client.post(
        "/projects",
        json={
            "title": "Wedding vault",
            "is_isolated": True,
            "start_date": today.isoformat(),
            "target_end_date": today.replace(year=today.year + 1).isoformat(),
            "wallet_allocations": wallet_allocations,
            "category_allocations": [
                {
                    "category": "Family & Events",
                    "limit_amount": category_amount if category_amount is not None else amount,
                }
            ],
        },
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_isolated_project_expense_rejects_wallet_that_did_not_fund_project(client):
    headers = create_user_and_token(
        client,
        "isolatedexpensezerowallet",
        "isolatedexpensezerowallet@example.com",
        "Password123!",
    )
    funded_wallet_id = _default_wallet_id(client, headers)
    unfunded_wallet_id = _create_wallet(client, headers, "Everyday cash")
    project = _create_isolated_project(client, headers, funded_wallet_id, amount=1_000_000)

    response = client.post(
        "/expenses/",
        json={
            "title": "Venue food",
            "amount": 100_000,
            "category": "Family & Events",
            "date": user_timezone_today().isoformat(),
            "wallet_id": unfunded_wallet_id,
            "project_id": project["id"],
        },
        headers=headers,
    )

    assert response.status_code == 400
    detail = response.json()["detail"]
    assert detail["code"] == "projects.wallet_funding_required"
    assert detail["wallet_id"] == unfunded_wallet_id
    assert detail["project_id"] == project["id"]


def test_isolated_project_expense_rejects_wallet_amount_above_remaining_contribution(client):
    headers = create_user_and_token(
        client,
        "isolatedexpensewalletover",
        "isolatedexpensewalletover@example.com",
        "Password123!",
    )
    wallet_id = _default_wallet_id(client, headers)
    second_wallet_id = _create_wallet(client, headers, "Wedding reserve", amount=1_000_000)
    project = _create_isolated_project_with_wallets(
        client,
        headers,
        [
            {"wallet_id": wallet_id, "amount": 400_000},
            {"wallet_id": second_wallet_id, "amount": 100_000},
        ],
        amount=500_000,
    )

    response = client.post(
        "/expenses/",
        json={
            "title": "Venue bill",
            "amount": 401_000,
            "category": "Family & Events",
            "date": user_timezone_today().isoformat(),
            "wallet_id": wallet_id,
            "project_id": project["id"],
        },
        headers=headers,
    )

    assert response.status_code == 400
    detail = response.json()["detail"]
    assert detail["code"] == "projects.wallet_funding_exceeded"
    assert detail["wallet_id"] == wallet_id
    assert detail["project_id"] == project["id"]
    assert detail["remaining_amount"] == 400_000
    assert detail["requested_amount"] == 401_000


def test_isolated_project_expense_allows_linked_wallet_within_remaining_without_monthly_budget(client, session):
    headers = create_user_and_token(
        client,
        "isolatedexpenseallowed",
        "isolatedexpenseallowed@example.com",
        "Password123!",
    )
    wallet_id = _default_wallet_id(client, headers)
    second_wallet_id = _create_wallet(client, headers, "Wedding reserve", amount=1_000_000)
    today = user_timezone_today()
    project = _create_isolated_project_with_wallets(
        client,
        headers,
        [
            {"wallet_id": wallet_id, "amount": 400_000},
            {"wallet_id": second_wallet_id, "amount": 100_000},
        ],
        amount=500_000,
    )

    response = client.post(
        "/expenses/",
        json={
            "title": "Venue bill",
            "amount": 300_000,
            "category": "Family & Events",
            "date": today.isoformat(),
            "wallet_id": wallet_id,
            "project_id": project["id"],
        },
        headers=headers,
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["project_id"] == project["id"]
    assert body["wallet_id"] == wallet_id

    budget = (
        session.query(models.Budget)
        .filter(
            models.Budget.owner_id == body["owner_id"],
            models.Budget.category == models.ExpenseCategory.FAMILY_EVENTS,
            models.Budget.budget_year == today.year,
            models.Budget.budget_month == today.month,
        )
        .first()
    )
    assert budget is None

    blocked = client.post(
        "/expenses/",
        json={
            "title": "Extra bill",
            "amount": 101_000,
            "category": "Family & Events",
            "date": today.isoformat(),
            "wallet_id": wallet_id,
            "project_id": project["id"],
        },
        headers=headers,
    )

    assert blocked.status_code == 400
    detail = blocked.json()["detail"]
    assert detail["code"] == "projects.wallet_funding_exceeded"
    assert detail["remaining_amount"] == 100_000


def test_isolated_project_expense_allows_multi_wallet_payment_with_each_wallet_within_cap(client):
    headers = create_user_and_token(
        client,
        "isolatedexpensemultiwallet",
        "isolatedexpensemultiwallet@example.com",
        "Password123!",
    )
    wallet_a_id = _default_wallet_id(client, headers)
    wallet_b_id = _create_wallet(client, headers, "Project savings", amount=1_000_000)
    project = _create_isolated_project_with_wallets(
        client,
        headers,
        [
            {"wallet_id": wallet_a_id, "amount": 400_000},
            {"wallet_id": wallet_b_id, "amount": 600_000},
        ],
        amount=1_000_000,
    )

    response = client.post(
        "/expenses/",
        json={
            "title": "Venue bill",
            "amount": 450_000,
            "category": "Family & Events",
            "date": user_timezone_today().isoformat(),
            "wallet_allocations": [
                {"wallet_id": wallet_a_id, "amount": 400_000},
                {"wallet_id": wallet_b_id, "amount": 50_000},
            ],
            "project_id": project["id"],
        },
        headers=headers,
    )

    assert response.status_code == 201, response.text
    assert sorted(
        (item["wallet_id"], item["amount"]) for item in response.json()["wallet_allocations"]
    ) == [
        (wallet_a_id, 400_000),
        (wallet_b_id, 50_000),
    ]


def test_isolated_project_session_finalize_rejects_wallet_above_remaining_contribution(client):
    headers = create_user_and_token(
        client,
        "isolatedexpensesessionwallet",
        "isolatedexpensesessionwallet@example.com",
        "Password123!",
    )
    wallet_id = _default_wallet_id(client, headers)
    second_wallet_id = _create_wallet(client, headers, "Wedding reserve", amount=1_000_000)
    today = user_timezone_today()
    project = _create_isolated_project_with_wallets(
        client,
        headers,
        [
            {"wallet_id": wallet_id, "amount": 100_000},
            {"wallet_id": second_wallet_id, "amount": 100_000},
        ],
        amount=200_000,
    )

    draft = client.post(
        "/expenses/session-drafts",
        json={
            "title": "Wedding receipt",
            "date": today.isoformat(),
            "amount_paid": 101_000,
        },
        headers=headers,
    )
    assert draft.status_code == 201, draft.text
    draft_id = draft.json()["id"]

    item = client.post(
        f"/expenses/session-drafts/{draft_id}/items",
        json={
            "label": "Venue snacks",
            "original_amount": 101_000,
            "category": "Family & Events",
            "project_id": project["id"],
        },
        headers=headers,
    )
    assert item.status_code == 201, item.text

    allocation = client.post(
        f"/expenses/session-drafts/{draft_id}/wallet-allocations",
        json={"wallet_id": wallet_id, "amount": 101_000},
        headers=headers,
    )
    assert allocation.status_code == 201, allocation.text

    response = client.post(f"/expenses/session-drafts/{draft_id}/finalize", headers=headers)

    assert response.status_code == 400
    detail = response.json()["detail"]
    assert detail["code"] == "projects.wallet_funding_exceeded"
    assert detail["wallet_id"] == wallet_id
    assert detail["remaining_amount"] == 100_000


def test_isolated_project_refund_restores_project_spent_and_wallet_remaining(client):
    headers = create_user_and_token(
        client,
        "isolatedexpenserefund",
        "isolatedexpenserefund@example.com",
        "Password123!",
    )
    wallet_id = _default_wallet_id(client, headers)
    today = user_timezone_today()
    project = _create_isolated_project(client, headers, wallet_id, amount=400_000)

    expense = client.post(
        "/expenses/",
        json={
            "title": "Venue bill",
            "amount": 300_000,
            "category": "Family & Events",
            "date": today.isoformat(),
            "wallet_id": wallet_id,
            "project_id": project["id"],
        },
        headers=headers,
    )
    assert expense.status_code == 201, expense.text

    refund = client.post(
        f"/expenses/{expense.json()['id']}/refund",
        json={"destination_wallet_id": wallet_id, "amount": 100_000},
        headers=headers,
    )
    assert refund.status_code == 201, refund.text
    assert refund.json()["project_id"] == project["id"]

    followup = client.post(
        "/expenses/",
        json={
            "title": "Venue extras",
            "amount": 200_000,
            "category": "Family & Events",
            "date": today.isoformat(),
            "wallet_id": wallet_id,
            "project_id": project["id"],
        },
        headers=headers,
    )
    assert followup.status_code == 201, followup.text

    detail = client.get(f"/projects/{project['id']}", headers=headers)
    assert detail.status_code == 200, detail.text
    category = detail.json()["category_breakdown"][0]
    assert category["spent"] == 400_000
    assert category["remaining"] == 0


def test_isolated_project_void_restores_wallet_remaining(client):
    headers = create_user_and_token(
        client,
        "isolatedexpensevoid",
        "isolatedexpensevoid@example.com",
        "Password123!",
    )
    wallet_id = _default_wallet_id(client, headers)
    today = user_timezone_today()
    project = _create_isolated_project(client, headers, wallet_id, amount=300_000)

    expense = client.post(
        "/expenses/",
        json={
            "title": "Venue bill",
            "amount": 300_000,
            "category": "Family & Events",
            "date": today.isoformat(),
            "wallet_id": wallet_id,
            "project_id": project["id"],
        },
        headers=headers,
    )
    assert expense.status_code == 201, expense.text

    deleted = client.delete(f"/expenses/{expense.json()['id']}", headers=headers)
    assert deleted.status_code == 204, deleted.text

    replacement = client.post(
        "/expenses/",
        json={
            "title": "Venue bill",
            "amount": 300_000,
            "category": "Family & Events",
            "date": today.isoformat(),
            "wallet_id": wallet_id,
            "project_id": project["id"],
        },
        headers=headers,
    )
    assert replacement.status_code == 201, replacement.text


def test_isolated_project_expense_list_shows_project_and_micro_subcategory_context(client):
    headers = create_user_and_token(
        client,
        "isolatedexpensecontext",
        "isolatedexpensecontext@example.com",
        "Password123!",
    )
    wallet_id = _default_wallet_id(client, headers)
    today = user_timezone_today()
    project = _create_isolated_project(client, headers, wallet_id, amount=300_000)

    subcategory = client.post(
        f"/projects/{project['id']}/subcategories",
        json={
            "category": "Family & Events",
            "name": "Catering",
            "limit_amount": 200_000,
        },
        headers=headers,
    )
    assert subcategory.status_code == 201, subcategory.text
    subcategories = client.get(f"/projects/{project['id']}/subcategories", headers=headers)
    assert subcategories.status_code == 200, subcategories.text
    subcategory_id = subcategories.json()[0]["id"]

    expense = client.post(
        "/expenses/",
        json={
            "title": "Food bill",
            "amount": 100_000,
            "category": "Family & Events",
            "date": today.isoformat(),
            "wallet_id": wallet_id,
            "project_id": project["id"],
            "project_subcategory_id": subcategory_id,
        },
        headers=headers,
    )
    assert expense.status_code == 201, expense.text
    assert expense.json()["project_title"] == "Wedding vault"
    assert expense.json()["project_subcategory_name"] == "Catering"

    listed = client.get("/expenses/", headers=headers)
    assert listed.status_code == 200, listed.text
    expense_items = [item["expense"] for item in listed.json()["items"] if item["type"] == "EXPENSE"]
    listed_expense = next(item for item in expense_items if item["id"] == expense.json()["id"])
    assert listed_expense["project_title"] == "Wedding vault"
    assert listed_expense["project_subcategory_name"] == "Catering"
