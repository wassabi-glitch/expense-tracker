from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator
import datetime as dt
from datetime import datetime, date
from typing import Any, Dict, List, Optional
from enum import Enum
import re

from .models import (
    ExpenseCategory,
    ExpenseSessionDraftSource,
    ExpenseSessionDraftStatus,
    GoalContributionType,
    GoalCompletionMode,
    DebtGoalTrackingMode,
    GoalIntent,
    GoalStatus,
    LifeStatus,
    ProjectStatus,
    RecurringFrequency,
    RecurringStatus,
    CycleBehavior,
    RecurringEventType,
    SavingsTransactionType,
    DebtActionKind,
    DebtActionRestrictionLevel,
    DebtActionRestrictionSource,
    DebtCounterpartyKind,
    DebtLedgerEntrySource,
    DebtLedgerEntryType,
    DebtOriginKind,
    DebtProductKind,
    DebtType,
    DebtStatus,
    ExpectedIncomeStatus,
    InstallmentFrequency,
    PaymentPlanType,
    InstallmentStatus,
    InstallmentPaymentStatus,
    InstallmentPaymentComponentType,
    WalletType,
    AccountingType,
    TransactionType,
)  # Importing enums

MIN_BUDGET_YEAR = 2020
MAX_BUDGET_YEARS_AHEAD = 5
MAX_INCOME_AMOUNT = 999_999_999_999
MAX_EXPENSE_AMOUNT = 999_999_999_999


class GoalTimeState(str, Enum):
    ON_TRACK = "on_track"
    DUE_SOON = "due_soon"
    OVERDUE = "overdue"


class GoalSettlementMode(str, Enum):
    DIRECT = "DIRECT"
    REIMBURSE_PAYMENT_WALLET = "REIMBURSE_PAYMENT_WALLET"
    PAID_OUTSIDE_GOAL_FUNDS = "PAID_OUTSIDE_GOAL_FUNDS"


class PlannedPurchaseResultType(str, Enum):
    EXPENSE_ONLY = "EXPENSE_ONLY"
    ASSET_PURCHASE = "ASSET_PURCHASE"


# --- USER SCHEMAS ---


class UserBase(BaseModel):
    username: str
    email: EmailStr

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str):
        v = v.strip()
        if not (3 <= len(v) <= 32):
            raise ValueError("auth.validation.username.length")
        if " " in v:
            raise ValueError("auth.validation.username.no_spaces")
        if not re.fullmatch(r"[A-Za-z0-9._]+", v):
            raise ValueError("auth.validation.username.allowed_chars")
        if v[0] in "._" or v[-1] in "._":
            raise ValueError("auth.validation.username.edge_separators")
        if ".." in v or "__" in v or "._" in v or "_." in v:
            raise ValueError("auth.validation.username.consecutive_separators")
        if v.isdigit():
            raise ValueError("auth.validation.username.not_only_numbers")
        return v

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: str):
        v = v.strip().lower()
        if len(v) > 254:
            raise ValueError("auth.validation.email.too_long")
        local, _, domain = v.partition("@")
        if len(local) > 64:
            raise ValueError("auth.validation.email.local_part_too_long")
        if not domain or "." not in domain:
            raise ValueError("auth.validation.email.domain_invalid")
        return v


class UserCreate(UserBase):
    password: str  # Only used during registration

    @field_validator('password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError("auth.validation.password.min")
        if len(v) > 64:
            raise ValueError("auth.validation.password.max")
        if " " in v:
            raise ValueError("auth.validation.password.no_spaces")
        if not re.search(r"[a-z]", v):
            raise ValueError("auth.validation.password.lowercase")
        if not re.search(r"[A-Z]", v):
            raise ValueError("auth.validation.password.uppercase")
        if not re.search(r"\d", v):
            raise ValueError("auth.validation.password.number")
        if not re.search(r"[^\w\s]", v):
            raise ValueError("auth.validation.password.special")
        return v

    @model_validator(mode="after")
    def validate_password_not_contains_email_local_part(self):
        local_part = self.email.split("@", 1)[0].strip().lower()
        if local_part and local_part in self.password.lower():
            raise ValueError("auth.validation.password.no_email_local_part")
        return self


# --- WALLET SCHEMAS ---

class WalletBase(BaseModel):
    name: str = Field(max_length=32)
    wallet_type: WalletType = WalletType.DEBIT
    accounting_type: AccountingType = AccountingType.ASSET
    initial_balance: int = 0
    current_balance: int = 0
    can_fund_goals: Optional[bool] = None

    # Optional limits
    has_overdraft: bool = False
    overdraft_limit: Optional[int] = Field(0, ge=0)

    credit_limit: int = Field(0, ge=0)
    allow_overlimit: bool = False

    color: str = "default"
    currency: str = "UZS"


class WalletCreate(WalletBase):
    @model_validator(mode="after")
    def validate_limits(self) -> 'WalletCreate':
        mag = abs(self.initial_balance)
        # 1. Negative balance check
        if self.initial_balance < 0:
            if self.wallet_type == WalletType.CREDIT:
                if not self.allow_overlimit and mag > self.credit_limit:
                    raise ValueError("wallets.validation.balanceExceedsLimit")
            elif self.wallet_type == WalletType.DEBIT:
                if not self.has_overdraft:
                    raise ValueError("wallets.validation.balanceExceedsLimit")
                if mag > self.overdraft_limit:
                    raise ValueError("wallets.validation.balanceExceedsLimit")
            else: # CASH, PRELOADED, SAVINGS
                raise ValueError("wallets.validation.balanceExceedsLimit")
        return self


class WalletUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=32)
    color: Optional[str] = None
    is_default: Optional[bool] = None
    is_active: Optional[bool] = None

    # Update limits
    has_overdraft: Optional[bool] = None
    overdraft_limit: Optional[int] = Field(None, ge=0)
    credit_limit: Optional[int] = Field(None, ge=0)
    allow_overlimit: Optional[bool] = None
    can_fund_goals: Optional[bool] = None


class WalletOut(WalletBase):
    id: int
    can_fund_goals: bool = False
    is_default: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime
    warning: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class WalletQuickActionRequest(BaseModel):
    """Payload for recording Fee, Interest or generic single-entry logging"""
    action_type: Optional[str] = None
    amount: int = Field(gt=0)
    note: Optional[str] = Field(None, max_length=150)

class WalletReconciliationRequest(BaseModel):
    """Payload for submitting the actual physical balance for Math reconciliation"""
    target_balance: int
    note: Optional[str] = Field("Balance Reconciliation", max_length=150)


class WalletTransferCreate(BaseModel):
    class GoalResolution(str, Enum):
        MOVE_TO_DESTINATION = "MOVE_TO_DESTINATION"
        RELEASE = "RELEASE"

    from_wallet_id: int
    to_wallet_id: int
    amount: int = Field(gt=0)
    note: Optional[str] = Field(None, max_length=200)
    date: date
    goal_resolution: Optional[GoalResolution] = None
    fee_amount: Optional[int] = Field(default=None, gt=0)
    fee_wallet_id: Optional[int] = None
    fee_note: Optional[str] = Field(default=None, max_length=200)

    @field_validator("amount", "fee_amount")
    @classmethod
    def validate_transfer_amount_max(cls, v: Optional[int]):
        if v is not None and v > MAX_INCOME_AMOUNT:
            raise ValueError("income.amount_too_large")
        return v


class WalletTransferOut(BaseModel):
    id: int
    from_wallet_id: int
    to_wallet_id: int
    amount: int
    note: Optional[str]
    date: date
    created_at: datetime
    fee_event_id: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class WalletBackedObligationPayoffCreate(BaseModel):
    from_wallet_id: int
    amount: int = Field(gt=0)
    note: Optional[str] = Field(None, max_length=200)
    date: date
    goal_resolution: Optional[WalletTransferCreate.GoalResolution] = None
    fee_amount: Optional[int] = Field(default=None, gt=0)
    fee_wallet_id: Optional[int] = None
    fee_note: Optional[str] = Field(default=None, max_length=200)

    @field_validator("amount", "fee_amount")
    @classmethod
    def validate_payoff_amount_max(cls, v: Optional[int]):
        if v is not None and v > MAX_INCOME_AMOUNT:
            raise ValueError("income.amount_too_large")
        return v


class WalletTransactionOut(BaseModel):
    id: int
    amount: int
    title: str
    event_type: TransactionType
    date: date
    created_at: datetime


class PaginatedWalletTransactionsOut(BaseModel):
    total: int
    items: List[WalletTransactionOut]


# --- ONBOARDING SCHEMAS ---

class UserOnboardingUpsert(BaseModel):
    life_statuses: List[LifeStatus] = Field(min_length=1)
    wallets: List[WalletCreate] = Field(min_length=1, max_length=200)


class UserProfileOut(BaseModel):
    id: int
    user_id: int
    life_status: Optional[LifeStatus] = None
    life_statuses: List[LifeStatus] = []
    monthly_income_amount: int
    initial_balance: int
    onboarding_completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)




class UserOut(UserBase):
    id: int
    created_at: datetime
    is_premium: bool
    needs_onboarding: bool = True
    profile: Optional[UserProfileOut] = None

    model_config = ConfigDict(from_attributes=True)


class IncomeSourceBase(BaseModel):
    name: str

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str):
        value = v.strip()
        if not (1 <= len(value) <= 32):
            raise ValueError("income.source_name_length")
        return value


class IncomeSourceCreate(IncomeSourceBase):
    pass


class IncomeSourceUpdate(IncomeSourceBase):
    pass


class IncomeSourceStatusUpdate(BaseModel):
    is_active: bool

    model_config = ConfigDict(extra="forbid")


class IncomeSourceOut(IncomeSourceBase):
    id: int
    owner_id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class IncomeWalletAllocationIn(BaseModel):
    wallet_id: int
    amount: int = Field(gt=0)

    @field_validator("amount")
    @classmethod
    def validate_amount_max(cls, v: int):
        if v > MAX_INCOME_AMOUNT:
            raise ValueError("income.amount_too_large")
        return v


class IncomeWalletAllocationOut(BaseModel):
    wallet_id: int
    amount: int
    wallet: Optional[WalletOut] = None


class IncomeEntryBase(BaseModel):
    amount: int = Field(gt=0)
    date: date
    note: Optional[str] = None
    source_id: Optional[int] = None
    wallet_id: Optional[int] = None
    wallet_allocations: List[IncomeWalletAllocationIn] = Field(default_factory=list)

    @field_validator("amount")
    @classmethod
    def validate_amount_max(cls, v: int):
        if v > MAX_INCOME_AMOUNT:
            raise ValueError("income.amount_too_large")
        return v

    @field_validator("date")
    @classmethod
    def validate_date(cls, v: date):
        if v.year < 2020:
            raise ValueError("income.date_too_early")
        return v

    @field_validator("note")
    @classmethod
    def validate_note(cls, v: Optional[str]):
        if v is None:
            return v
        value = v.strip()
        if len(value) > 200:
            raise ValueError("income.note_too_long")
        return value


