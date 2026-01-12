# Orbit Backend (FastAPI)

This directory hosts the new Orbit backend (separate from the ingestion service). The stack follows the plan in `backend-implementation-plan.md`: FastAPI, async SQLAlchemy, JWT auth with bcrypt hashing, and Postgres.

## Quickstart
- Install deps: `pip install -r backend/requirements.txt`
- Export env vars (see below) or create a `.env` alongside `backend/requirements.txt`.
- Run dev server: `uvicorn app.main:app --reload --app-dir backend`
- Apply DB migrations: `alembic -c backend/alembic.ini upgrade head`

## Required env
- `DATABASE_URL` (e.g., `postgresql+asyncpg://postgres:postgres@localhost:5432/orbit`)
- `JWT_SECRET_KEY` (strong secret)
- `JWT_ALGORITHM` (default `HS256`)
- `ACCESS_TOKEN_EXPIRES_MINUTES` (default `30`)
- `REFRESH_TOKEN_EXPIRES_MINUTES` (default `10080`)
- `CORS_ORIGINS` (JSON list of origins; defaults to `["*"]` if unset)
- `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` (required for Google Sign-In)
- `GOOGLE_ALLOWED_REDIRECTS` (JSON list of allowed OAuth redirect URIs)
- `GOOGLE_STATE_TTL_SECONDS` (optional; state token lifetime, default `600`)
- Optional SMTP/email (used for password reset & onboarding invites):
  - `SMTP_HOST`, `SMTP_PORT` (default `587`)
  - `SMTP_USER`, `SMTP_PASSWORD`
  - `SMTP_FROM`
  - `SMTP_USE_TLS` (default `true`)
  - `PASSWORD_RESET_EMAILS_PER_HOUR` (default `5`, in-process limiter)
  - `INVITE_EMAILS_PER_HOUR` (default `20`)
- Sample file: see `backend/env.sample`.

## Current scope
- Health endpoints at `/api/health/live` and `/api/health/ready`.
- Auth endpoints at `/api/auth/signup`, `/signin`, `/refresh`, `/me` with bcrypt hashing and JWT access/refresh tokens.
- Google OAuth endpoints at `/api/auth/google/init` and `/api/auth/google/complete`.
- Onboarding endpoints at `/api/onboarding/*` (status, step1-4, complete, skip).
- Password reset flow at `/api/auth/password/request|verify|reset` (SMTP-backed, rate limited).
- Async Postgres session helper in `app/db/session.py`; `User` model/schema in `app/models/user.py`.

## Notes
- Alembic (async) now includes migration `da2fd07bfb00_add_core_domain_tables` covering workspaces, projects, scopes, documents, templates, comments, quotations/proposals, usage metrics, and password reset tables.
- Postgres is the assumed runtime datastore across environments; `.env` defaults target a local Postgres instance.
- Billing/Stripe integration is deferred—no payment gateway code or env vars are loaded yet.
- Token rotation/blacklist and email verification flows are placeholders to be implemented per plan.
- See `docs/auth_onboarding_plan.md` for the detailed password reset + onboarding workplan.


