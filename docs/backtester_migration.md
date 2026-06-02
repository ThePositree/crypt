# Donor backtester migration

This document is the implementation handoff for ADR-0018. It defines how to
move M2 backtesting toward the donor `backtester/` package without deleting
the current `src/crypt/backtest/` harness before parity is proven.

## Repository layout (ADR-0021)

`backtester/` is part of the `crypt` git repository. It is **not** a nested
git repo or submodule.

| Layer | Location | Notes |
|-------|----------|-------|
| Git | `crypt/` root | Commit donor changes with `git add backtester/...` from the repo root |
| Python package | `backtester/pyproject.toml` | Run donor CLI/tests from `cd backtester` with `PYTHONPATH=src:../src` |
| Ensemble code | `src/crypt/` | Imported by `crypt_ensemble` strategy |

One-time migration (owner): `rm -rf backtester/.git`, then `git add backtester/`
from the `crypt` root. If Git previously staged a gitlink, run
`git rm --cached backtester` first. See ADR-0021 for rationale.

Historical upstream: `https://github.com/AuriumX/backtester`. File headers that
cite that URL remain valid provenance markers, not instructions to use a
second repository for day-to-day work.

## Goal

Make `backtester/` the canonical backtesting architecture for the product:

1. Load existing project Parquet data.
2. Run the current ensemble as one donor strategy named `crypt_ensemble`.
3. Produce trade setups with at least `signal` and `sl_price`, then let donor
   execution simulate entries, TP/SL/TTL, fees, risk sizing, and metrics.
4. Keep one symbol per run. Multi-symbol evaluation is many independent runs.
5. Preserve donor CSV and BingX workflows.

## Donor safety rule

`backtester/` is treated as a high-risk donor/source-of-truth package. It was
not originally designed by this repository's agents, and broad edits there can
silently invalidate the thing we are trying to measure.

Implementation rule:

- Prefer adapting `crypt_ensemble` to the existing donor strategy API.
- Do not add new donor-wide optimizer, execution, or CLI semantics unless the
  owner explicitly approves the surface.
- If a donor edit is unavoidable, keep it additive, small, covered by focused
  tests, and documented in this file.
- Do not add walk-forward/fold logic to the donor optimizer as a first step.
  Use the donor optimizer shape that already exists; `trials` may remain an
  optional run knob with the donor default.

## Non-goals

- Do not delete `src/crypt/backtest/` during the first migration slice.
- Do not rewrite donor `ExecutionSim` unless a failing parity or unit test
  proves a required behaviour is missing.
- Do not introduce portfolio-level multi-symbol simulation in the first slice.
- Do not optimize all possible strategy/risk knobs at once. Optuna comes after
  the donor-backed `crypt_ensemble` smoke backtest works.
- Do not replace Parquet with CSV.

## Current donor interface

The donor CLI currently supports:

```bash
python -m backtester run \
    --data-source csv \
    --csv data/SOLUSDT_1m.csv \
    --strategy strategies/dual_ma_v1.json \
    --output results/dual_ma_v1
```

and:

```bash
python -m backtester run \
    --data-source bingx \
    --bingx-symbol BTC-USDT \
    --bingx-interval 1h \
    --bingx-start-time "2024-01-01 00:00:00" \
    --bingx-end-time "2024-01-31 23:59:59" \
    --bingx-api-key "$BINGX_API_KEY" \
    --bingx-api-secret "$BINGX_API_SECRET" \
    --strategy strategies/dual_ma_v1.json
```

The donor `Backtester` expects a strategy callable that returns a DataFrame
with:

- `signal`: `1`, `-1`, or `0`;
- `sl_price`: stop-loss price;
- OHLCV columns and a `DatetimeIndex`.

## Current migration status

As of 2026-06-02, the additive loader slice and first engine-wired strategy
slice are shipped:

- `StrategyData` exists in the donor package.
- `parquet` mode loads one OHLCV Parquet file.
- `crypt-parquet` mode loads the project `ParquetStore` layout for one symbol.
- `crypt_ensemble` runs the existing engines and aggregator over closed H4
  slices and emits donor-compatible `signal`, `entry_price`, structural SMC
  `sl_price`, confidence, score, regime, rationale, stop diagnostics, and
  per-engine strength metadata.
