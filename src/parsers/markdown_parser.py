import os
import re
from .base import BaseParser, ParsedDocument


class MarkdownParser(BaseParser):
    SUPPORTED_EXTENSIONS = [".md", ".markdown"]

    def parse(self, file_path: str) -> ParsedDocument:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            raw = f.read()

        frontmatter = {}
        body = raw

        # Try python-frontmatter first
        try:
            import frontmatter as fm
            post = fm.loads(raw)
            frontmatter = dict(post.metadata)
            body = post.content
        except ImportError:
            # Fallback: manual YAML frontmatter parsing
            if raw.startswith("---"):
                parts = raw.split("---", 2)
                if len(parts) >= 3:
                    try:
                        import yaml
                        frontmatter = yaml.safe_load(parts[1]) or {}
                    except Exception:
                        frontmatter = {}
                    body = parts[2]

        # Extract title: frontmatter > first # heading > filename
        title = (
            frontmatter.get("title")
            or self._first_heading(body)
            or os.path.splitext(os.path.basename(file_path))[0]
        )
        author = frontmatter.get("author") or frontmatter.get("authors")
        if isinstance(author, list):
            author = ", ".join(author)

        headings = re.findall(r"^#{1,6}\s+(.+)$", body, re.MULTILINE)

        return ParsedDocument(
            title=str(title),
            text=body,
            file_path=file_path,
            file_type="md",
            author=str(author) if author else None,
            frontmatter=frontmatter,
            headings=headings,
        )

    @staticmethod
    def _first_heading(text: str) -> str:
        m = re.search(r"^#{1,6}\s+(.+)$", text, re.MULTILINE)
        return m.group(1).strip() if m else ""
