# API Endpoints Documentation

> **Last Updated:** January 2025  
> **Status:** Implementation in Progress  
> **Note:** This document should be updated whenever new API endpoints are created or existing ones are modified.

This document lists all API endpoints currently implemented in the Orbit backend, organized by feature area.

---

## Base URL

All endpoints are prefixed with `/api`:
- Development: `http://localhost:8001/api`
- Production: `https://api.orbit.example.com/api`

**Note:** The backend API container runs on port 8000 internally, but is exposed on port 8001 on the host machine via Docker port mapping (`BACKEND_PORT` environment variable).

---

## Authentication Endpoints (`/api/auth`)

### User Registration & Login

| Method | Endpoint | Description | Status |
|--------|----------|-------------|--------|
| `POST` | `/api/auth/signup` | Register a new user account with email and password | ✅ Implemented |
| `POST` | `/api/auth/signin` | Login with email and password | ✅ Implemented |
| `POST` | `/api/auth/refresh` | Refresh access token using refresh token | ✅ Implemented |
| `GET` | `/api/auth/me` | Get current authenticated user information | ✅ Implemented |

**Features:**
- Email/password authentication
- JWT-based access and refresh tokens
- User profile retrieval

**Get Current User (`GET /api/auth/me`):**
Returns user information including:
- `id` - User UUID
- `email` - User email address
- `full_name` - User's full name (registered during signup/onboarding)
- `is_active` - Account active status
- `is_verified` - Email verification status

---

### Google OAuth

| Method | Endpoint | Description | Status |
|--------|----------|-------------|--------|
| `POST` | `/api/auth/google/init` | Initialize Google OAuth flow, returns authorization URL | ✅ Implemented |
| `POST` | `/api/auth/google/complete` | Complete Google OAuth flow with authorization code | ✅ Implemented |

**Features:**
- Google OAuth 2.0 integration
- Automatic user creation for new Google accounts
- OAuth account linking for existing users
- State token validation for security

---

### Password Reset

| Method | Endpoint | Description | Status |
|--------|----------|-------------|--------|
| `POST` | `/api/auth/password/request` | Request password reset code (sent via email) | ✅ Implemented |
| `POST` | `/api/auth/password/verify` | Verify 6-digit reset code, returns reset token | ✅ Implemented |
| `POST` | `/api/auth/password/reset` | Complete password reset with new password | ✅ Implemented |

**Features:**
- 6-digit verification code generation
- Secure code hashing (SHA-256)
- Email dispatch with rate limiting
- JWT-based reset token for final step
- 15-minute code expiration

---

## Onboarding Endpoints (`/api/onboarding`)

### Onboarding Flow

| Method | Endpoint | Description | Status |
|--------|----------|-------------|--------|
| `GET` | `/api/onboarding/status` | Get current onboarding status and progress | ✅ Implemented |
| `POST` | `/api/onboarding/step1` | Complete workspace setup step | ✅ Implemented |
| `POST` | `/api/onboarding/step2` | Complete team invitation step | ✅ Implemented |
| `POST` | `/api/onboarding/step3` | Complete goals selection step | ✅ Implemented |
| `POST` | `/api/onboarding/step4` | Complete plan selection step | ✅ Implemented |
| `POST` | `/api/onboarding/complete` | Finalize onboarding process | ✅ Implemented |
| `POST` | `/api/onboarding/skip` | Skip onboarding and create default workspace | ✅ Implemented |

**Features:**
- Multi-step onboarding flow (workspace → team → goals → plan)
- State persistence in user's `onboarding_state` JSONB column
- Workspace creation during step 1
- Team member invitations with email dispatch
- Goals tracking (deliver faster, grow, scale, etc.)
- Plan selection (starter, pro, enterprise)
- Skip option that creates default workspace

**Step Details:**
- **Step 1 (Workspace):** Create workspace with name, colors, team size, data handling preferences
- **Step 2 (Team):** Invite team members via email with custom message
- **Step 3 (Goals):** Select goals and optional custom goal
- **Step 4 (Plan):** Select subscription plan and billing cycle

---

## Workspace Endpoints (`/api/workspaces`)

### Workspace Management

