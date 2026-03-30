"""DOCX → PDF converter.

Uses fpdf2 to generate a PDF from Word document content.
Preserves: headings (sized by level), bold/italic runs, paragraph text, tables.
"""
from __future__ import annotations

import os
import re

from .base import BaseConverter, ConversionResult
from ._pdf_utils import make_pdf, set_font

_HEADING_SIZES = {1: 20, 2: 16, 3: 14, 4: 12, 5: 11, 6: 10}


class DocxToPdfConverter(BaseConverter):
    FROM_EXT = ".docx"
    TO_EXT = ".pdf"

    def convert(self, input_path: str, output_path: str) -> ConversionResult:
        try:
            import docx
            from fpdf import FPDF  # noqa: F401
        except ImportError:
            raise ImportError(
                "python-docx and fpdf2 required: pip install python-docx fpdf2"
            )

        doc = docx.Document(input_path)
        pdf = make_pdf()

        for block in doc.element.body:
            local = block.tag.split("}")[-1] if "}" in block.tag else block.tag
            if local == "p":
                para = docx.text.paragraph.Paragraph(block, doc)
                _write_paragraph(pdf, para)
            elif local == "tbl":
                table = docx.table.Table(block, doc)
                _write_table(pdf, table)

        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        pdf.output(output_path)

        return ConversionResult(
            output_path=output_path,
            success=True,
            message=f"Converted {os.path.basename(input_path)} → {os.path.basename(output_path)}",
        )


# ── helpers ──────────────────────────────────────────────────────────────────

def _write_paragraph(pdf, para) -> None:
    text = para.text
    if not text.strip():
        pdf.ln(4)
        return

    style_name = para.style.name if para.style else ""

    m = re.search(r"(\d+)", style_name) if style_name.startswith("Heading") else None
    if m:
        level = min(max(int(m.group(1)), 1), 6)
        set_font(pdf, style="B", size=_HEADING_SIZES[level])
        pdf.multi_cell(0, 8, text.strip(), new_x="LMARGIN", new_y="NEXT")
        set_font(pdf, size=11)
        pdf.ln(2)
        return

    if "List Bullet" in style_name:
        set_font(pdf, size=11)
        pdf.multi_cell(0, 6, f"  \u2022  {text.strip()}", new_x="LMARGIN", new_y="NEXT")
        return

    if "List Number" in style_name:
        set_font(pdf, size=11)
        pdf.multi_cell(0, 6, f"  {text.strip()}", new_x="LMARGIN", new_y="NEXT")
        return

    if "Quote" in style_name or "Intense Quote" in style_name:
        set_font(pdf, style="I", size=11)
        pdf.multi_cell(0, 6, text.strip(), new_x="LMARGIN", new_y="NEXT")
        set_font(pdf, size=11)
        return

    set_font(pdf, size=11)
    pdf.multi_cell(0, 6, text.strip(), new_x="LMARGIN", new_y="NEXT")


def _write_table(pdf, table) -> None:
    if not table.rows:
        return

    col_count = max(len(row.cells) for row in table.rows)
    col_w = pdf.epw / col_count

    pdf.ln(3)
    for ri, row in enumerate(table.rows):
        row_h = 7
        for ci, cell in enumerate(row.cells[:col_count]):
            cell_text = " ".join(
                p.text.strip() for p in cell.paragraphs if p.text.strip()
            )
            style = "B" if ri == 0 else ""
            set_font(pdf, style=style, size=10)
            x = pdf.l_margin + ci * col_w
            pdf.set_xy(x, pdf.get_y())
            pdf.multi_cell(col_w, row_h, cell_text, border=1, new_x="RIGHT", new_y="TOP")
        pdf.ln(row_h)

    set_font(pdf, size=11)
    pdf.ln(3)
