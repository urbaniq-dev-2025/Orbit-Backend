# Orbit Backend Requirements Document

> **Version:** 1.0  
> **Date:** January 2025  
> **Purpose:** Complete backend specification for Orbit frontend integration

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Application Overview](#application-overview)
3. [Database Schema](#database-schema)
4. [API Endpoints](#api-endpoints)
5. [Authentication & Authorization](#authentication--authorization)
6. [File Upload & Processing](#file-upload--processing)
7. [AI Processing Pipeline](#ai-processing-pipeline)
8. [Quotations System](#quotations-system)
9. [Proposals System](#proposals-system)
10. [Templates System](#templates-system)
11. [Feature Flags & Plan Limits](#feature-flags--plan-limits)
12. [Real-time Features](#real-time-features)
13. [Environment Variables](#environment-variables)
14. [Implementation Priority](#implementation-priority)

---

## Executive Summary

**Orbit** is an AI-powered SaaS platform that transforms unstructured project documents into clear, structured scope definitions. The backend must support:

- Multi-tenant workspace architecture
- AI-powered document processing and scope extraction
- Collaborative scope management with comments and reviews
- Quotation and proposal generation
- Template-based scope creation
- Subscription-based billing with Stripe
- Real-time collaboration features

**Tech Stack Recommendations:**
- **Database:** PostgreSQL (Supabase/Neon)
- **Authentication:** Supabase Auth or NextAuth.js
- **File Storage:** Supabase Storage or Vercel Blob
- **AI Processing:** OpenAI GPT-4 or Anthropic Claude
- **Payments:** Stripe
- **Real-time:** Supabase Realtime or Pusher
- **Background Jobs:** Inngest, Trigger.dev, or BullMQ

---

## Application Overview

### Core Features Identified from Frontend

1. **User Authentication & Onboarding**
   - Email/password signup and login
   - Google OAuth
   - Password reset with 6-digit verification code
   - 4-step onboarding flow (workspace, team, goals, pricing)

2. **Workspace Management**
   - Multi-workspace support
   - Team member invitations
   - Role-based access control (owner, admin, member, viewer)
   - Workspace branding (logo, colors)

3. **Scope Management**
   - Create scopes from documents, text, URLs, voice, or templates
   - AI-powered scope extraction
   - Section-based scope structure
   - Status workflow (draft, in_review, approved, rejected)
   - Comments and collaboration
   - Favourites/bookmarking
   - Export to PDF/DOCX

4. **Quotations System**
   - Generate quotations from scopes
   - Hour-based estimation (design, frontend, backend, QA)
   - Multiple quotation items per scope
   - Status tracking (draft, pending, approved)

5. **Proposals System**
   - Create proposal decks from scopes
   - Multiple templates (Executive, Modern Split, Minimal, etc.)
   - Client sharing with view tracking
   - Status tracking (draft, sent, viewed, approved, rejected, expired)
   - Analytics (view count, slide count)

6. **Templates System**
   - Pre-built scope templates
   - Custom template creation
   - Template categories (web, mobile, software, etc.)
   - Template application to new scopes

7. **Dashboard & Analytics**
   - Activity feed
   - Scope statistics
   - Gantt chart visualization
   - Quick notes/tasks

---

## Database Schema

### Core Tables

#### `users`
```sql
CREATE TABLE users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email VARCHAR(255) UNIQUE NOT NULL,
  email_verified BOOLEAN DEFAULT false,
  password_hash TEXT,
  first_name VARCHAR(100),
  last_name VARCHAR(100),
  full_name VARCHAR(255),
  avatar_url TEXT,
  provider VARCHAR(50) DEFAULT 'email', -- 'email', 'google'
  provider_id VARCHAR(255), -- OAuth provider user ID
  onboarding_completed BOOLEAN DEFAULT false,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_provider ON users(provider, provider_id);
```

#### `workspaces`
```sql
CREATE TABLE workspaces (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name VARCHAR(255) NOT NULL,
  slug VARCHAR(255) UNIQUE NOT NULL,
  logo_url TEXT,
  brand_color VARCHAR(7) DEFAULT '#ff6b35',
  secondary_color VARCHAR(7) DEFAULT '#1a1a1a',
  website_url TEXT,
  owner_id UUID REFERENCES users(id) ON DELETE CASCADE NOT NULL,
  team_size VARCHAR(50), -- 'solo', 'small', 'large', 'enterprise'
  data_handling VARCHAR(50) DEFAULT 'standard', -- 'standard', 'enhanced'
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_workspaces_owner ON workspaces(owner_id);
CREATE INDEX idx_workspaces_slug ON workspaces(slug);
```

#### `workspace_members`
```sql
CREATE TABLE workspace_members (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id UUID REFERENCES workspaces(id) ON DELETE CASCADE NOT NULL,
  user_id UUID REFERENCES users(id) ON DELETE CASCADE,
  role VARCHAR(50) DEFAULT 'member', -- 'owner', 'admin', 'member', 'viewer'
  invited_email VARCHAR(255),
  invited_at TIMESTAMP WITH TIME ZONE,
  joined_at TIMESTAMP WITH TIME ZONE,
  status VARCHAR(50) DEFAULT 'pending', -- 'pending', 'active', 'inactive'
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  UNIQUE(workspace_id, user_id),
  UNIQUE(workspace_id, invited_email) WHERE user_id IS NULL
);

CREATE INDEX idx_workspace_members_workspace ON workspace_members(workspace_id);
CREATE INDEX idx_workspace_members_user ON workspace_members(user_id);
CREATE INDEX idx_workspace_members_email ON workspace_members(invited_email);
```

#### `projects`
```sql
CREATE TABLE projects (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id UUID REFERENCES workspaces(id) ON DELETE CASCADE NOT NULL,
  name VARCHAR(255) NOT NULL,
  description TEXT,
  client_name VARCHAR(255),
  status VARCHAR(50) DEFAULT 'active', -- 'active', 'archived', 'completed', 'cancelled'
  created_by UUID REFERENCES users(id),
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_projects_workspace ON projects(workspace_id);
CREATE INDEX idx_projects_status ON projects(status);
```

#### `scopes`
```sql
CREATE TABLE scopes (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
  workspace_id UUID REFERENCES workspaces(id) ON DELETE CASCADE NOT NULL,
  title VARCHAR(255) NOT NULL,
  description TEXT,
  status VARCHAR(50) DEFAULT 'draft', -- 'draft', 'in_progress', 'in_review', 'approved', 'rejected', 'archived'
  progress INTEGER DEFAULT 0, -- 0-100
  confidence_score INTEGER DEFAULT 0, -- 0-100 (AI-generated)
  risk_level VARCHAR(50) DEFAULT 'low', -- 'low', 'medium', 'high'
  due_date TIMESTAMP WITH TIME ZONE,
  created_by UUID REFERENCES users(id),
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_scopes_workspace ON scopes(workspace_id);
CREATE INDEX idx_scopes_project ON scopes(project_id);
CREATE INDEX idx_scopes_status ON scopes(status);
CREATE INDEX idx_scopes_created_by ON scopes(created_by);
```

#### `scope_sections`
```sql
CREATE TABLE scope_sections (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  scope_id UUID REFERENCES scopes(id) ON DELETE CASCADE NOT NULL,
  title VARCHAR(255) NOT NULL,
  content TEXT,
  section_type VARCHAR(50), -- 'deliverable', 'assumption', 'exclusion', 'constraint', 'dependency', 'risk', 'overview', 'timeline', 'team', 'budget', 'success_metrics'
  order_index INTEGER DEFAULT 0,
  ai_generated BOOLEAN DEFAULT false,
  confidence_score INTEGER DEFAULT 0,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_scope_sections_scope ON scope_sections(scope_id);
CREATE INDEX idx_scope_sections_order ON scope_sections(scope_id, order_index);
```

#### `documents`
```sql
CREATE TABLE documents (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  scope_id UUID REFERENCES scopes(id) ON DELETE CASCADE,
  workspace_id UUID REFERENCES workspaces(id) ON DELETE CASCADE NOT NULL,
  filename VARCHAR(255) NOT NULL,
  file_url TEXT NOT NULL,
  file_type VARCHAR(50), -- 'pdf', 'docx', 'doc', 'txt', 'xlsx', 'pptx', 'image'
  file_size INTEGER, -- bytes
  mime_type VARCHAR(100),
  processing_status VARCHAR(50) DEFAULT 'pending', -- 'pending', 'processing', 'completed', 'failed'
  extracted_text TEXT,
  extraction_error TEXT,
  uploaded_by UUID REFERENCES users(id),
  uploaded_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  processed_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX idx_documents_scope ON documents(scope_id);
CREATE INDEX idx_documents_workspace ON documents(workspace_id);
CREATE INDEX idx_documents_status ON documents(processing_status);
```

#### `quotations`
```sql
CREATE TABLE quotations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  scope_id UUID REFERENCES scopes(id) ON DELETE CASCADE NOT NULL,
  workspace_id UUID REFERENCES workspaces(id) ON DELETE CASCADE NOT NULL,
  name VARCHAR(255),
  status VARCHAR(50) DEFAULT 'draft', -- 'draft', 'pending', 'approved', 'rejected'
  total_hours INTEGER DEFAULT 0,
  design_hours INTEGER DEFAULT 0,
  frontend_hours INTEGER DEFAULT 0,
  backend_hours INTEGER DEFAULT 0,
  qa_hours INTEGER DEFAULT 0,
  created_by UUID REFERENCES users(id),
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_quotations_scope ON quotations(scope_id);
CREATE INDEX idx_quotations_workspace ON quotations(workspace_id);
CREATE INDEX idx_quotations_status ON quotations(status);
```

#### `quotation_items`
```sql
CREATE TABLE quotation_items (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  quotation_id UUID REFERENCES quotations(id) ON DELETE CASCADE NOT NULL,
  page VARCHAR(255),
  module VARCHAR(255),
  feature TEXT,
  interactions TEXT,
  notes TEXT,
  assumptions TEXT,
  design INTEGER DEFAULT 0, -- hours
  frontend INTEGER DEFAULT 0, -- hours
  backend INTEGER DEFAULT 0, -- hours
  qa INTEGER DEFAULT 0, -- hours
  order_index INTEGER DEFAULT 0,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_quotation_items_quotation ON quotation_items(quotation_id);
CREATE INDEX idx_quotation_items_order ON quotation_items(quotation_id, order_index);
```

#### `proposals`
```sql
CREATE TABLE proposals (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  scope_id UUID REFERENCES scopes(id) ON DELETE CASCADE NOT NULL,
  workspace_id UUID REFERENCES workspaces(id) ON DELETE CASCADE NOT NULL,
  name VARCHAR(255) NOT NULL,
  client_name VARCHAR(255),
  template VARCHAR(100), -- 'executive', 'modern_split', 'minimal', 'tech_grid', 'elegant_dark'
  cover_color VARCHAR(7),
  status VARCHAR(50) DEFAULT 'draft', -- 'draft', 'sent', 'viewed', 'approved', 'rejected', 'expired'
  slide_count INTEGER DEFAULT 0,
  view_count INTEGER DEFAULT 0,
  shared_link VARCHAR(255) UNIQUE,
  sent_at TIMESTAMP WITH TIME ZONE,
  viewed_at TIMESTAMP WITH TIME ZONE,
  expires_at TIMESTAMP WITH TIME ZONE,
  created_by UUID REFERENCES users(id),
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_proposals_scope ON proposals(scope_id);
CREATE INDEX idx_proposals_workspace ON proposals(workspace_id);
CREATE INDEX idx_proposals_status ON proposals(status);
CREATE INDEX idx_proposals_shared_link ON proposals(shared_link);
```

#### `proposal_slides`
```sql
CREATE TABLE proposal_slides (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  proposal_id UUID REFERENCES proposals(id) ON DELETE CASCADE NOT NULL,
  slide_number INTEGER NOT NULL,
  title VARCHAR(255),
  content TEXT, -- JSON or markdown
  slide_type VARCHAR(50), -- 'cover', 'overview', 'scope', 'timeline', 'team', 'pricing', 'next_steps'
  order_index INTEGER DEFAULT 0,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  UNIQUE(proposal_id, slide_number)
);

CREATE INDEX idx_proposal_slides_proposal ON proposal_slides(proposal_id);
CREATE INDEX idx_proposal_slides_order ON proposal_slides(proposal_id, order_index);
```

#### `proposal_views`
```sql
CREATE TABLE proposal_views (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  proposal_id UUID REFERENCES proposals(id) ON DELETE CASCADE NOT NULL,
  viewer_email VARCHAR(255),
  viewer_name VARCHAR(255),
  ip_address VARCHAR(45),
  user_agent TEXT,
  viewed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_proposal_views_proposal ON proposal_views(proposal_id);
CREATE INDEX idx_proposal_views_email ON proposal_views(viewer_email);
```

#### `templates`
```sql
CREATE TABLE templates (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id UUID REFERENCES workspaces(id) ON DELETE CASCADE,
  name VARCHAR(255) NOT NULL,
  description TEXT,
  category VARCHAR(100), -- 'web', 'mobile', 'software', 'maintenance', 'design', 'devops', 'data', 'ai', 'integration', 'security', 'consulting'
  sections JSONB NOT NULL, -- Array of section templates
  table_columns JSONB, -- Array of table column definitions
  is_public BOOLEAN DEFAULT false,
  is_system BOOLEAN DEFAULT false, -- System templates cannot be deleted
  usage_count INTEGER DEFAULT 0,
  created_by UUID REFERENCES users(id),
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_templates_workspace ON templates(workspace_id);
CREATE INDEX idx_templates_category ON templates(category);
CREATE INDEX idx_templates_public ON templates(is_public);
```

#### `comments`
```sql
CREATE TABLE comments (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  scope_id UUID REFERENCES scopes(id) ON DELETE CASCADE NOT NULL,
  section_id UUID REFERENCES scope_sections(id) ON DELETE CASCADE,
  user_id UUID REFERENCES users(id) ON DELETE CASCADE NOT NULL,
  content TEXT NOT NULL,
  resolved BOOLEAN DEFAULT false,
  parent_id UUID REFERENCES comments(id) ON DELETE CASCADE, -- For threaded replies
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_comments_scope ON comments(scope_id);
CREATE INDEX idx_comments_section ON comments(section_id);
CREATE INDEX idx_comments_user ON comments(user_id);
CREATE INDEX idx_comments_parent ON comments(parent_id);
```

#### `favourites`
```sql
CREATE TABLE favourites (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id) ON DELETE CASCADE NOT NULL,
  scope_id UUID REFERENCES scopes(id) ON DELETE CASCADE NOT NULL,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  UNIQUE(user_id, scope_id)
);

CREATE INDEX idx_favourites_user ON favourites(user_id);
CREATE INDEX idx_favourites_scope ON favourites(scope_id);
```

#### `activity_log`
```sql
CREATE TABLE activity_log (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id UUID REFERENCES workspaces(id) ON DELETE CASCADE,
  user_id UUID REFERENCES users(id),
  action VARCHAR(100) NOT NULL, -- 'created_scope', 'uploaded_document', 'added_comment', 'approved_scope', 'created_quotation', 'created_proposal', etc.
  entity_type VARCHAR(50), -- 'scope', 'document', 'comment', 'project', 'quotation', 'proposal'
  entity_id UUID,
  metadata JSONB, -- Additional context
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_activity_workspace ON activity_log(workspace_id);
CREATE INDEX idx_activity_user ON activity_log(user_id);
CREATE INDEX idx_activity_entity ON activity_log(entity_type, entity_id);
CREATE INDEX idx_activity_created ON activity_log(created_at DESC);
```

#### `subscriptions`
```sql
CREATE TABLE subscriptions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id UUID REFERENCES workspaces(id) ON DELETE CASCADE NOT NULL,
  stripe_customer_id VARCHAR(255),
  stripe_subscription_id VARCHAR(255),
  plan VARCHAR(50) DEFAULT 'free', -- 'free', 'starter', 'pro', 'enterprise'
  billing_cycle VARCHAR(50) DEFAULT 'monthly', -- 'monthly', 'annual'
  status VARCHAR(50) DEFAULT 'active', -- 'active', 'cancelled', 'past_due', 'trialing'
  current_period_start TIMESTAMP WITH TIME ZONE,
  current_period_end TIMESTAMP WITH TIME ZONE,
  cancel_at_period_end BOOLEAN DEFAULT false,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_subscriptions_workspace ON subscriptions(workspace_id);
CREATE INDEX idx_subscriptions_stripe_customer ON subscriptions(stripe_customer_id);
CREATE INDEX idx_subscriptions_stripe_subscription ON subscriptions(stripe_subscription_id);
```

#### `usage_metrics`
```sql
CREATE TABLE usage_metrics (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id UUID REFERENCES workspaces(id) ON DELETE CASCADE NOT NULL,
  metric_type VARCHAR(50) NOT NULL, -- 'scope_created', 'ai_extraction', 'document_upload', 'export_generated'
  metric_value INTEGER DEFAULT 1,
  period_start DATE NOT NULL, -- Start of billing period
  period_end DATE NOT NULL, -- End of billing period
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  UNIQUE(workspace_id, metric_type, period_start)
);

CREATE INDEX idx_usage_metrics_workspace ON usage_metrics(workspace_id);
CREATE INDEX idx_usage_metrics_period ON usage_metrics(period_start, period_end);
```

#### `password_resets`
```sql
CREATE TABLE password_resets (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id) ON DELETE CASCADE NOT NULL,
  code VARCHAR(6) NOT NULL, -- 6-digit verification code
  expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
  used BOOLEAN DEFAULT false,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_password_resets_user ON password_resets(user_id);
CREATE INDEX idx_password_resets_code ON password_resets(code);
CREATE INDEX idx_password_resets_expires ON password_resets(expires_at);
```

---

## API Endpoints

### Authentication

```
POST   /api/auth/signup
  Body: { email, password, firstName, lastName, agreeToTerms }
  Response: { user, session }

POST   /api/auth/signin
  Body: { email, password }
  Response: { user, session }

POST   /api/auth/signout
  Response: { success: true }

POST   /api/auth/forgot-password
  Body: { email }
  Response: { success: true, message: "Verification code sent" }

POST   /api/auth/verify-reset-code
  Body: { email, code }
  Response: { success: true, token }

POST   /api/auth/reset-password
  Body: { token, newPassword }
  Response: { success: true }

POST   /api/auth/google
  Body: { idToken }
  Response: { user, session }

GET    /api/auth/me
  Response: { user, workspaces[] }
```

### Onboarding

```
POST   /api/onboarding/workspace
  Body: { name, website?, logo?, primaryColor?, secondaryColor? }
  Response: { workspace }

PUT    /api/onboarding/team
  Body: { teamSize, dataHandling, invites?: [{ email, role }] }
  Response: { workspace, invites }

PUT    /api/onboarding/goals
  Body: { goals: string[] } // ['prds', 'architecture', 'scopes', 'quotations', 'workspaces']
  Response: { user }

POST   /api/onboarding/subscribe
  Body: { plan, billingCycle } // 'starter'|'pro'|'enterprise', 'monthly'|'annual'
  Response: { checkoutUrl }

GET    /api/onboarding/status
  Response: { completed: boolean, currentStep: number }
```

### Workspaces

```
GET    /api/workspaces
  Query: ?includeMembers=true
  Response: { workspaces[] }

POST   /api/workspaces
  Body: { name, website?, logo?, primaryColor?, secondaryColor? }
  Response: { workspace }

GET    /api/workspaces/:id
  Response: { workspace, members[], subscription }

PUT    /api/workspaces/:id
  Body: { name?, logo?, primaryColor?, secondaryColor?, website? }
  Response: { workspace }

DELETE /api/workspaces/:id
  Response: { success: true }

POST   /api/workspaces/:id/invite
  Body: { email, role }
  Response: { invite }

GET    /api/workspaces/:id/members
  Response: { members[] }

PUT    /api/workspaces/:id/members/:userId
  Body: { role }
  Response: { member }

DELETE /api/workspaces/:id/members/:userId
  Response: { success: true }

POST   /api/workspaces/:id/members/accept
  Body: { token }
  Response: { member }
```

### Projects

```
GET    /api/projects
  Query: ?workspaceId=xxx&status=active
  Response: { projects[] }

POST   /api/projects
  Body: { workspaceId, name, description?, clientName? }
  Response: { project }

GET    /api/projects/:id
  Response: { project, scopes[] }

PUT    /api/projects/:id
  Body: { name?, description?, clientName?, status? }
  Response: { project }

DELETE /api/projects/:id
  Response: { success: true }
```

### Scopes

```
GET    /api/scopes
  Query: ?workspaceId=xxx&projectId=xxx&status=xxx&search=xxx
  Response: { scopes[], pagination }

POST   /api/scopes
  Body: { workspaceId, projectId?, title, description?, templateId? }
  Response: { scope }

GET    /api/scopes/:id
  Response: { scope, sections[], documents[], comments[], quotation?, proposal? }

PUT    /api/scopes/:id
  Body: { title?, description?, status?, progress?, dueDate? }
  Response: { scope }

DELETE /api/scopes/:id
  Response: { success: true }

POST   /api/scopes/:id/duplicate
  Response: { scope }

PUT    /api/scopes/:id/status
  Body: { status }
  Response: { scope }

GET    /api/scopes/:id/export
  Query: ?format=pdf|docx
  Response: File download

POST   /api/scopes/:id/favourite
  Response: { favourite }

DELETE /api/scopes/:id/favourite
  Response: { success: true }
```

### Scope Sections

```
GET    /api/scopes/:id/sections
  Response: { sections[] }

POST   /api/scopes/:id/sections
  Body: { title, content?, sectionType?, orderIndex? }
  Response: { section }

PUT    /api/scopes/:id/sections/:sectionId
  Body: { title?, content?, orderIndex? }
  Response: { section }

DELETE /api/scopes/:id/sections/:sectionId
  Response: { success: true }

PUT    /api/scopes/:id/sections/reorder
  Body: { sectionIds: string[] }
  Response: { success: true }
```

### Documents & AI Processing

```
POST   /api/documents/upload
  Body: FormData { files: File[], scopeId?, workspaceId }
  Response: { documents[] }

GET    /api/documents/:id
  Response: { document }

DELETE /api/documents/:id
  Response: { success: true }

GET    /api/documents/:id/status
  Response: { status, extractedText?, error? }

POST   /api/ai/extract
  Body: { scopeId, documentIds?: string[] }
  Response: { jobId } // Async processing

GET    /api/ai/extract/:jobId
  Response: { status, scope?, sections?, error? }

POST   /api/ai/suggest
  Body: { scopeId, sectionId?, context }
  Response: { suggestions[] }

POST   /api/ai/analyze
  Body: { scopeId }
  Response: { risks[], gaps[], recommendations[] }
```

### Comments

```
GET    /api/scopes/:id/comments
  Query: ?sectionId=xxx&resolved=false
  Response: { comments[] }

POST   /api/scopes/:id/comments
  Body: { sectionId?, content, parentId? }
  Response: { comment }

PUT    /api/comments/:id
  Body: { content }
  Response: { comment }

DELETE /api/comments/:id
  Response: { success: true }

PUT    /api/comments/:id/resolve
  Body: { resolved: boolean }
  Response: { comment }
```

### Quotations

```
GET    /api/quotations
  Query: ?workspaceId=xxx&scopeId=xxx&status=xxx
  Response: { quotations[] }

POST   /api/quotations
  Body: { scopeId, name?, items?: [{ page, module, feature, interactions, notes, assumptions, design, frontend, backend, qa }] }
  Response: { quotation }

GET    /api/quotations/:id
  Response: { quotation, items[] }

PUT    /api/quotations/:id
  Body: { name?, status?, items? }
  Response: { quotation }

DELETE /api/quotations/:id
  Response: { success: true }

POST   /api/quotations/:id/items
  Body: { page, module, feature, interactions, notes, assumptions, design, frontend, backend, qa, orderIndex? }
  Response: { item }

PUT    /api/quotations/:id/items/:itemId
  Body: { page?, module?, feature?, interactions?, notes?, assumptions?, design?, frontend?, backend?, qa?, orderIndex? }
  Response: { item }

DELETE /api/quotations/:id/items/:itemId
  Response: { success: true }

PUT    /api/quotations/:id/items/reorder
  Body: { itemIds: string[] }
  Response: { success: true }
```

### Proposals

```
GET    /api/proposals
  Query: ?workspaceId=xxx&scopeId=xxx&status=xxx
  Response: { proposals[] }

POST   /api/proposals
  Body: { scopeId, name, clientName?, template, coverColor? }
  Response: { proposal }

GET    /api/proposals/:id
  Response: { proposal, slides[] }

PUT    /api/proposals/:id
  Body: { name?, clientName?, template?, coverColor?, status? }
  Response: { proposal }

DELETE /api/proposals/:id
  Response: { success: true }

POST   /api/proposals/:id/slides
  Body: { slideNumber, title, content, slideType, orderIndex? }
  Response: { slide }

PUT    /api/proposals/:id/slides/:slideId
  Body: { title?, content?, orderIndex? }
  Response: { slide }

DELETE /api/proposals/:id/slides/:slideId
  Response: { success: true }

POST   /api/proposals/:id/send
  Body: { recipientEmails: string[], message? }
  Response: { success: true, sharedLink }

GET    /api/proposals/shared/:linkId
  Response: { proposal, slides[] } // Public endpoint

POST   /api/proposals/shared/:linkId/view
  Body: { viewerEmail?, viewerName? }
  Response: { success: true }

GET    /api/proposals/:id/analytics
  Response: { viewCount, views[], uniqueViewers, averageViewTime }
```

### Templates

```
GET    /api/templates
  Query: ?workspaceId=xxx&category=xxx&public=true
  Response: { templates[] }

POST   /api/templates
  Body: { workspaceId?, name, description, category, sections, tableColumns?, isPublic? }
  Response: { template }

GET    /api/templates/:id
  Response: { template }

PUT    /api/templates/:id
  Body: { name?, description?, category?, sections?, tableColumns?, isPublic? }
  Response: { template }

DELETE /api/templates/:id
  Response: { success: true }

POST   /api/templates/:id/apply
  Body: { scopeId }
  Response: { scope, sections[] }
```

### Favourites

```
GET    /api/favourites
  Query: ?workspaceId=xxx
  Response: { favourites[] }

POST   /api/favourites
  Body: { scopeId }
  Response: { favourite }

DELETE /api/favourites/:scopeId
  Response: { success: true }
```

### Activity

```
GET    /api/activity
  Query: ?workspaceId=xxx&limit=50&offset=0
  Response: { activities[], pagination }

GET    /api/activity/workspace/:id
  Query: ?limit=50&offset=0
  Response: { activities[], pagination }
```

### Billing (Stripe)

```
POST   /api/billing/checkout
  Body: { plan, billingCycle, workspaceId }
  Response: { checkoutUrl }

POST   /api/billing/portal
  Body: { workspaceId }
  Response: { portalUrl }

POST   /api/billing/webhook
  Headers: { 'stripe-signature' }
  Body: Stripe webhook event
  Response: { received: true }

GET    /api/billing/subscription
  Query: ?workspaceId=xxx
  Response: { subscription, usage }
```

---

## Authentication & Authorization

### Authentication Flow

1. **Email/Password Signup**
   - Hash password with bcrypt (cost factor 12)
   - Send verification email (optional for MVP)
   - Create user record
   - Create default workspace
   - Return session token

2. **Email/Password Login**
   - Verify credentials
   - Create/refresh session
   - Return user data and workspaces

3. **Google OAuth**
   - Verify Google ID token
   - Find or create user
   - Link provider account
   - Create/refresh session

4. **Password Reset**
   - Generate 6-digit code
   - Store hashed code with expiration (15 minutes)
   - Send email with code
   - Verify code and issue reset token
   - Allow password update with token

### Authorization (Row Level Security)

#### Workspace Access
- Users can access workspaces where they are members
- Owners can manage workspace settings
- Admins can manage members (except owner)
- Members can create/edit content
- Viewers can only read

#### Scope Access
- Users can CRUD scopes in workspaces they're members of
- Viewers can only read
- Scope status changes require appropriate permissions

#### Document Access
- All workspace members can view documents
- Only members+ can upload documents
- Document deletion requires admin+ permissions

### Session Management

- Use JWT tokens or session cookies
- Token expiration: 7 days (refreshable)
- Refresh token expiration: 30 days
- Include workspace context in token

---

## File Upload & Processing

### Upload Flow

1. **Client uploads file(s)**
   - Validate file type and size
   - Generate unique filename
   - Upload to storage (Supabase Storage or Vercel Blob)
   - Create document record with status 'pending'

2. **Background Processing**
   - Queue job for text extraction
   - Extract text based on file type:
     - PDF: Use `pdf-parse` or `pdfjs-dist`
     - DOCX: Use `mammoth` or `docx`
     - TXT: Direct read
     - Images: Use OCR (Tesseract.js or cloud service)
   - Update document status to 'completed' or 'failed'
   - Store extracted text in `documents.extracted_text`

3. **File Storage Structure**
```
workspaces/{workspaceId}/documents/{documentId}/{filename}
```

### Supported File Types

- **Documents:** PDF, DOCX, DOC, TXT, XLSX, PPTX
- **Images:** PNG, JPG, JPEG (for OCR)
- **Max file size:** 50MB per file
- **Max files per upload:** 10 files

---

## AI Processing Pipeline

### Scope Extraction Flow

1. **User triggers extraction**
   - Collect all extracted text from documents
   - Combine with any manual input
   - Send to AI with structured prompt

2. **AI Prompt Structure**
```
You are a scope definition expert. Analyze the following project documents and extract a structured scope.

Documents:
{extracted_text}

Extract and organize into these categories:
1. Project Overview - Summary, objectives, stakeholders
2. Deliverables - What will be delivered
3. Assumptions - What we're assuming to be true
4. Exclusions - What is explicitly NOT included
5. Constraints - Limitations and boundaries
6. Dependencies - External dependencies
7. Risks - Potential risks identified
8. Timeline & Milestones - Project phases and deadlines
9. Team & Resources - Required team members and tools
10. Budget Estimation - Cost breakdown
11. Success Metrics - KPIs and success criteria

For each item, provide:
- Title (brief, clear)
- Description (detailed, specific)
- Confidence score (0-100)
- Risk level if applicable (low/medium/high)

Respond in JSON format matching this structure:
{
  "overview": { "title": "...", "content": "...", "confidence": 85 },
  "deliverables": [
    { "title": "...", "content": "...", "confidence": 90 }
  ],
  ...
}
```

3. **Parse and Store**
   - Parse AI JSON response
   - Create scope record
   - Create scope sections from parsed data
   - Calculate overall confidence score
   - Return structured scope to frontend

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
- Risk mitigation

Provide 3-5 specific, actionable suggestions.
```

### AI Analysis Flow

For risk and gap analysis:

```
Analyze this scope document for:
1. Potential risks (technical, timeline, budget, scope creep)
2. Missing information or gaps
3. Ambiguities that need clarification
4. Recommendations for improvement

Provide structured analysis with:
- Risk level (low/medium/high)
- Impact assessment
- Mitigation strategies
```

### Rate Limiting

- Free plan: 10 AI extractions/month
- Pro plan: 100 AI extractions/month
- Enterprise: Unlimited
- Track usage in `usage_metrics` table

---

## Quotations System

### Quotation Generation

1. **Create from Scope**
   - User selects scope
   - System creates quotation with scope reference
   - User can add quotation items manually or use AI estimation

2. **Quotation Items**
   - Each item represents a feature/module
   - Fields: page, module, feature, interactions, notes, assumptions
   - Hour estimates: design, frontend, backend, QA
   - Auto-calculate totals

3. **AI Estimation (Optional)**
   - Analyze scope sections
   - Estimate hours based on complexity
   - Suggest breakdown by role

### Quotation Status Workflow

```
draft → pending → approved/rejected
```

---

## Proposals System

### Proposal Generation

1. **Create from Scope**
   - User selects scope and template
   - System generates initial slides from scope data
   - User can customize slides

2. **Templates**
   - Executive: Professional, text-heavy
   - Modern Split: Visual, image-focused
   - Minimal: Clean, simple
   - Tech Grid: Technical, detailed
   - Elegant Dark: Dark theme, premium

3. **Slide Types**
   - Cover: Title, client name, date
   - Overview: Project summary
   - Scope: Key deliverables
   - Timeline: Project phases
   - Team: Team members
   - Pricing: Cost breakdown
   - Next Steps: Call to action

### Sharing & Analytics

1. **Generate Share Link**
   - Create unique, unguessable link
   - Set expiration (optional)
   - Track views

2. **View Tracking**
   - Record each view with timestamp
   - Track viewer email (if provided)
   - Track IP and user agent
   - Calculate unique viewers

3. **Status Updates**
   - Auto-update to 'viewed' when first viewed
   - Auto-update to 'expired' when expiration reached

---

## Templates System

### Template Structure

```typescript
interface Template {
  id: string;
  name: string;
  description: string;
  category: string;
  sections: TemplateSection[];
  tableColumns: TableColumn[];
  isPublic: boolean;
  isSystem: boolean;
}

interface TemplateSection {
  id: string;
  title: string;
  defaultContent: string;
  required: boolean;
  order: number;
}

interface TableColumn {
  id: string;
  name: string;
  width: string;
  required: boolean;
}
```

### Template Application

When applying a template to a scope:

1. Create scope with template name as title
2. Create scope sections from template sections
3. Populate default content
4. Create table structure if template has table columns

### System Templates

Pre-built templates included:
- Design & Development
- Web Development
- Mobile Development
- Software Development
- Maintenance & Support
- Design Services
- DevOps & Cloud
- Data & Analytics
- AI & Machine Learning
- Integration & Migration
- Security & Compliance
- Consulting & Strategy

---

## Feature Flags & Plan Limits

### Plan Comparison

| Feature | Free | Starter | Pro | Enterprise |
|---------|------|---------|-----|-------------|
| Scopes per month | 5 | 10 | Unlimited | Unlimited |
| Team members | 1 | 1 | 10 | Unlimited |
| AI extractions/month | 10 | 20 | 100 | Unlimited |
| Document storage | 100MB | 1GB | 10GB | Unlimited |
| Templates | Public only | + Custom | + Private library | + Custom branding |
| Export formats | PDF | + DOCX | + Custom branding | + White-label |
| Quotations | ❌ | ✅ | ✅ | ✅ |
| Proposals | ❌ | ✅ | ✅ | ✅ |
| Priority support | ❌ | Email | 24h | 1h |
| SSO/SAML | ❌ | ❌ | ❌ | ✅ |

### Usage Tracking

Track usage in `usage_metrics` table:
- `scope_created`: Count of scopes created in period
- `ai_extraction`: Count of AI extractions in period
- `document_upload`: Total file size uploaded in period
- `export_generated`: Count of exports in period

### Limit Enforcement

Before allowing action:
1. Check subscription plan
2. Query usage metrics for current period
3. Compare against plan limits
4. Return error if limit exceeded

---

## Real-time Features

### Recommended Implementation

- **Supabase Realtime:** For PostgreSQL changes
- **Pusher:** For custom events
- **WebSockets:** For direct connections

### Real-time Events

1. **Scope Updates**
   - Section content changes
   - Status changes
   - Comment additions

2. **Comments**
   - New comments
   - Comment resolutions
   - Replies

3. **Collaboration**
   - User presence (who's viewing)
   - Cursor positions (optional)
   - Live editing indicators

4. **Notifications**
   - Scope approval requests
   - Comment mentions
   - Team invitations

---

## Environment Variables

```env
# Database
DATABASE_URL=postgresql://...
DIRECT_URL=postgresql://... # For migrations

# Supabase
NEXT_PUBLIC_SUPABASE_URL=https://xxx.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=xxx
SUPABASE_SERVICE_ROLE_KEY=xxx

# Authentication
NEXTAUTH_SECRET=xxx
NEXTAUTH_URL=http://localhost:3000

# Google OAuth
GOOGLE_CLIENT_ID=xxx
GOOGLE_CLIENT_SECRET=xxx

# AI
OPENAI_API_KEY=sk-xxx
# or
ANTHROPIC_API_KEY=sk-ant-xxx

# Stripe
STRIPE_SECRET_KEY=sk_xxx
NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=pk_xxx
STRIPE_WEBHOOK_SECRET=whsec_xxx

# File Storage
BLOB_READ_WRITE_TOKEN=xxx
# or
SUPABASE_STORAGE_BUCKET=documents

# Email (for password reset, invitations)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=xxx
SMTP_PASSWORD=xxx
SMTP_FROM=noreply@orbit.app

# App
NEXT_PUBLIC_APP_URL=http://localhost:3000
NODE_ENV=development

# Rate Limiting (optional)
REDIS_URL=redis://localhost:6379
```

---

## Implementation Priority

### Phase 1: Foundation (Week 1-2)
1. ✅ Database setup with all tables
2. ✅ Authentication (email + Google OAuth)
3. ✅ User and workspace CRUD
4. ✅ Basic RLS policies
5. ✅ File upload to storage

### Phase 2: Core Product (Week 3-4)
1. ✅ Project and scope CRUD
2. ✅ Document upload and text extraction
3. ✅ AI extraction pipeline (basic)
4. ✅ Section management
5. ✅ Comments system

### Phase 3: Collaboration (Week 5-6)
1. ✅ Team invites and member management
2. ✅ Activity feed
3. ✅ Favourites
4. ✅ Real-time updates (optional)

### Phase 4: Advanced Features (Week 7-8)
1. ✅ Quotations system
2. ✅ Proposals system
3. ✅ Templates system
4. ✅ Export functionality

### Phase 5: Monetization (Week 9-10)
1. ✅ Stripe integration
2. ✅ Plan limits enforcement
3. ✅ Billing portal
4. ✅ Usage tracking

### Phase 6: Polish (Week 11-12)
1. ✅ Advanced AI features (suggestions, analysis)
2. ✅ Search functionality
3. ✅ Analytics dashboard
4. ✅ Performance optimization

---

## Additional Notes

### Error Handling

- Return consistent error format:
```json
{
  "error": {
    "code": "SCOPE_NOT_FOUND",
    "message": "Scope not found",
    "details": {}
  }
}
```

### Validation

- Use Zod for request validation
- Validate file types and sizes
- Sanitize user input
- Validate email formats

### Logging

- Log all API requests
- Log errors with context
- Log AI processing jobs
- Use structured logging (JSON)

### Security

- Rate limit API endpoints
- Sanitize file uploads
- Validate file types
- Use HTTPS everywhere
- Implement CORS properly
- Store sensitive data encrypted

### Performance

- Cache frequently accessed data
- Use database indexes
- Optimize queries
- Implement pagination
- Use CDN for static assets

---

## Testing Checklist

### Authentication
- [ ] Sign up with email/password
- [ ] Email verification flow
- [ ] Sign in with email/password
- [ ] Sign in with Google
- [ ] Password reset flow (6-digit code)
- [ ] Session persistence
- [ ] Sign out

### Onboarding
- [ ] Step 1: Workspace creation
- [ ] Step 1: Logo upload
- [ ] Step 1: Brand colors
- [ ] Step 2: Team size selection
- [ ] Step 2: Team invites
- [ ] Step 3: Goal selection
- [ ] Step 4: Plan selection
- [ ] Step 4: Stripe checkout
- [ ] Skip functionality

### Core Features
- [ ] Document upload (multiple formats)
- [ ] Text extraction (PDF, DOCX, images)
- [ ] AI scope extraction
- [ ] Scope creation and editing
- [ ] Section management
- [ ] Comments and replies
- [ ] Favourites
- [ ] Templates
- [ ] Export (PDF, DOCX)

### Quotations
- [ ] Create quotation from scope
- [ ] Add/edit quotation items
- [ ] Calculate totals
- [ ] Status workflow

### Proposals
- [ ] Create proposal from scope
- [ ] Generate slides
- [ ] Customize template
- [ ] Share link generation
- [ ] View tracking
- [ ] Analytics

### Billing
- [ ] Stripe checkout
- [ ] Subscription management
- [ ] Plan upgrades/downgrades
- [ ] Webhook handling
- [ ] Usage tracking
- [ ] Limit enforcement

---

## Contact & Support

For questions about this specification:
- Refer to the frontend codebase in `/Orbit/app/`
- Check the product spec in `/Orbit/docs/ORBIT-PRODUCT-SPEC.md`
- Contact the product team

---

**Document Version:** 1.0  
**Last Updated:** January 2025  
**Status:** Ready for Implementation

