# PR-4 TODO Plan

## Complete PR Comment Status List (ALL PR comments)

- [ ] 2755332394 — "Guard suggest-fixes against missing parsed board" (inline review comment)
- [x] IC_kwDORGerZM7kq91Z — Gemini summary comment (general summary; no action required)
- [x] IC_kwDORGerZM7krB61 — /gemini review command comment (no action required)

## Unresolved Comments List (ONLY unresolved comments)

- [ ] 2755332394 — "Guard suggest-fixes against missing parsed board"
  - Resolution plan: short-circuit suggest-fixes when `parse_result.board` is missing/falsey and emit a friendly message instead of calling `build_suggest_prompt()`.
