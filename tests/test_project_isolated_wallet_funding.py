from tests.helpers import create_user_and_token, user_timezone_today


def test_isolated_project_creation_derives_funding_from_wallet_allocations(client):
    headers = create_user_and_token(
        client,
        "isolatedwalletfunding",
        "isolatedwalletfunding@example.com",
        "Password123!",
    )
    today = user_timezone_today()

    wallets = client.get("/wallets", headers=headers)
    assert wallets.status_code == 200, wallets.text
    default_wallet_id = wallets.json()[0]["id"]

    credit_wallet = client.post(
        "/wallets",
        json={
            "name": "Prepaid credit",
            "wallet_type": "CREDIT",
            "accounting_type": "LIABILITY",
            "initial_balance": 500_000,
            "credit_limit": 2_000_000,
            "allow_overlimit": False,
            "can_fund_goals": True,
        },
        headers=headers,
    )
    assert credit_wallet.status_code == 201, credit_wallet.text
    credit_wallet_id = credit_wallet.json()["id"]

    response = client.post(
        "/projects",
        json={
            "title": "Wallet-backed renovation",
            "description": "Direct isolated stash",
            "is_isolated": True,
            "start_date": today.isoformat(),
            "target_end_date": today.replace(year=today.year + 1).isoformat(),
            "wallet_allocations": [
                {"wallet_id": default_wallet_id, "amount": 1_500_000},
                {"wallet_id": credit_wallet_id, "amount": 500_000},
            ],
        },
        headers=headers,
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["project_type"] == "ISOLATED"
    assert body["total_limit"] == 2_000_000
    assert body["remaining"] == 2_000_000
    assert body["isolated"]["funding_limit"] == 2_000_000
    assert body["isolated"]["remaining_funding"] == 2_000_000
    assert body["isolated"]["funding_shortfall"] == 0
    assert [
        {"wallet_id": item["wallet_id"], "amount": item["amount"]}
        for item in body["isolated"]["wallet_allocations"]
    ] == [
        {"wallet_id": default_wallet_id, "amount": 1_500_000},
        {"wallet_id": credit_wallet_id, "amount": 500_000},
    ]


def test_isolated_project_wallet_allocations_reduce_free_money_now(client):
    headers = create_user_and_token(
        client,
        "isolatedwalletfreemoney",
        "isolatedwalletfreemoney@example.com",
        "Password123!",
    )
    today = user_timezone_today()

    wallets = client.get("/wallets", headers=headers)
    assert wallets.status_code == 200, wallets.text
    wallet_id = wallets.json()[0]["id"]

    created = client.post(
        "/projects",
        json={
            "title": "Free money lock",
            "is_isolated": True,
            "start_date": today.isoformat(),
            "target_end_date": None,
            "wallet_allocations": [{"wallet_id": wallet_id, "amount": 2_000_000}],
        },
        headers=headers,
    )
    assert created.status_code == 201, created.text

    summary = client.get(
        f"/budgets/month-summary?budget_year={today.year}&budget_month={today.month}",
        headers=headers,
    )
    assert summary.status_code == 200, summary.text
    assert summary.json()["free_money_now"] == 8_000_000

    refreshed_wallets = client.get("/wallets", headers=headers)
    assert refreshed_wallets.status_code == 200, refreshed_wallets.text
    wallet = refreshed_wallets.json()[0]
    assert wallet["owned_balance"] == 10_000_000
    assert wallet["protected_for_projects"] == 2_000_000
    assert wallet["free_to_allocate"] == 8_000_000


def test_isolated_project_rejects_duplicate_wallet_allocations(client):
    headers = create_user_and_token(
        client,
        "isolatedwalletduplicate",
        "isolatedwalletduplicate@example.com",
        "Password123!",
    )
    today = user_timezone_today()

    wallets = client.get("/wallets", headers=headers)
    assert wallets.status_code == 200, wallets.text
    wallet_id = wallets.json()[0]["id"]

    response = client.post(
        "/projects",
        json={
            "title": "Duplicate wallet rows",
            "is_isolated": True,
            "start_date": today.isoformat(),
            "target_end_date": None,
            "wallet_allocations": [
                {"wallet_id": wallet_id, "amount": 100_000},
                {"wallet_id": wallet_id, "amount": 200_000},
            ],
        },
        headers=headers,
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "projects.wallet_allocation_duplicate"


def test_isolated_project_rejects_allocation_above_wallet_free_money(client):
    headers = create_user_and_token(
        client,
        "isolatedwalletover",
        "isolatedwalletover@example.com",
        "Password123!",
    )
    today = user_timezone_today()

    wallets = client.get("/wallets", headers=headers)
    assert wallets.status_code == 200, wallets.text
    wallet_id = wallets.json()[0]["id"]

    response = client.post(
        "/projects",
        json={
            "title": "Too much funding",
            "is_isolated": True,
            "start_date": today.isoformat(),
            "target_end_date": None,
            "wallet_allocations": [{"wallet_id": wallet_id, "amount": 10_000_001}],
        },
        headers=headers,
    )

    assert response.status_code == 400
    detail = response.json()["detail"]
    assert detail["code"] == "projects.wallet_allocation_exceeds_free_money"
    assert detail["wallet_id"] == wallet_id
    assert detail["free_to_allocate"] == 10_000_000


def test_isolated_project_wallet_allocations_are_owner_scoped(client):
    owner_headers = create_user_and_token(
        client,
        "isolatedwalletowner",
        "isolatedwalletowner@example.com",
        "Password123!",
    )
    other_headers = create_user_and_token(
        client,
        "isolatedwalletother",
        "isolatedwalletother@example.com",
        "Password123!",
    )
    today = user_timezone_today()

    other_wallets = client.get("/wallets", headers=other_headers)
    assert other_wallets.status_code == 200, other_wallets.text
    other_wallet_id = other_wallets.json()[0]["id"]

    response = client.post(
        "/projects",
        json={
            "title": "Wrong wallet owner",
            "is_isolated": True,
            "start_date": today.isoformat(),
            "target_end_date": None,
            "wallet_allocations": [{"wallet_id": other_wallet_id, "amount": 100_000}],
        },
        headers=owner_headers,
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "wallets.not_found"


def test_isolated_project_wallet_overallocation_leaves_no_partial_project(client):
    headers = create_user_and_token(
        client,
        "isolatedwalletrollback",
        "isolatedwalletrollback@example.com",
        "Password123!",
    )
    today = user_timezone_today()

    wallets = client.get("/wallets", headers=headers)
    assert wallets.status_code == 200, wallets.text
    wallet_id = wallets.json()[0]["id"]

    response = client.post(
        "/projects",
        json={
            "title": "Rollback funding",
            "is_isolated": True,
            "start_date": today.isoformat(),
            "target_end_date": None,
            "wallet_allocations": [{"wallet_id": wallet_id, "amount": 10_000_001}],
        },
        headers=headers,
    )
    assert response.status_code == 400

    projects = client.get("/projects", headers=headers)
    assert projects.status_code == 200, projects.text
    assert all(project["title"] != "Rollback funding" for project in projects.json())


def test_isolated_project_existing_project_locks_reduce_wallet_free_to_allocate(client):
    headers = create_user_and_token(
        client,
        "isolatedwalletlocks",
        "isolatedwalletlocks@example.com",
        "Password123!",
    )
    today = user_timezone_today()

    wallets = client.get("/wallets", headers=headers)
    assert wallets.status_code == 200, wallets.text
    wallet_id = wallets.json()[0]["id"]

    first_project = client.post(
        "/projects",
        json={
            "title": "First stash",
            "is_isolated": True,
            "start_date": today.isoformat(),
            "target_end_date": None,
            "wallet_allocations": [{"wallet_id": wallet_id, "amount": 9_500_000}],
        },
        headers=headers,
    )
    assert first_project.status_code == 201, first_project.text

    second_project = client.post(
        "/projects",
        json={
            "title": "Second stash",
            "is_isolated": True,
            "start_date": today.isoformat(),
            "target_end_date": None,
            "wallet_allocations": [{"wallet_id": wallet_id, "amount": 600_000}],
        },
        headers=headers,
    )

    assert second_project.status_code == 400
    detail = second_project.json()["detail"]
    assert detail["code"] == "projects.wallet_allocation_exceeds_free_money"
    assert detail["protected_for_projects"] == 9_500_000
    assert detail["free_to_allocate"] == 500_000


def test_wallet_funded_isolated_project_rejects_manual_total_limit_update(client):
    headers = create_user_and_token(
        client,
        "isolatedwallettotalupdate",
        "isolatedwallettotalupdate@example.com",
        "Password123!",
    )
    today = user_timezone_today()

    wallets = client.get("/wallets", headers=headers)
    assert wallets.status_code == 200, wallets.text
    wallet_id = wallets.json()[0]["id"]

    created = client.post(
        "/projects",
        json={
            "title": "Wallet funded total guard",
            "is_isolated": True,
            "start_date": today.isoformat(),
            "target_end_date": None,
            "wallet_allocations": [{"wallet_id": wallet_id, "amount": 1_000_000}],
        },
        headers=headers,
    )
    assert created.status_code == 201, created.text

    response = client.put(
        f"/projects/{created.json()['id']}",
        json={"total_limit": 2_000_000},
        headers=headers,
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "projects.isolated_wallet_funded_total_limit_not_allowed"
