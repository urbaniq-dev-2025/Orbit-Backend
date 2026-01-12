# Onboarding Service Design

This document expands the onboarding portion of `BACKEND-REQUIREMENTS.md` into concrete backend work items.

---

## Goals
- Capture the 4-step onboarding flow (workspace → team → goals → plan) plus skip/completion flows.
- Persist in-progress state so users can resume across sessions.
- Seed the initial workspace/team records when necessary.
- Provide a small, well-documented API surface that the frontend can consume immediately, while allowing upgrades (Stripe, external messaging) later.

---

## Data Model

### `users` table
- Add columns:
  - `onboarding_step` (`VARCHAR`): tracks the last completed step (`none`, `workspace`, `team`, `goals`, `plan`, `complete`).
  - `onboarding_state` (`JSONB`, nullable): scratchpad for step payloads (branding, invites, goals, plan choice).
  - Existing `onboarding_completed` boolean will be added if absent (default `false`).

### `workspace_members`
- Invitations already supported via `invited_email`. Onboarding step 2 will reuse this with status `pending`.

### Migration
- Create migration `20260107_0004_add_onboarding_columns.py` that adds the new columns with sensible defaults and indexes as needed.

---

## Service Abstractions

### `app/services/onboarding.py`
Responsibilities:
1. Fetch/save onboarding state slices.
2. Create the first workspace if missing (step 1 or skip).
3. Queue member invitations (step 2) using existing workspace service.
4. Store goals (step 3) and plan selection (step 4).
5. Mark completion and emit events (for now, log only).

Utilities inside:
- `OnboardingState` Pydantic model for the JSON payload.
- Helper to compute next step and to convert internal state to API DTO.

---

## API Surface

All endpoints authenticated with current user context; responses use camelCase keys to align with frontend.

| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/api/onboarding/status` | Returns `{ step, stepsCompleted, workspaceCreated, invitesPending, planSelected }` plus snapshots of saved data. |
| `POST` | `/api/onboarding/step1` | Payload: `{ name, primaryColor?, secondaryColor?, logoUrl?, websiteUrl?, teamSize?, dataHandling? }`. Creates workspace if absent or updates branding if a workspace exists. Returns updated status. |
| `POST` | `/api/onboarding/step2` | Payload: `{ teamSize, invites: string[] }`. Stores invites and triggers workspace invitations (email send stubbed/logged, rate-limited similar to password reset). |
| `POST` | `/api/onboarding/step3` | Payload: `{ goals: string[], customGoal? }`. Stores goals (freeform + enums). |
| `POST` | `/api/onboarding/step4` | Payload: `{ plan: "starter" | "growth" | "enterprise", billingCountry?, companySize? }`. Stores selection and returns a `checkoutUrl` placeholder. |
| `POST` | `/api/onboarding/complete` | Marks onboarding complete, ensures workspace exists, clears volatile state. |
| `POST` | `/api/onboarding/skip` | Creates minimal workspace (if missing), marks onboarding complete, saves reason (optional). |

Error model: reuse existing FastAPI HTTPException with `detail` for now; future iteration can wrap in `{ "error": { ... } }`.

---

## Security & Validation
- Ensure user is active and not already complete when calling step endpoints; return 409 if onboarding already done.
- Validate workspace slug uniqueness (if provided).
- Rate limit invitations per user (reuse email dispatcher limiter by key `invite:<email>` or add simple counter).
- Sanitise strings (trim, limit lengths).

---

## Implementation Plan
1. **Migration**: add columns to `users`.
2. **Schemas**: create onboarding request/response models in `app/schemas/onboarding.py`.
3. **Service Layer**: implement `app/services/onboarding.py` with CRUD helpers.
4. **Routes**: add new router `app/api/routes/onboarding.py`, include under `/api/onboarding` in `api_router`.
5. **Workspace Service Enhancements**: expose functions to upsert branding and invite users.
6. **Email integration**: reuse `EmailDispatcher` for invitation emails (stub when SMTP missing).
7. **Tests**: add `backend/tests/test_onboarding.py` covering status fetch, each step, completion/skip, and invalid transitions.
8. **Docs**: update README + plan doc once endpoints exist.

---

## Future Enhancements
- Connect Step 4 to real Stripe checkout session.
- Emit analytics / activity log entries on each step.
- Allow multi-workspace onboarding.
- Localize email templates and copy rewriting.




