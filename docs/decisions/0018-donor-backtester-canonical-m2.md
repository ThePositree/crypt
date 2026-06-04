# ADR-0018: Donor backtester becomes the canonical M2 backtest architecture

- **Status**: accepted
- **Date**: 2026-06-02
- **Owner**: agent (owner directed in chat)
- **Supersedes**: the implementation direction of the current
  `src/crypt/backtest/` harness for future M2 work. Existing replay and
  no-lookahead code remains useful reference material until the replacement is
  accepted.
- **Updated by**: ADR-0023 retired `src/crypt/backtest/` after the
  donor-backed route became the canonical package under `src/backtester/`.

## Context

The repository currently has two backtesting implementations:

- `src/crypt/backtest/` — the project-native M2 harness. It replays the live
  ensemble over OKX Parquet data, labels verdicts, performs expanding-window
  walk-forward validation, optimizes ensemble weights with grid search plus
  coordinate descent, and writes static reports.
- `backtester/` — a donor package in this workspace (vendored in the monorepo
  per ADR-0021; formerly a nested clone of `AuriumX/backtester`). It has a simpler
  product-oriented shape: a strategy emits `signal` and `sl_price`, then the
  backtester owns trade execution, risk sizing, TP/SL/TTL handling, fees,
  metrics, exports, dashboards, and an Optuna optimizer for strategy/risk
  parameters.

The owner wants the product to be strategy/backtester-first:

- the signal system should produce full trade setups, not only
  `BUY` / `SELL` / `HOLD`;
- the backtester should own execution simulation and risk metrics;
- the ensemble can be represented as one strategy;
- multi-symbol operation does not need to happen inside one backtest run. One
  run per symbol is acceptable;
- the existing Parquet datasets must remain the primary data source;
- donor backtester changes should be additive and minimal, preserving its
  existing CSV and BingX workflows.

## Decision

Future M2 work will migrate toward `backtester/` as the canonical backtest
architecture. The current `src/crypt/backtest/` harness is deprecated for new
feature work, except as reference code for parity, no-lookahead behaviour, data
contracts, and previously discovered bugs.

The donor package must be extended rather than rewritten:

1. Add Parquet data loading beside CSV and BingX.
2. Add a flexible strategy data contract that can carry a primary OHLCV frame,
   additional timeframe frames, optional extra data frames, and metadata.
3. Register a `crypt_ensemble` strategy that adapts the existing engines and
   aggregator into the donor strategy interface.
4. Keep one-symbol-per-run semantics. Multi-symbol reports can be composed by
   running the same strategy repeatedly over different symbols.
5. Do not remove `src/crypt/backtest/` until the donor-backed route can run at
   least one SOL backtest and produce auditable trade output. This guard was
   satisfied and then superseded by ADR-0023.

## Required interface shape

Add an additive data contract in `backtester/`, for example:

```python
@dataclass(frozen=True)
class StrategyData:
    primary: pd.DataFrame
    candles: dict[str, pd.DataFrame]
    extras: dict[str, pd.DataFrame]
    metadata: dict[str, Any]
```

The old interface remains valid:

```python
strategy.generate(df: pd.DataFrame) -> pd.DataFrame
```

The new interface supports richer strategies:

```python
strategy.generate(data: StrategyData) -> pd.DataFrame
```

The returned frame must remain compatible with donor `ExecutionSim`:

- `signal`: `1` for long, `-1` for short, `0` for no entry;
- `sl_price`: stop-loss price;
- OHLCV columns on the index used by execution.

Additional columns such as `confidence`, `score`, `regime`, `tp_price`,
`risk_percent`, `rrr`, and `rationale` should be preserved when practical so
reports can attribute trades back to ensemble decisions.

## Parquet data contract

The migration must not remove local Parquet datasets. Add two additive loader
modes:

- `parquet` — load a single OHLCV Parquet file into the existing single-frame
  strategy path.
- `crypt-parquet` — load the project's symbol directory from `data/` and build
  `StrategyData` with H4 as `primary`, H1/D1 under `candles`, and optional
  extra frames under `extras`.

The exact filenames should be discovered from the existing `ParquetStore`
layout rather than invented ad hoc. If the donor loader needs a new helper,
prefer wrapping or importing the existing store code instead of duplicating
path logic.

## Optuna direction

The donor Optuna optimizer is not copied blindly into `src/crypt/backtest/`.
Instead, Optuna should be made usable in the donor-backed route for the
`crypt_ensemble` strategy.

The first Optuna slice should optimize only safe, explicit strategy/backtest
parameters:

- ensemble regime weights and thresholds;
- optional setup parameters already exposed by the strategy contract, such as
  SL ATR multiplier, RRR, TTL, or risk percent, only after the trade setup
  contract exists.

Owner-defined acceptance criteria such as minimum average daily return are
allowed, but they must be evaluated on out-of-sample walk-forward test slices,
not on the same data used by Optuna to search.

## Alternatives considered

- Keep the current `src/crypt/backtest/` harness and add Optuna there —
  rejected by owner direction. The owner wants the product shape to be centered
  on a strategy/backtester architecture with trade setup output.
- Fully replace donor internals immediately — rejected. The donor package is
  useful because its current API is simple and tested; initial changes should
  be additive.
- Drop Parquet and use CSV input for the donor package — rejected. Parquet is
  the project's existing storage contract and is required for reproducible OKX
  backtests.
- Add multi-symbol portfolio simulation first — rejected for the migration
  phase. One-symbol-per-run keeps the interface smaller and avoids re-opening
  the previous multi-symbol execution-mixing bug class.

## Consequences

### Positive

- The backtest architecture matches the owner's product model: a strategy emits
  trade setups, the backtester simulates execution and reports results.
- Donor execution/risk semantics can be reused without bending the current
  ensemble-weight optimizer further.
- Optuna can be introduced in the place where it naturally belongs: strategy
  and risk-parameter search.
- Single-symbol runs reduce migration complexity.

### Negative

- Current M2 report artifacts and `src/crypt/backtest/optimizer.py` become
  transitional rather than the future source of truth.
- The donor package needs a richer strategy data interface before the existing
  ensemble can run there.
- Documentation and task tracking must be explicit so future agents do not
  continue extending the old harness by inertia.

## Follow-up

- Write `docs/backtester_migration.md` with concrete implementation phases.
- Add backlog items for Parquet loaders, flexible `StrategyData`,
  `crypt_ensemble` strategy registration, and first SOL smoke backtest.
- Keep `README.md` unchanged until the new donor-backed command actually runs.

## References

- `src/backtester/__main__.py`
- `src/backtester/data_loader.py`
- `src/backtester/optimizer.py`
- `src/crypt/backtest/`
- `docs/backtest.md`
- ADR-0014: M2 OHLCV-only calibration is rejected
- ADR-0017: M2 uses OHLCV-only calibration with SMC structure engines
- ADR-0021: Vend `backtester/` into the `crypt` monorepo
