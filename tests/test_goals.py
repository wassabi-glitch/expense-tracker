from datetime import date, timedelta

import pytest

from app import models
from app.redis_rate_limiter import redis_client
from app.services.goal_funding_service import get_goal_wallet_funded_amount
from tests.helpers import create_budget, create_expense, create_user_and_token, user_timezone_today


def _setup_premium_user_with_goal_wallet(client, headers, initial_balance=2_000_000):
    onboard = client.post(
        "/users/me/onboarding",
        json={
            "life_statuses": ["employed"],
            "wallets": [
                {
                    "name": "Savings",
                    "wallet_type": "SAVINGS",
                    "initial_balance": initial_balance,
                    "can_fund_goals": True,
                }
            ],
        },
        headers=headers,
    )
    assert onboard.status_code == 200
    premium = client.post("/users/me/toggle-premium", headers=headers)
    assert premium.status_code == 200
    wallets = client.get("/wallets", headers=headers)
    assert wallets.status_code == 200
    return wallets.json()[0]["id"]


def _make_premium(client, headers):
    premium = client.post("/users/me/toggle-premium", headers=headers)
    assert premium.status_code == 200


def _create_wallet(
    client,
    headers,
    *,
    name,
    wallet_type="SAVINGS",
    initial_balance=1_000_000,
    can_fund_goals=True,
):
    response = client.post(
        "/wallets",
        json={
            "name": name,
            "wallet_type": wallet_type,
            "initial_balance": initial_balance,
            "can_fund_goals": can_fund_goals,
        },
        headers=headers,
    )
    assert response.status_code == 201
    return response.json()["id"]


def _wallet_by_id(client, headers, wallet_id):
    response = client.get("/wallets", headers=headers)
    assert response.status_code == 200
    return next(item for item in response.json() if item["id"] == wallet_id)


def _create_current_budget(client, headers, category="Electronics", monthly_limit=1_000_000):
    response = create_budget(client, headers, category=category, monthly_limit=monthly_limit)
    assert response.status_code in {200, 201}


