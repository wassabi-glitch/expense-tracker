from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, selectinload

from .. import models, schemas
from ..services.budget_permission_service import (
    BudgetPermissionRequest,
    check_budget_permission,
)
from ..services.budget_service import (
    get_owned_project_or_404,
    get_owned_project_subcategory_or_404,
    get_owned_subcategory_or_404,
)
from ..services.financial_event_ledger_service import (
    PostEntityLeg,
    PostWalletLeg,
    post_financial_event,
)
from ..services.goal_funding_service import validate_wallet_goal_protection_for_outflow
from ..services.project_service import is_isolated_project
from app.domains.debt._debt_service import create_debt_ledger_entry


@dataclass
class SessionFinalizeResult:
    event: models.FinancialEvent
    budget_ids: set[int]


def get_owned_session_draft_or_404(
    db: Session,
    owner_id: int,
    draft_id: int,
    *,
    lock: bool = False,
) -> models.ExpenseSessionDraft:
    query = (
        db.query(models.ExpenseSessionDraft)
        .options(
            selectinload(models.ExpenseSessionDraft.items),
            selectinload(models.ExpenseSessionDraft.wallet_allocations).selectinload(
                models.ExpenseSessionDraftWalletAllocation.wallet
            ),
            selectinload(models.ExpenseSessionDraft.splits),
        )
        .filter(
            models.ExpenseSessionDraft.id == draft_id,
            models.ExpenseSessionDraft.owner_id == owner_id,
        )
    )
    if lock:
        query = query.with_for_update()
    draft = query.first()
    if not draft:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="expenses.session_draft_not_found")
    return draft


def get_owned_session_draft_item_or_404(
    db: Session,
    owner_id: int,
    draft_id: int,
    item_id: int,
) -> models.ExpenseSessionDraftItem:
    item = (
        db.query(models.ExpenseSessionDraftItem)
        .filter(
            models.ExpenseSessionDraftItem.id == item_id,
            models.ExpenseSessionDraftItem.draft_id == draft_id,
            models.ExpenseSessionDraftItem.owner_id == owner_id,
        )
        .first()
    )
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="expenses.session_draft_item_not_found")
    return item


def get_owned_session_wallet_allocation_or_404(
    db: Session,
    owner_id: int,
    draft_id: int,
    allocation_id: int,
) -> models.ExpenseSessionDraftWalletAllocation:
    allocation = (
        db.query(models.ExpenseSessionDraftWalletAllocation)
        .options(selectinload(models.ExpenseSessionDraftWalletAllocation.wallet))
        .filter(
            models.ExpenseSessionDraftWalletAllocation.id == allocation_id,
            models.ExpenseSessionDraftWalletAllocation.draft_id == draft_id,
            models.ExpenseSessionDraftWalletAllocation.owner_id == owner_id,
        )
        .first()
    )
    if not allocation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="expenses.session_draft_wallet_allocation_not_found",
        )
    return allocation


def get_owned_session_split_or_404(
    db: Session,
    owner_id: int,
    draft_id: int,
    split_id: int,
) -> models.ExpenseSessionDraftSplit:
    split = (
        db.query(models.ExpenseSessionDraftSplit)
        .filter(
            models.ExpenseSessionDraftSplit.id == split_id,
            models.ExpenseSessionDraftSplit.draft_id == draft_id,
            models.ExpenseSessionDraftSplit.owner_id == owner_id,
        )
        .first()
    )
    if not split:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="expenses.session_draft_split_not_found")
    return split


def ensure_draft_editable(draft: models.ExpenseSessionDraft) -> None:
    if draft.status == models.ExpenseSessionDraftStatus.FINALIZED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="expenses.session_draft_finalized")
    if draft.status == models.ExpenseSessionDraftStatus.ABANDONED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="expenses.session_draft_abandoned")


