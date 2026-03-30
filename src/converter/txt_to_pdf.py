"""Plain text → PDF converter.

Heuristics (same as txt_to_docx):
- First non-blank, short line → rendered as bold title
- Subsequent lines rendered as body text
"""
from __future__ import annotations

import os
import re

from .base import BaseConverter, ConversionResult
from ._pdf_utils import make_pdf, set_font


class TxtToPdfConverter(BaseConverter):
    FROM_EXT = ".txt"
    TO_EXT = ".pdf"

    def convert(self, input_path: str, output_path: str) -> ConversionResult:
        try:
            from fpdf import FPDF  # noqa: F401
        except ImportError:
            raise ImportError("fpdf2 required: pip install fpdf2")

        with open(input_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()

        pdf = make_pdf()

        lines = content.splitlines()
        title_used = False

        for line in lines:
            stripped = line.strip()
            if not stripped:
                pdf.ln(4)
                continue
            if not title_used and len(stripped) < 80 and not stripped.endswith("."):
                set_font(pdf, style="B", size=18)
                pdf.multi_cell(0, 10, stripped, new_x="LMARGIN", new_y="NEXT")
                pdf.ln(4)
                title_used = True
            elif _looks_like_heading(stripped) and title_used:
                set_font(pdf, style="B", size=13)
                pdf.multi_cell(0, 8, stripped, new_x="LMARGIN", new_y="NEXT")
                pdf.ln(2)
            else:
                set_font(pdf, size=11)
                pdf.multi_cell(0, 6, stripped, new_x="LMARGIN", new_y="NEXT")

        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        pdf.output(output_path)

        return ConversionResult(
            output_path=output_path,
            success=True,
            message=f"Converted {os.path.basename(input_path)} → {os.path.basename(output_path)}",
        )


def _looks_like_heading(line: str) -> bool:
    if len(line) > 60:
        return False
    if line.endswith((".", "。", "!", "?", "！", "？")):
        return False
    if re.search(r"[A-Z\u4e00-\u9fff]", line):
        return True
    return False
