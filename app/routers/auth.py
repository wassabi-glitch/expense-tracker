import hashlib
import logging
from datetime import datetime, timedelta, timezone
import secrets

# pyrefly: ignore [missing-import]
from fastapi import APIRouter, Depends, HTTPException, Header, Request, Response, status
# pyrefly: ignore [missing-import]
from sqlalchemy.orm import Session

from app import models, schemas, utils
from app import oauth2
from app.audit import log_security_event, SecurityAction, SecurityStatus
from app.email_service import send_password_changed_email, send_password_reset_email, send_verification_email
from app.email_verification import (
    build_verify_email_link,
    hash_email_verification_token,
    issue_email_verification_token,
)
from app.redis_rate_limiter import check_and_consume, consume_token_bucket, redis_client
from app.session import get_db
from app.timezone import _safe_zoneinfo
from config import settings


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["Auth"])

RESET_TOKEN_TTL_MINUTES = 30
FORGOT_PASSWORD_SUCCESS_MESSAGE = (  # nosec B105
    "If the account exists, please check your email inbox for a link to complete the reset."
)
VERIFY_EMAIL_SUCCESS_MESSAGE = "If the account exists, please check your email inbox for a verification link."  # nosec B105


def _hash_reset_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def _build_reset_link(raw_token: str) -> str:
    base = settings.frontend_url.rstrip("/")
    return f"{base}/reset-password?token={raw_token}"


@router.post("/forgot-password", response_model=schemas.MessageResponse, status_code=status.HTTP_200_OK)
def forgot_password(
    payload: schemas.ForgotPasswordRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
):
    if idempotency_key:
        cache_key = f"idempotency:forgot_password:{idempotency_key}"
        if not redis_client.set(cache_key, "IN_PROGRESS", nx=True, ex=30):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="auth.idempotency_conflict_in_progress"
            )

    client_ip = request.client.host if request.client else "unknown"

    if settings.require_captcha:
        if not payload.captcha_token:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="auth.captcha_failed")
        if not utils.verify_turnstile_token(
            token=payload.captcha_token,
            client_ip=client_ip,
            secret_key=settings.cloudflare_turnstile_secret_key.get_secret_value()
        ):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="auth.captcha_failed")

    email = payload.email.strip().lower()
    
    # Decoupled Rate Limiting
    # 1. IP Bucket: Max 10 requests per hour per IP
    ip_rl = consume_token_bucket("forgot_pw_ip", client_ip, capacity=10, refill_rate_per_second=10/3600)
    # 2. Email Bucket: Max 3 requests per hour per Email
    email_rl = consume_token_bucket("forgot_pw_email", email, capacity=3, refill_rate_per_second=3/3600)

    # Use the strictest retry-after if either fails
    if not ip_rl.allowed or not email_rl.allowed:
        retry_after = max(ip_rl.reset_seconds, email_rl.reset_seconds)
        rate_headers = {
            "Retry-After": str(retry_after),
            "X-RateLimit-Limit": str(min(ip_rl.limit, email_rl.limit)),
            "X-RateLimit-Remaining": "0",
            "X-RateLimit-Reset": str(retry_after),
        }
        for k, v in rate_headers.items():
            response.headers[k] = v
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="auth.forgot_password_rate_limited",
            headers=rate_headers,
        )

    # Standard success headers
    rate_headers = {
        "X-RateLimit-Limit": str(email_rl.limit),
        "X-RateLimit-Remaining": str(email_rl.remaining),
        "X-RateLimit-Reset": str(email_rl.reset_seconds),
    }
    for k, v in rate_headers.items():
        response.headers[k] = v

    user = db.query(models.User).filter(models.User.email == email).first()
    if user:
        now = datetime.now(timezone.utc)
        raw_token = secrets.token_urlsafe(48)
        token_hash = _hash_reset_token(raw_token)

        db.query(models.PasswordResetToken).filter(
            models.PasswordResetToken.user_id == user.id,
            models.PasswordResetToken.used_at.is_(None),
        ).update(
            {models.PasswordResetToken.used_at: now},
            synchronize_session=False,
        )

        db.add(
            models.PasswordResetToken(
                user_id=user.id,
                token_hash=token_hash,
                expires_at=now + timedelta(minutes=RESET_TOKEN_TTL_MINUTES),
            )
        )
        db.commit()

        reset_link = _build_reset_link(raw_token)
        sent = send_password_reset_email(email, reset_link, idempotency_key=raw_token)
        if not sent and not settings.is_production:
            logger.info("Password reset link fallback for %s: %s",
                        email, reset_link)

    return schemas.MessageResponse(message=FORGOT_PASSWORD_SUCCESS_MESSAGE)


