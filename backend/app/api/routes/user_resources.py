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
        clients = await user_resources_service.get_user_accessible_clients(
            session,
            current_user.id,
            workspace_id=workspace_id,
        )
        
        return [
            ClientSummary.model_validate(client)
            for client in clients
        ]
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
