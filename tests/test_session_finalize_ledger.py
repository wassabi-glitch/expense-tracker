"""Regression tests for Issue 2: Route session draft finalization through
the FinancialEventLedger seam.

Verifies that session draft finalization now exercises the shared ledger seam
without asserting private helper call order.
"""

from app import models
from tests.helpers import create_user_and_token, create_budget, user_timezone_today


def _get_default_wallet(session, email: str) -> int:
    user = session.query(models.User).filter(models.User.email == email).first()
    wallet = session.query(models.Wallet).filter(
        models.Wallet.owner_id == user.id,
        models.Wallet.is_default,
    ).first()
    return wallet.id


# ---------------------------------------------------------------------------
# End-to-end session draft finalization
# ---------------------------------------------------------------------------


def test_session_finalize_creates_posted_event_through_ledger_seam(client, session):
    """Finalizing a valid session draft creates one posted expense-shaped
    FinancialEvent with is_session=True."""
    headers = create_user_and_token(
        client, "sessionregress1", "sessionregress1@example.com", "Password123!"
    )
    create_budget(client, headers, category="Groceries", monthly_limit=1_000_000)
    wallet_id = _get_default_wallet(session, "sessionregress1@example.com")

    draft_res = client.post(
        "/expenses/session-drafts",
        json={
            "title": "Market run",
            "date": user_timezone_today().isoformat(),
            "amount_paid": 200_000,
        },
        headers=headers,
    )
    assert draft_res.status_code == 201, draft_res.text
    draft_id = draft_res.json()["id"]

    client.post(
        f"/expenses/session-drafts/{draft_id}/items",
        json={"label": "Groceries", "original_amount": 200_000, "category": "Groceries"},
        headers=headers,
    )
    client.post(
        f"/expenses/session-drafts/{draft_id}/wallet-allocations",
        json={"wallet_id": wallet_id, "amount": 200_000},
        headers=headers,
    )

    final = client.post(f"/expenses/session-drafts/{draft_id}/finalize", headers=headers)
    assert final.status_code == 201, final.text
    data = final.json()
    assert data["is_session"] is True
    assert data["title"] == "Market run"
    assert data["amount"] == 200_000
    assert data["category"] == "Groceries"

    session.expire_all()
    event = session.query(models.FinancialEvent).filter(
        models.FinancialEvent.id == data["id"],
    ).first()
    assert event is not None
    assert event.event_type == models.TransactionType.EXPENSE
    assert event.status == models.FinancialEventStatus.POSTED
    assert event.is_session is True


def test_session_finalize_creates_one_wallet_ledger_per_allocation(client, session):
    """Each wallet allocation produces exactly one WalletLedger entry with
    the correct negative amount."""
    headers = create_user_and_token(
        client, "sessionregress2", "sessionregress2@example.com", "Password123!"
    )
    create_budget(client, headers, category="Groceries", monthly_limit=1_000_000)
    wallet_id = _get_default_wallet(session, "sessionregress2@example.com")

    draft = client.post(
        "/expenses/session-drafts",
        json={
            "title": "Basket",
            "date": user_timezone_today().isoformat(),
            "amount_paid": 150_000,
        },
        headers=headers,
    )
    assert draft.status_code == 201, draft.text
    draft_id = draft.json()["id"]

    client.post(
        f"/expenses/session-drafts/{draft_id}/items",
        json={"label": "Food", "original_amount": 150_000, "category": "Groceries"},
        headers=headers,
    )
    client.post(
        f"/expenses/session-drafts/{draft_id}/wallet-allocations",
        json={"wallet_id": wallet_id, "amount": 150_000},
        headers=headers,
    )

    final = client.post(f"/expenses/session-drafts/{draft_id}/finalize", headers=headers)
    assert final.status_code == 201, final.text
    event_id = final.json()["id"]

    session.expire_all()
    event = session.query(models.FinancialEvent).filter(
        models.FinancialEvent.id == event_id,
    ).first()
    assert len(event.wallet_legs) == 1
    leg = event.wallet_legs[0]
    assert leg.wallet_id == wallet_id
    assert leg.amount == -150_000
    assert leg.owned_spend_amount is not None
    assert leg.borrowed_spend_amount is not None

    updated_wallet = session.query(models.Wallet).filter(
        models.Wallet.id == wallet_id,
    ).first()
    assert updated_wallet.current_balance == 10_000_000 - 150_000


