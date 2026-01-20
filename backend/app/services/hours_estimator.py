"""
Hours Estimation Service

Provides market-standard hours estimation for features based on complexity,
developer level, and industry benchmarks.
"""

from __future__ import annotations

from typing import Literal, Optional

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
        "junior": 1.5,  # Junior takes 50% more time
        "mid": 1.0,  # Baseline
        "senior": 0.75,  # Senior is 25% faster
    }

    # Integration complexity multipliers
    INTEGRATION_MULTIPLIER = 1.3  # 30% more time for integrations
    UI_COMPLEXITY_MULTIPLIER = 1.2  # 20% more time for complex UI

    # Market benchmark ranges (for validation)
    MARKET_BENCHMARKS = {
        "Low": {"min": 4, "max": 8, "avg": 6},
        "Medium": {"min": 8, "max": 16, "avg": 12},
        "High": {"min": 16, "max": 32, "avg": 24},
    }

    def estimate_hours(
        self,
        feature_description: str,
        complexity: Complexity,
        developer_level: Literal["junior", "mid", "senior"] = "mid",
        developer_experience_years: int = 3,
        has_integration: bool = False,
        has_ui: bool = False,
    ) -> dict:
        """
        Estimate hours for a feature.

        Args:
            feature_description: Description of the feature
            complexity: Complexity level (Low/Medium/High)
            developer_level: Developer level (junior/mid/senior)
            developer_experience_years: Years of experience
            has_integration: Whether feature requires external integrations
            has_ui: Whether feature has UI components

        Returns:
            Dictionary with hours breakdown and confidence score
        """
        base = self.COMPLEXITY_MULTIPLIERS[complexity].copy()

        # Adjust for integrations
        if has_integration:
            base["development"] *= self.INTEGRATION_MULTIPLIER
            base["testing"] *= 1.2  # More testing needed for integrations

        # Adjust for UI complexity
        if has_ui:
            base["development"] *= self.UI_COMPLEXITY_MULTIPLIER
            base["testing"] *= 1.3  # UI testing takes more time

        # Adjust for developer level
        developer_multiplier = self.DEVELOPER_MULTIPLIERS.get(developer_level, 1.0)
        # Fine-tune based on experience years
        if developer_level == "mid" and developer_experience_years < 3:
            developer_multiplier = 1.1
        elif developer_level == "mid" and developer_experience_years > 5:
            developer_multiplier = 0.9

        for key in base:
            base[key] *= developer_multiplier

        total = sum(base.values())

        # Calculate confidence based on complexity and factors
        confidence = self._calculate_confidence(
            complexity, has_integration, has_ui, developer_level
        )

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

        # Lower confidence for high complexity
        if complexity == "High":
            base_confidence -= 0.1
        elif complexity == "Low":
            base_confidence += 0.05

        # Lower confidence with integrations (more variables)
        if has_integration:
            base_confidence -= 0.05

        # Lower confidence with UI (subjective complexity)
        if has_ui:
            base_confidence -= 0.03

        # Higher confidence with senior developers (more predictable)
        if developer_level == "senior":
            base_confidence += 0.05

        return max(0.5, min(1.0, base_confidence))

    def validate_estimate(
        self, feature_type: str, complexity: Complexity, estimated_hours: float
    ) -> dict:
        """
        Validate estimate against market benchmarks.

        Args:
            feature_type: Type of feature (for future feature-specific benchmarks)
            complexity: Complexity level
            estimated_hours: Estimated hours to validate

        Returns:
            Validation result with market comparison
        """
        benchmark = self.MARKET_BENCHMARKS.get(complexity, {})
        if not benchmark:
            return {
                "is_within_range": True,
                "recommendation": "No benchmark available",
                "market_min": None,
                "market_max": None,
                "market_avg": None,
            }

        market_min = benchmark["min"]
        market_max = benchmark["max"]
        market_avg = benchmark["avg"]

        is_within_range = market_min <= estimated_hours <= market_max

        # Calculate deviation from average
        deviation = abs(estimated_hours - market_avg) / market_avg
        if deviation > 0.3:  # More than 30% deviation
            recommendation = "Review estimate - significant deviation from market average"
        elif not is_within_range:
            recommendation = "Adjust estimate - outside market range"
        else:
            recommendation = "Accept - within market standards"

        return {
            "is_within_range": is_within_range,
            "market_min": market_min,
            "market_max": market_max,
            "market_avg": market_avg,
            "deviation_percent": round(deviation * 100, 1),
            "recommendation": recommendation,
        }

    def detect_complexity(self, feature_description: str) -> Complexity:
        """
        Auto-detect complexity from feature description.

        This is a simple heuristic - can be enhanced with ML later.
        """
        description_lower = feature_description.lower()

        # High complexity indicators
        high_indicators = [
            "algorithm",
            "machine learning",
            "ai",
            "real-time",
            "scalable",
            "distributed",
            "complex",
            "advanced",
            "optimization",
            "performance",
        ]

        # Low complexity indicators
        low_indicators = [
            "simple",
            "basic",
            "crud",
            "form",
            "list",
            "display",
            "view",
            "read-only",
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
            "api",
            "integration",
            "third-party",
            "external",
            "webhook",
            "oauth",
            "payment gateway",
            "stripe",
            "paypal",
            "google",
            "facebook",
            "twitter",
        ]
        return any(keyword in description_lower for keyword in integration_keywords)

    def has_ui(self, feature_description: str) -> bool:
        """Detect if feature has UI components."""
        description_lower = feature_description.lower()
        ui_keywords = [
            "ui",
            "interface",
            "screen",
            "page",
            "component",
            "design",
            "user experience",
            "ux",
            "frontend",
            "responsive",
            "mobile",
        ]
        return any(keyword in description_lower for keyword in ui_keywords)
