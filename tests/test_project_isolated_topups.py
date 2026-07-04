from tests.helpers import create_user_and_token, user_timezone_today


def _wallet_id(client, headers):
    response = client.get("/wallets", headers=headers)
    assert response.status_code == 200, response.text
    return response.json()[0]["id"]


def test_isolated_project_top_up_adds_wallet_locks_and_unassigned_funding(client):
    headers = create_user_and_token(
        client,
        "isolatedtopup",
        "isolatedtopup@example.com",
        "Password123!",
    )
    today = user_timezone_today()
    default_wallet_id = _wallet_id(client, headers)
    cash_wallet = client.post(
        "/wallets",
        json={"name": "Cash top-up", "initial_balance": 1_000_000},
        headers=headers,
    )
    assert cash_wallet.status_code == 201, cash_wallet.text

    created = client.post(
        "/projects",
        json={
            "title": "Renovation",
            "is_isolated": True,
            "start_date": today.isoformat(),
            "wallet_allocations": [{"wallet_id": default_wallet_id, "amount": 1_000_000}],
            "category_allocations": [{"category": "Housing", "limit_amount": 700_000}],
        },
        headers=headers,
    )
    assert created.status_code == 201, created.text
    project_id = created.json()["id"]

    topped_up = client.post(
        f"/projects/{project_id}/top-ups",
        json={
            "wallet_allocations": [
                {"wallet_id": default_wallet_id, "amount": 300_000},
                {"wallet_id": cash_wallet.json()["id"], "amount": 400_000},
            ],
        },
        headers=headers,
    )

    assert topped_up.status_code == 200, topped_up.text
    isolated = topped_up.json()["isolated"]
    assert isolated["funding_limit"] == 1_700_000
    assert isolated["allocated_funding"] == 700_000
    assert isolated["unallocated_funding"] == 1_000_000
    assert [
        {"wallet_id": item["wallet_id"], "amount": item["amount"]}
        for item in isolated["wallet_allocations"]
    ] == [
        {"wallet_id": default_wallet_id, "amount": 1_300_000},
        {"wallet_id": cash_wallet.json()["id"], "amount": 400_000},
    ]


def test_isolated_project_category_allocation_assigns_unassigned_funding(client):
    headers = create_user_and_token(
        client,
        "isolatedassignparent",
        "isolatedassignparent@example.com",
        "Password123!",
    )
    today = user_timezone_today()
    wallet_id = _wallet_id(client, headers)
    created = client.post(
        "/projects",
        json={
            "title": "Wedding",
            "is_isolated": True,
            "start_date": today.isoformat(),
            "wallet_allocations": [{"wallet_id": wallet_id, "amount": 1_000_000}],
            "category_allocations": [{"category": "Family & Events", "limit_amount": 600_000}],
        },
        headers=headers,
    )
    assert created.status_code == 201, created.text
    project_id = created.json()["id"]

    assigned = client.post(
        f"/projects/{project_id}/category-allocations",
        json={"category": "Travel", "allocated_amount": 300_000},
        headers=headers,
    )

    assert assigned.status_code == 201, assigned.text
    assert assigned.json()["isolated"]["allocated_funding"] == 900_000
    assert assigned.json()["isolated"]["unallocated_funding"] == 100_000
    travel = next(item for item in assigned.json()["category_breakdown"] if item["category"] == "Travel")
    assert travel["allocated_amount"] == 300_000
    assert travel["remaining"] == 300_000

    over_assigned = client.post(
        f"/projects/{project_id}/category-allocations",
        json={"category": "Housing", "allocated_amount": 200_000},
        headers=headers,
    )

    assert over_assigned.status_code == 400
    assert over_assigned.json()["detail"] == "projects.category_allocations_exceed_unassigned_funding"


def test_isolated_project_subcategory_allocation_uses_parent_category_room(client):
    headers = create_user_and_token(
        client,
        "isolatedassignmicro",
        "isolatedassignmicro@example.com",
        "Password123!",
    )
    today = user_timezone_today()
    wallet_id = _wallet_id(client, headers)
    created = client.post(
        "/projects",
        json={
            "title": "Kitchen",
            "is_isolated": True,
            "start_date": today.isoformat(),
            "wallet_allocations": [{"wallet_id": wallet_id, "amount": 1_000_000}],
            "category_allocations": [{"category": "Housing", "limit_amount": 700_000}],
            "subcategory_allocations": [
                {"category": "Housing", "name": "Drywall", "limit_amount": 300_000}
            ],
        },
        headers=headers,
    )
    assert created.status_code == 201, created.text
    project_id = created.json()["id"]

    assigned = client.post(
        f"/projects/{project_id}/subcategory-allocations",
        json={"category": "Housing", "name": "Plumbing", "allocated_amount": 250_000},
        headers=headers,
    )

    assert assigned.status_code == 201, assigned.text
    housing = next(item for item in assigned.json()["category_breakdown"] if item["category"] == "Housing")
    assert [
        {"name": item["name"], "allocated_amount": item["allocated_amount"], "remaining": item["remaining"]}
        for item in housing["subcategories"]
    ] == [
        {"name": "Drywall", "allocated_amount": 300_000, "remaining": 300_000},
        {"name": "Plumbing", "allocated_amount": 250_000, "remaining": 250_000},
    ]

    over_assigned = client.post(
        f"/projects/{project_id}/subcategory-allocations",
        json={"category": "Housing", "name": "Flooring", "allocated_amount": 200_000},
        headers=headers,
    )

    assert over_assigned.status_code == 400
    assert over_assigned.json()["detail"] == "projects.isolated_subcategory_limit_exceeds_category"


