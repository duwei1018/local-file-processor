import os
import logging
from .base import BaseParser

logger = logging.getLogger(__name__)

# 优先使用 markitdown（支持 20+ 格式），失败时 fallback 到原有 parser
_PARSERS: list[BaseParser] = []

try:
    from .markitdown_parser import MarkitdownParser
    _PARSERS.append(MarkitdownParser())
    logger.info("[Parser] markitdown 已加载，支持 PDF/Word/Excel/PPT/HTML/图片等格式")
except ImportError:
    logger.warning("[Parser] markitdown 未安装，使用 fallback 解析器")

# Fallback parsers（markitdown 不可用或特定格式需要时）
from .pdf_parser import PDFParser
from .docx_parser import DocxParser
from .markdown_parser import MarkdownParser
from .text_parser import TextParser

_FALLBACK_PARSERS: list[BaseParser] = [
    PDFParser(),
    DocxParser(),
    MarkdownParser(),
    TextParser(),
]

# 如果 markitdown 没加载，用 fallback
if not _PARSERS:
    _PARSERS = _FALLBACK_PARSERS

# 合并所有支持的扩展名
SUPPORTED_EXTENSIONS: list[str] = []
for _p in _PARSERS:
    SUPPORTED_EXTENSIONS.extend(_p.SUPPORTED_EXTENSIONS)
# 确保 .md/.txt 始终支持（markitdown 不处理这些，用原生 parser）
for _p in _FALLBACK_PARSERS:
    for _ext in _p.SUPPORTED_EXTENSIONS:
        if _ext not in SUPPORTED_EXTENSIONS:
            SUPPORTED_EXTENSIONS.append(_ext)

# 构建扩展名→parser 映射
_EXT_MAP: dict[str, BaseParser] = {}
# 先注册 fallback（底层）
for _p in _FALLBACK_PARSERS:
    for _ext in _p.SUPPORTED_EXTENSIONS:
        _EXT_MAP[_ext.lower()] = _p
# markitdown 覆盖（优先级更高）
for _p in _PARSERS:
    for _ext in _p.SUPPORTED_EXTENSIONS:
        _EXT_MAP[_ext.lower()] = _p
# .md 和 .txt 始终用原生 parser（markitdown 对纯文本没有优势）
for _p in _FALLBACK_PARSERS:
    if isinstance(_p, MarkdownParser) or isinstance(_p, TextParser):
        for _ext in _p.SUPPORTED_EXTENSIONS:
            _EXT_MAP[_ext.lower()] = _p


def get_parser(file_path: str) -> BaseParser:
    ext = os.path.splitext(file_path)[1].lower()
    parser = _EXT_MAP.get(ext)
    if parser is None:
        raise ValueError(
            f"Unsupported file extension '{ext}'. "
            f"Supported: {', '.join(sorted(set(SUPPORTED_EXTENSIONS)))}"
        )
    return parser
