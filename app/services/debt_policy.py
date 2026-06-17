from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

from sqlalchemy import exists
from sqlalchemy.orm import Session

from .. import models
from .debt_service import POSTED_DEBT_LEDGER_STATUS


OPEN_DEBT_STATUSES = {
    models.DebtStatus.ACTIVE,
    models.DebtStatus.OVERDUE,
    models.DebtStatus.DEFAULTED,
    models.DebtStatus.IN_COLLECTION,
}

CLOSED_DEBT_STATUSES = {
    models.DebtStatus.PAID,
    models.DebtStatus.SETTLED,
    models.DebtStatus.FORGIVEN,
    models.DebtStatus.WRITTEN_OFF,
}

FORMAL_PRODUCT_KINDS = {
    models.DebtProductKind.BANK_LOAN,
    models.DebtProductKind.CAR_LOAN,
    models.DebtProductKind.MORTGAGE,
    models.DebtProductKind.STORE_INSTALLMENT,
    models.DebtProductKind.SERVICE_PAY_LATER,
}

INFORMAL_ORIGIN_KINDS = {
    models.DebtOriginKind.CASH_BORROWED,
    models.DebtOriginKind.CASH_LENT,
    models.DebtOriginKind.DEFERRED_EXPENSE,
    models.DebtOriginKind.SPLIT_REIMBURSEMENT,
    models.DebtOriginKind.PERSONAL_REIMBURSEMENT,
    models.DebtOriginKind.DAMAGE_COMPENSATION,
}

REVERSIBLE_ENTRY_TYPES = {
    models.DebtLedgerEntryType.CHARGE,
    models.DebtLedgerEntryType.PAYMENT,
    models.DebtLedgerEntryType.FORGIVENESS,
    models.DebtLedgerEntryType.ADJUSTMENT,
    models.DebtLedgerEntryType.ASSET_SETTLEMENT,
}

PAYMENT_PLAN_MANAGED_ACTIONS = {
    models.DebtActionKind.RECORD_PAYMENT,
    models.DebtActionKind.ADD_CHARGE,
    models.DebtActionKind.FORGIVE_PARTIAL,
    models.DebtActionKind.FORGIVE_FULL,
    models.DebtActionKind.ADJUST_BALANCE,
    models.DebtActionKind.REVERSE_ENTRY,
    models.DebtActionKind.SETTLE,
    models.DebtActionKind.LINK_ASSET,
    models.DebtActionKind.SET_COLLATERAL,
    models.DebtActionKind.RESTRUCTURE_TERMS,
}


@dataclass(frozen=True)
class DebtActionDecision:
    action_kind: models.DebtActionKind
    allowed: bool
    reason_code: str | None = None
    level: models.DebtActionRestrictionLevel | None = None
    requires_confirmation: bool = False
    undo_available: bool = True
    source: models.DebtActionRestrictionSource = models.DebtActionRestrictionSource.POLICY
    details: dict = field(default_factory=dict)

    def blocked(
        self,
        reason_code: str,
        *,
        level: models.DebtActionRestrictionLevel = models.DebtActionRestrictionLevel.BLOCKED,
        source: models.DebtActionRestrictionSource = models.DebtActionRestrictionSource.POLICY,
        details: dict | None = None,
    ) -> "DebtActionDecision":
        return DebtActionDecision(
            action_kind=self.action_kind,
            allowed=False,
            reason_code=reason_code,
            level=level,
            requires_confirmation=self.requires_confirmation,
            undo_available=self.undo_available,
            source=source,
            details=details or self.details,
        )

    def with_confirmation(
        self,
        reason_code: str,
        *,
        source: models.DebtActionRestrictionSource = models.DebtActionRestrictionSource.POLICY,
        details: dict | None = None,
    ) -> "DebtActionDecision":
        return DebtActionDecision(
            action_kind=self.action_kind,
            allowed=self.allowed,
            reason_code=reason_code,
            level=models.DebtActionRestrictionLevel.REQUIRES_CONFIRMATION,
            requires_confirmation=True,
            undo_available=self.undo_available,
            source=source,
            details=details or self.details,
        )

    def without_undo(
        self,
        reason_code: str,
        *,
        source: models.DebtActionRestrictionSource = models.DebtActionRestrictionSource.POLICY,
        details: dict | None = None,
    ) -> "DebtActionDecision":
        return DebtActionDecision(
            action_kind=self.action_kind,
            allowed=self.allowed,
            reason_code=reason_code,
            level=models.DebtActionRestrictionLevel.UNDO_UNAVAILABLE,
            requires_confirmation=self.requires_confirmation,
            undo_available=False,
            source=source,
            details=details or self.details,
        )

    def to_dict(self) -> dict:
        return {
            "action_kind": self.action_kind.value,
            "allowed": self.allowed,
            "reason_code": self.reason_code,
            "level": self.level.value if self.level else None,
            "requires_confirmation": self.requires_confirmation,
            "undo_available": self.undo_available,
            "source": self.source.value,
            "details": self.details,
        }


