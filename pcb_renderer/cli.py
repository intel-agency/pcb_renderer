"""Command-line interface for pcb-renderer."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

from .parse import parse_board_data, parse_board_json, read_board_file
from .render import render_board
from .stats import compute_stats
from .validate import CHECKS_RUN, validate_board


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
    parser.add_argument("--open", dest="auto_open", action="store_true", help="Open output with system default app")
    return parser


def _print_errors(errors) -> None:
    for err in errors:
        print(str(err), file=sys.stderr)


def main(argv: list[str] | None = None) -> int:
    parser = create_parser()
    _maybe_register_plugin(parser)
    args = parser.parse_args(argv)

    input_path = args.input or args.input_flag
    if not input_path:
        parser.error("Input file is required")
    verbose = args.verbose and not args.quiet

    if verbose:
        print(f"Loading board file from {input_path}...")

    raw_text, file_errors = read_board_file(Path(input_path))
    parse_errors: List[Any] = list(file_errors)
    board = None

    if not file_errors and raw_text is not None:
        if verbose:
            print("Parsing JSON...")
        data, json_errors = parse_board_json(raw_text)
        parse_errors.extend(json_errors)

        if not json_errors and data is not None:
            if verbose:
                print("Parsing board data...")
            board, board_errors = parse_board_data(data)
            parse_errors.extend(board_errors)

    all_errors = list(parse_errors)
    parse_success = not parse_errors and board is not None

    validation_errors: List[Any] = []
    if parse_success:
        if verbose:
            print("Validating board...")
        assert board is not None
        validation_errors = validate_board(board)
        all_errors.extend(validation_errors)

    render_success = False
    render_format = args.format or args.output.suffix.lstrip(".")

    if parse_success and (not validation_errors or args.permissive):
        if verbose:
            print("Rendering board...")
        try:
            assert board is not None
            render_board(board, args.output, format=args.format)
            render_success = True
        except Exception as exc:  # pragma: no cover
            print(f"ERROR: Rendering failed: {exc}", file=sys.stderr)
    else:
        if validation_errors and not args.permissive:
            _print_errors(validation_errors)

    stats = compute_stats(board) if parse_success and board else None

    export_path = args.export_json
    llm_modes = _llm_modes(args)
    temp_export: Optional[Path] = None
    if llm_modes and not export_path:
        temp_export = Path(tempfile.NamedTemporaryFile(delete=False, suffix=".json").name)
        export_path = temp_export

    payload = _build_export_payload(
        input_path=Path(input_path),
        board=board if parse_success else None,
        parse_errors=parse_errors,
        validation_errors=validation_errors,
        render_success=render_success,
        output_path=args.output,
        output_format=render_format,
        stats=stats,
    )

    if export_path:
        _write_export(export_path, payload)

    if llm_modes:
        _invoke_llm_plugin(export_path, llm_modes, verbose)

    if args.auto_open and render_success:
        try:
            open_file(args.output)
        except Exception as exc:  # pragma: no cover
            if verbose:
                print(f"Warning: could not open output: {exc}", file=sys.stderr)

    if temp_export and temp_export.exists():
        temp_export.unlink(missing_ok=True)

    if validation_errors and not args.permissive:
        return 1
    if not parse_success:
        _print_errors(parse_errors)
        return 1
    if not render_success:
        return 1

    if not args.quiet:
        print(f"Success: Board rendered to {args.output}")
    return 0


def _write_export(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2))


def open_file(path: Path) -> None:
    """Open a file with the OS default application (best-effort, cross-platform)."""

    if sys.platform.startswith("win"):
        os.startfile(path)  # type: ignore[attr-defined]
        return
    if sys.platform == "darwin":
        subprocess.run(["open", str(path)], check=False)
        return

    opener = shutil.which("xdg-open") or shutil.which("gio")
    if opener:
        subprocess.run([opener, str(path)], check=False)
        return
    raise RuntimeError("No system opener available (xdg-open/gio not found)")


def _build_export_payload(
    *,
    input_path: Path,
    board,
    parse_errors,
    validation_errors,
    render_success: bool,
    output_path: Path,
    output_format: str,
    stats: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    def _error_to_dict(err):
        return {
            "code": err.code.value,
            "severity": err.severity.value,
            "message": err.message,
            "json_path": err.json_path,
            "context": err.context,
        }

    parse_success = not parse_errors and board is not None
    validation_success = parse_success and not validation_errors
    checks_run = CHECKS_RUN if parse_success else []

    return {
        "schema_version": "1.0",
        "input_file": str(input_path),
        "parse_result": {
            "success": parse_success,
            "errors": [_error_to_dict(e) for e in parse_errors],
            "board": board.model_dump(mode="json") if parse_success and board else None,
            "stats": stats,
        },
        "validation_result": {
            "valid": validation_success,
            "error_count": len(validation_errors),
            "warning_count": 0,
            "errors": [_error_to_dict(e) for e in validation_errors],
            "warnings": [],
            "checks_run": checks_run,
        },
        "render_result": {
            "success": render_success,
            "output_file": str(output_path),
            "format": output_format,
        },
    }


def _maybe_register_plugin(parser: argparse.ArgumentParser) -> None:
    try:
        import llm_plugin  # type: ignore

        if hasattr(llm_plugin, "register_cli"):
            llm_plugin.register_cli(parser)
    except ImportError:
        return


def _llm_modes(args) -> List[str]:
    modes: List[str] = []
    for flag, name in [
        ("llm_explain", "explain"),
        ("llm_suggest_fixes", "suggest-fixes"),
        ("llm_analyze", "analyze"),
    ]:
        if getattr(args, flag, False):
            modes.append(name)
    return modes


def _invoke_llm_plugin(export_path: Optional[Path], modes: List[str], verbose: bool) -> None:
    if not export_path:
        if verbose:
            print("LLM plugin requested but no export available", file=sys.stderr)
        return
    try:
        import llm_plugin  # type: ignore

        if hasattr(llm_plugin, "run_from_core"):
            llm_plugin.run_from_core(export_path, modes)
        else:
            if verbose:
                print("LLM plugin missing run_from_core handler", file=sys.stderr)
    except ModuleNotFoundError:
        if verbose:
            print("LLM plugin not installed; skipping LLM invocation", file=sys.stderr)
    except Exception as exc:  # pragma: no cover
        if verbose:
            import traceback

            print(f"LLM plugin invocation failed: {exc}", file=sys.stderr)
            traceback.print_exc(file=sys.stderr)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
