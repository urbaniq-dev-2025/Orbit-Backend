from __future__ import annotations

import re
from io import BytesIO

from openpyxl import Workbook

from clarivo_ingestion.schemas.scope import ScopeDocument

HEADERS = [
    "Modules",
    "Features",
    "Interactions",
    "Notes",
    "Questions/Clarifications",
    "Answers",
]

_ILLEGAL_CHAR_RE = re.compile(r"[\000-\010\013\014\016-\037]")


def scope_to_excel_bytes(scope: ScopeDocument) -> bytes:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Features"
    sheet.append(HEADERS)

    module_map = _module_feature_map(scope)
    questions = "; ".join(_clean(q.question) for q in scope.open_questions) or ""
    answers = "; ".join(
        _clean(q.suggested_answer) for q in scope.open_questions if q.suggested_answer
    )

    for feature in scope.features:
        modules = module_map.get(_clean(feature.name), ["Unassigned"])
        interactions = "; ".join(_clean(item) for item in feature.acceptance_criteria) or ""
        notes = _clean(feature.summary)
        sheet.append(
            [
                ", ".join(modules),
                _clean(feature.name),
                interactions,
                notes,
                questions,
                answers,
            ]
        )

    buffer = BytesIO()
    workbook.save(buffer)
    buffer.seek(0)
    return buffer.read()


def _module_feature_map(scope: ScopeDocument) -> dict[str, list[str]]:
    mapping: dict[str, list[str]] = {}
    for module in scope.modules:
        module_name = _clean(module.name)
        for feature_name in module.features:
            mapping.setdefault(_clean(feature_name), []).append(module_name)
    return mapping or {"Unassigned": []}


def _clean(value: str | None) -> str:
    if value is None:
        return ""
    if not isinstance(value, str):
        value = str(value)
    return _ILLEGAL_CHAR_RE.sub("", value)

