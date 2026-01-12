from __future__ import annotations

from pathlib import Path

import pytest

from clarivo_ingestion.schemas.scope import ScopeDocument

FIXTURES_ROOT = Path(__file__).resolve().parents[1] / "test-fixtures" / "scope"
CANONICAL_MODULES = {
    "Authentication & Profile",
    "Location & Store Management",
    "Menu Management",
    "Cart & Ordering",
    "Payments & Checkout",
    "Order Tracking & History",
    "Offers & Promotions",
    "Rewards & Loyalty",
    "Notifications & Geofencing",
    "Support & Help Center",
    "Admin Back Office (Menu, Offers, Orders)",
    "POS & Third-Party Integrations",
    "Analytics & Reporting",
    "Infrastructure & DevOps",
    "QA, Testing & Release Pipeline",
}


def _fixture_directories() -> list[Path]:
    if not FIXTURES_ROOT.exists():
        return []
    return sorted(
        [path for path in FIXTURES_ROOT.iterdir() if path.is_dir()],
        key=lambda item: item.name,
    )


def _load_scope(scope_path: Path) -> ScopeDocument:
    return ScopeDocument.model_validate_json(scope_path.read_text())


def _module_names(scope: ScopeDocument) -> set[str]:
    return {module.name for module in scope.modules}


@pytest.mark.parametrize("fixture_dir", _fixture_directories())
def test_llm_scope_is_at_least_as_comprehensive(fixture_dir: Path) -> None:
    heuristic_path = fixture_dir / "heuristic.json"
    llm_path = fixture_dir / "llm.json"

    if not heuristic_path.exists() or not llm_path.exists():
        pytest.skip(f"Fixture {fixture_dir.name} is incomplete.")

    heuristic_scope = _load_scope(heuristic_path)
    llm_scope = _load_scope(llm_path)

    heuristic_modules = _module_names(heuristic_scope)
    llm_modules = _module_names(llm_scope)

    # Basic regression signal: the LLM should not return fewer modules.
    assert len(llm_modules) >= len(heuristic_modules)

    # Track how many canonical modules are covered.
    llm_canonical_hits = llm_modules & CANONICAL_MODULES
    heuristic_canonical_hits = heuristic_modules & CANONICAL_MODULES

    assert len(llm_canonical_hits) >= len(heuristic_canonical_hits)

    # Ensure the LLM path does not regress on feature count.
    assert len(llm_scope.features) >= len(heuristic_scope.features)








