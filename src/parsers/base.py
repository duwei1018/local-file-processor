from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ParsedDocument:
    title: str
    text: str
    file_path: str
    file_type: str
    author: Optional[str] = None
    page_count: Optional[int] = None
    frontmatter: Dict[str, Any] = field(default_factory=dict)
    headings: List[str] = field(default_factory=list)


class BaseParser:
    SUPPORTED_EXTENSIONS: List[str] = []

    def parse(self, file_path: str) -> ParsedDocument:
        raise NotImplementedError
