import logging
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Header, Request, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from .. import oauth2
from .. import models, schemas, utils
from ..session import get_db
from app.redis_rate_limiter import check_and_consume
from app.email_service import send_verification_email
from app.email_verification import build_verify_email_link, issue_email_verification_token
from app.timezone import _safe_zoneinfo
from config import settings

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/users",  # This means you don't have to type "/expenses" in every route!
    tags=['Users']    # This groups them nicely in your /docs page
)

# Used to reduce login timing differences between "user not found" and "bad password".
DUMMY_PASSWORD_HASH = utils.hash_password("dummy-password-not-used")


def _default_income_sources_for_status(life_status: models.LifeStatus) -> list[str]:
    mapping = {
        models.LifeStatus.STUDENT: [
            "Allowance",
            "Scholarship",
            "Part-time work",
        ],
        models.LifeStatus.EMPLOYED: [
            "Salary",
            "Bonus",
            "Side income",
        ],
        models.LifeStatus.SELF_EMPLOYED: [
            "Client payment",
            "Freelance work",
            "Project income",
        ],
        models.LifeStatus.BUSINESS_OWNER: [
            "Business income",
            "Other revenue",
        ],
        models.LifeStatus.UNEMPLOYED: [
            "Support",
            "Temporary income",
            "Other income",
        ],
    }
    return mapping.get(life_status, ["Other income"])


def build_user_out(user: models.User) -> schemas.UserOut:
    profile_out = None
    needs_onboarding = True
    if user.profile is not None:
        profile_out = schemas.UserProfileOut.model_validate(user.profile)
        needs_onboarding = user.profile.onboarding_completed_at is None

    return schemas.UserOut(
        id=user.id,
        username=user.username,
        email=user.email,
        created_at=user.created_at,
        is_premium=user.is_premium,
        needs_onboarding=needs_onboarding,
        profile=profile_out,
    )


def ensure_local_identity(db: Session, user: models.User) -> None:
    identity = (
        db.query(models.UserIdentity)
        .filter(
            models.UserIdentity.user_id == user.id,
            models.UserIdentity.provider == "local",
        )
        .first()
    )
    if identity:
        return

    db.add(
        models.UserIdentity(
            user_id=user.id,
            provider="local",
            provider_user_id=str(user.id),
            provider_email=user.email,
        )
    )
    try:
        db.commit()
    except IntegrityError:
        db.rollback()


@router.post("/sign-up", response_model=schemas.UserOut, status_code=status.HTTP_201_CREATED)
def create_user(
    user: schemas.UserCreate,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    client_ip = request.client.host if request.client else "unknown"
    signup_key = client_ip
    rl = check_and_consume("signup", signup_key)
    rate_headers = {
        "X-RateLimit-Limit": str(rl.limit),
        "X-RateLimit-Remaining": str(rl.remaining),
        "X-RateLimit-Reset": str(rl.reset_seconds),
    }
    for k, v in rate_headers.items():
        response.headers[k] = v

    if not rl.allowed:
        rate_headers["Retry-After"] = str(rl.reset_seconds)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="auth.signup_rate_limited",
            headers=rate_headers,
        )

    # 1. Check if user already exists
    db_user = db.query(models.User).filter(
        models.User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="auth.email_already_registered")
    db_username = db.query(models.User).filter(
        models.User.username == user.username).first()
    if db_username:
        raise HTTPException(status_code=409, detail="auth.username_already_taken")

    # 2. Hash the password using our utility
    hashed_pwd = utils.hash_password(user.password)

    # 3. Create the user object
    new_user = models.User(
        username=user.username,
        email=user.email,
        hashed_password=hashed_pwd
    )

    # 4. Save to Database
    db.add(new_user)
    try:
        db.flush()  # get new_user.id before commit

        db.add(
            models.UserIdentity(
                user_id=new_user.id,
                provider="local",
                provider_user_id=str(new_user.id),
                provider_email=new_user.email,
            )
        )

        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="auth.signup_conflict",
        )

    db.refresh(new_user)
    if not new_user.is_verified:
        raw_token = issue_email_verification_token(db, new_user)
        verify_link = build_verify_email_link(raw_token)
        sent = send_verification_email(new_user.email, verify_link)
        if not sent and not settings.is_production:
            logger.info("Email verification link fallback for %s: %s", new_user.email, verify_link)
    return build_user_out(new_user)


