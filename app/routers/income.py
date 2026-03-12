from datetime import date, tzinfo
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from .. import models, oauth2, schemas
from ..session import get_db
from app.timezone import get_effective_user_timezone, today_in_tz
from app.redis_rate_limiter import consume_token_bucket

INCOME_SOURCE_LIMIT = 20
INCOME_ENTRY_MONTH_LIMIT = 300
INCOME_SOURCE_WRITE_BUCKET_CAPACITY = 10
INCOME_SOURCE_WRITE_REFILL_RATE = 10 / 60
INCOME_ENTRY_WRITE_BUCKET_CAPACITY = 20
INCOME_ENTRY_WRITE_REFILL_RATE = 20 / 60

router = APIRouter(
    prefix="/income",
    tags=["Income"],
)


def _rate_limit_headers(rl) -> dict[str, str]:
    return {
        "X-RateLimit-Limit": str(rl.limit),
        "X-RateLimit-Remaining": str(rl.remaining),
        "X-RateLimit-Reset": str(rl.reset_seconds),
    }


def enforce_income_source_write_rate_limit(user_id: int) -> dict[str, str]:
    rl = consume_token_bucket(
        scope="income_sources_write",
        identifier=str(user_id),
        capacity=INCOME_SOURCE_WRITE_BUCKET_CAPACITY,
        refill_rate_per_second=INCOME_SOURCE_WRITE_REFILL_RATE,
    )
    headers = _rate_limit_headers(rl)
    if not rl.allowed:
        headers["Retry-After"] = str(rl.reset_seconds)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="income.sources_write_rate_limited",
            headers=headers,
        )
    return headers


def enforce_income_entry_write_rate_limit(user_id: int) -> dict[str, str]:
    rl = consume_token_bucket(
        scope="income_entries_write",
        identifier=str(user_id),
        capacity=INCOME_ENTRY_WRITE_BUCKET_CAPACITY,
        refill_rate_per_second=INCOME_ENTRY_WRITE_REFILL_RATE,
    )
    headers = _rate_limit_headers(rl)
    if not rl.allowed:
        headers["Retry-After"] = str(rl.reset_seconds)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="income.entries_write_rate_limited",
            headers=headers,
        )
    return headers


def _get_owned_source_or_404(db: Session, user_id: int, source_id: int) -> models.IncomeSource:
    source = (
        db.query(models.IncomeSource)
        .filter(
            models.IncomeSource.id == source_id,
            models.IncomeSource.owner_id == user_id,
        )
        .first()
    )
    if not source:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="income.source_not_found")
    return source


def _ensure_source_belongs_to_user(db: Session, user_id: int, source_id: int | None) -> None:
    if source_id is None:
        return
    source = _get_owned_source_or_404(db, user_id, source_id)
    if not source.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="income.source_inactive")


def _get_owned_entry_or_404(db: Session, user_id: int, entry_id: int) -> models.IncomeEntry:
    entry = (
        db.query(models.IncomeEntry)
        .filter(
            models.IncomeEntry.id == entry_id,
            models.IncomeEntry.owner_id == user_id,
        )
        .first()
    )
    if not entry:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="income.entry_not_found")
    return entry


def _validate_entry_date_in_current_month(entry_date: date, today: date) -> None:
    month_start = today.replace(day=1)
    if entry_date < month_start or entry_date > today:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="income.date_outside_current_month",
        )


@router.get("/sources", response_model=List[schemas.IncomeSourceOut])
def list_income_sources(
    include_inactive: bool = Query(default=False),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
):
    query = db.query(models.IncomeSource).filter(models.IncomeSource.owner_id == current_user.id)
    if not include_inactive:
        query = query.filter(models.IncomeSource.is_active.is_(True))
    return query.order_by(models.IncomeSource.created_at.desc()).all()


@router.post("/sources", response_model=schemas.IncomeSourceOut, status_code=status.HTTP_201_CREATED)
def create_income_source(
    payload: schemas.IncomeSourceCreate,
    response: Response,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
):
    rate_headers = enforce_income_source_write_rate_limit(current_user.id)
    for k, v in rate_headers.items():
        response.headers[k] = v

    source_count = (
        db.query(func.count(models.IncomeSource.id))
        .filter(models.IncomeSource.owner_id == current_user.id)
        .scalar()
    ) or 0
    if int(source_count) >= INCOME_SOURCE_LIMIT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="income.source_limit_reached",
        )

    existing = (
        db.query(models.IncomeSource)
        .filter(
            models.IncomeSource.owner_id == current_user.id,
            func.lower(models.IncomeSource.name) == payload.name.lower(),
        )
        .first()
    )
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="income.source_exists")

    source = models.IncomeSource(
        owner_id=current_user.id,
        name=payload.name,
        is_active=True,
    )
    db.add(source)
    db.commit()
    db.refresh(source)
    return source


