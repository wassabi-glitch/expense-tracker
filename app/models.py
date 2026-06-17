from sqlalchemy import Boolean, CheckConstraint, Column, Date, Index, Integer, BigInteger, String, DateTime, ForeignKey, Enum, UniqueConstraint, JSON
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
    INSTALLMENT_DOWN_PAYMENT = "installment_down_payment"
    INSTALLMENT_PAYMENT = "installment_payment"
    VOID_REVERSAL = "void_reversal"
    INSTALLMENT_FEE = "installment_fee"
    INSTALLMENT_PENALTY = "installment_penalty"



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
    SETTLE = "SETTLE"
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


class InstallmentFrequency(str, enum.Enum):
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


class InstallmentStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    PAID = "PAID"
    ARCHIVED = "ARCHIVED"


class InstallmentPaymentStatus(str, enum.Enum):
    PENDING = "PENDING"
    PARTIAL = "PARTIAL"
    PAID = "PAID"
    SKIPPED = "SKIPPED"


class InstallmentPaymentComponentType(str, enum.Enum):
    PRINCIPAL = "PRINCIPAL"
    CHARGE = "CHARGE"


class BudgetLedgerType(str, enum.Enum):
    ROLLOVER = "ROLLOVER"
    SWEEP = "SWEEP"
    CAP_TRIM = "CAP_TRIM"


class ExpectedIncomeStatus(str, enum.Enum):
    EXPECTED = "EXPECTED"
    RECEIVED = "RECEIVED"
    MISSED = "MISSED"
    CANCELLED = "CANCELLED"


class ProjectStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    STOPPED = "STOPPED"
    COMPLETED = "COMPLETED"
    ARCHIVED = "ARCHIVED"


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
    income_sources = relationship(
        "IncomeSource", back_populates="owner", cascade="all, delete")
    income_entries = relationship(
        "IncomeEntry", back_populates="owner", cascade="all, delete")
    expected_incomes = relationship(
        "ExpectedIncome", back_populates="owner", cascade="all, delete-orphan")
    budgets = relationship(
        "Budget", back_populates="owner", cascade="all, delete")
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
    debt_action_restrictions = relationship(
        "DebtActionRestriction", back_populates="owner", cascade="all, delete-orphan")
    installments = relationship(
        "InstallmentPlan", back_populates="owner", cascade="all, delete")
    installment_payments = relationship(
        "InstallmentPayment", back_populates="owner", cascade="all, delete")
    installment_payment_allocations = relationship(
        "InstallmentPaymentAllocation", back_populates="owner", cascade="all, delete-orphan")
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
            "(wallet_type != 'CREDIT' AND accounting_type = 'ASSET') OR can_fund_goals = FALSE",
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


