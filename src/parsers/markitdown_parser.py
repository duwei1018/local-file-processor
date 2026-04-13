# src/parsers/markitdown_parser.py — 基于 markitdown 的统一文档解析器
#
# 使用微软 markitdown 库，一个 parser 支持所有格式：
#   PDF, Word, Excel, PowerPoint, HTML, 图片(OCR), 音频(转写),
#   CSV, JSON, XML, ZIP 等
#
# 替代原有的 PDFParser + DocxParser，同时扩展支持更多格式。

import os
import re
from .base import BaseParser, ParsedDocument


class MarkitdownParser(BaseParser):
    """基于 markitdown 的统一文档解析器，支持 20+ 种格式。"""

    SUPPORTED_EXTENSIONS = [
        # 文档
        ".pdf", ".docx", ".doc",
        # 表格
        ".xlsx", ".xls", ".csv",
        # 演示
        ".pptx", ".ppt",
        # 网页
        ".html", ".htm",
        # 图片 (OCR)
        ".jpg", ".jpeg", ".png", ".bmp", ".gif", ".tiff",
        # 数据
        ".json", ".xml",
        # 压缩包
        ".zip",
        # 音频 (转写)
        ".mp3", ".wav", ".m4a",
        # 其他
        ".ipynb",  # Jupyter notebook
    ]

    def __init__(self):
        self._md = None

    def _get_converter(self):
        if self._md is None:
            from markitdown import MarkItDown
            self._md = MarkItDown()
        return self._md

    def parse(self, file_path: str) -> ParsedDocument:
        md = self._get_converter()
        result = md.convert(file_path)
        text = result.text_content or ""

        # 提取标题
        ext = os.path.splitext(file_path)[1].lower()
        title = self._extract_title(text, file_path)

        # 提取标题层级
        headings = re.findall(r"^#{1,6}\s+(.+)$", text, re.MULTILINE)

        # 推断文件类型
        file_type = self._ext_to_type(ext)

        # PDF 页数
        page_count = None
        if ext == ".pdf":
            page_count = self._count_pdf_pages(file_path)

        return ParsedDocument(
            title=title,
            text=text,
            file_path=file_path,
            file_type=file_type,
            page_count=page_count,
            headings=headings,
        )

    @staticmethod
    def _extract_title(text: str, file_path: str) -> str:
        """从 markdown 文本中提取标题，fallback 用文件名。"""
        # 尝试 # 标题
        m = re.search(r"^#\s+(.+)$", text, re.MULTILINE)
        if m:
            return m.group(1).strip()
        # 尝试前几行非空文本
        for line in text.split("\n")[:5]:
            line = line.strip()
            if len(line) > 5 and not line.startswith("|") and not line.startswith("-"):
                return line[:100]
        return os.path.splitext(os.path.basename(file_path))[0]

    @staticmethod
    def _ext_to_type(ext: str) -> str:
        type_map = {
            ".pdf": "pdf", ".docx": "docx", ".doc": "doc",
            ".xlsx": "xlsx", ".xls": "xls", ".csv": "csv",
            ".pptx": "pptx", ".ppt": "ppt",
            ".html": "html", ".htm": "html",
            ".jpg": "image", ".jpeg": "image", ".png": "image",
            ".bmp": "image", ".gif": "image", ".tiff": "image",
            ".json": "json", ".xml": "xml", ".zip": "zip",
            ".mp3": "audio", ".wav": "audio", ".m4a": "audio",
            ".ipynb": "notebook",
        }
        return type_map.get(ext, "unknown")

    @staticmethod
    def _count_pdf_pages(file_path: str) -> int | None:
        try:
            import pypdf
            return len(pypdf.PdfReader(file_path).pages)
        except Exception:
            return None
