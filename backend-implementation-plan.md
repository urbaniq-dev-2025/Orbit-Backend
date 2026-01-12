# Orbit Backend Implementation Plan

Author: Backend | Date: Dec 2025 | Scope: Implement complete backend per `ORBIT-PRODUCT-SPEC.md` using Python + FastAPI + PostgreSQL + Vercel AI SDK/OpenAI/Anthropic + Stripe.

---

## 0. Objectives
- Deliver secure, multi-tenant backend for Orbit: auth, onboarding, workspace/projects/scopes, documents + AI extraction, collaboration, billing, exports.
- Ship in thin, testable slices; maintain consistent contracts and observability from day one.
- Enforce plan limits and RLS; make AI usage safe and rate limited.

## 1. Architecture at a Glance
- **API surface:** FastAPI app (`/api/*`) with async routes, Pydantic models, dependency-injected auth/session.
- **Data:** PostgreSQL with schemas from product spec; SQLAlchemy + Alembic migrations.
- **Auth:** First-party email/password + Google OAuth; JWT-based sessions (access/refresh), password reset tokens; optional NextAuth on frontend consuming these endpoints.
- **Storage:** Vercel Blob/S3-compatible bucket for documents; presigned upload/download.
- **AI:** Vercel AI SDK via server-side client, OpenAI/Anthropic backends; async wrappers with timeouts/retries.
- **Payments:** Stripe for checkout, portal, webhooks; plan state stored in `subscriptions`.
- **Background jobs:** Worker (Celery/RQ/Arq) for document processing, AI extraction, exports; scheduler (e.g., APScheduler/Cron) for cleanups.
- **Observability:** Structured logging, request IDs, OpenTelemetry hooks; error reporting pluggable.

## 2. Foundations & Tooling
- Repo scaffolding: `app/` for FastAPI, `core/config.py` for env guard, `.env.example`, `db/session.py` for async engine/sessionmaker.
- Dependencies: FastAPI, Uvicorn, Pydantic, SQLAlchemy (async), Alembic, httpx, python-jose/passlib, Stripe SDK, storage SDK (boto3 or vercel-blob), Vercel AI SDK (python client) or OpenAI/Anthropic SDKs.
- Code quality: Ruff/flake8, Black, mypy; pre-commit hooks.
- Testing: Pytest + httpx AsyncClient for API, faker for data, Alembic migrations applied in test db (Postgres container).
- CI: lint + test + mypy per PR; Alembic migration check.

## 3. Data Model & Authorization
- Apply tables: `users`, `workspaces`, `workspace_members`, `projects`, `scopes`, `scope_sections`, `documents`, `comments`, `activity_log`, `subscriptions`, `templates`, `favourites`.
- Authorization (app-layer):
  - Users can read/update self.
  - Workspace read for members; owner-only delete; owner/admin update.
  - Projects/Scopes/Sections CRUD scoped to workspace membership; viewers read-only.
  - Documents readable by workspace members; uploads restricted to members.
  - Comments scoped to scope/section; threaded; resolve toggle by author/admins.
  - Subscriptions linked to workspace; read/update by owner/admin.
- Seeds/fixtures for local dev and tests.

## 4. API Modules (FastAPI)
- **Auth:** signup, signin, refresh, signout (refresh blacklist), forgot/reset, me, google OAuth callback, email verify.
- **Onboarding:** workspace create (step1), team/privacy (step2), goals (step3), subscribe intent (step4), status.
- **Workspaces & Members:** CRUD, invite (email), list members, update role, remove member.
- **Projects:** CRUD within workspace.
- **Scopes:** list/filter, create, get, update, delete, duplicate, status update, export.
- **Scope Sections:** list, add, update, delete, reorder.
- **Documents & AI:** upload (presign), get, delete, status; ai/extract, ai/suggest, ai/analyze.
- **Comments:** list/add/update/delete/resolve.
- **Templates:** list/create/get/update/delete, apply.
- **Favourites:** list/add/remove.
- **Activity:** global/activity by workspace.
- **Billing:** checkout, portal, webhook, subscription status.

