"""DOCX → plain text converter."""
from __future__ import annotations

import os

from .base import BaseConverter, ConversionResult


class DocxToTxtConverter(BaseConverter):
    FROM_EXT = ".docx"
    TO_EXT = ".txt"

    def convert(self, input_path: str, output_path: str) -> ConversionResult:
        try:
            import docx
        except ImportError:
            raise ImportError("python-docx required: pip install python-docx")

        doc = docx.Document(input_path)

        parts: list[str] = []
        for block in doc.element.body:
            local = block.tag.split("}")[-1] if "}" in block.tag else block.tag
            if local == "p":
                para = docx.text.paragraph.Paragraph(block, doc)
                text = para.text.strip()
                if text:
                    parts.append(text)
            elif local == "tbl":
                table = docx.table.Table(block, doc)
                for row in table.rows:
                    row_text = "\t".join(
                        " ".join(p.text.strip() for p in cell.paragraphs if p.text.strip())
                        for cell in row.cells
                    )
                    if row_text.strip():
                        parts.append(row_text)

        content = "\n\n".join(parts)

        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(content)

        return ConversionResult(
            output_path=output_path,
            success=True,
            message=f"Converted {os.path.basename(input_path)} → {os.path.basename(output_path)}",
        )
