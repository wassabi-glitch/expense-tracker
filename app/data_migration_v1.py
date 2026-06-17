from sqlalchemy.orm import Session
from app.session import SessionLocal
from app import models
import json

def migrate_data():
    db = SessionLocal()
    try:
        users = db.query(models.User).join(models.UserProfile).all()
        print(f"Found {len(users)} users to migrate.")
        
        for user in users:
            profile = user.profile
            if not profile:
                continue
            
            # 1. Migrate Life Status (if not already done)
            if profile.life_status and not profile.life_statuses:
                profile.life_statuses = [profile.life_status]
                print(f"Migrated life_status for user {user.username}")

            # 2. Create Default Wallet if none exists
            existing_wallets = db.query(models.Wallet).filter(models.Wallet.owner_id == user.id).count()
            if existing_wallets == 0:
                default_wallet = models.Wallet(
                    owner_id=user.id,
                    name="Cash",
                    initial_balance=int(profile.initial_balance or 0),
                    color="gradient-indigo", # Starting with a premium look
                    currency="UZS",
                    is_default=True
                )
                db.add(default_wallet)
                db.flush() # Get wallet ID
                print(f"Created default 'Cash' wallet for user {user.username} with balance {profile.initial_balance}")
                
        db.commit()
        print("Data migration completed successfully.")
    except Exception as e:
        db.rollback()
        print(f"Error during migration: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    migrate_data()
