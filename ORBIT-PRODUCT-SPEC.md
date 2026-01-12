# Orbit — Product Requirements Document

> **Version:** 1.0
> **Last Updated:** December 2024
> **Purpose:** Backend development specification for Cursor/AI agents

---

## Executive Summary

**Orbit** is an AI-powered SaaS platform that transforms unstructured project documents into clear, structured scope definitions. Users upload documents (contracts, briefs, emails) and Orbit extracts, organizes, and presents actionable scope items with AI-assisted analysis.

**Core Value Proposition:** "Define. Decide. Deliver." — Turn ambiguity into clarity.

**Target Users:** Project managers, consultants, agencies, product teams, freelancers.

---

## Brand Identity

- **Primary Color:** Orange (#f97316, #ea580c, #dc2626)
- **Logo:** Open arc with node at origin position (symbolizes "begin with focus")
- **Tone:** Professional, calm, intelligent, trustworthy

---

## Application Architecture

### Tech Stack (Frontend - Already Built)

- **Framework:** Next.js 16 (App Router)
- **Styling:** Tailwind CSS v4
- **UI Components:** shadcn/ui
- **State Management:** React hooks, localStorage (temporary)
- **Icons:** Lucide React

### Tech Stack (Backend - To Be Built)

- **Database:** Supabase (PostgreSQL) or Neon
- **Authentication:** Supabase Auth (email/password + OAuth)
- **File Storage:** Supabase Storage or Vercel Blob
- **AI Processing:** Vercel AI SDK with OpenAI/Anthropic
- **Payments:** Stripe (subscriptions)

---

## User Flows

### Flow 1: Authentication

```
Landing (/) → Sign Up → Email Verification → Onboarding (4 steps) → Dashboard
                ↓
            Sign In → Dashboard
```

### Flow 2: Onboarding (Post-Signup)

```
Step 1: Workspace Setup
  - Workspace name (required)
  - Logo upload (optional)
  - Brand color selection (optional)

Step 2: Team & Privacy
  - Team size selection (solo/small/large/enterprise)
  - Invite teammates (optional, email + role)
  - Data handling preference (standard/enhanced)

Step 3: Goals
  - Primary use case selection (multi-select):
    - Scope Definition
    - Requirement Tracking
    - Client Collaboration
    - Delivery Planning

Step 4: Plan Selection
  - Free / Pro / Enterprise tiers
  - Monthly/Annual toggle
  - Stripe checkout integration
```

### Flow 3: Core Product Usage

```
Dashboard → Upload Document(s) → AI Processing → Scope View → Edit/Collaborate → Export
```

---

## Database Schema

### Tables

#### `users`
```sql
CREATE TABLE users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email VARCHAR(255) UNIQUE NOT NULL,
  full_name VARCHAR(255),
  avatar_url TEXT,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

#### `workspaces`
```sql
CREATE TABLE workspaces (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name VARCHAR(255) NOT NULL,
  slug VARCHAR(255) UNIQUE NOT NULL,
  logo_url TEXT,
  brand_color VARCHAR(7) DEFAULT '#f97316',
  owner_id UUID REFERENCES users(id) ON DELETE CASCADE,
  team_size VARCHAR(50), -- 'solo', 'small', 'large', 'enterprise'
  data_handling VARCHAR(50) DEFAULT 'standard', -- 'standard', 'enhanced'
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

#### `workspace_members`
```sql
CREATE TABLE workspace_members (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id UUID REFERENCES workspaces(id) ON DELETE CASCADE,
  user_id UUID REFERENCES users(id) ON DELETE CASCADE,
  role VARCHAR(50) DEFAULT 'member', -- 'owner', 'admin', 'member', 'viewer'
  invited_email VARCHAR(255),
  invited_at TIMESTAMP WITH TIME ZONE,
  joined_at TIMESTAMP WITH TIME ZONE,
  status VARCHAR(50) DEFAULT 'pending', -- 'pending', 'active', 'inactive'
  UNIQUE(workspace_id, user_id)
);
```

#### `projects`
```sql
CREATE TABLE projects (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id UUID REFERENCES workspaces(id) ON DELETE CASCADE,
  name VARCHAR(255) NOT NULL,
  description TEXT,
  status VARCHAR(50) DEFAULT 'active', -- 'active', 'archived', 'completed'
  created_by UUID REFERENCES users(id),
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

#### `scopes`
```sql
CREATE TABLE scopes (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
  title VARCHAR(255) NOT NULL,
  description TEXT,
  status VARCHAR(50) DEFAULT 'draft', -- 'draft', 'in_review', 'approved', 'rejected'
  confidence_score INTEGER DEFAULT 0, -- 0-100
  risk_level VARCHAR(50) DEFAULT 'low', -- 'low', 'medium', 'high'
  created_by UUID REFERENCES users(id),
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

#### `scope_sections`
```sql
CREATE TABLE scope_sections (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  scope_id UUID REFERENCES scopes(id) ON DELETE CASCADE,
  title VARCHAR(255) NOT NULL,
  content TEXT,
  section_type VARCHAR(50), -- 'deliverable', 'assumption', 'exclusion', 'constraint', 'dependency'
  order_index INTEGER DEFAULT 0,
  ai_generated BOOLEAN DEFAULT false,
  confidence_score INTEGER DEFAULT 0,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

#### `documents`
```sql
CREATE TABLE documents (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  scope_id UUID REFERENCES scopes(id) ON DELETE CASCADE,
  filename VARCHAR(255) NOT NULL,
  file_url TEXT NOT NULL,
  file_type VARCHAR(50), -- 'pdf', 'docx', 'txt', 'image'
  file_size INTEGER,
  processing_status VARCHAR(50) DEFAULT 'pending', -- 'pending', 'processing', 'completed', 'failed'
  extracted_text TEXT,
  uploaded_by UUID REFERENCES users(id),
  uploaded_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

#### `comments`
```sql
CREATE TABLE comments (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  scope_id UUID REFERENCES scopes(id) ON DELETE CASCADE,
  section_id UUID REFERENCES scope_sections(id) ON DELETE CASCADE,
  user_id UUID REFERENCES users(id) ON DELETE CASCADE,
  content TEXT NOT NULL,
  resolved BOOLEAN DEFAULT false,
  parent_id UUID REFERENCES comments(id), -- for threaded replies
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

#### `activity_log`
```sql
CREATE TABLE activity_log (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id UUID REFERENCES workspaces(id) ON DELETE CASCADE,
  user_id UUID REFERENCES users(id),
  action VARCHAR(100) NOT NULL, -- 'created_scope', 'uploaded_document', 'added_comment', etc.
  entity_type VARCHAR(50), -- 'scope', 'document', 'comment', 'project'
  entity_id UUID,
  metadata JSONB,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

#### `subscriptions`
```sql
CREATE TABLE subscriptions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id UUID REFERENCES workspaces(id) ON DELETE CASCADE,
  stripe_customer_id VARCHAR(255),
  stripe_subscription_id VARCHAR(255),
  plan VARCHAR(50) DEFAULT 'free', -- 'free', 'pro', 'enterprise'
  billing_cycle VARCHAR(50) DEFAULT 'monthly', -- 'monthly', 'annual'
  status VARCHAR(50) DEFAULT 'active', -- 'active', 'cancelled', 'past_due'
  current_period_start TIMESTAMP WITH TIME ZONE,
  current_period_end TIMESTAMP WITH TIME ZONE,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

#### `templates`
```sql
CREATE TABLE templates (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id UUID REFERENCES workspaces(id) ON DELETE CASCADE,
  name VARCHAR(255) NOT NULL,
  description TEXT,
  category VARCHAR(100), -- 'software', 'construction', 'consulting', 'marketing'
  sections JSONB NOT NULL, -- array of section templates
  is_public BOOLEAN DEFAULT false,
  created_by UUID REFERENCES users(id),
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

#### `favourites`
```sql
CREATE TABLE favourites (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id) ON DELETE CASCADE,
  scope_id UUID REFERENCES scopes(id) ON DELETE CASCADE,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  UNIQUE(user_id, scope_id)
);
```

---

## API Endpoints

### Authentication

```
POST   /api/auth/signup          - Register new user
POST   /api/auth/signin          - Sign in user
POST   /api/auth/signout         - Sign out user
POST   /api/auth/forgot-password - Request password reset
POST   /api/auth/reset-password  - Reset password with token
GET    /api/auth/me              - Get current user
POST   /api/auth/google          - OAuth with Google
```

### Onboarding

```
POST   /api/onboarding/workspace - Create workspace (step 1)
PUT    /api/onboarding/team      - Set team preferences (step 2)
PUT    /api/onboarding/goals     - Set user goals (step 3)
POST   /api/onboarding/subscribe - Create Stripe checkout (step 4)
GET    /api/onboarding/status    - Get onboarding completion status
```

### Workspaces

```
GET    /api/workspaces                    - List user's workspaces
POST   /api/workspaces                    - Create workspace
GET    /api/workspaces/:id                - Get workspace details
PUT    /api/workspaces/:id                - Update workspace
DELETE /api/workspaces/:id                - Delete workspace
POST   /api/workspaces/:id/invite         - Invite team member
GET    /api/workspaces/:id/members        - List members
PUT    /api/workspaces/:id/members/:uid   - Update member role
DELETE /api/workspaces/:id/members/:uid   - Remove member
```

### Projects

```
GET    /api/projects                - List projects in workspace
POST   /api/projects                - Create project
GET    /api/projects/:id            - Get project details
PUT    /api/projects/:id            - Update project
DELETE /api/projects/:id            - Delete project
```

### Scopes

```
GET    /api/scopes                  - List scopes (with filters)
POST   /api/scopes                  - Create scope
GET    /api/scopes/:id              - Get scope with sections
PUT    /api/scopes/:id              - Update scope
DELETE /api/scopes/:id              - Delete scope
POST   /api/scopes/:id/duplicate    - Duplicate scope
PUT    /api/scopes/:id/status       - Update scope status
GET    /api/scopes/:id/export       - Export scope (PDF/DOCX)
```

### Scope Sections

```
GET    /api/scopes/:id/sections           - List sections
POST   /api/scopes/:id/sections           - Add section
PUT    /api/scopes/:id/sections/:sid      - Update section
DELETE /api/scopes/:id/sections/:sid      - Delete section
PUT    /api/scopes/:id/sections/reorder   - Reorder sections
```

### Documents & AI Processing

```
POST   /api/documents/upload        - Upload document(s)
GET    /api/documents/:id           - Get document details
DELETE /api/documents/:id           - Delete document
GET    /api/documents/:id/status    - Get processing status
POST   /api/ai/extract              - Extract scope from documents
POST   /api/ai/suggest              - Get AI suggestions for section
POST   /api/ai/analyze              - Analyze scope for risks/gaps
```

### Comments

```
GET    /api/scopes/:id/comments     - List comments
POST   /api/scopes/:id/comments     - Add comment
PUT    /api/comments/:id            - Update comment
DELETE /api/comments/:id            - Delete comment
PUT    /api/comments/:id/resolve    - Resolve comment
```

### Templates

```
GET    /api/templates               - List templates
POST   /api/templates               - Create template
GET    /api/templates/:id           - Get template
PUT    /api/templates/:id           - Update template
DELETE /api/templates/:id           - Delete template
POST   /api/templates/:id/apply     - Apply template to scope
```

### Favourites

```
GET    /api/favourites              - List user's favourites
POST   /api/favourites              - Add to favourites
DELETE /api/favourites/:scopeId     - Remove from favourites
```

### Activity

```
GET    /api/activity                - Get activity feed
GET    /api/activity/workspace/:id  - Get workspace activity
```

### Billing (Stripe)

```
POST   /api/billing/checkout        - Create checkout session
POST   /api/billing/portal          - Create customer portal session
POST   /api/billing/webhook         - Stripe webhook handler
GET    /api/billing/subscription    - Get subscription status
```

---

## AI Processing Pipeline

### Document Upload Flow

1. User uploads document(s) via `/api/documents/upload`
2. Files stored in Supabase Storage / Vercel Blob
3. Background job triggered for processing
4. Text extraction based on file type:
   - PDF: Use pdf-parse or similar
   - DOCX: Use mammoth.js
   - Images: Use OCR (Tesseract or cloud service)
5. Extracted text stored in `documents.extracted_text`
6. Status updated to 'completed'

### AI Scope Extraction Flow

1. User triggers extraction via `/api/ai/extract`
2. Collect all extracted text from documents
3. Send to AI with structured prompt:

```
You are a scope definition expert. Analyze the following project documents and extract a structured scope.

Documents:
{extracted_text}

Extract and organize into these categories:
1. Deliverables - What will be delivered
2. Assumptions - What we're assuming to be true
3. Exclusions - What is explicitly NOT included
4. Constraints - Limitations and boundaries
5. Dependencies - External dependencies
6. Risks - Potential risks identified

For each item, provide:
- Title (brief)
- Description (detailed)
- Confidence score (0-100)
- Risk level if applicable (low/medium/high)

Respond in JSON format.
```

4. Parse AI response and create scope sections
5. Calculate overall confidence score
6. Return structured scope to frontend

### AI Suggestions Flow

When user requests suggestions for a section:

```
Given this scope context:
{scope_summary}

And this section:
{section_content}

Suggest improvements or additions. Consider:
- Clarity and specificity
- Missing details
- Potential ambiguities
- Industry best practices
```

---

## Row Level Security (RLS) Policies

### Users
- Users can read/update their own profile

### Workspaces
- Users can read workspaces they're members of
- Only owners can delete workspaces
- Only owners/admins can update workspace settings

### Projects & Scopes
- Users can CRUD within workspaces they're members of
- Viewers can only read

### Documents
- Users can upload to workspaces they're members of
- All members can read documents

---

## Feature Flags / Plan Limits

| Feature | Free | Pro | Enterprise |
|---------|------|-----|------------|
| Scopes per month | 5 | Unlimited | Unlimited |
| Team members | 1 | 10 | Unlimited |
| AI extractions/month | 10 | 100 | Unlimited |
| Document storage | 100MB | 10GB | Unlimited |
| Templates | Public only | + Custom | + Private library |
| Export formats | PDF | + DOCX | + Custom branding |
| Priority support | - | Email | Dedicated |
| SSO/SAML | - | - | Yes |

---

## Webhook Events (Stripe)

Handle these Stripe webhook events:

- `checkout.session.completed` - Create subscription
- `customer.subscription.updated` - Update plan
- `customer.subscription.deleted` - Cancel subscription
- `invoice.payment_failed` - Handle failed payment
- `invoice.paid` - Confirm payment

---

## Environment Variables Required

```env
# Database
DATABASE_URL=
DIRECT_URL=

# Supabase
NEXT_PUBLIC_SUPABASE_URL=
NEXT_PUBLIC_SUPABASE_ANON_KEY=
SUPABASE_SERVICE_ROLE_KEY=

# Authentication
NEXTAUTH_SECRET=
NEXTAUTH_URL=

# Google OAuth
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=

# AI
OPENAI_API_KEY=
# or
ANTHROPIC_API_KEY=

# Stripe
STRIPE_SECRET_KEY=
NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=
STRIPE_WEBHOOK_SECRET=

# File Storage
BLOB_READ_WRITE_TOKEN=
```

---

## Frontend Pages Reference

| Route | Description | Auth Required |
|-------|-------------|---------------|
| `/` | Sign up / Sign in | No |
| `/onboarding/step-1` | Workspace setup | Yes |
| `/onboarding/step-2` | Team & privacy | Yes |
| `/onboarding/step-3` | Goals selection | Yes |
| `/onboarding/step-4` | Plan selection | Yes |
| `/onboarding/success` | Onboarding complete | Yes |
| `/dashboard` | Main dashboard | Yes |
| `/dashboard/workspace` | Workspace settings | Yes |
| `/dashboard/templates` | Template library | Yes |
| `/dashboard/favourites` | Favourited scopes | Yes |
| `/dashboard/quotation` | Quotation builder | Yes |
| `/dashboard/scope/[id]` | Scope detail view | Yes |
| `/dashboard/create` | Create new scope | Yes |

---

## Testing Checklist

### Authentication
- [ ] Sign up with email/password
- [ ] Email verification flow
- [ ] Sign in with email/password
- [ ] Sign in with Google
- [ ] Password reset flow
- [ ] Session persistence
- [ ] Sign out

### Onboarding
- [ ] Step 1: Workspace creation
- [ ] Step 1: Logo upload
- [ ] Step 2: Team size selection
- [ ] Step 2: Team invites
- [ ] Step 3: Goal selection
- [ ] Step 4: Plan selection
- [ ] Step 4: Stripe checkout
- [ ] Skip functionality
- [ ] Data persistence across steps

### Core Features
- [ ] Document upload (PDF, DOCX, images)
- [ ] AI extraction
- [ ] Scope creation
- [ ] Section editing
- [ ] Comments
- [ ] Favourites
- [ ] Templates
- [ ] Export

### Billing
- [ ] Stripe checkout
- [ ] Subscription management
- [ ] Plan upgrades/downgrades
- [ ] Webhook handling

---

## Implementation Priority

### Phase 1: Foundation
1. Database setup with Supabase
2. Authentication (email + Google)
3. User and workspace CRUD
4. Basic RLS policies

### Phase 2: Core Product
1. Project and scope CRUD
2. Document upload and storage
3. AI extraction pipeline
4. Section management

### Phase 3: Collaboration
1. Team invites
2. Comments system
3. Activity feed
4. Real-time updates (optional)

### Phase 4: Monetization
1. Stripe integration
2. Plan limits enforcement
3. Billing portal

### Phase 5: Polish
1. Templates system
2. Export functionality
3. Favourites
4. Search

---

## Notes for Backend Developer

1. **Use Supabase client libraries** — They handle auth tokens automatically
2. **Implement proper error handling** — Return consistent error responses
3. **Add request validation** — Use Zod for schema validation
4. **Log important events** — Use structured logging
5. **Rate limit AI endpoints** — Prevent abuse
6. **Implement caching** — For templates and frequently accessed data
7. **Use database transactions** — For multi-table operations
8. **Test webhook handlers** — Use Stripe CLI for local testing

---

## Contact

For questions about this specification, refer to the frontend codebase or the product team.
