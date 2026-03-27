from __future__ import annotations

import os
from typing import List, Optional, Tuple

from .store import DuckDBStore
from .hasher import normalize_text, fingerprint
from .cleaner import clean_text
from .chunker import Chunker
from ..parsers.registry import get_parser, SUPPORTED_EXTENSIONS


class FileIngestor:
    def __init__(self, db_path: str = "db/local_files.duckdb"):
        self.store = DuckDBStore(db_path)
        self.chunker = Chunker(max_tokens=500, overlap_tokens=50)

    def close(self) -> None:
        self.store.close()

    def ingest_file(
        self, file_path: str, force: bool = False
    ) -> Tuple[Optional[int], bool]:
        """Parse, deduplicate, and store a single file.

        Returns:
            (document_id, is_duplicate)
        """
        file_path = os.path.abspath(file_path)

        # Parse
        parser = get_parser(file_path)
        parsed = parser.parse(file_path)

        # Clean and fingerprint
        cleaned = clean_text(parsed.text, preserve_newlines=True)
        content_hash = fingerprint(normalize_text(cleaned))

        # Dedup check
        if not force:
            existing = self.store.find_document_by_hash(content_hash)
            if existing:
                self.store.insert_event(
                    existing["id"], "ingest_duplicate",
                    {"file_path": file_path, "content_hash": content_hash}
                )
                return existing["id"], True

        # Insert document
        metadata = {
            "content_hash": content_hash,
            "file_type": parsed.file_type,
            "page_count": parsed.page_count,
            "headings": parsed.headings[:10],
        }
        if parsed.frontmatter:
            metadata["frontmatter"] = parsed.frontmatter

        doc_id = self.store.insert_document(
            title=parsed.title,
            content=cleaned,
            file_path=file_path,
            file_type=parsed.file_type,
            metadata=metadata,
            source=file_path,
            author=parsed.author or "",
        )

        if doc_id is None:
            return None, False

        # Chunk and store
        chunks = self.chunker.chunk_document(parsed)
        for chunk in chunks:
            self.store.insert_chunk(
                document_id=doc_id,
                chunk_index=chunk.chunk_index,
                text=chunk.text,
                token_count=chunk.token_count,
            )

        self.store.insert_event(
            doc_id, "ingest",
            {
                "file_path": file_path,
                "file_type": parsed.file_type,
                "chunk_count": len(chunks),
                "content_hash": content_hash,
            }
        )

        return doc_id, False

    def ingest_directory(
        self,
        dir_path: str,
        recursive: bool = True,
        extensions: Optional[List[str]] = None,
        force: bool = False,
    ) -> List[Tuple[Optional[int], bool]]:
        """Ingest all supported files in a directory."""
        exts = set(e.lower() for e in (extensions or SUPPORTED_EXTENSIONS))
        results = []

        for root, dirs, files in os.walk(dir_path):
            dirs.sort()
            for fname in sorted(files):
                ext = os.path.splitext(fname)[1].lower()
                if ext in exts:
                    fpath = os.path.join(root, fname)
                    try:
                        result = self.ingest_file(fpath, force=force)
                        results.append(result)
                        status = "duplicate" if result[1] else f"doc_id={result[0]}"
                        print(f"  [ingest] {fname} → {status}")
                    except Exception as e:
                        print(f"  [error] {fname}: {e}")
                        results.append((None, False))
            if not recursive:
                break

        return results
