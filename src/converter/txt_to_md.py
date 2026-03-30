"""Plain text → Markdown converter.

Applies heuristic detection:
- First non-blank line becomes the H1 title
- Subsequent lines are treated as paragraphs (blank lines = paragraph break)
"""
from __future__ import annotations

import os
import re

from .base import BaseConverter, ConversionResult


class TxtToMdConverter(BaseConverter):
    FROM_EXT = ".txt"
    TO_EXT = ".md"

    def convert(self, input_path: str, output_path: str) -> ConversionResult:
        with open(input_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()

        lines = content.splitlines()
        md_lines: list[str] = []

        # Use filename as title if first line looks like a title (short, no period)
        title_used = False
        for i, line in enumerate(lines):
            stripped = line.strip()
            if not stripped:
                md_lines.append("")
                continue
            if not title_used and len(stripped) < 80 and not stripped.endswith("."):
                md_lines.append(f"# {stripped}")
                title_used = True
            else:
                md_lines.append(stripped)

        md_content = re.sub(r"\n{3,}", "\n\n", "\n".join(md_lines)).strip() + "\n"

        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(md_content)

        return ConversionResult(
            output_path=output_path,
            success=True,
            message=f"Converted {os.path.basename(input_path)} → {os.path.basename(output_path)}",
        )
