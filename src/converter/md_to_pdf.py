"""Markdown → PDF converter.

Renders Markdown to PDF using fpdf2. Handles:
- Headings (H1–H6)
- Bold, italic, bold+italic inline text
- Unordered and ordered lists
- Blockquotes
- Tables (GFM pipe format)
- Fenced code blocks
- Horizontal rules
- Plain paragraphs
"""
from __future__ import annotations

import os
import re

from .base import BaseConverter, ConversionResult
from ._pdf_utils import make_pdf, set_font

_HEADING_SIZES = {1: 20, 2: 16, 3: 14, 4: 12, 5: 11, 6: 10}


class MdToPdfConverter(BaseConverter):
    FROM_EXT = ".md"
    TO_EXT = ".pdf"

    def convert(self, input_path: str, output_path: str) -> ConversionResult:
        try:
            from fpdf import FPDF  # noqa: F401 — ensure fpdf2 is installed
        except ImportError:
            raise ImportError("fpdf2 required: pip install fpdf2")

        with open(input_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()

        # Strip YAML frontmatter
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                content = parts[2].lstrip("\n")

        pdf = make_pdf()

        lines = content.splitlines()
        i = 0
        while i < len(lines):
            line = lines[i]

            # Fenced code block
            if line.startswith("```"):
                code_lines = []
                i += 1
                while i < len(lines) and not lines[i].startswith("```"):
                    code_lines.append(lines[i])
                    i += 1
                set_font(pdf, size=9)
                pdf.multi_cell(0, 5, "\n".join(code_lines), new_x="LMARGIN", new_y="NEXT")
                set_font(pdf, size=11)
                pdf.ln(2)
                i += 1
                continue

            # Horizontal rule
            if re.match(r"^(\s*[-*_]){3,}\s*$", line):
                pdf.ln(2)
                pdf.line(pdf.l_margin, pdf.get_y(), pdf.w - pdf.r_margin, pdf.get_y())
                pdf.ln(4)
                i += 1
                continue

            # Heading
            m = re.match(r"^(#{1,6})\s+(.+)$", line)
            if m:
                level = len(m.group(1))
                set_font(pdf, style="B", size=_HEADING_SIZES[level])
                pdf.multi_cell(0, 8, m.group(2).strip(), new_x="LMARGIN", new_y="NEXT")
                set_font(pdf, size=11)
                pdf.ln(2)
                i += 1
                continue

            # Table — collect consecutive table lines
            if re.match(r"^\|.+\|", line):
                table_lines = []
                while i < len(lines) and re.match(r"^\|.+\|", lines[i]):
                    table_lines.append(lines[i])
                    i += 1
                _write_table(pdf, table_lines)
                continue

            # Blockquote
            if line.startswith(">"):
                text = re.sub(r"^>\s?", "", line)
                set_font(pdf, style="I", size=11)
                pdf.multi_cell(0, 6, text, new_x="LMARGIN", new_y="NEXT")
                set_font(pdf, size=11)
                i += 1
                continue

            # Unordered list
            m = re.match(r"^(\s*)([-*+])\s+(.+)$", line)
            if m:
                indent = len(m.group(1))
                set_font(pdf, size=11)
                pdf.multi_cell(
                    0, 6,
                    " " * indent + "\u2022  " + m.group(3),
                    new_x="LMARGIN", new_y="NEXT",
                )
                i += 1
                continue

            # Ordered list
            m = re.match(r"^(\s*)(\d+)\.\s+(.+)$", line)
            if m:
                indent = len(m.group(1))
                set_font(pdf, size=11)
                pdf.multi_cell(
                    0, 6,
                    " " * indent + m.group(2) + ".  " + m.group(3),
                    new_x="LMARGIN", new_y="NEXT",
                )
                i += 1
                continue

            # Blank line
            if not line.strip():
                pdf.ln(4)
                i += 1
                continue

            # Regular paragraph — collect continuation lines
            para_lines = [line]
            i += 1
            while i < len(lines) and lines[i].strip() and not _is_block_start(lines[i]):
                para_lines.append(lines[i])
                i += 1
            paragraph = " ".join(para_lines)
            set_font(pdf, size=11)
            pdf.multi_cell(0, 6, _strip_inline(paragraph), new_x="LMARGIN", new_y="NEXT")

        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        pdf.output(output_path)

        return ConversionResult(
            output_path=output_path,
            success=True,
            message=f"Converted {os.path.basename(input_path)} → {os.path.basename(output_path)}",
        )


# ── helpers ──────────────────────────────────────────────────────────────────

def _is_block_start(line: str) -> bool:
    return bool(
        re.match(r"^#{1,6}\s", line)
        or re.match(r"^(\s*)([-*+])\s+", line)
        or re.match(r"^(\s*)\d+\.\s+", line)
        or line.startswith(">")
        or line.startswith("```")
        or re.match(r"^\|.+\|", line)
        or re.match(r"^(\s*[-*_]){3,}\s*$", line)
    )


def _strip_inline(text: str) -> str:
    text = re.sub(r"\*\*\*(.+?)\*\*\*", r"\1", text)
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"\*(.+?)\*", r"\1", text)
    text = re.sub(r"`(.+?)`", r"\1", text)
    text = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", text)
    return text


def _write_table(pdf, table_lines: list[str]) -> None:
    data_rows = [
        line for line in table_lines
        if not re.match(r"^\|[\s\-:|]+\|$", line)
    ]
    if not data_rows:
        return

    rows = []
    for line in data_rows:
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        rows.append(cells)

    col_count = max(len(r) for r in rows)
    col_w = pdf.epw / col_count

    pdf.ln(3)
    for ri, row_data in enumerate(rows):
        for ci in range(col_count):
            cell_text = row_data[ci] if ci < len(row_data) else ""
            style = "B" if ri == 0 else ""
            set_font(pdf, style=style, size=10)
            x = pdf.l_margin + ci * col_w
            pdf.set_xy(x, pdf.get_y())
            pdf.multi_cell(col_w, 7, _strip_inline(cell_text), border=1,
                           new_x="RIGHT", new_y="TOP")
        pdf.ln(7)

    set_font(pdf, size=11)
    pdf.ln(3)
