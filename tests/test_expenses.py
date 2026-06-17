from datetime import date, timedelta

import app.routers.expenses as expenses_router
from app import models
from app.redis_rate_limiter import redis_client
from tests.helpers import create_user_and_token, create_budget, create_expense, user_timezone_today


def _feed_expenses(payload):
    return [item["expense"] for item in payload["items"] if item["type"] == "EXPENSE"]


def _make_goal_funding_wallet(client, headers, *, name="Goal Wallet", initial_balance=1_000_000):
    response = client.post(
        "/wallets",
        json={
            "name": name,
            "wallet_type": "SAVINGS",
            "initial_balance": initial_balance,
            "can_fund_goals": True,
        },
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def _make_premium(client, headers):
    response = client.post("/users/me/toggle-premium", headers=headers)
    assert response.status_code == 200, response.text


def _create_allocated_goal(client, headers, wallet_id, *, amount=800_000, intent="RESERVE"):
    created = client.post(
        "/goals/",
        json={
            "title": "Protected Goal",
            "target_amount": amount,
            "intent": intent,
        },
        headers=headers,
    )
    assert created.status_code == 201, created.text
    goal_id = created.json()["id"]

    allocated = client.post(
        f"/goals/{goal_id}/allocations",
        json={"wallet_id": wallet_id, "amount": amount},
        headers=headers,
    )
    assert allocated.status_code == 200, allocated.text
    return goal_id


def test_create_expense_requires_budget(client):
    headers = create_user_and_token(
        client, "expuser", "expuser@example.com", "Password123!"
    )
    res = create_expense(client, headers, category="Food")
    assert res.status_code == 400


def test_create_and_get_expense(client):
    headers = create_user_and_token(
        client, "expuser2", "expuser2@example.com", "Password123!"
    )
    create_budget(client, headers, category="Food", monthly_limit=500)
    res = create_expense(client, headers, title="Burger", amount=12, category="Food")
    assert res.status_code == 201
    assert "X-RateLimit-Limit" in res.headers
    assert "X-RateLimit-Remaining" in res.headers
    assert "X-RateLimit-Reset" in res.headers
    expense_id = res.json()["id"]

    res_get = client.get(f"/expenses/{expense_id}", headers=headers)
    assert res_get.status_code == 200
    assert res_get.json()["title"] == "Burger"


def test_quick_add_single_wallet_allocation_creates_non_session_event(client, session):
    headers = create_user_and_token(
        client, "expwalletsingle", "expwalletsingle@example.com", "Password123!"
    )
    create_budget(client, headers, category="Transport", monthly_limit=500_000)

    user = session.query(models.User).filter(
        models.User.email == "expwalletsingle@example.com"
    ).first()
    wallet = session.query(models.Wallet).filter(
        models.Wallet.owner_id == user.id,
        models.Wallet.is_default == True,
    ).first()

    res = client.post(
        "/expenses/",
        json={
            "title": "Taxi",
            "amount": 100_000,
            "category": "Transport",
            "description": "airport",
            "date": user_timezone_today().isoformat(),
            "wallet_allocations": [
                {"wallet_id": wallet.id, "amount": 100_000},
            ],
        },
        headers=headers,
    )

    assert res.status_code == 201, res.text
    data = res.json()
    assert data["is_session"] is False
    assert data["wallet_id"] == wallet.id
    assert data["wallet_allocations"] == [
        {
            "wallet_id": wallet.id,
            "amount": 100_000,
            "wallet": data["wallet_allocations"][0]["wallet"],
        }
    ]

    session.expire_all()
    event = session.query(models.FinancialEvent).filter(
        models.FinancialEvent.id == data["id"],
    ).first()
    assert event is not None
    assert event.is_session is False
    assert len(event.wallet_legs) == 1
    assert event.wallet_legs[0].wallet_id == wallet.id
    assert event.wallet_legs[0].amount == -100_000
    assert len(event.entity_legs) == 1
    assert event.entity_legs[0].amount == 100_000
    assert event.entity_legs[0].category == models.ExpenseCategory.TRANSPORT

    refreshed_wallet = session.query(models.Wallet).filter(models.Wallet.id == wallet.id).first()
    assert refreshed_wallet.current_balance == 9_900_000


def test_quick_add_multi_wallet_allocation_creates_one_non_session_event(client, session):
    headers = create_user_and_token(
        client, "expwalletmulti", "expwalletmulti@example.com", "Password123!"
    )
    create_budget(client, headers, category="Transport", monthly_limit=500_000)

    user = session.query(models.User).filter(
        models.User.email == "expwalletmulti@example.com"
    ).first()
    default_wallet = session.query(models.Wallet).filter(
        models.Wallet.owner_id == user.id,
        models.Wallet.is_default == True,
    ).first()
    second_wallet = models.Wallet(
        owner_id=user.id,
        name="Cash Pocket",
        wallet_type=models.WalletType.CASH,
        accounting_type=models.AccountingType.ASSET,
        initial_balance=500_000,
        current_balance=500_000,
        is_default=False,
    )
    session.add(second_wallet)
    session.commit()
    session.refresh(second_wallet)

    res = client.post(
        "/expenses/",
        json={
            "title": "Taxi",
            "amount": 100_000,
            "category": "Transport",
            "description": "split paid",
            "date": user_timezone_today().isoformat(),
            "wallet_allocations": [
                {"wallet_id": default_wallet.id, "amount": 60_000},
                {"wallet_id": second_wallet.id, "amount": 40_000},
            ],
        },
        headers=headers,
    )

    assert res.status_code == 201, res.text
    data = res.json()
    assert data["is_session"] is False
    assert data["wallet_id"] is None
    assert sorted(
        (item["wallet_id"], item["amount"]) for item in data["wallet_allocations"]
    ) == [
        (default_wallet.id, 60_000),
        (second_wallet.id, 40_000),
    ]

    session.expire_all()
    event = session.query(models.FinancialEvent).filter(
        models.FinancialEvent.id == data["id"],
    ).first()
    assert event is not None
    assert event.is_session is False
    assert len(event.entity_legs) == 1
    assert event.entity_legs[0].amount == 100_000
    assert sorted((leg.wallet_id, leg.amount) for leg in event.wallet_legs) == [
        (default_wallet.id, -60_000),
        (second_wallet.id, -40_000),
    ]

    draft_count = session.query(models.ExpenseSessionDraft).filter(
        models.ExpenseSessionDraft.owner_id == user.id,
    ).count()
    assert draft_count == 0

    refreshed_default = session.query(models.Wallet).filter(models.Wallet.id == default_wallet.id).first()
    refreshed_second = session.query(models.Wallet).filter(models.Wallet.id == second_wallet.id).first()
    assert refreshed_default.current_balance == 9_940_000
    assert refreshed_second.current_balance == 460_000


def test_quick_add_wallet_allocations_reject_total_mismatch(client, session):
    headers = create_user_and_token(
        client, "expwalletmismatch", "expwalletmismatch@example.com", "Password123!"
    )
    create_budget(client, headers, category="Transport", monthly_limit=500_000)

    user = session.query(models.User).filter(
        models.User.email == "expwalletmismatch@example.com"
    ).first()
    wallet = session.query(models.Wallet).filter(
        models.Wallet.owner_id == user.id,
        models.Wallet.is_default == True,
    ).first()

    res = client.post(
        "/expenses/",
        json={
            "title": "Taxi",
            "amount": 100_000,
            "category": "Transport",
            "description": "bad allocation",
            "date": user_timezone_today().isoformat(),
            "wallet_allocations": [
                {"wallet_id": wallet.id, "amount": 90_000},
            ],
        },
        headers=headers,
    )

    assert res.status_code == 400
    assert res.json()["detail"] == "expenses.wallet_allocation_total_mismatch"


def test_quick_add_wallet_allocations_reject_duplicate_wallets(client, session):
    headers = create_user_and_token(
        client, "expwalletduplicate", "expwalletduplicate@example.com", "Password123!"
    )
    create_budget(client, headers, category="Transport", monthly_limit=500_000)

    user = session.query(models.User).filter(
        models.User.email == "expwalletduplicate@example.com"
    ).first()
    wallet = session.query(models.Wallet).filter(
        models.Wallet.owner_id == user.id,
        models.Wallet.is_default == True,
    ).first()

    res = client.post(
        "/expenses/",
        json={
            "title": "Taxi",
            "amount": 100_000,
            "category": "Transport",
            "description": "duplicate allocation",
            "date": user_timezone_today().isoformat(),
            "wallet_allocations": [
                {"wallet_id": wallet.id, "amount": 60_000},
                {"wallet_id": wallet.id, "amount": 40_000},
            ],
        },
        headers=headers,
    )

    assert res.status_code == 400
    assert res.json()["detail"] == "expenses.wallet_allocation_duplicate"


def test_quick_add_blocks_spending_goal_protected_money(client, session):
    headers = create_user_and_token(
        client, "expgoalprotected", "expgoalprotected@example.com", "Password123!"
    )
    _make_premium(client, headers)
    wallet_id = _make_goal_funding_wallet(client, headers, initial_balance=1_000_000)
    _create_allocated_goal(client, headers, wallet_id, amount=800_000)
    create_budget(client, headers, category="Electronics", monthly_limit=5_000_000)

    blocked = client.post(
        "/expenses/",
        json={
            "title": "Headphones",
            "amount": 300_000,
            "category": "Electronics",
            "description": "normal spending",
            "date": user_timezone_today().isoformat(),
            "wallet_allocations": [{"wallet_id": wallet_id, "amount": 300_000}],
        },
        headers=headers,
    )

    assert blocked.status_code == 400
    detail = blocked.json()["detail"]
    assert detail["code"] == "expenses.goal_protection_conflict"
    assert detail["wallet_id"] == wallet_id
    assert detail["protected_for_goals"] == 800_000
    assert detail["free_to_spend"] == 200_000
    assert detail["requested_amount"] == 300_000
    assert detail["protected_amount_touched"] == 100_000

    session.expire_all()
    wallet = session.query(models.Wallet).filter(models.Wallet.id == wallet_id).first()
    assert wallet.current_balance == 1_000_000

    allowed = client.post(
        "/expenses/",
        json={
            "title": "Case",
            "amount": 200_000,
            "category": "Electronics",
            "description": "free money only",
            "date": user_timezone_today().isoformat(),
            "wallet_allocations": [{"wallet_id": wallet_id, "amount": 200_000}],
        },
        headers=headers,
    )
    assert allowed.status_code == 201, allowed.text

    session.expire_all()
    wallet = session.query(models.Wallet).filter(models.Wallet.id == wallet_id).first()
    assert wallet.current_balance == 800_000


def test_session_finalize_blocks_spending_goal_protected_money(client, session):
    headers = create_user_and_token(
        client, "expsessionprotected", "expsessionprotected@example.com", "Password123!"
    )
    _make_premium(client, headers)
    wallet_id = _make_goal_funding_wallet(client, headers, initial_balance=1_000_000)
    _create_allocated_goal(client, headers, wallet_id, amount=800_000)
    create_budget(client, headers, category="Groceries", monthly_limit=5_000_000)

    draft = client.post(
        "/expenses/session-drafts",
        json={
            "title": "Market receipt",
            "date": user_timezone_today().isoformat(),
            "amount_paid": 300_000,
        },
        headers=headers,
    )
    assert draft.status_code == 201, draft.text
    draft_id = draft.json()["id"]

    item = client.post(
        f"/expenses/session-drafts/{draft_id}/items",
        json={
            "label": "Groceries",
            "original_amount": 300_000,
            "category": "Groceries",
        },
        headers=headers,
    )
    assert item.status_code == 201, item.text

    wallet_allocation = client.post(
        f"/expenses/session-drafts/{draft_id}/wallet-allocations",
        json={"wallet_id": wallet_id, "amount": 300_000},
        headers=headers,
    )
    assert wallet_allocation.status_code == 201, wallet_allocation.text

    blocked = client.post(f"/expenses/session-drafts/{draft_id}/finalize", headers=headers)

    assert blocked.status_code == 400
    detail = blocked.json()["detail"]
    assert detail["code"] == "expenses.goal_protection_conflict"
    assert detail["outflow_type"] == "session_expense"
    assert detail["protected_for_goals"] == 800_000
    assert detail["free_to_spend"] == 200_000
    assert detail["protected_amount_touched"] == 100_000

    session.expire_all()
    wallet = session.query(models.Wallet).filter(models.Wallet.id == wallet_id).first()
    assert wallet.current_balance == 1_000_000


def test_project_expense_tagging_uses_expense_date_not_current_date(client):
    headers = create_user_and_token(
        client, "expprojectdates", "expprojectdates@example.com", "Password123!"
    )
    project = client.post(
        "/projects",
        json={
            "title": "Conference",
            "is_isolated": True,
            "total_limit": 1_000_000,
            "start_date": "2026-06-01",
            "target_end_date": "2026-06-10",
        },
        headers=headers,
    )
    assert project.status_code == 201, project.text
    project_id = project.json()["id"]

    accepted_late_entry = client.post(
        "/expenses/",
        json={
            "title": "Venue bill",
            "amount": 100_000,
            "category": "Family & Events",
            "date": "2026-06-10",
            "project_id": project_id,
        },
        headers=headers,
    )
    assert accepted_late_entry.status_code == 201, accepted_late_entry.text
    assert accepted_late_entry.json()["project_id"] == project_id

    outside_window = client.post(
        "/expenses/",
        json={
            "title": "Late taxi",
            "amount": 50_000,
            "category": "Transport",
            "date": "2026-06-11",
            "project_id": project_id,
        },
        headers=headers,
    )
    assert outside_window.status_code == 400
    assert outside_window.json()["detail"] == "projects.expense_after_end"


def test_project_date_update_allows_expansion_and_blocks_orphaning_tagged_expenses(client):
    headers = create_user_and_token(
        client, "expprojectshrink", "expprojectshrink@example.com", "Password123!"
    )
    project = client.post(
        "/projects",
        json={
            "title": "Renovation",
            "is_isolated": True,
            "total_limit": 1_000_000,
            "start_date": "2026-06-01",
            "target_end_date": "2026-06-30",
        },
        headers=headers,
    )
    assert project.status_code == 201, project.text
    project_id = project.json()["id"]

    expense = client.post(
        "/expenses/",
        json={
            "title": "Paint run",
            "amount": 100_000,
            "category": "Housing",
            "date": "2026-06-10",
            "project_id": project_id,
        },
        headers=headers,
    )
    assert expense.status_code == 201, expense.text

    expanded = client.put(
        f"/projects/{project_id}",
        json={
            "start_date": "2026-05-15",
            "target_end_date": "2026-07-15",
        },
        headers=headers,
    )
    assert expanded.status_code == 200, expanded.text
    assert expanded.json()["start_date"] == "2026-05-15"
    assert expanded.json()["target_end_date"] == "2026-07-15"

    start_shrink = client.put(
        f"/projects/{project_id}",
        json={"start_date": "2026-06-11"},
        headers=headers,
    )
    assert start_shrink.status_code == 400
    assert start_shrink.json()["detail"] == "projects.start_after_linked_expense"

    end_shrink = client.put(
        f"/projects/{project_id}",
        json={"target_end_date": "2026-06-09"},
        headers=headers,
    )
    assert end_shrink.status_code == 400
    assert end_shrink.json()["detail"] == "projects.end_before_linked_expense"


def test_completed_project_rejects_edits_and_expense_tagging_until_reopen(client):
    headers = create_user_and_token(
        client, "expprojectlocked", "expprojectlocked@example.com", "Password123!"
    )
    project = client.post(
        "/projects",
        json={
            "title": "Wedding",
            "is_isolated": True,
            "total_limit": 1_000_000,
            "start_date": "2026-06-01",
            "target_end_date": "2026-06-30",
        },
        headers=headers,
    )
    assert project.status_code == 201, project.text
    project_id = project.json()["id"]

    category_limit = client.post(
        f"/projects/{project_id}/category-limits",
        json={"category": "Family & Events", "limit_amount": 800_000},
        headers=headers,
    )
    assert category_limit.status_code == 201, category_limit.text
    subcategory = client.post(
        f"/projects/{project_id}/subcategories",
        json={"category": "Family & Events", "name": "Venue", "limit_amount": 500_000},
        headers=headers,
    )
    assert subcategory.status_code == 201, subcategory.text
    subcategory_id = subcategory.json()["category_breakdown"][0]["subcategories"][0]["id"]

    completed = client.post(
        f"/projects/{project_id}/complete",
        json={"effective_date": "2026-06-30"},
        headers=headers,
    )
    assert completed.status_code == 200, completed.text
    assert completed.json()["status"] == "COMPLETED"

    metadata_edit = client.put(
        f"/projects/{project_id}",
        json={"title": "Wedding final"},
        headers=headers,
    )
    assert metadata_edit.status_code == 400
    assert metadata_edit.json()["detail"] == "projects.completed_read_only"

    limit_edit = client.put(
        f"/projects/{project_id}/category-limits/Family%20%26%20Events",
        json={"limit_amount": 900_000},
        headers=headers,
    )
    assert limit_edit.status_code == 400
    assert limit_edit.json()["detail"] == "projects.completed_read_only"

    subcategory_edit = client.put(
        f"/projects/{project_id}/subcategories/{subcategory_id}",
        json={"name": "Venue final"},
        headers=headers,
    )
    assert subcategory_edit.status_code == 400
    assert subcategory_edit.json()["detail"] == "projects.completed_read_only"

    tagged_expense = client.post(
        "/expenses/",
        json={
            "title": "Late venue receipt",
            "amount": 100_000,
            "category": "Family & Events",
            "date": "2026-06-10",
            "project_id": project_id,
            "project_subcategory_id": subcategory_id,
        },
        headers=headers,
    )
    assert tagged_expense.status_code == 400
    assert tagged_expense.json()["detail"] == "projects.not_active"

    reopened = client.post(f"/projects/{project_id}/reopen", headers=headers)
    assert reopened.status_code == 200, reopened.text
    assert reopened.json()["status"] == "ACTIVE"

    after_reopen = client.put(
        f"/projects/{project_id}",
        json={"title": "Wedding final", "target_end_date": "2026-06-14"},
        headers=headers,
    )
    assert after_reopen.status_code == 200, after_reopen.text
    assert after_reopen.json()["title"] == "Wedding final"
    assert after_reopen.json()["target_end_date"] == "2026-06-14"

    accepted_expense = client.post(
        "/expenses/",
        json={
            "title": "Late venue receipt",
            "amount": 100_000,
            "category": "Family & Events",
            "date": "2026-06-10",
            "project_id": project_id,
            "project_subcategory_id": subcategory_id,
        },
        headers=headers,
    )
    assert accepted_expense.status_code == 201, accepted_expense.text
    assert accepted_expense.json()["project_id"] == project_id

    recompleted = client.post(
        f"/projects/{project_id}/complete",
        json={"effective_date": "2026-06-14"},
        headers=headers,
    )
    assert recompleted.status_code == 200, recompleted.text
    assert recompleted.json()["status"] == "COMPLETED"
    assert recompleted.json()["title"] == "Wedding final"
    assert recompleted.json()["target_end_date"] == "2026-06-14"


def test_split_expense_supports_cross_category_allocations_and_preserves_wallet_legs(client, session):
    headers = create_user_and_token(
        client, "expsplitcross", "expsplitcross@example.com", "Password123!"
    )
    create_budget(client, headers, category="Groceries", monthly_limit=1_000_000)
    create_budget(client, headers, category="Animals & Pets", monthly_limit=1_000_000)

    created = create_expense(client, headers, title="Korzinka", amount=500_000, category="Groceries")
    assert created.status_code == 201, created.text
    expense_id = created.json()["id"]

    split = client.post(
        f"/expenses/{expense_id}/split",
        json={
            "items": [
                {"label": "Groceries", "amount": 300_000, "category": "Groceries"},
                {"label": "Pet food", "amount": 200_000, "category": "Animals & Pets"},
            ]
        },
        headers=headers,
    )
    assert split.status_code == 200, split.text
    data = split.json()
    assert data["amount"] == 500_000
    assert data["is_split"] is True
    assert sorted((item["label"], item["amount"], item["category"]) for item in data["split_items"]) == [
        ("Groceries", 300_000, "Groceries"),
        ("Pet food", 200_000, "Animals & Pets"),
    ]

    session.expire_all()
    event = session.query(models.FinancialEvent).filter(models.FinancialEvent.id == expense_id).first()
    assert event is not None
    assert [(leg.wallet_id, leg.amount) for leg in event.wallet_legs] == [(created.json()["wallet_id"], -500_000)]
    assert sorted((leg.label, int(leg.amount), leg.category.value, leg.budget.category.value) for leg in event.entity_legs) == [
        ("Groceries", 300_000, "Groceries", "Groceries"),
        ("Pet food", 200_000, "Animals & Pets", "Animals & Pets"),
    ]

    groups = client.get("/expenses/?view=groups", headers=headers)
    assert groups.status_code == 200
    assert groups.json()["items"] == []


def test_split_expense_multi_wallet_parent_keeps_wallet_allocation_separate(client, session):
    headers = create_user_and_token(
        client, "expsplitmultiwallet", "expsplitmultiwallet@example.com", "Password123!"
    )
    create_budget(client, headers, category="Groceries", monthly_limit=1_000_000)
    create_budget(client, headers, category="Utilities", monthly_limit=1_000_000)

    user = session.query(models.User).filter(
        models.User.email == "expsplitmultiwallet@example.com"
    ).first()
    default_wallet = session.query(models.Wallet).filter(
        models.Wallet.owner_id == user.id,
        models.Wallet.is_default == True,
    ).first()
    second_wallet = models.Wallet(
        owner_id=user.id,
        name="Card 2",
        wallet_type=models.WalletType.DEBIT,
        accounting_type=models.AccountingType.ASSET,
        initial_balance=500_000,
        current_balance=500_000,
        is_default=False,
    )
    session.add(second_wallet)
    session.commit()
    session.refresh(second_wallet)

    created = client.post(
        "/expenses/",
        json={
            "title": "Market",
            "amount": 500_000,
            "category": "Groceries",
            "description": "mixed basket",
            "date": user_timezone_today().isoformat(),
            "wallet_allocations": [
                {"wallet_id": default_wallet.id, "amount": 250_000},
                {"wallet_id": second_wallet.id, "amount": 250_000},
            ],
        },
        headers=headers,
    )
    assert created.status_code == 201, created.text
    expense_id = created.json()["id"]

    split = client.post(
        f"/expenses/{expense_id}/split",
        json={
            "items": [
                {"label": "Food", "amount": 350_000, "category": "Groceries"},
                {"label": "Cleaning", "amount": 150_000, "category": "Utilities"},
            ]
        },
        headers=headers,
    )
    assert split.status_code == 200, split.text

    session.expire_all()
    event = session.query(models.FinancialEvent).filter(models.FinancialEvent.id == expense_id).first()
    assert sorted((leg.wallet_id, leg.amount) for leg in event.wallet_legs) == [
        (default_wallet.id, -250_000),
        (second_wallet.id, -250_000),
    ]
    assert sorted((leg.label, int(leg.amount), leg.category.value) for leg in event.entity_legs) == [
        ("Cleaning", 150_000, "Utilities"),
        ("Food", 350_000, "Groceries"),
    ]


def test_split_expense_rejects_total_mismatch_and_already_split_parent(client):
    headers = create_user_and_token(
        client, "expsplitlocks", "expsplitlocks@example.com", "Password123!"
    )
    create_budget(client, headers, category="Groceries", monthly_limit=1_000_000)

    created = create_expense(client, headers, title="Market", amount=500_000, category="Groceries")
    assert created.status_code == 201, created.text
    expense_id = created.json()["id"]

    mismatch = client.post(
        f"/expenses/{expense_id}/split",
        json={
            "items": [
                {"label": "Food", "amount": 300_000, "category": "Groceries"},
                {"label": "Other", "amount": 100_000, "category": "Groceries"},
            ]
        },
        headers=headers,
    )
    assert mismatch.status_code == 400
    assert mismatch.json()["detail"] == "expenses.split_total_mismatch"

    first_split = client.post(
        f"/expenses/{expense_id}/split",
        json={
            "items": [
                {"label": "Food", "amount": 300_000, "category": "Groceries"},
                {"label": "Other", "amount": 200_000, "category": "Groceries"},
            ]
        },
        headers=headers,
    )
    assert first_split.status_code == 200, first_split.text

    second_split = client.post(
        f"/expenses/{expense_id}/split",
        json={
            "items": [
                {"label": "Again 1", "amount": 250_000, "category": "Groceries"},
                {"label": "Again 2", "amount": 250_000, "category": "Groceries"},
            ]
        },
        headers=headers,
    )
    assert second_split.status_code == 400
    assert second_split.json()["detail"] == "expenses.split_parent_locked"


def test_split_parent_blocks_unsafe_actions_but_can_merge_and_void(client, session):
    headers = create_user_and_token(
        client, "expsplitactions", "expsplitactions@example.com", "Password123!"
    )
    create_budget(client, headers, category="Groceries", monthly_limit=1_000_000)

    created = create_expense(client, headers, title="Market", amount=500_000, category="Groceries")
    other = create_expense(client, headers, title="Another Market", amount=100_000, category="Groceries")
    assert created.status_code == 201, created.text
    assert other.status_code == 201, other.text
    expense_id = created.json()["id"]

    split = client.post(
        f"/expenses/{expense_id}/split",
        json={
            "items": [
                {"label": "Food", "amount": 300_000, "category": "Groceries"},
                {"label": "Other", "amount": 200_000, "category": "Groceries"},
            ]
        },
        headers=headers,
    )
    assert split.status_code == 200, split.text

    refund = client.post(f"/expenses/{expense_id}/refund", json={"amount": 100_000}, headers=headers)
    assert refund.status_code == 400
    assert refund.json()["detail"] == "expenses.complex_event_not_supported"

    asset = client.post(f"/expenses/{expense_id}/mark-as-asset", json={}, headers=headers)
    assert asset.status_code == 400
    assert asset.json()["detail"] == "expenses.split_parent_locked"

    user = session.query(models.User).filter(models.User.email == "expsplitactions@example.com").first()
    user.is_premium = True
    session.commit()
    recurring = client.post(
        f"/expenses/{expense_id}/mark-as-recurring",
        json={
            "frequency": "MONTHLY",
            "start_date": user_timezone_today().isoformat(),
            "wallet_id": created.json()["wallet_id"],
        },
        headers=headers,
    )
    assert recurring.status_code == 400
    assert recurring.json()["detail"] == "expenses.split_parent_locked"

    merge = client.post(
        "/expenses/merge-groups",
        json={"title": "Shopping folder", "expense_ids": [expense_id, other.json()["id"]]},
        headers=headers,
    )
    assert merge.status_code == 201, merge.text

    deleted = client.delete(f"/expenses/{expense_id}", headers=headers)
    assert deleted.status_code == 204

    session.expire_all()
    event = session.query(models.FinancialEvent).filter(models.FinancialEvent.id == expense_id).first()
    assert event.status == models.FinancialEventStatus.VOIDED
    reversal = session.query(models.FinancialEvent).filter(
        models.FinancialEvent.id == event.void_reversal_event_id,
    ).first()
    assert reversal.status == models.FinancialEventStatus.REVERSAL
    assert sorted((leg.label, int(leg.amount)) for leg in reversal.entity_legs) == [
        ("Food", -300_000),
        ("Other", -200_000),
    ]


def test_one_wallet_quick_add_can_be_marked_as_asset(client, session):
    headers = create_user_and_token(
        client, "expassetone", "expassetone@example.com", "Password123!"
    )
    create_budget(client, headers, category="Electronics", monthly_limit=5_000_000)
    created = create_expense(
        client,
        headers,
        title="Laptop",
        amount=3_000_000,
        category="Electronics",
    )
    assert created.status_code == 201, created.text
    expense_id = created.json()["id"]

    asset = client.post(
        f"/expenses/{expense_id}/mark-as-asset",
        json={"title": "Work laptop", "current_value": 2_800_000},
        headers=headers,
    )

    assert asset.status_code == 201, asset.text
    data = asset.json()
    assert data["origin_event_id"] == expense_id
    assert data["title"] == "Work laptop"
    assert data["purchase_value"] == 3_000_000
    assert data["current_value"] == 2_800_000

    session.expire_all()
    stored = session.query(models.Asset).filter(models.Asset.origin_event_id == expense_id).first()
    assert stored is not None
    assert stored.purchase_value == 3_000_000


def test_multi_wallet_quick_add_can_be_marked_as_asset(client, session):
    headers = create_user_and_token(
        client, "expassetmulti", "expassetmulti@example.com", "Password123!"
    )
    create_budget(client, headers, category="Electronics", monthly_limit=5_000_000)

    user = session.query(models.User).filter(models.User.email == "expassetmulti@example.com").first()
    default_wallet = session.query(models.Wallet).filter(
        models.Wallet.owner_id == user.id,
        models.Wallet.is_default == True,
    ).first()
    second_wallet = models.Wallet(
        owner_id=user.id,
        name="Card",
        wallet_type=models.WalletType.DEBIT,
        accounting_type=models.AccountingType.ASSET,
        initial_balance=2_000_000,
        current_balance=2_000_000,
        is_default=False,
    )
    session.add(second_wallet)
    session.commit()
    session.refresh(second_wallet)

    created = client.post(
        "/expenses/",
        json={
            "title": "Phone",
            "amount": 2_500_000,
            "category": "Electronics",
            "date": user_timezone_today().isoformat(),
            "wallet_allocations": [
                {"wallet_id": default_wallet.id, "amount": 1_500_000},
                {"wallet_id": second_wallet.id, "amount": 1_000_000},
            ],
        },
        headers=headers,
    )
    assert created.status_code == 201, created.text
    expense_id = created.json()["id"]

    asset = client.post(
        f"/expenses/{expense_id}/mark-as-asset",
        json={},
        headers=headers,
    )

    assert asset.status_code == 201, asset.text
    data = asset.json()
    assert data["origin_event_id"] == expense_id
    assert data["purchase_value"] == 2_500_000
    assert data["current_value"] == 2_500_000

    session.expire_all()
    event = session.query(models.FinancialEvent).filter(models.FinancialEvent.id == expense_id).first()
    assert sorted((leg.wallet_id, leg.amount) for leg in event.wallet_legs) == [
        (default_wallet.id, -1_500_000),
        (second_wallet.id, -1_000_000),
    ]


def test_refunded_expense_cannot_be_marked_as_asset(client):
    headers = create_user_and_token(
        client, "expassetrefunded", "expassetrefunded@example.com", "Password123!"
    )
    create_budget(client, headers, category="Electronics", monthly_limit=5_000_000)
    created = create_expense(
        client,
        headers,
        title="Laptop overcharge",
        amount=1_200_000,
        category="Electronics",
    )
    assert created.status_code == 201, created.text
    expense_id = created.json()["id"]

    refund = client.post(
        f"/expenses/{expense_id}/refund",
        json={"amount": 200_000},
        headers=headers,
    )
    assert refund.status_code == 201, refund.text

    asset = client.post(
        f"/expenses/{expense_id}/mark-as-asset",
        json={"title": "Laptop"},
        headers=headers,
    )

    assert asset.status_code == 400
    assert asset.json()["detail"] == "expenses.has_refund_lock"


def test_asset_linked_expense_blocks_refund_and_delete(client):
    headers = create_user_and_token(
        client, "expassetlocks", "expassetlocks@example.com", "Password123!"
    )
    create_budget(client, headers, category="Electronics", monthly_limit=5_000_000)
    created = create_expense(
        client,
        headers,
        title="Camera",
        amount=1_000_000,
        category="Electronics",
    )
    assert created.status_code == 201, created.text
    expense_id = created.json()["id"]

    asset = client.post(f"/expenses/{expense_id}/mark-as-asset", json={}, headers=headers)
    assert asset.status_code == 201, asset.text

    refund = client.post(
        f"/expenses/{expense_id}/refund",
        json={"amount": 100_000},
        headers=headers,
    )
    assert refund.status_code == 400
    assert refund.json()["detail"] == "expenses.asset_link_lock"

    deleted = client.delete(f"/expenses/{expense_id}", headers=headers)
    assert deleted.status_code == 400
    assert deleted.json()["detail"] == "expenses.asset_link_lock"


def test_direct_asset_creation_rejects_refunded_origin_event(client):
    headers = create_user_and_token(
        client, "expassetdirectrefund", "expassetdirectrefund@example.com", "Password123!"
    )
    create_budget(client, headers, category="Electronics", monthly_limit=5_000_000)
    created = create_expense(
        client,
        headers,
        title="Phone overcharge",
        amount=1_500_000,
        category="Electronics",
    )
    assert created.status_code == 201, created.text
    expense_id = created.json()["id"]
    refund = client.post(
        f"/expenses/{expense_id}/refund",
        json={"amount": 100_000},
        headers=headers,
    )
    assert refund.status_code == 201, refund.text

    asset = client.post(
        "/assets",
        json={
            "title": "Phone",
            "purchase_value": 1_400_000,
            "current_value": 1_400_000,
            "status": "owned",
            "origin_event_id": expense_id,
        },
        headers=headers,
    )

    assert asset.status_code == 400
    assert asset.json()["detail"] == "expenses.has_refund_lock"


def test_direct_asset_creation_rejects_split_origin_event(client):
    headers = create_user_and_token(
        client, "expassetdirectsplit", "expassetdirectsplit@example.com", "Password123!"
    )
    create_budget(client, headers, category="Groceries", monthly_limit=5_000_000)
    created = create_expense(
        client,
        headers,
        title="Korzinka",
        amount=500_000,
        category="Groceries",
    )
    assert created.status_code == 201, created.text
    expense_id = created.json()["id"]
    split = client.post(
        f"/expenses/{expense_id}/split",
        json={
            "items": [
                {"label": "Food", "amount": 300_000, "category": "Groceries"},
                {"label": "Cleaning", "amount": 200_000, "category": "Groceries"},
            ]
        },
        headers=headers,
    )
    assert split.status_code == 200, split.text

    asset = client.post(
        "/assets",
        json={
            "title": "Korzinka item",
            "purchase_value": 500_000,
            "current_value": 500_000,
            "status": "owned",
            "origin_event_id": expense_id,
        },
        headers=headers,
    )

    assert asset.status_code == 400
    assert asset.json()["detail"] == "expenses.split_parent_locked"


def test_split_expense_can_add_subcategories_when_parent_had_none(client, session):
    headers = create_user_and_token(
        client, "expsplitsubcatadd", "expsplitsubcatadd@example.com", "Password123!"
    )
    budget = create_budget(client, headers, category="Groceries", monthly_limit=1_000_000)
    assert budget.status_code == 201, budget.text
    budget_id = budget.json()["id"]
    food_subcat = client.post(
        f"/budgets/{budget_id}/subcategories",
        json={"category": "Groceries", "name": "Food", "monthly_limit": 700_000},
        headers=headers,
    )
    home_subcat = client.post(
        f"/budgets/{budget_id}/subcategories",
        json={"category": "Groceries", "name": "Home supplies", "monthly_limit": 300_000},
        headers=headers,
    )
    assert food_subcat.status_code == 201, food_subcat.text
    assert home_subcat.status_code == 201, home_subcat.text

    created = create_expense(client, headers, title="Korzinka", amount=500_000, category="Groceries")
    assert created.status_code == 201, created.text
    expense_id = created.json()["id"]
    assert created.json()["subcategory_id"] is None

    split = client.post(
        f"/expenses/{expense_id}/split",
        json={
            "items": [
                {
                    "label": "Food",
                    "amount": 300_000,
                    "category": "Groceries",
                    "subcategory_id": food_subcat.json()["id"],
                },
                {
                    "label": "Home",
                    "amount": 200_000,
                    "category": "Groceries",
                    "subcategory_id": home_subcat.json()["id"],
                },
            ]
        },
        headers=headers,
    )
    assert split.status_code == 200, split.text
    assert sorted(item["subcategory_id"] for item in split.json()["split_items"]) == sorted([
        food_subcat.json()["id"],
        home_subcat.json()["id"],
    ])

    session.expire_all()
    event = session.query(models.FinancialEvent).filter(models.FinancialEvent.id == expense_id).first()
    assert len(event.entity_legs) == 2
    assert sorted(leg.subcategory_id for leg in event.entity_legs) == sorted([
        food_subcat.json()["id"],
        home_subcat.json()["id"],
    ])


def test_split_expense_can_clear_parent_subcategory(client, session):
    headers = create_user_and_token(
        client, "expsplitsubcatclear", "expsplitsubcatclear@example.com", "Password123!"
    )
    budget = create_budget(client, headers, category="Groceries", monthly_limit=1_000_000)
    assert budget.status_code == 201, budget.text
    subcat = client.post(
        f"/budgets/{budget.json()['id']}/subcategories",
        json={"category": "Groceries", "name": "Food", "monthly_limit": 1_000_000},
        headers=headers,
    )
    assert subcat.status_code == 201, subcat.text

    created = client.post(
        "/expenses/",
        json={
            "title": "Korzinka",
            "amount": 500_000,
            "category": "Groceries",
            "subcategory_id": subcat.json()["id"],
            "description": "rough category",
            "date": user_timezone_today().isoformat(),
        },
        headers=headers,
    )
    assert created.status_code == 201, created.text
    expense_id = created.json()["id"]
    assert created.json()["subcategory_id"] == subcat.json()["id"]

    split = client.post(
        f"/expenses/{expense_id}/split",
        json={
            "items": [
                {"label": "Bread", "amount": 200_000, "category": "Groceries"},
                {"label": "Other groceries", "amount": 300_000, "category": "Groceries"},
            ]
        },
        headers=headers,
    )
    assert split.status_code == 200, split.text
    assert all(item["subcategory_id"] is None for item in split.json()["split_items"])

    session.expire_all()
    event = session.query(models.FinancialEvent).filter(models.FinancialEvent.id == expense_id).first()
    assert len(event.entity_legs) == 2
    assert all(leg.subcategory_id is None for leg in event.entity_legs)


def test_list_expenses(client):
    headers = create_user_and_token(
        client, "expuser3", "expuser3@example.com", "Password123!"
    )
    create_budget(client, headers, category="Food", monthly_limit=500)
    create_expense(client, headers, title="Item A", amount=5, category="Food")
    create_expense(client, headers, title="Item B", amount=7, category="Food")
    res = client.get("/expenses/", headers=headers)
    assert res.status_code == 200
    assert len(_feed_expenses(res.json())) == 2


def test_list_expenses_folds_merge_groups_as_feed_folders(client):
    headers = create_user_and_token(
        client, "expmergefeed", "expmergefeed@example.com", "Password123!"
    )
    create_budget(client, headers, category="Utilities", monthly_limit=2_000_000)
    electricity = create_expense(client, headers, title="Electricity", amount=400_000, category="Utilities")
    internet = create_expense(client, headers, title="Internet", amount=500_000, category="Utilities")
    water = create_expense(client, headers, title="Water", amount=300_000, category="Utilities")

    merge = client.post(
        "/expenses/merge-groups",
        json={
            "title": "May Utilities",
            "expense_ids": [electricity.json()["id"], internet.json()["id"], water.json()["id"]],
        },
        headers=headers,
    )
    assert merge.status_code == 201, merge.text

    res = client.get("/expenses/?view=all", headers=headers)
    assert res.status_code == 200
    items = res.json()["items"]
    assert len(items) == 1
    assert items[0]["type"] == "MERGE_GROUP"
    assert items[0]["merge_group"]["title"] == "May Utilities"
    assert items[0]["merge_group"]["total_amount"] == 1_200_000
    assert items[0]["merge_group"]["child_count"] == 3
    assert [child["title"] for child in items[0]["merge_group"]["items"]] == ["Electricity", "Internet", "Water"]


def test_list_expenses_feed_views_filter_quick_sessions_groups_and_refunds(client):
    headers = create_user_and_token(
        client, "expfeedviews", "expfeedviews@example.com", "Password123!"
    )
    create_budget(client, headers, category="Food", monthly_limit=1_000_000)
    create_budget(client, headers, category="Utilities", monthly_limit=2_000_000)

    quick = create_expense(client, headers, title="Coffee", amount=10_000, category="Food")
    electricity = create_expense(client, headers, title="Electricity", amount=400_000, category="Utilities")
    internet = create_expense(client, headers, title="Internet", amount=500_000, category="Utilities")
    merge = client.post(
        "/expenses/merge-groups",
        json={"title": "May Utilities", "expense_ids": [electricity.json()["id"], internet.json()["id"]]},
        headers=headers,
    )
    assert merge.status_code == 201, merge.text
    refund = client.post(f"/expenses/{quick.json()['id']}/refund", json={"amount": 5_000}, headers=headers)
    assert refund.status_code == 201, refund.text

    quick_res = client.get("/expenses/?view=quick", headers=headers)
    assert quick_res.status_code == 200
    assert [item["expense"]["title"] for item in quick_res.json()["items"]] == ["Coffee"]

    groups_res = client.get("/expenses/?view=groups", headers=headers)
    assert groups_res.status_code == 200
    assert [item["merge_group"]["title"] for item in groups_res.json()["items"] if item["type"] == "MERGE_GROUP"] == ["May Utilities"]

    refunds_res = client.get("/expenses/?view=refunds", headers=headers)
    assert refunds_res.status_code == 200
    assert len(refunds_res.json()["items"]) == 1
    assert refunds_res.json()["items"][0]["expense"]["transaction_type"] == "REFUND"


def test_create_expense_invalid_title(client):
    headers = create_user_and_token(
        client, "expuser6", "expuser6@example.com", "Password123!"
    )
    create_budget(client, headers, category="Food", monthly_limit=500)

    res_short = create_expense(client, headers, title="ab", amount=10, category="Food")
    assert res_short.status_code == 422

    res_blank = create_expense(client, headers, title="   ", amount=10, category="Food")
    assert res_blank.status_code == 422

    res_long = create_expense(client, headers, title="a" * 33, amount=10, category="Food")
    assert res_long.status_code == 422


def test_create_expense_invalid_description(client):
    headers = create_user_and_token(
        client, "expuser7", "expuser7@example.com", "Password123!"
    )
    create_budget(client, headers, category="Food", monthly_limit=500)

    res = create_expense(
        client,
        headers,
        title="Valid Title",
        amount=10,
        category="Food",
        description="x" * 501,
    )
    assert res.status_code == 422


def test_title_description_trimmed(client):
    headers = create_user_and_token(
        client, "expuser8", "expuser8@example.com", "Password123!"
    )
    create_budget(client, headers, category="Food", monthly_limit=500)

    res = create_expense(
        client,
        headers,
        title="  Sandwich  ",
        amount=10,
        category="Food",
        description="  tasty  ",
    )
    assert res.status_code == 201
    data = res.json()
    assert data["title"] == "Sandwich"
    assert data["description"] == "tasty"


def test_create_expense_invalid_amount(client):
    headers = create_user_and_token(
        client, "expuser9", "expuser9@example.com", "Password123!"
    )
    create_budget(client, headers, category="Food", monthly_limit=500)

    res_zero = create_expense(client, headers, title="Zero", amount=0, category="Food")
    assert res_zero.status_code == 422

    res_negative = create_expense(client, headers, title="Neg", amount=-5, category="Food")
    assert res_negative.status_code == 422


def test_create_expense_invalid_category(client):
    headers = create_user_and_token(
        client, "expuser10", "expuser10@example.com", "Password123!"
    )
    create_budget(client, headers, category="Food", monthly_limit=500)

    res = client.post("/expenses/", json={
        "title": "BadCategory",
        "amount": 10,
        "category": "InvalidCategory",
        "description": "test",
        "date": user_timezone_today().isoformat(),
    }, headers=headers)
    assert res.status_code == 422


def test_create_expense_rejects_financing_context_category(client):
    headers = create_user_and_token(
        client, "expuser10financing", "expuser10financing@example.com", "Password123!"
    )

    res = client.post("/expenses/", json={
        "title": "Phone plan",
        "amount": 100_000,
        "category": "Installments & Debt",
        "description": "financing mechanism is not a purchase category",
        "date": user_timezone_today().isoformat(),
    }, headers=headers)

    assert res.status_code == 400
    assert res.json()["detail"] == "expenses.validation.real_expense_category_required"


def test_active_category_metadata_excludes_financing_context_category(client):
    res = client.get("/meta/categories")

    assert res.status_code == 200
    assert "Installments & Debt" not in res.json()


def test_legacy_financing_context_expense_remains_readable(client, session):
    headers = create_user_and_token(
        client, "expuser10legacyfinancing", "expuser10legacyfinancing@example.com", "Password123!"
    )
    user = session.query(models.User).filter(
        models.User.email == "expuser10legacyfinancing@example.com"
    ).first()
    assert user is not None
    wallet = session.query(models.Wallet).filter(
        models.Wallet.owner_id == user.id,
        models.Wallet.is_default == True,
    ).first()
    assert wallet is not None

    legacy_event = models.FinancialEvent(
        owner_id=user.id,
        title="Legacy installment category row",
        event_type=models.TransactionType.EXPENSE,
        status=models.FinancialEventStatus.POSTED,
        description="seeded legacy data",
        date=user_timezone_today(),
    )
    legacy_event.wallet_legs.append(models.WalletLedger(
        owner_id=user.id,
        wallet_id=wallet.id,
        amount=-100_000,
    ))
    legacy_event.entity_legs.append(models.EntityLedger(
        label="Legacy installment category row",
        amount=100_000,
        category=models.ExpenseCategory.INSTALLMENTS_DEBT,
    ))
    session.add(legacy_event)
    session.commit()
    legacy_event_id = legacy_event.id

    listed = client.get("/expenses/", headers=headers)
    assert listed.status_code == 200, listed.text
    listed_expenses = _feed_expenses(listed.json())
    legacy_list_row = next(item for item in listed_expenses if item["id"] == legacy_event_id)
    assert legacy_list_row["category"] == "Installments & Debt"

    detail = client.get(f"/expenses/{legacy_event_id}", headers=headers)
    assert detail.status_code == 200, detail.text
    assert detail.json()["category"] == "Installments & Debt"

    rich_detail = client.get(f"/expenses/{legacy_event_id}/detail", headers=headers)
    assert rich_detail.status_code == 200, rich_detail.text
    assert rich_detail.json()["category"] == "Installments & Debt"

    blocked_create = client.post("/expenses/", json={
        "title": "New financing-category write",
        "amount": 100_000,
        "category": "Installments & Debt",
        "description": "new writes still blocked",
        "date": user_timezone_today().isoformat(),
    }, headers=headers)
    assert blocked_create.status_code == 400
    assert blocked_create.json()["detail"] == "expenses.validation.real_expense_category_required"


def test_split_expense_rejects_financing_context_category(client):
    headers = create_user_and_token(
        client, "expuser10splitfinancing", "expuser10splitfinancing@example.com", "Password123!"
    )
    create_budget(client, headers, category="Groceries", monthly_limit=500_000)
    created = create_expense(client, headers, title="Market", amount=100_000, category="Groceries")
    assert created.status_code == 201, created.text

    res = client.post(
        f"/expenses/{created.json()['id']}/split",
        json={
            "items": [
                {"label": "Groceries", "amount": 50_000, "category": "Groceries"},
                {"label": "Financing", "amount": 50_000, "category": "Installments & Debt"},
            ],
        },
        headers=headers,
    )

    assert res.status_code == 400
    assert res.json()["detail"] == "expenses.validation.real_expense_category_required"


def test_create_expense_invalid_date(client):
    headers = create_user_and_token(
        client, "expuser11", "expuser11@example.com", "Password123!"
    )
    create_budget(client, headers, category="Food", monthly_limit=500)

    future_date = (date.today() + timedelta(days=1)).isoformat()
    res_future = client.post("/expenses/", json={
        "title": "Future",
        "amount": 10,
        "category": "Groceries",
        "description": "test",
        "date": future_date,
    }, headers=headers)
    assert res_future.status_code == 400

    past_date = date(2019, 12, 31).isoformat()
    res_past = client.post("/expenses/", json={
        "title": "Past",
        "amount": 10,
        "category": "Groceries",
        "description": "test",
        "date": past_date,
    }, headers=headers)
    assert res_past.status_code == 422


def test_create_expense_future_date_uses_request_timezone(client, monkeypatch):
    headers = create_user_and_token(
        client, "expusertz1", "expusertz1@example.com", "Password123!"
    )
    create_budget(client, headers, category="Food", monthly_limit=500, budget_year=2026, budget_month=2)

    def fake_today_in_tz(tz):
        key = getattr(tz, "key", "")
        if key == "Asia/Tashkent":
            return date(2026, 2, 2)
        return date(2026, 2, 1)

    monkeypatch.setattr(expenses_router, "today_in_tz", fake_today_in_tz)

    base_payload = {
        "title": "Lunch",
        "amount": 10,
        "category": "Groceries",
        "description": "test",
        "date": "2026-02-02",
    }

    res_tashkent = client.post(
        "/expenses/",
        json=base_payload,
        headers={**headers, "X-Timezone": "Asia/Tashkent"},
    )
    assert res_tashkent.status_code == 201, res_tashkent.text

    res_utc = client.post(
        "/expenses/",
        json={**base_payload, "title": "Dinner"},
        headers={**headers, "X-Timezone": "UTC"},
    )
    assert res_utc.status_code == 400
    assert res_utc.json()["detail"] == "expenses.date_in_future"


def test_update_expense_rejects_financial_date_field(client, monkeypatch):
    headers = create_user_and_token(
        client, "expusertz2", "expusertz2@example.com", "Password123!"
    )
    create_budget(client, headers, category="Food", monthly_limit=500, budget_year=2026, budget_month=2)

    created = client.post(
        "/expenses/",
        json={
            "title": "Lunch",
            "amount": 10,
            "category": "Groceries",
            "description": "test",
            "date": "2026-02-01",
        },
        headers=headers,
    )
    assert created.status_code == 201, created.text
    expense_id = created.json()["id"]

    def fake_today_in_tz(tz):
        key = getattr(tz, "key", "")
        if key == "Asia/Tashkent":
            return date(2026, 2, 2)
        return date(2026, 2, 1)

    monkeypatch.setattr(expenses_router, "today_in_tz", fake_today_in_tz)

    res_tashkent = client.put(
        f"/expenses/{expense_id}",
        json={
            "title": "Lunch Updated",
            "description": "test updated",
            "date": "2026-02-02",
        },
        headers={**headers, "X-Timezone": "Asia/Tashkent"},
    )
    assert res_tashkent.status_code == 422


def test_list_expenses_filters_and_sort(client):
    headers = create_user_and_token(
        client, "expuser12", "expuser12@example.com", "Password123!"
    )
    create_budget(client, headers, category="Food", monthly_limit=500)
    create_budget(client, headers, category="Transport", monthly_limit=500)

    create_expense(client, headers, title="Coffee", amount=3, category="Food")
    create_expense(client, headers, title="Taxi Ride", amount=25, category="Transport")
    create_expense(client, headers, title="Big Lunch", amount=15, category="Food")

    res_search = client.get("/expenses/?search=coffee", headers=headers)
    assert res_search.status_code == 200
    assert len(res_search.json()["items"]) == 1

    res_category = client.get("/expenses/?category=Groceries", headers=headers)
    assert res_category.status_code == 200
    assert all(item["category"] == "Groceries" for item in _feed_expenses(res_category.json()))

    res_sort = client.get("/expenses/?sort=expensive", headers=headers)
    assert res_sort.status_code == 200
    amounts = [item["amount"] for item in _feed_expenses(res_sort.json())]
    assert amounts == sorted(amounts, reverse=True)

    res_oldest = client.get("/expenses/?sort=oldest", headers=headers)
    assert res_oldest.status_code == 200
    dates = [item["date"] for item in _feed_expenses(res_oldest.json())]
    assert dates == sorted(dates)


def test_list_expenses_newest_uses_expense_date(client):
    headers = create_user_and_token(
        client, "expuser14", "expuser14@example.com", "Password123!"
    )
    create_budget(client, headers, category="Food", monthly_limit=500, budget_year=2024, budget_month=1)
    create_budget(client, headers, category="Food", monthly_limit=500, budget_year=2025, budget_month=1)

    client.post("/expenses/", json={
        "title": "Older by date",
        "amount": 10,
        "category": "Groceries",
        "description": "test",
        "date": "2024-01-01",
    }, headers=headers)
    client.post("/expenses/", json={
        "title": "Newer by date",
        "amount": 10,
        "category": "Groceries",
        "description": "test",
        "date": "2025-01-01",
    }, headers=headers)

    res = client.get("/expenses/?sort=newest", headers=headers)
    assert res.status_code == 200
    data = _feed_expenses(res.json())
    assert len(data) >= 2
    assert data[0]["date"] >= data[1]["date"]
    assert data[0]["title"] == "Newer by date"


def test_list_expenses_time_range(client):
    headers = create_user_and_token(
        client, "expuser13", "expuser13@example.com", "Password123!"
    )
    old_date = (date.today() - timedelta(days=40)).isoformat()
    recent_date = (date.today() - timedelta(days=5)).isoformat()
    old_dt = date.fromisoformat(old_date)
    recent_dt = date.fromisoformat(recent_date)
    create_budget(client, headers, category="Food", monthly_limit=500, budget_year=old_dt.year, budget_month=old_dt.month)
    if (old_dt.year, old_dt.month) != (recent_dt.year, recent_dt.month):
        create_budget(client, headers, category="Food", monthly_limit=500, budget_year=recent_dt.year, budget_month=recent_dt.month)

    client.post("/expenses/", json={
        "title": "Old",
        "amount": 10,
        "category": "Groceries",
        "description": "test",
        "date": old_date,
    }, headers=headers)
    client.post("/expenses/", json={
        "title": "Recent",
        "amount": 10,
        "category": "Groceries",
        "description": "test",
        "date": recent_date,
    }, headers=headers)

    res = client.get("/expenses/?time_range=past_month", headers=headers)
    assert res.status_code == 200
    titles = [item["title"] for item in _feed_expenses(res.json())]
    assert "Recent" in titles
    assert "Old" not in titles


def test_update_expense_metadata_only(client, session):
    headers = create_user_and_token(
        client, "expuser4", "expuser4@example.com", "Password123!"
    )
    create_budget(client, headers, category="Food", monthly_limit=500)
    res = create_expense(client, headers, title="Old", amount=10, category="Food")
    expense_id = res.json()["id"]
    original_wallet_id = res.json()["wallet_id"]

    res_update = client.put(
        f"/expenses/{expense_id}",
        json={
            "title": "New",
            "description": "updated description",
        },
        headers=headers,
    )
    assert res_update.status_code == 200, res_update.text
    data = res_update.json()
    assert data["title"] == "New"
    assert data["description"] == "updated description"
    assert data["amount"] == 10
    assert data["wallet_id"] == original_wallet_id

    session.expire_all()
    event = session.query(models.FinancialEvent).filter(
        models.FinancialEvent.id == expense_id,
    ).first()
    assert event.title == "New"
    assert event.description == "updated description"
    assert len(event.wallet_legs) == 1
    assert event.wallet_legs[0].amount == -10
    assert len(event.entity_legs) == 1
    assert event.entity_legs[0].amount == 10


def test_update_expense_allows_optional_description(client):
    headers = create_user_and_token(
        client, "expuser18", "expuser18@example.com", "Password123!"
    )
    create_budget(client, headers, category="Food", monthly_limit=500)
    create_budget(client, headers, category="Food", monthly_limit=500, budget_year=2024, budget_month=1)
    res = create_expense(client, headers, title="Meal", amount=10, category="Food", description="note")
    expense_id = res.json()["id"]

    res_update = client.put(
        f"/expenses/{expense_id}",
        json={
            "title": "Meal Updated",
            "description": None,
        },
        headers=headers,
    )
    assert res_update.status_code == 200, res_update.text
    assert res_update.json()["category"] == "Groceries"
    assert res_update.json()["description"] is None


def test_update_expense_rejects_financial_fields(client):
    headers = create_user_and_token(
        client, "expuser16", "expuser16@example.com", "Password123!"
    )
    create_budget(client, headers, category="Food", monthly_limit=500)
    create_budget(client, headers, category="Food", monthly_limit=500, budget_year=2024, budget_month=1)
    res = create_expense(client, headers, title="Lunch", amount=10, category="Food")
    expense_id = res.json()["id"]

    res_update = client.put(
        f"/expenses/{expense_id}",
        json={
            "title": "Lunch",
            "amount": 10,
            "category": "Transport",
            "description": "test",
            "date": "2024-01-01",
            "wallet_id": 1,
            "subcategory_id": None,
            "project_id": None,
            "project_subcategory_id": None,
        },
        headers=headers,
    )
    assert res_update.status_code == 422


def test_update_expense_requires_title(client):
    headers = create_user_and_token(
        client, "expuser17", "expuser17@example.com", "Password123!"
    )
    create_budget(client, headers, category="Food", monthly_limit=500)
    create_budget(client, headers, category="Food", monthly_limit=500, budget_year=2024, budget_month=1)
    res = create_expense(client, headers, title="Snack", amount=5, category="Food")
    expense_id = res.json()["id"]

    res_update = client.put(
        f"/expenses/{expense_id}",
        json={"description": "metadata only still requires title"},
        headers=headers,
    )
    assert res_update.status_code == 422


def test_update_expense_metadata_only_allows_multi_wallet_event(client, session):
    headers = create_user_and_token(
        client, "expupdatemulti", "expupdatemulti@example.com", "Password123!"
    )
    create_budget(client, headers, category="Transport", monthly_limit=500_000)

    user = session.query(models.User).filter(
        models.User.email == "expupdatemulti@example.com"
    ).first()
    default_wallet = session.query(models.Wallet).filter(
        models.Wallet.owner_id == user.id,
        models.Wallet.is_default == True,
    ).first()
    second_wallet = models.Wallet(
        owner_id=user.id,
        name="Cash Pocket",
        wallet_type=models.WalletType.CASH,
        accounting_type=models.AccountingType.ASSET,
        initial_balance=500_000,
        current_balance=500_000,
        is_default=False,
    )
    session.add(second_wallet)
    session.commit()
    session.refresh(second_wallet)

    created = client.post(
        "/expenses/",
        json={
            "title": "Taxi",
            "amount": 100_000,
            "category": "Transport",
            "description": "split paid",
            "date": user_timezone_today().isoformat(),
            "wallet_allocations": [
                {"wallet_id": default_wallet.id, "amount": 60_000},
                {"wallet_id": second_wallet.id, "amount": 40_000},
            ],
        },
        headers=headers,
    )
    assert created.status_code == 201, created.text
    expense_id = created.json()["id"]

    updated = client.put(
        f"/expenses/{expense_id}",
        json={
            "title": "Taxi renamed",
            "description": "metadata changed",
        },
        headers=headers,
    )

    assert updated.status_code == 200, updated.text
    data = updated.json()
    assert data["title"] == "Taxi renamed"
    assert data["description"] == "metadata changed"
    assert data["amount"] == 100_000
    assert sorted(
        (item["wallet_id"], item["amount"]) for item in data["wallet_allocations"]
    ) == [
        (default_wallet.id, 60_000),
        (second_wallet.id, 40_000),
    ]

    session.expire_all()
    event = session.query(models.FinancialEvent).filter(
        models.FinancialEvent.id == expense_id,
    ).first()
    assert sorted((leg.wallet_id, leg.amount) for leg in event.wallet_legs) == [
        (default_wallet.id, -60_000),
        (second_wallet.id, -40_000),
    ]


def test_delete_expense_voids_one_wallet_quick_add(client, session):
    headers = create_user_and_token(
        client, "expuser5", "expuser5@example.com", "Password123!"
    )
    create_budget(client, headers, category="Food", monthly_limit=500)
    res = create_expense(client, headers, title="Delete", amount=10, category="Food")
    expense_id = res.json()["id"]
    wallet_id = res.json()["wallet_id"]

    res_del = client.delete(f"/expenses/{expense_id}", headers=headers)
    assert res_del.status_code == 204

    res_get = client.get(f"/expenses/{expense_id}", headers=headers)
    assert res_get.status_code == 404

    session.expire_all()
    original = session.query(models.FinancialEvent).filter(
        models.FinancialEvent.id == expense_id,
    ).first()
    assert original is not None
    assert original.status == models.FinancialEventStatus.VOIDED
    assert original.void_reversal_event_id is not None

    reversal = session.query(models.FinancialEvent).filter(
        models.FinancialEvent.id == original.void_reversal_event_id,
    ).first()
    assert reversal is not None
    assert reversal.status == models.FinancialEventStatus.REVERSAL
    assert reversal.reverses_event_id == original.id
    assert reversal.reference_type == models.ReferenceType.VOID_REVERSAL
    assert reversal.event_type == models.TransactionType.EXPENSE
    assert len(reversal.wallet_legs) == 1
    assert reversal.wallet_legs[0].wallet_id == wallet_id
    assert reversal.wallet_legs[0].amount == 10
    assert len(reversal.entity_legs) == 1
    assert reversal.entity_legs[0].amount == -10

    wallet = session.query(models.Wallet).filter(models.Wallet.id == wallet_id).first()
    assert wallet.current_balance == 10_000_000

    listed = client.get("/expenses/", headers=headers)
    assert listed.status_code == 200
    assert all(item["id"] != expense_id for item in _feed_expenses(listed.json()))

    res_second_delete = client.delete(f"/expenses/{expense_id}", headers=headers)
    assert res_second_delete.status_code == 400
    assert res_second_delete.json()["detail"] == "expenses.not_posted"


def test_delete_expense_voids_multi_wallet_quick_add(client, session):
    headers = create_user_and_token(
        client, "expvoidmulti", "expvoidmulti@example.com", "Password123!"
    )
    create_budget(client, headers, category="Transport", monthly_limit=500_000)

    user = session.query(models.User).filter(
        models.User.email == "expvoidmulti@example.com"
    ).first()
    default_wallet = session.query(models.Wallet).filter(
        models.Wallet.owner_id == user.id,
        models.Wallet.is_default == True,
    ).first()
    second_wallet = models.Wallet(
        owner_id=user.id,
        name="Cash Pocket",
        wallet_type=models.WalletType.CASH,
        accounting_type=models.AccountingType.ASSET,
        initial_balance=500_000,
        current_balance=500_000,
        is_default=False,
    )
    session.add(second_wallet)
    session.commit()
    session.refresh(second_wallet)

    created = client.post(
        "/expenses/",
        json={
            "title": "Taxi",
            "amount": 100_000,
            "category": "Transport",
            "description": "split paid",
            "date": user_timezone_today().isoformat(),
            "wallet_allocations": [
                {"wallet_id": default_wallet.id, "amount": 60_000},
                {"wallet_id": second_wallet.id, "amount": 40_000},
            ],
        },
        headers=headers,
    )
    assert created.status_code == 201, created.text
    expense_id = created.json()["id"]

    deleted = client.delete(f"/expenses/{expense_id}", headers=headers)
    assert deleted.status_code == 204

    session.expire_all()
    original = session.query(models.FinancialEvent).filter(
        models.FinancialEvent.id == expense_id,
    ).first()
    assert original.status == models.FinancialEventStatus.VOIDED

    reversal = session.query(models.FinancialEvent).filter(
        models.FinancialEvent.id == original.void_reversal_event_id,
    ).first()
    assert reversal.status == models.FinancialEventStatus.REVERSAL
    assert sorted((leg.wallet_id, leg.amount) for leg in reversal.wallet_legs) == [
        (default_wallet.id, 60_000),
        (second_wallet.id, 40_000),
    ]
    assert [leg.amount for leg in reversal.entity_legs] == [-100_000]

    refreshed_default = session.query(models.Wallet).filter(models.Wallet.id == default_wallet.id).first()
    refreshed_second = session.query(models.Wallet).filter(models.Wallet.id == second_wallet.id).first()
    assert refreshed_default.current_balance == 10_000_000
    assert refreshed_second.current_balance == 500_000


def test_expense_write_rate_limit_blocks_burst(client):
    for key in redis_client.scan_iter("tb:expenses_write:*"):
        redis_client.delete(key)

    headers = create_user_and_token(
        client, "expuser15", "expuser15@example.com", "Password123!"
    )
    create_budget(client, headers, category="Food", monthly_limit=5000)

    blocked = None
    for i in range(25):
        res = client.post("/expenses/", json={
            "title": f"Burst {i}",
            "amount": 10,
            "category": "Groceries",
            "description": "test",
            "date": user_timezone_today().isoformat(),
        }, headers=headers)
        if res.status_code == 429:
            blocked = res
            break

    assert blocked is not None
    assert blocked.status_code == 429
    assert "Retry-After" in blocked.headers


def test_expense_month_limit_blocks_1001st_expense(client, session, monkeypatch):
    headers = create_user_and_token(
        client, "expuser19", "expuser19@example.com", "Password123!"
    )

    target_today = date(2026, 3, 12)

    monkeypatch.setattr(expenses_router, "today_in_tz", lambda _tz: target_today)

    budget_res = create_budget(
        client,
        headers,
        category="Food",
        monthly_limit=5_000_000,
        budget_year=2026,
        budget_month=3,
    )
    assert budget_res.status_code == 201
    budget_id = budget_res.json()["id"]

    user = session.query(models.User).filter(models.User.email == "expuser19@example.com").first()
    assert user is not None
    wallet = session.query(models.Wallet).filter(models.Wallet.owner_id == user.id).first()

    seeded_events = []
    for i in range(1000):
        event = models.FinancialEvent(
            owner_id=user.id,
            title=f"Seeded {i}",
            event_type=models.TransactionType.EXPENSE,
            status=models.FinancialEventStatus.POSTED,
            description="seeded",
            date=date(2026, 3, (i % 12) + 1),
        )
        event.wallet_legs.append(models.WalletLedger(
            owner_id=user.id,
            wallet_id=wallet.id,
            amount=-(1000 + i),
        ))
        event.entity_legs.append(models.EntityLedger(
            amount=1000 + i,
            category=models.ExpenseCategory.GROCERIES,
            budget_id=budget_id,
        ))
        seeded_events.append(event)
    session.add_all(seeded_events)
    session.commit()

    res = client.post("/expenses/", json={
        "title": "Overflow expense",
        "amount": 10,
        "category": "Groceries",
        "description": "test",
        "date": "2026-03-12",
    }, headers=headers)

    assert res.status_code == 400
    assert res.json()["detail"] == "expenses.month_limit_reached"


def test_create_expense_sets_budget_id_for_matching_month_budget(client, session):
    headers = create_user_and_token(
        client, "expbudgetfk1", "expbudgetfk1@example.com", "Password123!"
    )
    target_date = date(2024, 1, 15)
    budget_res = create_budget(
        client,
        headers,
        category="Food",
        monthly_limit=500,
        budget_year=2024,
        budget_month=1,
    )
    assert budget_res.status_code == 201, budget_res.text
    budget_id = budget_res.json()["id"]

    res = create_expense(
        client,
        headers,
        title="Lunch",
        amount=10,
        category="Food",
        expense_date=target_date,
    )
    assert res.status_code == 201, res.text
    expense_id = res.json()["id"]

    db_expense = session.query(models.FinancialEvent).filter(
        models.FinancialEvent.id == expense_id,
        models.FinancialEvent.event_type == models.TransactionType.EXPENSE
    ).first()
    assert db_expense is not None
    assert db_expense.entity_legs[0].budget_id == budget_id


def test_update_expense_rebinds_budget_id_when_date_month_changes(client, session):
    headers = create_user_and_token(
        client, "expbudgetfk2", "expbudgetfk2@example.com", "Password123!"
    )
    jan_budget = create_budget(
        client,
        headers,
        category="Food",
        monthly_limit=500,
        budget_year=2024,
        budget_month=1,
    )
    feb_budget = create_budget(
        client,
        headers,
        category="Food",
        monthly_limit=700,
        budget_year=2024,
        budget_month=2,
    )
    assert jan_budget.status_code == 201, jan_budget.text
    assert feb_budget.status_code == 201, feb_budget.text
    jan_budget_id = jan_budget.json()["id"]
    _feb_budget_id = feb_budget.json()["id"]

    created = create_expense(
        client,
        headers,
        title="Meal",
        amount=20,
        category="Food",
        expense_date=date(2024, 1, 20),
    )
    assert created.status_code == 201, created.text
    expense_id = created.json()["id"]

    db_expense_before = session.query(models.FinancialEvent).filter(
        models.FinancialEvent.id == expense_id,
        models.FinancialEvent.event_type == models.TransactionType.EXPENSE
    ).first()
    assert db_expense_before is not None
    assert db_expense_before.entity_legs[0].budget_id == jan_budget_id

    updated = client.put(
        f"/expenses/{expense_id}",
        json={
            "title": "Meal moved",
            "amount": 25,
            "description": "moved to feb",
            "date": "2024-02-10",
        },
        headers=headers,
    )
    assert updated.status_code == 422, updated.text

    session.expire_all()
    db_expense_after = session.query(models.FinancialEvent).filter(
        models.FinancialEvent.id == expense_id,
        models.FinancialEvent.event_type == models.TransactionType.EXPENSE
    ).first()
    assert db_expense_after is not None
    assert db_expense_after.entity_legs[0].budget_id == jan_budget_id
