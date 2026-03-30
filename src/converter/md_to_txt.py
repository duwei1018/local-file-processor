"""Markdown → plain text converter.

Strips all Markdown syntax (headings, bold/italic, links, code fences,
table pipes, blockquote markers) and writes clean plain text.
"""
from __future__ import annotations

import os
import re

from .base import BaseConverter, ConversionResult


class MdToTxtConverter(BaseConverter):
    FROM_EXT = ".md"
    TO_EXT = ".txt"

    def convert(self, input_path: str, output_path: str) -> ConversionResult:
        with open(input_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()

        # Strip YAML frontmatter
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                content = parts[2].lstrip("\n")

        text = _strip_markdown(content)

        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(text)

        return ConversionResult(
            output_path=output_path,
            success=True,
            message=f"Converted {os.path.basename(input_path)} → {os.path.basename(output_path)}",
        )


def _strip_markdown(text: str) -> str:
    # Remove fenced code blocks (keep content)
    text = re.sub(r"```[^\n]*\n(.*?)```", r"\1", text, flags=re.DOTALL)
    # Remove headings markers
    text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)
    # Remove horizontal rules
    text = re.sub(r"^(\s*[-*_]){3,}\s*$", "", text, flags=re.MULTILINE)
    # Remove blockquote markers
    text = re.sub(r"^>\s?", "", text, flags=re.MULTILINE)
    # Remove bold+italic, bold, italic
    text = re.sub(r"\*\*\*(.+?)\*\*\*", r"\1", text)
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"\*(.+?)\*", r"\1", text)
    text = re.sub(r"___(.+?)___", r"\1", text)
    text = re.sub(r"__(.+?)__", r"\1", text)
    text = re.sub(r"_(.+?)_", r"\1", text)
    # Remove inline code
    text = re.sub(r"`(.+?)`", r"\1", text)
    # Remove links but keep text
    text = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", text)
    # Remove images
    text = re.sub(r"!\[([^\]]*)\]\([^\)]+\)", r"\1", text)
    # Remove table pipe separators and alignment rows
    text = re.sub(r"^\|[\s\-:|]+\|$", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\|(.+)\|$", lambda m: " | ".join(
        c.strip() for c in m.group(1).split("|")
    ), text, flags=re.MULTILINE)
    # Remove list markers (preserve content)
    text = re.sub(r"^(\s*)([-*+])\s+", r"\1", text, flags=re.MULTILINE)
    text = re.sub(r"^(\s*)\d+\.\s+", r"\1", text, flags=re.MULTILINE)
    # Collapse excessive blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip() + "\n"