class IncomeEntryCreate(IncomeEntryBase):
    pass


class IncomeEntryUpdate(IncomeEntryBase):
    model_config = ConfigDict(extra="forbid")


class IncomeEntryOut(IncomeEntryBase):
    id: int
    owner_id: int
    wallet_allocations: List[IncomeWalletAllocationOut] = []
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PaginatedIncomeEntriesOut(BaseModel):
    total: int
    items: List[IncomeEntryOut]


class ExpectedIncomeBase(BaseModel):
    source_id: Optional[int] = None
    debt_id: Optional[int] = None
    amount: int = Field(gt=0)
    due_date: date
    budget_year: int
    budget_month: int
    note: Optional[str] = Field(default=None, max_length=200)

    @field_validator("amount")
    @classmethod
    def validate_expected_amount_max(cls, v: int):
        if v > MAX_INCOME_AMOUNT:
            raise ValueError("income.amount_too_large")
        return v

    @field_validator("due_date")
    @classmethod
    def validate_expected_due_date(cls, v: date):
        if v.year < MIN_BUDGET_YEAR:
            raise ValueError("income.date_too_early")
        return v

    @field_validator("budget_year")
    @classmethod
    def validate_expected_budget_year(cls, v: int):
        if v < MIN_BUDGET_YEAR:
            raise ValueError("budgets.year_too_early")
        return v

    @field_validator("budget_month")
    @classmethod
    def validate_expected_budget_month(cls, v: int):
        if v < 1 or v > 12:
            raise ValueError("budgets.month_invalid")
        return v

    @model_validator(mode="after")
    def validate_expected_month_matches_due_date(self):
        if self.due_date.year != self.budget_year or self.due_date.month != self.budget_month:
            raise ValueError("expected_income.month_mismatch")
        if (self.source_id is None) == (self.debt_id is None):
            raise ValueError("expected_income.one_source_required")
        return self


class ExpectedIncomeCreate(ExpectedIncomeBase):
    pass


class ExpectedIncomeUpdate(BaseModel):
    source_id: Optional[int] = None
    debt_id: Optional[int] = None
    amount: Optional[int] = Field(default=None, gt=0)
    received_amount: Optional[int] = Field(default=None, gt=0)
    linked_transaction_id: Optional[int] = None
    due_date: Optional[date] = None
    budget_year: Optional[int] = None
    budget_month: Optional[int] = None
    status: Optional[ExpectedIncomeStatus] = None
    note: Optional[str] = Field(default=None, max_length=200)

    model_config = ConfigDict(extra="forbid")

    @field_validator("amount")
    @classmethod
    def validate_expected_update_amount_max(cls, v: Optional[int]):
        if v is not None and v > MAX_INCOME_AMOUNT:
            raise ValueError("income.amount_too_large")
        return v

    @field_validator("due_date")
    @classmethod
    def validate_expected_update_due_date(cls, v: Optional[date]):
        if v is not None and v.year < MIN_BUDGET_YEAR:
            raise ValueError("income.date_too_early")
        return v

    @field_validator("budget_year")
    @classmethod
    def validate_expected_update_budget_year(cls, v: Optional[int]):
        if v is not None and v < MIN_BUDGET_YEAR:
            raise ValueError("budgets.year_too_early")
        return v

    @field_validator("budget_month")
    @classmethod
    def validate_expected_update_budget_month(cls, v: Optional[int]):
        if v is not None and (v < 1 or v > 12):
            raise ValueError("budgets.month_invalid")
        return v


class ExpectedIncomeMarkReceivedCreate(BaseModel):
    received_amount: int = Field(gt=0)
    date: Optional[dt.date] = None
    note: Optional[str] = Field(default=None, max_length=200)
    wallet_id: Optional[int] = None
    wallet_allocations: List[IncomeWalletAllocationIn] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid")

    @field_validator("received_amount")
    @classmethod
    def validate_received_amount_max(cls, v: int):
        if v > MAX_INCOME_AMOUNT:
            raise ValueError("income.amount_too_large")
        return v


class ExpectedIncomeOut(BaseModel):
    id: int
    owner_id: int
    source_id: Optional[int]
    debt_id: Optional[int] = None
    source: Optional[IncomeSourceOut] = None
    amount: int
    received_amount: Optional[int] = None
    linked_transaction_id: Optional[int] = None
    due_date: date
    budget_year: int
    budget_month: int
    status: ExpectedIncomeStatus
    note: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MoneyInKind(str, Enum):
    ALL = "all"
    INCOME = "income"
    RETURNED = "returned"
    BORROWED = "borrowed"
    SOLD = "sold"
    ADJUSTMENT = "adjustment"


class MoneyInWalletOut(BaseModel):
    wallet_id: int
    wallet_name: str
    amount: int


class MoneyInItemOut(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    amount: int
    currency: str = "UZS"
    date: date
    created_at: datetime
    kind: MoneyInKind
    counts_as_income: bool
    event_type: TransactionType
    reference_type: Optional[str] = None
    source_id: Optional[int] = None
    source_name: Optional[str] = None
    debt_id: Optional[int] = None
    asset_id: Optional[int] = None
    linked_event_id: Optional[int] = None
    wallet_allocations: List[MoneyInWalletOut] = []
    read_only: bool = True
    original_domain: Optional[str] = None


class PaginatedMoneyInOut(BaseModel):
    total: int
    items: List[MoneyInItemOut]


class SavingsTransactionCreate(BaseModel):
    amount: int = Field(gt=0)
    transaction_type: SavingsTransactionType
    wallet_id: Optional[int] = None

    @field_validator("amount")
    @classmethod
    def validate_amount_max(cls, v: int):
        if v > MAX_INCOME_AMOUNT:
            raise ValueError("income.amount_too_large")
        return v


class SavingsTransactionOut(BaseModel):
    id: int
    owner_id: int
    wallet_id: Optional[int] = None
    amount: int
    transaction_type: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class GoalBase(BaseModel):
    title: str
    target_amount: int = Field(gt=0)
    currency: str = Field(default="UZS", min_length=3, max_length=3)
    intent: GoalIntent = GoalIntent.RESERVE
    debt_goal_tracking_mode: Optional[DebtGoalTrackingMode] = None
    template: Optional[str] = Field(default=None, max_length=50)
    target_date: Optional[date] = None
    linked_asset_id: Optional[int] = None
    linked_debt_id: Optional[int] = None
    linked_installment_plan_id: Optional[int] = None
    linked_expense_event_id: Optional[int] = None

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: str):
        value = v.strip()
        if not (3 <= len(value) <= 32):
            raise ValueError("expenses.validation.title.length")
        return value

    @field_validator("target_amount")
    @classmethod
    def validate_target_amount_max(cls, v: int):
        if v > MAX_INCOME_AMOUNT:
            raise ValueError("income.amount_too_large")
        return v

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, v: str):
        value = v.strip().upper()
        if len(value) != 3:
            raise ValueError("currency.invalid")
        return value

    @field_validator("template")
    @classmethod
    def normalize_template(cls, v: Optional[str]):
        if v is None:
            return v
        value = v.strip().lower().replace(" ", "_")
        if not value:
            return None
        if not re.fullmatch(r"[a-z0-9_:-]+", value):
            raise ValueError("goals.template_invalid")
        return value

    @field_validator("target_date")
    @classmethod
    def validate_target_date(cls, v: Optional[date]):
        if v is None:
            return v
        if v.year < 2020:
            raise ValueError("expenses.date_too_early")
        return v


class GoalCreate(GoalBase):
    pass


class GoalUpdate(BaseModel):
    title: Optional[str] = None
    target_amount: Optional[int] = Field(default=None, gt=0)
    currency: Optional[str] = Field(default=None, min_length=3, max_length=3)
    intent: Optional[GoalIntent] = None
    debt_goal_tracking_mode: Optional[DebtGoalTrackingMode] = None
    template: Optional[str] = Field(default=None, max_length=50)
    target_date: Optional[date] = None
    status: Optional[GoalStatus] = None
    linked_asset_id: Optional[int] = None
    linked_debt_id: Optional[int] = None
    linked_installment_plan_id: Optional[int] = None
    linked_expense_event_id: Optional[int] = None

    model_config = ConfigDict(extra="forbid")

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: Optional[str]):
        if v is None:
            return v
        value = v.strip()
        if not (3 <= len(value) <= 32):
            raise ValueError("expenses.validation.title.length")
        return value

    @field_validator("target_amount")
    @classmethod
    def validate_target_amount_max(cls, v: Optional[int]):
        if v is None:
            return v
        if v > MAX_INCOME_AMOUNT:
            raise ValueError("income.amount_too_large")
        return v

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, v: Optional[str]):
        if v is None:
            return v
        value = v.strip().upper()
        if len(value) != 3:
            raise ValueError("currency.invalid")
        return value

    @field_validator("template")
    @classmethod
    def normalize_template(cls, v: Optional[str]):
        if v is None:
            return v
        value = v.strip().lower().replace(" ", "_")
        if not value:
            return None
        if not re.fullmatch(r"[a-z0-9_:-]+", value):
            raise ValueError("goals.template_invalid")
        return value

    @field_validator("target_date")
    @classmethod
    def validate_target_date(cls, v: Optional[date]):
        if v is None:
            return v
        if v.year < 2020:
            raise ValueError("expenses.date_too_early")
        return v


class GoalContributionCreate(BaseModel):
    wallet_id: int
    amount: int = Field(gt=0)
    linked_event_id: Optional[int] = None

    @field_validator("amount")
    @classmethod
    def validate_amount_max(cls, v: int):
        if v > MAX_INCOME_AMOUNT:
            raise ValueError("income.amount_too_large")
        return v


class GoalAllocationItemCreate(BaseModel):
    wallet_id: int
    amount: int = Field(gt=0)

    @field_validator("amount")
    @classmethod
    def validate_amount_max(cls, v: int):
        if v > MAX_INCOME_AMOUNT:
            raise ValueError("income.amount_too_large")
        return v


class GoalAllocationCreate(BaseModel):
    allocations: List[GoalAllocationItemCreate] = Field(min_length=1)

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="before")
    @classmethod
    def normalize_single_allocation(cls, data):
        if isinstance(data, dict) and "allocations" not in data and "wallet_id" in data and "amount" in data:
            return {"allocations": [{"wallet_id": data["wallet_id"], "amount": data["amount"]}]}
        return data

    @model_validator(mode="after")
    def validate_unique_wallets(self):
        wallet_ids = [item.wallet_id for item in self.allocations]
        if len(wallet_ids) != len(set(wallet_ids)):
            raise ValueError("goals.allocation_duplicate_wallet")
        return self


class GoalAllocationReturnCreate(GoalContributionCreate):
    pass


class GoalAllocationConsumeCreate(GoalContributionCreate):
    pass


