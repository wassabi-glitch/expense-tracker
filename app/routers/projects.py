from datetime import tzinfo
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.redis_rate_limiter import consume_token_bucket
from app.timezone import get_effective_user_timezone, today_in_tz

from .. import models, oauth2, schemas
from ..services.budget_service import (
    get_owned_project_or_404,
    get_overlay_project_spent_by_project_subcategory,
    get_project_budget_summaries,
)
from ..services.category_policy import validate_active_expense_category
from ..services.project_service import (
    build_project_detail,
    get_owned_project_subcategory_or_404,
    get_owned_project_subcategory_monthly_limit_or_404,
    latest_project_event_date,
    validate_project_completion_date,
    validate_project_editable,
    validate_project_limit_sum,
    validate_overlay_project_subcategory_reservation,
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


def _project_detail_out(
    db: Session,
    current_user_id: int,
    project_id: int,
    budget_year: int | None = None,
    budget_month: int | None = None,
) -> schemas.ProjectBudgetOut:
    summaries = {
        item.id: item
        for item in get_project_budget_summaries(db, current_user_id, budget_year, budget_month)
    }
    summary = summaries.get(project_id)
    if summary is None:
        project = get_owned_project_or_404(db, current_user_id, project_id)
        return build_project_detail(project, 0, [])
    return summary


def _overlay_reservation_month(
    project: models.Project,
    budget_year: int | None,
    budget_month: int | None,
) -> tuple[int, int]:
    if budget_year is None and budget_month is None:
        return int(project.start_date.year), int(project.start_date.month)
    if budget_year is None or budget_month is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="projects.reservation_month_required")
    return int(budget_year), int(budget_month)


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
    budget_year: int | None = None,
    budget_month: int | None = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
):
    return get_project_budget_summaries(db, current_user.id, budget_year, budget_month)


@router.get("/{project_id}", response_model=schemas.ProjectBudgetOut)
def get_project(
    project_id: int,
    budget_year: int | None = None,
    budget_month: int | None = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
):
    get_owned_project_or_404(db, current_user.id, project_id)
    return _project_detail_out(db, current_user.id, project_id, budget_year, budget_month)


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
    selected_budget_year = payload.budget_year
    selected_budget_month = payload.budget_month
    if project.is_isolated:
        existing = next((item for item in project.category_limits if item.category == payload.category), None)
        if existing:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="projects.category_limit_exists")
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
    else:
        budget_year, budget_month = _overlay_reservation_month(project, payload.budget_year, payload.budget_month)
        selected_budget_year = budget_year
        selected_budget_month = budget_month
        existing = next(
            (
                item
                for item in project.monthly_category_limits
                if item.category == payload.category
                and int(item.budget_year) == budget_year
                and int(item.budget_month) == budget_month
            ),
            None,
        )
        if existing:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="projects.category_limit_exists")
        db.add(
            models.ProjectCategoryMonthlyLimit(
                project_id=project.id,
                category=payload.category,
                budget_year=budget_year,
                budget_month=budget_month,
                limit_amount=payload.limit_amount,
            )
        )
    db.commit()
    return _project_detail_out(db, current_user.id, project.id, selected_budget_year, selected_budget_month)


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
    budget_year = payload.budget_year
    budget_month = payload.budget_month
    if project.is_isolated:
        limit_row = next((item for item in project.category_limits if item.category == category), None)
    else:
        budget_year, budget_month = _overlay_reservation_month(project, payload.budget_year, payload.budget_month)
        limit_row = next(
            (
                item
                for item in project.monthly_category_limits
                if item.category == category
                and int(item.budget_year) == int(budget_year)
                and int(item.budget_month) == int(budget_month)
            ),
            None,
        )
    if limit_row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="projects.category_limit_not_found")
    if project.is_isolated:
        validate_project_limit_sum(
            int(project.total_limit) if project.total_limit is not None else None,
            list(project.category_limits),
            incoming_limit=payload.limit_amount,
            exclude_category=category,
        )
    limit_row.limit_amount = payload.limit_amount
    db.commit()
    return _project_detail_out(db, current_user.id, project.id, budget_year, budget_month)


