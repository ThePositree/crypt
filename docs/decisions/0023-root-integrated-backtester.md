# ADR-0023: Root-integrated backtester package

- **Status**: accepted
- **Date**: 2026-06-04
- **Owner**: owner (direction in chat); agent documented
- **Supersedes**: ADR-0021 item 3, which kept `backtester/` as a separate
  Python project with its own `pyproject.toml`, `uv.lock`, and test runner.
  ADR-0021 remains accepted for the git decision: `backtester` is ordinary
  source in the `crypt` repository, not a submodule or nested repository.

## Context

The donor backtester was first vendored as `backtester/`, then kept as a
separate Python project inside the `crypt` repo. That reduced git confusion
but still left day-to-day work awkward:

- agents had to switch between root and `backtester/`;
- commands needed `PYTHONPATH=src`;
- dependency and tool state was split across two `pyproject.toml` files and
  two lock files;
- the donor project still carried Hatch, donor `.cursor` rules, a local
  `.venv`, cache directories, and generated result artifacts;
- the old `src/crypt/backtest/` harness was a previous attempt to port donor
  logic into `crypt`, but M2 has since moved to the donor package per
  ADR-0018.

The owner asked to make the backtester look native in `crypt`, remove
unneeded donor tooling such as Hatch, adopt `mise` at the repository root, and
delete the old `src/crypt/backtest` attempt if it is unused.

## Decision

Make `backtester` a first-class package in the root `uv` project:

1. Move donor package code from `backtester/src/backtester/` to
   `src/backtester/`.
2. Move donor tests from `backtester/tests/` to `tests/backtester/`.
3. Move strategy JSON configs from `backtester/strategies/` to
   `strategies/backtester/`.
4. Remove the nested donor project boundary: `backtester/pyproject.toml`,
   `backtester/uv.lock`, `backtester/mise.toml`, donor `.cursor` rules,
   local `.venv`, caches, and generated `backtester/results/`.
5. Expose the donor CLI from the root project with the existing command name:
   `uv run backtester ...`.
6. Add root `mise.toml` for shared tool versions and common commands.
7. Retire `src/crypt/backtest/` and `tests/backtest/`. Usage search found only
   self-tests and stale docs/commands; no live pipeline, donor package, or CI
   entrypoint imports it.

The package import name remains `backtester`. The `crypt_ensemble` strategy
continues importing `crypt` internals directly from the same root `src/`
layout.

## Alternatives considered

- Keep `backtester/` as a separate root-level Python project — rejected. It
  preserves the command friction and split dependency graph the owner wants to
  remove.
- Merge donor code into `src/crypt/backtester/` — rejected. It would force a
  broad import rename and blur the donor package boundary more than necessary.
- Keep `src/crypt/backtest/` as archived code — rejected. It is no longer the
  canonical M2 path and stale public commands invite future agents to extend
  the wrong harness.
- Keep donor dashboards and scripts as first-class tooling — deferred. The M2
  product path currently uses CLI reports and CSV/Markdown artifacts; GUI
  scripts can be recovered from history if needed.

## Consequences

- Positive: one `uv sync`, one lock file, one CI job, and root-level commands
  cover both `crypt` and `backtester`.
- Positive: agents no longer need `cd backtester` or
  `PYTHONPATH=src:../src`.
- Positive: stale Hatch/versioningit/mise-in-subdir state is gone.
- Positive: the obsolete root-native backtest harness cannot accidentally
  receive new M2 work.
- Negative: upstream donor cherry-picks become more manual because file paths
  now differ from the historical upstream project.
- Negative: root dependency set grows to include the donor CLI/optimizer
  stack.
- Revisit: if Streamlit dashboards become useful again, add them back as an
  explicit optional extra with current docs and tests.

## References

- ADR-0018: Donor backtester becomes the canonical M2 backtest architecture
- ADR-0021: Vend `backtester/` into the `crypt` monorepo
- `docs/backtester_migration.md`
- Context7: `/astral-sh/uv` project dependency groups and scripts
- Context7: `/jdx/mise` tools and task configuration
