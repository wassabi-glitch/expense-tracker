from datetime import tzinfo
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.redis_rate_limiter import consume_token_bucket
from app.timezone import get_effective_user_timezone, today_in_tz

from .. import models, oauth2, schemas
from ..services.budget_service import get_budget_remaining_for_month, get_owned_project_or_404, get_project_budget_summaries
from ..services.category_policy import validate_active_expense_category
from ..services.project_service import (
    build_project_detail,
    get_owned_project_subcategory_or_404,
    latest_project_event_date,
    validate_project_completion_date,
    validate_project_editable,
    validate_project_limit_sum,
    validate_project_subcategory_limit_sum,
    validate_project_subcategory_rules,
    validate_project_update_rules,
)
from ..session import get_db

router = APIRouter(
    prefix="/projects",
    tags=["Projects"],
)

PROJECT_WRITE_BUCKET_CAPACITY = 10
PROJECT_WRITE_REFILL_RATE = 10 / 60


def enforce_project_write_rate_limit(user_id: int) -> dict[str, str]:
    rl = consume_token_bucket(
        scope="projects_write",
        identifier=str(user_id),
        capacity=PROJECT_WRITE_BUCKET_CAPACITY,
        refill_rate_per_second=PROJECT_WRITE_REFILL_RATE,
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
            detail="projects.write_rate_limited",
            headers=headers,
        )
    return headers


def _apply_headers(response: Response, headers: dict[str, str]) -> None:
    for key, value in headers.items():
        response.headers[key] = value


def _get_owned_goal_or_404(db: Session, user_id: int, goal_id: int) -> models.Goals:
    goal = db.query(models.Goals).filter(models.Goals.id == goal_id, models.Goals.owner_id == user_id).first()
    if not goal:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="goals.not_found")
    return goal


def _project_detail_out(db: Session, current_user_id: int, project_id: int) -> schemas.ProjectBudgetOut:
    summaries = {item.id: item for item in get_project_budget_summaries(db, current_user_id)}
    summary = summaries.get(project_id)
    if summary is None:
        project = get_owned_project_or_404(db, current_user_id, project_id)
        return build_project_detail(project, 0, [])
    return summary


def _validate_non_isolated_category_limit(
    db: Session,
    current_user_id: int,
    project: models.Project,
    category: models.ExpenseCategory,
    limit_amount: int,
) -> None:
    if project.is_isolated:
        return
    remaining = get_budget_remaining_for_month(
        db,
        current_user_id,
        category,
        int(project.start_date.year),
        int(project.start_date.month),
    )
    if int(limit_amount) > int(remaining):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="projects.non_isolated_category_limit_exceeds_budget_remaining",
        )


@router.post("", response_model=schemas.ProjectBudgetOut, status_code=status.HTTP_201_CREATED)
def create_project(
    payload: schemas.ProjectCreate,
    response: Response,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
):
    _apply_headers(response, enforce_project_write_rate_limit(current_user.id))

    if payload.origin_goal_id is not None:
        _get_owned_goal_or_404(db, current_user.id, payload.origin_goal_id)
        existing = (
            db.query(models.Project.id)
            .filter(
                models.Project.owner_id == current_user.id,
                models.Project.origin_goal_id == payload.origin_goal_id,
            )
            .first()
        )
        if existing:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="goals.project_already_exists")

    project = models.Project(
        owner_id=current_user.id,
        title=payload.title,
        description=payload.description,
        is_isolated=payload.is_isolated,
        origin_goal_id=payload.origin_goal_id,
        total_limit=payload.total_limit,
        status=models.ProjectStatus.ACTIVE,
        start_date=payload.start_date,
        target_end_date=payload.target_end_date,
    )
    db.add(project)
    db.commit()
    return _project_detail_out(db, current_user.id, project.id)


@router.get("", response_model=List[schemas.ProjectBudgetOut])
def list_projects(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
):
    return get_project_budget_summaries(db, current_user.id)


@router.get("/{project_id}", response_model=schemas.ProjectBudgetOut)
def get_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
):
    get_owned_project_or_404(db, current_user.id, project_id)
    return _project_detail_out(db, current_user.id, project_id)


@router.put("/{project_id}", response_model=schemas.ProjectBudgetOut)
def update_project(
    project_id: int,
    payload: schemas.ProjectUpdate,
    response: Response,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
):
    _apply_headers(response, enforce_project_write_rate_limit(current_user.id))
    project = get_owned_project_or_404(db, current_user.id, project_id)
    validate_project_editable(project)
    update_data = payload.model_dump(exclude_unset=True)

    next_is_isolated = update_data.get("is_isolated", project.is_isolated)
    next_total_limit = update_data.get("total_limit", project.total_limit)
    next_start_date = update_data.get("start_date", project.start_date)
    next_target_end_date = update_data.get("target_end_date", project.target_end_date)
    validate_project_update_rules(
        db,
        project,
        next_is_isolated=bool(next_is_isolated),
        next_total_limit=int(next_total_limit) if next_total_limit is not None else None,
        next_start_date=next_start_date,
        next_target_end_date=next_target_end_date,
    )

    for field, value in update_data.items():
        setattr(project, field, value)
    db.commit()
    return _project_detail_out(db, current_user.id, project.id)


