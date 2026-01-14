from fastapi import APIRouter

from . import activity, admin, auth, clients, dashboard, health, onboarding, projects, proposals, quotations, scopes, templates, workspaces

api_router = APIRouter(prefix="/api")
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(onboarding.router, prefix="/onboarding", tags=["onboarding"])
api_router.include_router(workspaces.router, prefix="/workspaces", tags=["workspaces"])
api_router.include_router(clients.router, prefix="/clients", tags=["clients"])
api_router.include_router(projects.router, prefix="/projects", tags=["projects"])
api_router.include_router(scopes.router, prefix="/scopes", tags=["scopes"])
api_router.include_router(quotations.router, prefix="/quotations", tags=["quotations"])
api_router.include_router(proposals.router, prefix="/proposals", tags=["proposals"])
api_router.include_router(activity.router, prefix="/activity", tags=["activity"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
api_router.include_router(templates.router, prefix="/templates", tags=["templates"])
api_router.include_router(admin.router, prefix="/admin", tags=["admin"])

__all__ = ["api_router"]


