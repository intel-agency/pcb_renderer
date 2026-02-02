from __future__ import annotations

from typing import Any, Dict, List


def filter_context(board: Dict[str, Any], errors: List[Dict[str, Any]], limit: int = 5) -> List[Dict[str, Any]]:
    """Return a bounded list of errors; placeholder for richer filtering."""

    return errors[:limit]
