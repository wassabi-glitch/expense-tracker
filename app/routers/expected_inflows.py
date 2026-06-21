from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app import models, oauth2, schemas
from app.session import get_db
from app.services import expected_inflow_service as service
from app.timezone import get_effective_user_timezone, today_in_tz


router = APIRouter(prefix="/expected-inflows", tags=["Expected Inflows"])


def _today(user_tz) -> date:
    return today_in_tz(user_tz)


def _serialize(
    db: Session,
    owner_id: int,
    promise_id: int,
    today: date,
    *,
    include_detail: bool = True,
) -> schemas.ExpectedInflowPromiseOut:
    promise = service.get_promise_or_404(db, owner_id, promise_id)
    return service.serialize_promise(promise, today=today, include_detail=include_detail)


@router.get("", response_model=list[schemas.ExpectedInflowPromiseOut])
def list_expected_inflows(
    budget_year: int | None = Query(default=None, ge=schemas.MIN_BUDGET_YEAR),
    budget_month: int | None = Query(default=None, ge=1, le=12),
    view: Literal["all", "active", "history"] = "all",
    kind: models.ExpectedInflowKind | None = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
    user_tz=Depends(get_effective_user_timezone),
):
    return service.list_promises(
        db,
        current_user.id,
        today=_today(user_tz),
        budget_year=budget_year,
        budget_month=budget_month,
        view=view,
        kind=kind,
    )


@router.get("/timeline", response_model=list[schemas.ExpectedInflowTimelineItemOut])
def expected_inflow_timeline(
    start_date: date,
    end_date: date,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
    user_tz=Depends(get_effective_user_timezone),
):
    today = _today(user_tz)
    promises = service.promise_query(db).filter(
        models.ExpectedInflowPromise.owner_id == current_user.id,
    ).all()
    items: list[schemas.ExpectedInflowTimelineItemOut] = []
    for promise in promises:
        for schedule in promise.schedules:
            if not (start_date <= schedule.due_date <= end_date):
                continue
            state = service._schedule_state(schedule)
            remaining = service.remaining_amount(schedule)
            items.append(schemas.ExpectedInflowTimelineItemOut(
                id=int(schedule.id),
                kind=service._promise_kind(promise),
                source_label=service._promise_source_label(promise),
                due_date=schedule.due_date,
                expected_amount=int(schedule.amount),
                received_amount=service.received_amount(schedule),
                remaining_amount=remaining,
                status=state,
                backing_eligible=bool(promise.backing_eligible),
                is_overdue=service._schedule_is_active(schedule) and schedule.due_date < today,
            ))
    return sorted(items, key=lambda item: (item.due_date, item.id))


@router.post("", response_model=schemas.ExpectedInflowPromiseOut, status_code=status.HTTP_201_CREATED)
def create_expected_inflow(
    payload: schemas.ExpectedInflowCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
    user_tz=Depends(get_effective_user_timezone),
):
    today = _today(user_tz)
    promise, _ = service.create_promise(db, current_user.id, payload, today=today)
    promise_id = int(promise.id)
    db.commit()
    return _serialize(db, current_user.id, promise_id, today)


@router.get("/{promise_id}", response_model=schemas.ExpectedInflowPromiseOut)
def get_expected_inflow(
    promise_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
    user_tz=Depends(get_effective_user_timezone),
):
    return _serialize(db, current_user.id, promise_id, _today(user_tz))


@router.patch("/{promise_id}", response_model=schemas.ExpectedInflowPromiseOut)
def update_expected_inflow(
    promise_id: int,
    payload: schemas.ExpectedInflowUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
    user_tz=Depends(get_effective_user_timezone),
):
    today = _today(user_tz)
    promise = service.get_promise_or_404(db, current_user.id, promise_id, lock=True)
    service.update_promise(db, promise, payload, today=today)
    db.commit()
    return _serialize(db, current_user.id, promise_id, today)