MAX_GOAL_PAYMENT_PREPARATION_TARGET_WALLETS = 3
MAX_GOAL_PAYMENT_PREPARATION_MOVE_ROWS = 9


class GoalFundingMoveItemCreate(BaseModel):
    source_wallet_id: int
    target_wallet_id: int
    amount: int = Field(gt=0)
    fee_amount: Optional[int] = Field(default=None, gt=0)
    fee_wallet_id: Optional[int] = None
    fee_note: Optional[str] = Field(default=None, max_length=200)

    model_config = ConfigDict(extra="forbid")

    @field_validator("amount", "fee_amount")
    @classmethod
    def validate_amount_max(cls, v: Optional[int]):
        if v is not None and v > MAX_INCOME_AMOUNT:
            raise ValueError("income.amount_too_large")
        return v


class GoalFundingMoveCreate(BaseModel):
    moves: Optional[List[GoalFundingMoveItemCreate]] = None
    source_wallet_id: Optional[int] = None
    target_wallet_id: Optional[int] = None
    amount: Optional[int] = Field(default=None, gt=0)
    date: dt.date
    note: Optional[str] = Field(default=None, max_length=200)
    fee_amount: Optional[int] = Field(default=None, gt=0)
    fee_wallet_id: Optional[int] = None
    fee_note: Optional[str] = Field(default=None, max_length=200)

    model_config = ConfigDict(extra="forbid")

    @field_validator("amount", "fee_amount")
    @classmethod
    def validate_amount_max(cls, v: Optional[int]):
        if v is not None and v > MAX_INCOME_AMOUNT:
            raise ValueError("income.amount_too_large")
        return v

    @model_validator(mode="before")
    @classmethod
    def normalize_single_move(cls, data):
        if not isinstance(data, dict):
            return data
        if data.get("moves") is not None:
            return data
        if all(data.get(key) is not None for key in ("source_wallet_id", "target_wallet_id", "amount")):
            normalized = dict(data)
            normalized["moves"] = [
                {
                    "source_wallet_id": normalized.pop("source_wallet_id"),
                    "target_wallet_id": normalized.pop("target_wallet_id"),
                    "amount": normalized.pop("amount"),
                    "fee_amount": normalized.pop("fee_amount", None),
                    "fee_wallet_id": normalized.pop("fee_wallet_id", None),
                    "fee_note": normalized.pop("fee_note", None),
                }
            ]
            return normalized
        return data

    @model_validator(mode="after")
    def validate_moves(self):
        if not self.moves:
            raise ValueError("goals.prepare_payment_moves_required")
        if len(self.moves) > MAX_GOAL_PAYMENT_PREPARATION_MOVE_ROWS:
            raise ValueError("goals.prepare_payment_move_limit_exceeded")
        pairs = [(move.source_wallet_id, move.target_wallet_id) for move in self.moves]
        if len(pairs) != len(set(pairs)):
            raise ValueError("goals.prepare_payment_duplicate_move")
        target_wallet_ids = {move.target_wallet_id for move in self.moves}
        if len(target_wallet_ids) > MAX_GOAL_PAYMENT_PREPARATION_TARGET_WALLETS:
            raise ValueError("goals.prepare_payment_target_wallet_limit_exceeded")
        return self


class GoalPaymentAllocationCreate(BaseModel):
    wallet_id: int
    amount: int = Field(gt=0)

    @field_validator("amount")
    @classmethod
    def validate_amount_max(cls, v: int):
        if v > MAX_INCOME_AMOUNT:
            raise ValueError("income.amount_too_large")
        return v


class GoalUseBase(BaseModel):
    amount: int = Field(gt=0)
    payment_allocations: List[GoalPaymentAllocationCreate] = Field(min_length=1)
    category: ExpenseCategory
    subcategory_id: Optional[int] = None
    project_id: Optional[int] = None
    project_subcategory_id: Optional[int] = None
    date: Optional[dt.date] = None
    title: Optional[str] = Field(default=None, min_length=3, max_length=100)
    description: Optional[str] = Field(default=None, max_length=500)
    settlement_mode: GoalSettlementMode = GoalSettlementMode.DIRECT

    model_config = ConfigDict(extra="forbid")

    @field_validator("amount")
    @classmethod
    def validate_use_amount_max(cls, v: int):
        if v > MAX_INCOME_AMOUNT:
            raise ValueError("income.amount_too_large")
        return v

    @field_validator("title")
    @classmethod
    def validate_use_title(cls, v: Optional[str]):
        if v is None:
            return v
        return v.strip()

    @field_validator("description")
    @classmethod
    def validate_use_description(cls, v: Optional[str]):
        if v is None:
            return v
        return v.strip()

    @field_validator("date")
    @classmethod
    def validate_use_date(cls, v: Optional[dt.date]):
        if v is None:
            return v
        if v.year < 2020:
            raise ValueError("expenses.date_too_early")
        return v

    @model_validator(mode="after")
    def validate_payment_allocation_total(self):
        total = sum(int(item.amount) for item in self.payment_allocations)
        if total != int(self.amount):
            raise ValueError("goals.payment_allocation_total_mismatch")
        wallet_ids = [item.wallet_id for item in self.payment_allocations]
        if len(wallet_ids) != len(set(wallet_ids)):
            raise ValueError("goals.payment_allocation_duplicate")
        return self


class GoalUseReserveCreate(GoalUseBase):
    pass


class GoalPurchaseInstallmentCreate(BaseModel):
    total_price: int = Field(gt=0)
    item_name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    store_or_bank_name: Optional[str] = Field(default=None, max_length=100)
    plan_type: PaymentPlanType = PaymentPlanType.STORE_INSTALLMENT
    months: int = Field(gt=0)
    frequency: InstallmentFrequency = InstallmentFrequency.MONTHLY
    start_date: Optional[dt.date] = None
    create_next_payment_goal: bool = True
    next_goal_title: Optional[str] = Field(default=None, min_length=3, max_length=32)
    next_goal_target_date: Optional[dt.date] = None

    model_config = ConfigDict(extra="forbid")

    @field_validator("total_price")
    @classmethod
    def validate_total_price_max(cls, v: int):
        if v > MAX_INCOME_AMOUNT:
            raise ValueError("income.amount_too_large")
        return v

    @field_validator("item_name", "store_or_bank_name", "next_goal_title")
    @classmethod
    def validate_optional_text(cls, v: Optional[str]):
        if v is None:
            return v
        return v.strip()

    @field_validator("start_date", "next_goal_target_date")
    @classmethod
    def validate_installment_dates(cls, v: Optional[dt.date]):
        if v is None:
            return v
        if v.year < 2020:
            raise ValueError("expenses.date_too_early")
        return v


class GoalUsePlannedPurchaseCreate(GoalUseBase):
    completion_mode: GoalCompletionMode = GoalCompletionMode.GOAL_FUNDED
    result_type: PlannedPurchaseResultType = PlannedPurchaseResultType.EXPENSE_ONLY
    asset_title: Optional[str] = Field(default=None, min_length=1, max_length=100)
    asset_description: Optional[str] = Field(default=None, max_length=500)
    asset_current_value: Optional[int] = Field(default=None, ge=0)
    release_unused_goal_funding: bool = False
    adjust_target_to_purchase_amount: bool = False
    installment_plan: Optional[GoalPurchaseInstallmentCreate] = None

    @field_validator("asset_title")
    @classmethod
    def validate_asset_title(cls, v: Optional[str]):
        if v is None:
            return v
        return v.strip()

    @field_validator("asset_description")
    @classmethod
    def validate_asset_description(cls, v: Optional[str]):
        if v is None:
            return v
        return v.strip()

    @model_validator(mode="after")
    def validate_installment_bridge(self):
        if self.installment_plan is None:
            return self
        if self.installment_plan.total_price <= int(self.amount):
            raise ValueError("goals.installment_total_must_exceed_down_payment")
        if self.installment_plan.plan_type == PaymentPlanType.BANK_LOAN:
            raise ValueError("goals.installment_bridge_bank_loan_not_supported")
        return self


class GoalDebtPaymentCreate(BaseModel):
    amount: int = Field(gt=0)
    payment_allocations: List[GoalPaymentAllocationCreate] = Field(min_length=1)
    date: Optional[dt.date] = None
    note: Optional[str] = Field(default=None, max_length=500)
    income_source_id: Optional[int] = None

    model_config = ConfigDict(extra="forbid")

    @field_validator("amount")
    @classmethod
    def validate_amount_max(cls, v: int):
        if v > MAX_INCOME_AMOUNT:
            raise ValueError("income.amount_too_large")
        return v

    @field_validator("note")
    @classmethod
    def validate_note(cls, v: Optional[str]):
        if v is None:
            return v
        return v.strip()

    @model_validator(mode="after")
    def validate_payment_allocation_total(self):
        total = sum(int(item.amount) for item in self.payment_allocations)
        if total != int(self.amount):
            raise ValueError("goals.payment_allocation_total_mismatch")
        wallet_ids = [item.wallet_id for item in self.payment_allocations]
        if len(wallet_ids) != len(set(wallet_ids)):
            raise ValueError("goals.payment_allocation_duplicate")
        return self


class GoalUseResultOut(BaseModel):
    goal: "GoalWithProgressOut"
    expense_event_id: int
    asset_id: Optional[int] = None
    transfer_event_ids: List[int] = Field(default_factory=list)
    consumed_amount: int = 0
    released_amount: int = 0
    outside_goal_amount: int = 0
    installment_plan: Optional["InstallmentPlanWithPaymentsOut"] = None
    next_payment_goal: Optional["GoalWithProgressOut"] = None


class GoalFundingMoveOut(BaseModel):
    goal: "GoalWithProgressOut"
    transfer: Optional[WalletTransferOut] = None
    transfers: List[WalletTransferOut] = Field(default_factory=list)
    moved_amount: int


class GoalContributionOut(BaseModel):
    id: int
    owner_id: int
    goal_id: int
    wallet_id: int
    linked_event_id: Optional[int] = None
    amount: int
    contribution_type: GoalContributionType
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class GoalActivityWalletOut(BaseModel):
    role: str
    wallet_id: int
    wallet_name: str
    amount: int


class GoalActivityItemOut(BaseModel):
    id: str
    type: str
    title: str
    description: Optional[str] = None
    amount: int = 0
    currency: str
    date: date
    time_label: Optional[str] = None
    created_at: datetime
    wallets: List[GoalActivityWalletOut] = Field(default_factory=list)
    linked_event_id: Optional[int] = None
    event_type: Optional[TransactionType] = None
    reference_type: Optional[str] = None


class GoalActivityOut(BaseModel):
    goal_id: int
    items: List[GoalActivityItemOut] = Field(default_factory=list)


class GoalOut(GoalBase):
    id: int
    owner_id: int
    status: GoalStatus
    completion_mode: Optional[GoalCompletionMode] = None
    linked_debt_transaction_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class GoalInstallmentTargetOut(BaseModel):
    plan_id: int
    payment_id: int
    payment_number: int
    total_payments: int
    due_date: date
    amount: int
    paid_amount: int
    remaining_amount: int
    status: InstallmentPaymentStatus
    item_name: Optional[str] = None