def _as_value(value):
    return value.value if hasattr(value, "value") else value


def is_formal_debt(debt: models.Debt) -> bool:
    product_kind = _as_value(debt.product_kind)
    counterparty_kind = _as_value(debt.counterparty_kind)
    return (
        product_kind in {item.value for item in FORMAL_PRODUCT_KINDS}
        or counterparty_kind in {
            models.DebtCounterpartyKind.BANK.value,
            models.DebtCounterpartyKind.GOVERNMENT.value,
        }
        or debt.formal_details is not None
    )


def is_informal_debt(debt: models.Debt) -> bool:
    origin_kind = _as_value(debt.origin_kind)
    product_kind = _as_value(debt.product_kind)
    return (
        not is_formal_debt(debt)
        and (
            origin_kind in {item.value for item in INFORMAL_ORIGIN_KINDS}
            or product_kind
            in {
                models.DebtProductKind.INFORMAL_DEBT.value,
                models.DebtProductKind.PERSONAL_REIMBURSEMENT.value,
            }
        )
    )


def is_open_debt(debt: models.Debt) -> bool:
    return debt.status in OPEN_DEBT_STATUSES


def is_closed_debt(debt: models.Debt) -> bool:
    return debt.status in CLOSED_DEBT_STATUSES


def payment_plan_managed_id(debt: models.Debt) -> int | None:
    plan = getattr(debt, "installment_plan", None)
    if plan is not None:
        return int(plan.id)
    return None


def is_pristine_debt(db: Session, debt: models.Debt) -> bool:
    if payment_plan_managed_id(debt) is not None:
        return False

    return not db.query(
        exists().where(
            models.DebtLedgerEntry.owner_id == debt.owner_id,
            models.DebtLedgerEntry.debt_id == debt.id,
            models.DebtLedgerEntry.status == POSTED_DEBT_LEDGER_STATUS,
            models.DebtLedgerEntry.entry_type != models.DebtLedgerEntryType.INITIAL,
        )
    ).scalar()


def get_active_action_restrictions(
    db: Session,
    debt: models.Debt,
    action_kind: models.DebtActionKind,
) -> list[models.DebtActionRestriction]:
    return (
        db.query(models.DebtActionRestriction)
        .filter(
            models.DebtActionRestriction.owner_id == debt.owner_id,
            models.DebtActionRestriction.debt_id == debt.id,
            models.DebtActionRestriction.action_kind == action_kind,
            models.DebtActionRestriction.is_active == True,
        )
        .order_by(models.DebtActionRestriction.id.asc())
        .all()
    )


def _base_decision(action_kind: models.DebtActionKind) -> DebtActionDecision:
    return DebtActionDecision(action_kind=action_kind, allowed=True)


def _apply_persisted_restrictions(
    decision: DebtActionDecision,
    restrictions: Iterable[models.DebtActionRestriction],
) -> DebtActionDecision:
    current = decision
    for restriction in restrictions:
        details = dict(restriction.details or {})
        if restriction.level == models.DebtActionRestrictionLevel.BLOCKED:
            return current.blocked(
                restriction.reason_code,
                source=restriction.source,
                details=details,
            )
        if restriction.level == models.DebtActionRestrictionLevel.REQUIRES_CONFIRMATION:
            current = current.with_confirmation(
                restriction.reason_code,
                source=restriction.source,
                details=details,
            )
        elif restriction.level == models.DebtActionRestrictionLevel.UNDO_UNAVAILABLE:
            current = current.without_undo(
                restriction.reason_code,
                source=restriction.source,
                details=details,
            )
    return current


def _evaluate_debt_state(
    debt: models.Debt,
    action_kind: models.DebtActionKind,
    decision: DebtActionDecision,
    *,
    allow_payment_plan_managed: bool = False,
) -> DebtActionDecision:
    managed_plan_id = payment_plan_managed_id(debt)
    if (
        managed_plan_id is not None
        and not allow_payment_plan_managed
        and action_kind in PAYMENT_PLAN_MANAGED_ACTIONS
    ):
        return decision.blocked(
            "debts.policy.managed_by_payment_plan",
            details={
                "installment_plan_id": managed_plan_id,
                "action_owner": "PAYMENT_PLANS",
            },
        )

    if debt.status == models.DebtStatus.ARCHIVED:
        if action_kind == models.DebtActionKind.RESTORE:
            return decision
        return decision.blocked("debts.policy.archived_immutable")

    if action_kind == models.DebtActionKind.RESTORE:
        return decision.blocked("debts.policy.restore_only_archived")

    if action_kind == models.DebtActionKind.ARCHIVE:
        if is_closed_debt(debt):
            return decision
        return decision.blocked("debts.policy.archive_only_closed")

    if action_kind in {
        models.DebtActionKind.RECORD_PAYMENT,
        models.DebtActionKind.ADD_CHARGE,
        models.DebtActionKind.FORGIVE_PARTIAL,
        models.DebtActionKind.FORGIVE_FULL,
        models.DebtActionKind.ADJUST_BALANCE,
        models.DebtActionKind.SETTLE,
        models.DebtActionKind.LINK_ASSET,
        models.DebtActionKind.SET_COLLATERAL,
        models.DebtActionKind.RESTRUCTURE_TERMS,
    }:
        if not is_open_debt(debt):
            return decision.blocked("debts.policy.closed_debt_immutable")
        if int(debt.remaining_amount or 0) <= 0:
            return decision.blocked("debts.policy.no_remaining_balance")

    return decision


