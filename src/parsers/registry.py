import os
from .base import BaseParser
from .pdf_parser import PDFParser
from .docx_parser import DocxParser
from .markdown_parser import MarkdownParser
from .text_parser import TextParser

_PARSERS: list[BaseParser] = [
    PDFParser(),
    DocxParser(),
    MarkdownParser(),
    TextParser(),
]

SUPPORTED_EXTENSIONS: list[str] = []
for _p in _PARSERS:
    SUPPORTED_EXTENSIONS.extend(_p.SUPPORTED_EXTENSIONS)

_EXT_MAP: dict[str, BaseParser] = {}
for _p in _PARSERS:
    for _ext in _p.SUPPORTED_EXTENSIONS:
        _EXT_MAP[_ext.lower()] = _p


def get_parser(file_path: str) -> BaseParser:
    ext = os.path.splitext(file_path)[1].lower()
    parser = _EXT_MAP.get(ext)
    if parser is None:
        raise ValueError(
            f"Unsupported file extension '{ext}'. "
            f"Supported: {', '.join(SUPPORTED_EXTENSIONS)}"
        )
    return parser
