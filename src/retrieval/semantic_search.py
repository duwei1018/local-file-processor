from __future__ import annotations

from typing import Any, Dict, List, Optional


class SemanticSearch:
    def __init__(self, store, embedder):
        self.store = store
        self.embedder = embedder

    def search(
        self,
        query: str,
        top_k: int = 5,
        filter_file_type: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Brute-force cosine distance search using array_distance."""
        vector = self.embedder.embed_text(query)

        where_clause = ""
        params: List[Any] = [vector, top_k]
        if filter_file_type:
            where_clause = "WHERE d.file_type = ?"
            params = [vector, filter_file_type, top_k]

        sql = f"""
            SELECT
                e.chunk_id,
                e.document_id,
                array_distance(e.vector, ?::FLOAT[1536]) AS score,
                c.text,
                d.title,
                d.file_path,
                d.file_type
            FROM embeddings e
            JOIN file_chunks c ON c.id = e.chunk_id
            JOIN documents d ON d.id = e.document_id
            {where_clause}
            ORDER BY score ASC
            LIMIT ?
        """
        try:
            return self.store.fetch_all(sql, params)
        except Exception as e:
            print(f"[search error] {e}")
            return []

    def search_with_hnsw(
        self,
        query: str,
        top_k: int = 5,
    ) -> List[Dict[str, Any]]:
        """Approximate nearest neighbor using DuckDB VSS HNSW index."""
        vector = self.embedder.embed_text(query)
        sql = """
            SELECT
                e.chunk_id,
                e.document_id,
                array_distance(e.vector, ?::FLOAT[1536]) AS score,
                c.text,
                d.title,
                d.file_path,
                d.file_type
            FROM embeddings e
            JOIN file_chunks c ON c.id = e.chunk_id
            JOIN documents d ON d.id = e.document_id
            ORDER BY score ASC
            LIMIT ?
        """
        try:
            self.store.load_vss_extension()
            return self.store.fetch_all(sql, [vector, top_k])
        except Exception as e:
            print(f"[hnsw search error] {e}, falling back to brute force")
            return self.search(query, top_k)