class GoalWithProgressOut(GoalOut):
    funded_amount: int = 0
    consumed_amount: int = 0
    released_amount: int = 0
    unreleased_amount: int = 0
    remaining_amount: int = 0
    progress_percent: float = 0
    linked_project_id: Optional[int] = None
    funding_sources: List["GoalFundingSourceOut"] = Field(default_factory=list)
    time_state: Optional[GoalTimeState] = None
    days_until_target: Optional[int] = None
    installment_target: Optional[GoalInstallmentTargetOut] = None


class GoalFundingSourceOut(BaseModel):
    wallet_id: int
    wallet_name: str
    wallet_type: WalletType
    currency: str
    allocated_amount: int
    released_amount: int = 0
    unreleased_amount: int = 0


class WalletGoalFundingOut(BaseModel):
    wallet_id: int
    wallet_name: str
    wallet_type: WalletType
    currency: str
    is_active: bool
    balance: int
    allocated_to_goals: int
    available_for_goals: int
    over_allocated_amount: int
    can_fund_goals: bool
    eligible_for_goal_funding: bool


class GoalFundingSummaryOut(BaseModel):
    total_wallet_balance: int
    allocated_to_goals: int
    available_for_goals: int
    over_allocated_amount: int
    wallets: List[WalletGoalFundingOut]


class SavingsSummaryOut(GoalFundingSummaryOut):
    pass


# --- EXPENSE SCHEMAS ---
MAX_EXPENSE_AMOUNT = 999_999_999_999


class ExpenseBase(BaseModel):
    title: str
    amount: int = Field(
        gt=0, description="The amount must be a positive integer")
    category: ExpenseCategory  # This ensures only our defined Enum values are accepted
    description: Optional[str] = None
    date: date
    wallet_id: Optional[int] = None
    subcategory_id: Optional[int] = None
    project_id: Optional[int] = None
    project_subcategory_id: Optional[int] = None

    @field_validator("date")
    @classmethod
    def validate_date(cls, v: date):
        if v.year < 2020:
            raise ValueError("expenses.date_too_early")

        return v

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: str):
        v = v.strip()
        if not (3 <= len(v) <= 32):
            raise ValueError("expenses.validation.title.length")
        return v

    @field_validator("description")
    @classmethod
    def validate_description(cls, v: Optional[str]):
        if v is None:
            return v
        v = v.strip()
        if len(v) > 500:
            raise ValueError("expenses.validation.description.max_length")
        return v

    @field_validator("amount")
    @classmethod
    def validate_amount_max(cls, v: int):
        if v > MAX_EXPENSE_AMOUNT:
            raise ValueError("expenses.amount_too_large")
        return v


class SplitItem(BaseModel):
    contact_name: str = Field(min_length=1, max_length=32)
    amount: int = Field(gt=0)


class ExpenseWalletAllocationCreate(BaseModel):
    wallet_id: int
    amount: int = Field(gt=0)


class ExpenseWalletAllocationOut(BaseModel):
    wallet_id: int
    amount: int
    wallet: Optional[WalletOut] = None

    model_config = ConfigDict(from_attributes=True)


class GoalProjectReleaseCreate(BaseModel):
    wallet_id: int
    amount: int = Field(gt=0)
    released_at: Optional[date] = None
    note: Optional[str] = Field(default=None, max_length=500)

    @field_validator("amount")
    @classmethod
    def validate_release_amount_max(cls, v: int):
        if v > MAX_INCOME_AMOUNT:
            raise ValueError("income.amount_too_large")
        return v

    @field_validator("note")
    @classmethod
    def validate_release_note(cls, v: Optional[str]):
        if v is None:
            return v
        return v.strip()


class GoalGraduateCreate(BaseModel):
    project_title: Optional[str] = Field(default=None, min_length=1, max_length=100)
    description: Optional[str] = Field(default=None, max_length=500)
    start_date: date
    target_end_date: Optional[date] = None
    total_limit: Optional[int] = Field(default=None, gt=0)
    is_isolated: bool = True
    initial_release_amount: Optional[int] = Field(default=None, gt=0)
    initial_release_wallet_id: Optional[int] = None

    @field_validator("project_title")
    @classmethod
    def validate_project_title(cls, v: Optional[str]):
        if v is None:
            return v
        return v.strip()

    @field_validator("description")
    @classmethod
    def validate_project_description(cls, v: Optional[str]):
        if v is None:
            return v
        return v.strip()

    @model_validator(mode="after")
    def validate_dates(self):
        if self.target_end_date is not None and self.target_end_date < self.start_date:
            raise ValueError("projects.target_end_before_start")
        return self


class GoalProjectReleaseOut(BaseModel):
    id: int
    owner_id: int
    goal_id: int
    project_id: int
    amount: int
    released_at: date
    note: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ExpenseSplitItemCreate(BaseModel):
    label: str = Field(min_length=1, max_length=100)
    amount: int = Field(gt=0)
    category: Optional[ExpenseCategory] = None
    subcategory_id: Optional[int] = None
    project_subcategory_id: Optional[int] = None


class ExpenseSplitItemOut(BaseModel):
    id: int
    label: Optional[str] = None
    amount: int
    category: ExpenseCategory
    subcategory_id: Optional[int] = None
    project_id: Optional[int] = None
    project_subcategory_id: Optional[int] = None
    budget_id: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class ExpenseSplitRequest(BaseModel):
    items: List[ExpenseSplitItemCreate] = Field(min_length=2)


class ExpenseCreate(ExpenseBase):
    splits: Optional[List[SplitItem]] = None
    wallet_allocations: Optional[List[ExpenseWalletAllocationCreate]] = None


class ExpenseUpdate(BaseModel):
    title: str
    description: Optional[str] = None

    model_config = ConfigDict(extra="forbid")

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: str):
        v = v.strip()
        if not (3 <= len(v) <= 32):
            raise ValueError("expenses.validation.title.length")
        return v

    @field_validator("description")
    @classmethod
    def validate_description(cls, v: Optional[str]):
        if v is None:
            return v
        v = v.strip()
        if len(v) > 500:
            raise ValueError("expenses.validation.description.max_length")
        return v


class ExpenseOut(ExpenseBase):
    transaction_type: TransactionType
    reference_type: Optional[str] = None
    id: int
    created_at: datetime
    owner_id: int
    owner: UserOut
    wallet: Optional[WalletOut] = None
    date: Optional[date]
    has_refund: bool = False
    refunded_amount: int = 0
    is_partially_refunded: bool = False
    is_fully_refunded: bool = False
    is_session: bool = False
    discount_amount: Optional[int] = None
    merge_group_id: Optional[int] = None
    merge_group_title: Optional[str] = None
    is_split: bool = False
    wallet_allocations: List[ExpenseWalletAllocationOut] = []
    split_items: List[ExpenseSplitItemOut] = []
    asset_id: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class ExpenseRelatedDebtOut(BaseModel):
    id: int
    debt_type: DebtType
    counterparty_name: str
    remaining_amount: int
    status: DebtStatus

    model_config = ConfigDict(from_attributes=True)


class RefundRequest(BaseModel):
    destination_wallet_id: Optional[int] = None
    amount: Optional[int] = None

    @field_validator("amount")
    @classmethod
    def validate_amount_positive(cls, v: Optional[int]):
        if v is not None and v <= 0:
            raise ValueError("expenses.amount_must_be_positive")
        return v


class PaginatedExpensesOut(BaseModel):
    total: int
    items: List[ExpenseOut]


class ExpenseMarkAssetRequest(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=100)
    description: Optional[str] = Field(default=None, max_length=500)
    current_value: Optional[int] = Field(default=None, ge=0)


class AssetOut(BaseModel):
    id: int
    owner_id: int
    title: str
    description: Optional[str] = None
    origin_event_id: Optional[int] = None
    purchase_value: int
    current_value: int
    status: str
    sale_event_id: Optional[int] = None
    sold_date: Optional[date] = None
    sale_value: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


ASSET_ALLOWED_STATUSES = {"owned", "sold", "disposed", "gifted", "lost"}


class AssetCreate(BaseModel):
    title: str = Field(min_length=1, max_length=100)
    description: Optional[str] = Field(default=None, max_length=500)
    purchase_value: int = Field(gt=0)
    current_value: int = Field(ge=0)
    status: str = "owned"
    origin_event_id: Optional[int] = None

    @field_validator("title")
    @classmethod
    def validate_asset_title(cls, v: str):
        return v.strip()

    @field_validator("description")
    @classmethod
    def validate_asset_description(cls, v: Optional[str]):
        if v is None:
            return v
        return v.strip()

    @field_validator("status")
    @classmethod
    def validate_asset_status(cls, v: str):
        value = v.strip().lower()
        if value not in ASSET_ALLOWED_STATUSES:
            raise ValueError("assets.status_invalid")
        return value


class AssetUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=100)
    description: Optional[str] = Field(default=None, max_length=500)
    current_value: Optional[int] = Field(default=None, ge=0)
    status: Optional[str] = None

    model_config = ConfigDict(extra="forbid")

    @field_validator("title")
    @classmethod
    def validate_optional_asset_title(cls, v: Optional[str]):
        if v is None:
            return v
        return v.strip()

    @field_validator("description")
    @classmethod
    def validate_optional_asset_description(cls, v: Optional[str]):
        if v is None:
            return v
        return v.strip()

    @field_validator("status")
    @classmethod
    def validate_optional_asset_status(cls, v: Optional[str]):
        if v is None:
            return v
        value = v.strip().lower()
        if value not in ASSET_ALLOWED_STATUSES:
            raise ValueError("assets.status_invalid")
        return value


class AssetWalletAllocationCreate(BaseModel):
    wallet_id: int
    amount: int = Field(gt=0)


class AssetSellRequest(BaseModel):
    sale_value: int = Field(ge=0)
    sold_date: Optional[date] = None
    destination_wallet_id: Optional[int] = None
    wallet_allocations: Optional[List[AssetWalletAllocationCreate]] = None
    note: Optional[str] = Field(default=None, max_length=500)
    status: str = "sold"

    @field_validator("note")
    @classmethod
    def validate_asset_sale_note(cls, v: Optional[str]):
        if v is None:
            return v
        return v.strip()

    @field_validator("status")
    @classmethod
    def validate_asset_sale_status(cls, v: str):
        value = v.strip().lower()
        if value != "sold":
            raise ValueError("assets.sale_status_invalid")
        return value


class AssetCloseRequest(BaseModel):
    closed_date: Optional[date] = None
    note: Optional[str] = Field(default=None, max_length=500)

    @field_validator("note")
    @classmethod
    def validate_asset_close_note(cls, v: Optional[str]):
        if v is None:
            return v
        return v.strip()


class PaginatedAssetsOut(BaseModel):
    total: int
    items: List[AssetOut]


