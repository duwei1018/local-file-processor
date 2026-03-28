import os
from .base import BaseParser, ParsedDocument


class TextParser(BaseParser):
    SUPPORTED_EXTENSIONS = [".txt", ".text"]

    def parse(self, file_path: str) -> ParsedDocument:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            text = f.read()

        title = os.path.splitext(os.path.basename(file_path))[0]

        return ParsedDocument(
            title=title,
            text=text,
            file_path=file_path,
            file_type="txt",
        )