@router.post("/resend-verification", response_model=schemas.MessageResponse, status_code=status.HTTP_200_OK)
def resend_verification(
    payload: schemas.ResendVerificationRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
):
    if idempotency_key:
        cache_key = f"idempotency:resend_verification:{idempotency_key}"
        if not redis_client.set(cache_key, "IN_PROGRESS", nx=True, ex=30):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="auth.idempotency_conflict_in_progress"
            )

    client_ip = request.client.host if request.client else "unknown"
    email = payload.email.strip().lower()
    rate_key = f"{client_ip}|{email}"
    rl = check_and_consume("resend_verification", rate_key)
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
            detail="auth.resend_verification_rate_limited",
            headers=rate_headers,
        )

    user = db.query(models.User).filter(models.User.email == email).first()
    if user and not user.is_verified:
        raw_token = issue_email_verification_token(db, user)
        verify_link = build_verify_email_link(raw_token)
        sent = send_verification_email(user.email, verify_link, idempotency_key=raw_token)
        if sent:
            logger.info("Resend verification email accepted for %s", user.email)
        elif not settings.is_production:
            logger.info("Email verification link fallback for %s: %s",
                        user.email, verify_link)
        else:
            logger.warning("Resend verification send failed for %s", user.email)
    elif not user:
        logger.info("Resend verification skipped: no user for %s", email)
    else:
        logger.info("Resend verification skipped: already verified %s", email)

    return schemas.MessageResponse(message=VERIFY_EMAIL_SUCCESS_MESSAGE)


@router.post("/verify-email", response_model=schemas.MessageResponse, status_code=status.HTTP_200_OK)
def verify_email(
    payload: schemas.VerifyEmailRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
):
    if idempotency_key:
        cache_key = f"idempotency:verify_email:{idempotency_key}"
        if not redis_client.set(cache_key, "IN_PROGRESS", nx=True, ex=30):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="auth.idempotency_conflict_in_progress"
            )

    client_ip = request.client.host if request.client else "unknown"
    rate_key = f"{client_ip}"
    rl = check_and_consume("verify_email", rate_key)
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
            detail="auth.verify_email_rate_limited",
            headers=rate_headers,
        )

    now = datetime.now(timezone.utc)
    token_hash = hash_email_verification_token(payload.token.strip())
    verify_token = (
        db.query(models.EmailVerificationToken)
        .filter(
            models.EmailVerificationToken.token_hash == token_hash,
            models.EmailVerificationToken.expires_at > now,
        )
        .first()
    )
    if not verify_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="auth.verify_email_token_invalid_or_expired",
        )

    user = db.query(models.User).filter(
        models.User.id == verify_token.user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="auth.verify_email_token_invalid_or_expired",
        )

    if verify_token.used_at is not None:
        if user.is_verified:
            # Idempotency: Scanner clicked it first, user clicked it second.
            return schemas.MessageResponse(message="Email verified successfully. You can now sign in.")
        else:
            # Token used but user somehow not verified, invalid state.
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="auth.verify_email_token_invalid_or_expired",
            )

    rows_updated = db.query(models.EmailVerificationToken).filter(
        models.EmailVerificationToken.id == verify_token.id,
        models.EmailVerificationToken.used_at.is_(None),
    ).update(
        {models.EmailVerificationToken.used_at: now},
        synchronize_session=False,
    )

    if rows_updated == 0:
        db.rollback()
        # Race condition: someone else used it right after we checked `.first()`.
        # If the user is now verified, consider it a successful idempotent hit.
        if user.is_verified:
            return schemas.MessageResponse(message="Email verified successfully. You can now sign in.")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="auth.verify_email_token_invalid_or_expired",
        )

    user.is_verified = True
    db.query(models.EmailVerificationToken).filter(
        models.EmailVerificationToken.user_id == user.id,
        models.EmailVerificationToken.used_at.is_(None),
        models.EmailVerificationToken.id != verify_token.id,
    ).update(
        {models.EmailVerificationToken.used_at: now},
        synchronize_session=False,
    )
    db.commit()
    log_security_event(db, action=SecurityAction.EMAIL_VERIFIED, status=SecurityStatus.SUCCESS,
                       request=request, user_id=user.id)
    return schemas.MessageResponse(message="Email verified successfully. You can now sign in.")