| Method | Endpoint | Description | Status |
|--------|----------|-------------|--------|
| `GET` | `/api/workspaces` | List all workspaces the user has access to | ✅ Implemented |
| `POST` | `/api/workspaces` | Create a new workspace | ✅ Implemented |
| `GET` | `/api/workspaces/{workspace_id}` | Get workspace details | ✅ Implemented |
| `PUT` | `/api/workspaces/{workspace_id}` | Update workspace settings | ✅ Implemented |

**Features:**
- Multi-workspace support
- Role-based access control (owner, admin, member, viewer)
- Workspace branding (logo, primary/secondary colors)
- Team size and data handling preferences
- Member roster retrieval (optional via `?includeMembers=true`)
- Workspace slug generation

**Query Parameters:**
- `includeMembers` (boolean): Include member roster in response

---

## Project Management Endpoints (`/api/projects`)

### Project CRUD Operations

| Method | Endpoint | Description | Status |
|--------|----------|-------------|--------|
| `GET` | `/api/projects` | List projects with filters | ✅ Implemented |
| `POST` | `/api/projects` | Create a new project | ✅ Implemented |
| `GET` | `/api/projects/{project_id}` | Get project details with scopes | ✅ Implemented |
| `PUT` | `/api/projects/{project_id}` | Update a project | ✅ Implemented |
| `DELETE` | `/api/projects/{project_id}` | Delete a project | ✅ Implemented |

**Features:**
- Workspace-based access control
- Filtering by workspace and status
- Project status workflow (active, archived, completed, on_hold)
- Scope count included in project details
- Client name tracking

**Query Parameters (List Projects):**
- `workspaceId` (UUID): Filter by workspace
- `status` (string): Filter by status (active, archived, completed, on_hold)

---

## Scope Management Endpoints (`/api/scopes`)

### Scope CRUD Operations

| Method | Endpoint | Description | Status |
|--------|----------|-------------|--------|
| `GET` | `/api/scopes` | List scopes with filters and pagination | ✅ Implemented |
| `POST` | `/api/scopes` | Create a new scope | ✅ Implemented |
| `GET` | `/api/scopes/{scope_id}` | Get scope details with sections | ✅ Implemented |
| `PUT` | `/api/scopes/{scope_id}` | Update a scope | ✅ Implemented |
| `DELETE` | `/api/scopes/{scope_id}` | Delete a scope | ✅ Implemented |
| `POST` | `/api/scopes/{scope_id}/duplicate` | Duplicate a scope with all sections | ✅ Implemented |
| `PUT` | `/api/scopes/{scope_id}/status` | Update scope status | ✅ Implemented |
| `POST` | `/api/scopes/{scope_id}/favourite` | Add scope to favourites | ✅ Implemented |
| `DELETE` | `/api/scopes/{scope_id}/favourite` | Remove scope from favourites | ✅ Implemented |

**Features:**
- Workspace-based access control
- Filtering by workspace, project, status, and search
- Pagination support
- Scope duplication with all sections
- Favourites/bookmarking
- Status workflow (draft, in_review, approved, rejected)

**Query Parameters (List Scopes):**
- `workspaceId` (UUID): Filter by workspace
- `projectId` (UUID): Filter by project
- `status` (string): Filter by status (draft, in_review, approved, rejected)
- `search` (string): Search in title and description
- `page` (int): Page number (default: 1)
- `pageSize` (int): Items per page (default: 20, max: 100)

---

### Scope Sections Endpoints

| Method | Endpoint | Description | Status |
|--------|----------|-------------|--------|
| `GET` | `/api/scopes/{scope_id}/sections` | List all sections for a scope | ✅ Implemented |
| `POST` | `/api/scopes/{scope_id}/sections` | Create a new section | ✅ Implemented |
| `PUT` | `/api/scopes/{scope_id}/sections/{section_id}` | Update a section | ✅ Implemented |
| `DELETE` | `/api/scopes/{scope_id}/sections/{section_id}` | Delete a section | ✅ Implemented |
| `PUT` | `/api/scopes/{scope_id}/sections/reorder` | Reorder sections | ✅ Implemented |

**Features:**
- Section ordering with `order_index`
- Section types (deliverable, assumption, exclusion, etc.)
- AI-generated sections support
- Automatic ordering when not specified

---

## Health Check Endpoints (`/api/health`)

