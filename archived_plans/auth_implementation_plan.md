# Step 2: Auth System Completion

Upgrade from single short-lived JWT access tokens (stored in localStorage) to a secure **dual-token architecture**: short-lived access tokens (in memory) + long-lived refresh tokens (in HttpOnly cookies, stored in Redis).

## Current State

| Aspect | Current | Problem |
|---|---|---|
| Access token TTL | 60 min | Too long for a single token; if stolen, attacker has 1hr window |
| Token storage | `localStorage` | Vulnerable to XSS attacks |
| Refresh mechanism | None | User gets logged out after token expires |
| Logout | Frontend-only (delete localStorage) | Token remains valid server-side |
| Google OAuth | Returns token in URL hash | Works, but needs refresh token too |

## Proposed Architecture

```
Login/OAuth → Backend issues:
  1. Access token  (JWT, 15 min TTL, returned in JSON body)
  2. Refresh token (opaque, 7 day TTL, Set-Cookie: HttpOnly, Secure, SameSite=Lax)

Frontend stores access token in memory (JS variable, NOT localStorage).

On 401 → Frontend calls POST /auth/refresh (cookie sent automatically)
  → Backend validates refresh token in Redis
  → Issues NEW access token + NEW refresh token (rotation)
  → Old refresh token is invalidated

Logout → POST /auth/logout
  → Backend deletes refresh token family from Redis
  → Clears cookie
```

## User Review Required

> [!IMPORTANT]
> **Breaking change**: After this update, all existing user sessions will be invalidated. Users will need to log in again. This is expected and necessary since the token format changes.

> [!IMPORTANT]
> **Access token TTL reduction**: Changing from 60 min → 15 min. The refresh mechanism compensates for this, so users won't notice any difference in UX.

---

## Proposed Changes

### Backend — Config

#### [MODIFY] [config.py](file:///c:/Users/me/Desktop/MyPROJECTS/ExpenseTracker/config.py)
- Add `refresh_token_expire_days: int = 7`
- Add `access_token_expire_minutes: int = 15` (reduce from 60)
- Add `cookie_secure: bool = True` (for HTTPS in production)
- Add `cookie_samesite: str = "lax"`

---

### Backend — Refresh Token Storage (Redis)

#### [MODIFY] [oauth2.py](file:///c:/Users/me/Desktop/MyPROJECTS/ExpenseTracker/app/oauth2.py)
- Add `create_refresh_token(user_id)` → generates opaque token (secrets.token_urlsafe), stores hash in Redis with key `rt:{token_hash}` → value `{user_id, family_id, created_at}`
- Add `verify_refresh_token(token)` → looks up hash in Redis, returns user_id or raises 401
- Add `revoke_refresh_token(token)` → deletes from Redis
- Add `revoke_all_user_tokens(user_id)` → scans and deletes all `rt:*` keys for a user (for password reset / account compromise)
- Reduce `ACCESS_TOKEN_EXPIRE_MINUTES` to 15
- Add `set_refresh_cookie(response, token)` and `clear_refresh_cookie(response)` helpers

**Why Redis (not DB)?**
- Refresh tokens are session-like data: high read frequency, auto-expiry via TTL
- Redis `SETEX` handles expiration automatically — no cleanup jobs needed
- We already have Redis running for rate limiting

**Token rotation design:**
- Each refresh token belongs to a "family" (random ID created at login)
- On refresh: old token is deleted, new token is created with same family_id
- If a revoked token is reused (replay attack), delete ALL tokens in that family

---

### Backend — New Endpoints

#### [MODIFY] [auth.py](file:///c:/Users/me/Desktop/MyPROJECTS/ExpenseTracker/app/routers/auth.py)

**`POST /auth/refresh`** (new)
- Read refresh token from `HttpOnly` cookie
- Validate in Redis → get user_id + family_id
- Delete old token from Redis
- Issue new access token (JWT) + new refresh token (Redis + cookie)
- If token not found in Redis → potential replay → revoke entire family
- Rate limited

**`POST /auth/logout`** (new)
- Read refresh token from cookie
- Delete from Redis
- Clear cookie
- Return 200

