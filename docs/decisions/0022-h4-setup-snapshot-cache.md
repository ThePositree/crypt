# ADR-0022: H4 setup snapshots in H1 MTF optimization

- **Status**: accepted
- **Date**: 2026-06-03
- **Owner**: agent

## Context

The first H1 MTF `crypt_ensemble` implementation recomputed the full H4
ensemble verdict on every H1 execution tick. This made bounded SOL H1 smokes
slow enough that Optuna was impractical: one January 2025 bounded slice still
took about five minutes even after the parity-safe closed-window cache.

The repeated H4 recomputation also had questionable semantics. H4 engines,
especially SMC structure/liquidity, age events from `ctx.tick_time`. When the
same closed H4 candle was replayed at 09:00, 10:00, 11:00, and 12:00 H1 ticks,
the H4 setup age drifted inside one H4 setup window even though no new H4
candle had closed.

The intended MTF model is top-down:

- D1 context;
- H4 setup;
- H1 trigger/execution.

In that model, the H4 setup should be a snapshot known when the H4 candle
closed. H1 bars should trigger or reject that setup, not mutate the H4 setup
age every hour.

## Decision

In H1 MTF mode, `crypt_ensemble` evaluates the H4 setup verdict once per closed
H4 setup timestamp and reuses that setup snapshot for H1 ticks until the next
H4 close. H1 trigger checks, H1 structural stop selection, and donor execution
timing remain evaluated at the actual H1 tick.

The H4 default mode remains per-H4-bar and does not use this cross-H1 setup
snapshot cache.

## Alternatives considered

- Keep per-H1 H4 verdict recomputation — rejected. It is too slow for Optuna
  and lets H4 event age drift inside an unchanged H4 setup window.
- Cache only candle/extras windows — already implemented. It improved bounded
  runtime, but not enough for optimizer use because engine and SMC evaluation
  still ran on every H1 tick.
- Cache SMC internals globally — rejected for this slice. It is lower-level and
  riskier; setup snapshot caching matches the MTF model directly.

## Consequences

- H1 MTF optimization becomes materially faster because the expensive H4
  ensemble is evaluated about once per four H1 bars instead of every H1 bar.
- H4 setup semantics are cleaner: setup freshness is tied to H4 close time;
  H1 is only the trigger/execution layer.
- Results may differ from the previous H1 diagnostic smokes. This is an
  intentional semantic change, not a parity-preserving speedup.
- Tests must prove snapshot invalidation at new H4 closes, while H1 trigger
  and H1 structural stop selection still use the actual H1 tick.

## References

- `docs/crypt_ensemble_mtf.md`
- `src/backtester/strategies/crypt_ensemble.py`
- ADR-0018: Donor backtester becomes the canonical M2 backtest architecture