def test_session_finalize_multi_item_creates_multi_entity_legs(client, session):
    """Multi-item sessions create one EntityLedger row per item with the
    correct label, adjusted amount, category, and budget link."""
    headers = create_user_and_token(
        client, "sessionregress3", "sessionregress3@example.com", "Password123!"
    )
    create_budget(client, headers, category="Groceries", monthly_limit=1_000_000)
    create_budget(client, headers, category="Utilities", monthly_limit=500_000)
    wallet_id = _get_default_wallet(session, "sessionregress3@example.com")

    draft = client.post(
        "/expenses/session-drafts",
        json={
            "title": "Multi-category receipt",
            "date": user_timezone_today().isoformat(),
            "amount_paid": 300_000,
        },
        headers=headers,
    )
    assert draft.status_code == 201, draft.text
    draft_id = draft.json()["id"]

    client.post(
        f"/expenses/session-drafts/{draft_id}/items",
        json={"label": "Groceries", "original_amount": 200_000, "category": "Groceries"},
        headers=headers,
    )
    client.post(
        f"/expenses/session-drafts/{draft_id}/items",
        json={"label": "Cleaning supplies", "original_amount": 100_000, "category": "Utilities"},
        headers=headers,
    )
    client.post(
        f"/expenses/session-drafts/{draft_id}/wallet-allocations",
        json={"wallet_id": wallet_id, "amount": 300_000},
        headers=headers,
    )

    final = client.post(f"/expenses/session-drafts/{draft_id}/finalize", headers=headers)
    assert final.status_code == 201, final.text
    event_id = final.json()["id"]

    session.expire_all()
    event = session.query(models.FinancialEvent).filter(
        models.FinancialEvent.id == event_id,
    ).first()
    assert len(event.entity_legs) == 2
    assert sorted(
        (leg.label, int(leg.amount), leg.category.value) for leg in event.entity_legs
    ) == [
        ("Cleaning supplies", 100_000, "Utilities"),
        ("Groceries", 200_000, "Groceries"),
    ]
    for leg in event.entity_legs:
        assert leg.budget_id is not None


def test_session_finalize_preserves_discount_original_amounts(client, session):
    """When amount_paid < sum(original_amounts), EntityLedger entries
    preserve the pre-discount original_amount."""
    headers = create_user_and_token(
        client, "sessionregress4", "sessionregress4@example.com", "Password123!"
    )
    create_budget(client, headers, category="Groceries", monthly_limit=1_000_000)
    wallet_id = _get_default_wallet(session, "sessionregress4@example.com")

    draft = client.post(
        "/expenses/session-drafts",
        json={
            "title": "Discounted order",
            "date": user_timezone_today().isoformat(),
            "amount_paid": 80_000,
        },
        headers=headers,
    )
    assert draft.status_code == 201, draft.text
    draft_id = draft.json()["id"]

    client.post(
        f"/expenses/session-drafts/{draft_id}/items",
        json={"label": "Original price item", "original_amount": 100_000, "category": "Groceries"},
        headers=headers,
    )
    client.post(
        f"/expenses/session-drafts/{draft_id}/wallet-allocations",
        json={"wallet_id": wallet_id, "amount": 80_000},
        headers=headers,
    )

    final = client.post(f"/expenses/session-drafts/{draft_id}/finalize", headers=headers)
    assert final.status_code == 201, final.text
    event_id = final.json()["id"]

    session.expire_all()
    event = session.query(models.FinancialEvent).filter(
        models.FinancialEvent.id == event_id,
    ).first()
    assert event.discount_amount == 20_000  # 100k - 80k
    leg = event.entity_legs[0]
    assert leg.amount == 80_000  # adjusted (paid) amount
    assert leg.original_amount == 100_000  # pre-discount