| Method | Endpoint | Description | Status |
|--------|----------|-------------|--------|
| `GET` | `/api/health/live` | Liveness probe for container orchestration | ✅ Implemented |
| `GET` | `/api/health/ready` | Readiness probe for container orchestration | ✅ Implemented |

**Features:**
- Kubernetes/Docker health checks
- Simple status responses

---

## Root Endpoint

| Method | Endpoint | Description | Status |
|--------|----------|-------------|--------|
| `GET` | `/` | Root endpoint with app status | ✅ Implemented |

---

## Implementation Status Summary

### ✅ Fully Implemented Features

1. **User Authentication & Onboarding**
   - Email/password signup and login
   - Google OAuth 2.0
   - Password reset flow with email dispatch
   - Multi-step onboarding (4 steps)
   - Onboarding skip option

2. **Workspace Management**
   - Workspace CRUD operations
   - Member management
   - Role-based access control

3. **Email Dispatcher**
   - Password reset emails
   - Team invitation emails
   - Rate limiting (configurable per hour)

### ✅ Recently Fixed

1. **Onboarding State Persistence** ✅
   - Issue: Team and goals data not appearing in status responses
   - Fix: Added `flag_modified()` to explicitly mark JSON column as changed in SQLAlchemy
   - Status: Fixed and tested

### ✅ Recently Implemented

1. **Project Management** ✅
   - Project CRUD operations (create, read, update, delete)
   - Project listing with filters
   - Project status management
   - Workspace-based access control
   - Scope count tracking

2. **Scope Management** ✅
   - Scope CRUD operations (create, read, update, delete)
   - Scope listing with filters and pagination
   - Scope duplication
   - Scope status management
   - Favourites/bookmarking
   - Section management (CRUD, reordering)
   - Workspace-based access control

3. **Quotations Management** ✅
   - Quotation CRUD operations (create, read, update, delete)
   - Quotation listing with filters (workspace, scope, status)
   - Automatic hour calculation (design, frontend, backend, QA)
   - Item management (CRUD, reordering)
   - Workspace-based access control

4. **Proposals Management** ✅
   - Proposal CRUD operations (create, read, update, delete)
   - Proposal listing with filters (workspace, scope, status)
   - Slide management (CRUD, reordering)
   - Shared link generation for client viewing
   - Public endpoints for shared proposals (no auth required)
   - View tracking and analytics
   - Multiple templates support (standard, minimal, detailed)
   - Link expiration (30 days default)
   - Workspace-based access control

5. **Activity Feed** ✅
   - Activity listing with pagination
   - Workspace-specific activity feeds
   - User information included in activities
   - Access control based on workspace membership

6. **Dashboard Statistics** ✅
   - Aggregate statistics for all entity types
   - Status breakdowns (scopes, projects, quotations, proposals)
   - Total hours and views tracking
   - Recent activity count (last 7 days)
   - Workspace-level or cross-workspace statistics

### 📋 Planned Features (Not Yet Implemented)

1. **Scope Management (Advanced)**
   - Document upload and processing
   - AI-powered scope extraction
   - Scope export (PDF/DOCX)

2. **Comments & Collaboration**
   - Comment threads on scopes
   - Real-time updates

3. **Proposals (Advanced)**
   - Email sending for proposal sharing (currently generates link only)

5. **Templates System**
   - Pre-built templates
   - Custom template creation

6. **Activity Feed**
   - Activity tracking
   - Workspace activity

7. **Favourites**
   - Bookmark scopes

8. **Billing Integration**
   - Stripe checkout
   - Subscription management

---

## Authentication

Most endpoints require authentication via JWT Bearer token:

```
Authorization: Bearer <access_token>
```

**Token Types:**
- **Access Token:** Short-lived (15 minutes default), used for API requests
- **Refresh Token:** Long-lived (7 days default), used to obtain new access tokens

**Public Endpoints (No Auth Required):**
- `POST /api/auth/signup`
- `POST /api/auth/signin`
- `POST /api/auth/google/init`
- `POST /api/auth/google/complete`
- `POST /api/auth/password/request`
- `POST /api/auth/password/verify`
- `GET /api/health/*`
- `GET /api/proposals/shared/{shared_link}` - Get proposal by shared link
- `POST /api/proposals/shared/{shared_link}/view` - Record proposal view
- `GET /`

---

## Error Responses

All endpoints follow standard HTTP status codes:

