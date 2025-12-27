# Agent Instructions

Scope: Entire repository.

- Follow tests-first, minimal-diff workflow; avoid new dependencies.
- Add or extend tests before implementation when feasible; include at least one property/invariant test for target behavior.
- Keep changes localized and avoid unrelated formatting.
- Cite sources in final summary as required.

Repo Commands:
- Test command: `python -m pytest`
- Type check: none
- Lint/format: none
- Quick security check: none
- Sweep dir/shard: `.`
- Critical invariants: Maintain simulation correctness; avoid blocking main thread with LLM calls; do not log secrets.
