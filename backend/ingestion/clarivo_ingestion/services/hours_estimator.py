"""
Hours Estimation Service for Ingestion

Provides market-standard hours estimation for features based on complexity.
This is a copy of the main backend service for use in ingestion service.
"""

from __future__ import annotations

from typing import Literal

Complexity = Literal["Low", "Medium", "High"]


class HoursEstimator:
    """Estimates development hours based on complexity and market standards."""

    # Base hours for mid-level developer (3 years experience)
    COMPLEXITY_MULTIPLIERS = {
        "Low": {
            "development": 4.0,
            "testing": 1.5,
            "code_review": 0.5,
            "documentation": 0.5,
        },
        "Medium": {
            "development": 8.0,
            "testing": 2.5,
            "code_review": 1.0,
            "documentation": 1.0,
        },
        "High": {
            "development": 16.0,
            "testing": 4.0,
            "code_review": 2.0,
            "documentation": 2.0,
        },
    }

    # Developer level multipliers (relative to mid-level)
    DEVELOPER_MULTIPLIERS = {
        "junior": 1.5,
        "mid": 1.0,
        "senior": 0.75,
    }

    # Integration complexity multipliers
    INTEGRATION_MULTIPLIER = 1.3
    UI_COMPLEXITY_MULTIPLIER = 1.2

    def estimate_hours(
        self,
        feature_description: str,
        complexity: Complexity,
        developer_level: Literal["junior", "mid", "senior"] = "mid",
        developer_experience_years: int = 3,
        has_integration: bool = False,
        has_ui: bool = False,
    ) -> dict:
        """Estimate hours for a feature."""
        base = self.COMPLEXITY_MULTIPLIERS[complexity].copy()

        # Adjust for integrations
        if has_integration:
            base["development"] *= self.INTEGRATION_MULTIPLIER
            base["testing"] *= 1.2

        # Adjust for UI complexity
        if has_ui:
            base["development"] *= self.UI_COMPLEXITY_MULTIPLIER
            base["testing"] *= 1.3

        # Adjust for developer level
        developer_multiplier = self.DEVELOPER_MULTIPLIERS.get(developer_level, 1.0)
        if developer_level == "mid" and developer_experience_years < 3:
            developer_multiplier = 1.1
        elif developer_level == "mid" and developer_experience_years > 5:
            developer_multiplier = 0.9

        for key in base:
            base[key] *= developer_multiplier

        total = sum(base.values())

        # Calculate confidence
        confidence = self._calculate_confidence(complexity, has_integration, has_ui, developer_level)

        return {
            "development": round(base["development"], 1),
            "testing": round(base["testing"], 1),
            "code_review": round(base["code_review"], 1),
            "documentation": round(base["documentation"], 1),
            "total": round(total, 1),
            "confidence": confidence,
        }

    def _calculate_confidence(
        self,
        complexity: Complexity,
        has_integration: bool,
        has_ui: bool,
        developer_level: str,
    ) -> float:
        """Calculate confidence score for the estimate."""
        base_confidence = 0.85

        if complexity == "High":
            base_confidence -= 0.1
        elif complexity == "Low":
            base_confidence += 0.05

        if has_integration:
            base_confidence -= 0.05

        if has_ui:
            base_confidence -= 0.03

        if developer_level == "senior":
            base_confidence += 0.05

        return max(0.5, min(1.0, base_confidence))

    def detect_complexity(self, feature_description: str) -> Complexity:
        """Auto-detect complexity from feature description."""
        description_lower = feature_description.lower()

        high_indicators = [
            "algorithm", "machine learning", "ai", "real-time", "scalable",
            "distributed", "complex", "advanced", "optimization", "performance",
        ]

        low_indicators = [
            "simple", "basic", "crud", "form", "list", "display", "view", "read-only",
        ]

        high_count = sum(1 for indicator in high_indicators if indicator in description_lower)
        low_count = sum(1 for indicator in low_indicators if indicator in description_lower)

        if high_count >= 2:
            return "High"
        elif low_count >= 2:
            return "Low"
        else:
            return "Medium"

    def has_integration(self, feature_description: str) -> bool:
        """Detect if feature requires external integrations."""
        description_lower = feature_description.lower()
        integration_keywords = [
            "api", "integration", "third-party", "external", "webhook",
            "oauth", "payment gateway", "stripe", "paypal", "google", "facebook", "twitter",
        ]
        return any(keyword in description_lower for keyword in integration_keywords)

    def has_ui(self, feature_description: str) -> bool:
        """Detect if feature has UI components."""
        description_lower = feature_description.lower()
        ui_keywords = [
            "ui", "interface", "screen", "page", "component", "design",
            "user experience", "ux", "frontend", "responsive", "mobile",
        ]
        return any(keyword in description_lower for keyword in ui_keywords)
