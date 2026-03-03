import hashlib
import logging
from datetime import datetime, timedelta, timezone
import secrets

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app import models, schemas, utils
from app import oauth2
from app.email_service import send_password_reset_email, send_verification_email
from app.email_verification import (
    build_verify_email_link,
    hash_email_verification_token,
    issue_email_verification_token,
)
from app.redis_rate_limiter import check_and_consume
from app.session import get_db
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
):
    client_ip = request.client.host if request.client else "unknown"
    email = payload.email.strip().lower()
    rate_key = f"{client_ip}|{email}"
    rl = check_and_consume("forgot_password", rate_key)
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
            detail="auth.forgot_password_rate_limited",
            headers=rate_headers,
        )

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
        sent = send_password_reset_email(email, reset_link)
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
):
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
        sent = send_verification_email(user.email, verify_link)
        if not sent and not settings.is_production:
            logger.info("Email verification link fallback for %s: %s",
                        user.email, verify_link)

    return schemas.MessageResponse(message=VERIFY_EMAIL_SUCCESS_MESSAGE)


@router.get("/verify-email", response_model=schemas.MessageResponse, status_code=status.HTTP_200_OK)
def verify_email(
    token: str,
    db: Session = Depends(get_db),
):
    now = datetime.now(timezone.utc)
    token_hash = hash_email_verification_token(token.strip())
    verify_token = (
        db.query(models.EmailVerificationToken)
        .filter(
            models.EmailVerificationToken.token_hash == token_hash,
            models.EmailVerificationToken.used_at.is_(None),
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

    user.is_verified = True
    verify_token.used_at = now
    db.query(models.EmailVerificationToken).filter(
        models.EmailVerificationToken.user_id == user.id,
        models.EmailVerificationToken.used_at.is_(None),
        models.EmailVerificationToken.id != verify_token.id,
    ).update(
        {models.EmailVerificationToken.used_at: now},
        synchronize_session=False,
    )
    db.commit()
    return schemas.MessageResponse(message="Email verified successfully. You can now sign in.")


@router.post("/reset-password", response_model=schemas.MessageResponse, status_code=status.HTTP_200_OK)
def reset_password(
    payload: schemas.ResetPasswordRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    client_ip = request.client.host if request.client else "unknown"
    rl = check_and_consume("reset_password", client_ip)
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
            detail="auth.reset_password_rate_limited",
            headers=rate_headers,
        )

    now = datetime.now(timezone.utc)
    token_hash = _hash_reset_token(payload.token)
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

    user.hashed_password = utils.hash_password(payload.new_password)
    reset_token.used_at = now

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

    return schemas.MessageResponse(
        message="Password reset successful. Please sign in with your new password."
    )


@router.post("/refresh", response_model=schemas.RefreshResponse, status_code=status.HTTP_200_OK)
def refresh_token(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
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

    # Step 4: Issue new access token
    access_token = oauth2.create_access_token(data={"user_id": user.id})

    # Step 5: Set the new refresh token cookie (replaces the old one)
    oauth2.set_refresh_cookie(response, new_raw_token)

    return {"access_token": access_token, "token_type": "bearer"}


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