@router.post("/reset-password", response_model=schemas.MessageResponse, status_code=status.HTTP_200_OK)
def reset_password(
    payload: schemas.ResetPasswordRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
):
    if idempotency_key:
        cache_key = f"idempotency:reset_password:{idempotency_key}"
        if not redis_client.set(cache_key, "IN_PROGRESS", nx=True, ex=30):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="auth.idempotency_conflict_in_progress"
            )

    client_ip = request.client.host if request.client else "unknown"

    if settings.require_captcha:
        if not payload.captcha_token:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="auth.captcha_failed")
        if not utils.verify_turnstile_token(
            token=payload.captcha_token,
            client_ip=client_ip,
            secret_key=settings.cloudflare_turnstile_secret_key.get_secret_value()
        ):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="auth.captcha_failed")

    token_hash = _hash_reset_token(payload.token)
    
    # Decoupled Rate Limiting
    # 1. IP Bucket: Max 5 attempts per minute
    ip_rl = check_and_consume("reset_password", client_ip, window_seconds=60, max_attempts=5)
    # 2. Token Bucket: Max 5 attempts per token per hour (Anti-bruteforce)
    token_rl = consume_token_bucket("reset_pw_token", token_hash, capacity=5, refill_rate_per_second=5/3600)

    if not ip_rl.allowed or not token_rl.allowed:
        retry_after = max(ip_rl.reset_seconds, token_rl.reset_seconds)
        rate_headers = {
            "Retry-After": str(retry_after),
            "X-RateLimit-Limit": str(min(ip_rl.limit, token_rl.limit)),
            "X-RateLimit-Remaining": "0",
            "X-RateLimit-Reset": str(retry_after),
        }
        for k, v in rate_headers.items():
            response.headers[k] = v
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="auth.reset_password_rate_limited",
            headers=rate_headers,
        )

    rate_headers = {
        "X-RateLimit-Limit": str(ip_rl.limit),
        "X-RateLimit-Remaining": str(ip_rl.remaining),
        "X-RateLimit-Reset": str(ip_rl.reset_seconds),
    }
    for k, v in rate_headers.items():
        response.headers[k] = v

    now = datetime.now(timezone.utc)
    reset_token = (
        db.query(models.PasswordResetToken)
        .filter(
            models.PasswordResetToken.token_hash == token_hash,
            models.PasswordResetToken.used_at.is_(None),
            models.PasswordResetToken.expires_at > now,
        )
        .first()
    )

    if not reset_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="auth.reset_token_invalid_or_expired",
        )

    user = db.query(models.User).filter(
        models.User.id == reset_token.user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="auth.reset_token_invalid_or_expired",
        )

    email_local_part = user.email.split("@", 1)[0].strip().lower()
    if email_local_part and email_local_part in payload.new_password.lower():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="auth.password_contains_email_local_part",
        )

    rows_updated = db.query(models.PasswordResetToken).filter(
        models.PasswordResetToken.id == reset_token.id,
        models.PasswordResetToken.used_at.is_(None),
    ).update(
        {models.PasswordResetToken.used_at: now},
        synchronize_session=False,
    )

    if rows_updated == 0:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="auth.reset_token_invalid_or_expired",
        )

    user.hashed_password = utils.hash_password(payload.new_password)

    db.query(models.PasswordResetToken).filter(
        models.PasswordResetToken.user_id == user.id,
        models.PasswordResetToken.used_at.is_(None),
        models.PasswordResetToken.id != reset_token.id,
    ).update(
        {models.PasswordResetToken.used_at: now},
        synchronize_session=False,
    )

    db.commit()

    # After password reset, revoke ALL refresh tokens for this user.
    # This forces them to log in again on every device — critical for security.
    # Imagine: attacker has your session, you reset your password → their session dies.
    oauth2.revoke_all_user_tokens(user.id)
    
    # Send an email notification about the password change
    send_password_changed_email(
        to_email=user.email,
        idempotency_key=f"reset-notif-{user.id}-{now.timestamp()}"
    )

    log_security_event(db, action=SecurityAction.PASSWORD_RESET, status=SecurityStatus.SUCCESS,
                       request=request, user_id=user.id)

    return schemas.MessageResponse(
        message="Password reset successful. Please sign in with your new password."
    )


