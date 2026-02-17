from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator
from typing import List, Optional
from datetime import datetime, date
from enum import Enum
import re

from sqlalchemy import Column, Integer
from .models import ExpenseCategory  # Importing the enum we defined in models.py

# --- USER SCHEMAS ---


class UserBase(BaseModel):
    username: str
    email: EmailStr

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str):
        v = v.strip()
        if not (3 <= len(v) <= 32):
            raise ValueError("Username must be 3-32 characters long")
        if " " in v:
            raise ValueError("Username cannot contain spaces")
        if not re.fullmatch(r"[A-Za-z0-9._]+", v):
            raise ValueError("Username can only use letters, numbers, dots, and underscores")
        if v[0] in "._" or v[-1] in "._":
            raise ValueError("Username cannot start or end with . or _")
        if ".." in v or "__" in v or "._" in v or "_." in v:
            raise ValueError("Username cannot contain consecutive or mixed separators")
        if v.isdigit():
            raise ValueError("Username cannot be only numbers")
        return v

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: str):
        v = v.strip().lower()
        if len(v) > 254:
            raise ValueError("Email is too long")
        local, _, domain = v.partition("@")
        if len(local) > 64:
            raise ValueError("Email local part is too long")
        if not domain or "." not in domain:
            raise ValueError("Email domain must contain a dot")
        return v


class UserCreate(UserBase):
    password: str  # Only used during registration

    @field_validator('password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError("Password too short (min 8)")
        if len(v) > 64:
            raise ValueError("Password too long (max 64)")
        if " " in v:
            raise ValueError("Password cannot contain spaces")
        if not re.search(r"[a-z]", v):
            raise ValueError("Password must include a lowercase letter")
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must include an uppercase letter")
        if not re.search(r"\d", v):
            raise ValueError("Password must include a number")
        if not re.search(r"[^\w\s]", v):
            raise ValueError("Password must include a special character")
        return v


class UserOut(UserBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- EXPENSE SCHEMAS ---

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
            raise ValueError(
                "Date is too far in the past (must be 2020 or later)")

        return v

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: str):
        v = v.strip()
        if not (3 <= len(v) <= 80):
            raise ValueError("Title must be 3-80 characters long")
        return v

    @field_validator("description")
    @classmethod
    def validate_description(cls, v: Optional[str]):
        if v is None:
            return v
        v = v.strip()
        if len(v) > 500:
            raise ValueError("Description must be 500 characters or less")
        return v


class ExpenseCreate(ExpenseBase):
    pass  # Used when a user POSTs a new expense


class ExpenseUpdate(BaseModel):
    # Everything is optional in an update so the user can change just one field
    title: Optional[str] = None
    amount: Optional[int] = Field(None, gt=0)
    category: Optional[ExpenseCategory] = None
    description: Optional[str] = None
    date: Optional[date]


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


class BudgetStatus(str, Enum):
    Healthy = "Healthy"
    Critical = "Critical"
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


class BudgetCreate(BudgetBase):
    pass


class BudgetOut(BudgetBase):
    id: int
    owner_id: int
    created_at: datetime
    # This is the 'Memory' piece we need for notifications4
    model_config = ConfigDict(from_attributes=True)


class BudgetUpdate(BaseModel):
    # This is the ONLY thing a user should touch
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
