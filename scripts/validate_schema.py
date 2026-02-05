from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable, List, Tuple

from jsonschema import Draft202012Validator, FormatChecker


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_DIR = ROOT / "docs" / "schema"
BOARDS_DIR = ROOT / "boards"
GENERATED_DIR = BOARDS_DIR / "generated"

PERMISSIVE_SCHEMA = SCHEMA_DIR / "ecad_schema_v1.0.0.0.json"
STRICT_SCHEMA = SCHEMA_DIR / "ecad_schema_v1.0.0.0.strict.json"


def _load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _iter_boards() -> List[Path]:
    boards = sorted(p for p in BOARDS_DIR.glob("*.json") if p.is_file())
    generated = sorted(p for p in GENERATED_DIR.glob("*.json") if p.is_file())
    return boards + generated


def _format_error(path: Path, error_path: Iterable[object], message: str) -> str:
    json_path = "$"
    for segment in error_path:
        if isinstance(segment, int):
            json_path += f"[{segment}]"
        else:
            json_path += f".{segment}"
    return f"- {path.relative_to(ROOT)}: {json_path} -> {message}"


def _validate_board(
    board_path: Path,
    validator: Draft202012Validator,
    label: str,
) -> Tuple[bool, List[str]]:
    data = _load_json(board_path)
    errors = sorted(validator.iter_errors(data), key=lambda err: err.path)
    formatted = [_format_error(board_path, err.path, err.message) for err in errors]
    if formatted:
        formatted.insert(0, f"{label} validation errors:")
    return (len(formatted) == 0), formatted


def main() -> int:
    if not PERMISSIVE_SCHEMA.exists() or not STRICT_SCHEMA.exists():
        missing = [p for p in [PERMISSIVE_SCHEMA, STRICT_SCHEMA] if not p.exists()]
        missing_list = ", ".join(str(p) for p in missing)
        print(f"Missing schema files: {missing_list}")
        return 2

    permissive = Draft202012Validator(_load_json(PERMISSIVE_SCHEMA), FormatChecker())
    strict = Draft202012Validator(_load_json(STRICT_SCHEMA), FormatChecker())

    all_boards = _iter_boards()
    if not all_boards:
        print("No boards found to validate.")
        return 1

    failures: List[str] = []

    for board_path in all_boards:
        ok, messages = _validate_board(board_path, permissive, "Permissive")
        if not ok:
            failures.extend(messages)

    generated_boards = [p for p in all_boards if p.is_relative_to(GENERATED_DIR)]
    for board_path in generated_boards:
        ok, messages = _validate_board(board_path, strict, "Strict")
        if not ok:
            failures.extend(messages)

    if failures:
        print("Schema validation failed:\n")
        print("\n".join(failures))
        return 1

    print(
        f"Schema validation passed for {len(all_boards)} boards ({len(generated_boards)} strict)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
