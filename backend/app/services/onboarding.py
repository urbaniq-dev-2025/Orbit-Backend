from __future__ import annotations

import copy
import datetime as dt
import uuid
from typing import Any, Dict, List, Optional

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.models import User, Workspace, WorkspaceMember
from app.schemas.onboarding import (
    GoalsStepPayload,
    OnboardingGoalsState,
    OnboardingPlanState,
    OnboardingStatusResponse,
    OnboardingTeamState,
    OnboardingWorkspaceState,
    PlanStepPayload,
    TeamStepPayload,
    WorkspaceStepPayload,
)
from app.services.email import EmailDispatcher, EmailRateLimitError, get_email_dispatcher
from app.services import workspaces as workspace_service

STEP_SEQUENCE: List[str] = ["workspace", "team", "goals", "plan"]


class OnboardingError(Exception):
    """Base onboarding exception."""


class InvalidStepError(OnboardingError):
    """Raised when a user attempts to complete steps out of order."""


class OnboardingCompletedError(OnboardingError):
    """Raised when onboarding is already complete."""


class WorkspaceRequiredError(OnboardingError):
    """Raised when a workspace is required but missing."""


def _load_state(user: User) -> Dict[str, Any]:
    state = user.onboarding_state or {}
    if not isinstance(state, dict):
        return {}
    return state


def _save_state(user: User, state: Dict[str, Any]) -> None:
    """Save onboarding state to user and flag the column as modified."""
    user.onboarding_state = copy.deepcopy(state)
    flag_modified(user, "onboarding_state")


def _steps_completed(user: User) -> List[str]:
    step = user.onboarding_step or "none"
    if step == "complete":
        return STEP_SEQUENCE.copy()
    try:
        idx = STEP_SEQUENCE.index(step)
    except ValueError:
        idx = -1
    return STEP_SEQUENCE[: idx + 1]


def _next_step(user: User) -> str:
    if user.onboarding_completed or user.onboarding_step == "complete":
        return "complete"
    current = user.onboarding_step or "none"
    try:
        idx = STEP_SEQUENCE.index(current)
    except ValueError:
        idx = -1
    next_idx = idx + 1
    if next_idx >= len(STEP_SEQUENCE):
        return "complete"
    return STEP_SEQUENCE[next_idx]


async def _get_primary_workspace(
    session: AsyncSession, user_id: uuid.UUID
) -> Optional[Workspace]:
    stmt: Select[Workspace] = (
        select(Workspace)
        .join(WorkspaceMember, WorkspaceMember.workspace_id == Workspace.id)
        .where(
            WorkspaceMember.user_id == user_id,
            WorkspaceMember.status == "active",
        )
        .order_by(Workspace.created_at.asc())
    )
    result = await session.execute(stmt)
    return result.scalars().first()


def _build_workspace_state(
    workspace: Optional[Workspace], state: Optional[Dict[str, Any]]
) -> Optional[Dict[str, Any]]:
    if workspace is None and not state:
        return None
    data: Dict[str, Any] = {}
    if state:
        data.update(state)
    if workspace:
        data.update(
            {
                "workspaceId": str(workspace.id),
                "name": workspace.name,
                "primaryColor": workspace.brand_color,
                "secondaryColor": workspace.secondary_color,
                "logoUrl": workspace.logo_url,
                "websiteUrl": workspace.website_url,
                "teamSize": workspace.team_size,
                "dataHandling": workspace.data_handling,
            }
        )
    return data


async def _snapshot(session: AsyncSession, user: User) -> OnboardingStatusResponse:
    state = _load_state(user)
    workspace = await _get_primary_workspace(session, user.id)
    workspace_state = _build_workspace_state(workspace, state.get("workspace"))
    team_state = state.get("team")
    goals_state = state.get("goals")
    plan_state = state.get("plan")

    response = OnboardingStatusResponse(
        step=_next_step(user),
        stepsCompleted=_steps_completed(user),
        completed=bool(user.onboarding_completed),
        workspace=OnboardingWorkspaceState.parse_obj(workspace_state)
        if workspace_state
        else None,
        team=OnboardingTeamState.parse_obj(team_state) if team_state else None,
        goals=OnboardingGoalsState.parse_obj(goals_state) if goals_state else None,
        plan=OnboardingPlanState.parse_obj(plan_state) if plan_state else None,
    )
    return response


def _ensure_step(expected_step: str, user: User) -> None:
    if user.onboarding_completed:
        raise OnboardingCompletedError("Onboarding already completed.")
    current = _next_step(user)
    if expected_step != current:
        raise InvalidStepError(
            f"Step '{expected_step}' cannot be completed at this time. Next step is '{current}'."
        )


async def _ensure_workspace_exists(
    session: AsyncSession, user: User, dispatcher: EmailDispatcher, state: Dict[str, Any]
) -> Workspace:
    workspace = await _get_primary_workspace(session, user.id)
    if workspace:
        return workspace
    name = None
    workspace_state = state.get("workspace") if isinstance(state.get("workspace"), dict) else {}
    if workspace_state:
        name = workspace_state.get("name")
    if not name:
        name = f"{user.full_name or 'Orbit'} Workspace"
    workspace = await workspace_service.create_workspace(
        session,
        owner_id=user.id,
        name=name,
        logo_url=workspace_state.get("logoUrl"),
        brand_color=workspace_state.get("primaryColor"),
        secondary_color=workspace_state.get("secondaryColor"),
        website_url=workspace_state.get("websiteUrl"),
        team_size=workspace_state.get("teamSize"),
        data_handling=workspace_state.get("dataHandling"),
    )
    return workspace


async def get_status(session: AsyncSession, user: User) -> OnboardingStatusResponse:
    return await _snapshot(session, user)


