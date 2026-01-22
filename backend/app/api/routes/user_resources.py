"""
API routes for user-accessible resources (clients, projects, scopes).
Provides endpoints to get user's clients and projects for organizing scopes.
"""

from __future__ import annotations

import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api import deps
from app.models import Client, Project
from app.schemas.client import ClientSummary
from app.schemas.project import ProjectSummary
from app.services import user_client_project as user_resources_service

router = APIRouter()


@router.get("/clients", response_model=List[ClientSummary])
async def get_user_clients(
    session: deps.SessionDep,
    current_user=Depends(deps.get_current_user),
    workspace_id: Optional[uuid.UUID] = Query(None, alias="workspaceId"),
) -> List[ClientSummary]:
    """
    Get all clients accessible to the current user.
    
    Returns clients from workspaces the user is a member of.
    """
    try:
        from app.services import client as client_service
        
        # Use the same service function as /api/clients to ensure consistency
        clients, total = await client_service.list_clients(
            session,
            current_user.id,
            workspace_id=workspace_id,
            status=None,  # Get all clients regardless of status for dropdown
            search=None,
            page=1,
            page_size=1000,  # Get all clients (high limit for dropdown)
        )
        
        # Build client summaries with proper formatting
        client_summaries = []
        for c in clients:
            # Compute location
            location = client_service._compute_location(c.city, c.state, c.country)
            
            # Get project and scope counts
            project_count = await client_service._get_client_project_count(session, c)
            scope_count = await client_service._get_client_scope_count(session, c)
            
            # Use model_validate with camelCase field names for Pydantic v2 compatibility
            client_summaries.append(
                ClientSummary.model_validate({
                    "id": c.id,
                    "workspaceId": c.workspace_id,
                    "name": c.name,
                    "logoUrl": c.logo_url,
                    "status": c.status,
                    "industry": c.industry,
                    "contactName": c.contact_name or "",
                    "contactEmail": c.contact_email or "",
                    "contactPhone": c.contact_phone,
                    "healthScore": c.health_score or 0,
                    "source": c.source,
                    "notes": c.notes,
                    "location": location,
                    "city": c.city,
                    "state": c.state,
                    "country": c.country,
                    "companySize": c.company_size,
                    "projectCount": project_count,
                    "scopeCount": scope_count,
                    "createdAt": c.created_at,
                    "updatedAt": c.updated_at,
                    "lastActivity": c.last_activity,
                })
            )
        
        return client_summaries
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve clients: {str(exc)}",
        ) from exc


@router.get("/projects", response_model=List[ProjectSummary])
async def get_user_projects(
    session: deps.SessionDep,
    current_user=Depends(deps.get_current_user),
    workspace_id: Optional[uuid.UUID] = Query(None, alias="workspaceId"),
    client_id: Optional[uuid.UUID] = Query(None, alias="clientId"),
) -> List[ProjectSummary]:
    """
    Get all projects accessible to the current user.
    
    Optionally filter by workspace_id or client_id.
    """
    try:
        projects = await user_resources_service.get_user_accessible_projects(
            session,
            current_user.id,
            workspace_id=workspace_id,
            client_id=client_id,
        )
        
        return [
            ProjectSummary(
                id=project.id,
                name=project.name,
                description=project.description,
                status=project.status,
                client_id=project.client_id,
                client_name=project.client.name if project.client else None,
                progress=project.progress,
            )
            for project in projects
        ]
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve projects: {str(exc)}",
        ) from exc


@router.get("/clients/{client_id}/projects", response_model=List[ProjectSummary])
async def get_client_projects_for_user(
    session: deps.SessionDep,
    client_id: uuid.UUID,
    current_user=Depends(deps.get_current_user),
) -> List[ProjectSummary]:
    """
    Get projects for a specific client that the user can access.
    """
    try:
        projects, has_access = await user_resources_service.get_client_projects_for_user(
            session,
            current_user.id,
            client_id,
        )
        
        if not has_access:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to client",
            )
        
        return [
            ProjectSummary(
                id=project.id,
                name=project.name,
                description=project.description,
                status=project.status,
                client_id=project.client_id,
                client_name=project.client.name if project.client else None,
                progress=project.progress,
            )
            for project in projects
        ]
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve client projects: {str(exc)}",
        ) from exc


@router.get("/clients-with-counts")
async def get_user_clients_with_counts(
    session: deps.SessionDep,
    current_user=Depends(deps.get_current_user),
    workspace_id: Optional[uuid.UUID] = Query(None, alias="workspaceId"),
):
    """
    Get clients accessible to user with project and scope counts.
    
    Useful for displaying client organization with statistics.
    """
    try:
        clients_data = await user_resources_service.get_user_clients_with_project_counts(
            session,
            current_user.id,
            workspace_id=workspace_id,
        )
        
        return [
            {
                "client": {
                    "id": str(data["client"].id),
                    "name": data["client"].name,
                    "status": data["client"].status,
                    "industry": data["client"].industry,
                },
                "project_count": data["project_count"],
                "scope_count": data["scope_count"],
            }
            for data in clients_data
        ]
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve clients with counts: {str(exc)}",
        ) from exc
