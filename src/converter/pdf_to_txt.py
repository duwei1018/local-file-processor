"""PDF → plain text converter."""
from __future__ import annotations

import os

from .base import BaseConverter, ConversionResult


class PdfToTxtConverter(BaseConverter):
    FROM_EXT = ".pdf"
    TO_EXT = ".txt"

    def convert(self, input_path: str, output_path: str) -> ConversionResult:
        try:
            import pypdf
        except ImportError:
            raise ImportError("pypdf required: pip install pypdf")

        reader = pypdf.PdfReader(input_path)
        pages = []
        for page in reader.pages:
            text = page.extract_text() or ""
            if text.strip():
                pages.append(text)

        content = "\n\n".join(pages)

        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(content)

        return ConversionResult(
            output_path=output_path,
            success=True,
            message=f"Converted {os.path.basename(input_path)} → {os.path.basename(output_path)}",
        )