def _create_i_owe_debt(client, headers, wallet_id, *, amount=500_000, counterparty="Friend"):
    response = client.post(
        "/debts",
        json={
            "debt_type": "OWING",
            "counterparty_name": counterparty,
            "initial_amount": amount,
            "currency": "UZS",
            "date": user_timezone_today().isoformat(),
            "expected_return_date": user_timezone_today().isoformat(),
            "is_money_transferred": True,
            "initial_wallet_id": wallet_id,
        },
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return response.json()


def _create_i_am_owed_debt(client, headers, *, amount=500_000, counterparty="Friend"):
    response = client.post(
        "/debts",
        json={
            "debt_type": "OWED",
            "counterparty_name": counterparty,
            "initial_amount": amount,
            "currency": "UZS",
            "date": user_timezone_today().isoformat(),
            "expected_return_date": user_timezone_today().isoformat(),
            "is_money_transferred": False,
        },
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return response.json()


def _create_payment_plan_debt(client, headers, *, amount=500_000):
    response = client.post(
        "/payment-plans",
        json={
            "item_name": "Phone",
            "store_or_bank_name": "Phone Store",
            "total_price": amount,
            "down_payment": 0,
            "months": 5,
            "frequency": "MONTHLY",
            "start_date": user_timezone_today().isoformat(),
            "expense_category": "Electronics",
        },
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_create_goal_and_list_with_zero_progress(client):
    headers = create_user_and_token(
        client, "goaluser1", "goaluser1@example.com", "Password123!"
    )
    _setup_premium_user_with_goal_wallet(client, headers)

    created = client.post(
        "/goals/",
        json={
            "title": "Laptop",
            "target_amount": 5_000_000,
            "target_date": "2026-12-31",
            "intent": "PLANNED_PURCHASE",
            "template": "laptop",
        },
        headers=headers,
    )
    assert created.status_code == 201
    payload = created.json()
    assert payload["title"] == "Laptop"
    assert payload["intent"] == "PLANNED_PURCHASE"
    assert payload["template"] == "laptop"
    assert payload["currency"] == "UZS"
    assert payload["funded_amount"] == 0
    assert payload["remaining_amount"] == 5_000_000
    assert payload["progress_percent"] == 0
    assert payload["status"] == "ACTIVE"
    assert payload["funding_sources"] == []

    listed = client.get("/goals/", headers=headers)
    assert listed.status_code == 200
    assert len(listed.json()) == 1
    assert listed.json()[0]["title"] == "Laptop"


def test_pay_obligation_goal_creation_validates_debt_and_duplicate_open_goal(client):
    headers = create_user_and_token(
        client, "goaldebtcreate", "goaldebtcreate@example.com", "Password123!"
    )
    wallet_id = _setup_premium_user_with_goal_wallet(client, headers)
    debt = _create_i_owe_debt(client, headers, wallet_id, amount=500_000)

    created = client.post(
        "/goals/",
        json={
            "title": "Friend debt",
            "target_amount": 500_000,
            "intent": "PAY_OBLIGATION",
            "linked_debt_id": debt["id"],
        },
        headers=headers,
    )
    assert created.status_code == 201, created.text
    payload = created.json()
    assert payload["intent"] == "PAY_OBLIGATION"
    assert payload["debt_goal_tracking_mode"] == "FULL_REMAINING_DEBT"
    assert payload["linked_debt_id"] == debt["id"]

    duplicate = client.post(
        "/goals/",
        json={
            "title": "Again debt",
            "target_amount": 100_000,
            "intent": "PAY_OBLIGATION",
            "linked_debt_id": debt["id"],
        },
        headers=headers,
    )
    assert duplicate.status_code == 400
    assert "goals.debt_goal_already_open" in duplicate.text


def test_pay_obligation_goal_rejects_owed_to_me_debt(client):
    headers = create_user_and_token(
        client, "goaldebtowed", "goaldebtowed@example.com", "Password123!"
    )
    _setup_premium_user_with_goal_wallet(client, headers)
    debt = _create_i_am_owed_debt(client, headers, amount=500_000)

    blocked = client.post(
        "/goals/",
        json={
            "title": "Collect friend debt",
            "target_amount": 500_000,
            "intent": "PAY_OBLIGATION",
            "linked_debt_id": debt["id"],
        },
        headers=headers,
    )
    assert blocked.status_code == 400
    assert blocked.json()["detail"] == "goals.debt_goal_requires_i_owe_debt"


def test_pay_obligation_goal_for_payment_plan_targets_next_payment_plan(client):
    headers = create_user_and_token(
        client, "goaldebtplan", "goaldebtplan@example.com", "Password123!"
    )
    _setup_premium_user_with_goal_wallet(client, headers)
    plan = _create_payment_plan_debt(client, headers, amount=500_000)

    created = client.post(
        "/goals/",
        json={
            "title": "Pay phone plan",
            "target_amount": 500_000,
            "intent": "PAY_OBLIGATION",
            "linked_payment_plan_id": plan["id"],
        },
        headers=headers,
    )
    assert created.status_code == 201, created.text
    payload = created.json()
    assert payload["intent"] == "PAY_OBLIGATION"
    assert payload["linked_debt_id"] is None
    assert payload["linked_payment_plan_id"] == plan["id"]
    assert payload["debt_goal_tracking_mode"] == "FIXED_DEBT_AMOUNT"
    assert payload["target_amount"] == 100_000
    assert payload["remaining_amount"] == 100_000
    assert payload["payment_plan_target"]["plan_id"] == plan["id"]
    assert payload["payment_plan_target"]["payment_number"] == 1
    assert payload["payment_plan_target"]["total_payments"] == 5
    assert payload["payment_plan_target"]["remaining_amount"] == 100_000


def test_pay_obligation_goal_payment_applies_to_next_payment_plan(client):
    headers = create_user_and_token(
        client, "goaldebtplanpay", "goaldebtplanpay@example.com", "Password123!"
    )
    wallet_id = _setup_premium_user_with_goal_wallet(client, headers, initial_balance=2_000_000)
    _create_current_budget(client, headers, category="Electronics")
    plan = _create_payment_plan_debt(client, headers, amount=500_000)

    created = client.post(
        "/goals/",
        json={
            "title": "Pay phone plan",
            "target_amount": 500_000,
            "intent": "PAY_OBLIGATION",
            "linked_payment_plan_id": plan["id"],
        },
        headers=headers,
    )
    assert created.status_code == 201, created.text
    goal_id = created.json()["id"]
    assert created.json()["target_amount"] == 100_000

    allocated = client.post(
        f"/goals/{goal_id}/allocations",
        json={"wallet_id": wallet_id, "amount": 100_000},
        headers=headers,
    )
    assert allocated.status_code == 200, allocated.text

    paid = client.post(
        f"/goals/{goal_id}/pay-debt",
        json={
            "amount": 100_000,
            "date": user_timezone_today().isoformat(),
            "payment_allocations": [{"wallet_id": wallet_id, "amount": 100_000}],
        },
        headers=headers,
    )
    assert paid.status_code == 200, paid.text
    result = paid.json()
    assert result["consumed_amount"] == 100_000
    assert result["debt"] is None
    assert result["debt_transaction"] is None
    assert result["payment_plan"]["remaining_amount"] == 400_000
    assert result["payment_plan_transaction_id"] is not None
    assert result["goal"]["status"] == "ACTIVE"
    assert result["goal"]["funded_amount"] == 0
    assert result["goal"]["target_amount"] == 100_000
    assert result["goal"]["remaining_amount"] == 100_000
    assert result["goal"]["payment_plan_target"]["payment_number"] == 2
    assert result["goal"]["payment_plan_target"]["remaining_amount"] == 100_000

    details = client.get(f"/payment-plans/{plan['id']}/details", headers=headers)
    assert details.status_code == 200, details.text
    payments = sorted(details.json()["plan"]["payments"], key=lambda item: (item["due_date"], item["id"]))
    assert payments[0]["status"] == "PAID"
    assert payments[0]["paid_amount"] == 100_000
    assert payments[1]["status"] == "PENDING"


def test_pay_obligation_goal_payment_consumes_goal_money_and_reduces_debt(client):
    headers = create_user_and_token(
        client, "goaldebtpay", "goaldebtpay@example.com", "Password123!"
    )
    wallet_id = _setup_premium_user_with_goal_wallet(client, headers)
    debt = _create_i_owe_debt(client, headers, wallet_id, amount=500_000)
    created = client.post(
        "/goals/",
        json={
            "title": "Pay friend",
            "target_amount": 200_000,
            "intent": "PAY_OBLIGATION",
            "linked_debt_id": debt["id"],
        },
        headers=headers,
    )
    assert created.status_code == 201, created.text
    goal_id = created.json()["id"]
    assert created.json()["debt_goal_tracking_mode"] == "FIXED_DEBT_AMOUNT"

    allocated = client.post(
        f"/goals/{goal_id}/allocations",
        json={"wallet_id": wallet_id, "amount": 200_000},
        headers=headers,
    )
    assert allocated.status_code == 200, allocated.text

    paid = client.post(
        f"/goals/{goal_id}/pay-debt",
        json={
            "amount": 200_000,
            "date": user_timezone_today().isoformat(),
            "payment_allocations": [{"wallet_id": wallet_id, "amount": 200_000}],
        },
        headers=headers,
    )
    assert paid.status_code == 200, paid.text
    result = paid.json()
    assert result["consumed_amount"] == 200_000
    assert result["debt"]["remaining_amount"] == 300_000
    assert result["goal"]["status"] == "COMPLETED"
    assert result["goal"]["consumed_amount"] == 200_000
    assert result["goal"]["funded_amount"] == 0
    assert result["goal"]["linked_debt_transaction_id"] == result["debt_transaction"]["id"]


def test_full_pay_obligation_goal_target_tracks_debt_charges_and_forgiveness(client):
    headers = create_user_and_token(
        client, "goaldebtsync", "goaldebtsync@example.com", "Password123!"
    )
    wallet_id = _setup_premium_user_with_goal_wallet(client, headers)
    debt = _create_i_owe_debt(client, headers, wallet_id, amount=500_000)
    created = client.post(
        "/goals/",
        json={
            "title": "Whole debt",
            "target_amount": 500_000,
            "intent": "PAY_OBLIGATION",
            "linked_debt_id": debt["id"],
        },
        headers=headers,
    )
    assert created.status_code == 201, created.text
    goal_id = created.json()["id"]

    charge = client.post(
        f"/debts/{debt['id']}/add-charge",
        json={"amount": 100_000, "reason": "Late charge"},
        headers=headers,
    )
    assert charge.status_code == 201, charge.text
    after_charge = client.get("/goals/", headers=headers)
    assert after_charge.status_code == 200
    goal_after_charge = next(goal for goal in after_charge.json() if goal["id"] == goal_id)
    assert goal_after_charge["target_amount"] == 600_000

    forgiveness = client.post(
        f"/debts/{debt['id']}/forgiveness",
        json={"amount": 50_000, "component": "PRINCIPAL", "date": user_timezone_today().isoformat()},
        headers=headers,
    )
    assert forgiveness.status_code == 200, forgiveness.text
    after_forgiveness = client.get("/goals/", headers=headers)
    goal_after_forgiveness = next(goal for goal in after_forgiveness.json() if goal["id"] == goal_id)
    assert goal_after_forgiveness["target_amount"] == 550_000


def test_full_pay_obligation_goal_target_syncs_after_reversal(client):
    headers = create_user_and_token(
        client, "goaldebtreverse", "goaldebtreverse@example.com", "Password123!"
    )
    wallet_id = _setup_premium_user_with_goal_wallet(client, headers)
    debt = _create_i_owe_debt(client, headers, wallet_id, amount=500_000)
    created = client.post(
        "/goals/",
        json={
            "title": "Whole reversible debt",
            "target_amount": 500_000,
            "intent": "PAY_OBLIGATION",
            "linked_debt_id": debt["id"],
        },
        headers=headers,
    )
    assert created.status_code == 201, created.text
    goal_id = created.json()["id"]

    adjusted = client.post(
        f"/debts/{debt['id']}/balance-adjustments",
        json={"confirmed_balance": 300_000, "note": "Friend corrected balance"},
        headers=headers,
    )
    assert adjusted.status_code == 200, adjusted.text
    after_adjustment = client.get("/goals/", headers=headers)
    adjusted_goal = next(goal for goal in after_adjustment.json() if goal["id"] == goal_id)
    assert adjusted_goal["target_amount"] == 300_000

    details = client.get(f"/debts/{debt['id']}/details", headers=headers)
    assert details.status_code == 200, details.text
    adjustment = next(item for item in details.json()["activity"] if item["kind"] == "ADJUSTMENT")
    reversed_response = client.post(
        f"/debts/{debt['id']}/ledger/{adjustment['ledger_entry_id']}/reverse",
        json={"note": "Correction was wrong"},
        headers=headers,
    )
    assert reversed_response.status_code == 200, reversed_response.text
    after_reversal = client.get("/goals/", headers=headers)
    reversed_goal = next(goal for goal in after_reversal.json() if goal["id"] == goal_id)
    assert reversed_goal["target_amount"] == 500_000


def test_goal_allocation_uses_wallet_available_without_changing_wallet_balance(client):
    headers = create_user_and_token(
        client, "goaluser2", "goaluser2@example.com", "Password123!"
    )
    wallet_id = _setup_premium_user_with_goal_wallet(client, headers)

    created = client.post(
        "/goals/",
        json={"title": "Phone", "target_amount": 800_000, "intent": "PLANNED_PURCHASE"},
        headers=headers,
    )
    assert created.status_code == 201
    goal_id = created.json()["id"]

    allocated = client.post(
        f"/goals/{goal_id}/allocations",
        json={"wallet_id": wallet_id, "amount": 800_000},
        headers=headers,
    )
    assert allocated.status_code == 200
    payload = allocated.json()
    assert payload["funded_amount"] == 800_000
    assert payload["remaining_amount"] == 0
    assert payload["status"] == "ACTIVE"
    assert payload["funding_sources"][0]["wallet_id"] == wallet_id
    assert payload["funding_sources"][0]["allocated_amount"] == 800_000

    wallets = client.get("/wallets", headers=headers)
    assert wallets.status_code == 200
    assert wallets.json()[0]["current_balance"] == 2_000_000

    summary = client.get("/goals/funding-summary", headers=headers)
    assert summary.status_code == 200
    assert summary.json()["total_wallet_balance"] == 2_000_000
    assert summary.json()["allocated_to_goals"] == 800_000


def test_fund_project_goal_creation_is_frozen(client):
    headers = create_user_and_token(
        client, "fundprojectfrozen", "fundprojectfrozen@example.com", "Password123!"
    )
    _make_premium(client, headers)

    created = client.post(
        "/goals/",
        json={"title": "Studio", "target_amount": 1_000_000, "intent": "FUND_PROJECT"},
        headers=headers,
    )
    assert created.status_code == 400, created.text
    assert created.json()["detail"] == "goals.fund_project_frozen"


def test_fund_project_goal_update_cannot_change_intent_to_fund_project(client):
    headers = create_user_and_token(
        client, "fundprojectupdf", "fundprojectupdf@example.com", "Password123!"
    )
    _setup_premium_user_with_goal_wallet(client, headers)

    created = client.post(
        "/goals/",
        json={"title": "Original", "target_amount": 500_000, "intent": "RESERVE"},
        headers=headers,
    )
    assert created.status_code == 201, created.text
    goal_id = created.json()["id"]

    update = client.patch(
        f"/goals/{goal_id}",
        json={"intent": "FUND_PROJECT"},
        headers=headers,
    )
    assert update.status_code == 400, update.text
    assert update.json()["detail"] == "goals.fund_project_frozen"


def test_only_fund_project_goals_can_graduate_and_past_target_date_stays_derived(client, session):
    headers = create_user_and_token(
        client, "fundprojectguards", "fundprojectguards@example.com", "Password123!"
    )
    wallet_id = _setup_premium_user_with_goal_wallet(client, headers, initial_balance=1_000_000)
    today = user_timezone_today()

    planned_purchase = client.post(
        "/goals/",
        json={"title": "Laptop", "target_amount": 500_000, "intent": "PLANNED_PURCHASE"},
        headers=headers,
    )
    assert planned_purchase.status_code == 201, planned_purchase.text
    blocked = client.post(
        f"/goals/{planned_purchase.json()['id']}/graduate",
        json={"project_title": "Laptop project", "start_date": today.isoformat(), "is_isolated": True},
        headers=headers,
    )
    assert blocked.status_code == 400
    assert blocked.json()["detail"] == "goals.graduation_requires_fund_project"

    user = session.query(models.User).filter(models.User.email == "fundprojectguards@example.com").first()
    fund_project = models.Goals(
        owner_id=user.id,
        title="Workshop",
        target_amount=700_000,
        target_date=today - timedelta(days=10),
        intent=models.GoalIntent.FUND_PROJECT,
        status=models.GoalStatus.ACTIVE,
    )
    session.add(fund_project)
    session.commit()
    goal_id = fund_project.id

    allocation = client.post(
        f"/goals/{goal_id}/allocations",
        json={"wallet_id": wallet_id, "amount": 300_000},
        headers=headers,
    )
    assert allocation.status_code == 200, allocation.text

    listed_before = client.get("/goals/", headers=headers)
    assert listed_before.status_code == 200, listed_before.text
    listed_goal = next(item for item in listed_before.json() if item["id"] == goal_id)
    assert listed_goal["status"] == "ACTIVE"
    assert listed_goal["time_state"] is None  # FUND_PROJECT is frozen, no time state

    graduated = client.post(
        f"/goals/{goal_id}/graduate",
        json={"project_title": "Workshop project", "start_date": today.isoformat(), "is_isolated": True},
        headers=headers,
    )
    assert graduated.status_code == 201, graduated.text
    assert graduated.json()["total_limit"] == 300_000

    listed_after = client.get("/goals/", headers=headers)
    assert listed_after.status_code == 200, listed_after.text
    stored_goal = next(item for item in listed_after.json() if item["id"] == goal_id)
    assert stored_goal["status"] == "GRADUATED"
    assert stored_goal["time_state"] is None


def test_planned_purchase_time_state_is_derived_from_user_timezone(client):
    headers = create_user_and_token(
        client, "pptimetz", "pptimetz@example.com", "Password123!"
    )
    _setup_premium_user_with_goal_wallet(client, headers)
    today = user_timezone_today()

    past_date = client.post(
        "/goals/",
        json={
            "title": "Past target purchase",
            "target_amount": 500_000,
            "target_date": (today - timedelta(days=10)).isoformat(),
            "intent": "PLANNED_PURCHASE",
        },
        headers=headers,
    )
    assert past_date.status_code == 201, past_date.text
    assert past_date.json()["status"] == "ACTIVE"
    assert past_date.json()["time_state"] == "overdue"

    future_date = client.post(
        "/goals/",
        json={
            "title": "Future target purchase",
            "target_amount": 500_000,
            "target_date": (today + timedelta(days=30)).isoformat(),
            "intent": "PLANNED_PURCHASE",
        },
        headers=headers,
    )
    assert future_date.status_code == 201, future_date.text
    assert future_date.json()["status"] == "ACTIVE"
    assert future_date.json()["time_state"] == "on_track"

    due_soon = client.post(
        "/goals/",
        json={
            "title": "Due soon purchase",
            "target_amount": 500_000,
            "target_date": (today + timedelta(days=3)).isoformat(),
            "intent": "PLANNED_PURCHASE",
        },
        headers=headers,
    )
    assert due_soon.status_code == 201, due_soon.text
    assert due_soon.json()["status"] == "ACTIVE"
    assert due_soon.json()["time_state"] == "due_soon"


def test_reserve_and_pay_obligation_goals_have_no_time_state(client, session):
    headers = create_user_and_token(
        client, "notimestate", "notimestate@example.com", "Password123!"
    )
    _setup_premium_user_with_goal_wallet(client, headers)

    reserve = client.post(
        "/goals/",
        json={
            "title": "Emergency fund",
            "target_amount": 1_000_000,
            "intent": "RESERVE",
        },
        headers=headers,
    )
    assert reserve.status_code == 201, reserve.text
    assert reserve.json()["status"] == "ACTIVE"
    assert reserve.json()["time_state"] is None
    assert reserve.json()["days_until_target"] is None
    assert reserve.json()["target_date"] is None

    reserve_no_date = client.post(
        "/goals/",
        json={"title": "Medical reserve", "target_amount": 500_000, "intent": "RESERVE"},
        headers=headers,
    )
    assert reserve_no_date.status_code == 201, reserve_no_date.text
    assert reserve_no_date.json()["time_state"] is None

    # Create an OWING debt for pay-obligation goal using the existing helper
    debt_wallet_id = _create_wallet(client, headers, name="DebtWallet", initial_balance=500_000)
    debt_res = _create_i_owe_debt(client, headers, debt_wallet_id, amount=300_000, counterparty="Mom")
    debt_id = debt_res["id"]

    pay_obl = client.post(
        "/goals/",
        json={
            "title": "Save for Mom loan",
            "target_amount": 300_000,
            "intent": "PAY_OBLIGATION",
            "linked_debt_id": debt_id,
        },
        headers=headers,
    )
    assert pay_obl.status_code == 201, pay_obl.text
    assert pay_obl.json()["status"] == "ACTIVE"
    assert pay_obl.json()["time_state"] is None


def test_goal_graduation_is_owner_scoped(client, session):
    owner_headers = create_user_and_token(
        client, "fundprojectowner", "fundprojectowner@example.com", "Password123!"
    )
    other_headers = create_user_and_token(
        client, "fundprojectother", "fundprojectother@example.com", "Password123!"
    )
    _make_premium(client, owner_headers)
    _make_premium(client, other_headers)
    today = user_timezone_today()

    owner_user = session.query(models.User).filter(models.User.email == "fundprojectowner@example.com").first()
    goal = models.Goals(
        owner_id=owner_user.id,
        title="Kitchen",
        target_amount=1_000_000,
        intent=models.GoalIntent.FUND_PROJECT,
        status=models.GoalStatus.ACTIVE,
    )
    session.add(goal)
    session.commit()

    response = client.post(
        f"/goals/{goal.id}/graduate",
        json={"project_title": "Kitchen project", "start_date": today.isoformat(), "is_isolated": True},
        headers=other_headers,
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "goals.not_found"


def test_goal_graduation_validation_failure_leaves_no_partial_project(client, session):
    headers = create_user_and_token(
        client, "fundprojectrollback", "fundprojectrollback@example.com", "Password123!"
    )
    wallet_id = _setup_premium_user_with_goal_wallet(client, headers, initial_balance=1_000_000)
    today = user_timezone_today()

    user = session.query(models.User).filter(models.User.email == "fundprojectrollback@example.com").first()
    goal = models.Goals(
        owner_id=user.id,
        title="Patio",
        target_amount=800_000,
        intent=models.GoalIntent.FUND_PROJECT,
        status=models.GoalStatus.ACTIVE,
    )
    session.add(goal)
    session.commit()
    goal_id = goal.id

    allocation = client.post(
        f"/goals/{goal_id}/allocations",
        json={"wallet_id": wallet_id, "amount": 300_000},
        headers=headers,
    )
    assert allocation.status_code == 200, allocation.text

    wallet = session.get(models.Wallet, wallet_id)
    wallet.currency = "USD"
    session.commit()

    response = client.post(
        f"/goals/{goal_id}/graduate",
        json={"project_title": "Patio project", "start_date": today.isoformat(), "is_isolated": True},
        headers=headers,
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "goals.currency_mismatch"
    assert (
        session.query(models.Project)
        .filter(models.Project.origin_goal_id == goal_id)
        .first()
        is None
    )
    session.expire_all()
    assert session.get(models.Goals, goal_id).status == models.GoalStatus.ACTIVE


def test_fund_project_goal_graduates_early_with_funded_stash_and_reports_shortfall(client, session):
    headers = create_user_and_token(
        client, "goalfundproject", "goalfundproject@example.com", "Password123!"
    )
    wallet_id = _setup_premium_user_with_goal_wallet(client, headers, initial_balance=2_000_000)
    today = user_timezone_today()

    user = session.query(models.User).filter(models.User.email == "goalfundproject@example.com").first()
    goal = models.Goals(
        owner_id=user.id,
        title="Wedding",
        target_amount=1_000_000,
        target_date=date(2026, 12, 31),
        intent=models.GoalIntent.FUND_PROJECT,
        status=models.GoalStatus.ACTIVE,
    )
    session.add(goal)
    session.commit()
    goal_id = goal.id

    allocation = client.post(
        f"/goals/{goal_id}/allocations",
        json={"wallet_id": wallet_id, "amount": 400_000},
        headers=headers,
    )
    assert allocation.status_code == 200, allocation.text
    assert allocation.json()["funded_amount"] == 400_000
    assert allocation.json()["progress_percent"] == 40

    graduated = client.post(
        f"/goals/{goal_id}/graduate",
        json={
            "project_title": "Wedding Project",
            "start_date": today.isoformat(),
            "target_end_date": "2026-12-31",
            "is_isolated": True,
        },
        headers=headers,
    )
    assert graduated.status_code == 201, graduated.text
    project = graduated.json()
    project_id = project["id"]
    assert project["origin_goal_id"] == goal_id
    assert project["is_isolated"] is True
    assert project["total_limit"] == 400_000
    assert project["released_funding"] == 400_000
    assert project["remaining_funding"] == 400_000
    assert project["progress_direction"] == "tick_down"
    assert project["funding_shortfall"] == 0
    assert project["isolated"]["funding_limit"] == 400_000
    assert project["isolated"]["allocated_funding"] == 0
    assert project["isolated"]["unallocated_funding"] == 400_000
    assert [
        (item["wallet_id"], item["amount"])
        for item in project["isolated"]["wallet_allocations"]
    ] == [(wallet_id, 400_000)]

    listed_goals = client.get("/goals/", headers=headers)
    assert listed_goals.status_code == 200, listed_goals.text
    linked_goal = next(item for item in listed_goals.json() if item["id"] == goal_id)
    assert linked_goal["status"] == "GRADUATED"
    assert linked_goal["funded_amount"] == 400_000
    assert linked_goal["released_amount"] == 400_000
    assert linked_goal["unreleased_amount"] == 0
    assert linked_goal["linked_project_id"] == project_id

    post_graduation_allocation = client.post(
        f"/goals/{goal_id}/allocations",
        json={"wallet_id": wallet_id, "amount": 100_000},
        headers=headers,
    )
    assert post_graduation_allocation.status_code == 400
    assert post_graduation_allocation.json()["detail"] == "goals.graduated_read_only"

    summary_after_graduation = client.get(
        f"/budgets/month-summary?budget_year={today.year}&budget_month={today.month}",
        headers=headers,
    )
    assert summary_after_graduation.status_code == 200, summary_after_graduation.text
    assert summary_after_graduation.json()["free_money_now"] == 1_600_000

    top_up = client.post(
        f"/projects/{project_id}/top-ups",
        json={"wallet_allocations": [{"wallet_id": wallet_id, "amount": 100_000}]},
        headers=headers,
    )
    assert top_up.status_code == 200, top_up.text
    assert top_up.json()["isolated"]["funding_limit"] == 500_000
    assert [
        (item["wallet_id"], item["amount"])
        for item in top_up.json()["isolated"]["wallet_allocations"]
    ] == [(wallet_id, 500_000)]

    category_limit = client.post(
        f"/projects/{project_id}/category-limits",
        json={"category": "Family & Events", "limit_amount": 400_000},
        headers=headers,
    )
    assert category_limit.status_code == 201, category_limit.text

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

    project_after_spend = client.get(f"/projects/{project_id}", headers=headers)
    assert project_after_spend.status_code == 200, project_after_spend.text
    spent_project = project_after_spend.json()
    assert spent_project["spent"] == 300_000
    assert spent_project["released_funding"] == 400_000
    assert spent_project["remaining_funding"] == 200_000
    assert spent_project["funding_shortfall"] == 0
    assert spent_project["progress_direction"] == "tick_down"

    summary = client.get(
        f"/budgets/month-summary?budget_year={today.year}&budget_month={today.month}",
        headers=headers,
    )
    assert summary.status_code == 200, summary.text
    assert summary.json()["free_money_now"] == 1_200_000
    assert summary.json()["backing_total"] == 1_200_000


def test_goal_allocation_cannot_exceed_target_amount(client):
    headers = create_user_and_token(
        client, "goaloverfund", "goaloverfund@example.com", "Password123!"
    )
    wallet_id = _setup_premium_user_with_goal_wallet(client, headers)

    created = client.post(
        "/goals/",
        json={"title": "Camera", "target_amount": 1_000_000, "intent": "PLANNED_PURCHASE"},
        headers=headers,
    )
    assert created.status_code == 201
    goal_id = created.json()["id"]

    first = client.post(
        f"/goals/{goal_id}/allocations",
        json={"wallet_id": wallet_id, "amount": 800_000},
        headers=headers,
    )
    assert first.status_code == 200

    blocked = client.post(
        f"/goals/{goal_id}/allocations",
        json={"wallet_id": wallet_id, "amount": 300_000},
        headers=headers,
    )
    assert blocked.status_code == 400
    assert blocked.json()["detail"] == "goals.allocation_exceeds_target"

    exact_remaining = client.post(
        f"/goals/{goal_id}/allocations",
        json={"wallet_id": wallet_id, "amount": 200_000},
        headers=headers,
    )
    assert exact_remaining.status_code == 200
    assert exact_remaining.json()["funded_amount"] == 1_000_000


def test_goal_allocation_accepts_multiple_wallets_in_one_request(client):
    headers = create_user_and_token(
        client, "goalmultireserve", "goalmultireserve@example.com", "Password123!"
    )
    _make_premium(client, headers)
    savings_id = _create_wallet(client, headers, name="MultiSavings", initial_balance=1_000_000)
    cash_id = _create_wallet(client, headers, name="MultiCash", wallet_type="CASH", initial_balance=1_000_000)

    created = client.post(
        "/goals/",
        json={"title": "Laptop", "target_amount": 1_000_000, "intent": "PLANNED_PURCHASE"},
        headers=headers,
    )
    assert created.status_code == 201
    goal_id = created.json()["id"]

    allocated = client.post(
        f"/goals/{goal_id}/allocations",
        json={
            "allocations": [
                {"wallet_id": savings_id, "amount": 600_000},
                {"wallet_id": cash_id, "amount": 400_000},
            ]
        },
        headers=headers,
    )
    assert allocated.status_code == 200
    payload = allocated.json()
    assert payload["funded_amount"] == 1_000_000
    assert payload["remaining_amount"] == 0
    assert {
        (source["wallet_id"], source["allocated_amount"])
        for source in payload["funding_sources"]
    } == {
        (cash_id, 400_000),
        (savings_id, 600_000),
    }

    summary = client.get("/goals/funding-summary", headers=headers)
    assert summary.status_code == 200
    assert summary.json()["allocated_to_goals"] == 1_000_000
    assert summary.json()["available_for_goals"] == 1_000_000


def test_goal_allocation_multi_wallet_request_is_atomic_when_one_row_fails(client):
    headers = create_user_and_token(
        client, "goalmultiatomic", "goalmultiatomic@example.com", "Password123!"
    )
    _make_premium(client, headers)
    savings_id = _create_wallet(client, headers, name="AtomicSavings", initial_balance=1_000_000)
    cash_id = _create_wallet(client, headers, name="AtomicCash", wallet_type="CASH", initial_balance=100_000)

    created = client.post(
        "/goals/",
        json={"title": "Camera", "target_amount": 1_000_000, "intent": "PLANNED_PURCHASE"},
        headers=headers,
    )
    assert created.status_code == 201
    goal_id = created.json()["id"]

    blocked = client.post(
        f"/goals/{goal_id}/allocations",
        json={
            "allocations": [
                {"wallet_id": savings_id, "amount": 500_000},
                {"wallet_id": cash_id, "amount": 200_000},
            ]
        },
        headers=headers,
    )
    assert blocked.status_code == 400
    assert blocked.json()["detail"] == "goals.insufficient_wallet_available_for_goal"

    goal = client.get("/goals/", headers=headers).json()[0]
    assert goal["funded_amount"] == 0
    assert goal["funding_sources"] == []


def test_goal_allocation_rejects_duplicate_wallet_rows(client):
    headers = create_user_and_token(
        client, "goalmultiduplicate", "goalmultiduplicate@example.com", "Password123!"
    )
    wallet_id = _setup_premium_user_with_goal_wallet(client, headers, initial_balance=1_000_000)

    created = client.post(
        "/goals/",
        json={"title": "Phone", "target_amount": 800_000, "intent": "PLANNED_PURCHASE"},
        headers=headers,
    )
    assert created.status_code == 201
    goal_id = created.json()["id"]

    blocked = client.post(
        f"/goals/{goal_id}/allocations",
        json={
            "allocations": [
                {"wallet_id": wallet_id, "amount": 300_000},
                {"wallet_id": wallet_id, "amount": 200_000},
            ]
        },
        headers=headers,
    )
    assert blocked.status_code == 422
    assert "goals.allocation_duplicate_wallet" in blocked.text


def test_one_wallet_can_fund_multiple_goals(client):
    headers = create_user_and_token(
        client, "goalwalletmany", "goalwalletmany@example.com", "Password123!"
    )
    wallet_id = _setup_premium_user_with_goal_wallet(client, headers, initial_balance=1_000_000)

    first = client.post(
        "/goals/",
        json={"title": "Desk", "target_amount": 400_000, "intent": "PLANNED_PURCHASE"},
        headers=headers,
    )
    second = client.post(
        "/goals/",
        json={"title": "Chair", "target_amount": 300_000, "intent": "PLANNED_PURCHASE"},
        headers=headers,
    )
    assert first.status_code == 201
    assert second.status_code == 201

    assert client.post(
        f"/goals/{first.json()['id']}/allocations",
        json={"allocations": [{"wallet_id": wallet_id, "amount": 400_000}]},
        headers=headers,
    ).status_code == 200
    assert client.post(
        f"/goals/{second.json()['id']}/allocations",
        json={"allocations": [{"wallet_id": wallet_id, "amount": 300_000}]},
        headers=headers,
    ).status_code == 200

    summary = client.get("/goals/funding-summary", headers=headers)
    assert summary.status_code == 200
    assert summary.json()["allocated_to_goals"] == 700_000
    assert summary.json()["available_for_goals"] == 300_000


def test_goal_allocation_rejects_when_wallet_available_is_insufficient(client):
    headers = create_user_and_token(
        client, "goaluser3", "goaluser3@example.com", "Password123!"
    )
    wallet_id = _setup_premium_user_with_goal_wallet(client, headers, initial_balance=200_000)

    created = client.post(
        "/goals/",
        json={"title": "Trip", "target_amount": 1_500_000},
        headers=headers,
    )
    assert created.status_code == 201
    goal_id = created.json()["id"]

    blocked = client.post(
        f"/goals/{goal_id}/allocations",
        json={"wallet_id": wallet_id, "amount": 300_000},
        headers=headers,
    )
    assert blocked.status_code == 400
    assert blocked.json()["detail"] == "goals.insufficient_wallet_available_for_goal"


def test_credit_limit_cannot_fund_goals_without_positive_balance(client):
    headers = create_user_and_token(
        client, "goaluser4", "goaluser4@example.com", "Password123!"
    )
    onboard = client.post(
        "/users/me/onboarding",
        json={
            "life_statuses": ["employed"],
            "wallets": [
                {
                    "name": "Credit",
                    "wallet_type": "CREDIT",
                    "accounting_type": "LIABILITY",
                    "initial_balance": 0,
                    "credit_limit": 1_000_000,
                    "can_fund_goals": True,
                }
            ],
        },
        headers=headers,
    )
    assert onboard.status_code == 200
    assert client.post("/users/me/toggle-premium", headers=headers).status_code == 200
    wallet = client.get("/wallets", headers=headers).json()[0]
    assert wallet["can_fund_goals"] is True

    created = client.post(
        "/goals/",
        json={"title": "Camera", "target_amount": 500_000},
        headers=headers,
    )
    goal_id = created.json()["id"]
    blocked = client.post(
        f"/goals/{goal_id}/allocations",
        json={"wallet_id": wallet["id"], "amount": 100_000},
        headers=headers,
    )
    assert blocked.status_code == 400
    assert blocked.json()["detail"] == "goals.insufficient_wallet_available_for_goal"


def test_goal_return_reduces_wallet_allocation_and_reopens_goal(client):
    headers = create_user_and_token(
        client, "goaluser5", "goaluser5@example.com", "Password123!"
    )
    wallet_id = _setup_premium_user_with_goal_wallet(client, headers)

    created = client.post(
        "/goals/",
        json={"title": "Emergency fund", "target_amount": 900_000},
        headers=headers,
    )
    goal_id = created.json()["id"]
    assert client.post(
        f"/goals/{goal_id}/allocations",
        json={"wallet_id": wallet_id, "amount": 900_000},
        headers=headers,
    ).status_code == 200

    returned = client.post(
        f"/goals/{goal_id}/allocations/return",
        json={"wallet_id": wallet_id, "amount": 300_000},
        headers=headers,
    )
    assert returned.status_code == 200
    payload = returned.json()
    assert payload["funded_amount"] == 600_000
    assert payload["remaining_amount"] == 300_000
    assert payload["status"] == "ACTIVE"

    summary = client.get("/goals/funding-summary", headers=headers)
    assert summary.status_code == 200
    assert summary.json()["allocated_to_goals"] == 600_000
    assert summary.json()["available_for_goals"] == 1_400_000


def test_goal_return_rejects_when_wallet_goal_balance_insufficient(client):
    headers = create_user_and_token(
        client, "goaluser6", "goaluser6@example.com", "Password123!"
    )
    wallet_id = _setup_premium_user_with_goal_wallet(client, headers)

    created = client.post(
        "/goals/",
        json={"title": "Console", "target_amount": 1_000_000},
        headers=headers,
    )
    goal_id = created.json()["id"]
    assert client.post(
        f"/goals/{goal_id}/allocations",
        json={"wallet_id": wallet_id, "amount": 200_000},
        headers=headers,
    ).status_code == 200

    blocked = client.post(
        f"/goals/{goal_id}/allocations/return",
        json={"wallet_id": wallet_id, "amount": 300_000},
        headers=headers,
    )
    assert blocked.status_code == 400
    assert blocked.json()["detail"] == "goals.insufficient_unreleased_balance"


def test_reserve_goal_consume_requires_and_accepts_real_event_link(client):
    headers = create_user_and_token(
        client, "goaluser7", "goaluser7@example.com", "Password123!"
    )
    wallet_id = _setup_premium_user_with_goal_wallet(client, headers)

    created = client.post(
        "/goals/",
        json={"title": "Phone", "target_amount": 1_000_000},
        headers=headers,
    )
    goal_id = created.json()["id"]
    assert client.post(
        f"/goals/{goal_id}/allocations",
        json={"wallet_id": wallet_id, "amount": 700_000},
        headers=headers,
    ).status_code == 200

    blocked = client.post(
        f"/goals/{goal_id}/allocations/consume",
        json={"wallet_id": wallet_id, "amount": 400_000},
        headers=headers,
    )
    assert blocked.status_code == 400
    assert blocked.json()["detail"] == "goals.reserve_consume_requires_real_event"

    _create_current_budget(client, headers, category="Electronics")
    expense = create_expense(
        client,
        headers,
        title="Emergency phone",
        amount=400_000,
        category="Electronics",
    )
    assert expense.status_code == 201

    consumed = client.post(
        f"/goals/{goal_id}/allocations/consume",
        json={
            "wallet_id": wallet_id,
            "amount": 400_000,
            "linked_event_id": expense.json()["id"],
        },
        headers=headers,
    )
    assert consumed.status_code == 200
    assert consumed.json()["funded_amount"] == 300_000
    assert consumed.json()["status"] == "ACTIVE"
    assert consumed.json()["linked_expense_event_id"] is None

    summary = client.get("/goals/funding-summary", headers=headers)
    assert summary.json()["allocated_to_goals"] == 300_000


def test_goals_routes_require_premium(client):
    headers = create_user_and_token(
        client, "goaluser8", "goaluser8@example.com", "Password123!"
    )

    listed = client.get("/goals/", headers=headers)
    assert listed.status_code == 403
    assert listed.json()["detail"] == "users.premium_required"

    created = client.post(
        "/goals/",
        json={"title": "Bike", "target_amount": 1_000_000},
        headers=headers,
    )
    assert created.status_code == 403
    assert created.json()["detail"] == "users.premium_required"


def test_update_goal_allows_title_target_date_intent_and_template_changes(client):
    headers = create_user_and_token(
        client, "goaluser9", "goaluser9@example.com", "Password123!"
    )
    _setup_premium_user_with_goal_wallet(client, headers)

    created = client.post(
        "/goals/",
        json={
            "title": "Bike",
            "target_amount": 1_000_000,
            "target_date": "2026-06-01",
            "intent": "PLANNED_PURCHASE",
        },
        headers=headers,
    )
    goal_id = created.json()["id"]

    updated = client.patch(
        f"/goals/{goal_id}",
        json={
            "title": "Road bike",
            "target_amount": 1_200_000,
            "target_date": "2026-07-01",
            "intent": "PLANNED_PURCHASE",
            "template": "vehicle",
        },
        headers=headers,
    )
    assert updated.status_code == 200
    payload = updated.json()
    assert payload["title"] == "Road bike"
    assert payload["target_amount"] == 1_200_000
    assert payload["target_date"] == "2026-07-01"
    assert payload["intent"] == "PLANNED_PURCHASE"
    assert payload["template"] == "vehicle"


def test_default_goal_intent_is_reserve_and_template_is_optional(client):
    headers = create_user_and_token(
        client, "goaluser15", "goaluser15@example.com", "Password123!"
    )
    _setup_premium_user_with_goal_wallet(client, headers)

    created = client.post(
        "/goals/",
        json={"title": "Safety", "target_amount": 1_000_000},
        headers=headers,
    )
    assert created.status_code == 201
    payload = created.json()
    assert payload["intent"] == "RESERVE"
    assert payload["template"] is None


def test_reserve_goal_reaching_target_stays_active(client):
    headers = create_user_and_token(
        client, "goaluser16", "goaluser16@example.com", "Password123!"
    )
    wallet_id = _setup_premium_user_with_goal_wallet(client, headers)

    created = client.post(
        "/goals/",
        json={
            "title": "Emergency",
            "target_amount": 500_000,
            "intent": "RESERVE",
            "template": "emergency_fund",
        },
        headers=headers,
    )
    assert created.status_code == 201
    goal_id = created.json()["id"]

    funded = client.post(
        f"/goals/{goal_id}/allocations",
        json={"wallet_id": wallet_id, "amount": 500_000},
        headers=headers,
    )
    assert funded.status_code == 200
    payload = funded.json()
    assert payload["funded_amount"] == 500_000
    assert payload["remaining_amount"] == 0
    assert payload["progress_percent"] == 100
    assert payload["status"] == "ACTIVE"


def test_reserve_goal_rejects_target_date_on_create_and_update(client):
    headers = create_user_and_token(
        client, "reservetarget", "reservetarget@example.com", "Password123!"
    )
    _setup_premium_user_with_goal_wallet(client, headers)
    today = user_timezone_today()

    created = client.post(
        "/goals/",
        json={
            "title": "Bad reserve",
            "target_amount": 500_000,
            "target_date": today.isoformat(),
            "intent": "RESERVE",
        },
        headers=headers,
    )
    assert created.status_code == 400, created.text
    assert created.json()["detail"] == "goals.reserve_target_date_not_allowed"

    good = client.post(
        "/goals/",
        json={"title": "Good reserve", "target_amount": 500_000, "intent": "RESERVE"},
        headers=headers,
    )
    assert good.status_code == 201, good.text
    goal_id = good.json()["id"]
    assert good.json()["target_date"] is None

    update = client.patch(
        f"/goals/{goal_id}",
        json={"target_date": today.isoformat()},
        headers=headers,
    )
    assert update.status_code == 400, update.text
    assert update.json()["detail"] == "goals.reserve_target_date_not_allowed"


def test_reserve_goal_rejects_direct_complete_status(client):
    headers = create_user_and_token(
        client, "reservenocomplete", "reservenocomplete@example.com", "Password123!"
    )
    _setup_premium_user_with_goal_wallet(client, headers)

    created = client.post(
        "/goals/",
        json={"title": "Never complete", "target_amount": 500_000, "intent": "RESERVE"},
        headers=headers,
    )
    assert created.status_code == 201, created.text
    goal_id = created.json()["id"]

    update = client.patch(
        f"/goals/{goal_id}",
        json={"status": "COMPLETED"},
        headers=headers,
    )
    assert update.status_code == 400, update.text
    assert update.json()["detail"] == "goals.reserve_cannot_complete"


def test_changing_intent_to_reserve_clears_target_date(client):
    headers = create_user_and_token(
        client, "changetoreserve", "changetoreserve@example.com", "Password123!"
    )
    _setup_premium_user_with_goal_wallet(client, headers)
    today = user_timezone_today()

    created = client.post(
        "/goals/",
        json={
            "title": "Will become reserve",
            "target_amount": 500_000,
            "target_date": today.isoformat(),
            "intent": "PLANNED_PURCHASE",
        },
        headers=headers,
    )
    assert created.status_code == 201, created.text
    goal_id = created.json()["id"]
    assert created.json()["target_date"] is not None

    update = client.patch(
        f"/goals/{goal_id}",
        json={"intent": "RESERVE"},
        headers=headers,
    )
    assert update.status_code == 200, update.text
    assert update.json()["intent"] == "RESERVE"
    assert update.json()["target_date"] is None


def test_planned_purchase_rejects_direct_complete_status(client):
    headers = create_user_and_token(
        client, "ppnocomplete", "ppnocomplete@example.com", "Password123!"
    )
    _setup_premium_user_with_goal_wallet(client, headers)

    created = client.post(
        "/goals/",
        json={"title": "New laptop", "target_amount": 800_000, "intent": "PLANNED_PURCHASE"},
        headers=headers,
    )
    assert created.status_code == 201, created.text
    goal_id = created.json()["id"]

    update = client.patch(
        f"/goals/{goal_id}",
        json={"status": "COMPLETED"},
        headers=headers,
    )
    assert update.status_code == 400, update.text
    assert update.json()["detail"] == "goals.planned_purchase_complete_via_purchase"


def test_old_goal_intents_are_rejected_by_api(client):
    headers = create_user_and_token(
        client, "goaluser17", "goaluser17@example.com", "Password123!"
    )
    _setup_premium_user_with_goal_wallet(client, headers)

    created = client.post(
        "/goals/",
        json={
            "title": "Old intent",
            "target_amount": 500_000,
            "intent": "PURCHASE_ASSET",
        },
        headers=headers,
    )
    assert created.status_code == 422


def test_goal_template_is_normalized_and_invalid_template_rejected(client):
    headers = create_user_and_token(
        client, "goaluser18", "goaluser18@example.com", "Password123!"
    )
    _setup_premium_user_with_goal_wallet(client, headers)

    created = client.post(
        "/goals/",
        json={
            "title": "Rainy day",
            "target_amount": 500_000,
            "intent": "RESERVE",
            "template": "Rainy Day",
        },
        headers=headers,
    )
    assert created.status_code == 201
    assert created.json()["template"] == "rainy_day"

    invalid = client.post(
        "/goals/",
        json={
            "title": "Bad tpl",
            "target_amount": 500_000,
            "intent": "RESERVE",
            "template": "bad/template",
        },
        headers=headers,
    )
    assert invalid.status_code == 422


def test_planned_purchase_generic_consume_is_blocked_even_with_real_event(client):
    headers = create_user_and_token(
        client, "goalpurchaseguard", "goalpurchaseguard@example.com", "Password123!"
    )
    _make_premium(client, headers)
    wallet_id = _create_wallet(client, headers, name="PurchaseGuard", initial_balance=2_000_000)
    _create_current_budget(client, headers)

    created = client.post(
        "/goals/",
        json={
            "title": "Camera",
            "target_amount": 1_000_000,
            "intent": "PLANNED_PURCHASE",
        },
        headers=headers,
    )
    assert created.status_code == 201
    goal_id = created.json()["id"]
    assert client.post(
        f"/goals/{goal_id}/allocations",
        json={"wallet_id": wallet_id, "amount": 1_000_000},
        headers=headers,
    ).status_code == 200

    expense = create_expense(
        client,
        headers,
        title="Camera buy",
        amount=1_000_000,
        category="Electronics",
    )
    assert expense.status_code == 201

    blocked = client.post(
        f"/goals/{goal_id}/allocations/consume",
        json={
            "wallet_id": wallet_id,
            "amount": 1_000_000,
            "linked_event_id": expense.json()["id"],
        },
        headers=headers,
    )
    assert blocked.status_code == 400
    assert blocked.json()["detail"] == "goals.planned_purchase_requires_record_purchase"


def test_planned_purchase_rejects_legacy_single_payment_wallet_field(client):
    headers = create_user_and_token(
        client, "goalpurchaselegacy", "goalpurchaselegacy@example.com", "Password123!"
    )
    _make_premium(client, headers)
    wallet_id = _create_wallet(client, headers, name="LegacyPay", initial_balance=2_000_000)
    _create_current_budget(client, headers)

    created = client.post(
        "/goals/",
        json={
            "title": "Legacy camera",
            "target_amount": 1_000_000,
            "intent": "PLANNED_PURCHASE",
        },
        headers=headers,
    )
    goal_id = created.json()["id"]
    assert client.post(
        f"/goals/{goal_id}/allocations",
        json={"wallet_id": wallet_id, "amount": 1_000_000},
        headers=headers,
    ).status_code == 200

    blocked = client.post(
        f"/goals/{goal_id}/record-purchase",
        json={
            "amount": 1_000_000,
            "payment_wallet_id": wallet_id,
            "category": "Electronics",
            "date": user_timezone_today().isoformat(),
            "settlement_mode": "DIRECT",
        },
        headers=headers,
    )
    assert blocked.status_code == 422


def test_planned_purchase_direct_settlement_creates_expense_asset_and_consumes_goal_funding(client):
    headers = create_user_and_token(
        client, "goaluse1", "goaluse1@example.com", "Password123!"
    )
    _make_premium(client, headers)
    wallet_id = _create_wallet(client, headers, name="SaveBuy", initial_balance=2_000_000)
    _create_current_budget(client, headers)

    created = client.post(
        "/goals/",
        json={
            "title": "Laptop",
            "target_amount": 1_000_000,
            "intent": "PLANNED_PURCHASE",
            "template": "laptop_phone",
        },
        headers=headers,
    )
    goal_id = created.json()["id"]
    assert client.post(
        f"/goals/{goal_id}/allocations",
        json={"wallet_id": wallet_id, "amount": 1_000_000},
        headers=headers,
    ).status_code == 200

    used = client.post(
        f"/goals/{goal_id}/record-purchase",
        json={
            "amount": 1_000_000,
            "payment_allocations": [{"wallet_id": wallet_id, "amount": 1_000_000}],
            "category": "Electronics",
            "date": user_timezone_today().isoformat(),
            "settlement_mode": "DIRECT",
            "result_type": "ASSET_PURCHASE",
            "asset_title": "Laptop Asset",
        },
        headers=headers,
    )
    assert used.status_code == 200
    payload = used.json()
    assert payload["consumed_amount"] == 1_000_000
    assert payload["outside_goal_amount"] == 0
    assert payload["asset_id"] is not None
    assert payload["goal"]["status"] == "COMPLETED"
    assert payload["goal"]["funded_amount"] == 0
    assert _wallet_by_id(client, headers, wallet_id)["current_balance"] == 1_000_000


def test_planned_purchase_down_payment_creates_payment_plan_and_next_goal(client, session):
    headers = create_user_and_token(
        client, "goaldownplan", "goaldownplan@example.com", "Password123!"
    )
    _make_premium(client, headers)
    wallet_id = _create_wallet(client, headers, name="DownPaySave", initial_balance=2_000_000)
    _create_current_budget(client, headers)

    created = client.post(
        "/goals/",
        json={
            "title": "Laptop down payment",
            "target_amount": 400_000,
            "intent": "PLANNED_PURCHASE",
        },
        headers=headers,
    )
    assert created.status_code == 201, created.text
    goal_id = created.json()["id"]
    assert client.post(
        f"/goals/{goal_id}/allocations",
        json={"wallet_id": wallet_id, "amount": 400_000},
        headers=headers,
    ).status_code == 200

    used = client.post(
        f"/goals/{goal_id}/record-purchase",
        json={
            "amount": 400_000,
            "payment_allocations": [{"wallet_id": wallet_id, "amount": 400_000}],
            "category": "Electronics",
            "date": user_timezone_today().isoformat(),
            "settlement_mode": "DIRECT",
            "result_type": "ASSET_PURCHASE",
            "asset_title": "Laptop Asset",
            "payment_plan": {
                "total_price": 1_000_000,
                "item_name": "Laptop",
                "store_or_bank_name": "Tech Store",
                "months": 3,
                "frequency": "MONTHLY",
                "create_next_payment_goal": True,
            },
        },
        headers=headers,
    )
    assert used.status_code == 200, used.text
    payload = used.json()
    plan = payload["payment_plan"]
    next_goal = payload["next_payment_goal"]
    assert payload["consumed_amount"] == 400_000
    assert payload["goal"]["status"] == "COMPLETED"
    assert payload["goal"]["linked_payment_plan_id"] == plan["id"]
    assert payload["asset_id"] is not None
    assert plan["total_price"] == 1_000_000
    assert plan["down_payment"] == 400_000
    assert plan["remaining_amount"] == 600_000
    assert plan["debt_id"] is None
    assert len(plan["payments"]) == 3
    assert {payment["amount"] for payment in plan["payments"]} == {200_000}
    assert next_goal["intent"] == "PAY_OBLIGATION"
    assert next_goal["linked_debt_id"] is None
    assert next_goal["linked_payment_plan_id"] == plan["id"]
    assert next_goal["target_amount"] == 200_000
    assert next_goal["payment_plan_target"]["payment_number"] == 1

    event = session.get(models.FinancialEvent, payload["expense_event_id"])
    assert event.reference_type == models.ReferenceType.GOAL_PLANNED_PURCHASE
    assert event.entity_legs[0].payment_plan_id == plan["id"]
    assert event.entity_legs[0].amount == 400_000
    duplicate_down_payment_events = session.query(models.FinancialEvent).filter(
        models.FinancialEvent.reference_type == models.ReferenceType.PAYMENT_PLAN_DOWN_PAYMENT,
        models.FinancialEvent.owner_id == event.owner_id,
    ).count()
    assert duplicate_down_payment_events == 0

    plan_record = session.get(models.PaymentPlan, plan["id"])
    assert plan_record.remaining_amount == 600_000
    asset = session.get(models.Asset, payload["asset_id"])
    assert asset.purchase_value == 1_000_000
    assert _wallet_by_id(client, headers, wallet_id)["current_balance"] == 1_600_000


def test_planned_purchase_payment_plan_bridge_rejects_total_not_above_down_payment(client):
    headers = create_user_and_token(
        client, "goaldownbad", "goaldownbad@example.com", "Password123!"
    )
    _make_premium(client, headers)
    wallet_id = _create_wallet(client, headers, name="DownBadSave", initial_balance=2_000_000)
    _create_current_budget(client, headers)

    created = client.post(
        "/goals/",
        json={"title": "Phone down", "target_amount": 400_000, "intent": "PLANNED_PURCHASE"},
        headers=headers,
    )
    goal_id = created.json()["id"]
    assert client.post(
        f"/goals/{goal_id}/allocations",
        json={"wallet_id": wallet_id, "amount": 400_000},
        headers=headers,
    ).status_code == 200

    blocked = client.post(
        f"/goals/{goal_id}/record-purchase",
        json={
            "amount": 400_000,
            "payment_allocations": [{"wallet_id": wallet_id, "amount": 400_000}],
            "category": "Electronics",
            "date": user_timezone_today().isoformat(),
            "settlement_mode": "DIRECT",
            "payment_plan": {
                "total_price": 400_000,
                "item_name": "Phone",
                "months": 3,
            },
        },
        headers=headers,
    )
    assert blocked.status_code == 422
    assert "goals.payment_plan_total_must_exceed_down_payment" in blocked.text


def test_planned_purchase_rejects_second_purchase(client):
    headers = create_user_and_token(
        client, "goalsecondpurchase", "goalsecondpurchase@example.com", "Password123!"
    )
    _make_premium(client, headers)
    wallet_id = _create_wallet(client, headers, name="OnePurchase", initial_balance=2_000_000)
    _create_current_budget(client, headers)

    created = client.post(
        "/goals/",
        json={"title": "Console", "target_amount": 1_000_000, "intent": "PLANNED_PURCHASE"},
        headers=headers,
    )
    goal_id = created.json()["id"]
    assert client.post(
        f"/goals/{goal_id}/allocations",
        json={"wallet_id": wallet_id, "amount": 1_000_000},
        headers=headers,
    ).status_code == 200

    payload = {
        "amount": 1_000_000,
        "payment_allocations": [{"wallet_id": wallet_id, "amount": 1_000_000}],
        "category": "Electronics",
        "date": user_timezone_today().isoformat(),
        "settlement_mode": "DIRECT",
    }
    first = client.post(f"/goals/{goal_id}/record-purchase", json=payload, headers=headers)
    assert first.status_code == 200

    second = client.post(f"/goals/{goal_id}/record-purchase", json=payload, headers=headers)
    assert second.status_code == 400
    assert second.json()["detail"] == "goals.purchase_already_recorded"


def test_goal_created_expenses_reject_future_dates(client):
    headers = create_user_and_token(
        client, "goalfuturedate", "goalfuturedate@example.com", "Password123!"
    )
    _make_premium(client, headers)
    wallet_id = _create_wallet(client, headers, name="FutureGuard", initial_balance=2_000_000)
    _create_current_budget(client, headers, category="Electronics")
    _create_current_budget(client, headers, category="Health")

    future_date = (user_timezone_today() + timedelta(days=1)).isoformat()

    purchase_goal = client.post(
        "/goals/",
        json={"title": "Speaker", "target_amount": 1_000_000, "intent": "PLANNED_PURCHASE"},
        headers=headers,
    )
    assert purchase_goal.status_code == 201
    purchase_goal_id = purchase_goal.json()["id"]
    assert client.post(
        f"/goals/{purchase_goal_id}/allocations",
        json={"wallet_id": wallet_id, "amount": 1_000_000},
        headers=headers,
    ).status_code == 200

    purchase = client.post(
        f"/goals/{purchase_goal_id}/record-purchase",
        json={
            "amount": 1_000_000,
            "payment_allocations": [{"wallet_id": wallet_id, "amount": 1_000_000}],
            "category": "Electronics",
            "date": future_date,
            "settlement_mode": "DIRECT",
        },
        headers=headers,
    )
    assert purchase.status_code == 400
    assert purchase.json()["detail"] == "expenses.date_in_future"

    reserve_goal = client.post(
        "/goals/",
        json={"title": "Medical", "target_amount": 500_000, "intent": "RESERVE"},
        headers=headers,
    )
    assert reserve_goal.status_code == 201
    reserve_goal_id = reserve_goal.json()["id"]
    assert client.post(
        f"/goals/{reserve_goal_id}/allocations",
        json={"wallet_id": wallet_id, "amount": 500_000},
        headers=headers,
    ).status_code == 200

    reserve_use = client.post(
        f"/goals/{reserve_goal_id}/use-reserve",
        json={
            "amount": 100_000,
            "payment_allocations": [{"wallet_id": wallet_id, "amount": 100_000}],
            "category": "Health",
            "date": future_date,
            "settlement_mode": "DIRECT",
        },
        headers=headers,
    )
    assert reserve_use.status_code == 400
    assert reserve_use.json()["detail"] == "expenses.date_in_future"


def test_planned_purchase_is_categorized_but_excluded_from_normal_monthly_budget(client, session):
    headers = create_user_and_token(
        client, "goalbudgetimpact", "goalbudgetimpact@example.com", "Password123!"
    )
    _make_premium(client, headers)
    today = user_timezone_today()
    budget = create_budget(
        client,
        headers,
        category="Electronics",
        monthly_limit=500_000,
        budget_year=today.year,
        budget_month=today.month,
    )
    assert budget.status_code == 201
    subcategory = client.post(
        f"/budgets/{budget.json()['id']}/subcategories",
        json={"category": "Electronics", "name": "Laptops", "monthly_limit": 100_000},
        headers=headers,
    )
    assert subcategory.status_code == 201

    normal = create_expense(
        client,
        headers,
        title="Mouse",
        amount=300_000,
        category="Electronics",
        expense_date=today,
    )
    assert normal.status_code == 201

    savings_id = _create_wallet(client, headers, name="LaptopFund", initial_balance=2_000_000)
    goal = client.post(
        "/goals/",
        json={"title": "Laptop", "target_amount": 1_000_000, "intent": "PLANNED_PURCHASE"},
        headers=headers,
    )
    assert goal.status_code == 201
    goal_id = goal.json()["id"]
    assert client.post(
        f"/goals/{goal_id}/allocations",
        json={"wallet_id": savings_id, "amount": 1_000_000},
        headers=headers,
    ).status_code == 200

    purchase = client.post(
        f"/goals/{goal_id}/record-purchase",
        json={
            "amount": 1_000_000,
            "payment_allocations": [{"wallet_id": savings_id, "amount": 1_000_000}],
            "category": "Electronics",
            "subcategory_id": subcategory.json()["id"],
            "date": today.isoformat(),
            "settlement_mode": "DIRECT",
        },
        headers=headers,
    )
    assert purchase.status_code == 200

    event = session.get(models.FinancialEvent, purchase.json()["expense_event_id"])
    assert event.reference_type == models.ReferenceType.GOAL_PLANNED_PURCHASE
    assert event.entity_legs[0].category == models.ExpenseCategory.ELECTRONICS
    assert event.entity_legs[0].subcategory_id == subcategory.json()["id"]
    assert event.entity_legs[0].budget_id is None

    budget_after = client.get(
        f"/budgets/item?budget_year={today.year}&budget_month={today.month}&category=Electronics",
        headers=headers,
    )
    assert budget_after.status_code == 200
    assert budget_after.json()["spent"] == 300_000
    assert budget_after.json()["remaining"] == 200_000

    detail = client.get(
        f"/budgets/item/detail?budget_year={today.year}&budget_month={today.month}&category=Electronics",
        headers=headers,
    )
    assert detail.status_code == 200
    assert detail.json()["expense_count"] == 1
    assert [item["title"] for item in detail.json()["recent_activity"]] == ["Mouse"]
    assert detail.json()["subcategories"][0]["spent"] == 0


def test_planned_purchase_goal_backed_off_wallet_is_excluded_from_normal_monthly_budget(client):
    headers = create_user_and_token(
        client, "goalbudgetoutside", "goalbudgetoutside@example.com", "Password123!"
    )
    _make_premium(client, headers)
    today = user_timezone_today()
    budget = create_budget(
        client,
        headers,
        category="Electronics",
        monthly_limit=500_000,
        budget_year=today.year,
        budget_month=today.month,
    )
    assert budget.status_code == 201

    normal = create_expense(
        client,
        headers,
        title="Mouse",
        amount=300_000,
        category="Electronics",
        expense_date=today,
    )
    assert normal.status_code == 201

    savings_id = _create_wallet(client, headers, name="OutsideSavings", initial_balance=1_000_000)
    debit_id = _create_wallet(
        client,
        headers,
        name="OutsideDebit",
        wallet_type="DEBIT",
        initial_balance=1_000_000,
        can_fund_goals=False,
    )
    goal = client.post(
        "/goals/",
        json={"title": "Laptop outside", "target_amount": 1_000_000, "intent": "PLANNED_PURCHASE"},
        headers=headers,
    )
    assert goal.status_code == 201
    goal_id = goal.json()["id"]
    assert client.post(
        f"/goals/{goal_id}/allocations",
        json={"wallet_id": savings_id, "amount": 1_000_000},
        headers=headers,
    ).status_code == 200

    purchase = client.post(
        f"/goals/{goal_id}/record-purchase",
        json={
            "amount": 1_000_000,
            "payment_allocations": [{"wallet_id": debit_id, "amount": 1_000_000}],
            "category": "Electronics",
            "date": today.isoformat(),
            "settlement_mode": "GOAL_BACKED_OFF_WALLET_PAYMENT",
        },
        headers=headers,
    )
    assert purchase.status_code == 200

    budget_after = client.get(
        f"/budgets/item?budget_year={today.year}&budget_month={today.month}&category=Electronics",
        headers=headers,
    )
    assert budget_after.status_code == 200
    assert budget_after.json()["spent"] == 300_000
    assert budget_after.json()["remaining"] == 200_000


def test_unplanned_purchase_still_counts_against_monthly_budget_without_blocking_save(client):
    headers = create_user_and_token(
        client, "goalbudgetnormal", "goalbudgetnormal@example.com", "Password123!"
    )
    today = user_timezone_today()
    create_budget(
        client,
        headers,
        category="Electronics",
        monthly_limit=500_000,
        budget_year=today.year,
        budget_month=today.month,
    )

    saved = create_expense(
        client,
        headers,
        title="Laptop",
        amount=600_000,
        category="Electronics",
        expense_date=today,
    )
    assert saved.status_code == 201, saved.text

    budget_after = client.get(
        f"/budgets/item?budget_year={today.year}&budget_month={today.month}&category=Electronics",
        headers=headers,
    )
    assert budget_after.status_code == 200, budget_after.text
    assert budget_after.json()["spent"] == 600_000
    assert budget_after.json()["remaining"] == -100_000
    assert budget_after.json()["is_over_limit"] is True


def test_planned_purchase_lower_price_requires_target_adjustment_and_releases_leftover(client):
    headers = create_user_and_token(
        client, "goaluse1b", "goaluse1b@example.com", "Password123!"
    )
    _make_premium(client, headers)
    wallet_id = _create_wallet(client, headers, name="LowerPrice", initial_balance=2_000_000)
    _create_current_budget(client, headers)

    created = client.post(
        "/goals/",
        json={
            "title": "Discount phone",
            "target_amount": 1_000_000,
            "intent": "PLANNED_PURCHASE",
            "template": "laptop_phone",
        },
        headers=headers,
    )
    goal_id = created.json()["id"]
    assert client.post(
        f"/goals/{goal_id}/allocations",
        json={"wallet_id": wallet_id, "amount": 1_000_000},
        headers=headers,
    ).status_code == 200

    blocked = client.post(
        f"/goals/{goal_id}/record-purchase",
        json={
            "amount": 800_000,
            "payment_allocations": [{"wallet_id": wallet_id, "amount": 800_000}],
            "category": "Electronics",
            "date": user_timezone_today().isoformat(),
            "settlement_mode": "DIRECT",
            "result_type": "EXPENSE_ONLY",
        },
        headers=headers,
    )
    assert blocked.status_code == 400
    assert blocked.json()["detail"] == "goals.purchase_target_adjustment_required"

    used = client.post(
        f"/goals/{goal_id}/record-purchase",
        json={
            "amount": 800_000,
            "payment_allocations": [{"wallet_id": wallet_id, "amount": 800_000}],
            "category": "Electronics",
            "date": user_timezone_today().isoformat(),
            "settlement_mode": "DIRECT",
            "result_type": "EXPENSE_ONLY",
            "adjust_target_to_purchase_amount": True,
        },
        headers=headers,
    )
    assert used.status_code == 200
    payload = used.json()
    assert payload["consumed_amount"] == 800_000
    assert payload["released_amount"] == 200_000
    assert payload["outside_goal_amount"] == 0
    assert payload["goal"]["status"] == "COMPLETED"
    assert payload["goal"]["target_amount"] == 800_000
    assert payload["goal"]["funded_amount"] == 0
    assert payload["goal"]["unreleased_amount"] == 0
    assert _wallet_by_id(client, headers, wallet_id)["current_balance"] == 1_200_000


def test_planned_purchase_goal_backed_off_wallet_consumes_funding_and_completes_goal(client, session):
    headers = create_user_and_token(
        client, "goaluse2", "goaluse2@example.com", "Password123!"
    )
    _make_premium(client, headers)
    savings_id = _create_wallet(client, headers, name="GoalSave", initial_balance=1_000_000)
    debit_id = _create_wallet(
        client,
        headers,
        name="PayCard",
        wallet_type="DEBIT",
        initial_balance=1_000_000,
        can_fund_goals=False,
    )
    _create_current_budget(client, headers)

    goal = client.post(
        "/goals/",
        json={"title": "Camera", "target_amount": 1_000_000, "intent": "PLANNED_PURCHASE"},
        headers=headers,
    )
    goal_id = goal.json()["id"]
    assert client.post(
        f"/goals/{goal_id}/allocations",
        json={"wallet_id": savings_id, "amount": 1_000_000},
        headers=headers,
    ).status_code == 200

    used = client.post(
        f"/goals/{goal_id}/record-purchase",
        json={
            "amount": 1_000_000,
            "payment_allocations": [{"wallet_id": debit_id, "amount": 1_000_000}],
            "category": "Electronics",
            "date": user_timezone_today().isoformat(),
            "settlement_mode": "GOAL_BACKED_OFF_WALLET_PAYMENT",
        },
        headers=headers,
    )
    assert used.status_code == 200
    payload = used.json()
    assert payload["consumed_amount"] == 1_000_000
    assert payload["goal"]["status"] == "COMPLETED"
    assert payload["transfer_event_ids"] == []
    assert _wallet_by_id(client, headers, savings_id)["current_balance"] == 1_000_000
    assert _wallet_by_id(client, headers, debit_id)["current_balance"] == 0

    event = session.get(models.FinancialEvent, payload["expense_event_id"])
    assert event.reference_type == models.ReferenceType.GOAL_PLANNED_PURCHASE


def test_planned_purchase_goal_backed_off_wallet_two_payment_wallets(client, session):
    headers = create_user_and_token(
        client, "goaluse2multi", "goaluse2multi@example.com", "Password123!"
    )
    _make_premium(client, headers)
    savings_id = _create_wallet(client, headers, name="FridgeSavings", initial_balance=1_000_000)
    cash_id = _create_wallet(
        client,
        headers,
        name="FridgeCash",
        wallet_type="CASH",
        initial_balance=1_000_000,
        can_fund_goals=False,
    )
    debit_id = _create_wallet(
        client,
        headers,
        name="FridgeCard",
        wallet_type="DEBIT",
        initial_balance=1_000_000,
        can_fund_goals=False,
    )
    _create_current_budget(client, headers, category="Housing")

    goal = client.post(
        "/goals/",
        json={"title": "Fridge", "target_amount": 1_000_000, "intent": "PLANNED_PURCHASE"},
        headers=headers,
    )
    goal_id = goal.json()["id"]
    assert client.post(
        f"/goals/{goal_id}/allocations",
        json={"wallet_id": savings_id, "amount": 1_000_000},
        headers=headers,
    ).status_code == 200

    used = client.post(
        f"/goals/{goal_id}/record-purchase",
        json={
            "amount": 1_000_000,
            "payment_allocations": [
                {"wallet_id": cash_id, "amount": 400_000},
                {"wallet_id": debit_id, "amount": 600_000},
            ],
            "category": "Housing",
            "date": user_timezone_today().isoformat(),
            "settlement_mode": "GOAL_BACKED_OFF_WALLET_PAYMENT",
        },
        headers=headers,
    )
    assert used.status_code == 200
    payload = used.json()
    assert payload["consumed_amount"] == 1_000_000
    assert payload["transfer_event_ids"] == []
    assert _wallet_by_id(client, headers, savings_id)["current_balance"] == 1_000_000
    assert _wallet_by_id(client, headers, cash_id)["current_balance"] == 600_000
    assert _wallet_by_id(client, headers, debit_id)["current_balance"] == 400_000

    event = session.get(models.FinancialEvent, payload["expense_event_id"])
    assert event is not None
    wallet_legs = sorted((leg.wallet_id, leg.amount) for leg in event.wallet_legs)
    assert wallet_legs == sorted([(cash_id, -400_000), (debit_id, -600_000)])
    entity_total = sum(int(leg.amount) for leg in event.entity_legs)
    assert entity_total == 1_000_000


def test_planned_purchase_rejects_more_than_three_payment_wallets(client):
    headers = create_user_and_token(
        client, "goaluse2toomany", "goaluse2toomany@example.com", "Password123!"
    )
    _make_premium(client, headers)
    savings_id = _create_wallet(client, headers, name="TooManySavings", initial_balance=1_000_000)
    wallet_ids = [
        _create_wallet(
            client,
            headers,
            name=f"TooManyPay{index}",
            wallet_type="DEBIT",
            initial_balance=250_000,
            can_fund_goals=False,
        )
        for index in range(4)
    ]
    _create_current_budget(client, headers)

    goal = client.post(
        "/goals/",
        json={"title": "Too many split", "target_amount": 1_000_000, "intent": "PLANNED_PURCHASE"},
        headers=headers,
    )
    goal_id = goal.json()["id"]
    assert client.post(
        f"/goals/{goal_id}/allocations",
        json={"wallet_id": savings_id, "amount": 1_000_000},
        headers=headers,
    ).status_code == 200

    blocked = client.post(
        f"/goals/{goal_id}/record-purchase",
        json={
            "amount": 1_000_000,
            "payment_allocations": [
                {"wallet_id": wallet_id, "amount": 250_000}
                for wallet_id in wallet_ids
            ],
            "category": "Electronics",
            "date": user_timezone_today().isoformat(),
            "settlement_mode": "GOAL_BACKED_OFF_WALLET_PAYMENT",
        },
        headers=headers,
    )
    assert blocked.status_code == 400
    assert blocked.json()["detail"] == "goals.payment_allocation_limit_exceeded"


def test_planned_purchase_goal_backed_off_wallet_allows_credit_card_truthfully(client):
    headers = create_user_and_token(
        client, "goaluse2credit", "goaluse2credit@example.com", "Password123!"
    )
    _make_premium(client, headers)
    savings_id = _create_wallet(client, headers, name="CreditOutsideSavings", initial_balance=1_000_000)
    credit = client.post(
        "/wallets",
        json={
            "name": "Credit checkout",
            "wallet_type": "CREDIT",
            "accounting_type": "LIABILITY",
            "initial_balance": 0,
            "credit_limit": 2_000_000,
            "can_fund_goals": False,
        },
        headers=headers,
    )
    assert credit.status_code == 201, credit.text
    credit_id = credit.json()["id"]
    _create_current_budget(client, headers)

    goal = client.post(
        "/goals/",
        json={"title": "Credit camera", "target_amount": 1_000_000, "intent": "PLANNED_PURCHASE"},
        headers=headers,
    )
    goal_id = goal.json()["id"]
    assert client.post(
        f"/goals/{goal_id}/allocations",
        json={"wallet_id": savings_id, "amount": 1_000_000},
        headers=headers,
    ).status_code == 200

    used = client.post(
        f"/goals/{goal_id}/record-purchase",
        json={
            "amount": 1_000_000,
            "payment_allocations": [{"wallet_id": credit_id, "amount": 1_000_000}],
            "category": "Electronics",
            "date": user_timezone_today().isoformat(),
            "settlement_mode": "GOAL_BACKED_OFF_WALLET_PAYMENT",
        },
        headers=headers,
    )
    assert used.status_code == 200, used.text
    payload = used.json()
    assert payload["consumed_amount"] == 1_000_000
    assert _wallet_by_id(client, headers, savings_id)["current_balance"] == 1_000_000
    assert _wallet_by_id(client, headers, credit_id)["current_balance"] == -1_000_000


def test_planned_purchase_goal_funded_rejects_credit_card_even_if_legacy_allocation_exists(client, session):
    email = "goaluse2creditbad@example.com"
    headers = create_user_and_token(
        client, "goaluse2creditbad", email, "Password123!"
    )
    _make_premium(client, headers)
    credit = client.post(
        "/wallets",
        json={
            "name": "Legacy credit goal source",
            "wallet_type": "CREDIT",
            "accounting_type": "LIABILITY",
            "initial_balance": 0,
            "credit_limit": 2_000_000,
            "can_fund_goals": False,
        },
        headers=headers,
    )
    assert credit.status_code == 201, credit.text
    credit_id = credit.json()["id"]
    _create_current_budget(client, headers)

    goal = client.post(
        "/goals/",
        json={"title": "Bad credit funding", "target_amount": 1_000_000, "intent": "PLANNED_PURCHASE"},
        headers=headers,
    )
    goal_id = goal.json()["id"]
    user = session.query(models.User).filter(models.User.email == email).one()
    session.add(
        models.GoalContributions(
            owner_id=user.id,
            goal_id=goal_id,
            wallet_id=credit_id,
            amount=1_000_000,
            contribution_type=models.GoalContributionType.ALLOCATE,
        )
    )
    session.commit()

    blocked = client.post(
        f"/goals/{goal_id}/record-purchase",
        json={
            "amount": 1_000_000,
            "payment_allocations": [{"wallet_id": credit_id, "amount": 1_000_000}],
            "category": "Electronics",
            "date": user_timezone_today().isoformat(),
            "settlement_mode": "DIRECT",
        },
        headers=headers,
    )
    assert blocked.status_code == 400
    assert blocked.json()["detail"] == "goals.goal_funded_payment_wallet_must_be_owned_money"


def test_planned_purchase_goal_backed_off_wallet_releases_leftover_multi_wallet(client):
    headers = create_user_and_token(
        client, "goaluse2matrix", "goaluse2matrix@example.com", "Password123!"
    )
    _make_premium(client, headers)
    savings_id = _create_wallet(client, headers, name="MatrixSavings", initial_balance=1_000_000)
    cash_id = _create_wallet(client, headers, name="MatrixCash", wallet_type="CASH", initial_balance=1_000_000)
    debit_one_id = _create_wallet(
        client,
        headers,
        name="MatrixDebitOne",
        wallet_type="DEBIT",
        initial_balance=1_000_000,
        can_fund_goals=False,
    )
    debit_two_id = _create_wallet(
        client,
        headers,
        name="MatrixDebitTwo",
        wallet_type="DEBIT",
        initial_balance=1_000_000,
        can_fund_goals=False,
    )
    _create_current_budget(client, headers, category="Electronics")

    goal = client.post(
        "/goals/",
        json={"title": "Camera kit", "target_amount": 1_000_000, "intent": "PLANNED_PURCHASE"},
        headers=headers,
    )
    goal_id = goal.json()["id"]
    assert client.post(
        f"/goals/{goal_id}/allocations",
        json={"wallet_id": savings_id, "amount": 700_000},
        headers=headers,
    ).status_code == 200
    assert client.post(
        f"/goals/{goal_id}/allocations",
        json={"wallet_id": cash_id, "amount": 300_000},
        headers=headers,
    ).status_code == 200

    used = client.post(
        f"/goals/{goal_id}/record-purchase",
        json={
            "amount": 1_000_000,
            "payment_allocations": [
                {"wallet_id": debit_one_id, "amount": 200_000},
                {"wallet_id": debit_two_id, "amount": 800_000},
            ],
            "category": "Electronics",
            "date": user_timezone_today().isoformat(),
            "settlement_mode": "GOAL_BACKED_OFF_WALLET_PAYMENT",
        },
        headers=headers,
    )
    assert used.status_code == 200
    payload = used.json()
    assert payload["consumed_amount"] == 1_000_000
    assert payload["transfer_event_ids"] == []
    assert _wallet_by_id(client, headers, savings_id)["current_balance"] == 1_000_000
    assert _wallet_by_id(client, headers, cash_id)["current_balance"] == 1_000_000
    assert _wallet_by_id(client, headers, debit_one_id)["current_balance"] == 800_000
    assert _wallet_by_id(client, headers, debit_two_id)["current_balance"] == 200_000


def test_planned_purchase_off_wallet_rejects_goal_funding_payment_wallet(client):
    headers = create_user_and_token(
        client, "goaluse2outsidebad", "goaluse2outsidebad@example.com", "Password123!"
    )
    _make_premium(client, headers)
    savings_id = _create_wallet(client, headers, name="OutsideBadSavings", initial_balance=1_000_000)
    _create_current_budget(client, headers)

    goal = client.post(
        "/goals/",
        json={"title": "Camera outside bad", "target_amount": 1_000_000, "intent": "PLANNED_PURCHASE"},
        headers=headers,
    )
    goal_id = goal.json()["id"]
    assert client.post(
        f"/goals/{goal_id}/allocations",
        json={"wallet_id": savings_id, "amount": 1_000_000},
        headers=headers,
    ).status_code == 200

    blocked = client.post(
        f"/goals/{goal_id}/record-purchase",
        json={
            "amount": 1_000_000,
            "payment_allocations": [{"wallet_id": savings_id, "amount": 1_000_000}],
            "category": "Electronics",
            "date": user_timezone_today().isoformat(),
            "settlement_mode": "GOAL_BACKED_OFF_WALLET_PAYMENT",
        },
        headers=headers,
    )
    assert blocked.status_code == 400
    assert blocked.json()["detail"] == "goals.goal_backed_off_wallet_requires_non_funding_wallet"
    assert _wallet_by_id(client, headers, savings_id)["current_balance"] == 1_000_000


def test_move_goal_funding_transfers_money_and_moves_only_selected_goal_label(client, session):
    headers = create_user_and_token(
        client, "goalmove1", "goalmove1@example.com", "Password123!"
    )
    _make_premium(client, headers)
    source_id = _create_wallet(client, headers, name="MoveSavings", initial_balance=2_000_000)
    target_id = _create_wallet(
        client,
        headers,
        name="MoveDebit",
        wallet_type="DEBIT",
        initial_balance=0,
        can_fund_goals=True,
    )

    emergency = client.post(
        "/goals/",
        json={"title": "Emergency", "target_amount": 500_000, "intent": "RESERVE"},
        headers=headers,
    )
    emergency_id = emergency.json()["id"]
    assert client.post(
        f"/goals/{emergency_id}/allocations",
        json={"wallet_id": source_id, "amount": 500_000},
        headers=headers,
    ).status_code == 200

    laptop = client.post(
        "/goals/",
        json={"title": "Laptop move", "target_amount": 1_000_000, "intent": "PLANNED_PURCHASE"},
        headers=headers,
    )
    laptop_id = laptop.json()["id"]
    assert client.post(
        f"/goals/{laptop_id}/allocations",
        json={"wallet_id": source_id, "amount": 1_000_000},
        headers=headers,
    ).status_code == 200

    moved = client.post(
        f"/goals/{laptop_id}/allocations/move",
        json={
            "source_wallet_id": source_id,
            "target_wallet_id": target_id,
            "amount": 600_000,
            "date": user_timezone_today().isoformat(),
            "note": "prepare card payment",
        },
        headers=headers,
    )
    assert moved.status_code == 200, moved.text
    assert moved.json()["moved_amount"] == 600_000

    session.expire_all()
    source_wallet = session.query(models.Wallet).filter(models.Wallet.id == source_id).first()
    owner_id = source_wallet.owner_id
    assert _wallet_by_id(client, headers, source_id)["current_balance"] == 1_400_000
    assert _wallet_by_id(client, headers, target_id)["current_balance"] == 600_000
    assert get_goal_wallet_funded_amount(session, owner_id, emergency_id, source_id) == 500_000
    assert get_goal_wallet_funded_amount(session, owner_id, laptop_id, source_id) == 400_000
    assert get_goal_wallet_funded_amount(session, owner_id, laptop_id, target_id) == 600_000


def test_fund_project_goal_cannot_prepare_payment_directly(client, session):
    headers = create_user_and_token(
        client, "fundprojectnoprep", "fundprojectnoprep@example.com", "Password123!"
    )
    _make_premium(client, headers)
    source_id = _create_wallet(client, headers, name="ProjectIncubator", initial_balance=1_000_000)
    target_id = _create_wallet(
        client,
        headers,
        name="ProjectCheckout",
        wallet_type="DEBIT",
        initial_balance=0,
        can_fund_goals=False,
    )

    user = session.query(models.User).filter(models.User.email == "fundprojectnoprep@example.com").first()
    goal = models.Goals(
        owner_id=user.id,
        title="Kitchen remodel",
        target_amount=1_000_000,
        intent=models.GoalIntent.FUND_PROJECT,
        status=models.GoalStatus.ACTIVE,
    )
    session.add(goal)
    session.commit()
    goal_id = goal.id
    assert client.post(
        f"/goals/{goal_id}/allocations",
        json={"wallet_id": source_id, "amount": 1_000_000},
        headers=headers,
    ).status_code == 200

    blocked = client.post(
        f"/goals/{goal_id}/allocations/move",
        json={
            "source_wallet_id": source_id,
            "target_wallet_id": target_id,
            "amount": 500_000,
            "date": user_timezone_today().isoformat(),
        },
        headers=headers,
    )
    assert blocked.status_code == 400
    assert blocked.json()["detail"] == "goals.prepare_payment_intent_not_supported"

    session.expire_all()
    source_wallet = session.query(models.Wallet).filter(models.Wallet.id == source_id).first()
    owner_id = source_wallet.owner_id
    assert _wallet_by_id(client, headers, source_id)["current_balance"] == 1_000_000
    assert _wallet_by_id(client, headers, target_id)["current_balance"] == 0
    assert get_goal_wallet_funded_amount(session, owner_id, goal_id, source_id) == 1_000_000
    assert get_goal_wallet_funded_amount(session, owner_id, goal_id, target_id) == 0


def test_move_goal_funding_with_fee_records_linked_bank_fee(client, session):
    headers = create_user_and_token(
        client, "goalmovefee", "goalmovefee@example.com", "Password123!"
    )
    _make_premium(client, headers)
    source_id = _create_wallet(client, headers, name="MoveFeeSavings", initial_balance=1_010_000)
    target_id = _create_wallet(
        client,
        headers,
        name="MoveFeeDebit",
        wallet_type="DEBIT",
        initial_balance=0,
        can_fund_goals=True,
    )

    goal = client.post(
        "/goals/",
        json={"title": "Laptop fee move", "target_amount": 1_000_000, "intent": "PLANNED_PURCHASE"},
        headers=headers,
    )
    goal_id = goal.json()["id"]
    assert client.post(
        f"/goals/{goal_id}/allocations",
        json={"wallet_id": source_id, "amount": 1_000_000},
        headers=headers,
    ).status_code == 200

    moved = client.post(
        f"/goals/{goal_id}/allocations/move",
        json={
            "source_wallet_id": source_id,
            "target_wallet_id": target_id,
            "amount": 1_000_000,
            "fee_amount": 10_000,
            "fee_wallet_id": source_id,
            "fee_note": "bank app transfer fee",
            "date": user_timezone_today().isoformat(),
            "note": "prepare card payment",
        },
        headers=headers,
    )

    assert moved.status_code == 200, moved.text
    payload = moved.json()
    assert payload["transfer"]["fee_event_id"] is not None
    session.expire_all()
    source_wallet = session.query(models.Wallet).filter(models.Wallet.id == source_id).first()
    owner_id = source_wallet.owner_id
    assert _wallet_by_id(client, headers, source_id)["current_balance"] == 0
    assert _wallet_by_id(client, headers, target_id)["current_balance"] == 1_000_000
    assert get_goal_wallet_funded_amount(session, owner_id, goal_id, source_id) == 0
    assert get_goal_wallet_funded_amount(session, owner_id, goal_id, target_id) == 1_000_000

    fee_event = session.query(models.FinancialEvent).filter(
        models.FinancialEvent.id == payload["transfer"]["fee_event_id"]
    ).first()
    assert fee_event is not None
    assert fee_event.linked_event_id == payload["transfer"]["id"]
    assert fee_event.reference_type == models.ReferenceType.BANK_FEE


def test_move_goal_funding_allows_goals_off_owned_payment_target_wallet(client, session):
    headers = create_user_and_token(
        client, "goalmove2", "goalmove2@example.com", "Password123!"
    )
    _make_premium(client, headers)
    source_id = _create_wallet(client, headers, name="MoveSource", initial_balance=1_000_000)
    target_id = _create_wallet(
        client,
        headers,
        name="MoveIneligible",
        wallet_type="DEBIT",
        initial_balance=0,
        can_fund_goals=False,
    )
    goal = client.post(
        "/goals/",
        json={"title": "Laptop ineligible", "target_amount": 1_000_000, "intent": "PLANNED_PURCHASE"},
        headers=headers,
    )
    goal_id = goal.json()["id"]
    assert client.post(
        f"/goals/{goal_id}/allocations",
        json={"wallet_id": source_id, "amount": 1_000_000},
        headers=headers,
    ).status_code == 200

    blocked = client.post(
        f"/goals/{goal_id}/allocations/move",
        json={
            "source_wallet_id": source_id,
            "target_wallet_id": target_id,
            "amount": 500_000,
            "date": user_timezone_today().isoformat(),
        },
        headers=headers,
    )
    assert blocked.status_code == 200, blocked.text
    session.expire_all()
    source_wallet = session.query(models.Wallet).filter(models.Wallet.id == source_id).first()
    owner_id = source_wallet.owner_id
    assert _wallet_by_id(client, headers, source_id)["current_balance"] == 500_000
    assert _wallet_by_id(client, headers, target_id)["current_balance"] == 500_000
    assert get_goal_wallet_funded_amount(session, owner_id, goal_id, source_id) == 500_000
    assert get_goal_wallet_funded_amount(session, owner_id, goal_id, target_id) == 500_000


def test_move_goal_funding_rejects_credit_target_wallet(client):
    headers = create_user_and_token(
        client, "goalmovecredit", "goalmovecredit@example.com", "Password123!"
    )
    _make_premium(client, headers)
    source_id = _create_wallet(client, headers, name="MoveCreditSource", initial_balance=1_000_000)
    credit_response = client.post(
        "/wallets",
        json={
            "name": "CheckoutCredit",
            "wallet_type": "CREDIT",
            "initial_balance": 0,
            "credit_limit": 5_000_000,
            "can_fund_goals": False,
        },
        headers=headers,
    )
    assert credit_response.status_code == 201
    credit_id = credit_response.json()["id"]
    goal = client.post(
        "/goals/",
        json={"title": "Laptop credit target", "target_amount": 1_000_000, "intent": "PLANNED_PURCHASE"},
        headers=headers,
    )
    goal_id = goal.json()["id"]
    assert client.post(
        f"/goals/{goal_id}/allocations",
        json={"wallet_id": source_id, "amount": 1_000_000},
        headers=headers,
    ).status_code == 200

    blocked = client.post(
        f"/goals/{goal_id}/allocations/move",
        json={
            "source_wallet_id": source_id,
            "target_wallet_id": credit_id,
            "amount": 500_000,
            "date": user_timezone_today().isoformat(),
        },
        headers=headers,
    )
    assert blocked.status_code == 400
    assert blocked.json()["detail"] == "goals.prepare_payment_target_must_be_owned_money"


def test_move_goal_funding_accepts_multi_source_multi_target_moves(client, session):
    headers = create_user_and_token(
        client, "goalmovemulti", "goalmovemulti@example.com", "Password123!"
    )
    _make_premium(client, headers)
    savings_id = _create_wallet(client, headers, name="MoveMultiSavings", initial_balance=6_000_000)
    cash_source_id = _create_wallet(
        client,
        headers,
        name="MoveMultiCashSource",
        wallet_type="CASH",
        initial_balance=4_000_000,
        can_fund_goals=True,
    )
    debit_target_id = _create_wallet(
        client,
        headers,
        name="MoveMultiDebitTarget",
        wallet_type="DEBIT",
        initial_balance=0,
        can_fund_goals=False,
    )
    cash_target_id = _create_wallet(
        client,
        headers,
        name="MoveMultiCashTarget",
        wallet_type="CASH",
        initial_balance=0,
        can_fund_goals=False,
    )
    goal = client.post(
        "/goals/",
        json={"title": "Laptop route", "target_amount": 10_000_000, "intent": "PLANNED_PURCHASE"},
        headers=headers,
    )
    goal_id = goal.json()["id"]
    assert client.post(
        f"/goals/{goal_id}/allocations",
        json={
            "allocations": [
                {"wallet_id": savings_id, "amount": 6_000_000},
                {"wallet_id": cash_source_id, "amount": 4_000_000},
            ]
        },
        headers=headers,
    ).status_code == 200

    moved = client.post(
        f"/goals/{goal_id}/allocations/move",
        json={
            "moves": [
                {"source_wallet_id": savings_id, "target_wallet_id": debit_target_id, "amount": 6_000_000},
                {"source_wallet_id": cash_source_id, "target_wallet_id": debit_target_id, "amount": 1_000_000},
                {"source_wallet_id": cash_source_id, "target_wallet_id": cash_target_id, "amount": 2_000_000},
            ],
            "date": user_timezone_today().isoformat(),
            "note": "prepare split checkout",
        },
        headers=headers,
    )
    assert moved.status_code == 200, moved.text
    payload = moved.json()
    assert payload["moved_amount"] == 9_000_000
    assert len(payload["transfers"]) == 3

    session.expire_all()
    savings_wallet = session.query(models.Wallet).filter(models.Wallet.id == savings_id).first()
    owner_id = savings_wallet.owner_id
    assert _wallet_by_id(client, headers, savings_id)["current_balance"] == 0
    assert _wallet_by_id(client, headers, cash_source_id)["current_balance"] == 1_000_000
    assert _wallet_by_id(client, headers, debit_target_id)["current_balance"] == 7_000_000
    assert _wallet_by_id(client, headers, cash_target_id)["current_balance"] == 2_000_000
    assert get_goal_wallet_funded_amount(session, owner_id, goal_id, savings_id) == 0
    assert get_goal_wallet_funded_amount(session, owner_id, goal_id, cash_source_id) == 1_000_000
    assert get_goal_wallet_funded_amount(session, owner_id, goal_id, debit_target_id) == 7_000_000
    assert get_goal_wallet_funded_amount(session, owner_id, goal_id, cash_target_id) == 2_000_000


def test_move_goal_funding_fee_cannot_use_protected_goal_money_after_move(client):
    headers = create_user_and_token(
        client, "goalmovefeeblock", "goalmovefeeblock@example.com", "Password123!"
    )
    _make_premium(client, headers)
    source_id = _create_wallet(client, headers, name="MoveFeeBlockSource", initial_balance=1_000_000)
    target_id = _create_wallet(
        client,
        headers,
        name="MoveFeeBlockTarget",
        wallet_type="DEBIT",
        initial_balance=0,
        can_fund_goals=False,
    )
    goal = client.post(
        "/goals/",
        json={"title": "Laptop fee blocked", "target_amount": 1_000_000, "intent": "PLANNED_PURCHASE"},
        headers=headers,
    )
    goal_id = goal.json()["id"]
    assert client.post(
        f"/goals/{goal_id}/allocations",
        json={"wallet_id": source_id, "amount": 1_000_000},
        headers=headers,
    ).status_code == 200

    blocked = client.post(
        f"/goals/{goal_id}/allocations/move",
        json={
            "source_wallet_id": source_id,
            "target_wallet_id": target_id,
            "amount": 1_000_000,
            "fee_amount": 10_000,
            "fee_wallet_id": source_id,
            "date": user_timezone_today().isoformat(),
        },
        headers=headers,
    )
    assert blocked.status_code == 400
    assert blocked.json()["detail"]["code"] == "wallets.fee_goal_protection_conflict"


def test_planned_purchase_can_be_goal_funded_after_moving_goal_money_to_payment_wallet(client):
    headers = create_user_and_token(
        client, "goalmove3", "goalmove3@example.com", "Password123!"
    )
    _make_premium(client, headers)
    source_id = _create_wallet(client, headers, name="PrepareSavings", initial_balance=1_000_000)
    target_id = _create_wallet(
        client,
        headers,
        name="PrepareDebit",
        wallet_type="DEBIT",
        initial_balance=0,
        can_fund_goals=True,
    )
    _create_current_budget(client, headers)
    goal = client.post(
        "/goals/",
        json={"title": "Laptop prepared", "target_amount": 1_000_000, "intent": "PLANNED_PURCHASE"},
        headers=headers,
    )
    goal_id = goal.json()["id"]
    assert client.post(
        f"/goals/{goal_id}/allocations",
        json={"wallet_id": source_id, "amount": 1_000_000},
        headers=headers,
    ).status_code == 200
    assert client.post(
        f"/goals/{goal_id}/allocations/move",
        json={
            "source_wallet_id": source_id,
            "target_wallet_id": target_id,
            "amount": 1_000_000,
            "date": user_timezone_today().isoformat(),
        },
        headers=headers,
    ).status_code == 200

    purchase = client.post(
        f"/goals/{goal_id}/record-purchase",
        json={
            "amount": 1_000_000,
            "payment_allocations": [{"wallet_id": target_id, "amount": 1_000_000}],
            "category": "Electronics",
            "date": user_timezone_today().isoformat(),
            "settlement_mode": "DIRECT",
        },
        headers=headers,
    )
    assert purchase.status_code == 200, purchase.text
    payload = purchase.json()
    assert payload["consumed_amount"] == 1_000_000
    assert payload["goal"]["status"] == "COMPLETED"
    assert _wallet_by_id(client, headers, source_id)["current_balance"] == 0
    assert _wallet_by_id(client, headers, target_id)["current_balance"] == 0


def test_planned_purchase_goal_backed_off_wallet_single_wallet(client, session):
    headers = create_user_and_token(
        client, "goaluse3multi", "goaluse3multi@example.com", "Password123!"
    )
    _make_premium(client, headers)
    cash_id = _create_wallet(client, headers, name="OutsideCash", wallet_type="CASH", initial_balance=1_000_000)
    debit_id = _create_wallet(
        client,
        headers,
        name="OutsideCard",
        wallet_type="DEBIT",
        initial_balance=1_000_000,
        can_fund_goals=False,
    )
    _create_current_budget(client, headers, category="Housing")

    goal = client.post(
        "/goals/",
        json={"title": "Fridge outside", "target_amount": 1_000_000, "intent": "PLANNED_PURCHASE"},
        headers=headers,
    )
    goal_id = goal.json()["id"]
    assert client.post(
        f"/goals/{goal_id}/allocations",
        json={"wallet_id": cash_id, "amount": 1_000_000},
        headers=headers,
    ).status_code == 200

    used = client.post(
        f"/goals/{goal_id}/record-purchase",
        json={
            "amount": 1_000_000,
            "payment_allocations": [
                {"wallet_id": debit_id, "amount": 1_000_000},
            ],
            "category": "Housing",
            "date": user_timezone_today().isoformat(),
            "settlement_mode": "GOAL_BACKED_OFF_WALLET_PAYMENT",
        },
        headers=headers,
    )
    assert used.status_code == 200, used.text
    payload = used.json()
    assert payload["consumed_amount"] == 1_000_000
    assert payload["goal"]["status"] == "COMPLETED"
    assert payload["transfer_event_ids"] == []
    assert _wallet_by_id(client, headers, cash_id)["current_balance"] == 1_000_000
    assert _wallet_by_id(client, headers, debit_id)["current_balance"] == 0

    event = session.get(models.FinancialEvent, payload["expense_event_id"])
    assert event is not None
    assert event.reference_type == models.ReferenceType.GOAL_PLANNED_PURCHASE


def test_planned_purchase_direct_settlement_rejects_payment_wallet_that_did_not_fund_goal(client):
    headers = create_user_and_token(
        client, "goaluse2b", "goaluse2b@example.com", "Password123!"
    )
    _make_premium(client, headers)
    savings_id = _create_wallet(client, headers, name="GoalSource", initial_balance=1_000_000)
    debit_id = _create_wallet(
        client,
        headers,
        name="WrongDirectCard",
        wallet_type="DEBIT",
        initial_balance=1_000_000,
        can_fund_goals=False,
    )
    _create_current_budget(client, headers)

    goal = client.post(
        "/goals/",
        json={"title": "Headphones", "target_amount": 1_000_000, "intent": "PLANNED_PURCHASE"},
        headers=headers,
    )
    goal_id = goal.json()["id"]
    assert client.post(
        f"/goals/{goal_id}/allocations",
        json={"wallet_id": savings_id, "amount": 1_000_000},
        headers=headers,
    ).status_code == 200

    blocked = client.post(
        f"/goals/{goal_id}/record-purchase",
        json={
            "amount": 1_000_000,
            "payment_allocations": [{"wallet_id": debit_id, "amount": 1_000_000}],
            "category": "Electronics",
            "date": user_timezone_today().isoformat(),
            "settlement_mode": "DIRECT",
        },
        headers=headers,
    )
    assert blocked.status_code == 400
    assert blocked.json()["detail"] == "goals.payment_wallet_not_funding_source"


def test_planned_purchase_off_wallet_still_rejects_second_purchase(client):
    headers = create_user_and_token(
        client, "goaluse3", "goaluse3@example.com", "Password123!"
    )
    _make_premium(client, headers)
    savings_id = _create_wallet(client, headers, name="UnusedSave", initial_balance=1_000_000)
    debit_id = _create_wallet(
        client,
        headers,
        name="OutsidePay",
        wallet_type="DEBIT",
        initial_balance=1_000_000,
        can_fund_goals=False,
    )
    _create_current_budget(client, headers)

    goal = client.post(
        "/goals/",
        json={"title": "Tablet", "target_amount": 1_000_000, "intent": "PLANNED_PURCHASE"},
        headers=headers,
    )
    goal_id = goal.json()["id"]
    assert client.post(
        f"/goals/{goal_id}/allocations",
        json={"wallet_id": savings_id, "amount": 1_000_000},
        headers=headers,
    ).status_code == 200

    first = client.post(
        f"/goals/{goal_id}/record-purchase",
        json={
            "amount": 1_000_000,
            "payment_allocations": [{"wallet_id": debit_id, "amount": 1_000_000}],
            "category": "Electronics",
            "date": user_timezone_today().isoformat(),
            "settlement_mode": "GOAL_BACKED_OFF_WALLET_PAYMENT",
        },
        headers=headers,
    )
    assert first.status_code == 200

    blocked = client.post(
        f"/goals/{goal_id}/record-purchase",
        json={
            "amount": 1_000_000,
            "payment_allocations": [{"wallet_id": debit_id, "amount": 1_000_000}],
            "category": "Electronics",
            "date": user_timezone_today().isoformat(),
            "settlement_mode": "GOAL_BACKED_OFF_WALLET_PAYMENT",
        },
        headers=headers,
    )
    assert blocked.status_code == 400
    assert blocked.json()["detail"] == "goals.purchase_already_recorded"
    assert _wallet_by_id(client, headers, savings_id)["current_balance"] == 1_000_000
    assert _wallet_by_id(client, headers, debit_id)["current_balance"] == 0


def test_reserve_off_wallet_payment_consumes_reserve_allocation(client):
    headers = create_user_and_token(
        client, "goaluse4", "goaluse4@example.com", "Password123!"
    )
    _make_premium(client, headers)
    savings_id = _create_wallet(client, headers, name="ReserveSave", initial_balance=1_000_000)
    debit_id = _create_wallet(
        client,
        headers,
        name="ReservePay",
        wallet_type="DEBIT",
        initial_balance=1_000_000,
        can_fund_goals=False,
    )
    _create_current_budget(client, headers, category="Health")

    goal = client.post(
        "/goals/",
        json={"title": "Emergency", "target_amount": 1_000_000, "intent": "RESERVE"},
        headers=headers,
    )
    goal_id = goal.json()["id"]
    assert client.post(
        f"/goals/{goal_id}/allocations",
        json={"wallet_id": savings_id, "amount": 1_000_000},
        headers=headers,
    ).status_code == 200

    used = client.post(
        f"/goals/{goal_id}/use-reserve",
        json={
            "amount": 300_000,
            "payment_allocations": [{"wallet_id": debit_id, "amount": 300_000}],
            "category": "Health",
            "date": user_timezone_today().isoformat(),
            "settlement_mode": "GOAL_BACKED_OFF_WALLET_PAYMENT",
        },
        headers=headers,
    )
    assert used.status_code == 200
    payload = used.json()
    assert payload["consumed_amount"] == 300_000
    assert payload["goal"]["status"] == "ACTIVE"
    assert payload["goal"]["funded_amount"] == 700_000
    assert _wallet_by_id(client, headers, savings_id)["current_balance"] == 1_000_000
    assert _wallet_by_id(client, headers, debit_id)["current_balance"] == 700_000


def test_reserve_direct_use_from_same_wallet_consumes_without_completing_goal(client):
    headers = create_user_and_token(
        client, "goaluse4b", "goaluse4b@example.com", "Password123!"
    )
    _make_premium(client, headers)
    savings_id = _create_wallet(client, headers, name="ReserveDirect", initial_balance=1_000_000)
    _create_current_budget(client, headers, category="Health")

    goal = client.post(
        "/goals/",
        json={"title": "Medical buffer", "target_amount": 1_000_000, "intent": "RESERVE"},
        headers=headers,
    )
    goal_id = goal.json()["id"]
    assert client.post(
        f"/goals/{goal_id}/allocations",
        json={"wallet_id": savings_id, "amount": 1_000_000},
        headers=headers,
    ).status_code == 200

    used = client.post(
        f"/goals/{goal_id}/use-reserve",
        json={
            "amount": 250_000,
            "payment_allocations": [{"wallet_id": savings_id, "amount": 250_000}],
            "category": "Health",
            "date": user_timezone_today().isoformat(),
            "settlement_mode": "DIRECT",
        },
        headers=headers,
    )
    assert used.status_code == 200
    payload = used.json()
    assert payload["expense_event_id"] is not None
    assert payload["transfer_event_ids"] == []
    assert payload["consumed_amount"] == 250_000
    assert payload["outside_goal_amount"] == 0
    assert payload["goal"]["status"] == "ACTIVE"
    assert payload["goal"]["linked_expense_event_id"] is None
    assert payload["goal"]["funded_amount"] == 750_000
    assert _wallet_by_id(client, headers, savings_id)["current_balance"] == 750_000


def test_reserve_off_wallet_use_can_consume_reserve_without_budget_pressure_or_transfer(client, session):
    headers = create_user_and_token(
        client, "goaluse5", "goaluse5@example.com", "Password123!"
    )
    _make_premium(client, headers)
    savings_id = _create_wallet(client, headers, name="ReserveFund", initial_balance=1_000_000)
    debit_id = _create_wallet(
        client,
        headers,
        name="ReserveCard",
        wallet_type="DEBIT",
        initial_balance=1_000_000,
        can_fund_goals=False,
    )
    _create_current_budget(client, headers, category="Health")

    goal = client.post(
        "/goals/",
        json={"title": "Medical", "target_amount": 1_000_000, "intent": "RESERVE"},
        headers=headers,
    )
    goal_id = goal.json()["id"]
    assert client.post(
        f"/goals/{goal_id}/allocations",
        json={"wallet_id": savings_id, "amount": 1_000_000},
        headers=headers,
    ).status_code == 200

    used = client.post(
        f"/goals/{goal_id}/use-reserve",
        json={
            "amount": 300_000,
            "payment_allocations": [{"wallet_id": debit_id, "amount": 300_000}],
            "category": "Health",
            "date": user_timezone_today().isoformat(),
            "settlement_mode": "GOAL_BACKED_OFF_WALLET_PAYMENT",
            "enforce_monthly_budget_limits": False,
        },
        headers=headers,
    )
    assert used.status_code == 200
    payload = used.json()
    assert payload["consumed_amount"] == 300_000
    assert payload["goal"]["status"] == "ACTIVE"
    assert payload["goal"]["linked_expense_event_id"] is None
    assert payload["goal"]["funded_amount"] == 700_000
    assert payload["transfer_event_ids"] == []
    assert _wallet_by_id(client, headers, savings_id)["current_balance"] == 1_000_000
    assert _wallet_by_id(client, headers, debit_id)["current_balance"] == 700_000

    today = user_timezone_today()
    budget_after = client.get(
        f"/budgets/item?budget_year={today.year}&budget_month={today.month}&category=Health",
        headers=headers,
    )
    assert budget_after.status_code == 200
    assert budget_after.json()["spent"] == 0
    assert budget_after.json()["remaining"] == 1_000_000

    expenses = client.get("/expenses/", headers=headers)
    assert expenses.status_code == 200
    assert any(
        item["expense"]["id"] == payload["expense_event_id"]
        for item in expenses.json()["items"]
        if item["expense"] is not None
    )

    event = session.get(models.FinancialEvent, payload["expense_event_id"])
    assert event.reference_type == models.ReferenceType.GOAL_CONSUME
    assert event.entity_legs[0].budget_id is None

    activity = client.get(f"/goals/{goal_id}/activity", headers=headers)
    assert activity.status_code == 200
    used_item = next(item for item in activity.json()["items"] if item["type"] == "GOAL_MONEY_USED")
    wallets_by_role = {wallet["role"]: wallet for wallet in used_item["wallets"]}
    assert wallets_by_role["paid_from"]["wallet_id"] == debit_id
    assert wallets_by_role["released_from"]["wallet_id"] == savings_id


def test_update_goal_rejects_target_below_funded_amount(client):
    headers = create_user_and_token(
        client, "goaluser10", "goaluser10@example.com", "Password123!"
    )
    wallet_id = _setup_premium_user_with_goal_wallet(client, headers)
    created = client.post(
        "/goals/",
        json={"title": "Monitor", "target_amount": 700_000},
        headers=headers,
    )
    goal_id = created.json()["id"]
    assert client.post(
        f"/goals/{goal_id}/allocations",
        json={"wallet_id": wallet_id, "amount": 300_000},
        headers=headers,
    ).status_code == 200

    updated = client.patch(
        f"/goals/{goal_id}",
        json={"target_amount": 200_000},
        headers=headers,
    )
    assert updated.status_code == 400
    assert updated.json()["detail"] == "goals.target_below_funded_amount"


def test_archive_restore_and_delete_goal_flow(client):
    headers = create_user_and_token(
        client, "goaluser11", "goaluser11@example.com", "Password123!"
    )
    _setup_premium_user_with_goal_wallet(client, headers)

    created = client.post(
        "/goals/",
        json={"title": "Desk", "target_amount": 400_000},
        headers=headers,
    )
    goal_id = created.json()["id"]

    archived = client.post(f"/goals/{goal_id}/archive", headers=headers)
    assert archived.status_code == 200
    assert archived.json()["status"] == "ARCHIVED"

    restored = client.post(f"/goals/{goal_id}/restore", headers=headers)
    assert restored.status_code == 200
    assert restored.json()["status"] == "ACTIVE"

    assert client.post(f"/goals/{goal_id}/archive", headers=headers).status_code == 200
    deleted = client.delete(f"/goals/{goal_id}", headers=headers)
    assert deleted.status_code == 204
    listed = client.get("/goals/", headers=headers)
    assert listed.status_code == 200
    assert listed.json() == []


def test_archive_returns_unreleased_funding_to_wallet_availability(client):
    headers = create_user_and_token(
        client, "goaluser12", "goaluser12@example.com", "Password123!"
    )
    wallet_id = _setup_premium_user_with_goal_wallet(client, headers)
    created = client.post(
        "/goals/",
        json={"title": "Desk lamp", "target_amount": 300_000},
        headers=headers,
    )
    goal_id = created.json()["id"]
    assert client.post(
        f"/goals/{goal_id}/allocations",
        json={"wallet_id": wallet_id, "amount": 100_000},
        headers=headers,
    ).status_code == 200

    archived = client.post(f"/goals/{goal_id}/archive", headers=headers)
    assert archived.status_code == 200
    payload = archived.json()
    assert payload["status"] == "ARCHIVED"
    assert payload["funded_amount"] == 0
    assert payload["remaining_amount"] == 300_000

    summary = client.get("/goals/funding-summary", headers=headers)
    assert summary.status_code == 200
    assert summary.json()["allocated_to_goals"] == 0
    assert summary.json()["available_for_goals"] == 2_000_000


def test_create_goal_rejects_when_active_limit_is_reached(client, session):
    headers = create_user_and_token(
        client, "goaluser13", "goaluser13@example.com", "Password123!"
    )
    _setup_premium_user_with_goal_wallet(client, headers)
    user = session.query(models.User).filter(models.User.email == "goaluser13@example.com").first()
    assert user is not None

    for i in range(20):
        session.add(
            models.Goals(
                owner_id=user.id,
                title=f"Goal {i:02d}",
                target_amount=100_000 + i,
                status=models.GoalStatus.ACTIVE,
            )
        )
    session.commit()

    blocked = client.post(
        "/goals/",
        json={"title": "Overflow goal", "target_amount": 999_999},
        headers=headers,
    )
    assert blocked.status_code == 400
    assert blocked.json()["detail"] == "goals.active_limit_reached"


def test_archived_goal_rejects_money_actions_for_each_intent(client):
    headers = create_user_and_token(
        client, "archivedmoney", "archivedmoney@example.com", "Password123!"
    )
    wallet_id = _setup_premium_user_with_goal_wallet(client, headers)

    reserve = client.post(
        "/goals/",
        json={"title": "Arch reserve", "target_amount": 300_000, "intent": "RESERVE"},
        headers=headers,
    )
    assert reserve.status_code == 201, reserve.text
    reserve_id = reserve.json()["id"]

    purchase = client.post(
        "/goals/",
        json={"title": "Arch purchase", "target_amount": 300_000, "intent": "PLANNED_PURCHASE"},
        headers=headers,
    )
    assert purchase.status_code == 201, purchase.text
    purchase_id = purchase.json()["id"]

    for goal_id in [reserve_id, purchase_id]:
        archived = client.post(f"/goals/{goal_id}/archive", headers=headers)
        assert archived.status_code == 200, archived.text
        assert archived.json()["status"] == "ARCHIVED"

        allocate = client.post(
            f"/goals/{goal_id}/allocations",
            json={"wallet_id": wallet_id, "amount": 100_000},
            headers=headers,
        )
        assert allocate.status_code == 400, allocate.text
        assert allocate.json()["detail"] == "goals.archived_read_only"


def test_delete_goal_requires_archived_and_empty(client):
    headers = create_user_and_token(
        client, "deletesafety", "deletesafety@example.com", "Password123!"
    )
    wallet_id = _setup_premium_user_with_goal_wallet(client, headers)

    active = client.post(
        "/goals/",
        json={"title": "Active goal", "target_amount": 300_000, "intent": "RESERVE"},
        headers=headers,
    )
    assert active.status_code == 201, active.text
    goal_id = active.json()["id"]

    delete_active = client.delete(f"/goals/{goal_id}", headers=headers)
    assert delete_active.status_code == 400, delete_active.text
    assert delete_active.json()["detail"] == "goals.delete_requires_archived"

    client.post(
        f"/goals/{goal_id}/allocations",
        json={"wallet_id": wallet_id, "amount": 100_000},
        headers=headers,
    )
    archived = client.post(f"/goals/{goal_id}/archive", headers=headers)
    assert archived.status_code == 200, archived.text
    assert archived.json()["funded_amount"] == 0  # archived releases funds

    # Now safe to delete
    deleted = client.delete(f"/goals/{goal_id}", headers=headers)
    assert deleted.status_code == 204, deleted.text


def test_goal_write_rate_limit_blocks_excess_requests(client):
    try:
        for key in redis_client.scan_iter("tb:goals_lifecycle_write:*"):
            redis_client.delete(key)
    except Exception:
        pytest.skip("Redis is not reachable for explicit rate-limit assertion.")

    headers = create_user_and_token(
        client, "goaluser14", "goaluser14@example.com", "Password123!"
    )
    _setup_premium_user_with_goal_wallet(client, headers)

    blocked = None
    for i in range(20):
        res = client.post(
            "/goals/",
            json={"title": f"Speed {i:02d}", "target_amount": 150_000 + i},
            headers=headers,
        )
        if res.status_code == 429:
            blocked = res
            break

    assert blocked is not None
    assert blocked.status_code == 429
    assert "Retry-After" in blocked.headers
    assert blocked.json()["detail"] == "goals.write_rate_limited"


def test_no_goal_route_returns_overdue_as_stored_status(client):
    headers = create_user_and_token(
        client, "nooverduestatus", "nooverduestatus@example.com", "Password123!"
    )
    _setup_premium_user_with_goal_wallet(client, headers)
    today = user_timezone_today()

    goals_to_create = [
        {"title": "Reserve", "target_amount": 100_000, "intent": "RESERVE"},
        {
            "title": "Past purchase",
            "target_amount": 100_000,
            "target_date": (today - timedelta(days=30)).isoformat(),
            "intent": "PLANNED_PURCHASE",
        },
        {
            "title": "Future purchase",
            "target_amount": 100_000,
            "target_date": (today + timedelta(days=60)).isoformat(),
            "intent": "PLANNED_PURCHASE",
        },
    ]

    for payload in goals_to_create:
        created = client.post("/goals/", json=payload, headers=headers)
        assert created.status_code == 201, created.text
        assert created.json()["status"] != "OVERDUE"

    listed = client.get("/goals/", headers=headers)
    assert listed.status_code == 200, listed.text
    for goal in listed.json():
        assert goal["status"] != "OVERDUE", f"Goal {goal['id']} has stored OVERDUE status"


def test_planned_purchase_timezone_boundary_time_state(client):
    headers_tashkent = create_user_and_token(
        client, "tztashkent", "tztashkent@example.com", "Password123!"
    )
    _setup_premium_user_with_goal_wallet(client, headers_tashkent)
    today_tashkent = user_timezone_today()

    due_tomorrow = client.post(
        "/goals/",
        json={
            "title": "Due tomorrow TZ",
            "target_amount": 200_000,
            "target_date": (today_tashkent + timedelta(days=1)).isoformat(),
            "intent": "PLANNED_PURCHASE",
        },
        headers=headers_tashkent,
    )
    assert due_tomorrow.status_code == 201, due_tomorrow.text
    assert due_tomorrow.json()["time_state"] in ("due_soon", "on_track")
    assert due_tomorrow.json()["status"] == "ACTIVE"

    past_yesterday = client.post(
        "/goals/",
        json={
            "title": "Past yesterday TZ",
            "target_amount": 200_000,
            "target_date": (today_tashkent - timedelta(days=1)).isoformat(),
            "intent": "PLANNED_PURCHASE",
        },
        headers=headers_tashkent,
    )
    assert past_yesterday.status_code == 201, past_yesterday.text
    assert past_yesterday.json()["time_state"] == "overdue"
    assert past_yesterday.json()["status"] == "ACTIVE"


def test_full_lifecycle_regression_reserve(client):
    headers = create_user_and_token(
        client, "lifecycler", "lifecycler@example.com", "Password123!"
    )
    wallet_id = _setup_premium_user_with_goal_wallet(client, headers)

    reserve = client.post(
        "/goals/",
        json={"title": "Lifecycle reserve", "target_amount": 300_000, "intent": "RESERVE"},
        headers=headers,
    )
    assert reserve.status_code == 201, reserve.text
    reserve_id = reserve.json()["id"]
    assert reserve.json()["status"] == "ACTIVE"
    assert reserve.json()["time_state"] is None

    client.post(
        f"/goals/{reserve_id}/allocations",
        json={"wallet_id": wallet_id, "amount": 300_000},
        headers=headers,
    )
    listed = client.get("/goals/", headers=headers)
    reserve_goal = next(g for g in listed.json() if g["id"] == reserve_id)
    assert reserve_goal["status"] == "ACTIVE"
    assert reserve_goal["progress_percent"] == 100

    archived = client.post(f"/goals/{reserve_id}/archive", headers=headers)
    assert archived.status_code == 200
    assert archived.json()["status"] == "ARCHIVED"

    restored = client.post(f"/goals/{reserve_id}/restore", headers=headers)
    assert restored.status_code == 200
    assert restored.json()["status"] == "ACTIVE"

    client.post(f"/goals/{reserve_id}/archive", headers=headers)
    client.delete(f"/goals/{reserve_id}", headers=headers)


def test_full_lifecycle_regression_planned_purchase(client):
    headers = create_user_and_token(
        client, "lifecyclepp", "lifecyclepp@example.com", "Password123!"
    )
    _setup_premium_user_with_goal_wallet(client, headers)

    purchase = client.post(
        "/goals/",
        json={
            "title": "Lifecycle purchase",
            "target_amount": 200_000,
            "target_date": (user_timezone_today() + timedelta(days=14)).isoformat(),
            "intent": "PLANNED_PURCHASE",
        },
        headers=headers,
    )
    assert purchase.status_code == 201, purchase.text
    purchase_id = purchase.json()["id"]
    assert purchase.json()["time_state"] == "on_track"

    archived = client.post(f"/goals/{purchase_id}/archive", headers=headers)
    assert archived.status_code == 200
    restored = client.post(f"/goals/{purchase_id}/restore", headers=headers)
    assert restored.status_code == 200

    client.post(f"/goals/{purchase_id}/archive", headers=headers)
    client.delete(f"/goals/{purchase_id}", headers=headers)


def test_full_lifecycle_regression_pay_obligation(client):
    headers = create_user_and_token(
        client, "lifecyclepo", "lifecyclepo@example.com", "Password123!"
    )
    _setup_premium_user_with_goal_wallet(client, headers)

    debt_wallet = _create_wallet(client, headers, name="DebtLifecycle", initial_balance=500_000)
    debt_res = _create_i_owe_debt(client, headers, debt_wallet, amount=200_000)
    debt_id = debt_res["id"]

    obligation = client.post(
        "/goals/",
        json={
            "title": "Lifecycle obligation",
            "target_amount": 200_000,
            "intent": "PAY_OBLIGATION",
            "linked_debt_id": debt_id,
        },
        headers=headers,
    )
    assert obligation.status_code == 201, obligation.text
    obl_id = obligation.json()["id"]
    assert obligation.json()["status"] == "ACTIVE"
    assert obligation.json()["time_state"] is None

    archived = client.post(f"/goals/{obl_id}/archive", headers=headers)
    assert archived.status_code == 200
    restored = client.post(f"/goals/{obl_id}/restore", headers=headers)
    assert restored.status_code == 200

    client.post(f"/goals/{obl_id}/archive", headers=headers)
    client.delete(f"/goals/{obl_id}", headers=headers)
