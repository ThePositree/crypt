# Backtester migration

This document is the current implementation handoff for ADR-0018 and
ADR-0023. The donor `backtester` is the canonical M2 backtest architecture,
but it is now integrated into the root `crypt` Python project.

## Repository layout

| Layer | Location | Notes |
|-------|----------|-------|
| Git | repository root | One history; no nested repo and no submodule |
| Python package | `src/backtester/` | Import name remains `backtester` |
| Strategy configs | `strategies/backtester/` | JSON files used by donor CLI |
| Tests | `tests/backtester/` | Run from repository root |
| Tooling | `pyproject.toml`, `uv.lock` | Canonical root Python environment |
| Convenience tasks | `mise.toml` | Optional wrappers around `uv` commands |
| Ensemble code | `src/crypt/` | Imported by `crypt_ensemble` strategy |

Removed donor-only state:

- `backtester/pyproject.toml`
- `backtester/uv.lock`
- `backtester/mise.toml`
- donor `.cursor` rules
- donor local `.venv`
- donor cache directories
- donor generated `results/`
- donor dashboard/scripts/gui files

Historical upstream remains `https://github.com/AuriumX/backtester`.
Provenance comments that mention that repo remain historical markers, not an
instruction to develop against a second repository.

## Goal

The backtester package owns M2 execution simulation and calibration:

1. Load existing project Parquet data.
2. Run the current ensemble as one strategy named `crypt_ensemble`.
3. Produce trade setups with `signal` and `sl_price`.
4. Simulate entries, TP/SL/TTL, fees, risk sizing, and metrics in donor
   execution code.
5. Keep one symbol per run. Multi-symbol evaluation is composed from multiple
   runs.

The old root-native harness under `src/crypt/backtest/` was retired by
ADR-0023. Usage search found only its own tests and stale docs. Do not extend
or resurrect it unless the owner explicitly reverses ADR-0023.

## Donor safety rule

`src/backtester/` is high-risk donor/source-of-truth code. It was not
originally designed by this repository's agents, and broad edits can silently
invalidate the thing being measured.

Implementation rules:

- Prefer adapting `crypt_ensemble` to the existing donor strategy API.
- Keep donor-wide execution, optimizer, and CLI changes additive and small.
- Cover donor changes with focused tests in `tests/backtester/`.
- Update this document and the relevant strategy spec before changing public
  strategy behaviour.
- Do not add portfolio-level multi-symbol simulation as part of normal M2
  cleanup. One-symbol runs are the accepted shape.

## Current commands

H4 donor-backed smoke:

```bash
uv run backtester run \
    --symbol SOL-USDT-SWAP \
    --strategy strategies/backtester/crypt_ensemble.json \
    --output results/crypt_ensemble_sol
```

H1 MTF diagnostic smoke:

```bash
uv run backtester run \
    --symbol SOL-USDT-SWAP \
    --from 2025-01-01 \
    --to 2025-02-01 \
    --strategy strategies/backtester/crypt_ensemble_h1.json \
    --output results/crypt_ensemble_sol_h1
```

Backtester tests:

```bash
uv run pytest tests/backtester -q
```

Every donor run export writes a chart frontend automatically:

- `ohlcv.csv`: continuous candles for the run window;
- `trade_chart.html`: TradingView Lightweight Charts report with candles,
  tradeable signal markers, entry/exit markers, and entry/TP/SL/trailing-stop
  level overlays.

This applies to `backtester run`, optimizer `best_run/`, `compare-fixed`,
`compare-grid`, and `signal-quality` artifacts because all of them export
through `ResultsAnalyzer.export_results(..., ohlcv_df=...)`.

Visual verdict workflow:

- `trade_chart.html` is part of the backtest evidence, not a separate optional
  tool. Every strategy-search handoff should treat it alongside `windows.csv`,
  `metrics.csv`, `trades.csv`, and mandate summaries.
- The owner may add an operator verdict in chat after reviewing the HTML
  reports. This verdict is optional, but when it exists the acting agent must
  record it in `docs/tasks/IN_PROGRESS.md` or `CHANGELOG.md` with the
  artifact path.
- The agent must then add its own verdict from metrics, trade logs, and chart
  evidence. If owner and agent verdicts disagree, the next step should be a
  narrow falsification run, not a broad optimizer search.
- Every combined verdict must end with the next concrete experiment, including
  the strategy file, windows, execution params, output path, and acceptance
  condition.

Manual regeneration for old artifacts remains available:

```bash
uv run backtester trade-chart \
    --run-dir results/crypt_ensemble_sol_h1/20260607_183249/runs/sol_2025_01
```

Manual regeneration uses `ohlcv.csv` by default; pass `--ohlcv
path/to/candles.csv` or `--ohlcv path/to/candles.parquet` for an external
continuous source frame. Legacy `trade_candles/` slices are only a fallback for
old artifacts and will not show between-trade candles.

