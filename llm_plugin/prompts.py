from __future__ import annotations

import json
from typing import Any, Dict, List


def build_explain_prompt(errors: List[Dict[str, Any]]) -> str:
    return "Explain these PCB validation errors in plain English and suggest fixes:\n" + json.dumps(errors, indent=2)


def build_suggest_prompt(board: Dict[str, Any], errors: List[Dict[str, Any]]) -> str:
    return (
        "Provide JSON edit suggestions for these errors given the board context:\n"
        + "Board summary: "
        + json.dumps(_summarize_board(board), indent=2)
        + "\nErrors:\n"
        + json.dumps(errors, indent=2)
    )


def build_analyze_prompt(stats: Dict[str, Any]) -> str:
    return "Analyze this PCB design and provide insights:\n" + json.dumps(stats or {}, indent=2)


def _summarize_board(board: Dict[str, Any]) -> Dict[str, Any]:
    stats = board.get("stats") or {}
    return {
        "components": len((board.get("components") or {}).keys()),
        "traces": len((board.get("traces") or {}).keys()),
        "vias": len((board.get("vias") or {}).keys()),
        "stats": stats,
    }
