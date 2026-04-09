import json
import os
import re
import shutil
import tempfile
from .base import BaseParser, ParsedDocument


def _ensure_java_on_path() -> bool:
    """Ensure Java is on PATH; add common Windows install dirs if needed."""
    if shutil.which("java"):
        return True
    # Common Windows JDK locations
    for base in [
        os.path.join(os.environ.get("ProgramFiles", ""), "Microsoft"),
        os.path.join(os.environ.get("ProgramFiles", ""), "Eclipse Adoptium"),
        os.path.join(os.environ.get("ProgramFiles", ""), "Java"),
    ]:
        if not os.path.isdir(base):
            continue
        for entry in os.listdir(base):
            java_bin = os.path.join(base, entry, "bin")
            if os.path.isfile(os.path.join(java_bin, "java.exe")):
                os.environ["PATH"] = java_bin + os.pathsep + os.environ["PATH"]
                return True
    return False


def _opendataloader_available() -> bool:
    """Check if opendataloader-pdf is installed and Java is available."""
    try:
        import opendataloader_pdf  # noqa: F401
        return _ensure_java_on_path()
    except ImportError:
        return False


class PDFParser(BaseParser):
    SUPPORTED_EXTENSIONS = [".pdf"]

    def __init__(self):
        self._use_opendataloader = _opendataloader_available()

    def parse(self, file_path: str) -> ParsedDocument:
        if self._use_opendataloader:
            return self._parse_opendataloader(file_path)
        return self._parse_pypdf(file_path)

    # ── OpenDataLoader (structured, AI-ready) ────────────────────────────

    def _parse_opendataloader(self, file_path: str) -> ParsedDocument:
        import opendataloader_pdf

        tmp_dir = tempfile.mkdtemp(prefix="odl_")
        try:
            opendataloader_pdf.convert(
                input_path=file_path,
                output_dir=tmp_dir,
                format="markdown,json",
            )

            stem = os.path.splitext(os.path.basename(file_path))[0]

            # Read markdown output
            md_path = os.path.join(tmp_dir, f"{stem}.md")
            full_text = ""
            if os.path.exists(md_path):
                with open(md_path, "r", encoding="utf-8") as f:
                    full_text = f.read()

            # Read JSON for metadata
            json_path = os.path.join(tmp_dir, f"{stem}.json")
            title = stem
            author = None
            page_count = None
            headings = []

            if os.path.exists(json_path):
                with open(json_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                title = data.get("title") or stem
                author = data.get("author")
                page_count = data.get("number of pages")

            # Extract headings from markdown
            headings = re.findall(r"^#{1,6}\s+(.+)$", full_text, re.MULTILINE)

            if page_count is None and full_text:
                # Rough estimate from pypdf as fallback
                try:
                    import pypdf
                    page_count = len(pypdf.PdfReader(file_path).pages)
                except Exception:
                    pass

            return ParsedDocument(
                title=str(title),
                text=full_text,
                file_path=file_path,
                file_type="pdf",
                author=str(author) if author else None,
                page_count=page_count,
                headings=headings,
            )
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

    # ── pypdf fallback (plain text) ──────────────────────────────────────

    def _parse_pypdf(self, file_path: str) -> ParsedDocument:
        try:
            import pypdf
        except ImportError:
            raise ImportError(
                "No PDF parser available. Install opendataloader-pdf (recommended) "
                "or pypdf: pip install opendataloader-pdf pypdf"
            )

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
