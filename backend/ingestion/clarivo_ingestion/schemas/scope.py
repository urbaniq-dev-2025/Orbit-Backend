from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

Priority = Literal["P1", "P2", "P3"]


class ExecutiveSummary(BaseModel):
    overview: str = ""
    key_points: list[str] = Field(default_factory=list)


class Persona(BaseModel):
    name: str
    description: str = ""
    goals: list[str] = Field(default_factory=list)
    pain_points: list[str] = Field(default_factory=list)


class Feature(BaseModel):
    name: str
    summary: str = ""
    priority: Priority = "P2"
    dependencies: list[str] = Field(default_factory=list)
    acceptance_criteria: list[str] = Field(default_factory=list)


class Module(BaseModel):
    name: str
    description: str = ""
    features: list[str] = Field(default_factory=list)


class FunctionalRequirement(BaseModel):
    statement: str


class TechnicalRequirement(BaseModel):
    statement: str


class NonFunctionalRequirement(BaseModel):
    statement: str


class OpenQuestion(BaseModel):
    question: str
    suggested_answer: str | None = None


class ScopePreviewRequest(BaseModel):
    content: str = Field(min_length=10, max_length=200_000)


class ScopeDocument(BaseModel):
    executive_summary: ExecutiveSummary = Field(default_factory=ExecutiveSummary)
    personas: list[Persona] = Field(default_factory=list)
    modules: list[Module] = Field(default_factory=list)
    features: list[Feature] = Field(default_factory=list)
    functional_requirements: list[FunctionalRequirement] = Field(default_factory=list)
    technical_requirements: list[TechnicalRequirement] = Field(default_factory=list)
    non_functional_requirements: list[NonFunctionalRequirement] = Field(default_factory=list)
    open_questions: list[OpenQuestion] = Field(default_factory=list)


# New schema matching Output folder format
class ModuleFeature(BaseModel):
    """Feature within a module, matching Output folder format."""
    name: str
    description: str = ""
    subfeatures: list[str] = Field(default_factory=list)
    source: str = ""
    
    model_config = {"populate_by_name": True}  # Allow both subfeatures and subFeatures in JSON input


# Enhanced schemas with hours estimation
class HoursBreakdown(BaseModel):
    """Hours breakdown for a feature/sub-feature."""
    development: float = Field(..., ge=0, description="Development hours")
    testing: float = Field(..., ge=0, description="Testing hours")
    code_review: float = Field(..., ge=0, description="Code review hours")
    documentation: float = Field(..., ge=0, description="Documentation hours")
    total: float = Field(..., ge=0, description="Total hours")
    confidence: float = Field(..., ge=0, le=1, description="Confidence score (0-1)")

    class Config:
        allow_population_by_field_name = True


class SubFeature(BaseModel):
    """Sub-feature with hours estimation."""
    name: str
    description: str
    complexity: Literal["Low", "Medium", "High"] = "Medium"
    estimated_hours: float = Field(..., ge=0, alias="estimatedHours")
    hours_breakdown: HoursBreakdown = Field(..., alias="hoursBreakdown")
    assumptions: list[str] = Field(default_factory=list)
    dependencies: list[str] = Field(default_factory=list)

    class Config:
        allow_population_by_field_name = True


class EnhancedFeature(BaseModel):
    """Feature with sub-features and hours."""
    name: str
    description: str
    sub_features: list[SubFeature] = Field(default_factory=list, alias="subFeatures")
    total_hours: float = Field(..., ge=0, alias="totalHours")
    priority: Priority = "P2"

    class Config:
        allow_population_by_field_name = True


class EnhancedModule(BaseModel):
    """Module with features and hours estimation."""
    name: str
    description: str
    features: list[EnhancedFeature] = Field(default_factory=list)
    total_hours: float = Field(..., ge=0, alias="totalHours")
    order_index: int = Field(0, alias="orderIndex")

    class Config:
        allow_population_by_field_name = True


class EnhancedScopeDocument(BaseModel):
    """Enhanced scope document with hours estimation."""
    modules: list[EnhancedModule] = Field(default_factory=list)
    project_summary: dict = Field(default_factory=dict, alias="projectSummary")
    technical_requirements: list[str] = Field(default_factory=list, alias="technicalRequirements")
    non_functional_requirements: list[str] = Field(default_factory=list, alias="nonFunctionalRequirements")
    total_project_hours: float = Field(..., ge=0, alias="totalProjectHours")
    estimated_timeline_weeks: Optional[float] = Field(None, alias="estimatedTimelineWeeks")
    team_size_recommendation: Optional[int] = Field(None, alias="teamSizeRecommendation")

    class Config:
        allow_population_by_field_name = True


class OutputFormatModule(BaseModel):
    """Module in Output folder format with nested features."""
    name: str
    description: str = ""
    features: list[ModuleFeature] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)  # Optional assumptions field


class OutputFormatScopeDocument(BaseModel):
    """Scope document matching the format used in Output folder examples."""
    productName: str = ""
    vision: str = ""
    businessObjective: str = ""
    platform: str = ""
    productType: str = ""
    primaryUserRoles: list[str] = Field(default_factory=list)
    recommendedTechStack: dict[str, str] = Field(default_factory=dict)
    modules: list[OutputFormatModule] = Field(default_factory=list)
    featureModules: list[OutputFormatModule] = Field(default_factory=list)  # Alternative name used in scatterplot.json
    scopeNotes: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
    futureOpportunities: list[str] = Field(default_factory=list)

