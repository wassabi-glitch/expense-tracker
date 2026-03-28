"""
Authentication module: handles JWT access tokens and Redis-backed refresh tokens.

ACCESS TOKEN (JWT):
  - Short-lived (15 min), returned in the JSON response body
  - Frontend stores it in a JS variable (memory), NOT localStorage
  - Used in Authorization header for every API request
  - Stateless — backend doesn't store it anywhere

REFRESH TOKEN (opaque):
  - Long-lived (7 days), stored in a HttpOnly cookie (browser sends it automatically)
  - Backend stores a SHA-256 hash of it in Redis (so the raw token is never stored anywhere)
  - Used ONLY to get a new access token when the old one expires
  - One-time-use: each refresh creates a new token (rotation)
  - Belongs to a "family" — if a revoked token is replayed, the entire family is deleted
"""
import hashlib
import secrets
from datetime import datetime, timedelta, timezone

import redis
from fastapi import Depends, HTTPException, Response, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt

from app import models
from app import schemas
from app.session import get_db
from config import settings

# ─── Constants ──────────────────────────────────────────────

SECRET_KEY = settings.secret_key.get_secret_value()
ALGORITHM = settings.algorithm
ACCESS_TOKEN_EXPIRE_MINUTES = settings.access_token_expire_minutes
REFRESH_TOKEN_EXPIRE_DAYS = settings.refresh_token_expire_days
REFRESH_TOKEN_EXPIRE_SECONDS = REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60
REFRESH_COOKIE_NAME = "refresh_token"

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/users/sign-in")

# ─── Redis client (reuse the same one from rate limiter) ────

_redis = redis.Redis.from_url(settings.redis_url, decode_responses=True)


# ═══════════════════════════════════════════════════════════
#  ACCESS TOKEN (JWT) — same as before, just better organized
# ═══════════════════════════════════════════════════════════

def create_access_token(data: dict) -> str:
    """
    Creates a short-lived JWT access token.

    - `data` should contain {"user_id": <int>}
    - The token is signed with our SECRET_KEY so nobody can tamper with it
    - It expires in ACCESS_TOKEN_EXPIRE_MINUTES (15 min)
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def verify_access_token(token: str, credentials_exception):
    """
    Decodes and validates a JWT access token, returning token data.

    - Decodes the JWT using our SECRET_KEY
    - Extracts the user_id from the payload
    - If anything is wrong (expired, tampered, missing user_id) → raises 401
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        extracted_id: str = payload.get("user_id")
        if extracted_id is None:
            raise credentials_exception
        token_data = schemas.TokenData(user_id=extracted_id)
    except JWTError:
        raise credentials_exception
    return token_data


