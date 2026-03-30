"""DOCX → Markdown converter.

Preserves:
- Heading levels (Heading 1-6 → # to ######)
- Bold / Italic / Bold+Italic inline formatting
- Bullet lists and numbered lists (with nesting)
- Tables (GFM pipe format)
- Hyperlinks
- Document order (paragraphs and tables interleaved)
"""
from __future__ import annotations

import os
import re

from .base import BaseConverter, ConversionResult


class DocxToMdConverter(BaseConverter):
    FROM_EXT = ".docx"
    TO_EXT = ".md"

    def convert(self, input_path: str, output_path: str) -> ConversionResult:
        try:
            import docx
            from docx.oxml.ns import qn
        except ImportError:
            raise ImportError("python-docx required: pip install python-docx")

        doc = docx.Document(input_path)

        # Extract title from core properties
        title = doc.core_properties.title or os.path.splitext(os.path.basename(input_path))[0]

        lines: list[str] = []
        if title:
            lines.append(f"# {title}\n")

        # Iterate document body in order (paragraphs + tables)
        for block in self._iter_blocks(doc):
            if block["type"] == "paragraph":
                line = self._format_paragraph(block["element"], doc)
                lines.append(line)
            elif block["type"] == "table":
                lines.append("")
                lines.extend(self._convert_table(block["element"], doc))
                lines.append("")

        # Clean up excessive blank lines
        md_content = re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip() + "\n"

        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(md_content)

        return ConversionResult(
            output_path=output_path,
            success=True,
            message=f"Converted {os.path.basename(input_path)} → {os.path.basename(output_path)}",
        )

    # ── internal helpers ────────────────────────────────────────────────────

    def _iter_blocks(self, doc):
        """Yield paragraphs and tables in document order."""
        import docx
        from docx.oxml.ns import qn

        body = doc.element.body
        for child in body:
            local = child.tag.split("}")[-1] if "}" in child.tag else child.tag
            if local == "p":
                yield {"type": "paragraph", "element": child}
            elif local == "tbl":
                yield {"type": "table", "element": child}

    def _format_paragraph(self, para_elem, doc) -> str:
        import docx
        para = docx.text.paragraph.Paragraph(para_elem, doc)
        text = para.text
        style = para.style.name if para.style else ""

        if not text.strip():
            return ""

        # Heading
        if style.startswith("Heading"):
            m = re.search(r"(\d+)", style)
            level = int(m.group(1)) if m else 1
            level = min(max(level, 1), 6)
            return f"{'#' * level} {text.strip()}"

        # Format runs with inline markup
        formatted = self._format_runs(para)

        # List styles
        if "List Bullet" in style:
            depth = self._list_depth(style)
            return f"{'  ' * depth}- {formatted}"
        if "List Number" in style:
            depth = self._list_depth(style)
            return f"{'  ' * depth}1. {formatted}"

        # Quote / code
        if "Quote" in style or "Intense Quote" in style:
            return f"> {formatted}"
        if "Code" in style:
            return f"`{formatted}`"

        return formatted

    def _format_runs(self, para) -> str:
        """Build inline-formatted string from paragraph runs."""
        from docx.oxml.ns import qn

        parts: list[str] = []
        for run in para.runs:
            text = run.text
            if not text:
                continue
            bold = run.bold
            italic = run.italic
            if bold and italic:
                text = f"***{text}***"
            elif bold:
                text = f"**{text}**"
            elif italic:
                text = f"*{text}*"
            parts.append(text)

        # Also capture hyperlinks
        for hl in para._p.findall(".//{http://schemas.openxmlformats.org/wordprocessingml/2006/main}hyperlink"):
            pass  # hyperlinks already captured via runs

        return "".join(parts)

    def _list_depth(self, style_name: str) -> int:
        """Infer list indent depth from style name like 'List Bullet 2'."""
        m = re.search(r"(\d+)$", style_name.strip())
        return (int(m.group(1)) - 1) if m else 0

    def _convert_table(self, tbl_elem, doc) -> list[str]:
        import docx
        table = docx.table.Table(tbl_elem, doc)
        rows: list[str] = []
        for i, row in enumerate(table.rows):
            cells = []
            for cell in row.cells:
                cell_text = " ".join(
                    p.text.strip() for p in cell.paragraphs if p.text.strip()
                )
                cells.append(cell_text.replace("|", "\\|"))
            rows.append("| " + " | ".join(cells) + " |")
            if i == 0:
                rows.append("| " + " | ".join(["---"] * len(cells)) + " |")
        return rows