def test_isolated_project_category_rebalance_preserves_wallet_funding_and_spent_floor(client):
    headers = create_user_and_token(
        client,
        "isolatedrebalanceparent",
        "isolatedrebalanceparent@example.com",
        "Password123!",
    )
    today = user_timezone_today()
    wallet_id = _wallet_id(client, headers)
    created = client.post(
        "/projects",
        json={
            "title": "Renovation rebalance",
            "is_isolated": True,
            "start_date": today.isoformat(),
            "wallet_allocations": [{"wallet_id": wallet_id, "amount": 1_000_000}],
            "category_allocations": [
                {"category": "Housing", "limit_amount": 500_000},
                {"category": "Travel", "limit_amount": 100_000},
            ],
        },
        headers=headers,
    )
    assert created.status_code == 201, created.text
    project_id = created.json()["id"]

    expense = client.post(
        "/expenses/",
        json={
            "title": "Cabinets",
            "amount": 300_000,
            "category": "Housing",
            "date": today.isoformat(),
            "project_id": project_id,
        },
        headers=headers,
    )
    assert expense.status_code == 201, expense.text

    rebalanced = client.post(
        f"/projects/{project_id}/rebalances",
        json={
            "scope": "CATEGORY",
            "from_category": "Housing",
            "to_category": "Travel",
            "amount": 100_000,
        },
        headers=headers,
    )

    assert rebalanced.status_code == 200, rebalanced.text
    assert rebalanced.json()["isolated"]["funding_limit"] == 1_000_000
    by_category = {item["category"]: item for item in rebalanced.json()["category_breakdown"]}
    assert by_category["Housing"]["allocated_amount"] == 400_000
    assert by_category["Travel"]["allocated_amount"] == 200_000

    below_spent = client.post(
        f"/projects/{project_id}/rebalances",
        json={
            "scope": "CATEGORY",
            "from_category": "Housing",
            "to_category": "Travel",
            "amount": 150_000,
        },
        headers=headers,
    )

    assert below_spent.status_code == 400
    assert below_spent.json()["detail"] == "projects.category_allocation_below_spent"


def test_isolated_project_category_rebalance_cannot_undercut_micro_allocations(client):
    headers = create_user_and_token(
        client,
        "isolatedrebalancemicroguard",
        "isolatedrebalancemicroguard@example.com",
        "Password123!",
    )
    today = user_timezone_today()
    wallet_id = _wallet_id(client, headers)
    created = client.post(
        "/projects",
        json={
            "title": "Micro guarded rebalance",
            "is_isolated": True,
            "start_date": today.isoformat(),
            "wallet_allocations": [{"wallet_id": wallet_id, "amount": 1_000_000}],
            "category_allocations": [
                {"category": "Housing", "limit_amount": 500_000},
                {"category": "Travel", "limit_amount": 100_000},
            ],
            "subcategory_allocations": [
                {"category": "Housing", "name": "Drywall", "limit_amount": 450_000}
            ],
        },
        headers=headers,
    )
    assert created.status_code == 201, created.text

    response = client.post(
        f"/projects/{created.json()['id']}/rebalances",
        json={
            "scope": "CATEGORY",
            "from_category": "Housing",
            "to_category": "Travel",
            "amount": 100_000,
        },
        headers=headers,
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "projects.subcategory_allocations_exceed_category"


def test_isolated_project_expense_cannot_spend_unassigned_project_funding(client):
    headers = create_user_and_token(
        client,
        "isolatedunassignedspend",
        "isolatedunassignedspend@example.com",
        "Password123!",
    )
    today = user_timezone_today()
    wallet_id = _wallet_id(client, headers)
    created = client.post(
        "/projects",
        json={
            "title": "Unassigned stash",
            "is_isolated": True,
            "start_date": today.isoformat(),
            "wallet_allocations": [{"wallet_id": wallet_id, "amount": 1_000_000}],
        },
        headers=headers,
    )
    assert created.status_code == 201, created.text
    assert created.json()["isolated"]["unallocated_funding"] == 1_000_000

    expense = client.post(
        "/expenses/",
        json={
            "title": "Unassigned paint",
            "amount": 100_000,
            "category": "Housing",
            "date": today.isoformat(),
            "project_id": created.json()["id"],
        },
        headers=headers,
    )

    assert expense.status_code == 400
    assert expense.json()["detail"] == {
        "code": "projects.assign_unassigned_funding_required",
        "repair": "ASSIGN_UNASSIGNED_FUNDING",
        "category": "Housing",
    }
