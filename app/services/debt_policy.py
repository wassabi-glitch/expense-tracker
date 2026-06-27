from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy import exists
from sqlalchemy.orm import Session, aliased

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
    return not is_archived_debt(debt) and int(debt.remaining_amount or 0) > 0


def is_closed_debt(debt: models.Debt) -> bool:
    return not is_archived_debt(debt) and int(debt.remaining_amount or 0) <= 0


def is_archived_debt(debt: models.Debt) -> bool:
    return getattr(debt, "archived_at", None) is not None or debt.status == models.DebtStatus.ARCHIVED


def is_pristine_debt(db: Session, debt: models.Debt) -> bool:
    return not db.query(
        exists().where(
            models.DebtLedgerEntry.owner_id == debt.owner_id,
            models.DebtLedgerEntry.debt_id == debt.id,
            models.DebtLedgerEntry.status == POSTED_DEBT_LEDGER_STATUS,
            models.DebtLedgerEntry.entry_type != models.DebtLedgerEntryType.INITIAL,
        )
    ).scalar()


def _base_decision(action_kind: models.DebtActionKind) -> DebtActionDecision:
    return DebtActionDecision(action_kind=action_kind, allowed=True)


def _evaluate_debt_state(
    debt: models.Debt,
    action_kind: models.DebtActionKind,
    decision: DebtActionDecision,
) -> DebtActionDecision:
    if is_archived_debt(debt):
        if action_kind == models.DebtActionKind.RESTORE:
            return decision
        return decision.blocked("debts.policy.archived_immutable")

    if action_kind == models.DebtActionKind.RESTORE:
        return decision.blocked("debts.policy.restore_only_archived")

    if action_kind == models.DebtActionKind.ARCHIVE:
        return decision

    if action_kind in {
        models.DebtActionKind.RECORD_PAYMENT,
        models.DebtActionKind.ADD_CHARGE,
        models.DebtActionKind.FORGIVE_PARTIAL,
        models.DebtActionKind.FORGIVE_FULL,
        models.DebtActionKind.ADJUST_BALANCE,
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
        return decision

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
) -> DebtActionDecision:
    decision = _base_decision(action_kind)
    decision = _evaluate_debt_state(
        debt,
        action_kind,
        decision,
    )
    if decision.allowed:
        decision = _evaluate_action_meaning(debt, action_kind, decision)
    return decision


def evaluate_debt_actions(
    db: Session,
    debt: models.Debt,
) -> dict[models.DebtActionKind, DebtActionDecision]:
    return {
        action_kind: evaluate_debt_action(db, debt, action_kind)
        for action_kind in models.DebtActionKind
    }


def _entry_has_posted_reversal(db: Session, entry: models.DebtLedgerEntry) -> bool:
    return db.query(
        exists().where(
            models.DebtLedgerEntry.reverses_entry_id == entry.id,
            models.DebtLedgerEntry.status == POSTED_DEBT_LEDGER_STATUS,
        )
    ).scalar()


def _latest_unreversed_reversible_entry(db: Session, debt: models.Debt) -> models.DebtLedgerEntry | None:
    reversal = aliased(models.DebtLedgerEntry)
    return (
        db.query(models.DebtLedgerEntry)
        .filter(
            models.DebtLedgerEntry.owner_id == debt.owner_id,
            models.DebtLedgerEntry.debt_id == debt.id,
            models.DebtLedgerEntry.status == POSTED_DEBT_LEDGER_STATUS,
            models.DebtLedgerEntry.entry_type != models.DebtLedgerEntryType.INITIAL,
            models.DebtLedgerEntry.entry_type != models.DebtLedgerEntryType.REVERSAL,
            models.DebtLedgerEntry.is_reversible,
            ~exists().where(
                reversal.reverses_entry_id == models.DebtLedgerEntry.id,
                reversal.status == POSTED_DEBT_LEDGER_STATUS,
            ),
        )
        .order_by(models.DebtLedgerEntry.id.desc())
        .first()
    )


def evaluate_ledger_entry_reversal(
    db: Session,
    debt: models.Debt,
    entry: models.DebtLedgerEntry,
) -> DebtActionDecision:
    decision = evaluate_debt_action(
        db,
        debt,
        models.DebtActionKind.REVERSE_ENTRY,
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

    latest_entry = _latest_unreversed_reversible_entry(db, debt)
    if latest_entry is not None and latest_entry.id != entry.id:
        return decision.blocked(
            "debts.policy.reverse_latest_first",
            details={
                "latest_entry_id": latest_entry.id,
                "latest_entry_type": latest_entry.entry_type.value,
                "blocked_entry_id": entry.id,
            },
        )

    if entry.source != models.DebtLedgerEntrySource.USER:
        return decision.with_confirmation("debts.policy.non_user_entry_reversal_confirm")
    return decision