def validate_session_item_links(
    db: Session,
    owner_id: int,
    category: models.ExpenseCategory,
    subcategory_id: int | None,
    project_id: int | None,
    project_subcategory_id: int | None = None,
) -> tuple[models.UserSubcategory | None, models.Project | None, models.LegacyProjectSubcategory | None]:
    subcategory = None
    if subcategory_id is not None:
        subcategory = get_owned_subcategory_or_404(db, owner_id, subcategory_id)
        if subcategory.category != category:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="budgets.subcategory_category_mismatch")

    project = None
    if project_id is not None:
        project = get_owned_project_or_404(db, owner_id, project_id)

    project_subcategory = None
    if project_subcategory_id is not None:
        if project is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="projects.subcategory_project_required")
        if subcategory_id is not None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="projects.subcategory_modes_conflict")
        project_subcategory = get_owned_project_subcategory_or_404(db, owner_id, project.id, project_subcategory_id)
        if not is_isolated_project(project):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="projects.subcategories_isolated_only")
        if project_subcategory.category != category:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="projects.subcategory_category_mismatch")
        if not project_subcategory.is_active:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="projects.subcategory_inactive")

    return subcategory, project, project_subcategory


def _distribute_amounts(
    items: list[models.ExpenseSessionDraftItem],
    amount_paid: int | None,
    *,
    strict: bool = True,
) -> tuple[dict[int, int], int, int]:
    original_total = int(sum(int(item.original_amount) for item in items))
    if amount_paid is None:
        return ({item.id: int(item.original_amount) for item in items}, original_total, original_total)
    if original_total <= 0:
        if not strict:
            return ({item.id: int(item.original_amount) for item in items}, original_total, int(amount_paid))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="expenses.session_draft_empty")
    if amount_paid > original_total:
        if not strict:
            return ({item.id: int(item.original_amount) for item in items}, original_total, int(amount_paid))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="expenses.session_amount_exceeds_items")

    distributed: dict[int, int] = {}
    remainders: list[tuple[int, int, int]] = []
    assigned = 0
    ordered = sorted(items, key=lambda item: (int(item.sort_order or 0), int(item.id)))
    for item in ordered:
        numerator = int(item.original_amount) * int(amount_paid)
        base_amount = numerator // original_total
        remainder = numerator % original_total
        distributed[item.id] = int(base_amount)
        assigned += int(base_amount)
        remainders.append((remainder, int(item.sort_order or 0), int(item.id)))

    missing = int(amount_paid) - assigned
    for _, _, item_id in sorted(remainders, key=lambda value: (-value[0], value[1], value[2]))[:missing]:
        distributed[item_id] += 1

    return distributed, original_total, int(amount_paid)


def build_session_draft_out(draft: models.ExpenseSessionDraft) -> schemas.SessionDraftOut:
    distributed, original_total, adjusted_total = _distribute_amounts(
        list(draft.items),
        draft.amount_paid,
        strict=False,
    )
    item_outs = []
    for item in sorted(draft.items, key=lambda value: (int(value.sort_order or 0), int(value.id))):
        item_outs.append(
            schemas.SessionDraftItemOut(
                id=item.id,
                draft_id=item.draft_id,
                owner_id=item.owner_id,
                label=item.label,
                original_amount=int(item.original_amount),
                adjusted_amount=(
                    distributed.get(item.id)
                    if draft.amount_paid is None or original_total >= int(draft.amount_paid or 0)
                    else None
                ),
                category=item.category,
                subcategory_id=item.subcategory_id,
                project_id=item.project_id,
                project_subcategory_id=item.project_subcategory_id,
                sort_order=int(item.sort_order or 0),
                created_at=item.created_at,
                updated_at=item.updated_at,
            )
        )

    wallet_allocations = [
        schemas.SessionDraftWalletAllocationOut(
            id=allocation.id,
            draft_id=allocation.draft_id,
            owner_id=allocation.owner_id,
            wallet_id=allocation.wallet_id,
            amount=int(allocation.amount),
            wallet=schemas.WalletOut.model_validate(allocation.wallet) if allocation.wallet else None,
            created_at=allocation.created_at,
            updated_at=allocation.updated_at,
        )
        for allocation in draft.wallet_allocations
    ]
    split_outs = [schemas.SessionDraftSplitOut.model_validate(split) for split in draft.splits]

    allocated_wallet_total = int(sum(int(allocation.amount) for allocation in draft.wallet_allocations))
    split_total = int(sum(int(split.amount) for split in draft.splits))
    discount_amount = (
        original_total - adjusted_total
        if draft.amount_paid is not None and original_total >= adjusted_total
        else None
    )
    can_finalize = (
        draft.status in {models.ExpenseSessionDraftStatus.ACTIVE, models.ExpenseSessionDraftStatus.PAUSED}
        and bool(draft.items)
        and draft.amount_paid is not None
        and allocated_wallet_total == int(draft.amount_paid)
        and split_total <= int(draft.amount_paid)
        and int(draft.amount_paid) <= original_total
    )

    return schemas.SessionDraftOut(
        id=draft.id,
        owner_id=draft.owner_id,
        title=draft.title,
        description=draft.description,
        date=draft.date,
        amount_paid=int(draft.amount_paid) if draft.amount_paid is not None else None,
        status=draft.status,
        source_type=draft.source_type,
        raw_ocr_text=draft.raw_ocr_text,
        finalized_event_id=draft.finalized_event_id,
        created_at=draft.created_at,
        updated_at=draft.updated_at,
        items=item_outs,
        wallet_allocations=wallet_allocations,
        splits=split_outs,
        original_total=original_total,
        allocated_wallet_total=allocated_wallet_total,
        split_total=split_total,
        discount_amount=discount_amount,
        remaining_wallet_allocation=(
            int(draft.amount_paid) - allocated_wallet_total if draft.amount_paid is not None else None
        ),
        can_finalize=can_finalize,
    )