@router.post("/{project_id}/stop", response_model=schemas.ProjectBudgetOut)
def stop_project(
    project_id: int,
    response: Response,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
):
    _apply_headers(response, enforce_project_write_rate_limit(current_user.id))
    project = get_owned_project_or_404(db, current_user.id, project_id)
    if project.status != models.ProjectStatus.ACTIVE:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="projects.stop_invalid_state")
    project.status = models.ProjectStatus.STOPPED
    db.commit()
    return _project_detail_out(db, current_user.id, project.id)


@router.post("/{project_id}/resume", response_model=schemas.ProjectBudgetOut)
def resume_project(
    project_id: int,
    response: Response,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
):
    _apply_headers(response, enforce_project_write_rate_limit(current_user.id))
    project = get_owned_project_or_404(db, current_user.id, project_id)
    if project.status != models.ProjectStatus.STOPPED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="projects.resume_invalid_state")
    project.status = models.ProjectStatus.ACTIVE
    db.commit()
    return _project_detail_out(db, current_user.id, project.id)


@router.post("/{project_id}/complete", response_model=schemas.ProjectBudgetOut)
def complete_project(
    project_id: int,
    payload: schemas.ProjectLifecycleRequest,
    response: Response,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
    user_tz: tzinfo = Depends(get_effective_user_timezone),
):
    _apply_headers(response, enforce_project_write_rate_limit(current_user.id))
    project = get_owned_project_or_404(db, current_user.id, project_id)
    effective_date = payload.effective_date or today_in_tz(user_tz)
    validate_project_completion_date(project, effective_date)
    latest_linked = latest_project_event_date(db, project.id)
    if latest_linked is not None and effective_date < latest_linked:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="projects.completed_before_linked_expense")
    project.status = models.ProjectStatus.COMPLETED
    project.completed_at = effective_date
    db.commit()
    return _project_detail_out(db, current_user.id, project.id)


@router.post("/{project_id}/archive", response_model=schemas.ProjectBudgetOut)
def archive_project(
    project_id: int,
    response: Response,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
):
    _apply_headers(response, enforce_project_write_rate_limit(current_user.id))
    project = get_owned_project_or_404(db, current_user.id, project_id)
    project.status = models.ProjectStatus.ARCHIVED
    db.commit()
    return _project_detail_out(db, current_user.id, project.id)


@router.post("/{project_id}/reopen", response_model=schemas.ProjectBudgetOut)
def reopen_project(
    project_id: int,
    response: Response,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
):
    _apply_headers(response, enforce_project_write_rate_limit(current_user.id))
    project = get_owned_project_or_404(db, current_user.id, project_id)
    if project.status == models.ProjectStatus.ACTIVE:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="projects.already_active")
    project.status = models.ProjectStatus.ACTIVE
    project.completed_at = None
    db.commit()
    return _project_detail_out(db, current_user.id, project.id)


@router.post("/{project_id}/category-limits", response_model=schemas.ProjectBudgetOut, status_code=status.HTTP_201_CREATED)
def create_project_category_limit(
    project_id: int,
    payload: schemas.ProjectCategoryLimitCreate,
    response: Response,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
):
    _apply_headers(response, enforce_project_write_rate_limit(current_user.id))
    validate_active_expense_category(
        payload.category,
        error_detail="projects.validation.real_expense_category_required",
    )
    project = get_owned_project_or_404(db, current_user.id, project_id)
    validate_project_editable(project)
    existing = next((item for item in project.category_limits if item.category == payload.category), None)
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="projects.category_limit_exists")
    _validate_non_isolated_category_limit(db, current_user.id, project, payload.category, payload.limit_amount)
    validate_project_limit_sum(
        int(project.total_limit) if project.total_limit is not None else None,
        list(project.category_limits),
        incoming_limit=payload.limit_amount,
    )
    db.add(
        models.ProjectCategoryLimit(
            project_id=project.id,
            category=payload.category,
            limit_amount=payload.limit_amount,
        )
    )
    db.commit()
    return _project_detail_out(db, current_user.id, project.id)


@router.put("/{project_id}/category-limits/{category}", response_model=schemas.ProjectBudgetOut)
def update_project_category_limit(
    project_id: int,
    category: models.ExpenseCategory,
    payload: schemas.ProjectCategoryLimitUpdate,
    response: Response,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
):
    _apply_headers(response, enforce_project_write_rate_limit(current_user.id))
    project = get_owned_project_or_404(db, current_user.id, project_id)
    validate_project_editable(project)
    limit_row = next((item for item in project.category_limits if item.category == category), None)
    if limit_row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="projects.category_limit_not_found")
    _validate_non_isolated_category_limit(db, current_user.id, project, category, payload.limit_amount)
    validate_project_limit_sum(
        int(project.total_limit) if project.total_limit is not None else None,
        list(project.category_limits),
        incoming_limit=payload.limit_amount,
        exclude_category=category,
    )
    limit_row.limit_amount = payload.limit_amount
    db.commit()
    return _project_detail_out(db, current_user.id, project.id)


