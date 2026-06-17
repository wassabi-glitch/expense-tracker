from app.session import SessionLocal
from app import models
from sqlalchemy import text

def backfill_transaction_wallets():
    db = SessionLocal()
    try:
        # Tables to update: expenses, income_entries, savings_transactions, debt_transactions
        tables = [
            "expenses", 
            "income_entries", 
            "savings_transactions", 
            "debt_transactions"
        ]
        
        for table in tables:
            print(f"Backfilling {table}...")
            # Subquery finds the default wallet ID for the owner of each transaction
            query = text(f"""
                UPDATE {table}
                SET wallet_id = sub.id
                FROM (
                    SELECT id, owner_id FROM wallets WHERE is_default = true
                ) AS sub
                WHERE {table}.owner_id = sub.owner_id
                AND {table}.wallet_id IS NULL;
            """)
            result = db.execute(query)
            print(f"Updated {result.rowcount} rows in {table}.")
        
        db.commit()
        print("Transaction backfill completed successfully.")
    except Exception as e:
        db.rollback()
        print(f"Error during backfill: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    backfill_transaction_wallets()
