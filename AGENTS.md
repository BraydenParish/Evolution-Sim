# Project Agent Guidelines

## Workflow
- Tests-first: add or update tests before implementation when feasible.
- Minimal diffs: keep changes small, avoid drive-by refactors or reformatting.
- No new dependencies unless essential.
- Cite references for nontrivial APIs in commit/PR context.

## Commands
- Test command: `python -m pytest`
- Type check: none
- Lint/format: none
- Quick security check: none
- Sweep dir/shard: `game.py`

## Invariants
- LLM calls must remain off the main thread (use background threads for Ollama requests).
- Preserve existing map sizing constants and screen calculations unless required for a change.
- Avoid introducing blocking network operations in the main loop.
