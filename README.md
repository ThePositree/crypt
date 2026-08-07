# crypt

Research workbench and live execution module for crypto perpetual strategies.

`crypt` is built to search for automated-trading strategies, validate them
against exact historical execution, archive useful research lines, and run the
owner-selected live strategy through the same portfolio/execution code path.

The public README is intentionally short. Detailed operating rules live in
`AGENTS.md`; deeper research and execution notes live under `docs/`.

## Current shape

- **Research:** strategy discovery, donor portfolio construction, exact
  backtests, optimizer runs, trade-filter research, and candidate archives.
- **Execution:** live OKX execution for the owner-selected strategy, including
  exchange sync, persistent state, risk-base checkpoints, Telegram reporting,
  and live/backtest reconciliation.
- **Benchmark:** `docs/strategy_benchmark.md` defines the main money target
  used to compare strategies. It is an optimization target, not a hard
  restriction on the owner. The owner may promote any strategy to production;
  agents must document the evidence, risks, and current source of truth.
- **History:** the old signal-only Telegram alert MVP is complete and now
  historical context, not the main product framing.

The active live strategy is resolved from runtime configuration, primarily
`EXECUTION_STRATEGY_CONFIG` and the loaded JSON. If documentation and runtime
configuration disagree, stop and ask the owner instead of guessing.

## Stack

- Python 3.11+
- `uv` package manager
- OKX market/execution APIs
- `pandas`, `pyarrow`, `pydantic` v2
- `APScheduler`, `aiogram`, `loguru`
- `pytest`, `ruff`, `mypy`

## Setup

```bash
uv sync --all-extras
cp .env.example .env
```

Fill `.env` with the required Telegram and OKX settings for the mode you are
running.

## Short research smoke

The owner-facing CLI defaults to `data/`, `SOL-USDT-SWAP`, full available
history, and `$10,000` starting capital. Add `--from/--to` only for bounded
smokes.

```bash
uv run backtester run \
    --from 2025-01-01 \
    --to 2025-02-01 \
    --strategy strategies/archive/filtered_donor_portfolio_post_adr0058_tail_control_v6_drop_negative_v5.json \
    --output results/smoke_v6_sol_2025_01
```

Full-history backtest:

```bash
uv run backtester run \
    --strategy strategies/archive/filtered_donor_portfolio_post_adr0058_tail_control_v6_drop_negative_v5.json \
    --output results/v6_sol_full
```

For DSS v3 candidate JSONs, `backtester run` and `backtester optimize` derive
the execution candle timeframe from the candidate trigger timeframe. Do not pass
a separate candle timeframe for those commands.

For the compact CLI runbook, see `docs/cli.md`.

## Live execution

Dry-run first:

```bash
PYTHONPATH=src \
EXECUTION_ENABLED=true \
EXECUTION_DRY_RUN=true \
EXECUTION_DRY_RUN_CAPITAL=10000 \
EXECUTION_STRATEGY_CONFIG=strategies/archive/filtered_donor_portfolio_post_adr0058_tail_control_v6_drop_negative_v5.json \
EXECUTION_SYMBOLS=SOL-USDT-SWAP \
uv run python -m crypt --once --execution-only
```

For Railway/live-money operation, use `docs/execution/live_execution.md` and
`docs/deploy/railway.md`. The repository default can differ from the active
deployment; verify the runtime environment before changing live state.

## Documentation map

- `AGENTS.md` — mandatory operating manual for agents.
- `docs/strategy_benchmark.md` — money benchmark and reporting requirements.
- `docs/backtester_regression.md` — canonical checks for backtester parity.
- `docs/execution/live_execution.md` — live execution behavior and state.
- `docs/deploy/railway.md` — Railway deployment/runbook.
- `docs/backtester/` — backtester and diagnostic contracts.
- `docs/archive/candidates/` — frozen strategy/candidate research archive.
- `docs/tasks/IN_PROGRESS.md` — only currently active work.
- `docs/tasks/BACKLOG.md` — unfinished queued work only.
- `CHANGELOG.md` — recent project history.
- `CHANGELOG_ARCHIVE.md` — older project history.

## Development

```bash
uv run ruff check .
uv run mypy src/crypt
uv run pytest tests -q
```

Do not run long research commands silently. Any command expected to take more
than roughly one minute must expose progress and ETA.
