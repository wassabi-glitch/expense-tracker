from fastapi import APIRouter, Depends, Query
# pyrefly: ignore [missing-import]
from sqlalchemy.orm import Session
# pyrefly: ignore [missing-import]
from sqlalchemy import func
from typing import List, Optional
# pyrefly: ignore [missing-import]
from pydantic import BaseModel
from datetime import datetime, date

from app.session import get_db
# pyrefly: ignore [missing-import]
from app.oauth2 import get_current_user
from app.models import User, ExpenseCategory, UserSubcategory, FinancialEvent, EntityLedger, FinancialEventStatus
from app.schemas import (
    UserSubcategoryOut,
    SubcategoryTaxonomyOut,
    SubcategoryUpdateIn,
    SubcategoryCreateIn,
    SubcategoryMergeIn,
)

router = APIRouter(
    prefix="/subcategories",
    tags=["Subcategories"],
)


@router.get("/", response_model=List[UserSubcategoryOut])
def get_user_subcategories(
    category: Optional[ExpenseCategory] = Query(None, description="Filter by category"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get all active global subcategory tags for the authenticated user.
    Optionally filter by parent ExpenseCategory.
    Archived (is_active=False) tags are excluded.
    """
    query = db.query(UserSubcategory).filter(
        UserSubcategory.owner_id == current_user.id,
        UserSubcategory.is_active == True
    )

    if category:
        query = query.filter(UserSubcategory.category == category)

    # Order by name for the Combobox
    tags = query.order_by(UserSubcategory.name).all()
    return tags

@router.get("/taxonomy", response_model=List[SubcategoryTaxonomyOut])
def get_taxonomy_hub(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get all global subcategory tags for the authenticated user (including archived ones),
    enriched with Lifetime Scorecards (first/last used dates, tx count, and total spent).
    """
    # Base query for user's subcategories
    subcategories = db.query(UserSubcategory).filter(
        UserSubcategory.owner_id == current_user.id,
        UserSubcategory.is_deleted == False
    ).order_by(
        UserSubcategory.category,
        UserSubcategory.name
    ).all()

    # pyrefly: ignore [missing-import]
    from sqlalchemy import case, and_
    from app.models import TransactionType

    signed_amount = case(
        (
            and_(
                FinancialEvent.status == FinancialEventStatus.POSTED,
                FinancialEvent.event_type == TransactionType.EXPENSE,
            ),
            EntityLedger.amount,
        ),
        (
            and_(
                FinancialEvent.status == FinancialEventStatus.POSTED,
                FinancialEvent.event_type == TransactionType.REFUND,
            ),
            -EntityLedger.amount,
        ),
        else_=0,
    )

    stats_query = db.query(
        EntityLedger.subcategory_id,
        func.min(FinancialEvent.date).label("first_used"),
        func.max(FinancialEvent.date).label("last_used"),
        func.count(EntityLedger.id).label("tx_count"),
        func.sum(signed_amount).label("total_drained")
    ).select_from(EntityLedger).join(
        FinancialEvent, EntityLedger.event_id == FinancialEvent.id
    ).filter(
        FinancialEvent.owner_id == current_user.id,
        FinancialEvent.status == FinancialEventStatus.POSTED,
        FinancialEvent.event_type.in_([
            TransactionType.EXPENSE,
            TransactionType.REFUND,
        ]),
        EntityLedger.subcategory_id.isnot(None),
    ).group_by(EntityLedger.subcategory_id).all()

    # Map subcategory_id -> stats
    stats_map = {}
    for row in stats_query:
        spent = row.total_drained if row.total_drained else 0
        stats_map[row.subcategory_id] = {
            "first_used": row.first_used,
            "last_used": row.last_used,
            "tx_count": row.tx_count,
            "lifetime_spent": spent
        }

    results = []
    for sub in subcategories:
        stats = stats_map.get(sub.id, {
            "first_used": None,
            "last_used": None,
            "tx_count": 0,
            "lifetime_spent": 0
        })
        
        # Build the enriched response
        # Using dict unpacking because we need to append the scorecard
        sub_dict = {
            "id": sub.id,
            "category": sub.category,
            "name": sub.name,
            "is_active": sub.is_active,
            "created_at": sub.created_at,
            "scorecard": stats
        }
        results.append(SubcategoryTaxonomyOut(**sub_dict))

    return results


@router.post("/", response_model=UserSubcategoryOut, status_code=201)
def create_subcategory(
    payload: SubcategoryCreateIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from fastapi import HTTPException, status
    
    # Check for uniqueness
    existing = db.query(UserSubcategory).filter(
        UserSubcategory.owner_id == current_user.id,
        UserSubcategory.category == payload.category,
        func.lower(UserSubcategory.name) == payload.name.lower()
    ).first()
    
    if existing:
        if existing.is_deleted:
            # Revive it
            existing.is_deleted = False
            existing.is_active = True
            existing.name = payload.name
            db.commit()
            db.refresh(existing)
            return existing
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Subcategory with this name already exists in this category."
            )
            
    new_subcat = UserSubcategory(
        owner_id=current_user.id,
        category=payload.category,
        name=payload.name,
        is_active=True,
    )
    db.add(new_subcat)
    db.commit()
    db.refresh(new_subcat)
    return new_subcat

@router.patch("/{subcategory_id}", response_model=UserSubcategoryOut)
def update_subcategory(
    subcategory_id: int,
    payload: SubcategoryUpdateIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Rename or archive a global taxonomy tag.
    Renaming requires the new name to be unique within the user's tags for that parent category.
    """
    from fastapi import HTTPException, status
    
    # 1. Fetch and Verify Ownership
    subcategory = db.query(UserSubcategory).filter(
        UserSubcategory.id == subcategory_id,
        UserSubcategory.owner_id == current_user.id
    ).first()
    
    if not subcategory:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subcategory not found.")

    # 2. Check Name Collision if renaming
    if payload.name is not None:
        new_name = payload.name.strip()
        if new_name.lower() != subcategory.name.lower():
            # They are attempting to change the name to something different
            # Is the new name already taken in the SAME category?
            collision = db.query(UserSubcategory).filter(
                UserSubcategory.owner_id == current_user.id,
                UserSubcategory.category == subcategory.category,
                func.lower(UserSubcategory.name) == new_name.lower(),
                UserSubcategory.id != subcategory_id
            ).first()
            
            if collision:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="A subcategory with this name already exists in this category."
                )
            subcategory.name = new_name

    # 3. Handle Active Toggle (Archive/Restore)
    if payload.is_active is not None:
        subcategory.is_active = payload.is_active

    db.commit()
    db.refresh(subcategory)
    return subcategory

@router.delete("/{subcategory_id}", status_code=204)
def delete_subcategory(
    subcategory_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Delete a global taxonomy tag.
    Performs a Hard Delete if there are zero historical transactions.
    Performs a Soft Delete if the tag is tied to voided or draft transactions.
    """
    from fastapi import HTTPException, status
    
    # 1. Fetch and Verify Ownership
    subcategory = db.query(UserSubcategory).filter(
        UserSubcategory.id == subcategory_id,
        UserSubcategory.owner_id == current_user.id
    ).first()
    
    if not subcategory:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subcategory not found.")

    # 2. Safety Check: Count EntityLedger usage
    usage_count = db.query(func.count(EntityLedger.id)).filter(
        EntityLedger.subcategory_id == subcategory_id
    ).scalar()

    if usage_count == 0:
        # 3a. Hard Deletion (Pristine tag)
        db.delete(subcategory)
    else:
        # 3b. Soft Deletion (Tag with voided/drafts)
        subcategory.is_deleted = True

    db.commit()
    return None


@router.post("/merge", status_code=200)
def merge_subcategories(
    payload: SubcategoryMergeIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Merge one or more source taxonomy tags into a target tag.
    All historical EntityLedger records attached to sources are reassigned to the target.
    Source tags are then permanently deleted.
    Target and sources must belong to the same parent ExpenseCategory.
    """
    from fastapi import HTTPException, status
    
    # 1. Basic sanity checks
    if payload.target_id in payload.source_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Target ID cannot be included in source IDs."
        )

    # Deduplicate sources
    unique_source_ids = list(set(payload.source_ids))

    # 2. Fetch the target
    target = db.query(UserSubcategory).filter(
        UserSubcategory.id == payload.target_id,
        UserSubcategory.owner_id == current_user.id
    ).first()

    if not target:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Target subcategory not found."
        )

    # 3. Fetch the sources
    sources = db.query(UserSubcategory).filter(
        UserSubcategory.id.in_(unique_source_ids),
        UserSubcategory.owner_id == current_user.id
    ).all()

    if len(sources) != len(unique_source_ids):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="One or more source subcategories not found or access denied."
        )

    # 4. Enforce category matching
    for source in sources:
        if source.category != target.category:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Source tag '{source.name}' belongs to a different category than target tag '{target.name}'."
            )

    try:
        # 5. Transactional reassignment
        # Update all EntityLedger rows that point to any of the source IDs to point to the target ID
        db.query(EntityLedger).filter(
            EntityLedger.subcategory_id.in_(unique_source_ids)
        ).update(
            {"subcategory_id": target.id},
            synchronize_session=False
        )

        # 6. Delete the source tags
        # Because we cascade delete, associated MonthlySubcategoryPlan limits will also be deleted.
        for source in sources:
            db.delete(source)

        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred during merge: {str(e)}"
        )

    return {"detail": "Merge successful"}