@router.patch("/sources/{source_id}", response_model=schemas.IncomeSourceOut)
def update_income_source(
    source_id: int,
    payload: schemas.IncomeSourceUpdate,
    response: Response,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
):
    rate_headers = enforce_income_source_write_rate_limit(current_user.id)
    for k, v in rate_headers.items():
        response.headers[k] = v
    source = _get_owned_source_or_404(db, current_user.id, source_id)

    duplicate = (
        db.query(models.IncomeSource)
        .filter(
            models.IncomeSource.owner_id == current_user.id,
            models.IncomeSource.id != source.id,
            func.lower(models.IncomeSource.name) == payload.name.lower(),
        )
        .first()
    )
    if duplicate:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="income.source_exists")

    source.name = payload.name
    source.is_active = True
    db.commit()
    db.refresh(source)
    return source


@router.delete("/sources/{source_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_income_source(
    source_id: int,
    response: Response,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
):
    rate_headers = enforce_income_source_write_rate_limit(current_user.id)
    for k, v in rate_headers.items():
        response.headers[k] = v
    source = _get_owned_source_or_404(db, current_user.id, source_id)
    db.delete(source)
    db.commit()
    response.status_code = status.HTTP_204_NO_CONTENT
    return None


@router.patch("/sources/{source_id}/active", response_model=schemas.IncomeSourceOut)
def update_income_source_active_state(
    source_id: int,
    payload: schemas.IncomeSourceStatusUpdate,
    response: Response,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
):
    rate_headers = enforce_income_source_write_rate_limit(current_user.id)
    for k, v in rate_headers.items():
        response.headers[k] = v
    source = _get_owned_source_or_404(db, current_user.id, source_id)
    source.is_active = payload.is_active
    db.commit()
    db.refresh(source)
    return source


@router.get("/entries", response_model=schemas.PaginatedIncomeEntriesOut)
def list_income_entries(
    limit: int = Query(default=20, ge=1, le=100),
    skip: int = Query(default=0, ge=0),
    source_id: int | None = Query(default=None),
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
):
    if (start_date is None) ^ (end_date is None):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="income.date_range_both_required")
    if start_date and end_date and start_date > end_date:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="income.start_after_end")

    query = db.query(models.IncomeEntry).filter(models.IncomeEntry.owner_id == current_user.id)
    if source_id is not None:
        _get_owned_source_or_404(db, current_user.id, source_id)
        query = query.filter(models.IncomeEntry.source_id == source_id)
    if start_date is not None:
        query = query.filter(models.IncomeEntry.date >= start_date)
    if end_date is not None:
        query = query.filter(models.IncomeEntry.date <= end_date)

    total = query.count()
    items = (
        query.order_by(models.IncomeEntry.date.desc(), models.IncomeEntry.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return {"total": total, "items": items}


@router.post("/entries", response_model=schemas.IncomeEntryOut, status_code=status.HTTP_201_CREATED)
def create_income_entry(
    payload: schemas.IncomeEntryCreate,
    response: Response,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
    user_tz: tzinfo = Depends(get_effective_user_timezone),
):
    today = today_in_tz(user_tz)
    current_month_start = today.replace(day=1)
    rate_headers = enforce_income_entry_write_rate_limit(current_user.id)
    for k, v in rate_headers.items():
        response.headers[k] = v

    _validate_entry_date_in_current_month(payload.date, today)
    _ensure_source_belongs_to_user(db, current_user.id, payload.source_id)

    month_entry_count = (
        db.query(func.count(models.IncomeEntry.id))
        .filter(
            models.IncomeEntry.owner_id == current_user.id,
            models.IncomeEntry.date >= current_month_start,
            models.IncomeEntry.date <= today,
        )
        .scalar()
    ) or 0
    if int(month_entry_count) >= INCOME_ENTRY_MONTH_LIMIT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="income.entry_month_limit_reached",
        )

    entry = models.IncomeEntry(
        owner_id=current_user.id,
        source_id=payload.source_id,
        amount=payload.amount,
        note=payload.note,
        date=payload.date,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


@router.put("/entries/{entry_id}", response_model=schemas.IncomeEntryOut)
def update_income_entry(
    entry_id: int,
    payload: schemas.IncomeEntryUpdate,
    response: Response,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
    user_tz: tzinfo = Depends(get_effective_user_timezone),
):
    rate_headers = enforce_income_entry_write_rate_limit(current_user.id)
    for k, v in rate_headers.items():
        response.headers[k] = v
    _validate_entry_date_in_current_month(payload.date, today_in_tz(user_tz))
    _ensure_source_belongs_to_user(db, current_user.id, payload.source_id)
    entry = _get_owned_entry_or_404(db, current_user.id, entry_id)

    entry.source_id = payload.source_id
    entry.amount = payload.amount
    entry.note = payload.note
    entry.date = payload.date

    db.commit()
    db.refresh(entry)
    return entry


@router.delete("/entries/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_income_entry(
    entry_id: int,
    response: Response,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
):
    rate_headers = enforce_income_entry_write_rate_limit(current_user.id)
    for k, v in rate_headers.items():
        response.headers[k] = v
    entry = _get_owned_entry_or_404(db, current_user.id, entry_id)
    db.delete(entry)
    db.commit()
    response.status_code = status.HTTP_204_NO_CONTENT
    return None