`mise` is an optional convenience layer. Use the `uv` commands above as the
canonical form; use these wrappers only when `mise` is installed locally:

```bash
mise run sync
mise run test-backtester
mise run backtester-help
```

## Current migration status

Shipped donor-backed capabilities:

- `StrategyData` in `src/backtester/data_contracts.py`.
- `parquet` mode for one OHLCV Parquet file.
- `crypt-parquet` mode for the project `ParquetStore` layout.
- `crypt_ensemble` strategy under `src/backtester/strategies/`.
- Structural SMC stop-loss anchors with diagnostics.
- Monthly risk-base sizing per ADR-0019.
- H1 MTF mode using D1 context, H4 setup snapshots, and H1 execution.
- `optimize`, `compare-fixed`, `compare-grid`, and `signal-quality` CLI
  commands.
- Partial `compare-grid` summaries when some windows fail.
- Default-off H1 setup/anchor filters in `crypt_ensemble` plus
  `strategies/backtester/crypt_ensemble_h1_filtered.json` for bounded
  diagnostics.

Current calibration state:

- Candidate A (`rrr = 1.25`, `ttl = 36`, `risk_percent = 1.0`) is rejected as
  a calibration candidate after full SOL/TON and monthly grid review.
- More raw `rrr`/`ttl` search is low leverage until signal quality changes.
- The latest signal-quality comparison made short-only the best narrow H1
  diagnostic, but the margin-realism audit rejected unconstrained promotion:
  the seven-window short-only run reached 18 simultaneous positions and peak
  locked margin near or above initial capital.
- `capital_before` / `capital_after` in trade exports are realized-equity
  fields, not free-margin fields. Current H1 candidate reports now expose
  `locked_margin`, `available_balance_before`, `open_positions_before`,
  total locked margin before/after entry, peak open positions, peak locked
  margin, and minimum available balance.
- Per ADR-0026, margin caps and leverage selection are centralized in
  `margin_policy.py`. Peak locked margin should now scale with `risk_percent`
  on tight-stop profiles; re-run bounded grids after this change.
- `max_positions` should become the next bounded optimizer/search parameter.
  Unconstrained `max_positions = 0` is only a diagnostic baseline for H1
  candidate work.
- Optional trailing-stop execution is available behind
  `trail_activation_rrr` and `trail_distance_atr`. `trail_activation_rrr = 0`
  preserves the existing fixed-TP behavior. When enabled, the fixed TP remains
  active only until price first reaches `trail_activation_rrr` times the
  structural stop distance in profit; after activation, fixed TP is disabled
  and the position exits through `exit_reason = trailing_stop` when price
  crosses the trailing stop. The trailing distance uses a strategy-provided
  `trail_atr` column when present, otherwise execution ATR14 computed from
  closed candles (`shift(1)`) to avoid look-ahead. Trailing exits use taker fee
  semantics like stop exits.

## StrategyData contract

The rich donor input object remains:

```python
from dataclasses import dataclass
from typing import Any

import pandas as pd


@dataclass(frozen=True)
class StrategyData:
    candles_by_timeframe: dict[str, pd.DataFrame]
    extras: dict[str, pd.DataFrame]
    metadata: dict[str, Any]
```

Expected `crypt-parquet` fields:

- `candles_by_timeframe["H4"]`, `["H1"]`, `["D1"]`, optionally `["M15"]`:
  available OHLCV frames.
- `extras`: optional OI/LS-ratio/taker-volume frames.
- `metadata["symbol"]`: OKX instrument id.
- `metadata["exchange"]`: `OKX`.

Compatibility requirement: existing donor strategies may still receive a plain
DataFrame and must keep working.

## `crypt_ensemble` strategy

The strategy emits donor-compatible rows with:

- `signal`: `1`, `-1`, or `0`;
- `sl_price`: structural stop-loss price;
- confidence, score, regime, rationale, setup/trigger diagnostics;
- stop anchor metadata and per-engine strengths when available.

Trade setup rules:

- entry is left empty so donor execution enters at the next execution-bar open
  after a closed signal candle;
- stop anchors prefer order blocks, then fresh liquidity sweeps, then
  confirmed pivots, with ATR buffer/guardrails;
- BUY/SELL verdicts are tradeable by default only when a valid structural stop
  exists;
- optional H1 diagnostic filters can neutralize disallowed sides, blocked stop
  anchor types, stale anchors, and explicit context reversals; these filters
  are off unless the strategy JSON enables them;
- `min_confidence` is optional and diagnostic; it is not the default live alert
  threshold;
- missing required context emits `signal = 0` for that row instead of raising
  through the whole run.

## Validation checklist

Before considering future donor changes complete:

- relevant `tests/backtester/` tests pass;
- `uv run backtester --help` imports the root package without manual
  `PYTHONPATH`;
- changed strategy JSON paths in docs use `strategies/backtester/...`;
- generated artifacts are written under ignored root `results/` or `/tmp`, not
  under a nested donor project;
- public command changes are reflected in `README.md`.
