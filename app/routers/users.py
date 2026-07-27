import logging
import json
# pyrefly: ignore [missing-import]
import httpx
from datetime import datetime, timezone
# pyrefly: ignore [missing-import]
from fastapi import APIRouter, Depends, HTTPException, Header, Request, Response, status
# pyrefly: ignore [missing-import]
from fastapi.security import OAuth2PasswordRequestForm
# pyrefly: ignore [missing-import]
from sqlalchemy.orm import Session
# pyrefly: ignore [missing-import]
from sqlalchemy.exc import IntegrityError
from app.utils import is_disposable_email
from .. import oauth2
from .. import models, schemas, utils
from ..session import get_db
from app.audit import log_security_event, SecurityAction, SecurityStatus
from app.redis_rate_limiter import check_and_consume, consume_token_bucket, redis_client
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


def _default_income_sources_for_statuses(life_statuses: list[models.LifeStatus]) -> list[str]:
    mapping = {
        models.LifeStatus.STUDENT: ["Allowance", "Scholarship", "Part-time work"],
        models.LifeStatus.EMPLOYED: ["Salary", "Bonus", "Side income"],
        models.LifeStatus.SELF_EMPLOYED: ["Client payment", "Freelance work", "Project income"],
        models.LifeStatus.BUSINESS_OWNER: ["Business income", "Other revenue"],
        models.LifeStatus.UNEMPLOYED: ["Support", "Temporary income", "Other income"],
    }
    sources = set()
    for life_status in life_statuses:
        sources.update(mapping.get(life_status, ["Other income"]))
    
    if not sources:
        sources.add("Other income")
    return list(sources)


def build_user_out(user: models.User, verification_email_sent: bool | None = None) -> schemas.UserOut:
    profile_out = None
    needs_onboarding = True
    if user.profile is not None:
        profile_out = schemas.UserProfileOut.model_validate(user.profile)
        needs_onboarding = user.profile.onboarding_completed_at is None

    has_local = any(identity.provider == "local" for identity in user.identities)

    return schemas.UserOut(
        id=user.id,
        username=user.username,
        email=user.email,
        created_at=user.created_at,
        is_premium=user.is_premium,
        has_local_password=has_local,
        needs_onboarding=needs_onboarding,
        profile=profile_out,
        verification_email_sent=verification_email_sent,
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
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
):
    cache_key = None
    if idempotency_key:
        cache_key = f"idempotency:signup:{idempotency_key}"
        cached_res = redis_client.get(cache_key)
        if cached_res == "locked":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, 
                detail="auth.idempotency_conflict_in_progress"
            )
        elif cached_res:
            try:
                # If valid JSON, return immediately 
                return json.loads(cached_res)
            except Exception:
                pass
        
        # Lock it for max 60s while processing
        redis_client.setex(cache_key, 60, "locked")

    # 1. Global Load Shedding (Token Bucket)
    # Capacity 100, refill rate of 100 per 60 seconds (approx 1.66/sec)
    global_rl = consume_token_bucket("signup_global", "global", capacity=100, refill_rate_per_second=100/60)
    if not global_rl.allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="auth.signup_global_rate_limited",
            headers={"Retry-After": str(global_rl.reset_seconds)},
        )

    if is_disposable_email(user.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="auth.disposable_email_blocked"
        )

    # 2. IP-based Rate Limiting (Sliding Window)
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

    # 3. Verify CAPTCHA (if required)
    if settings.require_captcha:
        if not user.captcha_token:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="auth.captcha_failed")
        if not utils.verify_turnstile_token(
            token=user.captcha_token,
            client_ip=client_ip,
            secret_key=settings.cloudflare_turnstile_secret_key.get_secret_value()
        ):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="auth.captcha_failed")

    # 4. Check if user already exists
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
        sent = send_verification_email(new_user.email, verify_link, idempotency_key=raw_token)
        if not sent and not settings.is_production:
            logger.info("Email verification link fallback for %s: %s", new_user.email, verify_link)
        out_data = build_user_out(new_user, verification_email_sent=sent)
    else:
        out_data = build_user_out(new_user)
        
    if cache_key:
        redis_client.setex(cache_key, 86400, out_data.model_dump_json())

    log_security_event(db, action=SecurityAction.SIGNUP, status=SecurityStatus.SUCCESS,
                       request=request, user_id=new_user.id, metadata={"email": new_user.email})

    return out_data


def _sync_user_timezone(db: Session, user: models.User, x_timezone: str | None) -> None:
    """
    Compares the browser timezone (from header) with the stored preference.
    Updates the DB if they differ to ensure background tasks (scheduler) stay accurate.
    """
    detected_tz = str(_safe_zoneinfo((x_timezone or "").strip() or None))
    if detected_tz and user.timezone != detected_tz:
        user.timezone = detected_tz
        db.commit()


