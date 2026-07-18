# ADR-0014: M2 OHLCV-only calibration is rejected

- **Status**: accepted
- **Date**: 2026-06-01
- **Owner**: agent

## Context

After the multi-symbol execution simulator fix, the owner re-ran the primary
M2 backtest:

```bash
PYTHONPATH=src uv run python -m crypt.backtest \
    --from 2024-06-01 --to 2026-06-01 \
    --symbols SOL-USDT-SWAP,TON-USDT-SWAP \
    --walk-forward-folds 5 \
    --report-dir reports/backtest_2026-06/
```

The replay completed with 8760 verdicts and 4 generated walk-forward folds.
The optimizer sanity guard fired on the first two out-of-sample folds:

- Fold 0: train objective `0.1208`, test objective `-0.1245`.
- Fold 1: train objective `0.1208`, test objective `-0.0257`.
- Fold 2: train objective `0.0382`, test objective `0.0084`.
- Fold 3: train objective `0.0405`, test objective `0.0090`.

The original replayed placeholder weights also did not justify promotion:
3070 labelled BUY/SELL alerts had average `h24` forward expectancy about
`-0.25%` per signal after the optimizer's fee/slippage proxy, with hit rate
about `46.5%`. Long signals were especially weak:

- `SOL` BUY: 603 alerts, mean `h24` proxy PnL about `-0.62%`.
- `TON` BUY: 379 alerts, mean `h24` proxy PnL about `-1.07%`.

Execution-simulator test trades were also negative overall:

- `SOL`: 351 trades, mean `pnl_rel` about `-0.29%`.
- `TON`: 339 trades, mean `pnl_rel` about `-0.05%`.

## Decision

Do not promote `reports/backtest_2026-06/weights.recommended.yaml` to
`config/weights.yaml`, and do not flip `Settings.uncalibrated` to `False`.

The OHLCV-only SMC/trend/mean-reversion ensemble is still useful as a research
baseline, but it is not a calibrated trading signal. Keep live alerts marked
uncalibrated until a later backtest passes the sanity guard on all
out-of-sample folds and beats the baselines with a non-negative expectancy CI.

## Alternatives considered

- Accept only folds 2 and 3 — rejected because this would cherry-pick recent
  regimes and ignore two failed out-of-sample periods.
- Raise thresholds to reduce alerts further — rejected for now because the
  optimizer already produced sparse test signals in the guarded folds, and the
  failures were sign/expectancy failures rather than alert-frequency failures.
- Copy `weights.recommended.yaml` anyway as a conservative candidate —
  rejected because it aggregates failed folds and would remove the
  uncalibrated warning without evidence.

## Consequences

- M2 remains incomplete as a calibration milestone.
- `config/weights.yaml` stays a placeholder/live research configuration.
- The next modeling iteration should focus on reducing bad long signals and
  adding missing context rather than tuning the current weights harder.
- The report writer needs a hygiene follow-up: when any fold fires the sanity
  guard, `weights.recommended.yaml` should be clearly marked non-promotable or
  omitted, and `weights.candidate.yaml` should not ambiguously contain only the
  last fold's weights.

## References

- `reports/backtest_2026-06/summary.html`
- `reports/backtest_2026-06/meta.json`
- `reports/backtest_2026-06/verdicts.parquet`
- `reports/backtest_2026-06/trades.parquet`
- ADR-0017: M2 uses OHLCV-only calibration with SMC structure engines
