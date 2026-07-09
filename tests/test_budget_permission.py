"""Regression tests for the Budget Permission seam (Issues 1–4 of PRD 2).

Coverage:
- Budget Permission allows valid normal expense posting
- Budget Permission preserves budget-required structured failure
- Budget Permission preserves overlay project reservation behavior
- Budget Permission preserves isolated project behavior (frozen)
- Budget Permission result carries the correct budget/subcategory/project refs
- Expense Posting integration through post_expense_event uses Budget Permission
- Budget Month Summary output remains stable after separation (Issue 3)
- Project Budget View output remains stable after separation (Issue 4)
- Budget Permission does not depend on summary/view reporting functions
"""

from datetime import date

from fastapi import HTTPException

from app import models
from app.services.budget_permission_service import (
    BudgetPermissionRequest,
    BudgetPermissionResult,
    check_budget_permission,
)
from app.services.expense_posting_service import post_expense_event
from tests.helpers import (
    create_user_and_token,
    user_timezone_today,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _seed_user_with_wallet(client, session, email: str) -> tuple[models.User, models.Wallet, dict]:
    """Create a test user via the API and return their User, default Wallet, and auth headers."""
    headers = create_user_and_token(client, email.split("@")[0], email, "Password123!")
    user = session.query(models.User).filter(models.User.email == email).first()
    wallet = session.query(models.Wallet).filter(
        models.Wallet.owner_id == user.id,
        models.Wallet.is_default,
    ).first()
    return user, wallet, headers


def _create_budget_row(
    session,
    user_id: int,
    category: models.ExpenseCategory,
    monthly_limit: int,
    expense_date: date | None = None,
) -> models.Budget:
    """Create a Budget row directly in the DB for testing."""
    today = expense_date or user_timezone_today()
    budget = models.Budget(
        owner_id=user_id,
        category=category,
        monthly_limit=monthly_limit,
        budget_year=today.year,
        budget_month=today.month,
        auto_created=False,
    )
    session.add(budget)
    session.commit()
    session.refresh(budget)
    return budget


def _create_subcategory(
    session,
    user_id: int,
    category: models.ExpenseCategory,
    name: str = "Test Subcategory",
) -> models.UserSubcategory:
    """Create a UserSubcategory row directly in the DB."""
    sub = models.UserSubcategory(
        owner_id=user_id,
        category=category,
        name=name,
        is_active=True,
    )
    session.add(sub)
    session.commit()
    session.refresh(sub)
    return sub


def _create_subcategory_limit(
    session,
    user_id: int,
    budget_id: int,
    subcategory_id: int,
    monthly_limit: int,
) -> models.BudgetSubcategoryLimit:
    """Create a BudgetSubcategoryLimit row directly in the DB."""
    limit = models.BudgetSubcategoryLimit(
        owner_id=user_id,
        budget_id=budget_id,
        subcategory_id=subcategory_id,
        monthly_limit=monthly_limit,
    )
    session.add(limit)
    session.commit()
    session.refresh(limit)
    return limit


def _create_overlay_project(
    session,
    user_id: int,
    title: str = "Test Project",
) -> models.Project:
    """Create an overlay Project with its detail row."""
    project = models.Project(
        owner_id=user_id,
        title=title,
        project_type=models.ProjectType.OVERLAY,
        status=models.ProjectStatus.ACTIVE,
        start_date=date(2025, 1, 1),
    )
    session.add(project)
    session.flush()
    project.overlay_detail = models.ProjectOverlayDetail(
        owner_id=user_id,
        target_estimate=None,
    )
    session.commit()
    session.refresh(project)
    return project


# ---------------------------------------------------------------------------
# Budget Permission direct tests
# ---------------------------------------------------------------------------


def test_check_budget_permission_allows_valid_expense(client, session):
    """Budget Permission returns a valid result when a Budget row exists."""
    user, _wallet, _headers = _seed_user_with_wallet(client, session, "bp1@example.com")
    today = user_timezone_today()
    _create_budget_row(session, user.id, models.ExpenseCategory.GROCERIES, 1_000_000, today)

    result = check_budget_permission(
        session,
        BudgetPermissionRequest(
            user_id=user.id,
            category=models.ExpenseCategory.GROCERIES,
            amount=50_000,
            expense_date=today,
        ),
    )

    assert isinstance(result, BudgetPermissionResult)
    assert result.budget is not None
    assert result.budget.category == models.ExpenseCategory.GROCERIES
    assert result.budget.budget_year == today.year
    assert result.budget.budget_month == today.month


def test_check_budget_permission_rejects_when_no_budget_exists(client, session):
    """Budget Permission raises budget_required when no Budget row exists
    and none can be materialized."""
    user, _wallet, _headers = _seed_user_with_wallet(client, session, "bp2@example.com")
    today = user_timezone_today()

    try:
        check_budget_permission(
            session,
            BudgetPermissionRequest(
                user_id=user.id,
                category=models.ExpenseCategory.GROCERIES,
                amount=50_000,
                expense_date=today,
            ),
        )
        assert False, "Expected HTTPException"
    except HTTPException as exc:
        assert exc.status_code == 400
        assert exc.detail == "expenses.budget_required"


def test_check_budget_permission_allows_overspend_within_budget_existence(client, session):
    """Budget Permission allows spend above the monthly limit — limits are
    soft during posting; the plan just reports over-planned status afterward."""
    user, _wallet, _headers = _seed_user_with_wallet(client, session, "bp3@example.com")
    today = user_timezone_today()
    _create_budget_row(session, user.id, models.ExpenseCategory.GROCERIES, 100_000, today)

    # Overspending is allowed — the budget limit is a planning soft limit.
    result = check_budget_permission(
        session,
        BudgetPermissionRequest(
            user_id=user.id,
            category=models.ExpenseCategory.GROCERIES,
            amount=200_000,
            expense_date=today,
        ),
    )
    assert isinstance(result, BudgetPermissionResult)
    assert result.budget is not None


def test_check_budget_permission_skips_budget_for_isolated_project(client, session):
    """Budget Permission returns budget=None for isolated projects (budget
    limits are not enforced for isolated project spend)."""
    user, _wallet, _headers = _seed_user_with_wallet(client, session, "bp4@example.com")
    today = user_timezone_today()

    project = models.Project(
        owner_id=user.id,
        title="Isolated Project",
        project_type=models.ProjectType.ISOLATED,
        status=models.ProjectStatus.ACTIVE,
        start_date=date(2025, 1, 1),
    )
    session.add(project)
    session.flush()
    project.isolated_detail = models.ProjectIsolatedDetail(
        owner_id=user.id,
        funding_limit=5_000_000,
    )
    # Add a category allocation so validate_project_budget doesn't fail
    alloc = models.IsolatedProjectCategoryAllocation(
        project_id=project.id,
        category=models.ExpenseCategory.GROCERIES,
        limit_amount=1_000_000,
    )
    session.add(alloc)
    session.commit()
    session.refresh(project)

    result = check_budget_permission(
        session,
        BudgetPermissionRequest(
            user_id=user.id,
            category=models.ExpenseCategory.GROCERIES,
            amount=50_000,
            expense_date=today,
            project=project,
        ),
    )

    assert isinstance(result, BudgetPermissionResult)
    # Budget is None for isolated projects — limits are project-managed
    assert result.budget is None
    assert result.project is not None
    assert result.project.id == project.id


def test_check_budget_permission_allows_subcategory_overspend(client, session):
    """Budget Permission allows spend above a subcategory limit — subcategory
    limits are soft during posting; budget detail just reports red state."""
    user, _wallet, _headers = _seed_user_with_wallet(client, session, "bp5@example.com")
    today = user_timezone_today()

    budget = _create_budget_row(
        session, user.id, models.ExpenseCategory.GROCERIES, 1_000_000, today
    )
    subcategory = _create_subcategory(
        session, user.id, models.ExpenseCategory.GROCERIES, "Snacks"
    )
    _create_subcategory_limit(
        session, user.id, budget.id, subcategory.id, monthly_limit=50_000
    )

    # Subcategory overspend is allowed — limits are soft during posting.
    result = check_budget_permission(
        session,
        BudgetPermissionRequest(
            user_id=user.id,
            category=models.ExpenseCategory.GROCERIES,
            amount=100_000,
            expense_date=today,
            subcategory=subcategory,
        ),
    )
    assert isinstance(result, BudgetPermissionResult)
    assert result.budget is not None
    assert result.subcategory is not None


def test_check_budget_permission_allows_subcategory_within_limit(client, session):
    """Budget Permission allows spend when subcategory limit is not exceeded."""
    user, _wallet, _headers = _seed_user_with_wallet(client, session, "bp6@example.com")
    today = user_timezone_today()

    budget = _create_budget_row(
        session, user.id, models.ExpenseCategory.GROCERIES, 1_000_000, today
    )
    subcategory = _create_subcategory(
        session, user.id, models.ExpenseCategory.GROCERIES, "Snacks"
    )
    _create_subcategory_limit(
        session, user.id, budget.id, subcategory.id, monthly_limit=200_000
    )

    result = check_budget_permission(
        session,
        BudgetPermissionRequest(
            user_id=user.id,
            category=models.ExpenseCategory.GROCERIES,
            amount=100_000,
            expense_date=today,
            subcategory=subcategory,
        ),
    )

    assert isinstance(result, BudgetPermissionResult)
    assert result.budget is not None
    assert result.subcategory is not None
    assert result.subcategory.id == subcategory.id


def test_check_budget_permission_preserves_overlay_project_category_check(
    client, session,
):
    """Budget Permission raises project_category_not_part_of_project when an
    overlay project has no reservation for the category in that month."""
    user, _wallet, _headers = _seed_user_with_wallet(client, session, "bp7@example.com")
    today = user_timezone_today()

    _create_budget_row(
        session, user.id, models.ExpenseCategory.GROCERIES, 1_000_000, today
    )
    project = _create_overlay_project(session, user.id, "Overlay Test")
    # Deliberately do NOT create a category reservation — the spend should fail.

    try:
        check_budget_permission(
            session,
            BudgetPermissionRequest(
                user_id=user.id,
                category=models.ExpenseCategory.GROCERIES,
                amount=50_000,
                expense_date=today,
                project=project,
            ),
        )
        assert False, "Expected HTTPException"
    except HTTPException as exc:
        assert exc.status_code == 400
        assert exc.detail == "budgets.project_category_not_part_of_project"


def test_check_budget_permission_allows_overlay_project_with_reservation(
    client, session,
):
    """Budget Permission allows spend when the overlay project has a valid
    category reservation for the month."""
    user, _wallet, _headers = _seed_user_with_wallet(client, session, "bp8@example.com")
    today = user_timezone_today()

    _create_budget_row(
        session, user.id, models.ExpenseCategory.GROCERIES, 1_000_000, today
    )
    project = _create_overlay_project(session, user.id, "Overlay With Reservation")

    reservation = models.OverlayProjectCategoryReservation(
        project_id=project.id,
        category=models.ExpenseCategory.GROCERIES,
        limit_amount=500_000,
        budget_year=today.year,
        budget_month=today.month,
    )
    session.add(reservation)
    session.commit()

    result = check_budget_permission(
        session,
        BudgetPermissionRequest(
            user_id=user.id,
            category=models.ExpenseCategory.GROCERIES,
            amount=50_000,
            expense_date=today,
            project=project,
        ),
    )

    assert isinstance(result, BudgetPermissionResult)
    assert result.budget is not None
    assert result.project is not None
    assert result.project.id == project.id


def test_check_budget_permission_result_carries_all_refs(client, session):
    """BudgetPermissionResult includes budget, subcategory, project, and
    project_subcategory so the caller does not need separate lookups."""
    user, _wallet, _headers = _seed_user_with_wallet(client, session, "bp9@example.com")
    today = user_timezone_today()

    budget = _create_budget_row(
        session, user.id, models.ExpenseCategory.GROCERIES, 1_000_000, today
    )
    subcategory = _create_subcategory(
        session, user.id, models.ExpenseCategory.GROCERIES, "TestSub"
    )
    _create_subcategory_limit(
        session, user.id, budget.id, subcategory.id, monthly_limit=200_000
    )

    result = check_budget_permission(
        session,
        BudgetPermissionRequest(
            user_id=user.id,
            category=models.ExpenseCategory.GROCERIES,
            amount=50_000,
            expense_date=today,
            subcategory=subcategory,
        ),
    )

    assert result.budget is not None
    assert result.budget.id == budget.id
    assert result.subcategory is not None
    assert result.subcategory.id == subcategory.id
    assert result.project is None
    assert result.project_subcategory is None


def test_check_budget_permission_enforce_monthly_budget_limits_false(
    client, session,
):
    """When enforce_monthly_budget_limits is False, no budget is resolved
    and no budget-required failure is raised."""
    user, _wallet, _headers = _seed_user_with_wallet(client, session, "bp10@example.com")
    today = user_timezone_today()

    result = check_budget_permission(
        session,
        BudgetPermissionRequest(
            user_id=user.id,
            category=models.ExpenseCategory.GROCERIES,
            amount=50_000,
            expense_date=today,
            enforce_monthly_budget_limits=False,
        ),
    )

    assert isinstance(result, BudgetPermissionResult)
    assert result.budget is None


# ---------------------------------------------------------------------------
# Integration tests — Budget Permission through Expense Posting
# ---------------------------------------------------------------------------


def test_post_expense_event_preserves_budget_required_through_permission(
    client, session,
):
    """post_expense_event still returns budget_required when called without
    a Budget row, proving the permission seam is wired correctly."""
    user, _wallet, _headers = _seed_user_with_wallet(client, session, "bp11@example.com")
    today = user_timezone_today()

    try:
        post_expense_event(
            session,
            user.id,
            title="No budget expense",
            amount=10_000,
            category=models.ExpenseCategory.GROCERIES,
            expense_date=today,
        )
        assert False, "Expected HTTPException"
    except HTTPException as exc:
        assert exc.status_code == 400
        assert exc.detail == "expenses.budget_required"


def test_post_expense_event_succeeds_through_permission_with_valid_budget(
    client, session,
):
    """post_expense_event creates a posted FinancialEvent when Budget Permission
    allows the spend."""
    user, wallet, _headers = _seed_user_with_wallet(client, session, "bp12@example.com")
    today = user_timezone_today()
    _create_budget_row(session, user.id, models.ExpenseCategory.GROCERIES, 1_000_000, today)

    balance_before = int(wallet.current_balance)

    result = post_expense_event(
        session,
        user.id,
        title="Valid expense through permission",
        amount=50_000,
        category=models.ExpenseCategory.GROCERIES,
        expense_date=today,
    )

    assert result.event is not None
    assert result.event.status == models.FinancialEventStatus.POSTED
    assert result.event.title == "Valid expense through permission"
    assert result.budget is not None
    assert result.budget.category == models.ExpenseCategory.GROCERIES
    # Wallet balance should have decreased by the expense amount
    session.refresh(wallet)
    assert wallet.current_balance == balance_before - 50_000


def test_post_expense_event_allows_overspend_through_permission(
    client, session,
):
    """post_expense_event allows spend above the monthly limit — limits are
    soft during posting; the plan reports over-planned status afterward."""
    user, wallet, _headers = _seed_user_with_wallet(client, session, "bp13@example.com")
    today = user_timezone_today()
    _create_budget_row(session, user.id, models.ExpenseCategory.GROCERIES, 50_000, today)

    balance_before = int(wallet.current_balance)

    result = post_expense_event(
        session,
        user.id,
        title="Over budget",
        amount=100_000,
        category=models.ExpenseCategory.GROCERIES,
        expense_date=today,
    )

    assert result.event is not None
    assert result.event.status == models.FinancialEventStatus.POSTED
    assert result.budget is not None
    session.refresh(wallet)
    assert wallet.current_balance == balance_before - 100_000


def test_post_expense_event_preserves_project_category_check_through_permission(
    client, session,
):
    """post_expense_event raises project_category_not_part_of_project when the
    overlay project has no reservation, routed through Budget Permission."""
    user, _wallet, _headers = _seed_user_with_wallet(client, session, "bp14@example.com")
    today = user_timezone_today()

    _create_budget_row(
        session, user.id, models.ExpenseCategory.GROCERIES, 1_000_000, today
    )
    project = _create_overlay_project(session, user.id, "Overlay No Reservation")

    try:
        post_expense_event(
            session,
            user.id,
            title="Project expense no reservation",
            amount=50_000,
            category=models.ExpenseCategory.GROCERIES,
            expense_date=today,
            project_id=project.id,
        )
        assert False, "Expected HTTPException"
    except HTTPException as exc:
        assert exc.status_code == 400
        assert exc.detail == "budgets.project_category_not_part_of_project"


def test_post_expense_event_allows_subcategory_overspend_through_permission(
    client, session,
):
    """post_expense_event allows spend above a subcategory limit — subcategory
    limits are soft during posting; budget detail reports red state afterward."""
    user, wallet, _headers = _seed_user_with_wallet(client, session, "bp15@example.com")
    today = user_timezone_today()

    budget = _create_budget_row(
        session, user.id, models.ExpenseCategory.GROCERIES, 1_000_000, today
    )
    subcategory = _create_subcategory(
        session, user.id, models.ExpenseCategory.GROCERIES, "Limited Sub"
    )
    _create_subcategory_limit(
        session, user.id, budget.id, subcategory.id, monthly_limit=10_000
    )

    balance_before = int(wallet.current_balance)

    result = post_expense_event(
        session,
        user.id,
        title="Subcategory overspend",
        amount=50_000,
        category=models.ExpenseCategory.GROCERIES,
        expense_date=today,
        subcategory_id=subcategory.id,
    )

    assert result.event is not None
    assert result.event.status == models.FinancialEventStatus.POSTED
    assert result.budget is not None
    assert result.subcategory is not None
    session.refresh(wallet)
    assert wallet.current_balance == balance_before - 50_000


# ============================================================================
# Issue 3 — Budget Month Summary remains stable after separation
# ============================================================================


def test_budget_month_summary_stable_covered_with_cushion(client, session):
    """Budget Month Summary reports covered_with_cushion when the plan is
    fully backed by free money, with cushion remaining."""
    headers = create_user_and_token(
        client, "bpsumm1", "bpsumm1@example.com", "Password123!"
    )
    today = user_timezone_today()

    created = client.post(
        "/budgets/",
        json={
            "category": "Groceries",
            "monthly_limit": 5_000_000,
            "budget_year": today.year,
            "budget_month": today.month,
        },
        headers=headers,
    )
    assert created.status_code == 201, created.text

    summary = client.get(
        f"/budgets/month-summary?budget_year={today.year}&budget_month={today.month}",
        headers=headers,
    )
    assert summary.status_code == 200, summary.text
    payload = summary.json()

    # Plan status — free money (10M) exceeds budget (5M) → cushion
    assert payload["plan_status"] == "covered_with_cushion"
    assert payload["backing_shortfall"] == 0
    assert payload["monthly_effective_limit_total"] == 5_000_000
    assert payload["free_money_now"] == 10_000_000
    assert payload["plan_free_money_remaining"] == 5_000_000

    # Key fields required by acceptance criteria must be present
    for key in (
        "owned_money_now",
        "protected_goal_money",
        "free_money_now",
        "expected_income_remaining",
        "valid_budget_spent",
        "backing_total",
        "backing_shortfall",
        "plan_status",
        "monthly_budget_limit_total",
        "monthly_effective_limit_total",
        "normal_budget_spent",
        "normal_budget_remaining",
        "category_floor_total",
        "category_floor_shortfall",
        "plan_free_money_remaining",
        "plan_backing_remaining",
        "cash_gap_to_budget_total",
        "categories_over_limit",
        "categories_close_to_limit",
        "borrowing_pressure",
        "cash_obligation_reserve_total",
        "cash_backing_total",
    ):
        assert key in payload, f"Missing key: {key}"


def test_budget_month_summary_stable_waiting_on_income(client, session):
    """Budget Month Summary reports waiting_on_income when the plan requires
    expected income to be fully backed."""
    headers = create_user_and_token(
        client, "bpsumm2", "bpsumm2@example.com", "Password123!"
    )
    today = user_timezone_today()

    # Create income source first
    source_res = client.post(
        "/income/sources",
        json={"name": "Salary"},
        headers=headers,
    )
    assert source_res.status_code == 201, source_res.text
    source_id = source_res.json()["id"]

    # Create expected income linked to the source
    client.post(
        "/budgets/expected-incomes",
        json={
            "source_id": source_id,
            "amount": 5_000_000,
            "due_date": today.isoformat(),
            "budget_year": today.year,
            "budget_month": today.month,
        },
        headers=headers,
    )

    # Budget above free money (10M) but within free + expected income (15M)
    created = client.post(
        "/budgets/",
        json={
            "category": "Groceries",
            "monthly_limit": 12_000_000,
            "budget_year": today.year,
            "budget_month": today.month,
        },
        headers=headers,
    )
    assert created.status_code == 201, created.text

    summary = client.get(
        f"/budgets/month-summary?budget_year={today.year}&budget_month={today.month}",
        headers=headers,
    )
    assert summary.status_code == 200, summary.text
    payload = summary.json()

    assert payload["plan_status"] == "waiting_on_income"
    assert payload["expected_income_remaining"] == 5_000_000
    assert payload["backing_shortfall"] == 0
    assert payload["backing_total"] == 15_000_000


def test_budget_month_summary_stable_over_planned(client, session):
    """Budget Month Summary reports over_planned when the plan exceeds
    available backing due to goal protection reducing free money."""
    headers = create_user_and_token(
        client, "bpsumm3", "bpsumm3@example.com", "Password123!"
    )
    today = user_timezone_today()
    user = session.query(models.User).filter(
        models.User.email == "bpsumm3@example.com"
    ).first()
    default_wallet = session.query(models.Wallet).filter(
        models.Wallet.owner_id == user.id, models.Wallet.is_default
    ).first()

    # Create budget within initial backing
    created = client.post(
        "/budgets/",
        json={
            "category": "Groceries",
            "monthly_limit": 9_000_000,
            "budget_year": today.year,
            "budget_month": today.month,
        },
        headers=headers,
    )
    assert created.status_code == 201, created.text

    # Add goal protection to reduce free money below the budget
    goal = models.Goals(
        owner_id=user.id,
        title="Emergency fund",
        target_amount=3_000_000,
        status=models.GoalStatus.ACTIVE,
    )
    session.add(goal)
    session.flush()
    session.add(
        models.GoalContributions(
            owner_id=user.id,
            goal_id=goal.id,
            wallet_id=default_wallet.id,
            amount=3_000_000,
            contribution_type=models.GoalContributionType.ALLOCATE,
        )
    )
    session.commit()

    summary = client.get(
        f"/budgets/month-summary?budget_year={today.year}&budget_month={today.month}",
        headers=headers,
    )
    assert summary.status_code == 200, summary.text
    payload = summary.json()

    assert payload["plan_status"] == "over_planned"
    assert payload["backing_shortfall"] > 0
    assert payload["monthly_effective_limit_total"] == 9_000_000
    # Free money reduced by goal protection: 10M - 3M = 7M < 9M budget
    assert payload["free_money_now"] == 7_000_000
    # category_floor fields must be present
    assert "category_floor_total" in payload
    assert "category_floor_shortfall" in payload
    assert "category_floors" in payload
    # borrowing pressure must be present
    assert "borrowing_pressure" in payload
    assert isinstance(payload["borrowing_pressure"], bool)
    # plan_causes must be present (at minimum BACKING_SHORTFALL)
    assert "plan_causes" in payload
    assert any(
        cause["code"] == "BACKING_SHORTFALL" for cause in payload["plan_causes"]
    )


def test_budget_permission_module_does_not_import_summary_functions():
    """Budget Permission module must not depend on Budget Month Summary or
    Project Budget View display functions."""
    import app.services.budget_permission_service as bps

    module_attrs = dir(bps)
    # Budget Permission must NOT expose summary/view functions
    assert "build_budget_month_summary" not in module_attrs
    assert "get_project_budget_summaries" not in module_attrs
    assert "build_project_detail" not in module_attrs

    # Verify the module's source doesn't import those functions
    import inspect
    source = inspect.getsource(bps)
    assert "build_budget_month_summary" not in source
    assert "get_project_budget_summaries" not in source


# ============================================================================
# Issue 4 — Project Budget View remains stable after separation
# ============================================================================


def test_project_budget_view_stable_overlay_project(client, session):
    """Project Budget View returns correct data for an Overlay Project
    with category reservations."""
    headers = create_user_and_token(
        client, "bpproj1", "bpproj1@example.com", "Password123!"
    )
    today = user_timezone_today()

    # Create overlay project
    project = client.post(
        "/projects",
        json={
            "title": "Work conference",
            "is_isolated": False,
            "start_date": today.isoformat(),
        },
        headers=headers,
    )
    assert project.status_code == 201, project.text
    project_id = project.json()["id"]

    # Create budget for the category
    client.post(
        "/budgets/",
        json={
            "category": "Transport",
            "monthly_limit": 1_000_000,
            "budget_year": today.year,
            "budget_month": today.month,
        },
        headers=headers,
    )

    # Add a category reservation to the overlay project
    reservation = client.post(
        f"/projects/{project_id}/category-limits",
        json={
            "category": "Transport",
            "limit_amount": 300_000,
            "budget_year": today.year,
            "budget_month": today.month,
        },
        headers=headers,
    )
    assert reservation.status_code == 201, reservation.text

    # Fetch project budget view
    projects = client.get("/budgets/projects", headers=headers)
    assert projects.status_code == 200, projects.text
    project_list = projects.json()
    assert isinstance(project_list, list)
    assert len(project_list) >= 1

    overlay = next(
        (p for p in project_list if p["id"] == project_id), None
    )
    assert overlay is not None, "Overlay project must appear in project budget view"
    assert overlay["project_type"] == "OVERLAY"
    assert overlay["is_isolated"] is False

    # Key fields that must remain stable
    for key in (
        "id", "title", "project_type", "is_isolated", "status",
        "spent", "remaining", "is_over_limit",
        "selected_budget_year", "selected_budget_month",
        "selected_month_reserved_amount", "total_reserved_scope",
        "category_breakdown", "created_at",
    ):
        assert key in overlay, f"Missing key in overlay project: {key}"

    # Overlay-specific financial block
    assert overlay["overlay"] is not None
    assert "target_estimate" in overlay["overlay"]
    assert "selected_month_reserved_amount" in overlay["overlay"]
    assert "total_reserved_scope" in overlay["overlay"]

    # Category breakdown must include the reserved category
    categories = overlay["category_breakdown"]
    assert len(categories) >= 1
    transport_cat = next(
        (c for c in categories if c["category"] == "Transport"), None
    )
    assert transport_cat is not None
    assert transport_cat["reserved_amount"] == 300_000
    assert "spent" in transport_cat
    assert "remaining" in transport_cat
    assert "is_over_limit" in transport_cat


def test_project_budget_view_stable_isolated_project(client, session):
    """Project Budget View preserves frozen Isolated Project data without
    introducing new mechanics."""
    headers = create_user_and_token(
        client, "bpproj2", "bpproj2@example.com", "Password123!"
    )
    today = user_timezone_today()

    # Create isolated project
    project = client.post(
        "/projects",
        json={
            "title": "Home renovation",
            "is_isolated": True,
            "total_limit": 2_000_000,
            "start_date": today.isoformat(),
            "category_allocations": [
                {"category": "Housing", "limit_amount": 1_000_000},
                {"category": "Electronics", "limit_amount": 500_000},
            ],
        },
        headers=headers,
    )
    assert project.status_code == 201, project.text
    project_id = project.json()["id"]

    # Post an expense against the isolated project
    client.post(
        "/expenses/",
        json={
            "title": "Paint supplies",
            "amount": 200_000,
            "category": "Housing",
            "date": today.isoformat(),
            "project_id": project_id,
        },
        headers=headers,
    )

    # Fetch project budget view
    projects = client.get("/budgets/projects", headers=headers)
    assert projects.status_code == 200, projects.text
    project_list = projects.json()

    isolated = next(
        (p for p in project_list if p["id"] == project_id), None
    )
    assert isolated is not None, "Isolated project must appear in project budget view"
    assert isolated["project_type"] == "ISOLATED"
    assert isolated["is_isolated"] is True
    assert isolated["spent"] == 200_000
    assert isolated["total_limit"] == 2_000_000
    assert isolated["progress_direction"] == "tick_down"

    # Isolated-specific financial block
    assert isolated["isolated"] is not None
    isolated_fin = isolated["isolated"]
    for key in (
        "funding_limit", "allocated_funding", "unallocated_funding",
        "released_funding", "remaining_funding", "funding_shortfall",
        "wallet_allocations",
    ):
        assert key in isolated_fin, f"Missing key in isolated financial: {key}"

    # Category breakdown for isolated project
    categories = isolated["category_breakdown"]
    assert len(categories) >= 1
    housing_cat = next(
        (c for c in categories if c["category"] == "Housing"), None
    )
    assert housing_cat is not None
    assert housing_cat["allocated_amount"] == 1_000_000
    assert housing_cat["spent"] == 200_000
    assert housing_cat["remaining"] == 800_000


def test_budget_permission_does_not_depend_on_project_view(client):
    """Budget Permission calls must not affect Project Budget View output —
    the two are separated concerns."""
    headers = create_user_and_token(
        client, "bpproj3", "bpproj3@example.com", "Password123!"
    )
    today = user_timezone_today()

    # Create budget and post expense (exercises Budget Permission)
    client.post(
        "/budgets/",
        json={
            "category": "Groceries",
            "monthly_limit": 1_000_000,
            "budget_year": today.year,
            "budget_month": today.month,
        },
        headers=headers,
    )
    client.post(
        "/expenses/",
        json={
            "title": "Weekly groceries",
            "amount": 100_000,
            "category": "Groceries",
            "date": today.isoformat(),
        },
        headers=headers,
    )
    client.post(
        "/expenses/",
        json={
            "title": "More groceries",
            "amount": 150_000,
            "category": "Groceries",
            "date": today.isoformat(),
        },
        headers=headers,
    )

    # Fetch project budget view — must still work correctly (empty list is fine)
    projects = client.get("/budgets/projects", headers=headers)
    assert projects.status_code == 200, projects.text
    assert isinstance(projects.json(), list)

    # Fetch budget month summary — must show correct spend
    summary = client.get(
        f"/budgets/month-summary?budget_year={today.year}&budget_month={today.month}",
        headers=headers,
    )
    assert summary.status_code == 200, summary.text
    payload = summary.json()
    assert payload["normal_budget_spent"] == 250_000
    assert payload["valid_budget_spent"] == 250_000
    assert payload["plan_status"] == "covered_with_cushion"
