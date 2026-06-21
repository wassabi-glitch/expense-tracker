from __future__ import annotations

from dataclasses import dataclass

from app import models


@dataclass(frozen=True)
class OutflowFundingBreakdown:
    """Financial substance of one wallet outflow at posting time."""

    owned_amount: int
    borrowed_amount: int


def owned_balance(wallet: models.Wallet) -> int:
    """Return value owned by the user, independent of the wallet label."""

    return max(int(wallet.current_balance or 0), 0)


def liability_exposure(wallet: models.Wallet) -> int:
    return max(-int(wallet.current_balance or 0), 0)


def classify_outflow(wallet: models.Wallet, amount: int) -> OutflowFundingBreakdown:
    """
    Split an outflow into owned and newly borrowed portions.

    The split uses the locked balance immediately before posting. This keeps a
    later card repayment from rewriting the financial meaning of old spending.
    """

    requested = max(int(amount), 0)
    owned_amount = min(owned_balance(wallet), requested)
    return OutflowFundingBreakdown(
        owned_amount=owned_amount,
        borrowed_amount=requested - owned_amount,
    )


def can_hold_goal_funds(wallet: models.Wallet) -> bool:
    """Whether this wallet may protect owned positive value for goals."""

    if not bool(wallet.is_active) or not bool(wallet.can_fund_goals):
        return False
    return (
        wallet.accounting_type == models.AccountingType.ASSET
        or wallet.wallet_type == models.WalletType.CREDIT
    )
