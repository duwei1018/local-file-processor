from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class TextChunk:
    text: str
    chunk_index: int
    token_count: int
    metadata: dict = field(default_factory=dict)


class Chunker:
    def __init__(self, max_tokens: int = 500, overlap_tokens: int = 50):
        self.max_tokens = max_tokens
        self.overlap_tokens = overlap_tokens

    def estimate_tokens(self, text: str) -> int:
        # Heuristic: CJK chars ≈ 1 token each, other words ≈ 1.3 tokens
        cjk = len(re.findall(r"[\u4e00-\u9fff\u3040-\u30ff\uac00-\ud7af]", text))
        words = len(text.split())
        return int(cjk + (words - cjk) * 1.3)

    def chunk_text(self, text: str, metadata: Optional[dict] = None) -> List[TextChunk]:
        if not text or not text.strip():
            return []

        metadata = metadata or {}
        paragraphs = [p.strip() for p in re.split(r"\n{2,}", text) if p.strip()]

        chunks: List[TextChunk] = []
        current_parts: List[str] = []
        current_tokens = 0

        for para in paragraphs:
            para_tokens = self.estimate_tokens(para)

            if para_tokens > self.max_tokens:
                # Flush current buffer first
                if current_parts:
                    chunks.append(self._make_chunk(
                        "\n\n".join(current_parts), len(chunks), current_tokens, metadata
                    ))
                    current_parts, current_tokens = [], 0

                # Split the oversized paragraph by sentences
                for sub in self._split_sentences(para):
                    sub_tokens = self.estimate_tokens(sub)
                    if current_tokens + sub_tokens > self.max_tokens and current_parts:
                        chunks.append(self._make_chunk(
                            "\n\n".join(current_parts), len(chunks), current_tokens, metadata
                        ))
                        # carry overlap
                        overlap_text = self._tail_tokens(current_parts, self.overlap_tokens)
                        current_parts = [overlap_text] if overlap_text else []
                        current_tokens = self.estimate_tokens(overlap_text) if overlap_text else 0
                    current_parts.append(sub)
                    current_tokens += sub_tokens
            else:
                if current_tokens + para_tokens > self.max_tokens and current_parts:
                    chunks.append(self._make_chunk(
                        "\n\n".join(current_parts), len(chunks), current_tokens, metadata
                    ))
                    overlap_text = self._tail_tokens(current_parts, self.overlap_tokens)
                    current_parts = [overlap_text] if overlap_text else []
                    current_tokens = self.estimate_tokens(overlap_text) if overlap_text else 0
                current_parts.append(para)
                current_tokens += para_tokens

        if current_parts:
            chunks.append(self._make_chunk(
                "\n\n".join(current_parts), len(chunks), current_tokens, metadata
            ))

        return chunks

    def chunk_document(self, parsed_doc) -> List[TextChunk]:
        return self.chunk_text(parsed_doc.text)

    @staticmethod
    def _make_chunk(text: str, idx: int, tokens: int, metadata: dict) -> TextChunk:
        return TextChunk(text=text, chunk_index=idx, token_count=tokens, metadata=metadata)

    @staticmethod
    def _split_sentences(text: str) -> List[str]:
        parts = re.split(r"(?<=[.!?。！？])\s+", text)
        return [p.strip() for p in parts if p.strip()]

    def _tail_tokens(self, parts: List[str], n_tokens: int) -> str:
        joined = "\n\n".join(parts)
        words = joined.split()
        tail_words = words[-n_tokens:]
        return " ".join(tail_words)
