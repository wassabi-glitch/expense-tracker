from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import models, oauth2, schemas
from ..savings_balances import build_savings_summary, ensure_premium_user
from ..session import get_db

router = APIRouter(
    prefix="/savings",
    tags=["Savings"],
)


@router.get("/summary", response_model=schemas.GoalFundingSummaryOut)
def get_savings_summary(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
):
    ensure_premium_user(current_user)
    return build_savings_summary(db, current_user.id)


@router.post("/deposit", status_code=status.HTTP_410_GONE)
def deposit_to_savings():
    raise HTTPException(
        status_code=status.HTTP_410_GONE,
        detail="savings.virtual_savings_removed",
    )


@router.post("/withdraw", status_code=status.HTTP_410_GONE)
def withdraw_from_savings():
    raise HTTPException(
        status_code=status.HTTP_410_GONE,
        detail="savings.virtual_savings_removed",
    )