class ExpenseMarkRecurringRequest(BaseModel):
    frequency: RecurringFrequency
    start_date: Optional[date] = None
    wallet_id: Optional[int] = None
    cycle_behavior: CycleBehavior = CycleBehavior.FIXED


class ExpenseMergeGroupBase(BaseModel):
    title: str = Field(min_length=1, max_length=100)
    description: Optional[str] = Field(default=None, max_length=500)

    @field_validator("title")
    @classmethod
    def validate_merge_group_title(cls, v: str):
        return v.strip()

    @field_validator("description")
    @classmethod
    def validate_merge_group_description(cls, v: Optional[str]):
        if v is None:
            return v
        return v.strip()


class ExpenseMergeGroupCreate(ExpenseMergeGroupBase):
    expense_ids: List[int] = Field(min_length=2)


class ExpenseMergeGroupUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=100)
    description: Optional[str] = Field(default=None, max_length=500)

    model_config = ConfigDict(extra="forbid")

    @field_validator("title")
    @classmethod
    def validate_optional_merge_group_title(cls, v: Optional[str]):
        if v is None:
            return v
        return v.strip()

    @field_validator("description")
    @classmethod
    def validate_optional_merge_group_description(cls, v: Optional[str]):
        if v is None:
            return v
        return v.strip()


class ExpenseMergeGroupItemsRequest(BaseModel):
    expense_ids: List[int] = Field(min_length=1)


class ExpenseMergeGroupOut(BaseModel):
    id: int
    owner_id: int
    title: str
    description: Optional[str] = None
    total_amount: int
    refunded_amount: int
    net_amount: int
    child_count: int
    earliest_date: Optional[date] = None
    latest_date: Optional[date] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ExpenseMergeGroupDetailOut(ExpenseMergeGroupOut):
    items: List[ExpenseOut]


class ExpenseFeedItemType(str, Enum):
    EXPENSE = "EXPENSE"
    MERGE_GROUP = "MERGE_GROUP"


class ExpenseFeedItemOut(BaseModel):
    type: ExpenseFeedItemType
    amount: int
    sort_date: Optional[date] = None
    sort_created_at: Optional[datetime] = None
    matched_child_count: int = 0
    expense: Optional[ExpenseOut] = None
    merge_group: Optional[ExpenseMergeGroupDetailOut] = None


class PaginatedExpenseFeedOut(BaseModel):
    total: int
    items: List[ExpenseFeedItemOut]


class ExpenseDetailOut(ExpenseOut):
    subcategory_name: Optional[str] = None
    project_subcategory_name: Optional[str] = None
    project_title: Optional[str] = None
    budget_year: Optional[int] = None
    budget_month: Optional[int] = None
    budget_effective_limit: Optional[int] = None
    budget_remaining: Optional[int] = None
    item_count: int = 0
    wallet_count: int = 0
    linked_asset: Optional["AssetOut"] = None
    merge_group: Optional[ExpenseMergeGroupOut] = None
    refund_parent: Optional[ExpenseOut] = None
    refunds: List[ExpenseOut] = []
    related_debts: List[ExpenseRelatedDebtOut] = []


class SessionDraftBase(BaseModel):
    title: str = Field(min_length=1, max_length=100)
    description: Optional[str] = Field(default=None, max_length=500)
    date: date
    amount_paid: Optional[int] = Field(default=None, gt=0)

    @field_validator("title")
    @classmethod
    def validate_session_title(cls, v: str):
        return v.strip()

    @field_validator("description")
    @classmethod
    def validate_session_description(cls, v: Optional[str]):
        if v is None:
            return v
        return v.strip()

    @field_validator("date")
    @classmethod
    def validate_session_date(cls, v: date):
        if v.year < 2020:
            raise ValueError("expenses.date_too_early")
        return v


class SessionDraftCreate(SessionDraftBase):
    source_type: ExpenseSessionDraftSource = ExpenseSessionDraftSource.MANUAL


class SessionDraftUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=100)
    description: Optional[str] = Field(default=None, max_length=500)
    date: Optional[date] = None
    amount_paid: Optional[int] = Field(default=None, gt=0)
    status: Optional[ExpenseSessionDraftStatus] = None

    model_config = ConfigDict(extra="forbid")

    @field_validator("title")
    @classmethod
    def validate_optional_session_title(cls, v: Optional[str]):
        if v is None:
            return v
        return v.strip()

    @field_validator("description")
    @classmethod
    def validate_optional_session_description(cls, v: Optional[str]):
        if v is None:
            return v
        return v.strip()

    @field_validator("date")
    @classmethod
    def validate_optional_session_date(cls, v: Optional[date]):
        if v is not None and v.year < 2020:
            raise ValueError("expenses.date_too_early")
        return v


class SessionDraftItemBase(BaseModel):
    label: str = Field(min_length=1, max_length=100)
    original_amount: int = Field(gt=0)
    category: ExpenseCategory
    subcategory_id: Optional[int] = None
    project_id: Optional[int] = None
    project_subcategory_id: Optional[int] = None
    sort_order: int = Field(default=0, ge=0)


class SessionDraftItemCreate(SessionDraftItemBase):
    pass


class SessionDraftItemUpdate(BaseModel):
    label: Optional[str] = Field(default=None, min_length=1, max_length=100)
    original_amount: Optional[int] = Field(default=None, gt=0)
    category: Optional[ExpenseCategory] = None
    subcategory_id: Optional[int] = None
    project_id: Optional[int] = None
    project_subcategory_id: Optional[int] = None
    sort_order: Optional[int] = Field(default=None, ge=0)

    model_config = ConfigDict(extra="forbid")


class SessionDraftWalletAllocationCreate(BaseModel):
    wallet_id: int
    amount: int = Field(gt=0)


class SessionDraftWalletAllocationUpdate(BaseModel):
    amount: int = Field(gt=0)


class SessionDraftSplitCreate(BaseModel):
    contact_name: str = Field(min_length=1, max_length=32)
    amount: int = Field(gt=0)


class SessionDraftSplitUpdate(BaseModel):
    contact_name: Optional[str] = Field(default=None, min_length=1, max_length=32)
    amount: Optional[int] = Field(default=None, gt=0)

    model_config = ConfigDict(extra="forbid")


class SessionDraftItemOut(BaseModel):
    id: int
    draft_id: int
    owner_id: int
    label: str
    original_amount: int
    adjusted_amount: Optional[int] = None
    category: ExpenseCategory
    subcategory_id: Optional[int] = None
    project_id: Optional[int] = None
    project_subcategory_id: Optional[int] = None
    sort_order: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SessionDraftWalletAllocationOut(BaseModel):
    id: int
    draft_id: int
    owner_id: int
    wallet_id: int
    amount: int
    wallet: Optional[WalletOut] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SessionDraftSplitOut(BaseModel):
    id: int
    draft_id: int
    owner_id: int
    contact_name: str
    amount: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SessionDraftOut(BaseModel):
    id: int
    owner_id: int
    title: str
    description: Optional[str] = None
    date: date
    amount_paid: Optional[int] = None
    status: ExpenseSessionDraftStatus
    source_type: ExpenseSessionDraftSource
    raw_ocr_text: Optional[str] = None
    finalized_event_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    items: List[SessionDraftItemOut] = []
    wallet_allocations: List[SessionDraftWalletAllocationOut] = []
    splits: List[SessionDraftSplitOut] = []
    original_total: int = 0
    allocated_wallet_total: int = 0
    split_total: int = 0
    discount_amount: Optional[int] = None
    remaining_wallet_allocation: Optional[int] = None
    can_finalize: bool = False

    model_config = ConfigDict(from_attributes=True)


# --- RECURRING EXPENSE SCHEMAS ---

class RecurringExpenseBase(BaseModel):
    title: str
    amount: int = Field(gt=0)
    category: ExpenseCategory
    description: Optional[str] = None
    frequency: RecurringFrequency
    start_date: date
    wallet_id: Optional[int] = None
    cycle_behavior: CycleBehavior = CycleBehavior.FIXED

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: str):
        v = v.strip()
        if not (3 <= len(v) <= 32):
            raise ValueError("expenses.validation.title.length")
        return v

    @field_validator("description")
    @classmethod
    def validate_description(cls, v: Optional[str]):
        if v is None:
            return v
        v = v.strip()
        if len(v) > 500:
            raise ValueError("expenses.validation.description.max_length")
        return v

    @field_validator("amount")
    @classmethod
    def validate_amount_max(cls, v: int):
        if v > MAX_EXPENSE_AMOUNT:
            raise ValueError("expenses.amount_too_large")
        return v

    @field_validator("start_date")
    @classmethod
    def validate_start_date(cls, v: date):
        if v.year < 2020:
            raise ValueError("expenses.date_too_early")
        return v


class RecurringExpenseCreate(RecurringExpenseBase):
    # Override: wallet_id is REQUIRED for creation.
    # The user must explicitly choose which wallet to charge.
    # No silent fallback to default — user controls their money.
    wallet_id: int


class RecurringExpenseUpdate(BaseModel):
    """
    PATCH-style update schema. Only supply the fields you want to change.
    Frequency and cycle_behavior are intentionally NOT editable —
    changing the cadence or behavior mid-stream would desynchronise
    the next_due_date calculations. Delete and recreate instead.
    """
    title: Optional[str] = None
    amount: Optional[int] = Field(default=None, gt=0)
    category: Optional[ExpenseCategory] = None
    description: Optional[str] = None
    wallet_id: Optional[int] = None

    model_config = ConfigDict(extra="forbid")

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: Optional[str]):
        if v is None:
            return v
        v = v.strip()
        if not (3 <= len(v) <= 32):
            raise ValueError("expenses.validation.title.length")
        return v

    @field_validator("description")
    @classmethod
    def validate_description(cls, v: Optional[str]):
        if v is None:
            return v
        v = v.strip()
        if len(v) > 500:
            raise ValueError("expenses.validation.description.max_length")
        return v

    @field_validator("amount")
    @classmethod
    def validate_amount_max(cls, v: Optional[int]):
        if v is None:
            return v
        if v > MAX_EXPENSE_AMOUNT:
            raise ValueError("expenses.amount_too_large")
        return v


class RecurringExpenseOut(RecurringExpenseBase):
    id: int
    owner_id: int
    next_due_date: date
    days_until_due: int
    status: RecurringStatus
    failing_due_date: Optional[date] = None
    wallet_id: Optional[int] = None
    cycle_behavior: CycleBehavior
    retry_count: int = 0
    original_due_day: Optional[int] = None
    created_at: datetime
    owner: UserOut

    model_config = ConfigDict(from_attributes=True)


class RecurringStatusToggle(BaseModel):
    """Payload for PATCH /recurring/{id}/toggle — switches between ACTIVE and DISABLED."""
    status: RecurringStatus

    model_config = ConfigDict(extra="forbid")


