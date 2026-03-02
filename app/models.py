from sqlalchemy import Boolean, CheckConstraint, Column, Date, Index, Integer, BigInteger, String, DateTime, ForeignKey, Enum, UniqueConstraint
from sqlalchemy.sql import func
from .session import Base
import enum
from sqlalchemy.orm import relationship
from datetime import date


class ExpenseCategory(str, enum.Enum):
    FOOD = "Food"
    TRANSPORT = "Transport"
    HOUSING = "Housing"
    ENTERTAINMENT = "Entertainment"
    UTILITIES = "Utilities"
    OTHER = "Other"


class UserIdentity(Base):
    __tablename__ = "user_identities"
    __table_args__ = (
        UniqueConstraint("provider", "provider_user_id",
                         name="uq_provider_provider_user_id"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey(
        "users.id", ondelete="CASCADE"), nullable=False, index=True)

    # e.g. "local", "google"
    provider = Column(String(50), nullable=False)

    # local: str(user.id) or normalized email; google: id_token "sub"
    provider_user_id = Column(String(255), nullable=False)

    provider_email = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True),
                        server_default=func.now(), nullable=False)

    user = relationship("User", back_populates="identities")


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    is_verified = Column(Boolean, default=False, nullable=False)
    identities = relationship(
        "UserIdentity", back_populates="user", cascade="all, delete-orphan")
    # This allows you to do: some_user.expenses to see all their spending
    expenses = relationship(
        "Expense", back_populates="owner", cascade="all, delete")
    budgets = relationship(
        "Budget", back_populates="owner", cascade="all, delete")
    reset_tokens = relationship(
        "PasswordResetToken", back_populates="user", cascade="all, delete-orphan")
    email_verification_tokens = relationship(
        "EmailVerificationToken", back_populates="user", cascade="all, delete-orphan")


class Expense(Base):
    __tablename__ = "expenses"
    __table_args__ = (
        CheckConstraint(
            "date >= '2020-01-01'",
            name="ck_expenses_date_min_2020_01_01",
        ),
    )
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(32), nullable=False)
    amount = Column(BigInteger, nullable=False)
    category = Column(Enum(ExpenseCategory), default=ExpenseCategory.OTHER, nullable=False)
    description = Column(String, nullable=True)
    owner_id = Column(Integer, ForeignKey(
        "users.id", ondelete="CASCADE"), nullable=False)
    owner = relationship("User", back_populates="expenses")
    budget_id = Column(Integer, ForeignKey(
        "budgets.id", ondelete="RESTRICT"), nullable=True, index=True)
    budget = relationship("Budget", back_populates="expenses")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    date = Column(Date, nullable=False, default=date.today)


class Budget(Base):
    __tablename__ = "budgets"
    __table_args__ = (
        UniqueConstraint("owner_id", "category", "budget_year",
                         "budget_month", name="uq_budgets_owner_category_year_month"),
        CheckConstraint("budget_month >= 1 AND budget_month <=12",
                        name="ck_budgets_budget_month_1_12"),
        CheckConstraint(
            "budget_year >= 2020",
            name="ck_budgets_budget_year_min_2020",
        ),
        Index("ix_budgets_owner_year_month",
              "owner_id", "budget_year", "budget_month")
    )

    id = Column(Integer, primary_key=True, index=True)
    category = Column(Enum(ExpenseCategory), nullable=False)
    monthly_limit = Column(BigInteger, nullable=False)

    budget_year = Column(Integer, nullable=False)
    budget_month = Column(Integer, nullable=False)

    owner_id = Column(Integer, ForeignKey(
        "users.id", ondelete="CASCADE"), nullable=False)
    owner = relationship("User", back_populates="budgets")
    expenses = relationship("Expense", back_populates="budget")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    # is_active = Column(Boolean, default=True)


class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey(
        "users.id", ondelete="CASCADE"), nullable=False, index=True)
    token_hash = Column(String, nullable=False, unique=True)
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)
    used_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True),
                        server_default=func.now(), nullable=False)
    user = relationship("User", back_populates="reset_tokens")


class EmailVerificationToken(Base):
    __tablename__ = "email_verification_tokens"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey(
        "users.id", ondelete="CASCADE"), nullable=False, index=True)
    token_hash = Column(String, nullable=False, unique=True)
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)
    used_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True),
                        server_default=func.now(), nullable=False)
    user = relationship("User", back_populates="email_verification_tokens")
