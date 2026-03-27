from __future__ import annotations

import time
from typing import Callable

import openai


def _make_openai_compatible_client(
    api_key: str,
    base_url: str,
    max_retries: int = 3,
    retry_delay: float = 10.0,
) -> Callable[[str, str], str]:
    """Core factory: wraps any OpenAI-compatible endpoint."""
    _oa = openai.OpenAI(api_key=api_key, base_url=base_url)

    def client(prompt: str, model: str, **kw) -> str:
        for attempt in range(max_retries):
            try:
                resp = _oa.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": prompt}],
                    **kw,
                )
                return resp.choices[0].message.content
            except openai.RateLimitError:
                if attempt < max_retries - 1:
                    time.sleep(retry_delay * (attempt + 1))
                else:
                    raise

    return client


def make_kimi_client(
    api_key: str,
    base_url: str = "https://api.moonshot.cn/v1",
    max_retries: int = 3,
    retry_delay: float = 10.0,
) -> Callable[[str, str], str]:
    """Kimi (Moonshot) API client."""
    return _make_openai_compatible_client(api_key, base_url, max_retries, retry_delay)


def make_ollama_client(
    base_url: str = "http://localhost:11434/v1",
    max_retries: int = 2,
    retry_delay: float = 3.0,
) -> Callable[[str, str], str]:
    """Ollama local model client (OpenAI-compatible endpoint).

    Usage in .env:
        LLM_BACKEND=ollama
        OLLAMA_BASE_URL=http://localhost:11434/v1
        LLM_MODEL_FAST=qwen2.5:7b
        LLM_MODEL_LARGE=qwen2.5:14b

    Model name passed to client() must match the model pulled in Ollama,
    e.g. 'qwen2.5:7b', 'llama3.2', 'mistral', etc.
    """
    return _make_openai_compatible_client("ollama", base_url, max_retries, retry_delay)


def make_client_from_env() -> Callable[[str, str], str]:
    """Auto-select backend from LLM_BACKEND env var.

    LLM_BACKEND=kimi   (default) — uses KIMI_API_KEY
    LLM_BACKEND=ollama           — uses OLLAMA_BASE_URL (default: http://localhost:11434/v1)
    """
    import os
    backend = os.environ.get("LLM_BACKEND", "kimi").lower()

    if backend == "ollama":
        base_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434/v1")
        return make_ollama_client(base_url=base_url)
    else:
        api_key = os.environ.get("KIMI_API_KEY", "")
        if not api_key:
            raise ValueError("KIMI_API_KEY not set. Set LLM_BACKEND=ollama for local models.")
        return make_kimi_client(api_key=api_key)