def _evaluate_action_meaning(
    debt: models.Debt,
    action_kind: models.DebtActionKind,
    decision: DebtActionDecision,
) -> DebtActionDecision:
    if action_kind in {
        models.DebtActionKind.FORGIVE_PARTIAL,
        models.DebtActionKind.FORGIVE_FULL,
    }:
        if is_informal_debt(debt):
            return decision
        return decision.blocked("debts.policy.forgiveness_only_informal")

    if action_kind == models.DebtActionKind.SETTLE:
        if is_formal_debt(debt):
            return decision.with_confirmation("debts.policy.formal_settlement_confirm")
        return decision.blocked("debts.policy.settlement_only_formal")

    if action_kind in {
        models.DebtActionKind.SET_COLLATERAL,
        models.DebtActionKind.RESTRUCTURE_TERMS,
    }:
        if is_formal_debt(debt):
            return decision
        return decision.blocked("debts.policy.formal_action_only")

    if action_kind == models.DebtActionKind.LINK_ASSET:
        if debt.origin_kind == models.DebtOriginKind.FINANCED_ASSET_PURCHASE or is_formal_debt(debt):
            return decision
        return decision.blocked("debts.policy.link_asset_only_financed_or_formal")

    return decision


def evaluate_debt_action(
    db: Session,
    debt: models.Debt,
    action_kind: models.DebtActionKind,
    *,
    allow_payment_plan_managed: bool = False,
) -> DebtActionDecision:
    decision = _base_decision(action_kind)
    decision = _evaluate_debt_state(
        debt,
        action_kind,
        decision,
        allow_payment_plan_managed=allow_payment_plan_managed,
    )
    if decision.allowed:
        decision = _evaluate_action_meaning(debt, action_kind, decision)

    return _apply_persisted_restrictions(
        decision,
        get_active_action_restrictions(db, debt, action_kind),
    )


def evaluate_debt_actions(
    db: Session,
    debt: models.Debt,
    *,
    allow_payment_plan_managed: bool = False,
) -> dict[models.DebtActionKind, DebtActionDecision]:
    return {
        action_kind: evaluate_debt_action(
            db,
            debt,
            action_kind,
            allow_payment_plan_managed=allow_payment_plan_managed,
        )
        for action_kind in models.DebtActionKind
    }


def _entry_has_posted_reversal(db: Session, entry: models.DebtLedgerEntry) -> bool:
    return db.query(
        exists().where(
            models.DebtLedgerEntry.reverses_entry_id == entry.id,
            models.DebtLedgerEntry.status == POSTED_DEBT_LEDGER_STATUS,
        )
    ).scalar()


def evaluate_ledger_entry_reversal(
    db: Session,
    debt: models.Debt,
    entry: models.DebtLedgerEntry,
    *,
    allow_payment_plan_managed: bool = False,
) -> DebtActionDecision:
    decision = evaluate_debt_action(
        db,
        debt,
        models.DebtActionKind.REVERSE_ENTRY,
        allow_payment_plan_managed=allow_payment_plan_managed,
    )
    if not decision.allowed:
        return decision

    if entry.debt_id != debt.id or entry.owner_id != debt.owner_id:
        return decision.blocked("debts.policy.entry_not_owned_by_debt")
    if entry.status != POSTED_DEBT_LEDGER_STATUS:
        return decision.blocked("debts.policy.entry_not_posted")
    if entry.entry_type == models.DebtLedgerEntryType.REVERSAL:
        return decision.blocked("debts.policy.reversal_entry_not_reversible")
    if entry.entry_type not in REVERSIBLE_ENTRY_TYPES:
        return decision.blocked("debts.policy.entry_type_not_reversible")
    if not entry.is_reversible:
        return decision.blocked("debts.policy.entry_marked_not_reversible")
    if _entry_has_posted_reversal(db, entry):
        return decision.blocked("debts.policy.entry_already_reversed")

    if entry.source != models.DebtLedgerEntrySource.USER:
        return decision.with_confirmation("debts.policy.non_user_entry_reversal_confirm")
    return decision
