# pyrefly: ignore [missing-import]
from sqlalchemy import Boolean, CheckConstraint, Column, Date, Index, Integer, BigInteger, String, DateTime, ForeignKey, Enum, UniqueConstraint, JSON
# pyrefly: ignore [missing-import]
from sqlalchemy.sql import func
from .session import Base
import enum
# pyrefly: ignore [missing-import]
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
    PAYMENT_PLANS_DEBT = "Installments & Debt"
    BUSINESS_WORK = "Business / Work"
    BANK_FEES_INTEREST = "Bank Fees & Interest"
    DEBT_CHARGES = "Debt Charges"
    TRAVEL = "Travel"
    CHARITY = "Charity"
    ANIMALS_PETS = "Animals & Pets"


class WalletType(str, enum.Enum):
    CASH = "CASH"
    DEBIT = "DEBIT"
    CREDIT = "CREDIT"
    PRELOADED = "PRELOADED"
    SAVINGS = "SAVINGS"


class AccountingType(str, enum.Enum):
    ASSET = "ASSET"  # Positive balance (My money)
    LIABILITY = "LIABILITY"  # Negative balance (Borrowed money)


class TransactionType(str, enum.Enum):
    EXPENSE = "EXPENSE"
    INCOME = "INCOME"
    TRANSFER = "TRANSFER"
    REFUND = "REFUND"
    ADJUSTMENT = "ADJUSTMENT"
    DEBT_SETTLEMENT = "DEBT_SETTLEMENT"
    NEUTRAL_FLOW = "NEUTRAL_FLOW"


class FinancialEventStatus(str, enum.Enum):
    POSTED = "POSTED"
    VOIDED = "VOIDED"
    REVERSAL = "REVERSAL"


class ReferenceType:
    """Application-level constants for transaction sub-classification.
    Stored as VARCHAR(50) in DB — no migration needed for new values.

    Rule: reference_type provides context that NO OTHER FIELD already provides.
    If debt_id, recurring_id, or original_transaction_id already tells you
    the context, you don't need a reference_type.
    """

    # ── TRANSFER sub-types (preserves direction for savings/goals) ────
    SAVINGS_DEPOSIT = "savings_deposit"
    SAVINGS_WITHDRAWAL = "savings_withdrawal"
    GOAL_ALLOCATION = "goal_allocation"
    GOAL_RETURN = "goal_return"
    GOAL_CONSUME = "goal_consume"
    GOAL_PLANNED_PURCHASE = "goal_planned_purchase"
    GOAL_ACHIEVED_OUTSIDE_FUNDS = "goal_achieved_outside_funds"
    WALLET_OBLIGATION_PAYOFF = "wallet_obligation_payoff"

    # ── DEBT_SETTLEMENT sub-types ─────────────────────────────────────
    DEBT_INITIAL = "debt_initial"
    LOAN_DISBURSEMENT = "loan_disbursement"
    DEBT_REPAYMENT = "debt_repayment"
    DEBT_EXPENSE = "debt_expense"
    DEBT_INCOME = "debt_income"
    DEBT_CHARGE = "debt_charge"
    DAMAGE_COMPENSATION = "damage_compensation"

    # ── EXPENSE sub-types (bank-driven, bypass wallet limits) ─────────
    BANK_FEE = "bank_fee"
    BANK_INTEREST = "bank_interest"
    PAYMENT_PLAN_DOWN_PAYMENT = "payment_plan_down_payment"
    PAYMENT_PLAN_PAYMENT = "payment_plan_payment"
    VOID_REVERSAL = "void_reversal"
    PAYMENT_PLAN_FEE = "payment_plan_fee"
    PAYMENT_PLAN_PENALTY = "payment_plan_penalty"



    # ── INCOME sub-types (distinguishes earnings from asset recovery) ──
    ASSET_SALE = "asset_sale"

    # ── NEUTRAL_FLOW sub-types (for future Send/Receive actions) ──────
    PASSTHROUGH = "passthrough"
    INSURANCE_PAYOUT = "insurance_payout"
    SECURITY_DEPOSIT = "security_deposit"

    # ── ADJUSTMENT sub-types ──────────────────────────────────────────
    BALANCE_CORRECTION = "balance_correction"


class RecurringFrequency(str, enum.Enum):
    ONE_TIME = "ONE_TIME"
    DAILY = "DAILY"
    WEEKLY = "WEEKLY"
    BIWEEKLY = "BIWEEKLY"
    MONTHLY = "MONTHLY"
    QUARTERLY = "QUARTERLY"
    SEMI_ANNUALLY = "SEMI_ANNUALLY"
    YEARLY = "YEARLY"


class RecurringStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"      # Normal — User wants this to run
    DISABLED = "DISABLED"  # User manually turned off (the toggle switch)


class CycleBehavior(str, enum.Enum):
    FIXED = "FIXED"        # Next due date anchored to calendar (rent, cleaner)
    FLEXIBLE = "FLEXIBLE"  # Next due date shifts on late payment (Netflix, gym)

class RecurringOccurrenceStatus(str, enum.Enum):
    PENDING_CONFIRMATION = "PENDING_CONFIRMATION"
    FULFILLED = "FULFILLED"
    SKIPPED = "SKIPPED"
    CANCELLED = "CANCELLED"


class RecurringEventType(str, enum.Enum):
    CREATED = "CREATED"
    PAID = "PAID"
    SKIPPED = "SKIPPED"
    FAILED = "FAILED"
    UPDATED = "UPDATED"
    RESUMED = "RESUMED"