- `200 OK` - Success
- `201 Created` - Resource created
- `202 Accepted` - Request accepted (async processing)
- `204 No Content` - Success with no response body
- `400 Bad Request` - Invalid request data
- `401 Unauthorized` - Missing or invalid authentication
- `403 Forbidden` - Insufficient permissions
- `404 Not Found` - Resource not found
- `409 Conflict` - Resource conflict (e.g., onboarding already completed)
- `429 Too Many Requests` - Rate limit exceeded
- `500 Internal Server Error` - Server error
- `502 Bad Gateway` - External service error (e.g., Google OAuth)
- `503 Service Unavailable` - Service not configured

---

## Rate Limiting

Currently implemented for:
- **Password Reset Emails:** Configurable per hour (default: 5 per hour per email)
- **Team Invitations:** Uses same email dispatcher rate limiter

---

## Quotations API

### List Quotations
**GET** `/api/quotations`

Query Parameters:
- `workspaceId` (UUID, optional) - Filter by workspace
- `scopeId` (UUID, optional) - Filter by scope
- `status` (string, optional) - Filter by status: `draft`, `pending`, `approved`, `rejected`

**Response:** `200 OK`
```json
[
  {
    "id": "uuid",
    "scopeId": "uuid",
    "workspaceId": "uuid",
    "name": "string",
    "status": "draft",
    "totalHours": 0,
    "designHours": 0,
    "frontendHours": 0,
    "backendHours": 0,
    "qaHours": 0,
    "createdBy": "uuid",
    "createdAt": "datetime",
    "updatedAt": "datetime"
  }
]
```

### Create Quotation
**POST** `/api/quotations`

**Request Body:**
```json
{
  "scopeId": "uuid",
  "name": "string (optional)",
  "status": "draft (optional)",
  "items": [
    {
      "page": "string (optional)",
      "module": "string (optional)",
      "feature": "string (optional)",
      "interactions": "string (optional)",
      "notes": "string (optional)",
      "assumptions": "string (optional)",
      "design": 0,
      "frontend": 0,
      "backend": 0,
      "qa": 0,
      "orderIndex": 0
    }
  ]
}
```

**Response:** `201 Created` - Returns full quotation with items

### Get Quotation
**GET** `/api/quotations/{quotation_id}`

**Response:** `200 OK` - Returns quotation with all items

### Update Quotation
**PUT** `/api/quotations/{quotation_id}`

**Request Body:**
```json
{
  "name": "string (optional)",
  "status": "draft|pending|approved|rejected (optional)"
}
```

**Response:** `200 OK` - Returns updated quotation

### Delete Quotation
**DELETE** `/api/quotations/{quotation_id}`

**Response:** `204 No Content`

### Quotation Items

#### List Items
**GET** `/api/quotations/{quotation_id}/items`

**Response:** `200 OK` - Returns list of items

#### Create Item
**POST** `/api/quotations/{quotation_id}/items`

**Request Body:** Same as item in create quotation

**Response:** `201 Created` - Returns created item

#### Update Item
**PUT** `/api/quotations/{quotation_id}/items/{item_id}`

**Request Body:** Partial item update

**Response:** `200 OK` - Returns updated item

#### Delete Item
**DELETE** `/api/quotations/{quotation_id}/items/{item_id}`

**Response:** `204 No Content`

#### Reorder Items
**PUT** `/api/quotations/{quotation_id}/items/reorder`

**Request Body:**
```json
{
  "itemIds": ["uuid", "uuid", ...]
}
```

**Response:** `204 No Content`

**Features:**
- Automatic calculation of total hours (design + frontend + backend + qa)
- Items can be reordered
- Access control based on workspace membership

---

## Proposals API

### List Proposals
**GET** `/api/proposals`

Query Parameters:
- `workspaceId` (UUID, optional) - Filter by workspace
- `scopeId` (UUID, optional) - Filter by scope
- `status` (string, optional) - Filter by status: `draft`, `sent`, `viewed`, `accepted`, `rejected`

