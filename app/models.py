from sqlalchemy import Boolean, Column, Date, Integer, BigInteger, String, DateTime, ForeignKey, Enum
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


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # This allows you to do: some_user.expenses to see all their spending
    expenses = relationship(
        "Expense", back_populates="owner", cascade="all, delete")
    budgets = relationship(
        "Budget", back_populates="owner", cascade="all, delete")


class Expense(Base):
    __tablename__ = "expenses"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    amount = Column(BigInteger, nullable=False)
    category = Column(Enum(ExpenseCategory), name="expense_category_enum",
                      default=ExpenseCategory.OTHER, nullable=False)
    description = Column(String, nullable=True)
    owner_id = Column(Integer, ForeignKey(
        "users.id", ondelete="CASCADE"), nullable=False)
    owner = relationship("User")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    date = Column(Date, nullable=False, default=date.today)


class Budget(Base):
    __tablename__ = "budgets"

    id = Column(Integer, primary_key=True, index=True)
    category = Column(Enum(ExpenseCategory), nullable=False)
    monthly_limit = Column(BigInteger, nullable=False)

    # NEW: This is the 'Memory' we discussed to prevent notification spam
    # It stores the highest threshold already reached this month (e.g., 50 or 90)
    last_notified_threshold = Column(Integer, default=0, nullable=False)
    last_notified_month = Column(Integer, default=0, nullable=False)
    last_notified_year = Column(Integer, default=0, nullable=False)

    owner_id = Column(Integer, ForeignKey(
        "users.id", ondelete="CASCADE"), nullable=False)
    owner = relationship("User")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    is_active = Column(Boolean, default=True)