@router.delete("/{project_id}/category-limits/{category}", response_model=schemas.ProjectBudgetOut)
def delete_project_category_limit(
    project_id: int,
    category: models.ExpenseCategory,
    response: Response,
    budget_year: int | None = None,
    budget_month: int | None = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
):
    _apply_headers(response, enforce_project_write_rate_limit(current_user.id))
    project = get_owned_project_or_404(db, current_user.id, project_id)
    validate_project_editable(project)
    if project.is_isolated:
        limit_row = next((item for item in project.category_limits if item.category == category), None)
    else:
        budget_year, budget_month = _overlay_reservation_month(project, budget_year, budget_month)
        limit_row = next(
            (
                item
                for item in project.monthly_category_limits
                if item.category == category
                and int(item.budget_year) == int(budget_year)
                and int(item.budget_month) == int(budget_month)
            ),
            None,
        )
    if limit_row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="projects.category_limit_not_found")
    if project.is_isolated and any(item.category == category for item in project.subcategories):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="projects.category_limit_has_subcategories")
    if not project.is_isolated:
        (
            db.query(models.ProjectSubcategoryMonthlyLimit)
            .filter(
                models.ProjectSubcategoryMonthlyLimit.project_id == project.id,
                models.ProjectSubcategoryMonthlyLimit.category == category,
                models.ProjectSubcategoryMonthlyLimit.budget_year == budget_year,
                models.ProjectSubcategoryMonthlyLimit.budget_month == budget_month,
            )
            .delete(synchronize_session=False)
        )
    db.delete(limit_row)
    db.commit()
    return _project_detail_out(db, current_user.id, project.id, budget_year, budget_month)


@router.get("/{project_id}/category-limits", response_model=List[schemas.ProjectBudgetCategoryOut])
def list_project_category_limits(
    project_id: int,
    budget_year: int | None = None,
    budget_month: int | None = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
):
    project = get_owned_project_or_404(db, current_user.id, project_id)
    if project.is_isolated:
        return [
            schemas.ProjectBudgetCategoryOut(
                category=item.category,
                limit_amount=int(item.limit_amount),
            )
            for item in sorted(project.category_limits, key=lambda value: str(value.category))
        ]
    if budget_year is not None or budget_month is not None:
        budget_year, budget_month = _overlay_reservation_month(project, budget_year, budget_month)
    rows = list(project.monthly_category_limits)
    if budget_year is not None and budget_month is not None:
        rows = [
            item
            for item in rows
            if int(item.budget_year) == int(budget_year)
            and int(item.budget_month) == int(budget_month)
        ]
    return [
        schemas.ProjectBudgetCategoryOut(
            category=item.category,
            limit_amount=int(item.limit_amount),
            budget_year=int(item.budget_year),
            budget_month=int(item.budget_month),
        )
        for item in sorted(rows, key=lambda value: (value.budget_year, value.budget_month, str(value.category)))
    ]