class RecurringEvent(Base):
    __tablename__ = "recurring_events"
    
    id = Column(Integer, primary_key=True, index=True)
    recurring_expense_id = Column(Integer, ForeignKey("recurring_expenses.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # What happened?
    event_type = Column(Enum(RecurringEventType), nullable=False)
    
    # Which specific occurrence does this event refer to? (e.g., The '2026-06-01' bill)
    target_due_date = Column(Date, nullable=False)
    
    # The state of the "Sticky Note" before and after this event
    old_next_due_date = Column(Date, nullable=True)
    new_next_due_date = Column(Date, nullable=True)
    
    # Optional: A place to dump error messages if it FAILED, or manual notes.
    metadata_notes = Column(String, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    recurring_expense = relationship("RecurringExpense", back_populates="events")


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
    GRADUATED = "GRADUATED"  # Goal became a Project via Graduation Pipeline
    ARCHIVED = "ARCHIVED"


class GoalCompletionMode(str, enum.Enum):
    GOAL_FUNDED = "GOAL_FUNDED"
    ACHIEVED_OUTSIDE_RESERVED_FUNDS = "ACHIEVED_OUTSIDE_RESERVED_FUNDS"


class DebtGoalTrackingMode(str, enum.Enum):
    FULL_REMAINING_DEBT = "FULL_REMAINING_DEBT"
    FIXED_DEBT_AMOUNT = "FIXED_DEBT_AMOUNT"


class GoalContributionType(str, enum.Enum):
    ALLOCATE = "ALLOCATE"
    RETURN = "RETURN"
    CONSUME = "CONSUME"


class GoalIntent(str, enum.Enum):
    RESERVE = "RESERVE"
    PLANNED_PURCHASE = "PLANNED_PURCHASE"
    PAY_OBLIGATION = "PAY_OBLIGATION"
    FUND_PROJECT = "FUND_PROJECT"


class DebtType(str, enum.Enum):
    OWED = "OWED"  # Money others owe me (receivable)
    OWING = "OWING"  # Money I owe others (payable)


class DebtStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    OVERDUE = "OVERDUE"
    DEFAULTED = "DEFAULTED"
    IN_COLLECTION = "IN_COLLECTION"
    PAID = "PAID"
    SETTLED = "SETTLED"
    FORGIVEN = "FORGIVEN"
    WRITTEN_OFF = "WRITTEN_OFF"
    ARCHIVED = "ARCHIVED"


class DebtOriginKind(str, enum.Enum):
    CASH_BORROWED = "CASH_BORROWED"
    CASH_LENT = "CASH_LENT"
    DEFERRED_EXPENSE = "DEFERRED_EXPENSE"
    SPLIT_REIMBURSEMENT = "SPLIT_REIMBURSEMENT"
    PERSONAL_REIMBURSEMENT = "PERSONAL_REIMBURSEMENT"
    RECEIVABLE_INCOME = "RECEIVABLE_INCOME"
    FINANCED_ASSET_PURCHASE = "FINANCED_ASSET_PURCHASE"
    DAMAGE_COMPENSATION = "DAMAGE_COMPENSATION"
    IMPORTED_BALANCE = "IMPORTED_BALANCE"


class DebtCounterpartyKind(str, enum.Enum):
    PERSON = "PERSON"
    BANK = "BANK"
    COMPANY = "COMPANY"
    STORE = "STORE"
    GOVERNMENT = "GOVERNMENT"
    OTHER = "OTHER"


class DebtProductKind(str, enum.Enum):
    INFORMAL_DEBT = "INFORMAL_DEBT"
    BANK_LOAN = "BANK_LOAN"
    CAR_LOAN = "CAR_LOAN"
    MORTGAGE = "MORTGAGE"
    STORE_INSTALLMENT = "STORE_INSTALLMENT"
    SERVICE_PAY_LATER = "SERVICE_PAY_LATER"
    PERSONAL_REIMBURSEMENT = "PERSONAL_REIMBURSEMENT"
    CLIENT_RECEIVABLE = "CLIENT_RECEIVABLE"
    OTHER = "OTHER"


class DebtLedgerEntryType(str, enum.Enum):
    INITIAL = "INITIAL"
    CHARGE = "CHARGE"
    PAYMENT = "PAYMENT"
    FORGIVENESS = "FORGIVENESS"
    ADJUSTMENT = "ADJUSTMENT"
    REVERSAL = "REVERSAL"
    ASSET_SETTLEMENT = "ASSET_SETTLEMENT"


class DebtLedgerEntrySource(str, enum.Enum):
    USER = "USER"
    SYSTEM = "SYSTEM"
    IMPORT = "IMPORT"


class DebtAssetSettlementType(str, enum.Enum):
    ASSET_RECEIVED = "ASSET_RECEIVED"
    ASSET_GIVEN = "ASSET_GIVEN"
    COLLATERAL_TAKEN = "COLLATERAL_TAKEN"


class DebtActionKind(str, enum.Enum):
    RECORD_PAYMENT = "RECORD_PAYMENT"
    ADD_CHARGE = "ADD_CHARGE"
    FORGIVE_PARTIAL = "FORGIVE_PARTIAL"
    FORGIVE_FULL = "FORGIVE_FULL"
    ADJUST_BALANCE = "ADJUST_BALANCE"
    REVERSE_ENTRY = "REVERSE_ENTRY"
    ARCHIVE = "ARCHIVE"
    RESTORE = "RESTORE"
    LINK_ASSET = "LINK_ASSET"
    SET_COLLATERAL = "SET_COLLATERAL"
    RESTRUCTURE_TERMS = "RESTRUCTURE_TERMS"


class DebtActionRestrictionLevel(str, enum.Enum):
    BLOCKED = "BLOCKED"
    REQUIRES_CONFIRMATION = "REQUIRES_CONFIRMATION"
    UNDO_UNAVAILABLE = "UNDO_UNAVAILABLE"


class DebtActionRestrictionSource(str, enum.Enum):
    SYSTEM = "SYSTEM"
    USER = "USER"
    POLICY = "POLICY"


class PaymentPlanFrequency(str, enum.Enum):
    WEEKLY = "WEEKLY"
    BIWEEKLY = "BIWEEKLY"
    MONTHLY = "MONTHLY"
    QUARTERLY = "QUARTERLY"
    YEARLY = "YEARLY"
    CUSTOM = "CUSTOM"


class PaymentPlanType(str, enum.Enum):
    STORE_INSTALLMENT = "STORE_INSTALLMENT"
    PRODUCT_FINANCING = "PRODUCT_FINANCING"
    MORTGAGE = "MORTGAGE"
    AUTO_LOAN = "AUTO_LOAN"
    BANK_LOAN = "BANK_LOAN"
    EDUCATION_LOAN = "EDUCATION_LOAN"
    SERVICE_CONTRACT = "SERVICE_CONTRACT"
    OTHER = "OTHER"


class PaymentPlanStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    PAID = "PAID"
    ARCHIVED = "ARCHIVED"


class PaymentPlanPaymentStatus(str, enum.Enum):
    PENDING = "PENDING"
    PARTIAL = "PARTIAL"
    PAID = "PAID"
    SKIPPED = "SKIPPED"
class PaymentPlanPaymentComponentType(str, enum.Enum):
    PRINCIPAL = "PRINCIPAL"
    CHARGE = "CHARGE"


class PaymentPlanLedgerEntryType(str, enum.Enum):
    INITIAL = "INITIAL"
    PAYMENT = "PAYMENT"
    CHARGE = "CHARGE"
    ADJUSTMENT = "ADJUSTMENT"
    REVERSAL = "REVERSAL"


class PaymentPlanLedgerEntrySource(str, enum.Enum):
    USER = "USER"
    SYSTEM = "SYSTEM"


class ExpectedIncomeStatus(str, enum.Enum):
    EXPECTED = "EXPECTED"
    PARTIALLY_RECEIVED = "PARTIALLY_RECEIVED"
    RESOLVED = "RESOLVED"
    SUPERSEDED = "SUPERSEDED"
    WRITTEN_OFF = "WRITTEN_OFF"
    RECEIVED = "RECEIVED"
    MISSED = "MISSED"
    CANCELLED = "CANCELLED"


class ExpectedInflowKind(str, enum.Enum):
    EARNED = "EARNED"
    RECEIVABLE = "RECEIVABLE"
    REFUND = "REFUND"
    ASSET_SALE = "ASSET_SALE"


class ExpectedInflowPromiseStatus(str, enum.Enum):
    EXPECTED = "EXPECTED"
    PARTIALLY_RECEIVED = "PARTIALLY_RECEIVED"
    RESOLVED = "RESOLVED"
    CANCELLED = "CANCELLED"
    WRITTEN_OFF = "WRITTEN_OFF"


class ProjectStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    STOPPED = "STOPPED"
    COMPLETED = "COMPLETED"
    ARCHIVED = "ARCHIVED"


class ProjectType(str, enum.Enum):
    OVERLAY = "OVERLAY"
    ISOLATED = "ISOLATED"


class ExpenseSessionDraftStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    FINALIZED = "FINALIZED"
    ABANDONED = "ABANDONED"


class ExpenseSessionDraftSource(str, enum.Enum):
    MANUAL = "MANUAL"
    OCR = "OCR"


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
    premium_expires_at = Column(DateTime(timezone=True), nullable=True)
    timezone = Column(String(50), default="UTC", nullable=False)
    total_debts_created = Column(Integer, default=0, nullable=False)
    profile = relationship(
        "UserProfile",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )
    identities = relationship(
        "UserIdentity", back_populates="user", cascade="all, delete-orphan")
    # The Grand Unification relationships
    financial_events = relationship(
        "FinancialEvent", back_populates="owner", cascade="all, delete")
    wallet_ledger_entries = relationship(
        "WalletLedger", back_populates="owner", cascade="all, delete")
    assets = relationship(
        "Asset", back_populates="owner", cascade="all, delete")
    recurring_expenses = relationship(
        "RecurringExpense", back_populates="owner", cascade="all, delete")
    recurring_occurrences = relationship(
        "RecurringOccurrence", back_populates="owner", cascade="all, delete-orphan")
    income_sources = relationship(
        "IncomeSource", back_populates="owner", cascade="all, delete")
    income_entries = relationship(
        "IncomeEntry", back_populates="owner", cascade="all, delete")
    expected_incomes = relationship(
        "ExpectedIncome", back_populates="owner", cascade="all, delete-orphan")
    expected_inflow_promises = relationship(
        "ExpectedInflowPromise", back_populates="owner", cascade="all, delete-orphan")
    expected_inflow_realizations = relationship(
        "ExpectedInflowRealization", back_populates="owner", cascade="all, delete-orphan")
    budgets = relationship(
        "Budget", back_populates="owner", cascade="all, delete")
    borrowing_survival_plans = relationship(
        "BorrowingSurvivalPlan", back_populates="owner", cascade="all, delete-orphan")
    budget_subcategory_limits = relationship(
        "BudgetSubcategoryLimit", back_populates="owner", cascade="all, delete-orphan")
    savings_transactions = relationship(
        "SavingsTransactions", back_populates="owner", cascade="all, delete")
    goals = relationship(
        "Goals", back_populates="owner", cascade="all, delete")
    goal_contributions = relationship(
        "GoalContributions", back_populates="owner", cascade="all, delete")
    goal_project_releases = relationship(
        "GoalProjectRelease", back_populates="owner", cascade="all, delete-orphan")
    isolated_project_wallet_allocations = relationship(
        "IsolatedProjectWalletAllocation", back_populates="owner", cascade="all, delete-orphan")
    reset_tokens = relationship(
        "PasswordResetToken", back_populates="user", cascade="all, delete-orphan")
    email_verification_tokens = relationship(
        "EmailVerificationToken", back_populates="user", cascade="all, delete-orphan")
    notifications = relationship(
        "Notification", back_populates="owner", cascade="all, delete")
    debts = relationship(
        "Debt", back_populates="owner", cascade="all, delete")
    debt_transactions = relationship(
        "DebtTransaction", back_populates="owner", cascade="all, delete")
    debt_charges = relationship(
        "DebtCharge", back_populates="owner", cascade="all, delete")
    debt_ledger_entries = relationship(
        "DebtLedgerEntry", back_populates="owner", cascade="all, delete")
    debt_formal_details = relationship(
        "DebtFormalDetails", back_populates="owner", cascade="all, delete-orphan")
    debt_transaction_wallet_allocations = relationship(
        "DebtTransactionWalletAllocation", back_populates="owner", cascade="all, delete-orphan")
    debt_asset_settlements = relationship(
        "DebtAssetSettlement", back_populates="owner", cascade="all, delete-orphan")
    payment_plans = relationship(
        "PaymentPlan", back_populates="owner", cascade="all, delete")
    payment_plan_transactions = relationship(
        "PaymentPlanTransaction", back_populates="owner", cascade="all, delete")
    payment_plan_charges = relationship(
        "PaymentPlanCharge", back_populates="owner", cascade="all, delete")
    payment_plan_ledger_entries = relationship(
        "PaymentPlanLedgerEntry", back_populates="owner", cascade="all, delete")
    payment_plan_payments = relationship(
        "PaymentPlanPayment", back_populates="owner", cascade="all, delete")
    payment_plan_payment_allocations = relationship(
        "PaymentPlanPaymentAllocation", back_populates="owner", cascade="all, delete-orphan")
    payment_plan_transaction_wallet_allocations = relationship(
        "PaymentPlanTransactionWalletAllocation", back_populates="owner", cascade="all, delete-orphan")
    wallets = relationship(
        "Wallet", back_populates="owner", cascade="all, delete-orphan")
    wallet_transfers = relationship(
        "WalletTransfer", back_populates="owner", cascade="all, delete-orphan")
    projects = relationship(
        "Project", back_populates="owner", cascade="all, delete")
    expense_merge_groups = relationship(
        "ExpenseMergeGroup", back_populates="owner", cascade="all, delete-orphan")
    subcategories = relationship(
        "UserSubcategory", back_populates="owner", cascade="all, delete")
    expense_session_drafts = relationship(
        "ExpenseSessionDraft", back_populates="owner", cascade="all, delete-orphan")
    expense_session_draft_items = relationship(
        "ExpenseSessionDraftItem", back_populates="owner", cascade="all, delete-orphan")
    expense_session_draft_wallet_allocations = relationship(
        "ExpenseSessionDraftWalletAllocation", back_populates="owner", cascade="all, delete-orphan")
    expense_session_draft_splits = relationship(
        "ExpenseSessionDraftSplit", back_populates="owner", cascade="all, delete-orphan")


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
        CheckConstraint(
            "monthly_income_amount <= 999999999999",
            name="ck_user_profiles_income_limit",
        ),
        CheckConstraint(
            "initial_balance <= 999999999999",
            name="ck_user_profiles_initial_balance_limit",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    life_status = Column(Enum(LifeStatus), nullable=True) # Old single status, keeping for migration
    life_statuses = Column(JSON, nullable=False, server_default='[]') # New multi-status
    monthly_income_amount = Column(BigInteger, nullable=False)
    initial_balance = Column(BigInteger, nullable=False, default=0)
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


class Wallet(Base):
    __tablename__ = "wallets"
    __table_args__ = (
        CheckConstraint(
            "(wallet_type = 'CREDIT') OR "
            "((wallet_type = 'CASH' OR wallet_type = 'SAVINGS') AND initial_balance >= 0) OR "
            "((wallet_type = 'DEBIT' OR wallet_type = 'PRELOADED') AND (has_overdraft = TRUE OR initial_balance >= 0))",
            name="ck_wallets_initial_balance_integrity"
        ),
        CheckConstraint(
            "accounting_type = 'ASSET' OR wallet_type = 'CREDIT' OR can_fund_goals = FALSE",
            name="ck_wallets_goal_funding_owned_money_only",
        ),
        # current_balance constraint removed to allow for Liability/Overdraft negative balances
        CheckConstraint(
            "initial_balance BETWEEN -999999999999 AND 999999999999",
            name="ck_wallets_initial_balance_limit"
        ),
        CheckConstraint(
            "overdraft_limit <= 999999999999",
            name="ck_wallets_overdraft_limit"
        ),
        CheckConstraint(
            "credit_limit <= 999999999999",
            name="ck_wallets_credit_limit"
        ),
        Index("ix_wallets_owner_id", "owner_id"),
    )

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(32), nullable=False)
    wallet_type = Column(Enum(WalletType), nullable=False, default=WalletType.DEBIT)
    accounting_type = Column(Enum(AccountingType), nullable=False, default=AccountingType.ASSET)
    
    initial_balance = Column(BigInteger, nullable=False, default=0)
    current_balance = Column(BigInteger, nullable=False, default=0)
    
    # Nuance Fields
    overdraft_limit = Column(BigInteger, nullable=True, default=0) # For Debit
    has_overdraft = Column(Boolean, nullable=False, default=False)
    
    credit_limit = Column(BigInteger, nullable=False, default=0) # For Credit
    allow_overlimit = Column(Boolean, nullable=False, default=False)
    
    billing_cycle_start_day = Column(Integer, nullable=True) # 1-31
    payment_due_day = Column(Integer, nullable=True) # 1-31
    
    color = Column(String(50), default="default", nullable=False)
    currency = Column(String(3), default="UZS", nullable=False)
    can_fund_goals = Column(Boolean, default=False, server_default="false", nullable=False)
    is_default = Column(Boolean, default=False, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False) # Soft Delete
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    owner = relationship("User", back_populates="wallets")
    ledger_entries = relationship("WalletLedger", back_populates="wallet", cascade="all, delete-orphan")
    goal_contributions = relationship("GoalContributions", back_populates="wallet")
    isolated_project_allocations = relationship("IsolatedProjectWalletAllocation", back_populates="wallet")


class WalletTransfer(Base):
    __tablename__ = "wallet_transfers"
    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_wallet_transfers_amount_positive"),
        CheckConstraint("amount <= 999999999999", name="ck_wallet_transfers_amount_limit"),
        CheckConstraint("from_wallet_id != to_wallet_id", name="ck_wallet_transfers_different_wallets"),
    )

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    from_wallet_id = Column(Integer, ForeignKey("wallets.id", ondelete="CASCADE"), nullable=False)
    to_wallet_id = Column(Integer, ForeignKey("wallets.id", ondelete="CASCADE"), nullable=False)
    amount = Column(BigInteger, nullable=False)
    note = Column(String(200), nullable=True)
    date = Column(Date, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    owner = relationship("User", back_populates="wallet_transfers")
    from_wallet = relationship("Wallet", foreign_keys=[from_wallet_id])
    to_wallet = relationship("Wallet", foreign_keys=[to_wallet_id])


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
    expected_incomes = relationship("ExpectedIncome", back_populates="source")
    expected_inflow_promises = relationship("ExpectedInflowPromise", back_populates="source")


class IncomeEntry(Base):
    __tablename__ = "income_entries"
    __table_args__ = (
        CheckConstraint(
            "amount > 0", name="ck_income_entries_amount_positive"),
        CheckConstraint("date >= '2020-01-01'",
                        name="ck_income_entries_date_min_2020_01_01"),
        CheckConstraint("amount <= 999999999999", name="ck_income_entries_amount_limit"),
        Index("ix_income_entries_owner_date", "owner_id", "date"),
    )

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey(
        "users.id", ondelete="CASCADE"), nullable=False, index=True)
    source_id = Column(Integer, ForeignKey(
        "income_sources.id", ondelete="SET NULL"), nullable=True, index=True)
    wallet_id = Column(Integer, ForeignKey("wallets.id", ondelete="SET NULL"), nullable=True, index=True)
    wallet = relationship("Wallet")
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


class ExpectedInflowPromise(Base):
    __tablename__ = "expected_inflow_promises"
    __table_args__ = (
        CheckConstraint("original_amount > 0", name="ck_expected_inflow_promises_amount_positive"),
        CheckConstraint("original_amount <= 999999999999", name="ck_expected_inflow_promises_amount_limit"),
        CheckConstraint(
            "(CASE WHEN source_id IS NOT NULL THEN 1 ELSE 0 END + "
            "CASE WHEN debt_id IS NOT NULL THEN 1 ELSE 0 END + "
            "CASE WHEN asset_id IS NOT NULL THEN 1 ELSE 0 END + "
            "CASE WHEN refund_event_id IS NOT NULL THEN 1 ELSE 0 END) = 1",
            name="ck_expected_inflow_promises_exactly_one_source",
        ),
        Index("ix_expected_inflow_promises_owner_status", "owner_id", "status"),
        Index("ix_expected_inflow_promises_owner_kind", "owner_id", "kind"),
    )

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    kind = Column(String(32), nullable=False, default=ExpectedInflowKind.EARNED.value, index=True)
    source_id = Column(Integer, ForeignKey("income_sources.id", ondelete="RESTRICT"), nullable=True, index=True)
    debt_id = Column(Integer, ForeignKey("debts.id", ondelete="RESTRICT"), nullable=True, index=True)
    asset_id = Column(Integer, ForeignKey("assets.id", ondelete="RESTRICT"), nullable=True, index=True)
    refund_event_id = Column(Integer, ForeignKey("financial_events.id", ondelete="RESTRICT"), nullable=True, index=True)
    title = Column(String(100), nullable=False)
    original_amount = Column(BigInteger, nullable=False)
    status = Column(
        Enum(ExpectedInflowPromiseStatus),
        nullable=False,
        default=ExpectedInflowPromiseStatus.EXPECTED,
    )
    backing_eligible = Column(Boolean, nullable=False, default=True)
    note = Column(String(200), nullable=True)
    closed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    owner = relationship("User", back_populates="expected_inflow_promises")
    source = relationship("IncomeSource", back_populates="expected_inflow_promises")
    debt = relationship("Debt", foreign_keys=[debt_id])
    asset = relationship("Asset", foreign_keys=[asset_id])
    refund_event = relationship("FinancialEvent", foreign_keys=[refund_event_id])
    schedules = relationship(
        "ExpectedIncome",
        back_populates="promise",
        cascade="all, delete-orphan",
        order_by="ExpectedIncome.due_date, ExpectedIncome.id",
    )
    realizations = relationship("ExpectedInflowRealization", back_populates="promise")
    write_offs = relationship(
        "ExpectedInflowWriteOff",
        back_populates="promise",
        cascade="all, delete-orphan",
    )


class ExpectedIncome(Base):
    __tablename__ = "expected_incomes"
    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_expected_incomes_amount_positive"),
        CheckConstraint("amount <= 999999999999", name="ck_expected_incomes_amount_limit"),
        CheckConstraint("due_date >= '2020-01-01'", name="ck_expected_incomes_due_date_min_2020_01_01"),
        CheckConstraint("budget_month >= 1 AND budget_month <= 12", name="ck_expected_incomes_budget_month_1_12"),
        CheckConstraint("budget_year >= 2020", name="ck_expected_incomes_budget_year_min_2020"),
        CheckConstraint(
            "(CASE WHEN source_id IS NOT NULL THEN 1 ELSE 0 END + "
            "CASE WHEN debt_id IS NOT NULL THEN 1 ELSE 0 END + "
            "CASE WHEN asset_id IS NOT NULL THEN 1 ELSE 0 END + "
            "CASE WHEN refund_event_id IS NOT NULL THEN 1 ELSE 0 END) = 1",
            name="ck_expected_incomes_exactly_one_source",
        ),
        Index("ix_expected_incomes_owner_month_status", "owner_id", "budget_year", "budget_month", "status"),
        Index("ix_expected_incomes_owner_kind_status", "owner_id", "kind", "status"),
        Index("ix_expected_incomes_owner_source", "owner_id", "source_id"),
    )

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    promise_id = Column(
        Integer,
        ForeignKey("expected_inflow_promises.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    kind = Column(String(32), nullable=False, default=ExpectedInflowKind.EARNED.value, index=True)
    source_id = Column(Integer, ForeignKey("income_sources.id", ondelete="SET NULL"), nullable=True, index=True)
    debt_id = Column(Integer, ForeignKey("debts.id", ondelete="SET NULL"), nullable=True, index=True)
    asset_id = Column(Integer, ForeignKey("assets.id", ondelete="SET NULL"), nullable=True, index=True)
    refund_event_id = Column(Integer, ForeignKey("financial_events.id", ondelete="SET NULL"), nullable=True, index=True)
    parent_id = Column(Integer, ForeignKey("expected_incomes.id", ondelete="RESTRICT"), nullable=True, index=True)
    amount = Column(BigInteger, nullable=False)
    received_amount = Column(BigInteger, nullable=True, default=0)
    linked_transaction_id = Column(Integer, ForeignKey("financial_events.id", ondelete="SET NULL"), nullable=True, index=True)
    due_date = Column(Date, nullable=False)
    budget_year = Column(Integer, nullable=False)
    budget_month = Column(Integer, nullable=False)
    status = Column(Enum(ExpectedIncomeStatus), nullable=False, default=ExpectedIncomeStatus.EXPECTED)
    backing_eligible = Column(Boolean, nullable=False, default=True)
    close_reason = Column(String(32), nullable=True)
    closed_at = Column(DateTime(timezone=True), nullable=True)
    note = Column(String(200), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    owner = relationship("User", back_populates="expected_incomes")
    promise = relationship("ExpectedInflowPromise", back_populates="schedules")
    source = relationship("IncomeSource", back_populates="expected_incomes")
    debt = relationship("Debt", back_populates="expected_incomes")
    asset = relationship("Asset", foreign_keys=[asset_id])
    refund_event = relationship("FinancialEvent", foreign_keys=[refund_event_id])
    linked_transaction = relationship("FinancialEvent", foreign_keys=[linked_transaction_id])
    parent = relationship("ExpectedIncome", remote_side=[id], back_populates="children", foreign_keys=[parent_id])
    children = relationship("ExpectedIncome", back_populates="parent", foreign_keys=[parent_id], passive_deletes=True)
    realization_allocations = relationship(
        "ExpectedInflowRealizationAllocation",
        back_populates="expected_inflow",
        passive_deletes=True,
    )
    write_offs = relationship(
        "ExpectedInflowWriteOff",
        back_populates="schedule",
        passive_deletes=True,
    )


class ExpectedInflowRealization(Base):
    __tablename__ = "expected_inflow_realizations"
    __table_args__ = (
        CheckConstraint("actual_amount > 0", name="ck_expected_inflow_realizations_amount_positive"),
        UniqueConstraint("owner_id", "idempotency_key", name="uq_expected_inflow_realizations_owner_idempotency"),
        Index("ix_expected_inflow_realizations_owner_date", "owner_id", "received_date"),
    )

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    promise_id = Column(
        Integer,
        ForeignKey("expected_inflow_promises.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    actual_amount = Column(BigInteger, nullable=False)
    received_date = Column(Date, nullable=False)
    note = Column(String(200), nullable=True)
    idempotency_key = Column(String(64), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    owner = relationship("User", back_populates="expected_inflow_realizations")
    promise = relationship("ExpectedInflowPromise", back_populates="realizations")
    allocations = relationship(
        "ExpectedInflowRealizationAllocation",
        back_populates="realization",
        cascade="all, delete-orphan",
    )
    event_links = relationship(
        "ExpectedInflowRealizationEvent",
        back_populates="realization",
        cascade="all, delete-orphan",
    )


class ExpectedInflowRealizationAllocation(Base):
    __tablename__ = "expected_inflow_realization_allocations"
    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_expected_inflow_realization_allocations_amount_positive"),
        UniqueConstraint(
            "realization_id",
            "expected_inflow_id",
            name="uq_expected_inflow_realization_allocation",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    realization_id = Column(
        Integer,
        ForeignKey("expected_inflow_realizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    expected_inflow_id = Column(
        Integer,
        ForeignKey("expected_incomes.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    amount = Column(BigInteger, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    realization = relationship("ExpectedInflowRealization", back_populates="allocations")
    expected_inflow = relationship("ExpectedIncome", back_populates="realization_allocations")


class ExpectedInflowRealizationEvent(Base):
    __tablename__ = "expected_inflow_realization_events"
    __table_args__ = (
        UniqueConstraint(
            "realization_id",
            "financial_event_id",
            name="uq_expected_inflow_realization_event",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    realization_id = Column(
        Integer,
        ForeignKey("expected_inflow_realizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    financial_event_id = Column(
        Integer,
        ForeignKey("financial_events.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    realization = relationship("ExpectedInflowRealization", back_populates="event_links")
    financial_event = relationship("FinancialEvent")


class ExpectedInflowWriteOff(Base):
    __tablename__ = "expected_inflow_write_offs"
    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_expected_inflow_write_offs_amount_positive"),
        CheckConstraint("amount <= 999999999999", name="ck_expected_inflow_write_offs_amount_limit"),
        Index("ix_expected_inflow_write_offs_promise_date", "promise_id", "written_off_date"),
    )

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    promise_id = Column(
        Integer,
        ForeignKey("expected_inflow_promises.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    schedule_id = Column(
        Integer,
        ForeignKey("expected_incomes.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    amount = Column(BigInteger, nullable=False)
    reason = Column(String(200), nullable=False)
    written_off_date = Column(Date, nullable=False)
    reversed_at = Column(DateTime(timezone=True), nullable=True)
    reversal_note = Column(String(200), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    promise = relationship("ExpectedInflowPromise", back_populates="write_offs")
    schedule = relationship("ExpectedIncome", back_populates="write_offs")


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
    owner_id = Column(Integer, ForeignKey(
        "users.id", ondelete="CASCADE"), nullable=False, index=True)
    owner = relationship("User", back_populates="recurring_expenses")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # ── Wallet Integration ────────────────────────────────────────────
    # Which wallet the scheduler should charge. NULL = fall back to default wallet.
    wallet_id = Column(Integer, ForeignKey(
        "wallets.id", ondelete="SET NULL"), nullable=True, index=True)
    wallet = relationship("Wallet")
    archived_at = Column(DateTime(timezone=True), nullable=True, index=True)
    paused_at = Column(DateTime(timezone=True), nullable=True)

    # ── State Machine ─────────────────────────────────────────────────
    status = Column(Enum(RecurringStatus), nullable=False, default=RecurringStatus.ACTIVE)

    # ── Cycle Behavior ────────────────────────────────────────────────
    cycle_behavior = Column(Enum(CycleBehavior), nullable=False, default=CycleBehavior.FIXED)

    # ── Date Anchoring ────────────────────────────────────────────────
    original_due_day = Column(Integer, nullable=True)

    custom_projection_horizons = Column(JSON, nullable=True)

    
    # Relationships
    events = relationship("RecurringEvent", back_populates="recurring_expense", cascade="all, delete-orphan")
    occurrences = relationship(
        "RecurringOccurrence",
        back_populates="template",
        cascade="all, delete-orphan",
        order_by="RecurringOccurrence.scheduled_due_date",
    )


class RecurringOccurrence(Base):
    __tablename__ = "recurring_occurrences"
    __table_args__ = (
        CheckConstraint("expected_amount > 0", name="ck_recurring_occurrences_expected_amount_positive"),
        CheckConstraint(
            "actual_amount IS NULL OR actual_amount > 0",
            name="ck_recurring_occurrences_actual_amount_positive",
        ),
        UniqueConstraint(
            "template_id",
            "scheduled_due_date",
            name="uq_recurring_occurrences_template_due_date",
        ),
        Index("ix_recurring_occurrences_owner_status", "owner_id", "status"),
        Index("ix_recurring_occurrences_owner_due_date", "owner_id", "scheduled_due_date"),
    )

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    template_id = Column(
        Integer,
        ForeignKey("recurring_expenses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    scheduled_due_date = Column(Date, nullable=False, index=True)
    expected_title = Column(String(32), nullable=False)
    expected_amount = Column(BigInteger, nullable=False)
    expected_category = Column(Enum(ExpenseCategory), nullable=False)
    status = Column(
        Enum(RecurringOccurrenceStatus),
        nullable=False,
        default=RecurringOccurrenceStatus.PENDING_CONFIRMATION,
    )
    actual_amount = Column(BigInteger, nullable=True)
    actual_date = Column(Date, nullable=True)
    linked_financial_event_id = Column(
        Integer,
        ForeignKey("financial_events.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    initial_notified_at = Column(DateTime(timezone=True), nullable=True)
    remind_at = Column(DateTime(timezone=True), nullable=True)
    failure_code = Column(String(100), nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    owner = relationship("User", back_populates="recurring_occurrences")
    template = relationship("RecurringExpense", back_populates="occurrences")
    linked_financial_event = relationship("FinancialEvent")


class Budget(Base):
    __tablename__ = "budgets"

    id = Column(Integer, primary_key=True, index=True)
    category = Column(Enum(ExpenseCategory), nullable=False)
    monthly_limit = Column(BigInteger, nullable=False)

    budget_year = Column(Integer, nullable=False)
    budget_month = Column(Integer, nullable=False)
    auto_created = Column(Boolean, default=False, nullable=False)

    owner_id = Column(Integer, ForeignKey(
        "users.id", ondelete="CASCADE"), nullable=False)
    owner = relationship("User", back_populates="budgets")
    entity_ledger_entries = relationship("EntityLedger", back_populates="budget")
    subcategory_limits = relationship(
        "BudgetSubcategoryLimit", back_populates="budget", cascade="all, delete-orphan")
    last_notified_threshold = Column(Integer, default=0, nullable=False)

    max_envelope_balance = Column(BigInteger, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    __table_args__ = (
        UniqueConstraint("owner_id", "category", "budget_year",
                         "budget_month", name="uq_budgets_owner_category_year_month"),
        CheckConstraint("budget_month >= 1 AND budget_month <= 12",
                        name="ck_budgets_budget_month_1_12"),
        CheckConstraint("budget_year >= 2020", name="ck_budgets_budget_year_min_2020"),
        CheckConstraint("monthly_limit <= 999999999999", name="ck_budgets_monthly_limit"),
        Index("ix_budgets_owner_year_month", "owner_id", "budget_year", "budget_month")
    )


class BorrowingSurvivalPlan(Base):
    __tablename__ = "borrowing_survival_plans"
    __table_args__ = (
        UniqueConstraint(
            "owner_id",
            "budget_year",
            "budget_month",
            name="uq_borrowing_survival_owner_month",
        ),
        CheckConstraint(
            "budget_month >= 1 AND budget_month <= 12",
            name="ck_borrowing_survival_month",
        ),
        CheckConstraint(
            "budget_year >= 2020",
            name="ck_borrowing_survival_year",
        ),
        CheckConstraint(
            "monthly_cap >= 0 AND monthly_cap <= 999999999999",
            name="ck_borrowing_survival_cap",
        ),
        Index(
            "ix_borrowing_survival_owner_month",
            "owner_id",
            "budget_year",
            "budget_month",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    budget_year = Column(Integer, nullable=False)
    budget_month = Column(Integer, nullable=False)
    enabled = Column(Boolean, nullable=False, default=False, server_default="false")
    monthly_cap = Column(BigInteger, nullable=False, default=0, server_default="0")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    owner = relationship("User", back_populates="borrowing_survival_plans")


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
        CheckConstraint(
            "amount <= 999999999999", name="ck_savings_transactions_amount_limit"),
        Index("ix_savings_transactions_owner_created_at",
              "owner_id", "created_at"),
    )

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey(
        "users.id", ondelete="CASCADE"), nullable=False, index=True)
    wallet_id = Column(Integer, ForeignKey("wallets.id", ondelete="SET NULL"), nullable=True, index=True)
    wallet = relationship("Wallet")
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
        CheckConstraint("target_amount <= 999999999999",
                        name="ck_goals_target_amount_limit"),
        Index("ix_goals_owner_status", "owner_id", "status"),
    )

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey(
        "users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(32), nullable=False)
    target_amount = Column(BigInteger, nullable=False)
    currency = Column(String(3), default="UZS", server_default="UZS", nullable=False)
    intent = Column(
        Enum(GoalIntent),
        nullable=False,
        default=GoalIntent.RESERVE,
        server_default=GoalIntent.RESERVE.value,
    )
    template = Column(String(50), nullable=True)
    target_date = Column(Date, nullable=True)
    status = Column(Enum(GoalStatus), nullable=False,
                    default=GoalStatus.ACTIVE)
    completion_mode = Column(Enum(GoalCompletionMode), nullable=True)
    debt_goal_tracking_mode = Column(Enum(DebtGoalTrackingMode), nullable=True)
    linked_asset_id = Column(Integer, ForeignKey("assets.id", ondelete="SET NULL"), nullable=True, index=True)
    linked_debt_id = Column(Integer, ForeignKey("debts.id", ondelete="SET NULL"), nullable=True, index=True)
    linked_debt_transaction_id = Column(Integer, ForeignKey("debt_transactions.id", ondelete="SET NULL"), nullable=True, index=True)
    linked_payment_plan_id = Column(Integer, ForeignKey("payment_plans.id", ondelete="SET NULL"), nullable=True, index=True)
    linked_expense_event_id = Column(Integer, ForeignKey("financial_events.id", ondelete="SET NULL"), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True),
                        server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(
    ), onupdate=func.now(), nullable=False)

    owner = relationship("User", back_populates="goals")
    contributions = relationship(
        "GoalContributions", back_populates="goal", cascade="all, delete")
    project_releases = relationship(
        "GoalProjectRelease", back_populates="goal", cascade="all, delete-orphan")
    linked_asset = relationship("Asset", foreign_keys=[linked_asset_id])
    linked_debt = relationship("Debt", foreign_keys=[linked_debt_id])
    linked_debt_transaction = relationship("DebtTransaction", foreign_keys=[linked_debt_transaction_id])
    linked_payment_plan = relationship("PaymentPlan", foreign_keys=[linked_payment_plan_id])
    linked_expense_event = relationship("FinancialEvent", foreign_keys=[linked_expense_event_id])


Index(
    "ux_goals_one_active_pay_obligation_per_debt",
    Goals.owner_id,
    Goals.linked_debt_id,
    unique=True,
    postgresql_where=(
        (Goals.intent == GoalIntent.PAY_OBLIGATION)
        & (Goals.status == GoalStatus.ACTIVE)
        & (Goals.linked_debt_id.isnot(None))
    ),
    sqlite_where=(
        (Goals.intent == GoalIntent.PAY_OBLIGATION)
        & (Goals.status == GoalStatus.ACTIVE)
        & (Goals.linked_debt_id.isnot(None))
    ),
)


class GoalContributions(Base):
    __tablename__ = "goal_contributions"
    __table_args__ = (
        CheckConstraint(
            "amount > 0", name="ck_goal_contributions_amount_positive"),
        Index("ix_goal_contributions_owner_created_at",
              "owner_id", "created_at"),
        Index("ix_goal_contributions_goal_created_at", "goal_id", "created_at"),
        Index("ix_goal_contributions_wallet_created_at", "wallet_id", "created_at"),
    )

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey(
        "users.id", ondelete="CASCADE"), nullable=False, index=True)
    goal_id = Column(Integer, ForeignKey(
        "goals.id", ondelete="CASCADE"), nullable=False, index=True)
    wallet_id = Column(Integer, ForeignKey("wallets.id", ondelete="RESTRICT"), nullable=False, index=True)
    linked_event_id = Column(Integer, ForeignKey("financial_events.id", ondelete="SET NULL"), nullable=True, index=True)
    amount = Column(BigInteger, nullable=False)
    contribution_type = Column(Enum(GoalContributionType), nullable=False)
    created_at = Column(DateTime(timezone=True),
                        server_default=func.now(), nullable=False)

    owner = relationship("User", back_populates="goal_contributions")
    goal = relationship("Goals", back_populates="contributions")
    wallet = relationship("Wallet", back_populates="goal_contributions")
    linked_event = relationship("FinancialEvent")


class GoalProjectRelease(Base):
    __tablename__ = "goal_project_releases"
    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_goal_project_releases_amount_positive"),
        Index("ix_goal_project_releases_goal_created_at", "goal_id", "created_at"),
        Index("ix_goal_project_releases_project_created_at", "project_id", "created_at"),
    )

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    goal_id = Column(Integer, ForeignKey("goals.id", ondelete="CASCADE"), nullable=False, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    wallet_id = Column(Integer, ForeignKey("wallets.id", ondelete="RESTRICT"), nullable=True, index=True)
    amount = Column(BigInteger, nullable=False)
    released_at = Column(Date, nullable=False, default=date.today)
    note = Column(String(500), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    owner = relationship("User", back_populates="goal_project_releases")
    goal = relationship("Goals", back_populates="project_releases")
    project = relationship("Project")
    wallet = relationship("Wallet")


class Debt(Base):
    __tablename__ = "debts"
    __table_args__ = (
        CheckConstraint("initial_amount > 0", name="ck_debts_initial_amount_positive"),
        CheckConstraint("remaining_amount >= 0", name="ck_debts_remaining_amount_non_negative"),
        CheckConstraint("date >= '2020-01-01'", name="ck_debts_date_min_2020_01_01"),
        CheckConstraint("expected_return_date >= '2020-01-01'", name="ck_debts_expected_return_date_min_2020_01_01"),
        CheckConstraint("expected_return_date >= date", name="ck_debts_expected_return_date_not_before_date"),
        Index("ix_debts_owner_status", "owner_id", "status"),
        Index("ix_debts_owner_type", "owner_id", "debt_type"),
        Index("ix_debts_owner_origin", "owner_id", "origin_kind"),
        Index("ix_debts_owner_product", "owner_id", "product_kind"),
        Index("ix_debts_owner_archived_at", "owner_id", "archived_at"),
    )

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    debt_type = Column(Enum(DebtType), nullable=False)
    origin_kind = Column(
        Enum(DebtOriginKind),
        nullable=False,
        default=DebtOriginKind.IMPORTED_BALANCE,
        server_default=DebtOriginKind.IMPORTED_BALANCE.value,
    )
    counterparty_kind = Column(
        Enum(DebtCounterpartyKind),
        nullable=False,
        default=DebtCounterpartyKind.OTHER,
        server_default=DebtCounterpartyKind.OTHER.value,
    )
    product_kind = Column(Enum(DebtProductKind), nullable=True)
    counterparty_name = Column(String(100), nullable=False)
    initial_amount = Column(BigInteger, nullable=False)
    remaining_amount = Column(BigInteger, nullable=False)
    currency = Column(String(3), default="UZS", nullable=False)
    description = Column(String, nullable=True)
    status = Column(Enum(DebtStatus), nullable=False, default=DebtStatus.ACTIVE)
    archived_at = Column(DateTime(timezone=True), nullable=True)
    date = Column(Date, nullable=False)
    expected_return_date = Column(Date, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    owner = relationship("User", back_populates="debts")
    # Relationships
    transactions = relationship("DebtTransaction", back_populates="debt", cascade="all, delete-orphan")
    charges = relationship("DebtCharge", back_populates="debt", cascade="all, delete-orphan")
    ledger_entries = relationship("DebtLedgerEntry", back_populates="debt", cascade="all, delete-orphan")
    formal_details = relationship("DebtFormalDetails", back_populates="debt", uselist=False, cascade="all, delete-orphan")
    transaction_wallet_allocations = relationship("DebtTransactionWalletAllocation", back_populates="debt", cascade="all, delete-orphan")
    asset_settlements = relationship("DebtAssetSettlement", back_populates="debt", cascade="all, delete-orphan")
    payment_plan = relationship("PaymentPlan", back_populates="debt", uselist=False)
    expected_incomes = relationship("ExpectedIncome", back_populates="debt")

    # New fields for real-world money flow
    is_money_transferred = Column(Boolean, default=False, nullable=False)
    initial_wallet_id = Column(Integer, ForeignKey("wallets.id", ondelete="SET NULL"), nullable=True)
    linked_event_id = Column(Integer, ForeignKey("financial_events.id", ondelete="SET NULL"), nullable=True)
    
    # Pre-tags for Cash-Basis Accounting
    expense_category = Column(Enum(ExpenseCategory), nullable=True)
    expense_subcategory_id = Column(Integer, ForeignKey("user_subcategories.id", ondelete="SET NULL"), nullable=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="SET NULL", use_alter=True, name="fk_debts_project_id"), nullable=True)
    project_subcategory_id = Column(Integer, ForeignKey("legacy_project_subcategories.id", ondelete="SET NULL", use_alter=True, name="fk_debts_project_subcategory_id"), nullable=True)
    income_source_id = Column(Integer, ForeignKey("income_sources.id", ondelete="SET NULL"), nullable=True)

    expense_subcategory = relationship("UserSubcategory")
    project = relationship("Project")
    project_subcategory = relationship("LegacyProjectSubcategory")



class DebtTransaction(Base):
    __tablename__ = "debt_transactions"
    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_debt_transactions_amount_positive"),
    )

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    wallet_id = Column(Integer, ForeignKey("wallets.id", ondelete="SET NULL"), nullable=True, index=True)
    wallet = relationship("Wallet")
    debt_id = Column(Integer, ForeignKey("debts.id", ondelete="CASCADE"), nullable=False, index=True)
    amount = Column(BigInteger, nullable=False)
    date = Column(Date, nullable=False)
    note = Column(String(200), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    owner = relationship("User", back_populates="debt_transactions")
    debt = relationship("Debt", back_populates="transactions")
    wallet_allocations = relationship("DebtTransactionWalletAllocation", back_populates="transaction", cascade="all, delete-orphan")


class DebtTransactionWalletAllocation(Base):
    __tablename__ = "debt_transaction_wallet_allocations"
    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_debt_transaction_wallet_allocations_amount_positive"),
        UniqueConstraint("debt_transaction_id", "wallet_id", name="uq_debt_transaction_wallet_allocations_wallet"),
    )

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    debt_id = Column(Integer, ForeignKey("debts.id", ondelete="CASCADE"), nullable=False, index=True)
    debt_transaction_id = Column(Integer, ForeignKey("debt_transactions.id", ondelete="CASCADE"), nullable=False, index=True)
    wallet_id = Column(Integer, ForeignKey("wallets.id", ondelete="RESTRICT"), nullable=False, index=True)
    amount = Column(BigInteger, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    owner = relationship("User", back_populates="debt_transaction_wallet_allocations")
    debt = relationship("Debt", back_populates="transaction_wallet_allocations")
    transaction = relationship("DebtTransaction", back_populates="wallet_allocations")
    wallet = relationship("Wallet")


class DebtCharge(Base):
    """Tracks interest, penalties, or additional charges added to a debt.
    These do NOT involve wallet transactions — they only increase the obligation."""
    __tablename__ = "debt_charges"
    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_debt_charges_amount_positive"),
        CheckConstraint("amount <= 999999999999", name="ck_debt_charges_amount_limit"),
        Index("ix_debt_charges_debt_id", "debt_id"),
    )

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    debt_id = Column(Integer, ForeignKey("debts.id", ondelete="CASCADE"), nullable=False)
    amount = Column(BigInteger, nullable=False)
    reason = Column(String(200), nullable=True)
    date = Column(Date, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    owner = relationship("User", back_populates="debt_charges")
    debt = relationship("Debt", back_populates="charges")


class DebtLedgerEntry(Base):
    __tablename__ = "debt_ledger_entries"
    __table_args__ = (
        CheckConstraint("amount_delta != 0", name="ck_debt_ledger_amount_delta_non_zero"),
        Index("ix_debt_ledger_owner_date", "owner_id", "entry_date"),
        Index("ix_debt_ledger_debt_date", "debt_id", "entry_date"),
        Index("ix_debt_ledger_financial_event_id", "financial_event_id"),
        Index("ix_debt_ledger_source_transaction_id", "source_debt_transaction_id"),
        Index("ix_debt_ledger_source_charge_id", "source_debt_charge_id"),
    )

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    debt_id = Column(Integer, ForeignKey("debts.id", ondelete="CASCADE"), nullable=False, index=True)
    financial_event_id = Column(Integer, ForeignKey("financial_events.id", ondelete="SET NULL"), nullable=True, index=True)
    source_debt_transaction_id = Column(Integer, ForeignKey("debt_transactions.id", ondelete="SET NULL"), nullable=True, index=True)
    source_debt_charge_id = Column(Integer, ForeignKey("debt_charges.id", ondelete="SET NULL"), nullable=True, index=True)
    reverses_entry_id = Column(Integer, ForeignKey("debt_ledger_entries.id", ondelete="SET NULL"), nullable=True, index=True)
    wallet_id = Column(Integer, ForeignKey("wallets.id", ondelete="SET NULL"), nullable=True, index=True)
    asset_id = Column(Integer, ForeignKey("assets.id", ondelete="SET NULL"), nullable=True, index=True)
    entry_type = Column(Enum(DebtLedgerEntryType), nullable=False)
    amount_delta = Column(BigInteger, nullable=False)
    principal_delta = Column(BigInteger, nullable=False, default=0, server_default="0")
    charge_delta = Column(BigInteger, nullable=False, default=0, server_default="0")
    balance_after = Column(BigInteger, nullable=True)
    event_subtype = Column(String(50), nullable=True)
    source = Column(
        Enum(DebtLedgerEntrySource),
        nullable=False,
        default=DebtLedgerEntrySource.USER,
        server_default=DebtLedgerEntrySource.USER.value,
    )
    is_reversible = Column(Boolean, nullable=False, default=True, server_default="true")
    status = Column(String(20), nullable=False, default="POSTED", server_default="POSTED")
    entry_date = Column(Date, nullable=False)
    note = Column(String(500), nullable=True)
    extra_data = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    owner = relationship("User", back_populates="debt_ledger_entries")
    debt = relationship("Debt", back_populates="ledger_entries")
    financial_event = relationship("FinancialEvent")
    source_debt_transaction = relationship("DebtTransaction")
    source_debt_charge = relationship("DebtCharge")
    reverses_entry = relationship("DebtLedgerEntry", remote_side=[id])
    wallet = relationship("Wallet")
    asset = relationship("Asset")


class DebtFormalDetails(Base):
    __tablename__ = "debt_formal_details"
    __table_args__ = (
        CheckConstraint("statement_balance IS NULL OR statement_balance >= 0", name="ck_debt_formal_statement_balance_non_negative"),
        CheckConstraint("annual_rate_bps IS NULL OR annual_rate_bps >= 0", name="ck_debt_formal_annual_rate_bps_non_negative"),
    )

    debt_id = Column(Integer, ForeignKey("debts.id", ondelete="CASCADE"), primary_key=True)
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    institution_name = Column(String(100), nullable=True)
    contract_number = Column(String(100), nullable=True)
    linked_asset_id = Column(Integer, ForeignKey("assets.id", ondelete="SET NULL"), nullable=True, index=True)
    collateral_asset_id = Column(Integer, ForeignKey("assets.id", ondelete="SET NULL"), nullable=True, index=True)
    statement_balance = Column(BigInteger, nullable=True)
    statement_balance_date = Column(Date, nullable=True)
    next_due_date = Column(Date, nullable=True)
    annual_rate_bps = Column(Integer, nullable=True)
    terms_summary = Column(String(500), nullable=True)
    extra_data = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    owner = relationship("User", back_populates="debt_formal_details")
    debt = relationship("Debt", back_populates="formal_details")
    linked_asset = relationship("Asset", foreign_keys=[linked_asset_id])
    collateral_asset = relationship("Asset", foreign_keys=[collateral_asset_id])


class DebtAssetSettlement(Base):
    __tablename__ = "debt_asset_settlements"
    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_debt_asset_settlements_amount_positive"),
        Index("ix_debt_asset_settlements_debt_date", "debt_id", "settlement_date"),
    )

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    debt_id = Column(Integer, ForeignKey("debts.id", ondelete="CASCADE"), nullable=False, index=True)
    asset_id = Column(Integer, ForeignKey("assets.id", ondelete="SET NULL"), nullable=True, index=True)
    financial_event_id = Column(Integer, ForeignKey("financial_events.id", ondelete="SET NULL"), nullable=True, index=True)
    debt_ledger_entry_id = Column(Integer, ForeignKey("debt_ledger_entries.id", ondelete="SET NULL"), nullable=True, index=True)
    settlement_type = Column(Enum(DebtAssetSettlementType), nullable=False)
    amount = Column(BigInteger, nullable=False)
    settlement_date = Column(Date, nullable=False)
    note = Column(String(500), nullable=True)
    extra_data = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    owner = relationship("User", back_populates="debt_asset_settlements")
    debt = relationship("Debt", back_populates="asset_settlements")
    asset = relationship("Asset")
    financial_event = relationship("FinancialEvent")
    debt_ledger_entry = relationship("DebtLedgerEntry")


class PaymentPlanTransaction(Base):
    __tablename__ = "payment_plan_transactions"
    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_payment_plan_transactions_amount_positive"),
    )

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    plan_id = Column(Integer, ForeignKey("payment_plans.id", ondelete="CASCADE"), nullable=False, index=True)
    amount = Column(BigInteger, nullable=False)
    date = Column(Date, nullable=False)
    note = Column(String(200), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    owner = relationship("User", back_populates="payment_plan_transactions")
    plan = relationship("PaymentPlan", back_populates="transactions")
    wallet_allocations = relationship("PaymentPlanTransactionWalletAllocation", back_populates="transaction", cascade="all, delete-orphan")


class PaymentPlanTransactionWalletAllocation(Base):
    __tablename__ = "payment_plan_transaction_wallet_allocations"
    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_payment_plan_txn_wallet_allocations_amount_positive"),
        UniqueConstraint("payment_plan_transaction_id", "wallet_id", name="uq_payment_plan_txn_wallet_allocations_wallet"),
    )

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    plan_id = Column(Integer, ForeignKey("payment_plans.id", ondelete="CASCADE"), nullable=False, index=True)
    payment_plan_transaction_id = Column(Integer, ForeignKey("payment_plan_transactions.id", ondelete="CASCADE"), nullable=False, index=True)
    wallet_id = Column(Integer, ForeignKey("wallets.id", ondelete="RESTRICT"), nullable=False, index=True)
    amount = Column(BigInteger, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    owner = relationship("User", back_populates="payment_plan_transaction_wallet_allocations")
    plan = relationship("PaymentPlan", back_populates="transaction_wallet_allocations")
    transaction = relationship("PaymentPlanTransaction", back_populates="wallet_allocations")
    wallet = relationship("Wallet")


class PaymentPlanCharge(Base):
    __tablename__ = "payment_plan_charges"
    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_payment_plan_charges_amount_positive"),
        Index("ix_payment_plan_charges_plan_id", "plan_id"),
    )

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    plan_id = Column(Integer, ForeignKey("payment_plans.id", ondelete="CASCADE"), nullable=False)
    amount = Column(BigInteger, nullable=False)
    reason = Column(String(200), nullable=True)
    date = Column(Date, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    owner = relationship("User", back_populates="payment_plan_charges")
    plan = relationship("PaymentPlan", back_populates="charges")


class PaymentPlanLedgerEntry(Base):
    __tablename__ = "payment_plan_ledger_entries"
    __table_args__ = (
        CheckConstraint("amount_delta != 0", name="ck_payment_plan_ledger_amount_delta_non_zero"),
        Index("ix_payment_plan_ledger_owner_date", "owner_id", "entry_date"),
        Index("ix_payment_plan_ledger_plan_date", "plan_id", "entry_date"),
    )

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    plan_id = Column(Integer, ForeignKey("payment_plans.id", ondelete="CASCADE"), nullable=False, index=True)
    financial_event_id = Column(Integer, ForeignKey("financial_events.id", ondelete="SET NULL"), nullable=True, index=True)
    source_transaction_id = Column(Integer, ForeignKey("payment_plan_transactions.id", ondelete="SET NULL"), nullable=True, index=True)
    source_charge_id = Column(Integer, ForeignKey("payment_plan_charges.id", ondelete="SET NULL"), nullable=True, index=True)
    reverses_entry_id = Column(Integer, ForeignKey("payment_plan_ledger_entries.id", ondelete="SET NULL"), nullable=True, index=True)
    entry_type = Column(Enum(PaymentPlanLedgerEntryType), nullable=False)
    amount_delta = Column(BigInteger, nullable=False)
    principal_delta = Column(BigInteger, nullable=False, default=0, server_default="0")
    charge_delta = Column(BigInteger, nullable=False, default=0, server_default="0")
    balance_after = Column(BigInteger, nullable=True)
    event_subtype = Column(String(50), nullable=True)
    source = Column(
        Enum(PaymentPlanLedgerEntrySource),
        nullable=False,
        default=PaymentPlanLedgerEntrySource.USER,
        server_default=PaymentPlanLedgerEntrySource.USER.value,
    )
    is_reversible = Column(Boolean, nullable=False, default=True, server_default="true")
    status = Column(String(20), nullable=False, default="POSTED", server_default="POSTED")
    entry_date = Column(Date, nullable=False)
    note = Column(String(500), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    owner = relationship("User", back_populates="payment_plan_ledger_entries")
    plan = relationship("PaymentPlan", back_populates="ledger_entries")
    financial_event = relationship("FinancialEvent")
    source_transaction = relationship("PaymentPlanTransaction")
    source_charge = relationship("PaymentPlanCharge")
    reverses_entry = relationship("PaymentPlanLedgerEntry", remote_side=[id])


class PaymentPlan(Base):
    __tablename__ = "payment_plans"
    __table_args__ = (
        CheckConstraint("total_price > 0", name="ck_payment_plans_total_price_positive"),
        CheckConstraint("down_payment >= 0", name="ck_payment_plans_down_payment_non_negative"),
        CheckConstraint("remaining_amount >= 0", name="ck_payment_plans_remaining_amount_non_negative"),
        CheckConstraint("months > 0", name="ck_payment_plans_months_positive"),
        CheckConstraint("payment_count > 0", name="ck_payment_plans_payment_count_positive"),
        CheckConstraint("regular_payment_amount >= 0", name="ck_payment_plans_regular_payment_amount_non_negative"),
        CheckConstraint("start_date >= '2020-01-01'", name="ck_payment_plans_start_date_min_2020_01_01"),
        Index("ix_payment_plans_owner_status", "owner_id", "status"),
        Index("ix_payment_plans_owner_plan_type", "owner_id", "plan_type"),
        Index("uq_payment_plans_debt_id", "debt_id", unique=True),
    )

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    debt_id = Column(Integer, ForeignKey("debts.id", ondelete="SET NULL", use_alter=True, name="fk_payment_plans_debt_id"), nullable=True)
    item_name = Column(String(100), nullable=False)
    store_or_bank_name = Column(String(100), nullable=True)
    plan_type = Column(
        Enum(PaymentPlanType),
        nullable=False,
        default=PaymentPlanType.STORE_INSTALLMENT,
        server_default=PaymentPlanType.STORE_INSTALLMENT.value,
    )
    total_price = Column(BigInteger, nullable=False)
    down_payment = Column(BigInteger, nullable=False, default=0)
    remaining_amount = Column(BigInteger, nullable=False)
    currency = Column(String(3), default="UZS", nullable=False)
    months = Column(Integer, nullable=False)
    payment_count = Column(Integer, nullable=False)
    frequency = Column(Enum(PaymentPlanFrequency), nullable=False, default=PaymentPlanFrequency.MONTHLY)
    monthly_payment_amount = Column(BigInteger, nullable=False)
    regular_payment_amount = Column(BigInteger, nullable=False)
    schedule_rule = Column(JSON, nullable=True)
    status = Column(Enum(PaymentPlanStatus), nullable=False, default=PaymentPlanStatus.ACTIVE)
    start_date = Column(Date, nullable=False)
    expense_category = Column(Enum(ExpenseCategory), nullable=True)
    expense_subcategory_id = Column(Integer, ForeignKey("user_subcategories.id", ondelete="SET NULL"), nullable=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="SET NULL", use_alter=True, name="fk_payment_plans_project_id"), nullable=True)
    project_subcategory_id = Column(Integer, ForeignKey("legacy_project_subcategories.id", ondelete="SET NULL", use_alter=True, name="fk_payment_plans_project_subcategory_id"), nullable=True)
    asset_id = Column(Integer, ForeignKey("assets.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    owner = relationship("User", back_populates="payment_plans")
    payments = relationship("PaymentPlanPayment", back_populates="plan", cascade="all, delete")
    transactions = relationship("PaymentPlanTransaction", back_populates="plan", cascade="all, delete")
    charges = relationship("PaymentPlanCharge", back_populates="plan", cascade="all, delete")
    ledger_entries = relationship("PaymentPlanLedgerEntry", back_populates="plan", cascade="all, delete")
    transaction_wallet_allocations = relationship("PaymentPlanTransactionWalletAllocation", back_populates="plan", cascade="all, delete-orphan")
    debt = relationship("Debt", back_populates="payment_plan")
    expense_subcategory = relationship("UserSubcategory")
    project = relationship("Project")
    project_subcategory = relationship("LegacyProjectSubcategory")
    asset = relationship("Asset")


class PaymentPlanPayment(Base):
    __tablename__ = "payment_plan_payments"
    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_payment_plan_payments_amount_positive"),
        CheckConstraint("paid_amount >= 0", name="ck_payment_plan_payments_paid_amount_non_negative"),
        CheckConstraint("written_off_amount >= 0", name="ck_payment_plan_payments_written_off_amount_non_negative"),
        CheckConstraint("paid_amount <= amount", name="ck_payment_plan_payments_paid_amount_not_above_amount"),
        CheckConstraint(
            "paid_amount + written_off_amount <= amount",
            name="ck_payment_plan_payments_settled_amount_not_above_amount",
        ),
        CheckConstraint("due_date >= '2020-01-01'", name="ck_payment_plan_payments_due_date_min_2020_01_01"),
        Index("ix_payment_plan_payments_plan_due_date", "plan_id", "due_date"),
        Index("ix_payment_plan_payments_owner_due_date", "owner_id", "due_date"),
    )
    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    plan_id = Column(Integer, ForeignKey("payment_plans.id", ondelete="CASCADE"), nullable=False, index=True)
    payment_plan_charge_id = Column(Integer, ForeignKey("payment_plan_charges.id", ondelete="SET NULL"), nullable=True, index=True)
    amount = Column(BigInteger, nullable=False)
    paid_amount = Column(BigInteger, nullable=False, default=0, server_default="0")
    written_off_amount = Column(BigInteger, nullable=False, default=0, server_default="0")
    component_type = Column(
        Enum(PaymentPlanPaymentComponentType),
        nullable=False,
        default=PaymentPlanPaymentComponentType.PRINCIPAL,
        server_default=PaymentPlanPaymentComponentType.PRINCIPAL.value,
    )
    status = Column(Enum(PaymentPlanPaymentStatus), nullable=False, default=PaymentPlanPaymentStatus.PENDING)
    due_date = Column(Date, nullable=False)
    paid_date = Column(Date, nullable=True)
    note = Column(String(200), nullable=True)
    event_id = Column(Integer, ForeignKey("financial_events.id", ondelete="SET NULL"), nullable=True, index=True)
    payment_plan_ledger_entry_id = Column(Integer, ForeignKey("payment_plan_ledger_entries.id", ondelete="SET NULL"), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    owner = relationship("User", back_populates="payment_plan_payments")
    plan = relationship("PaymentPlan", back_populates="payments")
    charge = relationship("PaymentPlanCharge")
    event = relationship("FinancialEvent")
    ledger_entry = relationship("PaymentPlanLedgerEntry")
    allocations = relationship("PaymentPlanPaymentAllocation", back_populates="payment", cascade="all, delete-orphan")


class PaymentPlanPaymentAllocation(Base):
    __tablename__ = "payment_plan_payment_allocations"
    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_payment_plan_payment_allocations_amount_positive"),
        Index("ix_payment_plan_payment_allocations_owner_date", "owner_id", "paid_date"),
    )

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    payment_plan_payment_id = Column(Integer, ForeignKey("payment_plan_payments.id", ondelete="CASCADE"), nullable=False, index=True)
    financial_event_id = Column(Integer, ForeignKey("financial_events.id", ondelete="SET NULL"), nullable=True, index=True)
    payment_plan_transaction_id = Column(Integer, ForeignKey("payment_plan_transactions.id", ondelete="SET NULL"), nullable=True, index=True)
    payment_plan_ledger_entry_id = Column(Integer, ForeignKey("payment_plan_ledger_entries.id", ondelete="SET NULL"), nullable=True, index=True)
    amount = Column(BigInteger, nullable=False)
    paid_date = Column(Date, nullable=False)
    note = Column(String(200), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    owner = relationship("User", back_populates="payment_plan_payment_allocations")
    payment = relationship("PaymentPlanPayment", back_populates="allocations")
    financial_event = relationship("FinancialEvent")
    transaction = relationship("PaymentPlanTransaction")
    ledger_entry = relationship("PaymentPlanLedgerEntry")


class PaymentStatus(str, enum.Enum):
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    REJECTED = "REJECTED"


class NotificationPriority(str, enum.Enum):
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class NotificationType(str, enum.Enum):
    BUDGET_WARNING = "budget_warning"
    BUDGET_EXCEEDED = "budget_exceeded"
    RECURRING_DUE = "recurring_due"
    RECURRING_FAILED = "recurring_failed"
    GOAL_MILESTONE = "goal_milestone"
    GOAL_COMPLETED = "goal_completed"
    DEBT_DUE_SOON = "debt_due_soon"
    DEBT_OVERDUE = "debt_overdue"
    DEBT_PAYMENT_PAID = "debt_payment_paid"
    DEBT_FULLY_PAID = "debt_fully_paid"
    SYSTEM = "system"


class Notification(Base):
    __tablename__ = "notifications"
    __table_args__ = (
        Index("ix_notifications_owner_id", "owner_id"),
        Index("ix_notifications_owner_is_read", "owner_id", "is_read"),
        Index("ix_notifications_owner_created_at", "owner_id", "created_at"),
    )

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey(
        "users.id", ondelete="CASCADE"), nullable=False)
    type = Column(String(50), nullable=False)
    title = Column(String(100), nullable=False)
    message = Column(String(500), nullable=False)
    is_read = Column(Boolean, default=False, nullable=False)
    priority = Column(String(20), nullable=False, default="info")
    extra_data = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True),
                        server_default=func.now(), nullable=False)

    owner = relationship("User", back_populates="notifications")


class PaymentTransaction(Base):
    __tablename__ = "payment_transactions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    order_code = Column(String(50), unique=True, index=True, nullable=False)
    plan_id = Column(String(50), nullable=False)
    amount = Column(Integer, nullable=False)
    currency = Column(String(10), default="UZS", nullable=False)
    status = Column(Enum(PaymentStatus), nullable=False, default=PaymentStatus.PENDING)
    telegram_user_id = Column(BigInteger, nullable=True, index=True)
    telegram_chat_id = Column(BigInteger, nullable=True, index=True)
    telegram_language_code = Column(String(10), nullable=True)

    telegram_receipt_message_id = Column(BigInteger, nullable=True)
    receipt_submitted_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    user = relationship("User", backref="payment_transactions")


class UserSubcategory(Base):
    __tablename__ = "user_subcategories"
    __table_args__ = (
        UniqueConstraint("owner_id", "category", "name", name="uq_user_subcats_owner_cat_name"),
        Index("ix_user_subcategories_owner_category", "owner_id", "category"),
    )

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    category = Column(Enum(ExpenseCategory), nullable=False)
    name = Column(String(50), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    is_deleted = Column(Boolean, default=False, nullable=False, server_default="false")

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    owner = relationship("User", back_populates="subcategories")
    monthly_limits = relationship(
        "BudgetSubcategoryLimit", back_populates="subcategory", cascade="all, delete-orphan")
    project_monthly_limits = relationship(
        "OverlayProjectSubcategoryReservation", back_populates="user_subcategory", cascade="all, delete-orphan")


class BudgetSubcategoryLimit(Base):
    __tablename__ = "budget_subcategory_limits"
    __table_args__ = (
        UniqueConstraint("budget_id", "subcategory_id", name="uq_budget_subcategory_limits_budget_subcategory"),
        CheckConstraint("monthly_limit > 0", name="ck_budget_subcategory_limits_monthly_limit_positive"),
        CheckConstraint("monthly_limit <= 999999999999", name="ck_budget_subcategory_limits_monthly_limit_max"),
        Index("ix_budget_subcategory_limits_budget", "budget_id"),
        Index("ix_budget_subcategory_limits_subcategory", "subcategory_id"),
    )

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    budget_id = Column(Integer, ForeignKey("budgets.id", ondelete="CASCADE"), nullable=False)
    subcategory_id = Column(Integer, ForeignKey("user_subcategories.id", ondelete="CASCADE"), nullable=False)
    monthly_limit = Column(BigInteger, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    owner = relationship("User", back_populates="budget_subcategory_limits")
    budget = relationship("Budget", back_populates="subcategory_limits")
    subcategory = relationship("UserSubcategory", back_populates="monthly_limits")


class BudgetLedger(Base):
    __tablename__ = "budget_ledger"
    __table_args__ = (
        UniqueConstraint("owner_id", "category", "budget_year", "budget_month", "entry_type", 
                         name="uq_budget_ledger_unique_entry"),
        Index("ix_budget_ledger_lookup", "owner_id", "category", "budget_year", "budget_month")
    )

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    category = Column(Enum(ExpenseCategory), nullable=False)
    budget_year = Column(Integer, nullable=False)
    budget_month = Column(Integer, nullable=False)
    
    amount = Column(BigInteger, nullable=False)
    entry_type = Column(String(20), nullable=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class Project(Base):
    __tablename__ = "projects"
    __table_args__ = (
        UniqueConstraint("origin_goal_id", name="uq_projects_origin_goal_id"),
    )
    
    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(100), nullable=False)
    description = Column(String(500), nullable=True)
    
    # Typology marker. Financial fields live in the type-specific detail tables.
    project_type = Column(Enum(ProjectType), nullable=False, default=ProjectType.OVERLAY)
    
    # Optional Graduation pipeline
    origin_goal_id = Column(Integer, ForeignKey("goals.id", ondelete="SET NULL"), nullable=True)
    
    status = Column(Enum(ProjectStatus), nullable=False, default=ProjectStatus.ACTIVE)
    start_date = Column(Date, nullable=False, default=date.today)
    target_end_date = Column(Date, nullable=True)
    completed_at = Column(Date, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    owner = relationship("User", back_populates="projects")
    overlay_detail = relationship(
        "ProjectOverlayDetail",
        back_populates="project",
        uselist=False,
        cascade="all, delete-orphan",
    )
    isolated_detail = relationship(
        "ProjectIsolatedDetail",
        back_populates="project",
        uselist=False,
        cascade="all, delete-orphan",
    )
    isolated_category_allocations = relationship(
        "IsolatedProjectCategoryAllocation", back_populates="project", cascade="all, delete-orphan"
    )
    overlay_category_reservations = relationship(
        "OverlayProjectCategoryReservation", back_populates="project", cascade="all, delete-orphan"
    )
    legacy_subcategories = relationship("LegacyProjectSubcategory", back_populates="project", cascade="all, delete-orphan")
    overlay_subcategory_reservations = relationship(
        "OverlayProjectSubcategoryReservation", back_populates="project", cascade="all, delete-orphan"
    )
    goal_releases = relationship("GoalProjectRelease", back_populates="project", cascade="all, delete-orphan")
    isolated_wallet_allocations = relationship(
        "IsolatedProjectWalletAllocation",
        back_populates="project",
        cascade="all, delete-orphan",
    )
    session_draft_items = relationship("ExpenseSessionDraftItem", back_populates="project")


class ProjectOverlayDetail(Base):
    __tablename__ = "project_overlay_details"
    __table_args__ = (
        UniqueConstraint("project_id", name="uq_project_overlay_details_project_id"),
        CheckConstraint("target_estimate IS NULL OR target_estimate > 0", name="ck_project_overlay_details_target_estimate_positive"),
    )

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    target_estimate = Column(BigInteger, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    project = relationship("Project", back_populates="overlay_detail")
    owner = relationship("User")


class ProjectIsolatedDetail(Base):
    __tablename__ = "project_isolated_details"
    __table_args__ = (
        UniqueConstraint("project_id", name="uq_project_isolated_details_project_id"),
        CheckConstraint("funding_limit IS NULL OR funding_limit > 0", name="ck_project_isolated_details_funding_limit_positive"),
    )

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    funding_limit = Column(BigInteger, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    project = relationship("Project", back_populates="isolated_detail")
    owner = relationship("User")


class IsolatedProjectWalletAllocation(Base):
    __tablename__ = "isolated_project_wallet_allocations"
    __table_args__ = (
        UniqueConstraint("project_id", "wallet_id", name="uq_isolated_project_wallet_allocations_project_wallet"),
        CheckConstraint("amount > 0", name="ck_isolated_project_wallet_allocations_amount_positive"),
        CheckConstraint("amount <= 999999999999", name="ck_isolated_project_wallet_allocations_amount_max"),
        Index("ix_isolated_project_wallet_allocations_owner_wallet", "owner_id", "wallet_id"),
    )

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    wallet_id = Column(Integer, ForeignKey("wallets.id", ondelete="RESTRICT"), nullable=False, index=True)
    amount = Column(BigInteger, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    project = relationship("Project", back_populates="isolated_wallet_allocations")
    owner = relationship("User", back_populates="isolated_project_wallet_allocations")
    wallet = relationship("Wallet", back_populates="isolated_project_allocations")


class IsolatedProjectCategoryAllocation(Base):
    __tablename__ = "isolated_project_category_allocations"
    __table_args__ = (
        UniqueConstraint("project_id", "category", name="uq_isolated_project_category_allocations_project_category"),
    )

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    category = Column(Enum(ExpenseCategory), nullable=False)
    limit_amount = Column(BigInteger, nullable=False)
    
    project = relationship("Project", back_populates="isolated_category_allocations")


class OverlayProjectCategoryReservation(Base):
    __tablename__ = "overlay_project_category_reservations"
    __table_args__ = (
        UniqueConstraint(
            "project_id",
            "category",
            "budget_year",
            "budget_month",
            name="uq_overlay_project_category_reservations_project_category_month",
        ),
        CheckConstraint("budget_month >= 1 AND budget_month <= 12", name="ck_overlay_project_category_reservations_month"),
        CheckConstraint("budget_year >= 2020", name="ck_overlay_project_category_reservations_year"),
        CheckConstraint("limit_amount > 0", name="ck_overlay_project_category_reservations_amount_positive"),
        CheckConstraint("limit_amount <= 999999999999", name="ck_overlay_project_category_reservations_amount_max"),
        Index("ix_overlay_project_category_reservations_month", "budget_year", "budget_month", "category"),
    )

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    category = Column(Enum(ExpenseCategory), nullable=False)
    budget_year = Column(Integer, nullable=False)
    budget_month = Column(Integer, nullable=False)
    limit_amount = Column(BigInteger, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    project = relationship("Project", back_populates="overlay_category_reservations")


class LegacyProjectSubcategory(Base):
    """Legacy-only project-local subcategories kept for historical references.

    Forward isolated micro-subcategory work must use
    IsolatedProjectSubcategoryAllocation, which references user taxonomy.
    """

    __tablename__ = "legacy_project_subcategories"
    __table_args__ = (
        UniqueConstraint("project_id", "category", "name", name="uq_legacy_project_subcategories_project_category_name"),
        Index("ix_legacy_project_subcategories_project_category", "project_id", "category"),
    )

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    category = Column(Enum(ExpenseCategory), nullable=False)
    name = Column(String(50), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    limit_amount = Column(BigInteger, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    project = relationship("Project", back_populates="legacy_subcategories")


class IsolatedProjectSubcategoryAllocation(Base):
    __tablename__ = "isolated_project_subcategory_allocations"
    __table_args__ = (
        UniqueConstraint(
            "project_id",
            "user_subcategory_id",
            name="uq_isolated_project_subcategory_allocations_project_taxonomy",
        ),
        CheckConstraint("allocated_amount > 0", name="ck_isolated_project_subcategory_allocations_amount_positive"),
        CheckConstraint("allocated_amount <= 999999999999", name="ck_isolated_project_subcategory_allocations_amount_max"),
        Index("ix_isolated_project_subcategory_allocations_project_category", "project_id", "category"),
        Index("ix_isolated_project_subcategory_allocations_taxonomy", "user_subcategory_id"),
    )

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    category_allocation_id = Column(
        Integer,
        ForeignKey("isolated_project_category_allocations.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    category = Column(Enum(ExpenseCategory), nullable=False)
    user_subcategory_id = Column(Integer, ForeignKey("user_subcategories.id", ondelete="RESTRICT"), nullable=False)
    allocated_amount = Column(BigInteger, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    archived_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    project = relationship("Project")
    category_allocation = relationship("IsolatedProjectCategoryAllocation")
    user_subcategory = relationship("UserSubcategory")


class OverlayProjectSubcategoryReservation(Base):
    __tablename__ = "overlay_project_subcategory_reservations"
    __table_args__ = (
        UniqueConstraint(
            "project_id",
            "user_subcategory_id",
            "budget_year",
            "budget_month",
            name="uq_overlay_proj_subcat_res_project_subcat_month",
        ),
        CheckConstraint("budget_month >= 1 AND budget_month <= 12", name="ck_overlay_project_subcategory_reservations_month"),
        CheckConstraint("budget_year >= 2020", name="ck_overlay_project_subcategory_reservations_year"),
        CheckConstraint("limit_amount > 0", name="ck_overlay_project_subcategory_reservations_amount_positive"),
        CheckConstraint("limit_amount <= 999999999999", name="ck_overlay_project_subcategory_reservations_amount_max"),
        Index("ix_overlay_project_subcategory_reservations_month", "budget_year", "budget_month", "category"),
        Index("ix_overlay_project_subcategory_reservations_subcategory", "user_subcategory_id"),
    )

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    user_subcategory_id = Column(Integer, ForeignKey("user_subcategories.id", ondelete="CASCADE"), nullable=False)
    category = Column(Enum(ExpenseCategory), nullable=False)
    budget_year = Column(Integer, nullable=False)
    budget_month = Column(Integer, nullable=False)
    limit_amount = Column(BigInteger, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    project = relationship("Project", back_populates="overlay_subcategory_reservations")
    user_subcategory = relationship("UserSubcategory", back_populates="project_monthly_limits")


class ExpenseSessionDraft(Base):
    __tablename__ = "expense_session_drafts"
    __table_args__ = (
        CheckConstraint("amount_paid IS NULL OR amount_paid > 0", name="ck_expense_session_drafts_amount_paid_positive"),
        Index("ix_expense_session_drafts_owner_status", "owner_id", "status"),
    )

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(100), nullable=False)
    description = Column(String(500), nullable=True)
    date = Column(Date, nullable=False, default=date.today)
    amount_paid = Column(BigInteger, nullable=True)
    status = Column(Enum(ExpenseSessionDraftStatus), nullable=False, default=ExpenseSessionDraftStatus.ACTIVE)
    source_type = Column(Enum(ExpenseSessionDraftSource), nullable=False, default=ExpenseSessionDraftSource.MANUAL)
    raw_ocr_text = Column(String, nullable=True)
    finalized_event_id = Column(Integer, ForeignKey("financial_events.id", ondelete="SET NULL"), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    owner = relationship("User", back_populates="expense_session_drafts")
    finalized_event = relationship("FinancialEvent", foreign_keys=[finalized_event_id])
    items = relationship("ExpenseSessionDraftItem", back_populates="draft", cascade="all, delete-orphan")
    wallet_allocations = relationship(
        "ExpenseSessionDraftWalletAllocation", back_populates="draft", cascade="all, delete-orphan"
    )
    splits = relationship("ExpenseSessionDraftSplit", back_populates="draft", cascade="all, delete-orphan")


class ExpenseSessionDraftItem(Base):
    __tablename__ = "expense_session_draft_items"
    __table_args__ = (
        CheckConstraint("original_amount > 0", name="ck_expense_session_draft_items_original_amount_positive"),
    )

    id = Column(Integer, primary_key=True, index=True)
    draft_id = Column(Integer, ForeignKey("expense_session_drafts.id", ondelete="CASCADE"), nullable=False, index=True)
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    label = Column(String(100), nullable=False)
    original_amount = Column(BigInteger, nullable=False)
    category = Column(Enum(ExpenseCategory), nullable=False)
    subcategory_id = Column(Integer, ForeignKey("user_subcategories.id", ondelete="SET NULL"), nullable=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="SET NULL"), nullable=True)
    project_subcategory_id = Column(Integer, ForeignKey("legacy_project_subcategories.id", ondelete="SET NULL"), nullable=True, index=True)
    isolated_project_subcategory_id = Column(Integer, ForeignKey("isolated_project_subcategory_allocations.id", ondelete="SET NULL"), nullable=True, index=True)
    sort_order = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    draft = relationship("ExpenseSessionDraft", back_populates="items")
    owner = relationship("User", back_populates="expense_session_draft_items")
    subcategory = relationship("UserSubcategory")
    project = relationship("Project", back_populates="session_draft_items")
    project_subcategory = relationship("LegacyProjectSubcategory")
    isolated_project_subcategory = relationship("IsolatedProjectSubcategoryAllocation")


class ExpenseSessionDraftWalletAllocation(Base):
    __tablename__ = "expense_session_draft_wallet_allocations"
    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_expense_session_draft_wallet_allocations_amount_positive"),
        UniqueConstraint("draft_id", "wallet_id", name="uq_expense_session_draft_wallet_allocations_draft_wallet"),
    )

    id = Column(Integer, primary_key=True, index=True)
    draft_id = Column(Integer, ForeignKey("expense_session_drafts.id", ondelete="CASCADE"), nullable=False, index=True)
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    wallet_id = Column(Integer, ForeignKey("wallets.id", ondelete="CASCADE"), nullable=False, index=True)
    amount = Column(BigInteger, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    draft = relationship("ExpenseSessionDraft", back_populates="wallet_allocations")
    owner = relationship("User", back_populates="expense_session_draft_wallet_allocations")
    wallet = relationship("Wallet")


class ExpenseSessionDraftSplit(Base):
    __tablename__ = "expense_session_draft_splits"
    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_expense_session_draft_splits_amount_positive"),
    )

    id = Column(Integer, primary_key=True, index=True)
    draft_id = Column(Integer, ForeignKey("expense_session_drafts.id", ondelete="CASCADE"), nullable=False, index=True)
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    contact_name = Column(String(32), nullable=False)
    amount = Column(BigInteger, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    draft = relationship("ExpenseSessionDraft", back_populates="splits")
    owner = relationship("User", back_populates="expense_session_draft_splits")


class ExpenseMergeGroup(Base):
    __tablename__ = "expense_merge_groups"
    __table_args__ = (
        Index("ix_expense_merge_groups_owner_created", "owner_id", "created_at"),
    )

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(100), nullable=False)
    description = Column(String(500), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    owner = relationship("User", back_populates="expense_merge_groups")
    events = relationship("FinancialEvent", back_populates="merge_group")


class FinancialEvent(Base):
    __tablename__ = "financial_events"
    
    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Context
    title = Column(String(100), nullable=False)
    description = Column(String(500), nullable=True)
    event_type = Column(Enum(TransactionType), nullable=False, index=True)
    status = Column(Enum(FinancialEventStatus), nullable=False, default=FinancialEventStatus.POSTED, server_default=FinancialEventStatus.POSTED.value, index=True)
    reference_type = Column(String(50), nullable=True, index=True)
    
    # Session Support (Basket/Multi-Expense Mode)
    is_session = Column(Boolean, default=False, nullable=False)
    discount_amount = Column(BigInteger, nullable=True, default=None)
    
    # Asset Lifecycle Pointer (e.g. for Refunds linking to original Event)
    linked_event_id = Column(Integer, ForeignKey("financial_events.id", ondelete="SET NULL"), nullable=True)
    merge_group_id = Column(Integer, ForeignKey("expense_merge_groups.id", ondelete="SET NULL"), nullable=True, index=True)
    void_reversal_event_id = Column(Integer, ForeignKey("financial_events.id", ondelete="SET NULL"), nullable=True, index=True)
    reverses_event_id = Column(Integer, ForeignKey("financial_events.id", ondelete="SET NULL"), nullable=True, index=True)
    voided_at = Column(DateTime(timezone=True), nullable=True)
    void_reason = Column(String(500), nullable=True)
    
    date = Column(Date, nullable=False, default=date.today)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    owner = relationship("User", back_populates="financial_events")
    merge_group = relationship("ExpenseMergeGroup", back_populates="events")
    wallet_legs = relationship("WalletLedger", back_populates="event", cascade="all, delete-orphan")
    entity_legs = relationship("EntityLedger", back_populates="event", cascade="all, delete-orphan")


class WalletLedger(Base):
    __tablename__ = "wallet_ledger"
    
    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    event_id = Column(Integer, ForeignKey("financial_events.id", ondelete="CASCADE"), nullable=False, index=True)
    wallet_id = Column(Integer, ForeignKey("wallets.id", ondelete="RESTRICT"), nullable=False, index=True)
    
    amount = Column(BigInteger, nullable=False) # Positive = Inflow, Negative = Outflow
    # Immutable event-time classification for expense outflows. NULL means a
    # legacy row whose funding split was not captured when it was posted.
    owned_spend_amount = Column(BigInteger, nullable=True)
    borrowed_spend_amount = Column(BigInteger, nullable=True)
    
    owner = relationship("User", back_populates="wallet_ledger_entries")
    event = relationship("FinancialEvent", back_populates="wallet_legs")
    wallet = relationship("Wallet", back_populates="ledger_entries")


class EntityLedger(Base):
    __tablename__ = "entity_ledger"
    
    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("financial_events.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Item-level metadata (for session items)
    label = Column(String(100), nullable=True)  # Item title within a session ("Beef", "Eggs")
    amount = Column(BigInteger, nullable=False)  # Positive = Budget Space Gained, Negative = Space Drained
    original_amount = Column(BigInteger, nullable=True)  # Pre-discount price (NULL if no discount)
    
    # The Polymorphic Pointers
    category = Column(Enum(ExpenseCategory), nullable=True)
    subcategory_id = Column(Integer, ForeignKey("user_subcategories.id", ondelete="SET NULL"), nullable=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="SET NULL"), nullable=True)
    project_subcategory_id = Column(Integer, ForeignKey("legacy_project_subcategories.id", ondelete="SET NULL"), nullable=True, index=True)
    isolated_project_subcategory_id = Column(Integer, ForeignKey("isolated_project_subcategory_allocations.id", ondelete="SET NULL"), nullable=True, index=True)
    budget_id = Column(Integer, ForeignKey("budgets.id", ondelete="SET NULL"), nullable=True)
    debt_id = Column(Integer, ForeignKey("debts.id", ondelete="SET NULL"), nullable=True)
    income_source_id = Column(Integer, ForeignKey("income_sources.id", ondelete="SET NULL"), nullable=True)
    payment_plan_id = Column(Integer, ForeignKey("payment_plans.id", ondelete="SET NULL"), nullable=True, index=True)
    payment_plan_payment_id = Column(Integer, ForeignKey("payment_plan_payments.id", ondelete="SET NULL"), nullable=True, index=True)
    
    event = relationship("FinancialEvent", back_populates="entity_legs")
    budget = relationship("Budget", back_populates="entity_ledger_entries")
    debt = relationship("Debt")
    income_source = relationship("IncomeSource")
    payment_plan = relationship("PaymentPlan")
    payment_plan_payment = relationship("PaymentPlanPayment")
    project = relationship("Project")
    subcategory = relationship("UserSubcategory")
    project_subcategory = relationship("LegacyProjectSubcategory")
    isolated_project_subcategory = relationship("IsolatedProjectSubcategoryAllocation")


class Asset(Base):
    """Tracks owned items of value that originated from an expense.
    Simple ownership record — no depreciation schedules or valuation formulas.
    User manually updates current_value when they feel like it."""
    __tablename__ = "assets"
    __table_args__ = (
        CheckConstraint("purchase_value > 0", name="ck_assets_purchase_value_positive"),
        CheckConstraint("current_value >= 0", name="ck_assets_current_value_non_negative"),
        Index("ix_assets_owner_status", "owner_id", "status"),
    )

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(100), nullable=False)
    description = Column(String(500), nullable=True)
    
    # Lineage — where this asset came from
    origin_event_id = Column(Integer, ForeignKey("financial_events.id", ondelete="SET NULL"), nullable=True)
    
    # Value tracking (manual)
    purchase_value = Column(BigInteger, nullable=False)
    current_value = Column(BigInteger, nullable=False)
    
    # Lifecycle status
    status = Column(String(20), default="owned", nullable=False)  # owned, sold, disposed, gifted
    
    # Sale tracking (populated when sold)
    sale_event_id = Column(Integer, ForeignKey("financial_events.id", ondelete="SET NULL"), nullable=True)
    sold_date = Column(Date, nullable=True)
    sale_value = Column(BigInteger, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    owner = relationship("User", back_populates="assets")
    origin_event = relationship("FinancialEvent", foreign_keys=[origin_event_id])
    sale_event = relationship("FinancialEvent", foreign_keys=[sale_event_id])