class RecurringEventOut(BaseModel):
    id: int
    recurring_expense_id: int
    event_type: RecurringEventType
    target_due_date: Optional[date] = None
    old_next_due_date: Optional[date] = None
    new_next_due_date: Optional[date] = None
    metadata_notes: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RecurringProjectionUnit(str, Enum):
    OCCURRENCES = "occurrences"
    DAYS = "days"
    WEEKS = "weeks"
    MONTHS = "months"
    QUARTERS = "quarters"
    HALF_YEARS = "half_years"
    YEARS = "years"


class RecurringProjectionHorizonIn(BaseModel):
    unit: RecurringProjectionUnit
    value: int = Field(gt=0)

    model_config = ConfigDict(extra="forbid")


class RecurringProjectionHorizonListIn(BaseModel):
    horizons: List[RecurringProjectionHorizonIn] = Field(default_factory=list, max_length=12)

    model_config = ConfigDict(extra="forbid")


class RecurringProjectionRowOut(BaseModel):
    source: str
    unit: str
    value: int
    label: str
    horizon_start: date
    horizon_end: date
    occurrence_count: int
    total_amount: int


class RecurringProjectionOut(BaseModel):
    recurring_id: int
    anchor_date: date
    default_projections: List[RecurringProjectionRowOut] = []
    custom_projections: List[RecurringProjectionRowOut] = []
    ad_hoc_projections: List[RecurringProjectionRowOut] = []


class RecurringChangeWallet(BaseModel):
    """Payload for PATCH /recurring/{id}/change-wallet"""
    wallet_id: int

    model_config = ConfigDict(extra="forbid")


# --- TOKEN SCHEMAS (For JWT Auth) ---


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    user_id: Optional[int] = None


class MessageResponse(BaseModel):
    message: str


class RefreshResponse(BaseModel):
    access_token: str
    token_type: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: str):
        return v.strip().lower()


class ResendVerificationRequest(BaseModel):
    email: EmailStr

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: str):
        return v.strip().lower()


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str

    @field_validator("token")
    @classmethod
    def validate_token(cls, v: str):
        value = v.strip()
        if not value:
            raise ValueError("auth.validation.reset.token_required")
        return value

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, v: str):
        if len(v) < 8:
            raise ValueError("auth.validation.password.min")
        if len(v) > 64:
            raise ValueError("auth.validation.password.max")
        if " " in v:
            raise ValueError("auth.validation.password.no_spaces")
        if not re.search(r"[a-z]", v):
            raise ValueError("auth.validation.password.lowercase")
        if not re.search(r"[A-Z]", v):
            raise ValueError("auth.validation.password.uppercase")
        if not re.search(r"\d", v):
            raise ValueError("auth.validation.password.number")
        if not re.search(r"[^\w\s]", v):
            raise ValueError("auth.validation.password.special")
        return v


class BudgetStatus(str, Enum):
    On_track = "On Track"
    Warning = "Warning"
    High_risk = "High Risk"
    Over_limit = "Over Limit"


class BudgetPlanStatus(str, Enum):
    COVERED_WITH_CUSHION = "covered_with_cushion"
    COVERED_NO_CUSHION = "covered_no_cushion"
    WAITING_ON_INCOME = "waiting_on_income"
    OVER_PLANNED = "over_planned"


class BudgetMonthSetupMode(str, Enum):
    PLAN_FROM_SCRATCH = "PLAN_FROM_SCRATCH"
    COPY_PREVIOUS_MONTH = "COPY_PREVIOUS_MONTH"
    SMART_AUTO_FILL = "SMART_AUTO_FILL"


# This handles the individual category objects
class CategoryStat(BaseModel):
    category: str
    total: int
    count: int
    budget_limit: int    # NEW
    remaining: int       # NEW
    percentage_used: float  # NEW
    is_over_budget: bool   # NEW
    budget_status: BudgetStatus

# This handles the overall response


class ExpenseStats(BaseModel):
    total_expenses: int
    average_expenses: float
    max_expenses: int
    min_expenses: int
    category_breakdown: List[CategoryStat]

    model_config = ConfigDict(from_attributes=True)


class BudgetBase(BaseModel):
    category: ExpenseCategory
    monthly_limit: int = Field(gt=0)
    budget_year: int
    budget_month: int
    max_envelope_balance: Optional[int] = Field(default=None, ge=0)

    @field_validator("budget_year")
    @classmethod
    def validate_budget_year(cls, v: int):
        if v < MIN_BUDGET_YEAR:
            raise ValueError("budgets.year_too_early")
        return v

    @field_validator("budget_month")
    @classmethod
    def validate_budget_month(cls, v: int):
        if v < 1 or v > 12:
            raise ValueError("budgets.month_invalid")
        return v


class BudgetCreate(BudgetBase):
    pass


class BudgetOut(BudgetBase):
    id: int
    owner_id: int
    created_at: datetime
    spent: int = 0
    effective_monthly_limit: int = 0
    cap_trim_amount: int = 0
    reallocated_in: int = 0
    reallocated_out: int = 0
    remaining: int = 0
    effective_available: int = 0
    is_over_limit: bool = False

    model_config = ConfigDict(from_attributes=True)


class BudgetUpdate(BaseModel):
    monthly_limit: Optional[int] = Field(default=None, gt=0)
    max_envelope_balance: Optional[int] = Field(default=None, ge=0)

    model_config = ConfigDict(
        from_attributes=True,
        extra="forbid"
    )


class BudgetDetailOut(BudgetOut):
    subcategories: List["BudgetSubcategoryOut"] = []
    recent_activity: List["BudgetActivityOut"] = []
    project_spending: List["BudgetProjectSpendOut"] = []
    expense_count: int = 0


class BudgetCategoryFloorOut(BaseModel):
    category: ExpenseCategory
    floor_amount: int
    effective_monthly_limit: int = 0
    shortfall: int = 0
    sources: List[str] = []


class ExpectedIncomeLifecycleTotalOut(BaseModel):
    status: ExpectedIncomeStatus
    count: int = 0
    amount: int = 0
    received_amount: int = 0


class BudgetMonthSummaryOut(BaseModel):
    budget_year: int
    budget_month: int
    owned_money_now: int
    protected_goal_money: int
    free_money_now: int
    expected_income_remaining: int = 0
    expected_income_totals: List[ExpectedIncomeLifecycleTotalOut] = []
    expected_income_items: List[ExpectedIncomeOut] = []
    cash_obligation_reserve_total: int = 0
    backing_total: int = 0
    monthly_budget_limit_total: int
    monthly_effective_limit_total: int
    normal_budget_spent: int
    valid_budget_spent: int = 0
    normal_budget_remaining: int
    category_floor_total: int = 0
    category_floor_shortfall: int = 0
    category_floors: List[BudgetCategoryFloorOut] = []
    plan_free_money_remaining: int
    plan_backing_remaining: int = 0
    cash_gap_to_budget_total: int = 0
    backing_shortfall: int = 0
    plan_status: BudgetPlanStatus
    categories_over_limit: int
    categories_close_to_limit: int
    borrowing_pressure: bool


class BudgetMonthSetupRequest(BaseModel):
    budget_year: int
    budget_month: int
    mode: BudgetMonthSetupMode

    model_config = ConfigDict(extra="forbid")

    @field_validator("budget_year")
    @classmethod
    def validate_setup_budget_year(cls, v: int):
        if v < MIN_BUDGET_YEAR:
            raise ValueError("budgets.year_too_early")
        return v

    @field_validator("budget_month")
    @classmethod
    def validate_setup_budget_month(cls, v: int):
        if v < 1 or v > 12:
            raise ValueError("budgets.month_invalid")
        return v


class BudgetMonthSetupSubcategoryLimitOut(BaseModel):
    subcategory_id: int
    name: str
    monthly_limit: int


class BudgetMonthSetupCategoryProposalOut(BaseModel):
    category: ExpenseCategory
    existing_budget_id: Optional[int] = None
    existing_monthly_limit: Optional[int] = None
    previous_budget_id: Optional[int] = None
    previous_monthly_limit: Optional[int] = None
    proposed_monthly_limit: int = 0
    floor_amount: int = 0
    floor_shortfall: int = 0
    floor_sources: List[str] = []
    copied_from_previous: bool = False
    subcategory_limits: List[BudgetMonthSetupSubcategoryLimitOut] = []


class BudgetMonthSetupPreviewOut(BaseModel):
    budget_year: int
    budget_month: int
    mode: BudgetMonthSetupMode
    source_budget_year: int
    source_budget_month: int
    category_proposals: List[BudgetMonthSetupCategoryProposalOut]
    proposed_monthly_limit_total: int = 0
    backing_total: int = 0
    backing_shortfall: int = 0
    plan_status: BudgetPlanStatus
    category_floor_total: int = 0
    category_floor_shortfall: int = 0
    cash_obligation_reserve_total: int = 0
    month_summary: BudgetMonthSummaryOut


class BudgetSubcategoryBase(BaseModel):
    category: ExpenseCategory
    name: str = Field(min_length=1, max_length=50)
    monthly_limit: Optional[int] = Field(default=None, gt=0)
    is_active: bool = True


class BudgetSubcategoryCreate(BudgetSubcategoryBase):
    pass


class BudgetSubcategoryUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=50)
    monthly_limit: Optional[int] = Field(default=None, gt=0)
    is_active: Optional[bool] = None

    model_config = ConfigDict(extra="forbid")


class BudgetSubcategoryReallocateRequest(BaseModel):
    from_subcategory_id: Optional[int] = None
    to_subcategory_id: int
    amount: int = Field(gt=0)

    model_config = ConfigDict(extra="forbid")


class BudgetSubcategoryOut(BudgetSubcategoryBase):
    id: int
    owner_id: int
    created_at: datetime
    spent: int = 0
    remaining: Optional[int] = None
    is_over_limit: bool = False

    model_config = ConfigDict(from_attributes=True)


class BudgetActivityOut(BaseModel):
    event_id: int
    title: str
    amount: int
    transaction_type: TransactionType
    date: date
    is_session: bool = False
    subcategory_id: Optional[int] = None
    subcategory_name: Optional[str] = None
    project_id: Optional[int] = None
    project_title: Optional[str] = None
    merge_group_id: Optional[int] = None
    merge_group_title: Optional[str] = None


class BudgetProjectSpendOut(BaseModel):
    project_id: int
    project_title: str
    is_isolated: bool
    spent: int


class BudgetReallocateRequest(BaseModel):
    from_category: ExpenseCategory
    to_category: ExpenseCategory
    amount: int = Field(gt=0)
    budget_year: int
    budget_month: int


class BudgetRecalculateRequest(BaseModel):
    category: ExpenseCategory


class ProjectBudgetCategoryOut(BaseModel):
    category: ExpenseCategory
    limit_amount: Optional[int] = None
    spent: int = 0
    remaining: Optional[int] = None
    is_over_limit: bool = False


