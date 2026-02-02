from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict

import typer

from .client import get_client
from .context import filter_context
from .prompts import build_analyze_prompt, build_explain_prompt, build_suggest_prompt

app = typer.Typer(add_completion=False)


def _load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text())


def _ensure_backend():
    backend = os.getenv("LLM_BACKEND", "template").lower()
    return backend


def _emit(text: str) -> None:
    typer.echo(text)


@app.command()
def explain(json_file: Path) -> None:
    """Explain validation errors using the configured LLM backend."""

    data = _load_json(json_file)
    errors = data.get("validation_result", {}).get("errors", [])
    backend = _ensure_backend()
    client = get_client(backend)
    prompt = build_explain_prompt(errors)
    response = client(prompt)
    _emit(response)


@app.command("suggest-fixes")
def suggest_fixes(json_file: Path) -> None:
    """Suggest fixes for validation errors."""

    data = _load_json(json_file)
    errors = data.get("validation_result", {}).get("errors", [])
    board = data.get("parse_result", {}).get("board", {})
    backend = _ensure_backend()
    client = get_client(backend)
    filtered = filter_context(board, errors)
    prompt = build_suggest_prompt(board, filtered)
    response = client(prompt)
    _emit(response)


@app.command()
def analyze(json_file: Path) -> None:
    """Provide design insights from board stats."""

    data = _load_json(json_file)
    stats = data.get("parse_result", {}).get("stats", {}) or {}
    backend = _ensure_backend()
    client = get_client(backend)
    prompt = build_analyze_prompt(stats)
    response = client(prompt)
    _emit(response)


def main():  # pragma: no cover - Typer entry
    app()
