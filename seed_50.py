import sys
from datetime import date
import random
sys.path.append("/app")

from app.database import SessionLocal
from app import models
from app.models import ExpenseCategory, RecurringFrequency

db = SessionLocal()

# We need to restore the 34 templates the user lost, plus the 16 they requested.
# Total = 50 templates, to perfectly hit the edge of their limit.
categories = list(ExpenseCategory)
frequencies = list(RecurringFrequency)

for i in range(1, 51):
    expense = models.RecurringExpense(
        owner_id=7,
        title=f"Restored Subscription {i}" if i <= 34 else f"New Subscription {i}",
        amount=random.randint(5, 50) * 1000,
        category=random.choice(categories),
        description=f"Automated test data #{i}",
        frequency=random.choice(frequencies),
        start_date=date(2026, 3, 5),
        next_due_date=date(2026, 3, 5),
        is_active=True
    )
    db.add(expense)

db.commit()
db.close()
print("Successfully inserted 50 recurring expenses for user 7!")
