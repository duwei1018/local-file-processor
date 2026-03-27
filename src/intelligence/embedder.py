from __future__ import annotations

import time
from typing import List

import openai


class Embedder:
    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.moonshot.cn/v1",
        model: str = "moonshot-v1-embedding",
    ):
        self._client = openai.OpenAI(api_key=api_key, base_url=base_url)
        self.model = model
        self.dimension = 1536
        self._max_chars = 8000

    def embed_text(self, text: str) -> List[float]:
        text = text[: self._max_chars]
        resp = self._client.embeddings.create(model=self.model, input=text)
        return resp.data[0].embedding

    def embed_batch(
        self, texts: List[str], batch_size: int = 16
    ) -> List[List[float]]:
        results: List[List[float]] = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            for text in batch:
                results.append(self.embed_text(text))
            if i + batch_size < len(texts):
                time.sleep(1)
        return results