@router.post('/sign-in')
def login(
    response: Response,
    request: Request,
    user_credentials: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
    x_timezone: str | None = Header(default=None, alias="X-Timezone"),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
):
    if idempotency_key:
        cache_key = f"idempotency:signin:{idempotency_key}"
        if not redis_client.set(cache_key, "IN_PROGRESS", nx=True, ex=30):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="auth.idempotency_conflict_in_progress"
            )

    username = (user_credentials.username or "").strip().lower()
    client_ip = request.client.host if request.client else "unknown"
    # Bucket 1: IP Bucket (20 attempts / 5 mins)
    ip_rl = check_and_consume("login_ip", client_ip, window_seconds=300, max_attempts=20)
    
    # Bucket 2: Email Bucket (5 attempts / 5 mins)
    email_rl = check_and_consume("login_email", username, window_seconds=300, max_attempts=5)
    
    failed_rl = email_rl if not email_rl.allowed else ip_rl
    
    rate_headers = {
        "X-RateLimit-Limit": str(failed_rl.limit),
        "X-RateLimit-Remaining": str(failed_rl.remaining),
        "X-RateLimit-Reset": str(failed_rl.reset_seconds),
    }
    for k, v in rate_headers.items():
        response.headers[k] = v

    if not ip_rl.allowed or not email_rl.allowed:
        rate_headers["Retry-After"] = str(max(ip_rl.reset_seconds, email_rl.reset_seconds))
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
        log_security_event(db, action=SecurityAction.LOGIN, status=SecurityStatus.FAILED,
                           request=request, metadata={"reason": "user_not_found", "email": username})
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="auth.invalid_credentials",
            headers=rate_headers,
        )

    if not utils.verify_password(user_credentials.password, user.hashed_password):
        log_security_event(db, action=SecurityAction.LOGIN, status=SecurityStatus.FAILED,
                           request=request, user_id=user.id, metadata={"reason": "invalid_password"})
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="auth.invalid_credentials",
            headers=rate_headers,
        )

    if not user.is_verified:
        log_security_event(db, action=SecurityAction.LOGIN, status=SecurityStatus.FAILED,
                           request=request, user_id=user.id, metadata={"reason": "email_not_verified"})
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="auth.email_not_verified",
            headers=rate_headers,
        )

    if not user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="auth.email_not_verified",
            headers=rate_headers,
        )

    ensure_local_identity(db, user)

    # Sync timezone preference
    _sync_user_timezone(db, user, x_timezone)

    # 3. Create BOTH tokens
    access_token = oauth2.create_access_token(data={"user_id": user.id})
    refresh_token = oauth2.create_refresh_token(user_id=user.id)

    # 4. Set refresh token as HttpOnly cookie (browser stores it automatically)
    oauth2.set_refresh_cookie(response, refresh_token)

    # 5. Return access token in the JSON response body
    log_security_event(db, action=SecurityAction.LOGIN, status=SecurityStatus.SUCCESS,
                       request=request, user_id=user.id)

    return {"access_token": access_token, "token_type": "bearer"}  # nosec B105


@router.get("/me", response_model=schemas.UserOut)
def get_me(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
    x_timezone: str | None = Header(default=None, alias="X-Timezone"),
):
    # Proactive Sync: Update DB if user traveled to a new country
    _sync_user_timezone(db, current_user, x_timezone)
    
    return build_user_out(current_user)


@router.post("/me/onboarding", response_model=schemas.UserOut, status_code=status.HTTP_200_OK)
def upsert_onboarding_profile(
    payload: schemas.UserOnboardingUpsert,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
    x_timezone: str | None = Header(default=None, alias="X-Timezone"),
):
    # Ensure timezone is captured during initial setup
    _sync_user_timezone(db, current_user, x_timezone)
    profile = (
        db.query(models.UserProfile)
        .filter(models.UserProfile.user_id == current_user.id)
        .first()
    )

    if profile is None:
        profile = models.UserProfile(
            user_id=current_user.id,
            life_statuses=payload.life_statuses,
            monthly_income_amount=0,
            initial_balance=0, # Deprecated
            onboarding_completed_at=datetime.now(timezone.utc),
        )
        db.add(profile)
    else:
        profile.life_statuses = payload.life_statuses
        profile.onboarding_completed_at = datetime.now(timezone.utc)

    # Wallet Creation
    # Clear existing if any (re-onboarding) to ensure clean state
    db.query(models.Wallet).filter(models.Wallet.owner_id == current_user.id).delete()
    
    for i, wallet_data in enumerate(payload.wallets):
        is_val_default = (i == 0)
        new_wallet = models.Wallet(
            owner_id=current_user.id,
            name=wallet_data.name,
            wallet_type=wallet_data.wallet_type,
            accounting_type=wallet_data.accounting_type,
            initial_balance=wallet_data.initial_balance,
            current_balance=wallet_data.initial_balance,
            has_overdraft=wallet_data.has_overdraft,
            overdraft_limit=wallet_data.overdraft_limit,
            credit_limit=wallet_data.credit_limit,
            allow_overlimit=wallet_data.allow_overlimit,
            color=wallet_data.color,
            currency=wallet_data.currency,
            can_fund_goals=(
                False
                if wallet_data.accounting_type != models.AccountingType.ASSET
                and wallet_data.wallet_type != models.WalletType.CREDIT
                else (
                    bool(wallet_data.can_fund_goals)
                    if wallet_data.can_fund_goals is not None
                    else wallet_data.wallet_type == models.WalletType.SAVINGS
                )
            ),
            is_default=is_val_default
        )
        db.add(new_wallet)

    existing_sources = (
        db.query(models.IncomeSource)
        .filter(models.IncomeSource.owner_id == current_user.id)
        .all()
    )
    existing_by_name = {source.name.lower(): source for source in existing_sources}

    for source_name in _default_income_sources_for_statuses(payload.life_statuses):
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
    if settings.is_production or not settings.debug_allow_premium_toggle:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="users.premium_toggle_disabled")
    current_user.is_premium = not current_user.is_premium
    db.commit()
    db.refresh(current_user)
    return build_user_out(current_user)
