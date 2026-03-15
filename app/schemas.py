from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator
from typing import List, Optional
from datetime import datetime, date
from enum import Enum
import re

from .models import (
    ExpenseCategory,
    GoalContributionType,
    GoalStatus,
    LifeStatus,
    RecurringFrequency,
    SavingsTransactionType,
)  # Importing enums

MIN_BUDGET_YEAR = 2020
MAX_BUDGET_YEARS_AHEAD = 5
MAX_INCOME_AMOUNT = 999_999_999_999


class GoalTimeState(str, Enum):
    ON_TRACK = "on_track"
    DUE_SOON = "due_soon"
    OVERDUE = "overdue"


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


class UserOnboardingUpsert(BaseModel):
    life_status: LifeStatus
    initial_balance: int = Field(ge=0)

    @field_validator("initial_balance")
    @classmethod
    def validate_initial_balance_max(cls, v: int):
        if v > MAX_INCOME_AMOUNT:
            raise ValueError("income.amount_too_large")
        return v


class UserProfileOut(BaseModel):
    id: int
    user_id: int
    life_status: LifeStatus
    monthly_income_amount: int
    initial_balance: int
    budget_rollover_enabled: bool = True
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


class IncomeEntryBase(BaseModel):
    amount: int = Field(gt=0)
    date: date
    note: Optional[str] = None
    source_id: Optional[int] = None

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
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PaginatedIncomeEntriesOut(BaseModel):
    total: int
    items: List[IncomeEntryOut]


class SavingsTransactionCreate(BaseModel):
    amount: int = Field(gt=0)

    @field_validator("amount")
    @classmethod
    def validate_amount_max(cls, v: int):
        if v > MAX_INCOME_AMOUNT:
            raise ValueError("income.amount_too_large")
        return v


class SavingsTransactionOut(BaseModel):
    id: int
    owner_id: int
    amount: int
    transaction_type: SavingsTransactionType
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class GoalBase(BaseModel):
    title: str
    target_amount: int = Field(gt=0)
    target_date: Optional[date] = None

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
    target_date: Optional[date] = None
    status: Optional[GoalStatus] = None

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

    @field_validator("target_date")
    @classmethod
    def validate_target_date(cls, v: Optional[date]):
        if v is None:
            return v
        if v.year < 2020:
            raise ValueError("expenses.date_too_early")
        return v


class GoalContributionCreate(BaseModel):
    amount: int = Field(gt=0)

    @field_validator("amount")
    @classmethod
    def validate_amount_max(cls, v: int):
        if v > MAX_INCOME_AMOUNT:
            raise ValueError("income.amount_too_large")
        return v


class GoalContributionOut(BaseModel):
    id: int
    owner_id: int
    goal_id: int
    amount: int
    contribution_type: GoalContributionType
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class GoalOut(GoalBase):
    id: int
    owner_id: int
    status: GoalStatus
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class GoalWithProgressOut(GoalOut):
    funded_amount: int = 0
    remaining_amount: int = 0
    progress_percent: float = 0
    time_state: Optional[GoalTimeState] = None
    days_until_target: Optional[int] = None


class SavingsSummaryOut(BaseModel):
    total_balance: int
    free_savings_balance: int
    locked_in_goals: int
    spendable_balance: int


# --- EXPENSE SCHEMAS ---
MAX_EXPENSE_AMOUNT = 999_999_999_999


class ExpenseBase(BaseModel):
    title: str
    amount: int = Field(
        gt=0, description="The amount must be a positive integer")
    category: ExpenseCategory  # This ensures only our defined Enum values are accepted
    description: Optional[str] = None
    date: date

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


class ExpenseCreate(ExpenseBase):
    pass  # Used when a user POSTs a new expense


class ExpenseUpdate(BaseModel):
    # PUT is treated as full replacement for editable fields.
    title: str
    amount: int = Field(gt=0)
    description: Optional[str] = None
    date: date

    model_config = ConfigDict(extra="forbid")

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


class ExpenseOut(ExpenseBase):
    id: int
    created_at: datetime
    owner_id: int
    owner: UserOut
    date: Optional[date]

    model_config = ConfigDict(from_attributes=True)


class PaginatedExpensesOut(BaseModel):
    total: int
    items: List[ExpenseOut]


# --- RECURRING EXPENSE SCHEMAS ---

class RecurringExpenseBase(BaseModel):
    title: str
    amount: int = Field(gt=0)
    category: ExpenseCategory
    description: Optional[str] = None
    frequency: RecurringFrequency
    start_date: date

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
    pass


class RecurringExpenseUpdate(BaseModel):
    """
    PATCH-style update schema. Only supply the fields you want to change.
    Frequency is intentionally NOT editable — changing the cadence mid-stream
    would desynchronise next_due_date. Delete and recreate instead.
    """
    title: Optional[str] = None
    amount: Optional[int] = Field(default=None, gt=0)
    category: Optional[ExpenseCategory] = None
    description: Optional[str] = None

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
    is_active: bool
    created_at: datetime
    owner: UserOut

    model_config = ConfigDict(from_attributes=True)


class RecurringActiveToggle(BaseModel):
    """Payload for PATCH /recurring/{id}/active"""
    is_active: bool

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
    rollover_amount: int = 0
    effective_monthly_limit: int = 0

    model_config = ConfigDict(from_attributes=True)


class UserBudgetRolloverPreferenceUpdate(BaseModel):
    budget_rollover_enabled: bool


class BudgetUpdate(BaseModel):
    monthly_limit: int = Field(..., gt=0)

    model_config = ConfigDict(
        from_attributes=True,
        extra="forbid"
    )


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
