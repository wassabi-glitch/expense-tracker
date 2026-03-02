import re
import secrets
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app import models, oauth2, utils
from app.session import get_db
from config import settings

router = APIRouter(prefix="/auth/google", tags=["Google Auth"])
STATE_TTL_MIN = 10
GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"


def _create_state(nonce: str) -> str:
    payload = {
        "type": "google_oauth_state",
        "nonce": nonce,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=STATE_TTL_MIN)
    }

    return jwt.encode(payload, settings.secret_key.get_secret_value(), algorithm=settings.algorithm)


def _verify_state(token: str) -> dict:
    try:
        payload = jwt.decode(
            token, settings.secret_key.get_secret_value(), algorithms=[settings.algorithm])
        if payload.get("type") != "google_oauth_state":
            raise ValueError("Invalid state token type")
        return payload
    except (JWTError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="auth.google_invalid_state")


def _base_username_from_email(email: str) -> str:
    base = email.split("@")[0].lower()
    base = re.sub(r"[^a-z0-9._]", "", base).strip("._")
    if not base:
        base = "user"
    return base[:24]


def _unique_username(db: Session, email: str) -> str:
    base = _base_username_from_email(email)
    candidate = base
    i = 1
    while db.query(models.User).filter(models.User.username == candidate).first():
        suffix = str(i)
        candidate = f"{base[:32-len(suffix)]}{suffix}"
        i += 1
    return candidate


@router.get("/login")
def google_login():
    nonce = secrets.token_urlsafe(16)
    state = _create_state(nonce)

    query = urlencode({
        "client_id": settings.google_client_id,
        "redirect_uri": settings.google_redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "nonce": nonce,
        "prompt": "select_account"
    })
    return RedirectResponse(f"{GOOGLE_AUTH_URL}?{query}", status_code=302)


@router.get("/callback")
def google_callback(code: str, state: str, db: Session = Depends(get_db)):
    state_payload = _verify_state(state)
    nonce_expected = state_payload["nonce"]

    token_resp = httpx.post(
        GOOGLE_TOKEN_URL,
        data={
            "code": code,
            "client_id": settings.google_client_id,
            "client_secret": settings.google_client_secret.get_secret_value(),
            "redirect_uri": settings.google_redirect_uri,
            "grant_type": "authorization_code",
        },
        timeout=15.0,
    )

    if token_resp.status_code != 200:
        raise HTTPException(
            status_code=400, detail="auth.google_token_exchange_failed")

    token_data = token_resp.json()
    raw_id_token = token_data.get("id_token")
    if not raw_id_token:
        raise HTTPException(status_code=400, detail="auth.google_id_token_missing")

    idinfo = id_token.verify_oauth2_token(
        raw_id_token,
        google_requests.Request(),
        settings.google_client_id,
    )

    # nonce check (important)
    if idinfo.get("nonce") != nonce_expected:
        raise HTTPException(status_code=400, detail="auth.google_invalid_nonce")

    google_sub = idinfo.get("sub")
    email = (idinfo.get("email") or "").strip().lower()
    email_verified = bool(idinfo.get("email_verified"))

    if not google_sub:
        raise HTTPException(status_code=400, detail="auth.google_subject_missing")

    identity = (
        db.query(models.UserIdentity)
        .filter(
            models.UserIdentity.provider == "google",
            models.UserIdentity.provider_user_id == google_sub,
        )
        .first()
    )

    if identity:
        user = identity.user
    else:
        user = None
        # auto-link only verified emails
        if email and email_verified:
            user = db.query(models.User).filter(
                models.User.email == email).first()

        if not user:
            if not email:
                raise HTTPException(
                    status_code=400, detail="auth.google_email_missing")
            user = models.User(
                email=email,
                username=_unique_username(db, email),
                hashed_password=utils.hash_password(secrets.token_urlsafe(32)),
                is_verified=email_verified,
            )
            db.add(user)
            db.flush()

        db.add(
            models.UserIdentity(
                user_id=user.id,
                provider="google",
                provider_user_id=google_sub,
                provider_email=email or None,
            )
        )
        db.commit()
        db.refresh(user)

    app_token = oauth2.create_access_token({"user_id": user.id})

    # frontend will parse token from hash and save it
    return RedirectResponse(
        f"{settings.frontend_url}/auth/callback#token={app_token}",
        status_code=302,
    )
