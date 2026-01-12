from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, EmailStr, Field, conlist, constr

OnboardingStep = Literal["workspace", "team", "goals", "plan", "complete"]
PlanSelection = Literal["starter", "growth", "enterprise"]


class WorkspaceStepPayload(BaseModel):
    name: constr(min_length=1, max_length=255)
    primary_color: Optional[str] = Field(None, alias="primaryColor", max_length=7)
    secondary_color: Optional[str] = Field(None, alias="secondaryColor", max_length=7)
    logo_url: Optional[str] = Field(None, alias="logoUrl", max_length=500)
    website_url: Optional[str] = Field(None, alias="websiteUrl", max_length=255)
    team_size: Optional[str] = Field(None, alias="teamSize", max_length=50)
    data_handling: Optional[str] = Field(None, alias="dataHandling", max_length=50)

    class Config:
        allow_population_by_field_name = True


class TeamStepPayload(BaseModel):
    team_size: Optional[str] = Field(None, alias="teamSize", max_length=50)
    invites: conlist(EmailStr, max_items=20) = Field(default_factory=list)
    invite_message: Optional[str] = Field(None, alias="inviteMessage", max_length=1000)

    class Config:
        allow_population_by_field_name = True


class GoalsStepPayload(BaseModel):
    goals: conlist(constr(min_length=1, max_length=100), min_items=1) = Field(
        default_factory=list
    )
    custom_goal: Optional[str] = Field(None, alias="customGoal", max_length=500)

    class Config:
        allow_population_by_field_name = True


class PlanStepPayload(BaseModel):
    plan: PlanSelection
    billing_country: Optional[str] = Field(None, alias="billingCountry", max_length=100)
    company_size: Optional[str] = Field(None, alias="companySize", max_length=100)

    class Config:
        allow_population_by_field_name = True


class OnboardingWorkspaceState(BaseModel):
    workspace_id: Optional[str] = Field(None, alias="workspaceId")
    name: Optional[str] = None
    primary_color: Optional[str] = Field(None, alias="primaryColor")
    secondary_color: Optional[str] = Field(None, alias="secondaryColor")
    logo_url: Optional[str] = Field(None, alias="logoUrl")
    website_url: Optional[str] = Field(None, alias="websiteUrl")
    team_size: Optional[str] = Field(None, alias="teamSize")
    data_handling: Optional[str] = Field(None, alias="dataHandling")

    class Config:
        allow_population_by_field_name = True


class OnboardingTeamState(BaseModel):
    team_size: Optional[str] = Field(None, alias="teamSize")
    invites: list[EmailStr] = Field(default_factory=list)
    invite_message: Optional[str] = Field(None, alias="inviteMessage")

    class Config:
        allow_population_by_field_name = True


class OnboardingGoalsState(BaseModel):
    goals: list[str] = Field(default_factory=list)
    custom_goal: Optional[str] = Field(None, alias="customGoal")

    class Config:
        allow_population_by_field_name = True


class OnboardingPlanState(BaseModel):
    plan: Optional[PlanSelection] = None
    billing_country: Optional[str] = Field(None, alias="billingCountry")
    company_size: Optional[str] = Field(None, alias="companySize")
    checkout_url: Optional[str] = Field(None, alias="checkoutUrl")

    class Config:
        allow_population_by_field_name = True


class OnboardingStatusResponse(BaseModel):
    step: OnboardingStep
    steps_completed: list[str] = Field(default_factory=list, alias="stepsCompleted")
    completed: bool = False
    workspace: Optional[OnboardingWorkspaceState] = None
    team: Optional[OnboardingTeamState] = None
    goals: Optional[OnboardingGoalsState] = None
    plan: Optional[OnboardingPlanState] = None

    class Config:
        allow_population_by_field_name = True


