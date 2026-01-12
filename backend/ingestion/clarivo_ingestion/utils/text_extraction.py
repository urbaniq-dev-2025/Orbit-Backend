from __future__ import annotations

from io import BytesIO

from docx import Document
from pdfminer.high_level import extract_text as pdf_extract_text


def extract_text_from_bytes(filename: str | None, content: bytes) -> str:
    if not content:
        return ""

    lower_name = (filename or "").lower()
    try:
        if lower_name.endswith(".pdf"):
            return _extract_pdf_text(content)
        if lower_name.endswith(".docx"):
            return _extract_docx_text(content)
    except Exception:
        pass

    return content.decode("utf-8", errors="ignore")


def _extract_pdf_text(content: bytes) -> str:
    with BytesIO(content) as buffer:
        return pdf_extract_text(buffer) or ""


def _extract_docx_text(content: bytes) -> str:
    with BytesIO(content) as buffer:
        document = Document(buffer)
        return "\n".join(paragraph.text for paragraph in document.paragraphs if paragraph.text)
