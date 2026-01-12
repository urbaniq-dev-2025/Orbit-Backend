from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.api import deps
from app.core.logging import get_logger
from app.schemas.onboarding import (
    GoalsStepPayload,
    OnboardingStatusResponse,
    PlanStepPayload,
    TeamStepPayload,
    WorkspaceStepPayload,
)
from app.services.email import EmailRateLimitError, get_email_dispatcher
from app.services import onboarding as onboarding_service

router = APIRouter()
logger = get_logger(__name__)


def _map_onboarding_exception(exc: Exception) -> HTTPException:
    if isinstance(exc, onboarding_service.OnboardingCompletedError):
        return HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        )
    if isinstance(exc, onboarding_service.InvalidStepError):
        return HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        )
    if isinstance(exc, onboarding_service.WorkspaceRequiredError):
        return HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Unable to process onboarding request.",
    )


@router.get("/status", response_model=OnboardingStatusResponse)
async def get_status(
    session: deps.SessionDep, current_user=Depends(deps.get_current_user)
) -> OnboardingStatusResponse:
    return await onboarding_service.get_status(session, current_user)


@router.post("/step1", response_model=OnboardingStatusResponse)
async def complete_step_one(
    payload: WorkspaceStepPayload,
    session: deps.SessionDep,
    current_user=Depends(deps.get_current_user),
) -> OnboardingStatusResponse:
    try:
        return await onboarding_service.handle_workspace_step(session, current_user, payload)
    except Exception as exc:
        logger.exception(
            "Error in onboarding step1",
            extra={"user_id": str(current_user.id), "error": str(exc)},
        )
        raise _map_onboarding_exception(exc) from exc


@router.post("/step2", response_model=OnboardingStatusResponse)
async def complete_step_two(
    payload: TeamStepPayload,
    session: deps.SessionDep,
    current_user=Depends(deps.get_current_user),
) -> OnboardingStatusResponse:
    dispatcher = get_email_dispatcher()
    try:
        return await onboarding_service.handle_team_step(
            session, current_user, payload, dispatcher=dispatcher
        )
    except EmailRateLimitError as exc:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=str(exc)
        ) from exc
    except Exception as exc:
        raise _map_onboarding_exception(exc) from exc


@router.post("/step3", response_model=OnboardingStatusResponse)
async def complete_step_three(
    payload: GoalsStepPayload,
    session: deps.SessionDep,
    current_user=Depends(deps.get_current_user),
) -> OnboardingStatusResponse:
    try:
        return await onboarding_service.handle_goals_step(session, current_user, payload)
    except Exception as exc:
        raise _map_onboarding_exception(exc) from exc


@router.post("/step4", response_model=OnboardingStatusResponse)
async def complete_step_four(
    payload: PlanStepPayload,
    session: deps.SessionDep,
    current_user=Depends(deps.get_current_user),
) -> OnboardingStatusResponse:
    try:
        return await onboarding_service.handle_plan_step(session, current_user, payload)
    except Exception as exc:
        raise _map_onboarding_exception(exc) from exc


@router.post("/complete", response_model=OnboardingStatusResponse)
async def finalize_onboarding(
    session: deps.SessionDep, current_user=Depends(deps.get_current_user)
) -> OnboardingStatusResponse:
    dispatcher = get_email_dispatcher()
    try:
        return await onboarding_service.complete_onboarding(
            session, current_user, dispatcher=dispatcher
        )
    except Exception as exc:
        raise _map_onboarding_exception(exc) from exc


@router.post("/skip", response_model=OnboardingStatusResponse)
async def skip_onboarding(
    session: deps.SessionDep, current_user=Depends(deps.get_current_user)
) -> OnboardingStatusResponse:
    dispatcher = get_email_dispatcher()
    try:
        return await onboarding_service.skip_onboarding(
            session, current_user, dispatcher=dispatcher
        )
    except Exception as exc:
        raise _map_onboarding_exception(exc) from exc


