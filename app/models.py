from sqlalchemy import Boolean, CheckConstraint, Column, Date, Index, Integer, BigInteger, String, DateTime, ForeignKey, Enum, UniqueConstraint
from sqlalchemy.sql import func
from .session import Base
import enum
from sqlalchemy.orm import relationship
from datetime import date


class ExpenseCategory(str, enum.Enum):
    GROCERIES = "Groceries"
    DINING_OUT = "Dining Out"
    ELECTRONICS = "Electronics"
    HOUSING = "Housing"
    UTILITIES = "Utilities"
    SUBSCRIPTIONS = "Subscriptions"
    TRANSPORT = "Transport"
    HEALTH = "Health"
    PERSONAL_CARE = "Personal care"
    EDUCATION = "Education"
    CLOTHING = "Clothing"
    FAMILY_EVENTS = "Family & Events"
    ENTERTAINMENT = "Entertainment"
    INSTALLMENTS_DEBT = "Installments & Debt"
    BUSINESS_WORK = "Business / Work"


class RecurringFrequency(str, enum.Enum):
    DAILY = "DAILY"
    WEEKLY = "WEEKLY"
    MONTHLY = "MONTHLY"
    YEARLY = "YEARLY"


class LifeStatus(str, enum.Enum):
    STUDENT = "student"
    EMPLOYED = "employed"
    SELF_EMPLOYED = "self_employed"
    BUSINESS_OWNER = "business_owner"
    UNEMPLOYED = "unemployed"


class SavingsTransactionType(str, enum.Enum):
    DEPOSIT = "DEPOSIT"
    WITHDRAWAL = "WITHDRAWAL"


class GoalStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    ARCHIVED = "ARCHIVED"


class GoalContributionType(str, enum.Enum):
    ALLOCATE = "ALLOCATE"
    RETURN = "RETURN"


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
    is_premium = Column(Boolean, default=False, nullable=False)
    timezone = Column(String(50), default="UTC", nullable=False)
    profile = relationship(
        "UserProfile",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )
    identities = relationship(
        "UserIdentity", back_populates="user", cascade="all, delete-orphan")
    # This allows you to do: some_user.expenses to see all their spending
    expenses = relationship(
        "Expense", back_populates="owner", cascade="all, delete")
    recurring_expenses = relationship(
        "RecurringExpense", back_populates="owner", cascade="all, delete")
    income_sources = relationship(
        "IncomeSource", back_populates="owner", cascade="all, delete")
    income_entries = relationship(
        "IncomeEntry", back_populates="owner", cascade="all, delete")
    budgets = relationship(
        "Budget", back_populates="owner", cascade="all, delete")
    savings_transactions = relationship(
        "SavingsTransactions", back_populates="owner", cascade="all, delete")
    goals = relationship(
        "Goals", back_populates="owner", cascade="all, delete")
    goal_contributions = relationship(
        "GoalContributions", back_populates="owner", cascade="all, delete")
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
    category = Column(Enum(ExpenseCategory), nullable=False)  # No default
    description = Column(String, nullable=True)
    owner_id = Column(Integer, ForeignKey(
        "users.id", ondelete="CASCADE"), nullable=False)
    owner = relationship("User", back_populates="expenses")
    budget_id = Column(Integer, ForeignKey(
        "budgets.id", ondelete="RESTRICT"), nullable=True, index=True)
    budget = relationship("Budget", back_populates="expenses")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    date = Column(Date, nullable=False, default=date.today)