@router.post('/sign-in')
def login(
    response: Response,
    request: Request,
    user_credentials: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
    x_timezone: str | None = Header(default=None, alias="X-Timezone"),
):
    username = (user_credentials.username or "").strip().lower()
    client_ip = request.client.host if request.client else "unknown"
    rate_key = f"{client_ip}|{username}"
    rl = check_and_consume("login", rate_key)
    rate_headers = {
        "X-RateLimit-Limit": str(rl.limit),
        "X-RateLimit-Remaining": str(rl.remaining),
        "X-RateLimit-Reset": str(rl.reset_seconds),
    }
    for k, v in rate_headers.items():
        response.headers[k] = v

    if not rl.allowed:
        rate_headers["Retry-After"] = str(rl.reset_seconds)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="auth.login_rate_limited",
            headers=rate_headers,
        )

    # 1. Try to find the user in the DB
    user = db.query(models.User).filter(
        models.User.email == user_credentials.username).first()

    # 2. If user doesn't exist or password is wrong, throw a 403
    if not user:
        utils.verify_password(
            user_credentials.password or "", DUMMY_PASSWORD_HASH)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="auth.invalid_credentials",
            headers=rate_headers,
        )

    if not utils.verify_password(user_credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="auth.invalid_credentials",
            headers=rate_headers,
        )

    if not user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="auth.email_not_verified",
            headers=rate_headers,
        )

    ensure_local_identity(db, user)

    # Save the browser timezone so the scheduler can use the correct local date per user
    detected_tz = str(_safe_zoneinfo((x_timezone or "").strip() or None))
    if detected_tz and user.timezone != detected_tz:
        user.timezone = detected_tz
        db.commit()

    # 3. Create BOTH tokens
    access_token = oauth2.create_access_token(data={"user_id": user.id})
    refresh_token = oauth2.create_refresh_token(user_id=user.id)

    # 4. Set refresh token as HttpOnly cookie (browser stores it automatically)
    oauth2.set_refresh_cookie(response, refresh_token)

    # 5. Return access token in the JSON response body
    return {"access_token": access_token, "token_type": "bearer"}  # nosec B105


@router.get("/me", response_model=schemas.UserOut)
def get_me(current_user: models.User = Depends(oauth2.get_current_user)):
    return build_user_out(current_user)


@router.post("/me/onboarding", response_model=schemas.UserOut, status_code=status.HTTP_200_OK)
def upsert_onboarding_profile(
    payload: schemas.UserOnboardingUpsert,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
):
    profile = (
        db.query(models.UserProfile)
        .filter(models.UserProfile.user_id == current_user.id)
        .first()
    )

    if profile is None:
        profile = models.UserProfile(
            user_id=current_user.id,
            life_status=payload.life_status,
            monthly_income_amount=0,
            initial_balance=payload.initial_balance,
            onboarding_completed_at=datetime.now(timezone.utc),
        )
        db.add(profile)
    else:
        profile.life_status = payload.life_status
        profile.initial_balance = payload.initial_balance
        profile.onboarding_completed_at = datetime.now(timezone.utc)

    existing_sources = (
        db.query(models.IncomeSource)
        .filter(models.IncomeSource.owner_id == current_user.id)
        .all()
    )
    existing_by_name = {source.name.lower(): source for source in existing_sources}

    for source_name in _default_income_sources_for_status(payload.life_status):
        existing_source = existing_by_name.get(source_name.lower())
        if existing_source is None:
            db.add(
                models.IncomeSource(
                    owner_id=current_user.id,
                    name=source_name,
                    is_active=True,
                )
            )
        elif not existing_source.is_active:
            existing_source.is_active = True

    db.commit()
    db.refresh(current_user)
    return build_user_out(current_user)


@router.post("/me/toggle-premium", response_model=schemas.UserOut)
def toggle_premium(
    db: Session = Depends(get_db), current_user: models.User = Depends(oauth2.get_current_user)
):
    current_user.is_premium = not current_user.is_premium
    db.commit()
    db.refresh(current_user)
    return build_user_out(current_user)