@router.get("/{project_id}/subcategories", response_model=List[schemas.ProjectSubcategoryOut])
def list_project_subcategories(
    project_id: int,
    category: models.ExpenseCategory | None = None,
    budget_year: int | None = None,
    budget_month: int | None = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
):
    project = get_owned_project_or_404(db, current_user.id, project_id)
    if project.is_isolated:
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

    budget_year, budget_month = _overlay_reservation_month(project, budget_year, budget_month)
    query = (
        db.query(models.ProjectSubcategoryMonthlyLimit)
        .join(models.UserSubcategory, models.UserSubcategory.id == models.ProjectSubcategoryMonthlyLimit.user_subcategory_id)
        .filter(
            models.ProjectSubcategoryMonthlyLimit.project_id == project.id,
            models.ProjectSubcategoryMonthlyLimit.budget_year == budget_year,
            models.ProjectSubcategoryMonthlyLimit.budget_month == budget_month,
        )
    )
    if category is not None:
        query = query.filter(models.ProjectSubcategoryMonthlyLimit.category == category)
    spent_by_subcategory = get_overlay_project_spent_by_project_subcategory(
        db,
        current_user.id,
        budget_year,
        budget_month,
    )
    rows = query.order_by(models.ProjectSubcategoryMonthlyLimit.category.asc(), models.UserSubcategory.name.asc()).all()
    output = []
    for item in rows:
        spent = int(spent_by_subcategory.get((int(item.project_id), int(item.user_subcategory_id)), 0))
        remaining = int(item.limit_amount) - spent
        output.append(
            schemas.ProjectSubcategoryOut(
                id=item.id,
                project_id=item.project_id,
                category=item.category,
                name=item.user_subcategory.name,
                is_active=bool(item.user_subcategory.is_active),
                user_subcategory_id=int(item.user_subcategory_id),
                budget_year=int(item.budget_year),
                budget_month=int(item.budget_month),
                limit_amount=int(item.limit_amount),
                spent=spent,
                remaining=remaining,
                is_over_limit=remaining < 0,
                created_at=item.created_at,
                updated_at=item.updated_at,
            )
        )
    return output


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
    if project.is_isolated:
        if payload.name is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="projects.subcategory_name_required")
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
        selected_budget_year = None
        selected_budget_month = None
    else:
        if payload.user_subcategory_id is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="projects.global_subcategory_required")
        if payload.limit_amount is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="projects.subcategory_limit_required")
        selected_budget_year, selected_budget_month = _overlay_reservation_month(project, payload.budget_year, payload.budget_month)
        validate_overlay_project_subcategory_reservation(
            db,
            current_user.id,
            project,
            category=payload.category,
            user_subcategory_id=int(payload.user_subcategory_id),
            budget_year=selected_budget_year,
            budget_month=selected_budget_month,
            limit_amount=int(payload.limit_amount),
        )
        db.add(
            models.ProjectSubcategoryMonthlyLimit(
                project_id=project.id,
                user_subcategory_id=int(payload.user_subcategory_id),
                category=payload.category,
                budget_year=selected_budget_year,
                budget_month=selected_budget_month,
                limit_amount=int(payload.limit_amount),
            )
        )
    db.commit()
    return _project_detail_out(db, current_user.id, project.id, selected_budget_year, selected_budget_month)


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
    if project.is_isolated:
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
            if field in {"user_subcategory_id", "budget_year", "budget_month", "category"}:
                continue
            setattr(subcategory, field, value)
        selected_budget_year = None
        selected_budget_month = None
    else:
        reservation = get_owned_project_subcategory_monthly_limit_or_404(
            db,
            current_user.id,
            project_id,
            subcategory_id,
        )
        next_category = payload.category if payload.category is not None else reservation.category
        next_user_subcategory_id = (
            payload.user_subcategory_id
            if "user_subcategory_id" in payload.model_fields_set and payload.user_subcategory_id is not None
            else reservation.user_subcategory_id
        )
        next_budget_year = payload.budget_year if payload.budget_year is not None else int(reservation.budget_year)
        next_budget_month = payload.budget_month if payload.budget_month is not None else int(reservation.budget_month)
        next_limit_amount = payload.limit_amount if "limit_amount" in payload.model_fields_set else int(reservation.limit_amount)
        if next_limit_amount is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="projects.subcategory_limit_required")
        validate_overlay_project_subcategory_reservation(
            db,
            current_user.id,
            project,
            category=next_category,
            user_subcategory_id=int(next_user_subcategory_id),
            budget_year=int(next_budget_year),
            budget_month=int(next_budget_month),
            limit_amount=int(next_limit_amount),
            exclude_reservation_id=int(reservation.id),
        )
        reservation.category = next_category
        reservation.user_subcategory_id = int(next_user_subcategory_id)
        reservation.budget_year = int(next_budget_year)
        reservation.budget_month = int(next_budget_month)
        reservation.limit_amount = int(next_limit_amount)
        selected_budget_year = int(next_budget_year)
        selected_budget_month = int(next_budget_month)
    db.commit()
    return _project_detail_out(db, current_user.id, project.id, selected_budget_year, selected_budget_month)


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
    if project.is_isolated:
        subcategory = get_owned_project_subcategory_or_404(db, current_user.id, project_id, subcategory_id)
        selected_budget_year = None
        selected_budget_month = None
    else:
        subcategory = get_owned_project_subcategory_monthly_limit_or_404(
            db,
            current_user.id,
            project_id,
            subcategory_id,
        )
        selected_budget_year = int(subcategory.budget_year)
        selected_budget_month = int(subcategory.budget_month)
    db.delete(subcategory)
    db.commit()
    return _project_detail_out(db, current_user.id, project.id, selected_budget_year, selected_budget_month)
