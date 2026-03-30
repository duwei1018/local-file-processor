"""PDF → Markdown converter.

Extracts text from each page and wraps it with basic Markdown structure:
- Document title as H1 (from PDF metadata or filename)
- Each page as a section with a horizontal rule separator
"""
from __future__ import annotations

import os
import re

from .base import BaseConverter, ConversionResult


class PdfToMdConverter(BaseConverter):
    FROM_EXT = ".pdf"
    TO_EXT = ".md"

    def convert(self, input_path: str, output_path: str) -> ConversionResult:
        try:
            import pypdf
        except ImportError:
            raise ImportError("pypdf required: pip install pypdf")

        reader = pypdf.PdfReader(input_path)

        meta = reader.metadata or {}
        title = (
            meta.get("/Title")
            or meta.get("title")
            or os.path.splitext(os.path.basename(input_path))[0]
        )
        author = meta.get("/Author") or meta.get("author")

        lines: list[str] = [f"# {title}", ""]
        if author:
            lines += [f"*作者：{author}*", ""]

        for i, page in enumerate(reader.pages, 1):
            text = (page.extract_text() or "").strip()
            if not text:
                continue
            if len(reader.pages) > 1:
                lines += [f"## 第 {i} 页", ""]
            lines.append(text)
            lines.append("")

        md_content = re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip() + "\n"

        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(md_content)

        return ConversionResult(
            output_path=output_path,
            success=True,
            message=f"Converted {os.path.basename(input_path)} → {os.path.basename(output_path)}",
        )