class ExpectedIncome(Base):
    __tablename__ = "expected_incomes"
    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_expected_incomes_amount_positive"),
        CheckConstraint("amount <= 999999999999", name="ck_expected_incomes_amount_limit"),
        CheckConstraint("due_date >= '2020-01-01'", name="ck_expected_incomes_due_date_min_2020_01_01"),
        CheckConstraint("budget_month >= 1 AND budget_month <= 12", name="ck_expected_incomes_budget_month_1_12"),
        CheckConstraint("budget_year >= 2020", name="ck_expected_incomes_budget_year_min_2020"),
        Index("ix_expected_incomes_owner_month_status", "owner_id", "budget_year", "budget_month", "status"),
        Index("ix_expected_incomes_owner_source", "owner_id", "source_id"),
    )

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    source_id = Column(Integer, ForeignKey("income_sources.id", ondelete="SET NULL"), nullable=True, index=True)
    debt_id = Column(Integer, ForeignKey("debts.id", ondelete="SET NULL"), nullable=True, index=True)
    amount = Column(BigInteger, nullable=False)
    received_amount = Column(BigInteger, nullable=True)
    linked_transaction_id = Column(Integer, ForeignKey("financial_events.id", ondelete="SET NULL"), nullable=True, index=True)
    due_date = Column(Date, nullable=False)
    budget_year = Column(Integer, nullable=False)
    budget_month = Column(Integer, nullable=False)
    status = Column(Enum(ExpectedIncomeStatus), nullable=False, default=ExpectedIncomeStatus.EXPECTED)
    note = Column(String(200), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    owner = relationship("User", back_populates="expected_incomes")
    source = relationship("IncomeSource", back_populates="expected_incomes")
    debt = relationship("Debt", back_populates="expected_incomes")
    linked_transaction = relationship("FinancialEvent")


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

    # ── State Machine ─────────────────────────────────────────────────
    # status: User Intent (ACTIVE/DISABLED).
    # failing_due_date: The date of the specific bill that is currently stuck.
    #                  If NULL, the template is healthy.
    status = Column(Enum(RecurringStatus), nullable=False, default=RecurringStatus.ACTIVE)
    failing_due_date = Column(Date, nullable=True)

    # ── Cycle Behavior ────────────────────────────────────────────────
    # FIXED    → Next due date anchored to calendar (rent, cleaner).
    #            Paid late on Wednesday? Next due is still next Sunday.
    # FLEXIBLE → Next due date shifts on late payment (Netflix, gym).
    #            Paid 9 days late? next_due = payment_date + interval.
    cycle_behavior = Column(Enum(CycleBehavior), nullable=False, default=CycleBehavior.FIXED)

    # ── Date Anchoring ────────────────────────────────────────────────
    # The original day of the month/year the user intended (e.g. 31).
    # Used to "snap back" to the correct day after a short month like February.
    original_due_day = Column(Integer, nullable=True)

    # ── Retry Tracking ────────────────────────────────────────────────
    # How many consecutive hourly retries have failed. Reset to 0 on success.
    # At 72 (3 days × 24 hours), the system auto-pauses the template.
    retry_count = Column(Integer, nullable=False, default=0)
    # Timestamp of the most recent failed attempt. Used to throttle notifications
    # to once per day (so the user doesn't get 24 alerts for the same failure).
    last_retry_at = Column(DateTime(timezone=True), nullable=True)
    custom_projection_horizons = Column(JSON, nullable=True)
    
    # Relationships
    events = relationship("RecurringEvent", back_populates="recurring_expense", cascade="all, delete-orphan")


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

    # ── Rollover Controls (The 3 Knobs) ──────────────────────────
    max_envelope_balance = Column(BigInteger, nullable=True)
    max_rollover_amount = Column(BigInteger, nullable=True)
    rollover_mode = Column(String(10), nullable=True)

    # ── Sweeping (The Wealth Builder) ─────────────────────────────
    sweep_target_goal_id = Column(Integer, ForeignKey("goals.id", ondelete="SET NULL"), nullable=True)

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
    linked_installment_plan_id = Column(Integer, ForeignKey("installment_plans.id", ondelete="SET NULL"), nullable=True, index=True)
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
    linked_installment_plan = relationship("InstallmentPlan", foreign_keys=[linked_installment_plan_id])
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
        Index("ix_debts_owner_status", "owner_id", "status"),
        Index("ix_debts_owner_type", "owner_id", "debt_type"),
        Index("ix_debts_owner_origin", "owner_id", "origin_kind"),
        Index("ix_debts_owner_product", "owner_id", "product_kind"),
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
    date = Column(Date, nullable=False)
    expected_return_date = Column(Date, nullable=True)
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
    action_restrictions = relationship("DebtActionRestriction", back_populates="debt", cascade="all, delete-orphan")
    installment_plan = relationship("InstallmentPlan", back_populates="debt", uselist=False)
    expected_incomes = relationship("ExpectedIncome", back_populates="debt")

    # New fields for real-world money flow
    is_money_transferred = Column(Boolean, default=False, nullable=False)
    initial_wallet_id = Column(Integer, ForeignKey("wallets.id", ondelete="SET NULL"), nullable=True)
    linked_event_id = Column(Integer, ForeignKey("financial_events.id", ondelete="SET NULL"), nullable=True)
    
    # Pre-tags for Cash-Basis Accounting
    expense_category = Column(Enum(ExpenseCategory), nullable=True)
    expense_subcategory_id = Column(Integer, ForeignKey("user_subcategories.id", ondelete="SET NULL"), nullable=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="SET NULL", use_alter=True), nullable=True)
    project_subcategory_id = Column(Integer, ForeignKey("project_subcategories.id", ondelete="SET NULL", use_alter=True), nullable=True)
    income_source_id = Column(Integer, ForeignKey("income_sources.id", ondelete="SET NULL"), nullable=True)

    expense_subcategory = relationship("UserSubcategory")
    project = relationship("Project")
    project_subcategory = relationship("ProjectSubcategory")



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


