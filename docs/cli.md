# CLI runbook

This is the owner-facing command surface. Commands default to:

- data directory: `data`
- symbol: `SOL-USDT-SWAP`
- historical period: full available candles
- starting capital: `$10,000`
- owner commands need only `PYTHONPATH=src` when the console script/module is
  not already installed in the active environment

Use `--from` / `--to` only for smoke windows. `full` and `all` are accepted
aliases for an omitted bound.

Agents running inside a restricted sandbox should additionally set
`UV_CACHE_DIR=/tmp/uv-cache` and `MPLCONFIGDIR=/tmp/matplotlib-cache`. Do not
include those cache env vars in owner-facing commands unless the owner asks for
an agent/sandbox-safe command.

## Available Commands

Backtester:

- `backtester run`
- `backtester optimize`
- `backtester search-signals`
- `backtester search-signals-matrix`

Runtime/data modules:

- `python -m crypt`
- `python -m crypt.backfill`

The old research/reporting CLIs were removed from the owner-facing product
surface. Use the kept commands or write a one-off script when an old archived
workflow needs reproduction.

## Backtest

Full production-strategy replay:

```bash
PYTHONPATH=src uv run backtester run \
  --strategy strategies/archive/filtered_donor_portfolio_post_adr0058_tail_control_v6_drop_negative_v5.json \
  --output results/v6_sol_full
```

Bounded smoke:

```bash
PYTHONPATH=src uv run backtester run \
  --from 2025-01-01 \
  --to 2025-02-01 \
  --strategy strategies/archive/filtered_donor_portfolio_post_adr0058_tail_control_v6_drop_negative_v5.json \
  --output results/v6_sol_2025_01
```

Advanced overrides still exist for unusual cases: `--data-dir`, `--symbol`,
`--capital`, `--risk-percent`, `--rrr`, `--ttl-minutes`, `--from`, `--to`,
and strategy-specific execution geometry flags. Legacy archived commands may
still contain `--ttl`; treat it as bars for reproduction only.

## Optuna

Default Optuna is a serious post-DSS money-geometry run: `50,000` trials, full
available SOL history, `$10,000` capital, the strategy-owned execution
timeframe, strategy-param search disabled, and execution-family search enabled.

```bash
PYTHONPATH=src uv run backtester optimize \
  --strategy path/to/dss_candidate.json \
  --output results/optuna_candidate
```

One run searches `exit_family` (`sl_rrr`, `sl_rrr_trailing`, `tp_pct`), `rrr`,
`position_ttl_minutes`, `risk_percent`, family-specific `trail_distance_atr`,
and family-specific `tp_move_pct`. It writes `best_geometry_summary.txt` next
to `best_trial.json` so the winning family and money parameters are readable
without digging through raw Optuna artifacts.

Default ranges:

- `rrr`: `1.0` to `10.0`, step `0.25`
- `risk_percent`: `0.25` to `3.0`, step `0.25`
- `position_ttl_minutes`: `60` to `10080`, step `60`
- `trail_distance_atr`: `0.5` to `10.0`, step `0.5`
- `tp_move_pct`: `0.004` to `0.14`, step `0.002`

Use `--trials N` only for bounded diagnostics. Common geometry overrides are
`--rrr-low/--rrr-high/--rrr-step`,
`--ttl-minutes-low/--ttl-minutes-high/--ttl-minutes-step`,
`--risk-percent-low/--risk-percent-high/--risk-percent-step`,
`--trail-distance-atr-low/--trail-distance-atr-high`, and
`--tp-move-pct-low/--tp-move-pct-high`. Candidates coming from DSS should
normally go straight to Optuna; DSS does not optimize RRR, TTL, or risk.

## DSS v3

Main endless matrix search:

```bash
PYTHONPATH=src uv run backtester search-signals-matrix \
  --output-root results/dss_v3_sol_all_endless
```

The matrix defaults to all DSS backends, all trigger/filter catalogs, SOL, the
standard 2022/2023/2024/2025H1 windows, minimum directional WR `45%`, and
endless resumable mode. Do not pass `--n-trials` for normal owner runs.

Useful DSS overrides:

- `--symbol BTC-USDT-SWAP` or repeat `--symbol` for multi-symbol searches.
- `--windows 2022,2023,2024,2025H1` to change validation windows.
- `--directional-min-wr 0.50` to tighten the per-window win-rate floor.
- `--n-trials N` for short bounded smoke tests only.
- `--algorithms smac_qd,hyperband_qd` when debugging a subset.

## Backfill

Backfill stays explicit because dates are exchange/data dependent:

```bash
PYTHONPATH=src uv run python -m crypt.backfill \
  --symbol SOL-USDT-SWAP \
  --from 2022-01-01 \
  --to 2026-08-04 \
  --data-types ohlcv \
  --data-dir data
```

Research CLIs fail fast with a suggested backfill command when required
candles are missing.