**Response:** `200 OK`
```json
[
  {
    "id": "uuid",
    "scopeId": "uuid",
    "workspaceId": "uuid",
    "name": "string",
    "clientName": "string (optional)",
    "template": "standard|minimal|detailed (optional)",
    "coverColor": "#RRGGBB (optional)",
    "status": "draft",
    "slideCount": 0,
    "viewCount": 0,
    "sharedLink": "string (optional)",
    "sentAt": "datetime (optional)",
    "viewedAt": "datetime (optional)",
    "expiresAt": "datetime (optional)",
    "createdBy": "uuid",
    "createdAt": "datetime",
    "updatedAt": "datetime"
  }
]
```

### Create Proposal
**POST** `/api/proposals`

**Request Body:**
```json
{
  "scopeId": "uuid",
  "name": "string",
  "clientName": "string (optional)",
  "template": "standard|minimal|detailed (optional)",
  "coverColor": "#RRGGBB (optional)",
  "status": "draft (optional)"
}
```

**Response:** `201 Created` - Returns proposal with empty slides array

### Get Proposal
**GET** `/api/proposals/{proposal_id}`

**Response:** `200 OK` - Returns proposal with all slides

### Update Proposal
**PUT** `/api/proposals/{proposal_id}`

**Request Body:**
```json
{
  "name": "string (optional)",
  "clientName": "string (optional)",
  "template": "standard|minimal|detailed (optional)",
  "coverColor": "#RRGGBB (optional)",
  "status": "draft|sent|viewed|accepted|rejected (optional)"
}
```

**Response:** `200 OK` - Returns updated proposal

### Delete Proposal
**DELETE** `/api/proposals/{proposal_id}`

**Response:** `204 No Content`

### Send Proposal
**POST** `/api/proposals/{proposal_id}/send`

**Request Body:**
```json
{
  "recipientEmails": ["email1@example.com", "email2@example.com"],
  "message": "string (optional)"
}
```

**Response:** `200 OK`
```json
{
  "success": true,
  "sharedLink": "token"
}
```

**Features:**
- Generates unique shared link if not exists
- Sets expiration to 30 days from send date
- Updates status to "sent"
- TODO: Sends emails to recipients (currently just generates link)

### Get Proposal by Shared Link (Public)
**GET** `/api/proposals/shared/{shared_link}`

**Note:** This is a public endpoint, no authentication required.

**Response:** `200 OK` - Returns proposal with slides

### Record Proposal View (Public)
**POST** `/api/proposals/shared/{shared_link}/view`

**Note:** This is a public endpoint, no authentication required.

**Request Body:**
```json
{
  "viewerEmail": "string (optional)",
  "viewerName": "string (optional)"
}
```

**Response:** `204 No Content`

**Features:**
- Records view with IP address and user agent
- Updates proposal view count and viewed_at timestamp
- Sets proposal status to "viewed" if first view
- Checks for expired links

### Get Proposal Analytics
**GET** `/api/proposals/{proposal_id}/analytics`

**Response:** `200 OK`
```json
{
  "viewCount": 0,
  "uniqueViewers": 0,
  "views": [
    {
      "id": "uuid",
      "viewerEmail": "string (optional)",
      "viewerName": "string (optional)",
      "viewedAt": "datetime"
    }
  ]
}
```

### Proposal Slides

#### List Slides
**GET** `/api/proposals/{proposal_id}/slides`

**Response:** `200 OK` - Returns list of slides ordered by order_index and slide_number

#### Create Slide
**POST** `/api/proposals/{proposal_id}/slides`

**Request Body:**
```json
{
  "slideNumber": 1,
  "title": "string (optional)",
  "content": "string (optional)",
  "slideType": "string (optional)",
  "orderIndex": 0
}
```

**Response:** `201 Created` - Returns created slide

**Features:**
- Validates unique slide_number per proposal
- Automatically updates proposal slide_count

#### Update Slide
**PUT** `/api/proposals/{proposal_id}/slides/{slide_id}`

**Request Body:**
```json
{
  "title": "string (optional)",
  "content": "string (optional)",
  "orderIndex": 0
}
```

**Response:** `200 OK` - Returns updated slide

#### Delete Slide
**DELETE** `/api/proposals/{proposal_id}/slides/{slide_id}`

**Response:** `204 No Content`

**Features:**
- Automatically updates proposal slide_count

#### Reorder Slides
**PUT** `/api/proposals/{proposal_id}/slides/reorder`

**Request Body:**
```json
{
  "slideIds": ["uuid", "uuid", ...]
}
```

**Response:** `204 No Content`

