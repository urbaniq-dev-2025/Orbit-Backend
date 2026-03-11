from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status

from app.api import deps
from app.core.logging import get_logger
from app.schemas.client import (
    ClientCreate,
    ClientDetail,
    ClientListResponse,
    ClientLogoResponse,
    ClientProjectItem,
    ClientProjectsResponse,
    ClientScopeItem,
    ClientScopesResponse,
    ClientStatsResponse,
    ClientSummary,
    ClientUpdate,
    RecentProject,
)
from app.services import client as client_service

logger = get_logger(__name__)
router = APIRouter()


@router.get("", response_model=ClientListResponse)
async def list_clients(
    session: deps.SessionDep,
    current_user=Depends(deps.get_current_user),
    workspace_id: uuid.UUID | None = Query(None, alias="workspaceId"),
    client_status: str | None = Query(None, alias="status", description="Filter by status: prospect, active, past"),
    search: str | None = Query(
        None,
        description="Search in name, industry, contact name, or email",
    ),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100, alias="pageSize"),
) -> ClientListResponse:
    """List clients with filters and pagination."""
    try:
        clients, total = await client_service.list_clients(
            session,
            current_user.id,
            workspace_id=workspace_id,
            status=client_status,
            search=search,
            page=page,
            page_size=page_size,
        )

        # Build client summaries with computed fields
        client_summaries = []
        for c in clients:
            # Compute location
            location = client_service._compute_location(c.city, c.state, c.country)
            
            # Get project and scope counts
            project_count = await client_service._get_client_project_count(session, c)
            scope_count = await client_service._get_client_scope_count(session, c)
            
            # Use model_validate with from_attributes for Pydantic v2 compatibility
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

        return ClientListResponse.model_validate({
            "clients": client_summaries,
            "total": total,
            "page": page,
            "pageSize": page_size,
            "hasMore": (page * page_size) < total,
        })
    except Exception as exc:
        logger.error("Error listing clients", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unable to retrieve clients: {exc}",
        ) from exc


@router.get("/{client_id}", response_model=ClientDetail)
async def get_client(
    client_id: uuid.UUID,
    session: deps.SessionDep,
    current_user=Depends(deps.get_current_user),
) -> ClientDetail:
    """Get client details by ID."""
    try:
        client = await client_service.get_client(session, client_id, current_user.id)
        
        # Compute location
        location = client_service._compute_location(client.city, client.state, client.country)
        
        # Get project and scope counts
        project_count = await client_service._get_client_project_count(session, client)
        scope_count = await client_service._get_client_scope_count(session, client)
        
        # Get recent projects (last 3)
        projects, _ = await client_service.get_client_projects(
            session, client_id, current_user.id, limit=3
        )
        recent_projects = [
            RecentProject(
                id=p.id,
                name=p.name,
                status=p.status,
                updated_at=p.updated_at,
            )
            for p in projects
        ]
        
        return ClientDetail(
            id=client.id,
            workspace_id=client.workspace_id,
            name=client.name,
            logo_url=client.logo_url,
            status=client.status,
            industry=client.industry,
            contact_name=client.contact_name,
            contact_email=client.contact_email,
            contact_phone=client.contact_phone,
            health_score=client.health_score,
            source=client.source,
            notes=client.notes,
            location=location,
            city=client.city,
            state=client.state,
            country=client.country,
            company_size=client.company_size,
            project_count=project_count,
            scope_count=scope_count,
            created_at=client.created_at,
            updated_at=client.updated_at,
            last_activity=client.last_activity,
            recent_projects=recent_projects,
        )
    except client_service.ClientNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client not found.",
        ) from exc
    except client_service.ClientAccessError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied.",
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unable to retrieve client.",
        ) from exc


