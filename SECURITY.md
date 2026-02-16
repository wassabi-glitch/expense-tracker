# Security Configuration Guide (v1)

This project now includes security hardening in the API:
- Strict CORS (configured via env)
- Trusted host validation
- Optional HTTPS redirect in production
- Security response headers (including CSP)

## 1) Environment Variables

Use `.env` for local development. Use your hosting provider's secret manager for production.

Required:

```env
DATABASE_HOSTNAME=localhost
DATABASE_PORT=5432
DATABASE_USERNAME=postgres
DATABASE_PASSWORD=your_db_password
DATABASE_NAME=ExpenseTracker

SECRET_KEY=replace_with_long_random_secret
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60

REDIS_URL=redis://localhost:6379/0

CORS_ORIGINS=http://localhost:5173
TRUSTED_HOSTS=localhost,127.0.0.1,testserver
IS_PRODUCTION=false
```

## 2) Production Example

```env
CORS_ORIGINS=https://your-frontend-domain.com
TRUSTED_HOSTS=your-api-domain.com
IS_PRODUCTION=true
```

Notes:
- `IS_PRODUCTION=true` enables HTTPS redirect and HSTS header.
- Keep only real domains in `CORS_ORIGINS` and `TRUSTED_HOSTS`.
- Do not commit real secrets to git.

## 3) Pre-Deploy Security Checklist

- Rotate `SECRET_KEY` and DB credentials if they were ever committed.
- Confirm `.env` is ignored by git.
- Ensure Redis and Postgres are not publicly exposed in production.
- Verify API works behind HTTPS.
- Verify frontend can call API from allowed origin only.

