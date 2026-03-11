from fastapi import APIRouter

from . import (
    activity,
    admin,
    ai,
    auth,
    clients,
    credits,
    dashboard,
    health,
    notifications,
    onboarding,
    projects,
    proposals,
    quotations,
    reminders,
    scopes,
    settings,
    subscription,
    tasks,
    templates,
    user_resources,
    workspaces,
)

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
api_router.include_router(reminders.router, prefix="/reminders", tags=["reminders"])
api_router.include_router(activity.router, prefix="/activity", tags=["activity"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
api_router.include_router(templates.router, prefix="/templates", tags=["templates"])
api_router.include_router(admin.router, prefix="/admin", tags=["admin"])
api_router.include_router(ai.router, prefix="/ai", tags=["ai"])
api_router.include_router(tasks.router, prefix="/tasks", tags=["tasks"])
api_router.include_router(subscription.router, prefix="/subscription", tags=["subscription"])
api_router.include_router(credits.router, prefix="/credits", tags=["credits"])
api_router.include_router(user_resources.router, prefix="/user", tags=["user-resources"])
api_router.include_router(settings.router, tags=["settings"])
api_router.include_router(notifications.router, prefix="/notifications", tags=["notifications"])

__all__ = ["api_router"]