@router.post("", response_model=ClientSummary, status_code=status.HTTP_201_CREATED)
async def create_client(
    payload: ClientCreate,
    session: deps.SessionDep,
    current_user=Depends(deps.get_current_user),
) -> ClientSummary:
    """Create a new client."""
    try:
        client = await client_service.create_client(session, current_user.id, payload)
        
        # Compute location
        location = client_service._compute_location(client.city, client.state, client.country)
        
        return ClientSummary.model_validate({
            "id": client.id,
            "workspaceId": client.workspace_id,
            "name": client.name,
            "logoUrl": client.logo_url,
            "status": client.status,
            "industry": client.industry,
            "contactName": client.contact_name or "",
            "contactEmail": client.contact_email or "",
            "contactPhone": client.contact_phone,
            "healthScore": client.health_score or 0,
            "source": client.source,
            "notes": client.notes,
            "location": location,
            "city": client.city,
            "state": client.state,
            "country": client.country,
            "companySize": client.company_size,
            "projectCount": 0,
            "scopeCount": 0,
            "createdAt": client.created_at,
            "updatedAt": client.updated_at,
            "lastActivity": client.last_activity,
        })
    except client_service.ClientAccessError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to workspace.",
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unable to create client.",
        ) from exc


@router.put("/{client_id}", response_model=ClientSummary)
async def update_client(
    client_id: uuid.UUID,
    payload: ClientUpdate,
    session: deps.SessionDep,
    current_user=Depends(deps.get_current_user),
) -> ClientSummary:
    """Update an existing client."""
    try:
        client = await client_service.update_client(session, client_id, current_user.id, payload)
        
        # Compute location
        location = client_service._compute_location(client.city, client.state, client.country)
        
        # Get project and scope counts
        project_count = await client_service._get_client_project_count(session, client)
        scope_count = await client_service._get_client_scope_count(session, client)
        
        return ClientSummary.model_validate({
            "id": client.id,
            "workspaceId": client.workspace_id,
            "name": client.name,
            "logoUrl": client.logo_url,
            "status": client.status,
            "industry": client.industry,
            "contactName": client.contact_name or "",
            "contactEmail": client.contact_email or "",
            "contactPhone": client.contact_phone,
            "healthScore": client.health_score or 0,
            "source": client.source,
            "notes": client.notes,
            "location": location,
            "city": client.city,
            "state": client.state,
            "country": client.country,
            "companySize": client.company_size,
            "projectCount": project_count,
            "scopeCount": scope_count,
            "createdAt": client.created_at,
            "updatedAt": client.updated_at,
            "lastActivity": client.last_activity,
        })
    except client_service.ClientNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client not found.",
        ) from exc
    except client_service.ClientAccessError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied.",
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unable to update client.",
        ) from exc


@router.delete("/{client_id}", status_code=status.HTTP_200_OK)
async def delete_client(
    client_id: uuid.UUID,
    session: deps.SessionDep,
    current_user=Depends(deps.get_current_user),
) -> dict:
    """Delete a client (soft delete by default)."""
    try:
        await client_service.delete_client(session, client_id, current_user.id, soft_delete=True)
        return {"message": "Client deleted successfully"}
    except client_service.ClientNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client not found.",
        ) from exc
    except client_service.ClientAccessError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied.",
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unable to delete client.",
        ) from exc


@router.get("/stats", response_model=ClientStatsResponse)
async def get_client_stats(
    session: deps.SessionDep,
    current_user=Depends(deps.get_current_user),
    workspace_id: uuid.UUID | None = Query(None, alias="workspaceId"),
) -> ClientStatsResponse:
    """Get client statistics."""
    try:
        stats = await client_service.get_client_stats(
            session, current_user.id, workspace_id=workspace_id
        )
        return ClientStatsResponse(**stats)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unable to retrieve client statistics.",
        ) from exc


