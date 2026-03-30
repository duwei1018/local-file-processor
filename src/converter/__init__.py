"""Format converter registry.

Supported conversions (12 directions across 4 formats):
  pdf  ↔ md, docx, txt
  md   ↔ docx, txt
  docx ↔ txt
"""
from __future__ import annotations

from .base import BaseConverter, ConversionResult
from .pdf_to_md import PdfToMdConverter
from .pdf_to_docx import PdfToDocxConverter
from .pdf_to_txt import PdfToTxtConverter
from .md_to_docx import MdToDocxConverter
from .md_to_pdf import MdToPdfConverter
from .md_to_txt import MdToTxtConverter
from .docx_to_md import DocxToMdConverter
from .docx_to_pdf import DocxToPdfConverter
from .docx_to_txt import DocxToTxtConverter
from .txt_to_md import TxtToMdConverter
from .txt_to_docx import TxtToDocxConverter
from .txt_to_pdf import TxtToPdfConverter

_REGISTRY: list[type[BaseConverter]] = [
    PdfToMdConverter,
    PdfToDocxConverter,
    PdfToTxtConverter,
    MdToDocxConverter,
    MdToPdfConverter,
    MdToTxtConverter,
    DocxToMdConverter,
    DocxToPdfConverter,
    DocxToTxtConverter,
    TxtToMdConverter,
    TxtToDocxConverter,
    TxtToPdfConverter,
]


def get_converter(from_ext: str, to_ext: str) -> BaseConverter:
    """Return a converter instance for the given extension pair.

    Raises ValueError if no converter handles the combination.
    """
    from_ext = from_ext if from_ext.startswith(".") else f".{from_ext}"
    to_ext = to_ext if to_ext.startswith(".") else f".{to_ext}"
    for cls in _REGISTRY:
        if cls.can_handle(from_ext, to_ext):
            return cls()
    raise ValueError(
        f"No converter found for {from_ext} → {to_ext}. "
        f"Supported formats: pdf, md, docx, txt"
    )


def supported_pairs() -> list[tuple[str, str]]:
    """Return all (from_ext, to_ext) pairs that have a converter."""
    return [(cls.FROM_EXT, cls.TO_EXT) for cls in _REGISTRY]


__all__ = [
    "BaseConverter",
    "ConversionResult",
    "get_converter",
    "supported_pairs",
]
