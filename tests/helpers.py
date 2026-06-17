from datetime import datetime
from zoneinfo import ZoneInfo

from app import models
from app.main import app
from app.session import get_db

TEST_CATEGORY_MAP = {
    "Food": "Groceries",
    "Other": "Utilities",
}
TEST_TIMEZONE = "Asia/Tashkent"


def _normalize_test_category(category: str) -> str:
    return TEST_CATEGORY_MAP.get(category, category)


def user_timezone_today():
    return datetime.now(ZoneInfo(TEST_TIMEZONE)).date()


def create_user_and_token(client, username, email, password):
    client.post("/users/sign-up", json={
        "username": username,
        "email": email,
        "password": password,
    }, headers={"X-Timezone": TEST_TIMEZONE})

    # Tests bypass email inbox flow by marking the user verified directly.
    override_db_factory = app.dependency_overrides.get(get_db)
    if override_db_factory is not None:
        db_gen = override_db_factory()
        db = next(db_gen)
        try:
            user = db.query(models.User).filter(models.User.email == email).first()
            if user is not None:
                user.is_verified = True
                
                # NEW: Every test user needs a default wallet now for Transactions to work!
                # We create a simple CASH wallet so expenses have a place to deduct from.
                default_wallet = models.Wallet(
                    owner_id=user.id,
                    name="Default Wallet",
                    wallet_type=models.WalletType.CASH,
                    accounting_type=models.AccountingType.ASSET,
                    initial_balance=10_000_000, # Give them some test money
                    current_balance=10_000_000,
                    is_default=True
                )
                db.add(default_wallet)
                db.commit()
        finally:
            db.close()
            try:
                next(db_gen)
            except StopIteration:
                pass

    res = client.post("/users/sign-in", data={
        "username": email,
        "password": password,
    }, headers={"X-Timezone": TEST_TIMEZONE})
    token = res.json()["access_token"]
    return {"Authorization": f"Bearer {token}", "X-Timezone": TEST_TIMEZONE}


def create_budget(client, headers, category="Groceries", monthly_limit=1000, budget_year=None, budget_month=None):
    today = user_timezone_today()
    category = _normalize_test_category(category)
    return client.post("/budgets/", json={
        "category": category,
        "monthly_limit": monthly_limit,
        "budget_year": budget_year or today.year,
        "budget_month": budget_month or today.month,
    }, headers=headers)


def create_expense(client, headers, title="Lunch", amount=10, category="Groceries", description="test", expense_date=None):
    category = _normalize_test_category(category)
    return client.post("/expenses/", json={
        "title": title,
        "amount": amount,
        "category": category,
        "description": description,
        "date": (expense_date or user_timezone_today()).isoformat(),
    }, headers=headers)
