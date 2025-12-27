# AGENTS

## Guardrails
- Tests-first: add/extend tests before implementation when feasible; include at least one property/invariant test per behavior change.
- Minimal diffs: keep changes small and targeted; avoid drive-by formatting.
- No new dependencies unless essential and documented.
- Document grounding: cite relevant docs or file paths in summaries.
- Invariants: keep LLM calls off the main loop; use `trigger_thinking` for asynchronous reasoning; avoid blocking UI.

## Commands
- Test command: python -m pytest
- Type check: none
- Lint/format: none
- Security: none

Scope: repository root.