@router.post("/refresh", response_model=schemas.RefreshResponse, status_code=status.HTTP_200_OK)
def refresh_token(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    x_timezone: str | None = Header(default=None, alias="X-Timezone"),
):
    """
    Exchange a valid refresh token (from HttpOnly cookie) for a new
    access token + new refresh token.

    This is the endpoint the frontend calls when the access token expires.
    The browser sends the refresh_token cookie automatically.
    """
    # Step 1: Read the refresh token from the cookie
    raw_token = request.cookies.get(oauth2.REFRESH_COOKIE_NAME)
    if not raw_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="auth.refresh_token_missing",
        )

    # Step 2: Rotate — validates old token, deletes it, creates new one
    new_raw_token, user_id = oauth2.rotate_refresh_token(raw_token)

    # Step 3: Make sure the user still exists in the database
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        oauth2.revoke_refresh_token(new_raw_token)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="auth.refresh_token_invalid",
        )

    # Update timezone from browser on every refresh — keeps it accurate if user travels
    detected_tz = str(_safe_zoneinfo((x_timezone or "").strip() or None))
    if detected_tz and user.timezone != detected_tz:
        user.timezone = detected_tz
        db.commit()

    # Step 4: Issue new access token
    access_token = oauth2.create_access_token(data={"user_id": user.id})

    # Step 5: Set the new refresh token cookie (replaces the old one)
    oauth2.set_refresh_cookie(response, new_raw_token)

    return {"access_token": access_token, "token_type": "bearer"}  # nosec B105


@router.post("/logout", status_code=status.HTTP_200_OK)
def logout(
    request: Request,
    response: Response,
):
    """
    Logs out: revokes the refresh token in Redis and clears the cookie.
    """
    raw_token = request.cookies.get(oauth2.REFRESH_COOKIE_NAME)
    if raw_token:
        oauth2.revoke_refresh_token(raw_token)

    oauth2.clear_refresh_cookie(response)
    return {"message": "Logged out successfully."}


@router.post("/logout-all", status_code=status.HTTP_200_OK)
def logout_all(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
):
    """
    Logs out of ALL devices: revokes all refresh token families in Redis and clears the cookie.
    """
    oauth2.revoke_all_user_tokens(current_user.id)
    oauth2.clear_refresh_cookie(response)
    log_security_event(db, action=SecurityAction.LOGOUT_ALL, status=SecurityStatus.SUCCESS,
                       request=request, user_id=current_user.id)
    return {"message": "Logged out of all devices successfully."}


# --- MOBILE NATIVE ENDPOINTS ---