@router.delete("/{project_id}/category-limits/{category}", response_model=schemas.ProjectBudgetOut)
def delete_project_category_limit(
    project_id: int,
    category: models.ExpenseCategory,
    response: Response,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
):
    _apply_headers(response, enforce_project_write_rate_limit(current_user.id))
    project = get_owned_project_or_404(db, current_user.id, project_id)
    validate_project_editable(project)
    limit_row = next((item for item in project.category_limits if item.category == category), None)
    if limit_row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="projects.category_limit_not_found")
    if any(item.category == category for item in project.subcategories):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="projects.category_limit_has_subcategories")
    db.delete(limit_row)
    db.commit()
    return _project_detail_out(db, current_user.id, project.id)


@router.get("/{project_id}/subcategories", response_model=List[schemas.ProjectSubcategoryOut])
def list_project_subcategories(
    project_id: int,
    category: models.ExpenseCategory | None = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
):
    project = get_owned_project_or_404(db, current_user.id, project_id)
    rows = list(project.subcategories)
    if category is not None:
        rows = [item for item in rows if item.category == category]
    return [
        schemas.ProjectSubcategoryOut(
            id=item.id,
            project_id=item.project_id,
            category=item.category,
            name=item.name,
            is_active=bool(item.is_active),
            limit_amount=int(item.limit_amount) if item.limit_amount is not None else None,
            spent=0,
            remaining=int(item.limit_amount) if item.limit_amount is not None else None,
            is_over_limit=False,
            created_at=item.created_at,
            updated_at=item.updated_at,
        )
        for item in sorted(rows, key=lambda value: (str(value.category), value.name.lower()))
    ]


@router.post("/{project_id}/subcategories", response_model=schemas.ProjectBudgetOut, status_code=status.HTTP_201_CREATED)
def create_project_subcategory(
    project_id: int,
    payload: schemas.ProjectSubcategoryCreate,
    response: Response,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
):
    _apply_headers(response, enforce_project_write_rate_limit(current_user.id))
    validate_active_expense_category(
        payload.category,
        error_detail="projects.validation.real_expense_category_required",
    )
    project = get_owned_project_or_404(db, current_user.id, project_id)
    validate_project_editable(project)
    validate_project_subcategory_rules(project, payload.category)
    existing = next(
        (item for item in project.subcategories if item.category == payload.category and item.name.lower() == payload.name.lower()),
        None,
    )
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="projects.subcategory_exists")
    validate_project_subcategory_limit_sum(project, payload.category, payload.limit_amount)
    db.add(
        models.ProjectSubcategory(
            project_id=project.id,
            category=payload.category,
            name=payload.name,
            is_active=payload.is_active,
            limit_amount=payload.limit_amount,
        )
    )
    db.commit()
    return _project_detail_out(db, current_user.id, project.id)


@router.put("/{project_id}/subcategories/{subcategory_id}", response_model=schemas.ProjectBudgetOut)
def update_project_subcategory(
    project_id: int,
    subcategory_id: int,
    payload: schemas.ProjectSubcategoryUpdate,
    response: Response,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
):
    _apply_headers(response, enforce_project_write_rate_limit(current_user.id))
    project = get_owned_project_or_404(db, current_user.id, project_id)
    validate_project_editable(project)
    subcategory = get_owned_project_subcategory_or_404(db, current_user.id, project_id, subcategory_id)
    validate_project_subcategory_rules(project, subcategory.category)
    next_name = payload.name if payload.name is not None else subcategory.name
    duplicate = next(
        (
            item for item in project.subcategories
            if item.id != subcategory.id
            and item.category == subcategory.category
            and item.name.lower() == next_name.lower()
        ),
        None,
    )
    if duplicate:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="projects.subcategory_exists")
    next_limit_amount = payload.limit_amount if "limit_amount" in payload.model_fields_set else subcategory.limit_amount
    validate_project_subcategory_limit_sum(project, subcategory.category, next_limit_amount, exclude_subcategory_id=subcategory.id)
    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(subcategory, field, value)
    db.commit()
    return _project_detail_out(db, current_user.id, project.id)


@router.delete("/{project_id}/subcategories/{subcategory_id}", response_model=schemas.ProjectBudgetOut)
def delete_project_subcategory(
    project_id: int,
    subcategory_id: int,
    response: Response,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
):
    _apply_headers(response, enforce_project_write_rate_limit(current_user.id))
    project = get_owned_project_or_404(db, current_user.id, project_id)
    validate_project_editable(project)
    subcategory = get_owned_project_subcategory_or_404(db, current_user.id, project_id, subcategory_id)
    db.delete(subcategory)
    db.commit()
    return _project_detail_out(db, current_user.id, project.id)