class ProjectSubcategoryOut(BaseModel):
    id: int
    project_id: int
    category: ExpenseCategory
    name: str
    is_active: bool
    limit_amount: Optional[int] = None
    spent: int = 0
    remaining: Optional[int] = None
    is_over_limit: bool = False
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ProjectBudgetCategoryDetailOut(ProjectBudgetCategoryOut):
    subcategories: List["ProjectSubcategoryOut"] = []


class ProjectBudgetOut(BaseModel):
    id: int
    owner_id: int
    title: str
    description: Optional[str] = None
    is_isolated: bool
    total_limit: Optional[int] = None
    status: ProjectStatus
    origin_goal_id: Optional[int] = None
    start_date: date
    target_end_date: Optional[date] = None
    completed_at: Optional[date] = None
    spent: int = 0
    released_funding: Optional[int] = None
    remaining_funding: Optional[int] = None
    funding_shortfall: int = 0
    progress_direction: str = "tick_up"
    remaining: Optional[int] = None
    is_over_limit: bool = False
    category_breakdown: List[ProjectBudgetCategoryDetailOut] = []
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ProjectBase(BaseModel):
    title: str = Field(min_length=1, max_length=100)
    description: Optional[str] = Field(default=None, max_length=500)
    is_isolated: bool = False
    total_limit: Optional[int] = Field(default=None, gt=0)
    start_date: date
    target_end_date: Optional[date] = None
    origin_goal_id: Optional[int] = None

    @field_validator("title")
    @classmethod
    def validate_project_title(cls, v: str):
        return v.strip()

    @field_validator("description")
    @classmethod
    def validate_project_description(cls, v: Optional[str]):
        if v is None:
            return v
        return v.strip()

    @model_validator(mode="after")
    def validate_project_dates(self):
        if self.target_end_date is not None and self.target_end_date < self.start_date:
            raise ValueError("projects.target_end_before_start")
        return self


class ProjectCreate(ProjectBase):
    pass


class ProjectUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=100)
    description: Optional[str] = Field(default=None, max_length=500)
    is_isolated: Optional[bool] = None
    total_limit: Optional[int] = Field(default=None, gt=0)
    start_date: Optional[date] = None
    target_end_date: Optional[date] = None

    model_config = ConfigDict(extra="forbid")

    @field_validator("title")
    @classmethod
    def validate_optional_project_title(cls, v: Optional[str]):
        if v is None:
            return v
        return v.strip()

    @field_validator("description")
    @classmethod
    def validate_optional_project_description(cls, v: Optional[str]):
        if v is None:
            return v
        return v.strip()


class ProjectLifecycleRequest(BaseModel):
    effective_date: Optional[date] = None


class ProjectCategoryLimitCreate(BaseModel):
    category: ExpenseCategory
    limit_amount: int = Field(gt=0)


class ProjectCategoryLimitUpdate(BaseModel):
    limit_amount: int = Field(gt=0)


class ProjectSubcategoryCreate(BaseModel):
    category: ExpenseCategory
    name: str = Field(min_length=1, max_length=50)
    limit_amount: Optional[int] = Field(default=None, gt=0)
    is_active: bool = True

    @field_validator("name")
    @classmethod
    def validate_project_subcategory_name(cls, v: str):
        return v.strip()


class ProjectSubcategoryUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=50)
    limit_amount: Optional[int] = Field(default=None, gt=0)
    is_active: Optional[bool] = None

    model_config = ConfigDict(extra="forbid")

    @field_validator("name")
    @classmethod
    def validate_optional_project_subcategory_name(cls, v: Optional[str]):
        if v is None:
            return v
        return v.strip()


class AnalyticsHistory(BaseModel):
    total_spent_lifetime: int
    average_transaction: float
    total_transaction: int
    member_since: Optional[date]


class DailyTrendItem(BaseModel):
    date: date
    amount: int


class CategoryBreakdownItem(BaseModel):
    category: str
    total: int
    count: int


class DashboardSummary(BaseModel):
    income: int
    spent: int
    remaining: int
    daily_average: int
    overall_balance: int


class CreateInvoiceIn(BaseModel):
    plan_id: str

    model_config = ConfigDict(extra="forbid")


class CreateInvoiceOut(BaseModel):
    order_code: str
    amount: int
    currency: str
    plan_id: str


# --- NOTIFICATION SCHEMAS ---


class NotificationTypeEnum(str, Enum):
    BUDGET_WARNING = "budget_warning"
    BUDGET_EXCEEDED = "budget_exceeded"
    RECURRING_DUE = "recurring_due"
    GOAL_MILESTONE = "goal_milestone"
    GOAL_COMPLETED = "goal_completed"
    DEBT_DUE_SOON = "debt_due_soon"
    DEBT_OVERDUE = "debt_overdue"
    DEBT_PAYMENT_PAID = "debt_payment_paid"
    DEBT_FULLY_PAID = "debt_fully_paid"
    SYSTEM = "system"


class NotificationPriorityEnum(str, Enum):
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class NotificationOut(BaseModel):
    id: int
    type: str
    title: str
    message: str
    is_read: bool
    priority: str
    extra_data: Optional[dict] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class NotificationListOut(BaseModel):
    total: int
    unread_count: int
    items: List[NotificationOut]


class NotificationMarkRead(BaseModel):
    notification_ids: List[int]

    @field_validator("notification_ids")
    @classmethod
    def validate_notification_ids(cls, v: List[int]):
        if not v:
            raise ValueError("notifications.ids_required")
        if len(v) > 100:
            raise ValueError("notifications.too_many_ids")
        return v


# --- DEBT SCHEMAS (Qarz) ---


class DebtBase(BaseModel):
    debt_type: DebtType
    origin_kind: DebtOriginKind = DebtOriginKind.IMPORTED_BALANCE
    counterparty_kind: DebtCounterpartyKind = DebtCounterpartyKind.OTHER
    product_kind: Optional[DebtProductKind] = None
    counterparty_name: str
    initial_amount: int = Field(gt=0)
    currency: str = "UZS"
    description: Optional[str] = None
    date: date
    expected_return_date: Optional[date] = None

    @field_validator("counterparty_name")
    @classmethod
    def validate_counterparty_name(cls, v: str):
        value = v.strip()
        if not (1 <= len(value) <= 100):
            raise ValueError("debts.counterparty_name_length")
        return value

    @field_validator("description")
    @classmethod
    def validate_description(cls, v: Optional[str]):
        if v is None:
            return v
        value = v.strip()
        if len(value) > 1000:
            raise ValueError("debts.description_too_long")
        return value


class DebtInitialWalletAllocationIn(BaseModel):
    wallet_id: int
    amount: int = Field(gt=0)


class DebtCreate(DebtBase):
    is_money_transferred: bool = False
    initial_wallet_id: Optional[int] = None
    initial_wallet_allocations: List[DebtInitialWalletAllocationIn] = Field(default_factory=list)
    expense_category: Optional[ExpenseCategory] = None
    expense_subcategory_id: Optional[int] = None
    project_id: Optional[int] = None
    project_subcategory_id: Optional[int] = None
    income_source_id: Optional[int] = None

    @model_validator(mode="after")
    def validate_semantics(self):
        if self.expected_return_date is not None and self.date is not None and self.expected_return_date < self.date:
            raise ValueError("debts.validation.expected_date_before_date")
        if (
            self.debt_type == DebtType.OWING
            and not self.is_money_transferred
            and not self.initial_wallet_allocations
            and self.expense_category is None
        ):
            raise ValueError("debts.validation.expense_category.required")
        return self


class DebtUpdate(BaseModel):
    counterparty_name: Optional[str] = None
    description: Optional[str] = None
    date: Optional[dt.date] = None
    expected_return_date: Optional[dt.date] = None
    status: Optional[DebtStatus] = None
    origin_kind: Optional[DebtOriginKind] = None
    counterparty_kind: Optional[DebtCounterpartyKind] = None
    product_kind: Optional[DebtProductKind] = None
    initial_amount: Optional[int] = Field(default=None, gt=0)
    expense_category: Optional[ExpenseCategory] = None
    expense_subcategory_id: Optional[int] = None
    project_id: Optional[int] = None
    project_subcategory_id: Optional[int] = None
    income_source_id: Optional[int] = None

    @field_validator("counterparty_name")
    @classmethod
    def validate_counterparty_name(cls, v: Optional[str]):
        if v is not None:
            value = v.strip()
            if not (1 <= len(value) <= 100):
                raise ValueError("debts.counterparty_name_length")
        return v

    @field_validator("initial_amount")
    @classmethod
    def validate_initial_amount_max(cls, v: Optional[int]):
        if v is not None and v > MAX_EXPENSE_AMOUNT:
            raise ValueError("debts.amount_too_large")
        return v

    @model_validator(mode="after")
    def validate_expected_return_date(self):
        if self.expected_return_date is not None and self.date is not None and self.expected_return_date < self.date:
            raise ValueError("debts.validation.expected_date_before_date")
        return self


class DebtTransactionBase(BaseModel):
    amount: int = Field(gt=0)
    date: date
    note: Optional[str] = None
    wallet_id: Optional[int] = None


class DebtTransactionCreate(DebtTransactionBase):
    debt_id: int
    income_source_id: Optional[int] = None


class DebtTransactionWalletAllocationIn(BaseModel):
    wallet_id: int
    amount: int = Field(gt=0)


class DebtPaymentCreate(BaseModel):
    amount: int = Field(gt=0)
    date: Optional[dt.date] = None
    note: Optional[str] = None
    wallet_allocations: List[DebtTransactionWalletAllocationIn] = Field(default_factory=list)
    income_source_id: Optional[int] = None


class DebtTransactionWalletAllocationOut(BaseModel):
    id: int
    owner_id: int
    debt_id: int
    debt_transaction_id: int
    wallet_id: int
    amount: int
    wallet: Optional["WalletOut"] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DebtTransactionOut(DebtTransactionBase):
    id: int
    owner_id: int
    debt_id: int
    created_at: datetime
    wallet: Optional["WalletOut"] = None  # To show wallet name in history
    wallet_allocations: List[DebtTransactionWalletAllocationOut] = []

    model_config = ConfigDict(from_attributes=True)


class GoalDebtPaymentResultOut(BaseModel):
    goal: GoalWithProgressOut
    debt: "DebtOut"
    debt_transaction: DebtTransactionOut
    consumed_amount: int = 0


class DebtAddChargeRequest(BaseModel):
    amount: int = Field(gt=0)
    reason: Optional[str] = Field(None, max_length=200)

    @field_validator("amount")
    @classmethod
    def validate_amount_max(cls, v: int):
        if v > MAX_EXPENSE_AMOUNT:
            raise ValueError("debts.charge.amount_too_large")
        return v