@router.post("/mobile/sign-in", response_model=schemas.MobileTokenResponse)
def mobile_sign_in(
    payload: schemas.MobileSignInRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    x_timezone: str | None = Header(default=None, alias="X-Timezone"),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
):
    from app.routers.users import DUMMY_PASSWORD_HASH, ensure_local_identity, _sync_user_timezone

    if idempotency_key:
        cache_key = f"idempotency:signin:{idempotency_key}"
        if not redis_client.set(cache_key, "IN_PROGRESS", nx=True, ex=30):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="auth.idempotency_conflict_in_progress"
            )

    email = payload.email.strip().lower()
    client_ip = request.client.host if request.client else "unknown"
    # Bucket 1: IP Bucket (20 attempts / 5 mins)
    ip_rl = check_and_consume("login_ip", client_ip, window_seconds=300, max_attempts=20)
    
    # Bucket 2: Email Bucket (5 attempts / 5 mins)
    email_rl = check_and_consume("login_email", email, window_seconds=300, max_attempts=5)
    
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

    user = db.query(models.User).filter(models.User.email == email).first()

    if not user:
        utils.verify_password(payload.password or "", DUMMY_PASSWORD_HASH)
        log_security_event(db, action=SecurityAction.LOGIN, status=SecurityStatus.FAILED,
                           request=request, metadata={"reason": "user_not_found", "email": email, "client": "mobile"})
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="auth.invalid_credentials",
            headers=rate_headers,
        )

    if not utils.verify_password(payload.password, user.hashed_password):
        log_security_event(db, action=SecurityAction.LOGIN, status=SecurityStatus.FAILED,
                           request=request, user_id=user.id, metadata={"reason": "invalid_password", "client": "mobile"})
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="auth.invalid_credentials",
            headers=rate_headers,
        )

    if not user.is_verified:
        log_security_event(db, action=SecurityAction.LOGIN, status=SecurityStatus.FAILED,
                           request=request, user_id=user.id, metadata={"reason": "email_not_verified", "client": "mobile"})
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="auth.email_not_verified",
            headers=rate_headers,
        )

    ensure_local_identity(db, user)
    _sync_user_timezone(db, user, x_timezone)

    access_token = oauth2.create_access_token(data={"user_id": user.id})
    refresh_token = oauth2.create_refresh_token(user_id=user.id)

    log_security_event(db, action=SecurityAction.LOGIN, status=SecurityStatus.SUCCESS,
                       request=request, user_id=user.id, metadata={"client": "mobile"})

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }


@router.post("/mobile/refresh", response_model=schemas.MobileTokenResponse, status_code=status.HTTP_200_OK)
def mobile_refresh_token(
    payload: schemas.MobileRefreshRequest,
    db: Session = Depends(get_db),
    x_timezone: str | None = Header(default=None, alias="X-Timezone"),
):
    raw_token = payload.refresh_token.strip()
    if not raw_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="auth.refresh_token_missing",
        )

    new_raw_token, user_id = oauth2.rotate_refresh_token(raw_token)

    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        oauth2.revoke_refresh_token(new_raw_token)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="auth.refresh_token_invalid",
        )

    detected_tz = str(_safe_zoneinfo((x_timezone or "").strip() or None))
    if detected_tz and user.timezone != detected_tz:
        user.timezone = detected_tz
        db.commit()

    access_token = oauth2.create_access_token(data={"user_id": user.id})

    return {
        "access_token": access_token,
        "refresh_token": new_raw_token,
        "token_type": "bearer"
    }


@router.post("/mobile/logout", status_code=status.HTTP_200_OK)
def mobile_logout(
    payload: schemas.MobileRefreshRequest,
):
    raw_token = payload.refresh_token.strip()
    if raw_token:
        oauth2.revoke_refresh_token(raw_token)

    return {"message": "Logged out successfully."}


@router.post("/change-password")
def change_password(
    payload: schemas.ChangePasswordRequest,
    response: Response,
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
):
    if idempotency_key:
        cache_key = f"idempotency:change_password:{idempotency_key}"
        if not redis_client.set(cache_key, "IN_PROGRESS", nx=True, ex=30):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="auth.idempotency_conflict_in_progress"
            )

    client_ip = request.client.host if request.client else "unknown"
    ip_rl = check_and_consume("change_pw_ip", client_ip, window_seconds=3600, max_attempts=10)
    user_rl = check_and_consume("change_pw_user", str(current_user.id), window_seconds=3600, max_attempts=5)

    if not ip_rl.allowed or not user_rl.allowed:
        retry_after = max(ip_rl.reset_seconds, user_rl.reset_seconds)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="auth.change_password_rate_limited",
            headers={"Retry-After": str(retry_after)},
        )

    has_local = any(identity.provider == "local" for identity in current_user.identities)
    if not has_local:
        raise HTTPException(status_code=400, detail="auth.google_only_cannot_change_password")

    if not utils.verify_password(payload.current_password, current_user.hashed_password):
        log_security_event(db, action=SecurityAction.PASSWORD_CHANGED, status=SecurityStatus.FAILED,
                           request=request, user_id=current_user.id,
                           metadata={"reason": "incorrect_current_password"})
        raise HTTPException(status_code=403, detail="auth.incorrect_current_password")

    current_user.hashed_password = utils.hash_password(payload.new_password)
    db.commit()

    oauth2.revoke_all_user_tokens(current_user.id)

    access_token = oauth2.create_access_token(data={"user_id": current_user.id})
    refresh_token = oauth2.create_refresh_token(user_id=current_user.id)
    oauth2.set_refresh_cookie(response, refresh_token)

    try:
        send_password_changed_email(current_user.email)
    except Exception as e:
        logger.error("Failed to send password changed email to %s: %s", current_user.email, e)

    log_security_event(db, action=SecurityAction.PASSWORD_CHANGED, status=SecurityStatus.SUCCESS,
                       request=request, user_id=current_user.id)

    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/mobile/change-password", response_model=schemas.MobileTokenResponse)
