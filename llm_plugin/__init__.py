from __future__ import annotations

from argparse import ArgumentParser
from pathlib import Path
from typing import Iterable

from . import cli

__all__ = ["register_cli", "run_from_core"]


def register_cli(parser: ArgumentParser) -> None:
    """Register optional LLM flags on the core CLI parser."""

    parser.add_argument("--llm-explain", action="store_true", help="Use LLM to explain errors (requires plugin)")
    parser.add_argument("--llm-suggest-fixes", action="store_true", help="Use LLM to suggest fixes (requires plugin)")
    parser.add_argument("--llm-analyze", action="store_true", help="Use LLM to analyze design (requires plugin)")


def run_from_core(export_path: Path, modes: Iterable[str]) -> None:
    """Entry used by the core CLI to invoke plugin actions."""

    for mode in modes:
        if mode == "explain":
            cli.explain(export_path)
        elif mode == "suggest-fixes":
            cli.suggest_fixes(export_path)
        elif mode == "analyze":
            cli.analyze(export_path)