def test_session_finalize_creates_split_reimbursement_debts(client, session):
    """Split reimbursement Debts and their DebtLedger entries are created
    when session splits are present."""
    headers = create_user_and_token(
        client, "sessionregress5", "sessionregress5@example.com", "Password123!"
    )
    create_budget(client, headers, category="Dining Out", monthly_limit=1_000_000)
    wallet_id = _get_default_wallet(session, "sessionregress5@example.com")

    draft = client.post(
        "/expenses/session-drafts",
        json={
            "title": "Group dinner",
            "date": user_timezone_today().isoformat(),
            "amount_paid": 200_000,
        },
        headers=headers,
    )
    assert draft.status_code == 201, draft.text
    draft_id = draft.json()["id"]

    client.post(
        f"/expenses/session-drafts/{draft_id}/items",
        json={"label": "Dinner", "original_amount": 200_000, "category": "Dining Out"},
        headers=headers,
    )
    client.post(
        f"/expenses/session-drafts/{draft_id}/wallet-allocations",
        json={"wallet_id": wallet_id, "amount": 200_000},
        headers=headers,
    )
    client.post(
        f"/expenses/session-drafts/{draft_id}/splits",
        json={"contact_name": "Alice", "amount": 100_000},
        headers=headers,
    )
    client.post(
        f"/expenses/session-drafts/{draft_id}/splits",
        json={"contact_name": "Bob", "amount": 50_000},
        headers=headers,
    )

    final = client.post(f"/expenses/session-drafts/{draft_id}/finalize", headers=headers)
    assert final.status_code == 201, final.text
    event_id = final.json()["id"]

    session.expire_all()
    splits = session.query(models.Debt).filter(
        models.Debt.linked_event_id == event_id,
        models.Debt.origin_kind == models.DebtOriginKind.SPLIT_REIMBURSEMENT,
    ).all()
    assert len(splits) == 2
    assert sorted((s.counterparty_name, int(s.initial_amount)) for s in splits) == [
        ("Alice", 100_000),
        ("Bob", 50_000),
    ]
    for debt in splits:
        assert debt.remaining_amount == debt.initial_amount
        assert debt.remaining_amount > 0  # open lifecycle (ADR 0026)
        ledgers = session.query(models.DebtLedgerEntry).filter(
            models.DebtLedgerEntry.debt_id == debt.id,
        ).all()
        assert len(ledgers) == 1
        assert ledgers[0].entry_type == models.DebtLedgerEntryType.INITIAL


def test_session_finalize_updates_draft_status_and_linkage(client, session):
    """Session draft status and finalized_event_id are updated exactly once."""
    headers = create_user_and_token(
        client, "sessionregress6", "sessionregress6@example.com", "Password123!"
    )
    create_budget(client, headers, category="Groceries", monthly_limit=1_000_000)
    wallet_id = _get_default_wallet(session, "sessionregress6@example.com")

    draft = client.post(
        "/expenses/session-drafts",
        json={
            "title": "Single item",
            "date": user_timezone_today().isoformat(),
            "amount_paid": 50_000,
        },
        headers=headers,
    )
    assert draft.status_code == 201, draft.text
    draft_id = draft.json()["id"]

    client.post(
        f"/expenses/session-drafts/{draft_id}/items",
        json={"label": "Item", "original_amount": 50_000, "category": "Groceries"},
        headers=headers,
    )
    client.post(
        f"/expenses/session-drafts/{draft_id}/wallet-allocations",
        json={"wallet_id": wallet_id, "amount": 50_000},
        headers=headers,
    )

    final = client.post(f"/expenses/session-drafts/{draft_id}/finalize", headers=headers)
    assert final.status_code == 201, final.text
    event_id = final.json()["id"]

    session.expire_all()
    updated_draft = session.query(models.ExpenseSessionDraft).filter(
        models.ExpenseSessionDraft.id == draft_id,
    ).first()
    assert updated_draft.status == models.ExpenseSessionDraftStatus.FINALIZED
    assert updated_draft.finalized_event_id == event_id

    second_finalize = client.post(f"/expenses/session-drafts/{draft_id}/finalize", headers=headers)
    assert second_finalize.status_code == 400
    assert second_finalize.json()["detail"] == "expenses.session_draft_finalized"


def test_session_finalize_preserves_project_links_in_entity_ledger(client, session):
    """Entity Ledger entries preserve project and project subcategory links
    from session items."""
    headers = create_user_and_token(
        client, "sessionregress7", "sessionregress7@example.com", "Password123!"
    )
    wallet_id = _get_default_wallet(session, "sessionregress7@example.com")

    project = client.post(
        "/projects",
        json={
            "title": "Renovation",
            "is_isolated": True,
            "total_limit": 2_000_000,
            "start_date": "2026-06-01",
            "target_end_date": "2026-07-31",
        },
        headers=headers,
    )
    assert project.status_code == 201, project.text
    project_id = project.json()["id"]

    client.post(
        f"/projects/{project_id}/category-limits",
        json={"category": "Housing", "limit_amount": 2_000_000},
        headers=headers,
    )

    draft = client.post(
        "/expenses/session-drafts",
        json={
            "title": "Paint supplies",
            "date": "2026-07-01",
            "amount_paid": 120_000,
        },
        headers=headers,
    )
    assert draft.status_code == 201, draft.text
    draft_id = draft.json()["id"]

    client.post(
        f"/expenses/session-drafts/{draft_id}/items",
        json={
            "label": "Paint",
            "original_amount": 100_000,
            "category": "Housing",
            "project_id": project_id,
        },
        headers=headers,
    )
    client.post(
        f"/expenses/session-drafts/{draft_id}/items",
        json={
            "label": "Brushes",
            "original_amount": 20_000,
            "category": "Housing",
            "project_id": project_id,
        },
        headers=headers,
    )
    client.post(
        f"/expenses/session-drafts/{draft_id}/wallet-allocations",
        json={"wallet_id": wallet_id, "amount": 120_000},
        headers=headers,
    )

    final = client.post(f"/expenses/session-drafts/{draft_id}/finalize", headers=headers)
    assert final.status_code == 201, final.text
    event_id = final.json()["id"]

    session.expire_all()
    event = session.query(models.FinancialEvent).filter(
        models.FinancialEvent.id == event_id,
    ).first()
    for leg in event.entity_legs:
        assert leg.project_id == project_id