class UserProfile(Base):
    __tablename__ = "user_profiles"
    __table_args__ = (
        UniqueConstraint("user_id", name="uq_user_profiles_user_id"),
        CheckConstraint(
            "monthly_income_amount >= 0",
            name="ck_user_profiles_monthly_income_amount_non_negative",
        ),
        CheckConstraint(
            "initial_balance >= 0",
            name="ck_user_profiles_initial_balance_non_negative",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    life_status = Column(Enum(LifeStatus), nullable=False)
    monthly_income_amount = Column(BigInteger, nullable=False)
    initial_balance = Column(BigInteger, nullable=False, default=0)
    budget_rollover_enabled = Column(Boolean, nullable=False, default=True)
    onboarding_completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True),
                        server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    user = relationship("User", back_populates="profile")


class IncomeSource(Base):
    __tablename__ = "income_sources"
    __table_args__ = (
        UniqueConstraint("owner_id", "name",
                         name="uq_income_sources_owner_name"),
    )

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey(
        "users.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(32), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True),
                        server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    owner = relationship("User", back_populates="income_sources")
    income_entries = relationship("IncomeEntry", back_populates="source")


class IncomeEntry(Base):
    __tablename__ = "income_entries"
    __table_args__ = (
        CheckConstraint(
            "amount > 0", name="ck_income_entries_amount_positive"),
        CheckConstraint("date >= '2020-01-01'",
                        name="ck_income_entries_date_min_2020_01_01"),
        Index("ix_income_entries_owner_date", "owner_id", "date"),
    )

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey(
        "users.id", ondelete="CASCADE"), nullable=False, index=True)
    source_id = Column(Integer, ForeignKey(
        "income_sources.id", ondelete="SET NULL"), nullable=True, index=True)
    amount = Column(BigInteger, nullable=False)
    note = Column(String(200), nullable=True)
    date = Column(Date, nullable=False, default=date.today)
    created_at = Column(DateTime(timezone=True),
                        server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    owner = relationship("User", back_populates="income_entries")
    source = relationship("IncomeSource", back_populates="income_entries")


class RecurringExpense(Base):
    __tablename__ = "recurring_expenses"
    __table_args__ = (
        CheckConstraint(
            "start_date >= '2020-01-01'",
            name="ck_recurring_expenses_start_date_min_2020_01_01",
        ),
    )
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(32), nullable=False)
    amount = Column(BigInteger, nullable=False)
    category = Column(Enum(ExpenseCategory), nullable=False)
    description = Column(String, nullable=True)
    frequency = Column(Enum(RecurringFrequency), nullable=False)
    start_date = Column(Date, nullable=False)
    next_due_date = Column(Date, nullable=False, index=True)
    is_active = Column(Boolean, default=True, nullable=False)
    owner_id = Column(Integer, ForeignKey(
        "users.id", ondelete="CASCADE"), nullable=False, index=True)
    owner = relationship("User", back_populates="recurring_expenses")
    created_at = Column(DateTime(timezone=True), server_default=func.now())


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
    auto_created = Column(Boolean, default=False, nullable=False)

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


class SavingsTransactions(Base):
    __tablename__ = "savings_transactions"
    __table_args__ = (
        CheckConstraint(
            "amount > 0", name="ck_savings_transactions_amount_positive"),
        Index("ix_savings_transactions_owner_created_at",
              "owner_id", "created_at"),
    )

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey(
        "users.id", ondelete="CASCADE"), nullable=False, index=True)
    amount = Column(BigInteger, nullable=False)
    transaction_type = Column(Enum(SavingsTransactionType), nullable=False)
    created_at = Column(DateTime(timezone=True),
                        server_default=func.now(), nullable=False)

    owner = relationship("User", back_populates="savings_transactions")


class Goals(Base):
    __tablename__ = "goals"
    __table_args__ = (
        CheckConstraint("target_amount > 0",
                        name="ck_goals_target_amount_positive"),
        Index("ix_goals_owner_status", "owner_id", "status"),
    )

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey(
        "users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(32), nullable=False)
    target_amount = Column(BigInteger, nullable=False)
    target_date = Column(Date, nullable=True)
    status = Column(Enum(GoalStatus), nullable=False,
                    default=GoalStatus.ACTIVE)
    created_at = Column(DateTime(timezone=True),
                        server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(
    ), onupdate=func.now(), nullable=False)

    owner = relationship("User", back_populates="goals")
    contributions = relationship(
        "GoalContributions", back_populates="goal", cascade="all, delete")


class GoalContributions(Base):
    __tablename__ = "goal_contributions"
    __table_args__ = (
        CheckConstraint(
            "amount > 0", name="ck_goal_contributions_amount_positive"),
        Index("ix_goal_contributions_owner_created_at",
              "owner_id", "created_at"),
        Index("ix_goal_contributions_goal_created_at", "goal_id", "created_at"),
    )

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey(
        "users.id", ondelete="CASCADE"), nullable=False, index=True)
    goal_id = Column(Integer, ForeignKey(
        "goals.id", ondelete="CASCADE"), nullable=False, index=True)
    amount = Column(BigInteger, nullable=False)
    contribution_type = Column(Enum(GoalContributionType), nullable=False)
    created_at = Column(DateTime(timezone=True),
                        server_default=func.now(), nullable=False)

    owner = relationship("User", back_populates="goal_contributions")
    goal = relationship("Goals", back_populates="contributions")