#### [MODIFY] [users.py](file:///c:/Users/me/Desktop/MyPROJECTS/ExpenseTracker/app/routers/users.py)
- Update [login()](file:///c:/Users/me/Desktop/MyPROJECTS/ExpenseTracker/app/routers/users.py#127-189) → also create refresh token + set cookie
- Update response to include [access_token](file:///c:/Users/me/Desktop/MyPROJECTS/ExpenseTracker/app/oauth2.py#19-32) in body (as before)

#### [MODIFY] [oauth_google.py](file:///c:/Users/me/Desktop/MyPROJECTS/ExpenseTracker/app/routers/oauth_google.py)
- Update [google_callback()](file:///c:/Users/me/Desktop/MyPROJECTS/ExpenseTracker/app/routers/oauth_google.py#82-174) → set refresh token cookie before redirect
- Keep access token in URL hash for frontend to capture

#### [MODIFY] [auth.py](file:///c:/Users/me/Desktop/MyPROJECTS/ExpenseTracker/app/routers/auth.py)
- Update [reset_password()](file:///c:/Users/me/Desktop/MyPROJECTS/ExpenseTracker/app/routers/auth.py#182-256) → after password reset, call `revoke_all_user_tokens(user_id)` to invalidate all sessions

---

### Backend — Schemas

#### [MODIFY] [schemas.py](file:///c:/Users/me/Desktop/MyPROJECTS/ExpenseTracker/app/schemas.py)
- Add `RefreshResponse` schema ([access_token](file:///c:/Users/me/Desktop/MyPROJECTS/ExpenseTracker/app/oauth2.py#19-32), `token_type`)

---

### Backend — CORS

#### [MODIFY] [main.py](file:///c:/Users/me/Desktop/MyPROJECTS/ExpenseTracker/app/main.py)
- Add `allow_credentials=True` to CORS middleware (required for cookies)

---

### Frontend — API Client

#### [MODIFY] [api.js](file:///c:/Users/me/Desktop/MyPROJECTS/ExpenseTracker/frontend/src/lib/api.js)
- Store access token in **module-level variable** (not localStorage)
- Add `credentials: "include"` to all `fetch()` calls (sends cookies)
- On 401 response: attempt `POST /auth/refresh` first, retry original request. If refresh also fails → redirect to sign-in
- Update [signin()](file:///c:/Users/me/Desktop/MyPROJECTS/ExpenseTracker/frontend/src/lib/api.js#87-128) → store returned access_token in memory variable
- Update [logout()](file:///c:/Users/me/Desktop/MyPROJECTS/ExpenseTracker/frontend/src/lib/api.js#41-46) → call `POST /auth/logout`, then clear memory variable
- Update [isLoggedIn()](file:///c:/Users/me/Desktop/MyPROJECTS/ExpenseTracker/frontend/src/lib/api.js#247-250) → check memory variable instead of localStorage

#### [MODIFY] [AuthCallback.jsx](file:///c:/Users/me/Desktop/MyPROJECTS/ExpenseTracker/frontend/src/features/auth/AuthCallback.jsx)
- Read access_token from URL hash → store in memory (not localStorage)
- Refresh token cookie is already set by backend during Google OAuth

#### [MODIFY] [App.jsx](file:///c:/Users/me/Desktop/MyPROJECTS/ExpenseTracker/frontend/src/App.jsx)
- On app mount: call `POST /auth/refresh` to get a fresh access token (silent refresh)
- This handles page reloads (since memory variable is lost on reload)

---

## Verification Plan

### Automated Tests
Add to [tests/test_auth.py](file:///c:/Users/me/Desktop/MyPROJECTS/ExpenseTracker/tests/test_auth.py):
- Login returns access token in body + sets refresh cookie
- `POST /auth/refresh` with valid cookie → new access + new cookie
- `POST /auth/refresh` with expired/invalid cookie → 401
- Used refresh token cannot be reused (rotation)
- Replay of revoked token → entire family revoked
- `POST /auth/logout` → cookie cleared, refresh token invalid
- Password reset → all refresh tokens revoked
- Google OAuth callback sets refresh cookie

```bash
pytest -q --cov=app --cov-report=term-missing
npm run lint
npm run build
```

### Manual Verification
- Sign in → verify access token works for API calls
- Wait 15+ min or manually expire → verify auto-refresh kicks in transparently
- Refresh page → verify silent refresh restores session
- Sign out → verify refresh token is invalidated server-side
- Open two tabs → verify both sessions work independently
