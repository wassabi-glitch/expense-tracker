from fastapi import APIRouter
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.utils import check_budget_alerts
from .. import oauth2
from .. import models, schemas
from ..session import get_db


router = APIRouter(
    prefix="/budgets",  # This means you don't have to type "/expenses" in every route!
    tags=['Budgets']    # This groups them nicely in your /docs page
)


@router.post("/", response_model=schemas.BudgetOut, status_code=status.HTTP_201_CREATED)
def create_budget(budget: schemas.BudgetCreate, db: Session = Depends(get_db), current_user: models.User = Depends(oauth2.get_current_user)):
    # Check if category budget already exists for user
    existing_budget = db.query(models.Budget).filter(
        models.Budget.owner_id == current_user.id, models.Budget.category == budget.category).first()

    if existing_budget:
        if existing_budget.is_active:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                                detail=f"Budget for this category already exists.")

        else:
            # Reactivate and update the existing budget
            existing_budget.is_active = True
            existing_budget.monthly_limit = budget.monthly_limit
            existing_budget.last_notified_threshold = 0
            db.commit()
            db.refresh(existing_budget)
            return existing_budget

    new_budget = models.Budget(
        **budget.model_dump(), owner_id=current_user.id, owner=current_user, is_active=True
    )

    db.add(new_budget)
    db.commit()
    db.refresh(new_budget)
    return new_budget


@router.get("/", response_model=List[schemas.BudgetOut])
def get_budgets(db: Session = Depends(get_db), current_user: models.User = Depends(oauth2.get_current_user)):
    budgets = db.query(models.Budget).filter(
        models.Budget.owner_id == current_user.id,
        models.Budget.is_active == True
    ).all()
    return budgets


@router.get("/{category}", response_model=schemas.BudgetOut)
def get_budget(
    category: schemas.ExpenseCategory,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user)
):
    budget = db.query(models.Budget).filter(models.Budget.owner_id ==
                                            current_user.id, models.Budget.category == category,
                                            models.Budget.is_active == True).first()
    if not budget:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Budget for category {category.value} not found."
        )
    return budget


@router.put("/{category}", response_model=schemas.BudgetOut)
def update_budget(
    category: schemas.ExpenseCategory,
    budget_update: schemas.BudgetUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user)
):

    budget_query = db.query(models.Budget).filter(
        models.Budget.owner_id == current_user.id,
        models.Budget.category == category,
        models.Budget.is_active == True
    )
    budget = budget_query.first()

    if not budget:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Budget for category {category.value} not found."
        )

    old_limit = budget.monthly_limit
    new_limit = budget_update.monthly_limit

    budget.monthly_limit = new_limit

    # 3. AUTOMATIC MEMORY WIPE
    # TRAP: If we increase the budget (e.g. $100 -> $1000), the user's spending % drops.
    # We MUST reset the 'last_notified' memory to 0.
    # If we don't, the system will think "I already warned them at 90%" and stay silent
    # even when they hit 90% of the NEW, higher budget.
    if new_limit != old_limit:
        budget.last_notified_threshold = 0

    db.flush()

    check_budget_alerts(db, current_user.id, budget.category)

    db.commit()
    db.refresh(budget)
    return budget


@router.delete("/{category}", status_code=status.HTTP_204_NO_CONTENT)
def delete_budget(
    category: schemas.ExpenseCategory,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user)
):
    budget_query = db.query(models.Budget).filter(
        models.Budget.owner_id == current_user.id, models.Budget.category == category)
    budget = budget_query.first()

    if not budget:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Budget for category {category.value} not found."
        )

    budget.is_active = False

    db.commit()
    return
