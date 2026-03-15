from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from .. import models, oauth2, schemas
from ..redis_rate_limiter import consume_token_bucket
from ..session import get_db
from ..savings_balances import build_savings_summary, ensure_premium_user

router = APIRouter(
    prefix="/savings",
    tags=["Savings"],
)

SAVINGS_WRITE_BUCKET_CAPACITY = 12
SAVINGS_WRITE_REFILL_RATE = 12 / 60


def enforce_savings_write_rate_limit(user_id: int) -> dict[str, str]:
    rl = consume_token_bucket(
        scope="savings_write",
        identifier=str(user_id),
        capacity=SAVINGS_WRITE_BUCKET_CAPACITY,
        refill_rate_per_second=SAVINGS_WRITE_REFILL_RATE,
    )
    headers = {
        "X-RateLimit-Limit": str(rl.limit),
        "X-RateLimit-Remaining": str(rl.remaining),
        "X-RateLimit-Reset": str(rl.reset_seconds),
    }
    if not rl.allowed:
        headers["Retry-After"] = str(rl.reset_seconds)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="savings.write_rate_limited",
            headers=headers,
        )
    return headers

@router.get("/summary", response_model=schemas.SavingsSummaryOut)
def get_savings_summary(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
):
    ensure_premium_user(current_user)
    return build_savings_summary(db, current_user.id)


@router.post("/deposit", response_model=schemas.SavingsTransactionOut, status_code=status.HTTP_201_CREATED)
def deposit_to_savings(
    payload: schemas.SavingsTransactionCreate,
    response: Response,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
):
    ensure_premium_user(current_user)
    rate_headers = enforce_savings_write_rate_limit(current_user.id)
    for k, v in rate_headers.items():
        response.headers[k] = v
    summary = build_savings_summary(db, current_user.id)
    if payload.amount > summary.spendable_balance:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="savings.insufficient_spendable_balance",
        )

    transaction = models.SavingsTransactions(
        owner_id=current_user.id,
        amount=payload.amount,
        transaction_type=models.SavingsTransactionType.DEPOSIT,
    )
    db.add(transaction)
    db.commit()
    db.refresh(transaction)
    return transaction


@router.post("/withdraw", response_model=schemas.SavingsTransactionOut, status_code=status.HTTP_201_CREATED)
def withdraw_from_savings(
    payload: schemas.SavingsTransactionCreate,
    response: Response,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
):
    ensure_premium_user(current_user)
    rate_headers = enforce_savings_write_rate_limit(current_user.id)
    for k, v in rate_headers.items():
        response.headers[k] = v
    summary = build_savings_summary(db, current_user.id)
    if payload.amount > summary.free_savings_balance:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="savings.insufficient_free_savings_balance",
        )

    transaction = models.SavingsTransactions(
        owner_id=current_user.id,
        amount=payload.amount,
        transaction_type=models.SavingsTransactionType.WITHDRAWAL,
    )
    db.add(transaction)
    db.commit()
    db.refresh(transaction)
    return transaction
