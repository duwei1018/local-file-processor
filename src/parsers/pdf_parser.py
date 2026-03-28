import os
from .base import BaseParser, ParsedDocument


class PDFParser(BaseParser):
    SUPPORTED_EXTENSIONS = [".pdf"]

    def parse(self, file_path: str) -> ParsedDocument:
        try:
            import pypdf
        except ImportError:
            raise ImportError("pypdf is required for PDF parsing: pip install pypdf")

        reader = pypdf.PdfReader(file_path)
        pages = []
        for page in reader.pages:
            text = page.extract_text() or ""
            pages.append(text)

        full_text = "\n\n".join(p for p in pages if p.strip())

        meta = reader.metadata or {}
        title = (
            meta.get("/Title")
            or meta.get("title")
            or os.path.splitext(os.path.basename(file_path))[0]
        )
        author = meta.get("/Author") or meta.get("author")

        return ParsedDocument(
            title=str(title),
            text=full_text,
            file_path=file_path,
            file_type="pdf",
            author=str(author) if author else None,
            page_count=len(reader.pages),
        )