class DebtActionRestriction(Base):
    __tablename__ = "debt_action_restrictions"
    __table_args__ = (
        Index("ix_debt_action_restrictions_debt_active", "debt_id", "is_active"),
        Index("ix_debt_action_restrictions_owner_action", "owner_id", "action_kind"),
    )

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    debt_id = Column(Integer, ForeignKey("debts.id", ondelete="CASCADE"), nullable=False, index=True)
    action_kind = Column(Enum(DebtActionKind), nullable=False)
    level = Column(Enum(DebtActionRestrictionLevel), nullable=False)
    reason_code = Column(String(100), nullable=False)
    source = Column(
        Enum(DebtActionRestrictionSource),
        nullable=False,
        default=DebtActionRestrictionSource.SYSTEM,
        server_default=DebtActionRestrictionSource.SYSTEM.value,
    )
    is_active = Column(Boolean, nullable=False, default=True, server_default="true")
    details = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    resolved_at = Column(DateTime(timezone=True), nullable=True)

    owner = relationship("User", back_populates="debt_action_restrictions")
    debt = relationship("Debt", back_populates="action_restrictions")


class InstallmentPlan(Base):
    __tablename__ = "installment_plans"
    __table_args__ = (
        CheckConstraint("total_price > 0", name="ck_installments_total_price_positive"),
        CheckConstraint("down_payment >= 0", name="ck_installments_down_payment_non_negative"),
        CheckConstraint("remaining_amount >= 0", name="ck_installments_remaining_amount_non_negative"),
        CheckConstraint("months > 0", name="ck_installments_months_positive"),
        CheckConstraint("payment_count > 0", name="ck_installments_payment_count_positive"),
        CheckConstraint("regular_payment_amount >= 0", name="ck_installments_regular_payment_amount_non_negative"),
        Index("ix_installments_owner_status", "owner_id", "status"),
        Index("ix_installments_owner_plan_type", "owner_id", "plan_type"),
        Index("uq_installment_plans_debt_id", "debt_id", unique=True),
    )

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    debt_id = Column(Integer, ForeignKey("debts.id", ondelete="SET NULL", use_alter=True), nullable=True)
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
    frequency = Column(Enum(InstallmentFrequency), nullable=False, default=InstallmentFrequency.MONTHLY)
    monthly_payment_amount = Column(BigInteger, nullable=False)
    regular_payment_amount = Column(BigInteger, nullable=False)
    schedule_rule = Column(JSON, nullable=True)
    status = Column(Enum(InstallmentStatus), nullable=False, default=InstallmentStatus.ACTIVE)
    start_date = Column(Date, nullable=False)
    expense_category = Column(Enum(ExpenseCategory), nullable=True)
    expense_subcategory_id = Column(Integer, ForeignKey("user_subcategories.id", ondelete="SET NULL"), nullable=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="SET NULL", use_alter=True), nullable=True)
    project_subcategory_id = Column(Integer, ForeignKey("project_subcategories.id", ondelete="SET NULL", use_alter=True), nullable=True)
    asset_id = Column(Integer, ForeignKey("assets.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    owner = relationship("User", back_populates="installments")
    payments = relationship("InstallmentPayment", back_populates="plan", cascade="all, delete")
    debt = relationship("Debt", back_populates="installment_plan")
    expense_subcategory = relationship("UserSubcategory")
    project = relationship("Project")
    project_subcategory = relationship("ProjectSubcategory")
    asset = relationship("Asset")


class InstallmentPayment(Base):
    __tablename__ = "installment_payments"
    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_installment_payments_amount_positive"),
        CheckConstraint("paid_amount >= 0", name="ck_installment_payments_paid_amount_non_negative"),
        CheckConstraint("written_off_amount >= 0", name="ck_installment_payments_written_off_amount_non_negative"),
        CheckConstraint("paid_amount <= amount", name="ck_installment_payments_paid_amount_not_above_amount"),
        CheckConstraint(
            "paid_amount + written_off_amount <= amount",
            name="ck_installment_payments_settled_amount_not_above_amount",
        ),
        Index("ix_installment_payments_plan_due_date", "plan_id", "due_date"),
        Index("ix_installment_payments_owner_due_date", "owner_id", "due_date"),
    )

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    plan_id = Column(Integer, ForeignKey("installment_plans.id", ondelete="CASCADE"), nullable=False, index=True)
    debt_charge_id = Column(Integer, ForeignKey("debt_charges.id", ondelete="SET NULL"), nullable=True, index=True)
    amount = Column(BigInteger, nullable=False)
    paid_amount = Column(BigInteger, nullable=False, default=0, server_default="0")
    written_off_amount = Column(BigInteger, nullable=False, default=0, server_default="0")
    component_type = Column(
        Enum(InstallmentPaymentComponentType),
        nullable=False,
        default=InstallmentPaymentComponentType.PRINCIPAL,
        server_default=InstallmentPaymentComponentType.PRINCIPAL.value,
    )
    status = Column(Enum(InstallmentPaymentStatus), nullable=False, default=InstallmentPaymentStatus.PENDING)
    due_date = Column(Date, nullable=False)
    paid_date = Column(Date, nullable=True)
    note = Column(String(200), nullable=True)
    event_id = Column(Integer, ForeignKey("financial_events.id", ondelete="SET NULL"), nullable=True, index=True)
    debt_ledger_entry_id = Column(Integer, ForeignKey("debt_ledger_entries.id", ondelete="SET NULL"), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    owner = relationship("User", back_populates="installment_payments")
    plan = relationship("InstallmentPlan", back_populates="payments")
    debt_charge = relationship("DebtCharge")
    event = relationship("FinancialEvent")
    debt_ledger_entry = relationship("DebtLedgerEntry")
    allocations = relationship("InstallmentPaymentAllocation", back_populates="payment", cascade="all, delete-orphan")


class InstallmentPaymentAllocation(Base):
    __tablename__ = "installment_payment_allocations"
    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_installment_payment_allocations_amount_positive"),
        Index("ix_installment_payment_allocations_owner_date", "owner_id", "paid_date"),
    )

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    installment_payment_id = Column(Integer, ForeignKey("installment_payments.id", ondelete="CASCADE"), nullable=False, index=True)
    financial_event_id = Column(Integer, ForeignKey("financial_events.id", ondelete="SET NULL"), nullable=True, index=True)
    debt_transaction_id = Column(Integer, ForeignKey("debt_transactions.id", ondelete="SET NULL"), nullable=True, index=True)
    debt_ledger_entry_id = Column(Integer, ForeignKey("debt_ledger_entries.id", ondelete="SET NULL"), nullable=True, index=True)
    wallet_id = Column(Integer, ForeignKey("wallets.id", ondelete="SET NULL"), nullable=True, index=True)
    amount = Column(BigInteger, nullable=False)
    paid_date = Column(Date, nullable=False)
    note = Column(String(200), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    owner = relationship("User", back_populates="installment_payment_allocations")
    payment = relationship("InstallmentPayment", back_populates="allocations")
    financial_event = relationship("FinancialEvent")
    debt_transaction = relationship("DebtTransaction")
    debt_ledger_entry = relationship("DebtLedgerEntry")
    wallet = relationship("Wallet")


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

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    owner = relationship("User", back_populates="subcategories")
    monthly_limits = relationship(
        "BudgetSubcategoryLimit", back_populates="subcategory", cascade="all, delete-orphan")


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
    entry_type = Column(Enum(BudgetLedgerType), nullable=False)
    
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
    
    # Core project type
    is_isolated = Column(Boolean, nullable=False, default=False)
    
    # Optional Graduation pipeline
    origin_goal_id = Column(Integer, ForeignKey("goals.id", ondelete="SET NULL"), nullable=True)
    
    # Financials
    total_limit = Column(BigInteger, nullable=True)
    status = Column(Enum(ProjectStatus), nullable=False, default=ProjectStatus.ACTIVE)
    start_date = Column(Date, nullable=False, default=date.today)
    target_end_date = Column(Date, nullable=True)
    completed_at = Column(Date, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    owner = relationship("User", back_populates="projects")
    category_limits = relationship("ProjectCategoryLimit", back_populates="project", cascade="all, delete-orphan")
    subcategories = relationship("ProjectSubcategory", back_populates="project", cascade="all, delete-orphan")
    goal_releases = relationship("GoalProjectRelease", back_populates="project", cascade="all, delete-orphan")
    session_draft_items = relationship("ExpenseSessionDraftItem", back_populates="project")


class ProjectCategoryLimit(Base):
    __tablename__ = "project_category_limits"
    __table_args__ = (
        UniqueConstraint("project_id", "category", name="uq_project_category_limits"),
    )

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    category = Column(Enum(ExpenseCategory), nullable=False)
    limit_amount = Column(BigInteger, nullable=False)
    
    project = relationship("Project", back_populates="category_limits")


class ProjectSubcategory(Base):
    __tablename__ = "project_subcategories"
    __table_args__ = (
        UniqueConstraint("project_id", "category", "name", name="uq_project_subcategories_project_category_name"),
        Index("ix_project_subcategories_project_category", "project_id", "category"),
    )

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    category = Column(Enum(ExpenseCategory), nullable=False)
    name = Column(String(50), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    limit_amount = Column(BigInteger, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    project = relationship("Project", back_populates="subcategories")


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
    project_subcategory_id = Column(Integer, ForeignKey("project_subcategories.id", ondelete="SET NULL"), nullable=True, index=True)
    sort_order = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    draft = relationship("ExpenseSessionDraft", back_populates="items")
    owner = relationship("User", back_populates="expense_session_draft_items")
    subcategory = relationship("UserSubcategory")
    project = relationship("Project", back_populates="session_draft_items")
    project_subcategory = relationship("ProjectSubcategory")


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
    project_subcategory_id = Column(Integer, ForeignKey("project_subcategories.id", ondelete="SET NULL"), nullable=True, index=True)
    budget_id = Column(Integer, ForeignKey("budgets.id", ondelete="SET NULL"), nullable=True)
    debt_id = Column(Integer, ForeignKey("debts.id", ondelete="SET NULL"), nullable=True)
    income_source_id = Column(Integer, ForeignKey("income_sources.id", ondelete="SET NULL"), nullable=True)
    installment_plan_id = Column(Integer, ForeignKey("installment_plans.id", ondelete="SET NULL"), nullable=True, index=True)
    installment_payment_id = Column(Integer, ForeignKey("installment_payments.id", ondelete="SET NULL"), nullable=True, index=True)
    
    event = relationship("FinancialEvent", back_populates="entity_legs")
    budget = relationship("Budget", back_populates="entity_ledger_entries")
    debt = relationship("Debt")
    income_source = relationship("IncomeSource")
    installment_plan = relationship("InstallmentPlan")
    installment_payment = relationship("InstallmentPayment")
    project = relationship("Project")
    subcategory = relationship("UserSubcategory")
    project_subcategory = relationship("ProjectSubcategory")


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
