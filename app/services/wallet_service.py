from datetime import date
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException, status
from .. import models

class WalletService:
    @staticmethod
    def adjust_balance(
        db: Session,
        wallet_id: int,
        amount_delta: int,
        transaction_type: models.TransactionType | None = None,
        is_bypass: bool = False
    ) -> models.Wallet:
        """
        Realistic balance update engine.
        Enforces conditional floors (Overdrafts/Credit Limits).
        """
        # 1. Row Locking & Fetch
        wallet = db.query(models.Wallet).filter(models.Wallet.id == wallet_id).with_for_update().first()
        
        if not wallet:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="wallets.not_found")

        # 2. Lifecycle Safety
        if not wallet.is_active:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="wallets.is_archived")

        # 3. Predict new balance
        new_balance = wallet.current_balance + amount_delta

        # 4. Enforce Context-Aware Floor Logic
        is_bypass_type = is_bypass or transaction_type == models.TransactionType.ADJUSTMENT

        if amount_delta < 0 and not is_bypass_type:
            if wallet.wallet_type == models.WalletType.CASH:
                # Cash is always strictly >= 0, no exceptions.
                if new_balance < 0:
                    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="wallets.insufficient_funds")
            
            elif wallet.accounting_type == models.AccountingType.ASSET:
                # Logic for Debit/Preloaded (allows for Overdrafts)
                floor = -wallet.overdraft_limit if (wallet.has_overdraft and wallet.overdraft_limit) else 0
                if new_balance < floor:
                    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="wallets.insufficient_funds")
            
            elif wallet.accounting_type == models.AccountingType.LIABILITY:
                # Logic for Credit/Charge
                if not wallet.allow_overlimit:
                    if new_balance < -wallet.credit_limit:
                        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="wallets.limit_exceeded")

        # 5. Apply and Save
        wallet.current_balance = new_balance
        db.flush()
        return wallet

    @staticmethod
    def record_transaction(
        db: Session,
        owner_id: int,
        wallet_id: int,
        transaction_type: models.TransactionType,
        amount_delta: int, # Negative means money leaving (-), Positive means money entering (+)
        currency: str = "UZS",
        category: models.ExpenseCategory | None = None,
        description: str | None = None,
        title: str | None = None,
        budget_id: int | None = None,
        income_source_id: int | None = None,
        debt_id: int | None = None,
        transaction_date: date | None = None,
        linked_event_id: int | None = None,
        is_bypass: bool = False,
        # Legacy parameters for backward compatibility with routers during migration:
        related_wallet_id: int | None = None,
        reference_id: int | None = None,
        recurring_id: int | None = None,
        idempotency_key: str | None = None,
        reference_type: str | None = None
    ) -> models.FinancialEvent:
        """
        The Master Ledger Engine for single-entry points.
        Performs the money movement and atomically logs the 3-Pile Ledger records.
        """
        if amount_delta == 0:
            raise HTTPException(status_code=400, detail="Transaction amount cannot be zero.")

        # 1. Engage the Math & Floor Constraints Engine
        is_bypass_type = is_bypass or category == models.ExpenseCategory.BANK_FEES_INTEREST
        WalletService.adjust_balance(db, wallet_id, amount_delta, transaction_type, is_bypass_type)

        # 2. Pile 1: Financial Event (The Receipt)
        from datetime import date as dt_date
        event = models.FinancialEvent(
            owner_id=owner_id,
            title=title or "Transaction",
            description=description,
            event_type=transaction_type,
            reference_type=reference_type,
            linked_event_id=linked_event_id,
            date=transaction_date or dt_date.today()
        )
        db.add(event)
        db.flush() # Get ID

        # 3. Pile 2: Wallet Ledger (The Money Movement)
        wallet_ledger = models.WalletLedger(
            owner_id=owner_id,
            event_id=event.id,
            wallet_id=wallet_id,
            amount=amount_delta # Keeps its sign! (- for expense, + for income)
        )
        db.add(wallet_ledger)

        # 4. Pile 3: Entity Ledger (The Allocation)
        entity_ledger = models.EntityLedger(
            event_id=event.id,
            amount=abs(amount_delta), # Usually stored as positive allocation
            category=category,
            budget_id=budget_id,
            debt_id=debt_id,
            income_source_id=income_source_id
        )
        db.add(entity_ledger)
        
        db.flush()
        return event

    @staticmethod
    def reconcile_balance(
        db: Session,
        owner_id: int,
        wallet_id: int,
        target_balance: int,
        note: str | None = None
    ) -> models.FinancialEvent | None:
        """
        Calculates the delta between the ledger balance and the actual balance,
        and logs a unified ADJUSTMENT transaction to sync them.
        """
        wallet = db.query(models.Wallet).filter(
            models.Wallet.id == wallet_id, 
            models.Wallet.owner_id == owner_id
        ).with_for_update().first()
        
        if not wallet:
            raise HTTPException(status_code=404, detail="Wallet not found")

        current_balance = wallet.current_balance
        delta = target_balance - current_balance
        
        if delta == 0:
            return None # Already synced
            
        return WalletService.record_transaction(
            db=db,
            owner_id=owner_id,
            wallet_id=wallet_id,
            transaction_type=models.TransactionType.ADJUSTMENT,
            amount_delta=delta,
            title="Balance Adjustment",
            description=note
        )

    @staticmethod
    def transfer_funds(
        db: Session, 
        owner_id: int, 
        from_wallet_id: int, 
        to_wallet_id: int, 
        amount: int, 
        description: str | None = None,
        transaction_date: date | None = None
    ) -> models.FinancialEvent:
        """
        Atomic Transfer Engine tracking a single Ledger row across two wallets.
        """
        if amount <= 0:
            raise HTTPException(status_code=400, detail="Transfer amount must be positive.")

        # 1. Lock in consistent order to prevent Database Deadlocks
        first_id, second_id = sorted([from_wallet_id, to_wallet_id])
        locked_wallets_by_id: dict[int, models.Wallet] = {}
        for wallet_id in (first_id, second_id):
            wallet = db.query(models.Wallet).filter(models.Wallet.id == wallet_id).with_for_update().first()
            if not wallet:
                raise HTTPException(status_code=404, detail="wallets.not_found")
            locked_wallets_by_id[wallet_id] = wallet
        from_wallet = locked_wallets_by_id[from_wallet_id]
        to_wallet = locked_wallets_by_id[to_wallet_id]

        # 2. Move the money mathematically
        WalletService.adjust_balance(db, from_wallet_id, -amount)
        WalletService.adjust_balance(db, to_wallet_id, amount)

        # 3. Pile 1: Financial Event
        from datetime import date as dt_date
        event = models.FinancialEvent(
            owner_id=owner_id,
            title=f"{from_wallet.name} \u2192 {to_wallet.name}",
            description=description,
            event_type=models.TransactionType.TRANSFER,
            date=transaction_date or dt_date.today()
        )
        db.add(event)
        db.flush()

        # 4. Pile 2: Wallet Ledger (2 Legs)
        leg_out = models.WalletLedger(
            owner_id=owner_id,
            event_id=event.id,
            wallet_id=from_wallet_id,
            amount=-amount
        )
        leg_in = models.WalletLedger(
            owner_id=owner_id,
            event_id=event.id,
            wallet_id=to_wallet_id,
            amount=amount
        )
        db.add_all([leg_out, leg_in])
        
        # 5. Pile 3: Entity Ledger (Just indicating Transfer)
        entity_ledger = models.EntityLedger(
            event_id=event.id,
            amount=amount
        )
        db.add(entity_ledger)
        
        db.flush()
        return event
