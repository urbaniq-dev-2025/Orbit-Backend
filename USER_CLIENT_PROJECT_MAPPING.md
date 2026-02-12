# User-Client-Project Mapping Implementation

## Overview
This implementation maps users to clients and projects, ensuring scopes are properly organized and saved under the correct client/project for each user.

## Architecture

### Current Relationships
```
User → WorkspaceMember → Workspace
Workspace → Client
Workspace → Project
Client → Project (one-to-many)
Project → Scope (one-to-many)
Scope → Project (many-to-one, optional)
```

### Access Control
- Users can only access clients/projects from workspaces they are members of
- Scopes are filtered by workspace membership
- Project access is validated when creating scopes

## New Features

### 1. Enhanced Scope Filtering
**File:** `backend/app/services/scopes.py`

- Added `client_id` parameter to `list_scopes()` function
- Scopes can now be filtered by:
  - `workspace_id` - Filter by workspace
  - `project_id` - Filter by specific project
  - `client_id` - Filter by client (via projects)
  - `status` - Filter by scope status
  - `search` - Search by title/description
  - `is_favourite` - Filter by favourite status

**API Endpoint:** `GET /api/scopes?clientId={client_id}`

### 2. User Resource Service
**File:** `backend/app/services/user_client_project.py`

New service functions:
- `get_user_accessible_clients()` - Get all clients user can access
- `get_user_accessible_projects()` - Get all projects user can access
- `get_client_projects_for_user()` - Get projects for a specific client
- `get_user_clients_with_project_counts()` - Get clients with statistics

### 3. User Resources API
**File:** `backend/app/api/routes/user_resources.py`

New endpoints:
- `GET /api/user/clients` - Get user's accessible clients
- `GET /api/user/projects` - Get user's accessible projects (optionally filtered by client)
- `GET /api/user/clients/{client_id}/projects` - Get projects for a specific client
- `GET /api/user/clients-with-counts` - Get clients with project/scope counts

### 4. Enhanced Scope Creation
**File:** `backend/app/services/scopes.py`

- Improved project validation when creating scopes
- Verifies user has access to project's workspace
- Ensures project belongs to the specified workspace

## API Usage Examples

### Get User's Clients
```http
GET /api/user/clients?workspaceId={workspace_id}
Authorization: Bearer {token}
```

Response:
```json
[
  {
    "id": "client-uuid",
    "name": "Client Name",
    "status": "active",
    "industry": "Technology",
    ...
  }
]
```

### Get User's Projects
```http
GET /api/user/projects?workspaceId={workspace_id}&clientId={client_id}
Authorization: Bearer {token}
```

Response:
```json
[
  {
    "id": "project-uuid",
    "name": "Project Name",
    "client_id": "client-uuid",
    "client_name": "Client Name",
    "status": "active",
    ...
  }
]
```

### Get Scopes by Client
```http
GET /api/scopes?clientId={client_id}&workspaceId={workspace_id}
Authorization: Bearer {token}
```

### Get Scopes by Project
```http
GET /api/scopes?projectId={project_id}&workspaceId={workspace_id}
Authorization: Bearer {token}
```

### Create Scope with Project
```http
POST /api/scopes
Authorization: Bearer {token}
Content-Type: application/json

{
  "workspaceId": "workspace-uuid",
  "projectId": "project-uuid",  // Optional - links scope to project
  "title": "Scope Title",
  "inputType": "pdf",
  ...
}
```

## Scope Organization

### How Scopes are Organized

1. **By Workspace:** All scopes belong to a workspace
2. **By Project (Optional):** Scopes can be linked to a project
3. **By Client (Via Project):** If scope has a project, it's associated with that project's client

### Scope Hierarchy
```
Workspace
  └── Client
      └── Project
          └── Scope (with sections)
```

### Access Control Flow

1. User creates/views scope
2. System checks:
   - User is member of scope's workspace
   - If scope has project: User has access to project's workspace
   - If filtering by client: Client belongs to accessible workspace

## Database Schema

### Existing Fields (No Migration Needed)
- `scopes.project_id` - Links scope to project
- `scopes.workspace_id` - Links scope to workspace
- `scopes.created_by` - Links scope to user
- `projects.client_id` - Links project to client
- `projects.workspace_id` - Links project to workspace
- `clients.workspace_id` - Links client to workspace

### Relationships
- Scope → Project (optional, many-to-one)
- Project → Client (optional, many-to-one)
- All entities → Workspace (required, many-to-one)
- User → Workspace (via WorkspaceMember, many-to-many)

## Frontend Integration

### Recommended Frontend Flow

1. **Scope Creation:**
   ```
   User selects workspace
   → Frontend calls GET /api/user/clients?workspaceId={id}
   → User selects client (optional)
   → Frontend calls GET /api/user/projects?clientId={id}
   → User selects project (optional)
   → Create scope with projectId
   ```

2. **Scope Listing:**
   ```
   User views scopes
   → Filter by client: GET /api/scopes?clientId={id}
   → Filter by project: GET /api/scopes?projectId={id}
   → Or view all: GET /api/scopes?workspaceId={id}
   ```

3. **Organization View:**
   ```
   User views clients
   → GET /api/user/clients-with-counts
   → Shows clients with project/scope counts
   → Click client → Show projects → Show scopes
   ```

## Testing

### Test Scenarios

1. **User can see only their workspace's clients**
   - Create client in workspace A
   - User in workspace B should not see it

2. **Scopes are filtered by client**
   - Create scope with project linked to client A
   - Filter by client A → scope appears
   - Filter by client B → scope does not appear

3. **Scope creation validates project access**
   - User tries to create scope with project from different workspace
   - Should fail with access denied

4. **User can get projects for a client**
   - GET /api/user/clients/{client_id}/projects
   - Returns only projects user has access to

## Files Modified

1. ✅ `backend/app/services/scopes.py` - Added client_id filtering
2. ✅ `backend/app/api/routes/scopes.py` - Added client_id query parameter
3. ✅ `backend/app/services/user_client_project.py` - New service (created)
4. ✅ `backend/app/api/routes/user_resources.py` - New API routes (created)
5. ✅ `backend/app/api/routes/__init__.py` - Registered new router

## Next Steps

1. **Frontend Integration:**
   - Update scope creation form to include client/project selection
   - Add client/project filters to scope listing
   - Create organization view (clients → projects → scopes)

2. **Optional Enhancements:**
   - Add bulk scope assignment to projects
   - Add scope move between projects
   - Add client/project statistics dashboard

## API Endpoints Summary

### User Resources
- `GET /api/user/clients` - Get user's clients
- `GET /api/user/projects` - Get user's projects
- `GET /api/user/clients/{client_id}/projects` - Get client's projects
- `GET /api/user/clients-with-counts` - Get clients with counts

### Scopes (Enhanced)
- `GET /api/scopes?clientId={id}` - Filter by client
- `GET /api/scopes?projectId={id}` - Filter by project
- `POST /api/scopes` - Create scope (with optional projectId)