def get_current_user(token: str = Depends(oauth2_scheme), db=Depends(get_db)):
    """
    FastAPI dependency: extracts and validates the access token from the
    Authorization header, then loads the user from the database.

    Used like: current_user = Depends(get_current_user)
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="auth.credentials_invalid",
        headers={"WWW-Authenticate": "Bearer"},
    )
    token = verify_access_token(token, credentials_exception)
    user = db.query(models.User).filter(models.User.id == token.user_id).first()
    if user is None:
        raise credentials_exception

    if user.is_premium and user.premium_expires_at is not None:
        now = datetime.now(timezone.utc)
        if user.premium_expires_at <= now:
            user.is_premium = False
            user.premium_expires_at = None
            db.commit()
    return user


# ═══════════════════════════════════════════════════════════
#  REFRESH TOKEN (opaque, stored in Redis)
# ═══════════════════════════════════════════════════════════

def _hash_token(raw_token: str) -> str:
    """
    Hash a raw refresh token with SHA-256.

    WHY: We never store the raw token in Redis. If Redis is compromised,
    the attacker only gets hashes — useless without the raw token (which
    only the user's browser cookie has).
    """
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def _rt_key(token_hash: str) -> str:
    """Redis key for a specific refresh token."""
    return f"rt:{token_hash}"


def _rt_family_key(family_id: str) -> str:
    """Redis key for a token family (set of all token hashes in the family)."""
    return f"rt_family:{family_id}"


def _rt_user_families_key(user_id: int) -> str:
    """Redis key for a user's set of family IDs (tracks all their sessions)."""
    return f"rt_user:{user_id}"


def create_refresh_token(user_id: int) -> str:
    """
    Generates a new refresh token and stores its hash in Redis.

    HOW IT WORKS:
    1. Generate a random opaque token (secrets.token_urlsafe)
       - This is NOT a JWT — it's just a random string, no payload
       - 48 bytes = 64 characters of URL-safe base64 = very hard to guess

    2. Create a "family_id" — a unique ID for this login session
       - All refresh tokens created from the same login share a family_id
       - This lets us revoke an ENTIRE session if we detect a replay attack

    3. Store in Redis:
       - rt:{hash} → "user_id|family_id" (the actual token record)
       - rt_family:{family_id} → set of token hashes   (for family revocation)
       - rt_user:{user_id} → set of family IDs         (for revoking all sessions)

    4. All keys have a TTL = refresh token lifetime (7 days)
       - Redis automatically deletes them after expiry — no cleanup jobs needed!

    RETURNS: the raw token string (to be placed in the HttpOnly cookie)
    """
    raw_token = secrets.token_urlsafe(48)
    token_hash = _hash_token(raw_token)
    family_id = secrets.token_urlsafe(16)

    # Store the token record
    _redis.setex(
        _rt_key(token_hash),
        REFRESH_TOKEN_EXPIRE_SECONDS,
        f"{user_id}|{family_id}",
    )

    # Track this token hash in its family
    family_key = _rt_family_key(family_id)
    _redis.sadd(family_key, token_hash)
    _redis.expire(family_key, REFRESH_TOKEN_EXPIRE_SECONDS)

    # Track this family under the user
    user_key = _rt_user_families_key(user_id)
    _redis.sadd(user_key, family_id)
    _redis.expire(user_key, REFRESH_TOKEN_EXPIRE_SECONDS)

    return raw_token


def rotate_refresh_token(old_raw_token: str) -> tuple[str, int]:
    """
    Validates an existing refresh token and issues a NEW one (rotation).

    TOKEN ROTATION explained:
    - Each refresh token can only be used ONCE
    - After use, it's deleted and a brand-new token is created
    - The new token inherits the same family_id (same login session)

    WHY ROTATION?
    - If an attacker steals a refresh token and tries to use it AFTER
      the real user already used it, the old token won't exist in Redis
    - We detect this as a "replay attack" and delete ALL tokens in that family
    - This forces the attacker AND the real user to log in again (safe)

    RETURNS: (new_raw_token, user_id)
    RAISES:  HTTPException 401 if token is invalid/expired/already used
    """
    old_hash = _hash_token(old_raw_token)
    old_key = _rt_key(old_hash)
    rotated_marker_key = f"rotated:{old_hash}"

    # 1. Check if this token was ALREADY rotated (already used once)
    # If a rotated_marker exists, this old token is invalid — raise 401.
    rotated_info = _redis.get(rotated_marker_key)
    if rotated_info:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="auth.refresh_token_invalid",
        )

    # 2. Look up the old token in Redis (the "live" one)
    stored = _redis.get(old_key)
    if not stored:
        # Token not found — either expired naturally, or this is a replay attack.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="auth.refresh_token_invalid",
        )

    # Parse the stored value: "user_id|family_id"
    parts = stored.split("|", 1)
    if len(parts) != 2:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="auth.refresh_token_invalid",
        )

    user_id = int(parts[0])
    family_id = parts[1]

    # 3. Rotate!
    _redis.delete(old_key)
    family_key = _rt_family_key(family_id)
    _redis.srem(family_key, old_hash)

    # Create a new token in the SAME family
    new_raw = secrets.token_urlsafe(48)
    new_hash = _hash_token(new_raw)

    # Write the new token to Redis
    _redis.setex(
        _rt_key(new_hash),
        REFRESH_TOKEN_EXPIRE_SECONDS,
        f"{user_id}|{family_id}",
    )
    _redis.sadd(family_key, new_hash)
    _redis.expire(family_key, REFRESH_TOKEN_EXPIRE_SECONDS)

    # 4. Set a short-lived marker so we know this old hash was already rotated.
    # This prevents the old hash from being used again (replay protection).
    _redis.setex(rotated_marker_key, 30, "used")

    return new_raw, user_id


def revoke_refresh_token(raw_token: str) -> None:
    """
    Revokes a single refresh token (used during logout).

    Simply deletes it from Redis — the token can never be used again.
    """
    token_hash = _hash_token(raw_token)
    stored = _redis.get(_rt_key(token_hash))
    if stored:
        parts = stored.split("|", 1)
        if len(parts) == 2:
            family_id = parts[1]
            _redis.srem(_rt_family_key(family_id), token_hash)
        _redis.delete(_rt_key(token_hash))


def revoke_all_user_tokens(user_id: int) -> None:
    """
    Revokes ALL refresh tokens for a user (used during password reset).

    This ensures that if someone resets their password, ALL existing
    sessions (on all devices/browsers) are immediately killed.

    HOW: walks through user's families → each family's tokens → deletes all.
    """
    user_key = _rt_user_families_key(user_id)
    family_ids = _redis.smembers(user_key) or set()

    for family_id in family_ids:
        family_key = _rt_family_key(family_id)
        token_hashes = _redis.smembers(family_key) or set()
        for token_hash in token_hashes:
            _redis.delete(_rt_key(token_hash))
        _redis.delete(family_key)

    _redis.delete(user_key)


# ═══════════════════════════════════════════════════════════
#  COOKIE HELPERS
# ═══════════════════════════════════════════════════════════

def set_refresh_cookie(response: Response, raw_token: str) -> None:
    """
    Sets the refresh token as an HttpOnly cookie on the response.

    Cookie attributes explained:
    - httponly=True  → JavaScript CANNOT read this cookie (prevents XSS theft)
    - secure=...    → Only sent over HTTPS (prevents interception over HTTP)
    - samesite="lax"→ Sent on same-site requests + top-level navigations
                      (prevents CSRF while allowing normal link navigation)
    - max_age=...   → Cookie expires after N seconds (matches Redis TTL)
    - path="/"      → Cookie is sent for ALL requests to our API
    """
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=raw_token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        max_age=REFRESH_TOKEN_EXPIRE_SECONDS,
        path="/",
        domain=settings.cookie_domain,
    )


def clear_refresh_cookie(response: Response) -> None:
    """Clears the refresh token cookie (used during logout)."""
    response.delete_cookie(
        key=REFRESH_COOKIE_NAME,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        path="/",
        domain=settings.cookie_domain,
    )