def finalize_session_draft(
    db: Session,
    owner_id: int,
    draft_id: int,
    local_today: date | None = None,
) -> SessionFinalizeResult:
    draft = get_owned_session_draft_or_404(db, owner_id, draft_id, lock=True)
    ensure_draft_editable(draft)

    if local_today is not None and draft.date > local_today:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="expenses.date_in_future")

    items = sorted(list(draft.items), key=lambda item: (int(item.sort_order or 0), int(item.id)))
    if not items:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="expenses.session_draft_empty")
    if draft.amount_paid is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="expenses.amount_required")
    if not draft.wallet_allocations:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="expenses.session_wallets_required")

    distributed, original_total, adjusted_total = _distribute_amounts(items, int(draft.amount_paid), strict=True)
    if adjusted_total != int(draft.amount_paid):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="expenses.session_distribution_failed")

    wallet_total = int(sum(int(allocation.amount) for allocation in draft.wallet_allocations))
    if wallet_total != int(draft.amount_paid):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="expenses.session_wallet_total_mismatch")

    split_total = int(sum(int(split.amount) for split in draft.splits))
    if split_total > int(draft.amount_paid):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="expenses.splits_exceed_total")

    wallet_currency: str | None = None
    for allocation in draft.wallet_allocations:
        wallet = allocation.wallet
        if wallet is None:
            wallet = (
                db.query(models.Wallet)
                .filter(
                    models.Wallet.id == allocation.wallet_id,
                    models.Wallet.owner_id == owner_id,
                )
                .with_for_update()
                .first()
            )
        if not wallet:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="wallets.not_found")
        if not wallet.is_active:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="wallets.archived_locked")
        if wallet_currency is None:
            wallet_currency = wallet.currency
        elif wallet.currency != wallet_currency:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="expenses.session_wallet_currency_mismatch")
        validate_wallet_goal_protection_for_outflow(
            db,
            owner_id,
            wallet,
            int(allocation.amount),
            outflow_type="session_expense",
        )

    validated_items: list[
        tuple[
            models.ExpenseSessionDraftItem,
            int,
            models.UserSubcategory | None,
            models.Project | None,
            models.LegacyProjectSubcategory | None,
            models.Budget | None,
        ]
    ] = []
    grouped_budget_amounts: dict[int, int] = {}
    grouped_subcategory_amounts: dict[int, int] = {}
    grouped_project_amounts: dict[tuple[int, models.ExpenseCategory], int] = {}
    subcategories: dict[int, models.UserSubcategory] = {}
    projects: dict[int, models.Project] = {}

    for item in items:
        adjusted_amount = int(distributed[item.id])
        subcategory, project, project_subcategory = validate_session_item_links(
            db, owner_id, item.category, item.subcategory_id, item.project_id, item.project_subcategory_id
        )
        permission = check_budget_permission(
            db,
            BudgetPermissionRequest(
                user_id=owner_id,
                category=item.category,
                amount=adjusted_amount,
                expense_date=draft.date,
                subcategory=subcategory,
                project=project,
                project_subcategory=project_subcategory,
                enforce_monthly_budget_limits=(
                    project is None or not is_isolated_project(project)
                ),
            ),
        )
        budget = permission.budget
        if budget is not None:
            grouped_budget_amounts[budget.id] = grouped_budget_amounts.get(budget.id, 0) + adjusted_amount
        if subcategory is not None:
            subcategories[subcategory.id] = subcategory
            grouped_subcategory_amounts[subcategory.id] = (
                grouped_subcategory_amounts.get(subcategory.id, 0) + adjusted_amount
            )
        if project is not None:
            projects[project.id] = project
            key = (project.id, item.category)
            grouped_project_amounts[key] = grouped_project_amounts.get(key, 0) + adjusted_amount
        validated_items.append((item, adjusted_amount, subcategory, project, project_subcategory, budget))

    for (project_id, category), amount in grouped_project_amounts.items():
        project_subcategory = next(
            (
                project_subcategory
                for item, _, _, project, project_subcategory, _ in validated_items
                if project is not None
                and project.id == project_id
                and item.category == category
                and project_subcategory is not None
            ),
            None,
        )
        check_budget_permission(
            db,
            BudgetPermissionRequest(
                user_id=owner_id,
                category=category,
                amount=amount,
                expense_date=draft.date,
                project=projects[project_id],
                project_subcategory=project_subcategory,
            ),
        )

    wallet_legs: list[PostWalletLeg] = []
    for allocation in draft.wallet_allocations:
        wallet_legs.append(
            PostWalletLeg(
                wallet_id=allocation.wallet_id,
                amount=-int(allocation.amount),
            )
        )

    budget_ids: set[int] = set()
    has_discount = original_total != adjusted_total
    entity_legs: list[PostEntityLeg] = []
    for item, adjusted_amount, subcategory, project, project_subcategory, budget in validated_items:
        if budget is not None:
            budget_ids.add(int(budget.id))
        entity_legs.append(
            PostEntityLeg(
                label=item.label.strip(),
                amount=adjusted_amount,
                original_amount=int(item.original_amount) if has_discount else None,
                category=item.category,
                subcategory_id=subcategory.id if subcategory is not None else None,
                project_id=project.id if project is not None else None,
                project_subcategory_id=project_subcategory.id if project_subcategory is not None else None,
                budget_id=budget.id if budget is not None else None,
            )
        )

    event = post_financial_event(
        db,
        owner_id=owner_id,
        title=draft.title,
        event_type=models.TransactionType.EXPENSE,
        date=draft.date,
        description=draft.description,
        is_session=True,
        discount_amount=(original_total - adjusted_total) if original_total != adjusted_total else None,
        entity_category=None,
        wallet_legs=wallet_legs,
        entity_legs=entity_legs,
    )

    for split in draft.splits:
        db.add(
            models.Debt(
                owner_id=owner_id,
                debt_type=models.DebtType.OWED,
                origin_kind=models.DebtOriginKind.SPLIT_REIMBURSEMENT,
                counterparty_kind=models.DebtCounterpartyKind.PERSON,
                counterparty_name=split.contact_name,
                initial_amount=int(split.amount),
                remaining_amount=int(split.amount),
                currency=wallet_currency or "UZS",
                description=draft.title,
                date=draft.date,
                expected_return_date=draft.date,
                linked_event_id=event.id,
            )
        )

    draft.status = models.ExpenseSessionDraftStatus.FINALIZED
    draft.finalized_event_id = event.id
    db.flush()
    split_debts = (
        db.query(models.Debt)
        .filter(
            models.Debt.owner_id == owner_id,
            models.Debt.linked_event_id == event.id,
            models.Debt.origin_kind == models.DebtOriginKind.SPLIT_REIMBURSEMENT,
        )
        .all()
    )
    for split_debt in split_debts:
        create_debt_ledger_entry(
            db,
            owner_id=owner_id,
            debt_id=split_debt.id,
            entry_type=models.DebtLedgerEntryType.INITIAL,
            amount_delta=int(split_debt.initial_amount),
            principal_delta=int(split_debt.initial_amount),
            financial_event_id=event.id,
            entry_date=split_debt.date,
            note=f"Initial split reimbursement from {split_debt.counterparty_name}",
        )
    return SessionFinalizeResult(event=event, budget_ids=budget_ids)