**Features:**
- Access control based on workspace membership
- Public endpoints for shared proposals (no auth required)
- Automatic view tracking
- Link expiration (30 days default)

---

## Activity Feed API

### List Activities
**GET** `/api/activity`

Query Parameters:
- `workspaceId` (UUID, optional) - Filter by workspace
- `page` (int, default: 1) - Page number
- `pageSize` (int, default: 50, max: 100) - Items per page

**Response:** `200 OK`
```json
{
  "activities": [
    {
      "id": "uuid",
      "workspaceId": "uuid",
      "userId": "uuid",
      "action": "created_scope",
      "entityType": "scope",
      "entityId": "uuid",
      "payload": {},
      "createdAt": "datetime",
      "userName": "string",
      "userEmail": "string"
    }
  ],
  "total": 0,
  "page": 1,
  "pageSize": 50,
  "hasMore": false
}
```

### List Workspace Activities
**GET** `/api/activity/workspace/{workspace_id}`

Query Parameters:
- `page` (int, default: 1) - Page number
- `pageSize` (int, default: 50, max: 100) - Items per page

**Response:** `200 OK` - Same format as list activities

**Features:**
- Paginated activity feed
- Workspace-based filtering
- Includes user information (name, email)
- Ordered by most recent first
- Access control based on workspace membership

---

## Dashboard API

### Get Dashboard Statistics
**GET** `/api/dashboard/stats`

Query Parameters:
- `workspaceId` (UUID, optional) - Filter by specific workspace (default: all accessible workspaces)
  - When provided, includes workspace name and member information

**Response:** `200 OK`
```json
{
  "workspaceId": "uuid (optional)",
  "workspace": {
    "id": "uuid",
    "name": "string",
    "slug": "string",
    "logoUrl": "string (optional)",
    "brandColor": "#RRGGBB",
    "secondaryColor": "#RRGGBB"
  },
  "members": [
    {
      "id": "uuid",
      "email": "string",
      "fullName": "string (optional)",
      "role": "owner|admin|member|viewer",
      "status": "active|pending|inactive"
    }
  ],
  "scopes": {
    "total": 0,
    "byStatus": {
      "draft": 0,
      "in_review": 0,
      "approved": 0,
      "rejected": 0
    },
    "draft": 0,
    "inReview": 0,
    "approved": 0,
    "rejected": 0
  },
  "projects": {
    "total": 0,
    "byStatus": {
      "active": 0,
      "archived": 0,
      "completed": 0
    },
    "active": 0,
    "archived": 0,
    "completed": 0
  },
  "quotations": {
    "total": 0,
    "byStatus": {
      "draft": 0,
      "pending": 0,
      "approved": 0,
      "rejected": 0
    },
    "totalHours": 0,
    "draft": 0,
    "pending": 0,
    "approved": 0,
    "rejected": 0
  },
  "proposals": {
    "total": 0,
    "byStatus": {
      "draft": 0,
      "sent": 0,
      "viewed": 0,
      "accepted": 0,
      "rejected": 0
    },
    "totalViews": 0,
    "draft": 0,
    "sent": 0,
    "viewed": 0,
    "accepted": 0,
    "rejected": 0
  },
  "recentActivityCount": 0
}
```

**Features:**
- Aggregate statistics for scopes, projects, quotations, and proposals
- Status breakdowns for each entity type
- Total hours across all quotations
- Total views across all proposals
- Recent activity count (last 7 days)
- Workspace-level or cross-workspace statistics
- **Workspace information included when `workspaceId` is provided:**
  - Workspace name, slug, logo, brand colors
  - List of active members with names, emails, roles
- Access control based on workspace membership

---

## Next Steps

1. **Comments System** - Add collaboration features
2. **Documents API** - Implement document upload and processing
3. **AI-Powered Scope Extraction** - Automatically extract scope from documents
4. **Scope Export** - PDF/DOCX export functionality
5. **Email Integration** - Complete email sending for proposal sharing
6. **Activity Logging Integration** - Automatically log activities when entities are created/updated

---

## Testing

All endpoints have corresponding test suites:
- `backend/tests/test_auth.py` - Authentication tests
- `backend/tests/test_onboarding.py` - Onboarding tests
- `backend/tests/test_workspaces.py` - Workspace tests

Run tests with:
```bash
pytest backend/tests/
```

