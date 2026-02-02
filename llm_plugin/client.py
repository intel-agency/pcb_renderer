from __future__ import annotations

import os
from typing import Callable


def get_client(backend: str = "template") -> Callable[[str], str]:
    backend = backend.lower()

    if backend == "template":
        return _template_client
    if backend == "local":
        return _local_stub
    if backend in {"http", "openai"}:
        return _http_client
    # fallback
    return _template_client


def _template_client(prompt: str) -> str:
    return f"[LLM TEMPLATE]\n{prompt}"


def _local_stub(prompt: str) -> str:
    return f"[LOCAL STUB]\n{prompt}"


def _http_client(prompt: str) -> str:
    api_key = os.getenv("OPENAI_API_KEY") or os.getenv("PCB_RENDERER_LLM_API_KEY")
    base_url = os.getenv("OPENAI_BASE_URL") or os.getenv("LLM_API_BASE") or os.getenv("PCB_RENDERER_LLM_BASE_URL")
    try:
        from openai import OpenAI
    except ImportError:  # pragma: no cover
        return "[ERROR] openai package not installed; falling back to template"

    if not api_key:
        return "[ERROR] OPENAI_API_KEY (or PCB_RENDERER_LLM_API_KEY) not set; cannot call HTTP backend"

    client = OpenAI(api_key=api_key, base_url=base_url)
    try:
        completion = client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            messages=[{"role": "user", "content": prompt}],
        )
        return completion.choices[0].message.content or ""
    except Exception as exc:  # pragma: no cover
        return f"[ERROR] LLM request failed: {exc}"