## 4.1 Suggested Module Layout (Python/FastAPI)
- `app/main.py`: FastAPI factory, middleware (CORS, logging, request ID), exception handlers.
- `app/core/`: config, logging, security (JWT), rate limiting helpers, feature flags/plan limits, pagination utilities.
- `app/db/`: engine/session, base model, Alembic migrations (in `migrations/`), repositories/unit-of-work helpers.
- `app/models/`: SQLAlchemy models (users, workspaces, workspace_members, projects, scopes, scope_sections, documents, comments, activity_log, subscriptions, templates, favourites).
- `app/schemas/`: Pydantic request/response models per feature.
- `app/api/`: routers per domain:
  - `auth/` (auth routes, oauth callbacks)
  - `onboarding/` (steps 1-4, status)
  - `workspaces/` (workspaces CRUD, members, invites)
  - `projects/`
  - `scopes/` (scopes + sections subrouter)
  - `documents/` (uploads/presign/status)
  - `ai/` (extract/suggest/analyze)
  - `comments/`
  - `templates/`
  - `favourites/`
  - `activity/`
  - `billing/`
- `app/services/`: business logic per domain (auth service, onboarding service, workspace/membership service, project service, scope/section service, document service, AI service, comment service, template service, billing service).
- `app/storage/`: blob client, presign helpers, upload callbacks.
- `app/ai/`: provider clients/wrappers, prompt builders, parsers, safety guards, rate limits.
- `app/billing/`: Stripe client wrappers, webhook verifier, plan resolver.
- `app/workers/`: Celery/RQ tasks for document processing, AI extraction, exports; schedules.
- `app/utils/`: shared utilities (slugging, hashing, email sending hooks, idempotency keys).
- `tests/`: unit and API tests per module; fixtures for db, auth, storage, AI, Stripe.

## 5. Cross-Cutting Concerns
- **Validation:** Pydantic models per route; shared error envelope `{error:{code,message}, data?:T}`.
- **AuthN/AuthZ:** FastAPI dependencies to hydrate user + workspace membership; role guard helper.
- **Plan limits:** Central module for limits (scopes/month, AI calls, members, storage, exports); enforced at route entry.
- **Idempotency:** For onboarding steps, invites, AI extractions (per scope/version), Stripe webhooks (idempotency key).
- **Transactions:** Multi-table writes (scope+sections, invites, duplicates) use transactions.
- **Pagination/filters:** Cursor/limit; whitelisted sort fields.
- **Rate limiting:** Especially auth, AI, export; per-user + per-workspace where relevant.
- **Logging/metrics:** Request ID, user/workspace IDs; log AI call metadata (not payloads); webhook audit.

## 5.1 Foundational Auth & Identity (M1 focus)
- **Models & storage:** `users` table with email, hashed_password, full_name, avatar_url, verification + reset tokens (separate table or columns with expiry), oauth identities table for Google.
- **Hashing/secrets:** Argon2/bcrypt via passlib; JWT signing keys; refresh token rotation with blacklist table or token versioning.
- **JWT flows:** Access token (short), refresh token (long); `me` endpoint to hydrate profile; middleware dependency to load user from Authorization header.
- **Email flows:** Signup issues verification token; password reset issues reset token; both stored with expiry and single-use semantics.
- **Google OAuth:** Endpoint to exchange code → user linkage; create user if new; skip password requirement.
- **Session security:** Refresh rotation, IP/user-agent binding optional, revoke on password change, email verification required gate.
- **Rate limits & brute-force protection:** Per-IP/email limits on signin/signup/reset; CAPTCHA hook optional.
- **Audit:** Login success/fail events; signup and verification logged to activity/audit stream.
- **Testing:** Unit tests for token issuance/validation, password hashing, expiry; API tests for signup/signin/refresh/reset/verify/me with happy + failure paths.