def test_session_finalize_rejects_budget_required(client, session):
    """Budget-required failure remains unchanged."""
    headers = create_user_and_token(
        client, "sessionbudget", "sessionbudget@example.com", "Password123!"
    )
    wallet_id = _get_default_wallet(session, "sessionbudget@example.com")

    draft = client.post(
        "/expenses/session-drafts",
        json={
            "title": "No budget draft",
            "date": user_timezone_today().isoformat(),
            "amount_paid": 10_000,
        },
        headers=headers,
    )
    assert draft.status_code == 201, draft.text
    draft_id = draft.json()["id"]

    client.post(
        f"/expenses/session-drafts/{draft_id}/items",
        json={"label": "Item", "original_amount": 10_000, "category": "Groceries"},
        headers=headers,
    )
    client.post(
        f"/expenses/session-drafts/{draft_id}/wallet-allocations",
        json={"wallet_id": wallet_id, "amount": 10_000},
        headers=headers,
    )

    blocked = client.post(f"/expenses/session-drafts/{draft_id}/finalize", headers=headers)
    assert blocked.status_code == 400
    assert blocked.json()["detail"] == "expenses.budget_required"


def test_session_finalize_rejects_wallet_total_mismatch(client, session):
    """Wallet-total mismatch validation remains unchanged."""
    headers = create_user_and_token(
        client, "sessionwallettotal", "sessionwallettotal@example.com", "Password123!"
    )
    create_budget(client, headers, category="Groceries", monthly_limit=500_000)
    wallet_id = _get_default_wallet(session, "sessionwallettotal@example.com")

    draft = client.post(
        "/expenses/session-drafts",
        json={
            "title": "Mismatch draft",
            "date": user_timezone_today().isoformat(),
            "amount_paid": 10_000,
        },
        headers=headers,
    )
    assert draft.status_code == 201, draft.text
    draft_id = draft.json()["id"]

    client.post(
        f"/expenses/session-drafts/{draft_id}/items",
        json={"label": "Item", "original_amount": 10_000, "category": "Groceries"},
        headers=headers,
    )
    client.post(
        f"/expenses/session-drafts/{draft_id}/wallet-allocations",
        json={"wallet_id": wallet_id, "amount": 9_000},  # mismatch
        headers=headers,
    )

    blocked = client.post(f"/expenses/session-drafts/{draft_id}/finalize", headers=headers)
    assert blocked.status_code == 400
    assert blocked.json()["detail"] == "expenses.session_wallet_total_mismatch"


def test_session_finalize_rejects_split_total_exceeds(client, session):
    """Split-total-exceeds validation remains unchanged."""
    headers = create_user_and_token(
        client, "sessionsplitover", "sessionsplitover@example.com", "Password123!"
    )
    create_budget(client, headers, category="Groceries", monthly_limit=500_000)
    wallet_id = _get_default_wallet(session, "sessionsplitover@example.com")

    draft = client.post(
        "/expenses/session-drafts",
        json={
            "title": "Oversplit draft",
            "date": user_timezone_today().isoformat(),
            "amount_paid": 10_000,
        },
        headers=headers,
    )
    assert draft.status_code == 201, draft.text
    draft_id = draft.json()["id"]

    client.post(
        f"/expenses/session-drafts/{draft_id}/items",
        json={"label": "Item", "original_amount": 10_000, "category": "Groceries"},
        headers=headers,
    )
    client.post(
        f"/expenses/session-drafts/{draft_id}/wallet-allocations",
        json={"wallet_id": wallet_id, "amount": 10_000},
        headers=headers,
    )
    client.post(
        f"/expenses/session-drafts/{draft_id}/splits",
        json={"contact_name": "Alice", "amount": 15_000},  # > amount_paid
        headers=headers,
    )

    blocked = client.post(f"/expenses/session-drafts/{draft_id}/finalize", headers=headers)
    assert blocked.status_code == 400
    assert blocked.json()["detail"] == "expenses.splits_exceed_total"
