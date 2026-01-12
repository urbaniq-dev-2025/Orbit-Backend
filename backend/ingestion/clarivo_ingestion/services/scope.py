from __future__ import annotations

import re

from clarivo_ingestion.schemas.scope import (
    ExecutiveSummary,
    Feature,
    FunctionalRequirement,
    Module,
    NonFunctionalRequirement,
    OpenQuestion,
    Persona,
    ScopeDocument,
    TechnicalRequirement,
)


def _sentences(text: str) -> list[str]:
    candidates = re.split(r"(?<=[.!?])\s+", text.strip())
    return [sentence.strip() for sentence in candidates if sentence.strip()]


def _clean_bullet(line: str) -> str:
    return re.sub(r"^[-*\d.\s]+", "", line).strip()


class ScopeParser:
    """Heuristic parser to create a scope document from raw discovery text."""

    def parse(self, text: str) -> ScopeDocument:
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        sentences = _sentences(text)

        personas = self._extract_personas(lines, sentences)
        modules, features = self._extract_modules_and_features(lines)

        return ScopeDocument(
            executive_summary=self._build_executive_summary(sentences),
            personas=personas,
            modules=modules,
            features=features,
            functional_requirements=self._extract_functional_requirements(sentences),
            technical_requirements=self._extract_technical_requirements(sentences, lines),
            non_functional_requirements=self._extract_non_functional_requirements(sentences, lines),
            open_questions=self._extract_questions(lines),
        )

    def _build_executive_summary(self, sentences: list[str]) -> ExecutiveSummary:
        overview = " ".join(sentences[:2]) if sentences else ""
        key_points = sentences[:3]
        return ExecutiveSummary(overview=overview, key_points=key_points)

    def _extract_personas(self, lines: list[str], sentences: list[str]) -> list[Persona]:
        personas: list[Persona] = []
        for line in lines:
            if line.lower().startswith("persona"):
                name = line.split(":", maxsplit=1)[-1].strip() or "Persona"
                personas.append(Persona(name=name.title()))
            elif re.search(r"\b(user|customer|admin|manager|operator)\b", line, re.IGNORECASE):
                tokens = line.split(":")
                name = tokens[0].strip().title()
                desc = tokens[1].strip() if len(tokens) > 1 else line
                personas.append(Persona(name=name, description=desc))

        if not personas and sentences:
            inferred = sentences[0].split("for")[-1].strip().title()
            personas.append(Persona(name=inferred or "Primary Persona"))

        merged: dict[str, Persona] = {}
        for persona in personas:
            key = persona.name.lower()
            existing = merged.get(key)
            if existing:
                if persona.description and persona.description not in existing.description:
                    existing.description = (existing.description + " " + persona.description).strip()
            else:
                merged[key] = persona
        return list(merged.values())

    def _extract_modules_and_features(self, lines: list[str]) -> tuple[list[Module], list[Feature]]:
        modules: dict[str, set[str]] = {"General": set()}
        feature_data: dict[str, dict[str, set[str] | str]] = {}
        current_module = "General"
        last_feature: str | None = None

        for raw_line in lines:
            lower = raw_line.lower()
            module_match = re.match(r"(module|page|area|section)\s*[:\-]\s*(.+)", raw_line, re.IGNORECASE)
            if module_match:
                current_module = module_match.group(2).strip().title()
                modules.setdefault(current_module, set())
                last_feature = None
                continue

            if raw_line.isupper() and len(raw_line.split()) <= 4:
                current_module = raw_line.title()
                modules.setdefault(current_module, set())
                last_feature = None
                continue

            if self._looks_like_module_heading(raw_line):
                heading = raw_line.rstrip(":").strip()
                current_module = heading
                modules.setdefault(current_module, set())
                last_feature = None
                continue

            cleaned = _clean_bullet(raw_line)
            if not cleaned:
                continue

            if raw_line.startswith("-") or any(keyword in lower for keyword in ["feature", "module", "workflow", "screen", "page"]):
                feature_name = self._feature_name_from_text(cleaned)
                data = feature_data.setdefault(
                    feature_name,
                    {"summary": cleaned, "interactions": set(), "notes": set()},
                )
                data["interactions"].add(self._interaction_from_text(cleaned))
                data["notes"].add(cleaned)
                modules.setdefault(current_module, set()).add(feature_name)
                last_feature = feature_name
            elif last_feature:
                data = feature_data[last_feature]
                data["notes"].add(cleaned)
                if any(token in lower for token in ["allow", "enable", "user", "workflow", "step"]):
                    data["interactions"].add(self._interaction_from_text(cleaned))

        if "General" in modules and len(modules) > 1 and not modules["General"]:
            modules.pop("General")

        module_objects = [Module(name=name, features=sorted(list(features))) for name, features in modules.items()]

        feature_objects: list[Feature] = []
        for name, data in feature_data.items():
            interactions = sorted(data["interactions"])
            summary = next(iter(data["notes"]), "") if data["notes"] else ""
            feature_objects.append(
                Feature(
                    name=name,
                    summary=summary,
                    priority="P1" if any(keyword in summary.lower() for keyword in ["must", "critical"]) else "P2",
                    dependencies=[],
                    acceptance_criteria=interactions,
                )
            )

        if not feature_objects:
            feature_objects.append(Feature(name="General Feature", summary="Initial placeholder feature."))

        return module_objects, feature_objects

    def _feature_name_from_text(self, text: str) -> str:
        name = text
        if ":" in text:
            name = text.split(":", 1)[0]
        if "-" in name:
            name = name.split("-", 1)[0]
        return name.strip().title()[:80]

    def _looks_like_module_heading(self, line: str) -> bool:
        if not line or line.endswith("."):
            return False
        if line[0] in "-•*0123456789":
            return False
        if len(line.split()) > 10:
            return False
        stripped = line.strip()
        if stripped.islower():
            return False
        normalized = re.sub(r"[()]", " ", stripped)
        tokens = [token for token in re.split(r"[\s/&,-]+", normalized) if token]
        if len(tokens) < 2:
            return False
        capitalized = sum(1 for token in tokens if token[0].isalpha() and token[0].isupper())
        return capitalized / len(tokens) >= 0.6

    def _interaction_from_text(self, text: str) -> str:
        return text.strip().rstrip(".")

    def _extract_functional_requirements(self, sentences: list[str]) -> list[FunctionalRequirement]:
        requirements = [
            sentence
            for sentence in sentences
            if re.search(r"\b(should|must|allow|enable)\b", sentence, re.IGNORECASE)
        ]
        seen = set()
        unique = []
        for requirement in requirements:
            key = requirement.lower()
            if key not in seen:
                seen.add(key)
                unique.append(requirement)
        return [FunctionalRequirement(statement=req) for req in unique[:8]]

    def _extract_technical_requirements(self, sentences: list[str], lines: list[str]) -> list[TechnicalRequirement]:
        keywords = {"api", "integration", "database", "encryption", "authentication", "infrastructure"}
        candidates = sentences + [_clean_bullet(line) for line in lines if line.startswith("-")]
        matches = [sentence for sentence in candidates if any(keyword in sentence.lower() for keyword in keywords)]
        unique = []
        seen = set()
        for item in matches:
            key = item.lower()
            if key not in seen:
                seen.add(key)
                unique.append(item)
        return [TechnicalRequirement(statement=match) for match in unique[:5]]

    def _extract_non_functional_requirements(self, sentences: list[str], lines: list[str]) -> list[NonFunctionalRequirement]:
        keywords = {"performance", "scalability", "uptime", "latency", "security", "compliance"}
        candidates = sentences + [_clean_bullet(line) for line in lines if line.startswith("-")]
        matches = [sentence for sentence in candidates if any(keyword in sentence.lower() for keyword in keywords)]
        unique = []
        seen = set()
        for item in matches:
            key = item.lower()
            if key not in seen:
                seen.add(key)
                unique.append(item)
        return [NonFunctionalRequirement(statement=match) for match in unique[:5]]

    def _extract_questions(self, lines: list[str]) -> list[OpenQuestion]:
        questions = [line.strip() for line in lines if line.strip().endswith("?")]
        return [OpenQuestion(question=question) for question in questions[:5]]