def mobile_change_password(
    payload: schemas.ChangePasswordRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
):
    if idempotency_key:
        cache_key = f"idempotency:mobile_change_password:{idempotency_key}"
        if not redis_client.set(cache_key, "IN_PROGRESS", nx=True, ex=30):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="auth.idempotency_conflict_in_progress"
            )

    client_ip = request.client.host if request.client else "unknown"
    ip_rl = check_and_consume("change_pw_ip", client_ip, window_seconds=3600, max_attempts=10)
    user_rl = check_and_consume("change_pw_user", str(current_user.id), window_seconds=3600, max_attempts=5)

    if not ip_rl.allowed or not user_rl.allowed:
        retry_after = max(ip_rl.reset_seconds, user_rl.reset_seconds)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="auth.change_password_rate_limited",
            headers={"Retry-After": str(retry_after)},
        )

    has_local = any(identity.provider == "local" for identity in current_user.identities)
    if not has_local:
        raise HTTPException(status_code=400, detail="auth.google_only_cannot_change_password")

    if not utils.verify_password(payload.current_password, current_user.hashed_password):
        log_security_event(db, action=SecurityAction.PASSWORD_CHANGED, status=SecurityStatus.FAILED,
                           request=request, user_id=current_user.id,
                           metadata={"reason": "incorrect_current_password", "client": "mobile"})
        raise HTTPException(status_code=403, detail="auth.incorrect_current_password")

    current_user.hashed_password = utils.hash_password(payload.new_password)
    db.commit()

    oauth2.revoke_all_user_tokens(current_user.id)

    access_token = oauth2.create_access_token(data={"user_id": current_user.id})
    refresh_token = oauth2.create_refresh_token(user_id=current_user.id)

    try:
        send_password_changed_email(current_user.email)
    except Exception as e:
        logger.error("Failed to send password changed email to %s: %s", current_user.email, e)

    log_security_event(db, action=SecurityAction.PASSWORD_CHANGED, status=SecurityStatus.SUCCESS,
                       request=request, user_id=current_user.id, metadata={"client": "mobile"})

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }


@router.post("/verify-password")
def verify_password(
    payload: schemas.VerifyPasswordRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
):
    """Verify the current user's password without changing anything.

    Used by the mobile PIN recovery flow after 30-min cooldown.
    Does not modify any state — just confirms the password is correct.
    """
    # Idempotency guard (30-second window)
    if idempotency_key:
        cache_key = f"idempotency:verify_password:{idempotency_key}"
        if not redis_client.set(cache_key, "IN_PROGRESS", nx=True, ex=30):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="auth.idempotency_conflict_in_progress",
            )

    # Rate limiting
    client_ip = request.client.host if request.client else "unknown"
    ip_rl = check_and_consume("verify_pw_ip", client_ip, window_seconds=3600, max_attempts=10)
    user_rl = check_and_consume("verify_pw_user", str(current_user.id), window_seconds=3600, max_attempts=5)

    if not ip_rl.allowed or not user_rl.allowed:
        retry_after = max(ip_rl.reset_seconds, user_rl.reset_seconds)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="auth.rate_limited",
            headers={"Retry-After": str(retry_after)},
        )

    # Verify the password
    if not current_user.hashed_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="auth.google_only_cannot_change_password",
        )

    if not utils.verify_password(payload.password, current_user.hashed_password):
        log_security_event(
            db,
            action=SecurityAction.PASSWORD_CHANGED,
            status=SecurityStatus.FAILED,
            request=request,
            user_id=current_user.id,
            metadata={"reason": "incorrect_password_verification"},
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="auth.incorrect_password",
        )

    return {"verified": True}