- Per ADR-0020, `crypt_ensemble` does not apply the arbitrary live alert
  threshold of `75` as a default donor entry gate. BUY/SELL verdicts are
  tradeable by default only when a valid structural stop exists.
  `min_confidence` remains an optional explicit diagnostic parameter; when
  set, lower-confidence BUY/SELL verdicts remain auditable in the metadata but
  become `signal = 0`.
- Donor execution now preserves strategy metadata on trade rows, including
  `signal_time`, `risk_base_capital`, confidence, score, regime, rationale,
  `sl_anchor_type`, `sl_anchor_level`, `sl_anchor_known_at`, `sl_distance_atr`,
  and `strength_<engine>` columns.
- Donor result export now includes `trade_diagnostics.csv` when trades exist.
  It summarizes exit reasons, long/short exit counts, PnL by side/reason,
  holding duration, trades per day, and `sl_distance_atr` by exit reason and
  stop anchor type.
- `crypt_ensemble` uses monthly risk-base sizing per ADR-0019:
  `risk_base_period = monthly`.
- The strategy includes a `progress` parameter, enabled in
  `backtester/strategies/crypt_ensemble.json`, because full one-symbol runs
  are slow enough to need visible progress.
- First MTF contract slice exists: `crypt-parquet` can select
  `primary_timeframe`, the donor CLI exposes `--primary-timeframe`, and
  `backtester/strategies/crypt_ensemble_h1.json` runs D1 context -> H4 setup
  -> H1 candle-confirm trigger/execution. The full SOL H1 smoke is not yet
  accepted; an attempted run loaded 21517 H1 bars but ended before export.
  Add a range limiter or performance pass before rerunning full-history H1
  smoke in normal agent sessions.

Verified smoke command:

```bash
cd backtester
PYTHONPATH=src:../src uv run --extra dev backtester run \
    --data-source crypt-parquet \
    --data-dir ../data \
    --symbol SOL-USDT-SWAP \
    --strategy strategies/crypt_ensemble.json \
    --output /tmp/crypt_donor_crypt_parquet_smoke
```

Experimental H1 MTF smoke shape:

```bash
cd backtester
PYTHONPATH=src:../src uv run --extra dev backtester run \
    --data-source crypt-parquet \
    --data-dir ../data \
    --primary-timeframe 1h \
    --symbol SOL-USDT-SWAP \
    --strategy strategies/crypt_ensemble_h1.json \
    --output /tmp/crypt_donor_h1_mtf_smoke
```

The neutral skeleton smoke loaded 5545 SOL H4 bars and wrote a no-trades
report. After engine wiring, the owner completed a SOL smoke run under the old
per-trade risk-base mode: it produced 1792 trades, final capital 6548.74 from
10000 initial capital, `total_return_pct = -34.51`, `profit_factor = 0.88`,
and showed that long-side trades were the main drag. That run also exposed
that donor execution was dropping `crypt_ensemble` verdict metadata from
`trades.csv`; this is now fixed.

The structural SOL smoke at
`/tmp/crypt_donor_structural_sl_smoke/20260602_143827` produced 1672 trades,
but 1496 of them closed by `ttl_expired`. The diagnostic root cause is the
current setup geometry: `ttl = 6` H4 bars gives a 24-hour holding window, while
TTL-expired trades had median `sl_distance_atr = 3.985`; with `rrr = 2`, the TP
is roughly 8 ATR away. That is usually too far for a one-day H4 trade to hit
before TTL. Do not optimize or cache the strategy path unless
parity/no-lookahead tests prove the optimized output is identical to the
straightforward replay.

## Structural stop-loss before optimizer

Implemented 2026-06-02. Before running the optimizer or treating backtest
metrics as meaningful, rerun the SOL smoke with the structure-aware stop.

Previous behaviour:

- BUY: `sl_price = close - sl_atr_mult * ATR14`.
- SELL: `sl_price = close + sl_atr_mult * ATR14`.

Current behaviour:

1. Prefer an active SMC order-block boundary aligned with the trade direction.
   For a long, stop below the bullish order-block low. For a short, stop above
   the bearish order-block high.
