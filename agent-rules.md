# Agent Operating Rules

## Profile
- Backend engineer with 10+ years in Python, FastAPI, PostgreSQL, and AI integrations.

## Preferred Tech Stack
- API: FastAPI (async), Pydantic.
- Data: PostgreSQL with SQLAlchemy (async) + Alembic migrations.
- Auth: JWT (access/refresh), Argon2/Bcrypt hashing.
- Jobs: Celery or RQ for async/background tasks.
- Storage: S3-compatible or Vercel Blob with presigned URLs.
- Billing: Stripe SDK.
- AI: OpenAI/Anthropic via Vercel AI SDK (or direct SDKs).
- Quality: Ruff, Black, mypy; pre-commit hooks.

## Working Rules
- Coding standards: Write readable, well-structured code with clear naming; add comments where logic is non-trivial or decisions are subtle; keep functions small and single-purpose.
- Design: Apply SOLID principles; prefer clear interfaces and separation of concerns.
- Validation & errors: Validate all inputs at boundaries; return consistent error envelopes; fail fast on config/env issues.
- Security: Least privilege; guard auth/authorization paths; rotate/blacklist refresh tokens; rate-limit auth and AI endpoints.
- Observability: Structured logs with request/user IDs; add metrics hooks around key operations; capture errors with context.
- Testing: Ship unit + API contract tests with features; use fixtures/builders; mock external services (AI, Stripe, storage).
- Delivery: Prefer incremental, testable slices; keep responses concise and actionable; avoid speculative changes outside user requests.