class DebtChargeOut(BaseModel):
    id: int
    debt_id: int
    amount: int
    reason: Optional[str] = None
    date: date
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class DebtLedgerEntryOut(BaseModel):
    id: int
    owner_id: int
    debt_id: int
    financial_event_id: Optional[int] = None
    source_debt_transaction_id: Optional[int] = None
    source_debt_charge_id: Optional[int] = None
    reverses_entry_id: Optional[int] = None
    wallet_id: Optional[int] = None
    asset_id: Optional[int] = None
    entry_type: DebtLedgerEntryType
    amount_delta: int
    principal_delta: int = 0
    charge_delta: int = 0
    balance_after: Optional[int] = None
    event_subtype: Optional[str] = None
    source: DebtLedgerEntrySource = DebtLedgerEntrySource.USER
    is_reversible: bool = True
    status: str
    entry_date: date
    note: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DebtOut(DebtBase):
    id: int
    owner_id: int
    remaining_amount: int
    status: DebtStatus
    created_at: datetime
    updated_at: datetime
    is_money_transferred: bool = False
    initial_wallet_id: Optional[int] = None
    has_archived_transactions: bool = False
    total_charges: int = 0
    expense_category: Optional[ExpenseCategory] = None
    expense_subcategory_id: Optional[int] = None
    project_id: Optional[int] = None
    project_subcategory_id: Optional[int] = None
    income_source_id: Optional[int] = None
    managed_by_installment_plan_id: Optional[int] = None
    workflow_warnings: List[str] = Field(default_factory=list)
    source_type: str = "DEBT"
    wallet_id: Optional[int] = None
    wallet_name: Optional[str] = None
    wallet_type: Optional[WalletType] = None
    available_actions: List[str] = Field(default_factory=list)
    model_config = ConfigDict(from_attributes=True)


class DebtActionDecisionOut(BaseModel):
    action_kind: DebtActionKind
    allowed: bool
    reason_code: Optional[str] = None
    level: Optional[DebtActionRestrictionLevel] = None
    requires_confirmation: bool = False
    undo_available: bool = True
    source: DebtActionRestrictionSource = DebtActionRestrictionSource.POLICY
    details: Dict[str, Any] = Field(default_factory=dict)


class DebtActivityItemOut(BaseModel):
    ledger_entry_id: int
    kind: DebtLedgerEntryType
    title: str
    description: Optional[str] = None
    amount_delta: int
    principal_delta: int = 0
    charge_delta: int = 0
    balance_after: Optional[int] = None
    event_subtype: Optional[str] = None
    entry_date: date
    created_at: datetime
    source: DebtLedgerEntrySource = DebtLedgerEntrySource.USER
    is_reversible: bool = True
    reversal: Optional[DebtActionDecisionOut] = None
    financial_event_id: Optional[int] = None
    source_debt_transaction_id: Optional[int] = None
    source_debt_charge_id: Optional[int] = None
    reverses_entry_id: Optional[int] = None
    wallet_id: Optional[int] = None
    asset_id: Optional[int] = None


class DebtFormalDetailsUpdate(BaseModel):
    institution_name: Optional[str] = Field(default=None, max_length=100)
    contract_number: Optional[str] = Field(default=None, max_length=100)
    linked_asset_id: Optional[int] = None
    collateral_asset_id: Optional[int] = None
    statement_balance: Optional[int] = Field(default=None, ge=0)
    statement_balance_date: Optional[date] = None
    next_due_date: Optional[date] = None
    annual_rate_bps: Optional[int] = Field(default=None, ge=0)
    terms_summary: Optional[str] = Field(default=None, max_length=500)
    extra_data: Optional[Dict[str, Any]] = None


class DebtFormalDetailsOut(DebtFormalDetailsUpdate):
    debt_id: int
    owner_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DebtForgivenessCreate(BaseModel):
    amount: Optional[int] = Field(default=None, gt=0)
    date: Optional[dt.date] = None
    note: Optional[str] = Field(default=None, max_length=500)


class DebtSettlementCreate(BaseModel):
    payment_amount: int = Field(ge=0)
    settlement_discount: Optional[int] = Field(default=None, ge=0)
    date: Optional[dt.date] = None
    note: Optional[str] = Field(default=None, max_length=500)
    wallet_allocations: List[DebtTransactionWalletAllocationIn] = Field(default_factory=list)


class DebtBalanceAdjustmentCreate(BaseModel):
    confirmed_balance: int = Field(ge=0)
    date: Optional[dt.date] = None
    note: Optional[str] = Field(default=None, max_length=500)


class DebtLedgerEntryReverseCreate(BaseModel):
    date: Optional[dt.date] = None
    note: Optional[str] = Field(default=None, max_length=500)


class DebtDetailsOut(BaseModel):
    debt: DebtOut
    formal_details: Optional[DebtFormalDetailsOut] = None
    installment_plan: Optional["InstallmentPlanWithPaymentsOut"] = None
    actions: List[DebtActionDecisionOut] = []
    transactions: List[DebtTransactionOut] = []
    charges: List[DebtChargeOut] = []
    ledger_entries: List[DebtLedgerEntryOut] = []
    activity: List[DebtActivityItemOut] = []


class DebtWithTransactionsOut(DebtOut):
    transactions: List[DebtTransactionOut] = []
    charges: List[DebtChargeOut] = []
    ledger_entries: List[DebtLedgerEntryOut] = []
    model_config = ConfigDict(from_attributes=True)


class DebtListOut(BaseModel):
    total: int
    items: List[DebtOut]


class DebtSummaryOut(BaseModel):
    total_i_owe: int = 0
    total_owed_to_me: int = 0


# --- INSTALLMENT SCHEMAS (Nasiya) ---


class InstallmentWalletAllocationIn(BaseModel):
    wallet_id: int
    amount: int = Field(gt=0)


class InstallmentPlanBase(BaseModel):
    item_name: str
    store_or_bank_name: Optional[str] = None
    plan_type: PaymentPlanType = PaymentPlanType.STORE_INSTALLMENT
    total_price: int = Field(gt=0)
    down_payment: int = Field(ge=0)
    months: int = Field(gt=0)
    frequency: InstallmentFrequency = InstallmentFrequency.MONTHLY
    start_date: date
    expense_category: Optional[ExpenseCategory] = None
    expense_subcategory_id: Optional[int] = None
    project_id: Optional[int] = None
    project_subcategory_id: Optional[int] = None

    @field_validator("item_name")
    @classmethod
    def validate_item_name(cls, v: str):
        value = v.strip()
        if not (1 <= len(value) <= 100):
            raise ValueError("installments.item_name_length")
        return value


class InstallmentPlanCreate(InstallmentPlanBase):
    wallet_allocations: List[InstallmentWalletAllocationIn] = Field(default_factory=list)
    category: ExpenseCategory = ExpenseCategory.INSTALLMENTS_DEBT
    track_as_asset: bool = False
    asset_current_value: Optional[int] = Field(default=None, ge=0)
    loan_disbursement_wallet_id: Optional[int] = None


class InstallmentPlanUpdate(BaseModel):
    item_name: Optional[str] = None
    store_or_bank_name: Optional[str] = None
    total_price: Optional[int] = Field(default=None, gt=0)
    months: Optional[int] = Field(default=None, gt=0)
    frequency: Optional[InstallmentFrequency] = None
    start_date: Optional[date] = None
    status: Optional[InstallmentStatus] = None

    @field_validator("item_name")
    @classmethod
    def validate_update_item_name(cls, v: Optional[str]):
        if v is None:
            return v
        value = v.strip()
        if not (1 <= len(value) <= 100):
            raise ValueError("installments.item_name_length")
        return value


class InstallmentPaymentBase(BaseModel):
    amount: int = Field(gt=0)
    due_date: date
    note: Optional[str] = None


class InstallmentPaymentUpdate(BaseModel):
    status: Optional[InstallmentPaymentStatus] = None
    paid_date: Optional[date] = None
    note: Optional[str] = None
    event_id: Optional[int] = None
    expense_id: Optional[int] = None


class InstallmentPaymentAllocationOut(BaseModel):
    id: int
    owner_id: int
    installment_payment_id: int
    financial_event_id: Optional[int] = None
    debt_transaction_id: Optional[int] = None
    debt_ledger_entry_id: Optional[int] = None
    wallet_id: Optional[int] = None
    amount: int
    paid_date: date
    note: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class InstallmentPaymentOut(InstallmentPaymentBase):
    id: int
    owner_id: int
    plan_id: int
    debt_charge_id: Optional[int] = None
    paid_amount: int = 0
    written_off_amount: int = 0
    component_type: InstallmentPaymentComponentType = InstallmentPaymentComponentType.PRINCIPAL
    status: InstallmentPaymentStatus
    paid_date: Optional[date] = None
    event_id: Optional[int] = None
    expense_id: Optional[int] = None
    debt_ledger_entry_id: Optional[int] = None
    allocations: List[InstallmentPaymentAllocationOut] = []
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class InstallmentPlanOut(InstallmentPlanBase):
    id: int
    owner_id: int
    debt_id: Optional[int] = None
    asset_id: Optional[int] = None
    remaining_amount: int
    currency: str
    monthly_payment_amount: int
    payment_count: int
    regular_payment_amount: int
    schedule_rule: Optional[Dict[str, Any]] = None
    status: InstallmentStatus
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class InstallmentPlanWithPaymentsOut(InstallmentPlanOut):
    payments: List[InstallmentPaymentOut] = []
    model_config = ConfigDict(from_attributes=True)


class InstallmentPlanListOut(BaseModel):
    total: int
    items: List[InstallmentPlanWithPaymentsOut]


class InstallmentPaymentListOut(BaseModel):
    total: int
    items: List[InstallmentPaymentOut]


class InstallmentSummaryOut(BaseModel):
    pending_count: int = 0
    pending_amount: int = 0
    paid_count: int = 0
    paid_amount: int = 0
    overdue_count: int = 0
    overdue_amount: int = 0


class InstallmentPaymentRecordCreate(BaseModel):
    amount: int = Field(gt=0)
    paid_date: Optional[dt.date] = None
    wallet_allocations: List[InstallmentWalletAllocationIn] = Field(default_factory=list)
    note: Optional[str] = Field(default=None, max_length=200)


class InstallmentPlanDetailsOut(BaseModel):
    plan: InstallmentPlanWithPaymentsOut
    debt: Optional[DebtOut] = None
    debt_actions: List[DebtActionDecisionOut] = []
    debt_activity: List[DebtActivityItemOut] = []


class MarkPaidIn(BaseModel):
    paid_date: Optional[date] = None
    wallet_allocations: List[InstallmentWalletAllocationIn] = Field(default_factory=list)
    category: Optional[ExpenseCategory] = None
    note: Optional[str] = None


class InstallmentChargeCreate(BaseModel):
    charge_type: str
    amount: int = Field(gt=0)
    date: Optional[dt.date] = None
    wallet_allocations: List[InstallmentWalletAllocationIn] = Field(default_factory=list)
    category: ExpenseCategory = ExpenseCategory.DEBT_CHARGES
    note: Optional[str] = None

    @field_validator("charge_type")
    @classmethod
    def validate_charge_type(cls, value: str):
        normalized = value.strip().upper()
        if normalized not in {"FEE", "PENALTY"}:
            raise ValueError("installments.invalid_charge_type")
        return normalized
