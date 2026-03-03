from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator
from typing import List, Optional
from datetime import datetime, date
from enum import Enum
import re

from .models import ExpenseCategory  # Importing the enum we defined in models.py

MIN_BUDGET_YEAR = 2020
MAX_BUDGET_YEARS_AHEAD = 5


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


class UserOut(UserBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


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

    @model_validator(mode="after")
    def validate_budget_window(self):
        candidate = date(self.budget_year, self.budget_month, 1)
        min_allowed = date(MIN_BUDGET_YEAR, 1, 1)

        today = date.today()
        max_allowed = date(today.year + MAX_BUDGET_YEARS_AHEAD, today.month, 1)

        if candidate < min_allowed:
            raise ValueError("budgets.month_too_early")

        if candidate > max_allowed:
            raise ValueError("budgets.month_too_far_in_future")

        return self


class BudgetCreate(BudgetBase):
    pass


class BudgetOut(BudgetBase):
    id: int
    owner_id: int
    created_at: datetime
    spent: int = 0

    model_config = ConfigDict(from_attributes=True)


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
