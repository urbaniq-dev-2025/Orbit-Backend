# Authentication & Onboarding Work Plan

This note breaks down the remaining work required to satisfy the **"User Authentication & Onboarding"** feature set described in `BACKEND-REQUIREMENTS.md`.

---

## 1. Password Reset (6-digit code)

### Data Model
- Reuse existing `password_resets` table (columns: `user_id`, `code`, `expires_at`, `consumed_at`, etc.).

### Endpoints
| Method | Path | Auth | Purpose |
| ------ | ---- | ---- | ------- |
| `POST` | `/api/auth/password/request` | Public | Accepts `{ "email": "user@example.com" }`, issues a 6-digit code, stores hashed code + expiry (15 minutes), triggers email job. Always returns 202 to prevent account enumeration. |
| `POST` | `/api/auth/password/verify` | Public | Accepts `{ "email": "...", "code": "123456" }`, validates code, returns one-time token (or opaque ID) for password change. |
| `POST` | `/api/auth/password/reset` | Public | Accepts `{ "email": "...", "code": "123456", "newPassword": "..." }` **or** `{ "resetToken": "...", "newPassword": "..." }`. Updates password, revokes outstanding reset codes. |

### Implementation Notes
- Store codes as hashed strings (e.g. SHA256) to avoid leakage. ✅
- Built-in in-process rate limiting guards password reset emails (default 5/hour per address) and SMTP delivery falls back to logging when credentials are missing. ✅
- Optional: emit events or audit log entries.

### Tasks
1. Create Pydantic schemas (`PasswordResetRequest`, `PasswordResetVerify`, `PasswordResetComplete`).
2. Implement service helpers for issuing, validating, and consuming reset codes.
3. Wire email sending hook (stubbed logging if SMTP not configured).
4. Add tests covering happy path, expired codes, wrong code, multiple requests.

---

## 2. Multi-step Onboarding

Target flow aligns with the four frontend steps: workspace setup, team, goals, plan.

### API Surface
| Method | Path | Auth | Purpose |
| ------ | ---- | ---- | ------- |
| `GET` | `/api/onboarding/status` | Auth required | Returns progress object: current step, completed steps, stored data. |
| `POST` | `/api/onboarding/step1` | Auth required | Payload includes workspace name, slug (optional), logo URL, brand colors, website. Creates workspace + owner membership, persists branding. |
| `POST` | `/api/onboarding/step2` | Auth required | Accepts team size + invitation emails; enqueues invites and returns pending list. |
| `POST` | `/api/onboarding/step3` | Auth required | Saves product goals (enum array / freeform). |
| `POST` | `/api/onboarding/step4` | Auth required | Captures selected plan/tier; returns Stripe checkout link (placeholder). |
| `POST` | `/api/onboarding/complete` | Auth required | Marks onboarding complete, toggles `user.onboarding_completed = True`. |
| `POST` | `/api/onboarding/skip` | Auth required | Skips remaining steps, still ensures workspace exists. |

### Storage
- Extend existing models:
  - `users`: already has `onboarding_completed` boolean.
  - Add `onboarding_state` JSONB column (either on `users` or new `onboarding_progress` table) to store interim data. (To be implemented.)
  - Invitations can reuse `workspace_members` with `invited_email`.

### Tasks
1. Design state persistence (new table vs. JSON column).
2. Implement status retrieval + helper to map backend state to FE stepper.
3. Build each step endpoint, reusing workspace services.
4. Integrate with Stripe stub (plan returns fake checkout URL for now).
5. Unit tests + integration tests covering step order, skip, resume.

---

## 3. Supporting Enhancements

1. **Session / JWT updates**
   - Ensure onboarding endpoints enforce authenticated user.
   - Optionally embed onboarding status in `/api/auth/me`.
2. **Rate limiting & security**
   - Add TODO placeholders or use simple in-memory limiter for reset requests.
3. **Error model**
   - Align error responses with doc (wrap in `{ "error": { ... } }`).
4. **Docs**
   - Update `backend/README.md` and API reference once endpoints land.

---

## Proposed Implementation Order
1. Password reset service + endpoints.
2. Onboarding data model changes (migration).
3. Onboarding endpoints (status + steps).
4. Integrations/tests/documentation updates.

Each major deliverable will be raised as its own PR/commit with tests.


