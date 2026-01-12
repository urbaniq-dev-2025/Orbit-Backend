from __future__ import annotations

from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate

from clarivo_ingestion.schemas.scope import ScopeDocument


def scope_to_pdf_bytes(scope: ScopeDocument) -> bytes:
    """Convert scope document to a simple PDF for download."""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=LETTER, rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=72)
    story = []
    styles = getSampleStyleSheet()
    heading = styles["Heading1"]
    heading.spaceAfter = 12
    subheading = styles["Heading2"]
    body = styles["BodyText"]
    body.spaceAfter = 6

    story.append(Paragraph("Executive Summary", heading))
    story.append(Paragraph(_safe(scope.executive_summary.overview) or "Summary not provided.", body))
    if scope.executive_summary.key_points:
        story.append(Paragraph("Key Points", subheading))
        for point in scope.executive_summary.key_points:
            story.append(Paragraph(f"- {_safe(point)}", body))

    if scope.personas:
        story.append(PageBreak())
        story.append(Paragraph("Personas", heading))
        for persona in scope.personas:
            story.append(Paragraph(_safe(persona.name), subheading))
            if persona.description:
                story.append(Paragraph(_safe(persona.description), body))
            if persona.goals:
                story.append(Paragraph("Goals:", body))
                for goal in persona.goals:
                    story.append(Paragraph(f"- {_safe(goal)}", body))
            if persona.pain_points:
                story.append(Paragraph("Pain Points:", body))
                for pain in persona.pain_points:
                    story.append(Paragraph(f"- {_safe(pain)}", body))

    if scope.modules or scope.features:
        story.append(PageBreak())
        story.append(Paragraph("Modules & Features", heading))
        module_lookup = {module.name: module for module in scope.modules}
        for feature in scope.features:
            modules = [name for name, module in module_lookup.items() if feature.name in module.features]
            modules_label = ", ".join(modules) if modules else "Unassigned"
            title = f"{_safe(feature.name)} ({_safe(modules_label)})"
            story.append(Paragraph(title, subheading))
            story.append(Paragraph(f"Priority: {feature.priority}", body))
            if feature.summary:
                story.append(Paragraph(_safe(feature.summary), body))
            if feature.dependencies:
                deps = ", ".join(feature.dependencies)
                story.append(Paragraph(f"Dependencies: {_safe(deps)}", body))
            if feature.acceptance_criteria:
                story.append(Paragraph("Acceptance Criteria:", body))
                for criteria in feature.acceptance_criteria:
                    story.append(Paragraph(f"- {_safe(criteria)}", body))

    if scope.functional_requirements or scope.technical_requirements or scope.non_functional_requirements:
        story.append(PageBreak())
        story.append(Paragraph("Requirements", heading))

        if scope.functional_requirements:
            story.append(Paragraph("Functional", subheading))
            for req in scope.functional_requirements:
                story.append(Paragraph(f"- {_safe(req.statement)}", body))

        if scope.technical_requirements:
            story.append(Paragraph("Technical", subheading))
            for req in scope.technical_requirements:
                story.append(Paragraph(f"- {_safe(req.statement)}", body))

        if scope.non_functional_requirements:
            story.append(Paragraph("Non-Functional", subheading))
            for req in scope.non_functional_requirements:
                story.append(Paragraph(f"- {_safe(req.statement)}", body))

    if scope.open_questions:
        story.append(PageBreak())
        story.append(Paragraph("Open Questions", heading))
        for question in scope.open_questions:
            story.append(Paragraph(f"• {_safe(question.question)}", body))
            if question.suggested_answer:
                story.append(Paragraph(f"Suggested answer: {_safe(question.suggested_answer)}", body))

    doc.build(story)
    buffer.seek(0)
    return buffer.read()


def _safe(text: str | None) -> str:
    if not text:
        return ""
    return escape(text)

