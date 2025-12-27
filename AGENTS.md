# Agent Guidelines

## Process
- Follow a tests-first approach: add or update tests before implementing code changes when feasible.
- Aim for minimal diffs and avoid introducing new dependencies unless absolutely necessary.
- Ground documentation and comments in repository sources when referencing behavior.
- Preserve existing invariants and public APIs unless explicitly instructed otherwise.

## Commands
- Test command: `pytest`
- Type check: `none`
- Lint/format: `none`
- Quick security check: `none`
- Sweep dir/shard: `tests/`
- Critical invariants: keep simulation rules consistent and avoid leaking secrets.

## Final Output
- Provide unified diffs for modified files.
- Include citations for referenced files or outputs when summarizing changes.