async def handle_workspace_step(
    session: AsyncSession, user: User, payload: WorkspaceStepPayload
) -> OnboardingStatusResponse:
    _ensure_step("workspace", user)
    state = _load_state(user)
    workspace = await _get_primary_workspace(session, user.id)
    if workspace is None:
        workspace = await workspace_service.create_workspace(
            session,
            owner_id=user.id,
            name=payload.name,
            logo_url=payload.logo_url,
            brand_color=payload.primary_color,
            secondary_color=payload.secondary_color,
            website_url=payload.website_url,
            team_size=payload.team_size,
            data_handling=payload.data_handling,
        )
    else:
        workspace = await workspace_service.update_workspace(
            session,
            workspace,
            name=payload.name,
            logo_url=payload.logo_url,
            brand_color=payload.primary_color,
            secondary_color=payload.secondary_color,
            website_url=payload.website_url,
            team_size=payload.team_size,
            data_handling=payload.data_handling,
        )

    state["workspace"] = {
        "workspaceId": str(workspace.id),
        "name": workspace.name,
        "primaryColor": payload.primary_color or workspace.brand_color,
        "secondaryColor": payload.secondary_color or workspace.secondary_color,
        "logoUrl": payload.logo_url or workspace.logo_url,
        "websiteUrl": payload.website_url or workspace.website_url,
        "teamSize": payload.team_size or workspace.team_size,
        "dataHandling": payload.data_handling or workspace.data_handling,
    }
    _save_state(user, state)
    user.onboarding_step = "workspace"
    await session.commit()
    await session.refresh(user)
    return await _snapshot(session, user)


async def handle_team_step(
    session: AsyncSession,
    user: User,
    payload: TeamStepPayload,
    dispatcher: Optional[EmailDispatcher] = None,
) -> OnboardingStatusResponse:
    _ensure_step("team", user)
    state = _load_state(user)
    dispatcher = dispatcher or get_email_dispatcher()
    workspace = await _get_primary_workspace(session, user.id)
    if workspace is None:
        raise WorkspaceRequiredError("Workspace must be created before inviting team members.")

    invites_unique = []
    seen = set()
    for email in payload.invites:
        key = email.lower()
        if key not in seen:
            seen.add(key)
            invites_unique.append(email)

    now = dt.datetime.now(dt.timezone.utc)
    for email in invites_unique:
        stmt = select(WorkspaceMember).where(
            WorkspaceMember.workspace_id == workspace.id,
            WorkspaceMember.invited_email == email,
        )
        result = await session.execute(stmt)
        membership = result.scalar_one_or_none()
        if membership is None:
            membership = WorkspaceMember(
                workspace_id=workspace.id,
                invited_email=email,
                status="pending",
                invited_at=now,
            )
            session.add(membership)
        else:
            membership.invited_at = now
        await dispatcher.send_workspace_invite(
            email,
            workspace_name=workspace.name,
            inviter_name=user.full_name,
            invite_message=payload.invite_message,
        )

    state["team"] = {
        "teamSize": payload.team_size,
        "invites": invites_unique,
        "inviteMessage": payload.invite_message,
    }
    _save_state(user, state)
    user.onboarding_step = "team"
    await session.commit()
    await session.refresh(user)
    return await _snapshot(session, user)


async def handle_goals_step(
    session: AsyncSession, user: User, payload: GoalsStepPayload
) -> OnboardingStatusResponse:
    _ensure_step("goals", user)
    state = _load_state(user)
    state["goals"] = {
        "goals": payload.goals,
        "customGoal": payload.custom_goal,
    }
    _save_state(user, state)
    user.onboarding_step = "goals"
    await session.commit()
    await session.refresh(user)
    return await _snapshot(session, user)


async def handle_plan_step(
    session: AsyncSession, user: User, payload: PlanStepPayload
) -> OnboardingStatusResponse:
    _ensure_step("plan", user)
    state = _load_state(user)
    checkout_url = f"https://app.orbit.dev/checkout/{payload.plan}"
    plan_state = OnboardingPlanState(
        plan=payload.plan,
        billingCountry=payload.billing_country,
        companySize=payload.company_size,
        checkoutUrl=checkout_url,
    )
    state["plan"] = plan_state.dict(by_alias=True)
    _save_state(user, state)
    user.onboarding_step = "plan"
    await session.commit()
    await session.refresh(user)
    return await _snapshot(session, user)


async def complete_onboarding(
    session: AsyncSession, user: User, dispatcher: Optional[EmailDispatcher] = None
) -> OnboardingStatusResponse:
    if user.onboarding_completed:
        raise OnboardingCompletedError("Onboarding already completed.")
    state = _load_state(user)
    dispatcher = dispatcher or get_email_dispatcher()
    await _ensure_workspace_exists(session, user, dispatcher, state)
    user.onboarding_step = "complete"
    user.onboarding_completed = True
    await session.commit()
    await session.refresh(user)
    return await _snapshot(session, user)


async def skip_onboarding(
    session: AsyncSession, user: User, dispatcher: Optional[EmailDispatcher] = None
) -> OnboardingStatusResponse:
    if user.onboarding_completed:
        return await _snapshot(session, user)
    state = _load_state(user)
    dispatcher = dispatcher or get_email_dispatcher()
    workspace = await _ensure_workspace_exists(session, user, dispatcher, state)
    state.setdefault(
        "workspace",
        {
            "workspaceId": str(workspace.id),
            "name": workspace.name,
        },
    )
    _save_state(user, state)
    user.onboarding_step = "complete"
    user.onboarding_completed = True
    await session.commit()
    await session.refresh(user)
    return await _snapshot(session, user)