## 6. AI Pipeline
- **Extract:** Collect `documents.extracted_text` → prompt (per spec) → parse JSON → create sections → compute overall confidence → persist `scopes` + `scope_sections`.
- **Suggest:** Contextual improvements for a section using scope summary.
- **Analyze:** Risk/gap analysis; attach to scope metadata or return inline.
- **Safety:** Max tokens/size guard, content sanitization, retries with backoff, timeouts; mockable interface for tests.

## 7. Documents & Storage
- Upload via presigned URLs to Vercel Blob/S3; callbacks update DB.
- Record metadata in `documents`; lifecycle: pending → processing → completed/failed.
- Processing workers per type: PDF (pdf-parse), DOCX (mammoth), Images (OCR).
- Limits: file size per plan; allowed mime types; virus/malware scan hook (stub if not available).

## 8. Billing (Stripe)
- Checkout session creation per plan + billing cycle; attach workspace + user metadata.
- Portal session for self-serve management.
- Webhook handler for: `checkout.session.completed`, `customer.subscription.updated/deleted`, `invoice.payment_failed/paid`; signature verification; idempotent updates to `subscriptions`.
- Plan enforcement hooks reused by routes.

## 9. Exports
- `/api/scopes/:id/export` → PDF/DOCX; queue heavy jobs; plan-gated branding options.
- Cache or reuse generated exports when unchanged; signed download URLs.

## 10. Activity & Collaboration
- Comments with resolve/unresolve and threading; role checks.
- Activity log writes on key actions (scope created, document uploaded, comment added, status change).
- Activity feed endpoints with pagination and optional filters.

## 11. Templates & Favourites
- Templates: workspace-owned vs public; apply merges sections; cache public templates.
- Favourites: simple add/remove/list with uniqueness per user/scope.

## 12. Delivery Milestones
- **M1 (Foundation):** Env/config, Postgres schema + Alembic migrations, auth endpoints, CI/tests skeleton.
- **M2 (Onboarding & Workspaces):** Onboarding steps, workspaces/members, activity logging baseline.
- **M3 (Projects/Scopes/Sections):** CRUD + reorder + status + duplicate; plan limits wired.
- **M4 (Documents & AI):** Upload/storage, processing pipeline, ai/extract/suggest/analyze with rate limits.
- **M5 (Collab & Templates):** Comments, activity feed, templates, favourites.
- **M6 (Billing & Exports):** Stripe checkout/portal/webhooks, subscription state, export service.
- **M7 (Hardening):** Perf/caching, alerting, test coverage sweep, security review.

## 13. Testing Strategy
- Unit: validators, helpers, plan limit checks.
- API contract: pytest + httpx AsyncClient against FastAPI with mocked DB/AI/Stripe.
- Integration: test Postgres (container) with Alembic migrations; seed data; storage ops.
- Webhooks: signature verification fixtures; idempotency checks.
- Load/smoke: AI endpoints with mocks; export under load.

## 14. Environment & Secrets
- Required env per spec: `DATABASE_URL` (Postgres), `DIRECT_URL` (optional), JWT secrets, Google OAuth, OPENAI/ANTHROPIC keys, Stripe keys/webhook secret, BLOB/S3 credentials.
- Config guard fails fast on missing/invalid values; .env.example kept in sync.

## 15. Acceptance Criteria (per milestone)
- AuthZ: only workspace members can access workspace resources; viewers read-only; owners delete.
- Onboarding: progress persists; steps idempotent; skip works.
- AI: extraction produces sections with confidence; retries/timeouts logged; rate limits enforced.
- Billing: webhook-driven subscription state; plan limits active; checkout/portal reachable.
- Exports: PDF/DOCX downloadable for authorized users; branding gated by plan.

## 16. Next Actions
- Generate Postgres schema + Alembic migrations from spec; apply locally.
- Scaffold API route structure with shared middleware, logger, error handler, and Pydantic validators.
- Implement Auth + Onboarding first (M1 → M2) with tests; then proceed per milestones above.