@router.get("/{client_id}/projects", response_model=ClientProjectsResponse)
async def get_client_projects(
    client_id: uuid.UUID,
    session: deps.SessionDep,
    current_user=Depends(deps.get_current_user),
    limit: int = Query(10, ge=1, le=100),
) -> ClientProjectsResponse:
    """Get projects associated with a client."""
    try:
        projects, total = await client_service.get_client_projects(
            session, client_id, current_user.id, limit=limit
        )
        
        project_items = [
            ClientProjectItem(
                id=p.id,
                name=p.name,
                status=p.status,
                description=p.description,
                updated_at=p.updated_at,
            )
            for p in projects
        ]
        
        return ClientProjectsResponse(projects=project_items, total=total)
    except client_service.ClientNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client not found.",
        )
    except client_service.ClientAccessError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied.",
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unable to retrieve client projects.",
        ) from exc


@router.get("/{client_id}/scopes", response_model=ClientScopesResponse)
async def get_client_scopes(
    client_id: uuid.UUID,
    session: deps.SessionDep,
    current_user=Depends(deps.get_current_user),
    limit: int = Query(10, ge=1, le=100),
) -> ClientScopesResponse:
    """Get scopes associated with a client."""
    try:
        scopes, total = await client_service.get_client_scopes(
            session, client_id, current_user.id, limit=limit
        )
        
        scope_items = []
        for scope in scopes:
            project_name = scope.project.name if scope.project and scope.project_id else "No Project"
            project_id = scope.project_id if scope.project_id else uuid.UUID("00000000-0000-0000-0000-000000000000")
            scope_items.append(
                ClientScopeItem(
                    id=scope.id,
                    name=scope.title,  # Scope uses 'title' field
                    status=scope.status,
                    project_id=project_id,
                    project_name=project_name,
                    updated_at=scope.updated_at,
                )
            )
        
        return ClientScopesResponse(scopes=scope_items, total=total)
    except client_service.ClientNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client not found.",
        )
    except client_service.ClientAccessError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied.",
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unable to retrieve client scopes.",
        ) from exc


@router.post("/{client_id}/logo", response_model=ClientLogoResponse, status_code=status.HTTP_200_OK)
async def upload_client_logo(
    client_id: uuid.UUID,
    session: deps.SessionDep,
    file: UploadFile = File(...),
    current_user=Depends(deps.get_current_user),
) -> ClientLogoResponse:
    """Upload a logo for a client."""
    try:
        # Validate file type
        allowed_extensions = {".jpg", ".jpeg", ".png", ".webp"}
        file_ext = None
        if file.filename:
            for ext in allowed_extensions:
                if file.filename.lower().endswith(ext):
                    file_ext = ext
                    break

        if not file_ext:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File type not supported. Allowed: {', '.join(allowed_extensions)}",
            )

        # Validate file size (5MB max)
        max_file_size = 5 * 1024 * 1024  # 5MB
        file_content = await file.read()
        file_size = len(file_content)

        if file_size > max_file_size:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File size exceeds maximum of {max_file_size // (1024 * 1024)}MB",
            )

        # TODO: Upload file to storage (S3, Cloudinary, etc.)
        # For now, create a placeholder file URL
        # In production, this should:
        # 1. Generate unique filename
        # 2. Upload to storage service
        # 3. Get public URL
        # 4. Update client logo_url

        # Placeholder: Save to local storage (for development)
        # In production, use S3 or similar
        upload_dir = Path("uploads") / "clients" / str(client_id)
        upload_dir.mkdir(parents=True, exist_ok=True)

        unique_filename = f"{uuid.uuid4()}{file_ext}"
        file_path = upload_dir / unique_filename

        # Save file
        with open(file_path, "wb") as f:
            f.write(file_content)

        # Generate URL (placeholder - in production this would be a cloud storage URL)
        logo_url = f"/uploads/clients/{client_id}/{unique_filename}"

        # Update client logo
        client = await client_service.update_client_logo(
            session, client_id, current_user.id, logo_url
        )

        return ClientLogoResponse(logo_url=client.logo_url)
    except client_service.ClientNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client not found.",
        ) from exc
    except client_service.ClientAccessError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied.",
        ) from exc
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unable to upload logo.",
        ) from exc