2. If no usable order block exists, prefer the swept liquidity level from a
   fresh SMC liquidity sweep. For a long after a sweep low, stop below the
   swept low. For a short after a sweep high, stop above the swept high.
3. If no fresh sweep exists, use the nearest confirmed SMC pivot on the
   protective side of entry. For a long, use the most recent confirmed
   swing/internal low below entry. For a short, use the most recent confirmed
   swing/internal high above entry.
4. Keep ATR as a guardrail, not as the primary stop anchor:
   - add a small ATR buffer outside the structural level;
   - reject or neutralize trades whose structural stop is on the wrong side of
     entry;
   - neutralize stop distances above `8 * ATR14`.

Use `pinescript/smc.pine` and `docs/engines/smc_core.md` as the behavioural
reference. The Python implementation reuses `crypt.structure.smc` outputs
(`SMCOrderBlock`, `SMCLiquiditySweep`, `SMCPivot`) rather than adding a
parallel SMC parser inside donor code.

The donor strategy output must keep the same `sl_price` column expected by
`ExecutionSim`; only the way `crypt_ensemble` computes that value changes.
Diagnostic columns are emitted as strategy metadata: `sl_anchor_type`,
`sl_anchor_level`, `sl_anchor_known_at`, and `sl_distance_atr`.

## Future donor Optuna direction

After structural stop-loss is implemented and smoke-tested, wire the existing
donor optimizer to `crypt_ensemble` with a minimal strategy parameter surface:

- `sl_atr_buffer_mult` or equivalent structural-stop buffer;
- optional `min_confidence`;
- per-regime decision thresholds;
- per-regime weights for the active OHLCV engines:
  `trend`, `meanrev`, `smc_structure`, `smc_order_blocks`, `smc_liquidity`.

`derivatives` remains weight `0` for primary OHLCV M2 calibration unless a
future ADR accepts deep OI/LS history as a reliable input. Do not introduce
`folds` or a new donor optimizer command as part of the first optimizer
repair. `trials` may remain an optional override if the existing donor
optimizer path exposes it; otherwise keep the donor default.

## Target CLI shape

Add simple Parquet mode first:

```bash
cd backtester
uv run backtester run \
    --data-source parquet \
    --parquet ../data/SOL-USDT-SWAP/ohlcv_H4.parquet \
    --strategy strategies/dual_ma_v1.json \
    --output results/parquet_smoke
```

Then add project-aware Parquet mode:

```bash
cd backtester
uv run backtester run \
    --data-source crypt-parquet \
    --data-dir ../data \
    --symbol SOL-USDT-SWAP \
    --strategy strategies/crypt_ensemble.json \
    --output results/crypt_ensemble_sol
```

The exact Parquet filenames must be derived from the existing
`crypt.data.store.ParquetStore` layout. Do not invent a parallel path scheme if
the store already provides the canonical one.

## StrategyData contract

Add a richer strategy input object while preserving the old DataFrame path:

```python
from dataclasses import dataclass
from typing import Any

import pandas as pd


@dataclass(frozen=True)
class StrategyData:
    primary: pd.DataFrame
    candles: dict[str, pd.DataFrame]
    extras: dict[str, pd.DataFrame]
    metadata: dict[str, Any]
```

Expected fields for `crypt-parquet`:

- `primary`: H4 OHLCV for the selected symbol.
- `candles["H4"]`: same H4 frame as `primary`.
- `candles["H1"]`: H1 OHLCV when available.
- `candles["D1"]`: D1 OHLCV when available.
- `extras`: optional OI/LS-ratio or future auxiliary frames.
- `metadata["symbol"]`: OKX instrument id, for example `SOL-USDT-SWAP`.
- `metadata["exchange"]`: `OKX`.

Compatibility requirement: existing donor strategies continue receiving a
plain DataFrame and continue passing current tests.

## Parquet loaders

Add loaders in `backtester/src/backtester/data_loader.py` or a nearby module:

- `ParquetDataLoader`: loads one Parquet file and standardizes it to donor
  OHLCV columns.
- `CryptParquetDataLoader`: loads a project symbol directory and returns
  `StrategyData`.

