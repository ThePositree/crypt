# Archived strategy candidates

This directory stores frozen research packages for strategies and portfolios
that are worth preserving. It is not the source of truth for the active live
strategy.

The active live strategy is resolved from runtime configuration, primarily
`EXECUTION_STRATEGY_CONFIG` and the JSON loaded by the executor. If runtime
configuration and documentation disagree, stop and ask the owner.

## How to read an archive package

Start with the package `README.md`, then inspect only the linked artifacts that
matter for the current task.

Useful files inside a candidate package:

- `README.md` — compact verdict, why the package was kept, why it was not
  enough or why it was superseded.
- `mandate_snapshot.md` / benchmark snapshot — historical benchmark report at
  archive time.
- `monthly_mandate.csv` — monthly return/drawdown rows when copied.
- `execution_params.json` — frozen execution knobs used for the archived run.
- `provenance.json` — source strategy path and local `results/` artifact paths.
- copied strategy JSONs or backtest snapshots when the archive package needs
  full reproducibility.

Archived packages can be useful even when they fail the benchmark: they may be
research seeds, regime examples, negative examples, or owner-selected
production lineages.

## Current important package

`post_adr0058_tail_control_portfolio/` is the main recent production/research
lineage. It contains v1-v7 portfolio history, copied configs, backtest
snapshots, attribution, and live replay notes.

Read it before drawing conclusions from older Core4/v6/v7 artifacts.

## Rules

- Do not delete archived strategy JSONs from git.
- Do not treat archive presence as production status.
- Do not rerun expensive Optuna on archived packages unless the owner revives a
  branch or the task explicitly requires it.
- Prefer the package README and provenance over reconstructing history from
  old task files.

## Related docs

- `docs/backtester/candidate_archive.md`
- `docs/strategy_benchmark.md`
- `docs/tasks/IN_PROGRESS.md`
- `docs/tasks/BACKLOG.md`
