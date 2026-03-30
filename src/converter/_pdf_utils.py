"""Shared utilities for PDF generation via fpdf2.

Registers a Unicode font so that CJK and other non-Latin characters render
correctly. Falls back gracefully if the preferred font is not found.
"""
from __future__ import annotations

import os

# Candidate Unicode fonts (checked in order)
_UNICODE_FONT_CANDIDATES = [
    "/Library/Fonts/Arial Unicode.ttf",
    "/System/Library/Fonts/STHeiti Light.ttc",
    "/System/Library/Fonts/PingFang.ttc",
]

_FONT_NAME = "UniFont"


def _find_unicode_font() -> str | None:
    for path in _UNICODE_FONT_CANDIDATES:
        if os.path.isfile(path):
            return path
    return None


def make_pdf(font_size: int = 11):
    """Return a configured FPDF instance with Unicode font support."""
    from fpdf import FPDF

    font_path = _find_unicode_font()

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    if font_path:
        pdf.add_font(_FONT_NAME, style="", fname=font_path)
        pdf.add_font(_FONT_NAME, style="B", fname=font_path)
        pdf.add_font(_FONT_NAME, style="I", fname=font_path)
        pdf.add_font(_FONT_NAME, style="BI", fname=font_path)
        pdf.set_font(_FONT_NAME, size=font_size)
        pdf._unicode_font = _FONT_NAME
    else:
        # Fallback: latin-only but won't crash
        pdf.set_font("Helvetica", size=font_size)
        pdf._unicode_font = None

    return pdf


def set_font(pdf, style: str = "", size: int = 11) -> None:
    """Set font on a pdf instance, using the registered Unicode font if available."""
    font = getattr(pdf, "_unicode_font", None) or "Helvetica"
    # fpdf2 built-in fonts don't have BI style; map it to B
    if font == "Helvetica" and style == "BI":
        style = "B"
    pdf.set_font(font, style=style, size=size)
