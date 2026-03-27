from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional

import duckdb


class DuckDBStore:
    def __init__(self, db_path: str = "db/local_files.duckdb"):
        os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
        self.db_path = db_path
        self.conn = duckdb.connect(db_path)

    def close(self) -> None:
        self.conn.close()

    def create_tables(self, sql_file: str = "db/init.sql") -> None:
        with open(sql_file, "r", encoding="utf-8") as f:
            sql = f.read()
        for stmt in sql.split(";"):
            stmt = stmt.strip()
            if stmt:
                try:
                    self.conn.execute(stmt)
                except Exception as e:
                    if "already exists" not in str(e).lower():
                        raise

    def load_vss_extension(self) -> None:
        try:
            self.conn.execute("INSTALL vss")
            self.conn.execute("LOAD vss")
        except Exception as e:
            print(f"[warn] VSS extension not available: {e}")

    def build_hnsw_index(self) -> None:
        try:
            self.conn.execute("DROP INDEX IF EXISTS embeddings_hnsw")
            self.conn.execute(
                "CREATE INDEX embeddings_hnsw ON embeddings USING HNSW (vector)"
            )
            print("[info] HNSW index created on embeddings.vector")
        except Exception as e:
            print(f"[warn] Could not build HNSW index: {e}")

    # ── document operations ──────────────────────────────────────────────────

    def insert_document(
        self,
        title: str,
        content: str,
        file_path: str = "",
        file_type: str = "",
        metadata: Optional[Dict] = None,
        source: str = "",
        author: str = "",
    ) -> Optional[int]:
        meta_str = json.dumps(metadata or {}, ensure_ascii=False)
        result = self.conn.execute(
            """
            INSERT INTO documents (title, content, file_path, file_type, metadata, source, author)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            RETURNING id
            """,
            [title, content, file_path, file_type, meta_str, source, author],
        ).fetchone()
        return result[0] if result else None

    def update_document_summary(self, document_id: int, summary: str) -> None:
        self.conn.execute(
            "UPDATE documents SET summary = ?, updated_at = now() WHERE id = ?",
            [summary, document_id],
        )

    def update_document_tags(self, document_id: int, tags: List[str]) -> None:
        self.conn.execute(
            "UPDATE documents SET tags = ?, updated_at = now() WHERE id = ?",
            [json.dumps(tags, ensure_ascii=False), document_id],
        )

    def find_document_by_hash(self, content_hash: str) -> Optional[Dict]:
        row = self.conn.execute(
            """
            SELECT id, title, file_path, file_type, created_at
            FROM documents
            WHERE json_extract_string(metadata, '$.content_hash') = ?
            LIMIT 1
            """,
            [content_hash],
        ).fetchone()
        if row is None:
            return None
        cols = ["id", "title", "file_path", "file_type", "created_at"]
        return dict(zip(cols, row))

    def list_documents(self, limit: int = 50) -> List[Dict]:
        return self.fetch_all(
            "SELECT * FROM documents ORDER BY created_at DESC LIMIT ?", [limit]
        )

    def get_document(self, document_id: int) -> Optional[Dict]:
        return self.fetch_one("SELECT * FROM documents WHERE id = ?", [document_id])

    def get_unprocessed_documents(self, limit: int = 20) -> List[Dict]:
        return self.fetch_all(
            """
            SELECT d.*
            FROM documents d
            LEFT JOIN events e ON e.document_id = d.id AND e.type = 'classify'
            WHERE e.id IS NULL
            ORDER BY d.created_at ASC
            LIMIT ?
            """,
            [limit],
        )

    # ── chunk operations ─────────────────────────────────────────────────────

    def insert_chunk(
        self,
        document_id: int,
        chunk_index: int,
        text: str,
        token_count: int = 0,
        metadata: Optional[Dict] = None,
    ) -> Optional[int]:
        meta_str = json.dumps(metadata or {}, ensure_ascii=False)
        result = self.conn.execute(
            """
            INSERT INTO file_chunks (document_id, chunk_index, text, token_count, metadata)
            VALUES (?, ?, ?, ?, ?)
            RETURNING id
            """,
            [document_id, chunk_index, text, token_count, meta_str],
        ).fetchone()
        return result[0] if result else None

    def get_chunks_for_document(self, document_id: int) -> List[Dict]:
        return self.fetch_all(
            "SELECT * FROM file_chunks WHERE document_id = ? ORDER BY chunk_index",
            [document_id],
        )

    def get_unembedded_chunks(self, limit: int = 100) -> List[Dict]:
        return self.fetch_all(
            """
            SELECT c.*
            FROM file_chunks c
            LEFT JOIN embeddings e ON e.chunk_id = c.id
            WHERE e.id IS NULL
            ORDER BY c.document_id, c.chunk_index
            LIMIT ?
            """,
            [limit],
        )

    # ── embedding operations ─────────────────────────────────────────────────

    def insert_embedding(
        self,
        chunk_id: int,
        document_id: int,
        vector: List[float],
        model: str = "moonshot-v1-embedding",
    ) -> Optional[int]:
        result = self.conn.execute(
            """
            INSERT INTO embeddings (chunk_id, document_id, model, vector)
            VALUES (?, ?, ?, ?)
            RETURNING id
            """,
            [chunk_id, document_id, model, vector],
        ).fetchone()
        return result[0] if result else None

    # ── event operations ──────────────────────────────────────────────────────

    def insert_event(
        self,
        document_id: int,
        event_type: str,
        payload: Optional[Dict] = None,
    ) -> Optional[int]:
        payload_str = json.dumps(payload or {}, ensure_ascii=False)
        result = self.conn.execute(
            """
            INSERT INTO events (document_id, type, payload)
            VALUES (?, ?, ?)
            RETURNING id
            """,
            [document_id, event_type, payload_str],
        ).fetchone()
        return result[0] if result else None

    # ── generic query helpers ─────────────────────────────────────────────────

    def fetch_all(self, sql: str, params: Optional[List] = None) -> List[Dict]:
        cur = self.conn.execute(sql, params or [])
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]

    def fetch_one(self, sql: str, params: Optional[List] = None) -> Optional[Dict]:
        cur = self.conn.execute(sql, params or [])
        row = cur.fetchone()
        if row is None:
            return None
        cols = [d[0] for d in cur.description]
        return dict(zip(cols, row))