@router.post("/{promise_id}/realize", response_model=schemas.ExpectedInflowRealizeOut)
def realize_expected_inflow(
    promise_id: int,
    payload: schemas.ExpectedInflowRealizeCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
    user_tz=Depends(get_effective_user_timezone),
):
    today = _today(user_tz)
    realization, promise = service.realize_promise(
        db,
        current_user.id,
        promise_id,
        payload,
        today=today,
    )
    realization_id = int(realization.id)
    db.commit()
    realization = db.query(models.ExpectedInflowRealization).filter(
        models.ExpectedInflowRealization.id == realization_id,
        models.ExpectedInflowRealization.owner_id == current_user.id,
    ).first()
    output = _serialize(db, current_user.id, int(promise.id), today)
    realization_output = schemas.ExpectedInflowRealizationOut(
        id=int(realization.id),
        actual_amount=int(realization.actual_amount),
        received_date=realization.received_date,
        note=realization.note,
        event_ids=sorted(int(link.financial_event_id) for link in realization.event_links),
        created_at=realization.created_at,
    )
    return schemas.ExpectedInflowRealizeOut(
        realization=realization_output,
        inflow=output,
        inflows=[output],
    )


@router.post("/{promise_id}/reschedule", response_model=schemas.ExpectedInflowRescheduleOut)
def reschedule_expected_inflow(
    promise_id: int,
    payload: schemas.ExpectedInflowRescheduleCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
    user_tz=Depends(get_effective_user_timezone),
):
    today = _today(user_tz)
    promise, replacements = service.reschedule_promise(
        db,
        current_user.id,
        promise_id,
        payload,
        today=today,
    )
    promise_id = int(promise.id)
    replacement_ids = [int(schedule.id) for schedule in replacements]
    db.commit()
    reloaded = service.get_promise_or_404(db, current_user.id, promise_id)
    replacement_by_id = {int(schedule.id): schedule for schedule in reloaded.schedules}
    return schemas.ExpectedInflowRescheduleOut(
        source=service.serialize_promise(reloaded, today=today),
        replacements=[service._serialize_schedule(replacement_by_id[item_id], today=today) for item_id in replacement_ids],
    )


@router.post("/{promise_id}/cancel", response_model=schemas.ExpectedInflowPromiseOut)
def cancel_expected_inflow(
    promise_id: int,
    payload: schemas.ExpectedInflowCloseCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
    user_tz=Depends(get_effective_user_timezone),
):
    today = _today(user_tz)
    promise = service.get_promise_or_404(db, current_user.id, promise_id, lock=True)
    service.cancel_promise(promise, payload)
    db.commit()
    return _serialize(db, current_user.id, promise_id, today)


@router.post("/{promise_id}/write-off", response_model=schemas.ExpectedInflowPromiseOut)
def write_off_expected_inflow(
    promise_id: int,
    payload: schemas.ExpectedInflowWriteOffCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
    user_tz=Depends(get_effective_user_timezone),
):
    today = _today(user_tz)
    service.write_off_promise(db, current_user.id, promise_id, payload, today=today)
    db.commit()
    return _serialize(db, current_user.id, promise_id, today)


@router.post("/{promise_id}/write-offs/{write_off_id}/reverse", response_model=schemas.ExpectedInflowPromiseOut)
def reverse_expected_inflow_write_off(
    promise_id: int,
    write_off_id: int,
    payload: schemas.ExpectedInflowWriteOffReverseCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
    user_tz=Depends(get_effective_user_timezone),
):
    today = _today(user_tz)
    service.reverse_write_off(db, current_user.id, promise_id, write_off_id, payload)
    db.commit()
    return _serialize(db, current_user.id, promise_id, today)


@router.post("/{promise_id}/reopen", response_model=schemas.ExpectedInflowPromiseOut)
def reopen_expected_inflow(
    promise_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
    user_tz=Depends(get_effective_user_timezone),
):
    today = _today(user_tz)
    promise = service.get_promise_or_404(db, current_user.id, promise_id, lock=True)
    service.reopen_promise(promise)
    db.commit()
    return _serialize(db, current_user.id, promise_id, today)


@router.post("/{promise_id}/reconcile", response_model=schemas.ExpectedInflowPromiseOut)
def reconcile_expected_inflow(
    promise_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
    user_tz=Depends(get_effective_user_timezone),
):
    today = _today(user_tz)
    promise = service.get_promise_or_404(db, current_user.id, promise_id, lock=True)
    service.reconcile_promise(promise)
    db.commit()
    return _serialize(db, current_user.id, promise_id, today)


@router.delete("/{promise_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_expected_inflow(
    promise_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
):
    promise = service.get_promise_or_404(db, current_user.id, promise_id, lock=True)
    service.delete_promise(db, promise)
    db.commit()