Single-file Parquet standardization:

- accept both donor-style columns (`open`, `high`, `low`, `close`, `volume`)
  and project-style columns (`o`, `h`, `l`, `c`, `v`, `open_time`);
- set a `DatetimeIndex`;
- sort by timestamp;
- validate required OHLCV fields.

Project-aware loading:

- prefer reusing `crypt.data.store.ParquetStore` for path conventions;
- H4 is required;
- H1/D1 are optional but missing frames must be represented as empty
  DataFrames, not as raised runtime errors;
- missing optional extras must not block a smoke backtest.

## `crypt_ensemble` strategy

Register a donor strategy key:

```text
crypt_ensemble -> CryptEnsembleStrategy
```

The first version should be minimal:

1. Accept `StrategyData`.
2. For each closed H4 candle, build an evaluation context equivalent to the
   existing replay context for that timestamp and symbol.
3. Run the existing engines and aggregator.
4. Emit a DataFrame aligned to H4 with:
   - `signal`;
   - `sl_price`;
   - `confidence`;
   - `score`;
   - `regime`;
   - `rationale` or a compact rationale id/string when practical.

Trade setup rule for the first slice:

- entry is the closed H4 candle close unless donor execution later uses next
  open by design;
- long SL = protective SMC level minus `sl_atr_buffer_mult * ATR14(H4)`;
- short SL = protective SMC level plus `sl_atr_buffer_mult * ATR14(H4)`;
- structural anchor hierarchy is order block, fresh liquidity sweep, then
  confirmed pivot;
- BUY/SELL verdicts emit donor signals by default only when a structural stop
  is valid;
- when `allow_atr_sl_fallback = true`, the old ATR-only stop can be used as a
  diagnostic fallback; it is disabled in the default strategy JSON;
- if `min_confidence` is explicitly configured, BUY/SELL verdicts with
  `confidence < min_confidence` emit `signal = 0`;
- RRR remains a donor backtest argument until a strategy-level TP contract is
  introduced.
- risk sizing for `crypt_ensemble` defaults to monthly window-base capital,
  not current capital after every trade. `trade`, `weekly`, `monthly`, and
  `backtest` modes remain available through `risk_base_period`.

The strategy must degrade gracefully: if required context is missing for a
timestamp, emit `signal = 0` for that row instead of raising through the whole
run.

## Optuna phase

Do not start with Optuna. First prove:

1. Parquet loader works.
2. `crypt_ensemble` runs on SOL.
3. The donor execution output is coherent.

Then add Optuna support for `crypt_ensemble`.

Initial search space should be explicit and small:

- regime thresholds;
- regime weights for active ensemble engines, normalized per regime;
- optional `min_confidence` and `sl_atr_buffer_mult`;
- later: `rrr`, `ttl`, `risk_percent`, and `risk_base_period`.

Owner-defined acceptance criteria are allowed, for example minimum average
daily return. They must be treated as report/acceptance criteria and evaluated
on out-of-sample slices, not only on the Optuna train objective.

## Validation checklist

Before considering the migration slice complete:

- donor CSV strategy tests still pass;
- new Parquet loader tests pass for project-style and donor-style columns;
- `crypt-parquet` missing optional H1/D1/extras does not crash the loader;
- `crypt_ensemble` smoke run produces trades or a clear no-trades report for
  one SOL dataset;
- generated trades include enough metadata to trace them back to ensemble
  verdicts;
- no code deletes or rewrites `src/crypt/backtest/` yet;
- `README.md` is updated only after a working command is available.

## Suggested implementation order

1. Add `StrategyData` and adapt donor `Backtester`/CLI plumbing so old
   strategies still receive DataFrames.
2. Add `ParquetDataLoader` and tests.
3. Add `CryptParquetDataLoader` and tests.
4. Add `CryptEnsembleStrategy` skeleton that can emit neutral/no-trade rows.
5. Wire existing engines into `CryptEnsembleStrategy`.
6. Run one SOL smoke backtest to completion.
7. Add Optuna support for ensemble weights only.
8. Decide whether to retire or keep individual modules under
   `src/crypt/backtest/`.
