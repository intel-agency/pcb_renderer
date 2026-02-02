# PR-4 TODO Plan

## Complete PR Comment Status List (ALL PR comments)

- [x] 2755332394 — "Guard suggest-fixes against missing parsed board" (inline review comment)
- [x] 2755332396 — "Mark validation as not run when parse fails" (inline review comment)
- [x] 2755338306 — "Avoid broad except in _maybe_register_plugin" (inline review comment)
- [x] 2755338316 — "Improve exception handling in _invoke_llm_plugin" (inline review comment)
- [x] 2755338323 — "Docs: update validate.py table to 18 rules" (inline review comment)
- [x] 2755338328 — "Remove basedpyright ignore in test_models" (inline review comment)
- [x] 2755350890 — "Dependencies: move basedpyright/typer to extras" (inline review comment)
- [x] 2755350897 — "Docs: 14 vs 18 validation rules" (inline review comment)
- [x] 2755350899 — "Avoid broad except in _maybe_register_plugin" (inline review comment)
- [x] IC_kwDORGerZM7kq91Z — Gemini summary comment (general summary; no action required)
- [x] IC_kwDORGerZM7krB61 — /gemini review command comment (no action required)

## Unresolved Comments List (ONLY unresolved comments)

- [x] 2755332394 — "Guard suggest-fixes against missing parsed board"
  - Resolution plan: short-circuit suggest-fixes when `parse_result.board` is missing/falsey and emit a friendly message instead of calling `build_suggest_prompt()`.
- [x] 2755332396 — "Mark validation as not run when parse fails"
  - Resolution plan: set `validation_result.valid` to `parse_success and not validation_errors` and clear `checks_run` when parsing fails.
- [x] 2755338306 — "Avoid broad except in _maybe_register_plugin"
  - Resolution plan: catch `ImportError`/`ModuleNotFoundError` only; let unexpected errors surface.
- [x] 2755338316 — "Improve exception handling in _invoke_llm_plugin"
  - Resolution plan: keep ModuleNotFoundError path, add traceback logging for unexpected exceptions when verbose.
- [x] 2755338323 — "Docs: update validate.py table to 18 rules"
  - Resolution plan: update AGENTS.md table to match 18 validation rules.
- [x] 2755338328 — "Remove basedpyright ignore in test_models"
  - Resolution plan: use `Board.model_validate` with dict input to avoid ignore.
- [x] 2755350890 — "Dependencies: move basedpyright/typer to extras"
  - Resolution plan: remove from core deps; move basedpyright to dev extra; keep typer in llm extra; update lockfile.
- [x] 2755350897 — "Docs: 14 vs 18 validation rules"
  - Resolution plan: same as 2755338323 (update AGENTS.md table).
- [x] 2755350899 — "Avoid broad except in _maybe_register_plugin"
  - Resolution plan: same as 2755338306 (narrow exception handling).
