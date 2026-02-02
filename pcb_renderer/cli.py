"""Command-line interface for pcb-renderer."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .parse import load_board
from .render import render_board
from .validate import validate_board


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="pcb-render", description="Render PCB boards from ECAD JSON files")
    parser.add_argument("input", nargs="?", type=Path, help="Input JSON board file")
    parser.add_argument("-i", "--input", dest="input_flag", type=Path, help="Input JSON board file (alias)")
    parser.add_argument("-o", "--output", required=True, type=Path, help="Output file path")
    parser.add_argument("--format", choices=["svg", "png", "pdf"], help="Output format (defaults from extension)")
    parser.add_argument("--verbose", action="store_true", default=True, help="Show progress messages (default on)")
    parser.add_argument("--quiet", action="store_true", help="Suppress success output")
    parser.add_argument("--permissive", action="store_true", help="Render even if validation errors occur")
    parser.add_argument("--export-json", dest="export_json", type=Path, help="Write normalized board + errors to JSON")
    return parser


def _print_errors(errors) -> None:
    for err in errors:
        print(str(err), file=sys.stderr)


def main(argv: list[str] | None = None) -> int:
    parser = create_parser()
    args = parser.parse_args(argv)

    input_path = args.input or args.input_flag
    if not input_path:
        parser.error("Input file is required")
    verbose = args.verbose and not args.quiet

    if verbose:
        print(f"Loading board from {input_path}...")

    board, parse_errors = load_board(Path(input_path))
    all_errors = list(parse_errors)
    if parse_errors:
        _print_errors(parse_errors)
        _maybe_export(args.export_json, board, all_errors)
        return 1
    assert board is not None

    if verbose:
        print("Validating board...")
    validation_errors = validate_board(board)
    all_errors.extend(validation_errors)
    if validation_errors and not args.permissive:
        _print_errors(validation_errors)
        _maybe_export(args.export_json, board, all_errors)
        return 1

    if verbose:
        print("Rendering board...")
    try:
        render_board(board, args.output, format=args.format)
    except Exception as exc:  # pragma: no cover
        print(f"ERROR: Rendering failed: {exc}", file=sys.stderr)
        _maybe_export(args.export_json, board, all_errors)
        return 1

    if args.export_json:
        _maybe_export(args.export_json, board, all_errors)

    if not args.quiet:
        print(f"Success: Board rendered to {args.output}")
    return 0


def _maybe_export(path: Path | None, board, errors) -> None:
    if not path:
        return
    payload = {
        "board": board.model_dump(mode="json") if board else None,
        "errors": [err.__dict__ | {"code": err.code.value, "severity": err.severity.value} for err in errors],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2))


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
