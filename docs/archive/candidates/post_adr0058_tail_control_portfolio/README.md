# Archived: post-ADR-0058 tail-control portfolio lineage

**Candidate id:** `post_adr0058_tail_control_portfolio`  
**Archived:** 2026-07-13  
**Status:** research lineage, not promoted  
**Symbol:** `SOL-USDT-SWAP`  
**Range:** `2021-12-18T00:00:00Z` to `2026-06-29T14:00:00Z`  
**Execution:** H1 signals with 1m last/mark execution, OKX SOL-USDT-SWAP precision and margin settings.

## Why archived

This archive preserves the decision-critical v1-v7 research branch created after ADR-0058 aggregate-average accounting. The branch starts from 24 split-RRR Optuna best-trial DSS donors, then iteratively removes or filters donors to trade off final account value, profit factor, liquidation count, drawdown, and weekly trade density.

Large run artifacts are intentionally not stored here. Full `signals.csv`, `ohlcv.csv`, `trades.csv`, `equity_curve.csv`, `trade_chart.html`, and per-trade candle reports are reproducible outputs, not durable archive inputs.

The best risk-quality version so far is v7. It is not promoted: the full-period result is strong, but filters were researched on the same history and require train/validation or walk-forward confirmation before any mandate or live decision.

## Version summary

| Version | Final | Return | PF | DD below start | Peak DD | Trades | Notes |
|---|---:|---:|---:|---:|---:|---:|---|
| `v1_all24` | $172,325.77 | 1623.26% | 1.01 | -8.58% | -90.72% | 5655 | Exact archive of all 24 split-RRR Optuna best-trial donors. |
| `v2_reduced_risk1` | $62,074.13 | 520.74% | 1.10 | -2.49% | -39.28% | 3278 | First drawdown-control cut: seven donors, risk capped at 1.0. |
| `v3_return_first` | $883,881.46 | 8738.81% | 1.09 | -1.36% | -62.81% | 3279 | Return-first branch: keep all v1 net-positive donors with original Optuna risk. |
| `v4_positive_v3` | $340,047.49 | 3300.47% | 1.09 | -1.36% | -58.44% | 3292 | Minimal cleanup from v3: remove only v3 net-negative donors. |
| `v5_filtered_v3` | $1,360,197.25 | 13501.97% | 1.39 | -6.79% | -39.14% | 1553 | Keep all v3 donors and original risk; add one entry-known catalog filter per donor. |
| `v6_drop_negative_v5` | $1,098,402.88 | 10884.03% | 1.48 | -17.75% | -39.23% | 1515 | Remove only the two v5 net-negative donors; keep remaining filters and risk. |
| `v7_apr2026` | $866,481.95 | 8564.82% | 1.90 | -6.85% | -32.33% | 935 | Start from v6; add four extra filters to the main 2026-04 loss contributors. |

## Files in this archive

- `versions_summary.csv` — one row per portfolio version with full-period metrics and compact snapshot paths.
- `donors_by_version.csv` — donor composition, execution params, and filter rules for every version.
- `commands.sh` — exact owner-run commands used to reproduce each full-period backtest.
- `strategy_configs/` — snapshots of the v1-v7 portfolio JSON configs.
- `backtest_snapshots/<version>/` — compact run artifacts: `metrics.csv`, `monthly_returns_snapshot.csv`, diagnostics, strategy attribution, and monthly strategy PnL when available.
- `provenance.json` — machine-readable archive provenance.

## What is intentionally omitted

The archive does not keep full backtest output trees or source-research run directories. Those files made the archive too large for git and duplicated reproducible data. The compact archive keeps enough information to understand and reproduce the decision:

- full-period money metrics in `versions_summary.csv`;
- donor membership and filters in `donors_by_version.csv`;
- portfolio configs in `strategy_configs/`;
- compact per-version metrics/monthly/attribution snapshots in `backtest_snapshots/`;
- reproduction commands in `commands.sh`.

Historical run-output directory paths are not part of this archive's provenance. Reproduction commands write to `/tmp/crypt_archive_reproduction/...` by default.

## Current interpretation

- v5 maximized full-history final account value (`$1.36M`) with PF 1.39 and peak DD around -39%.
- v6 improved cleanliness versus v5 by removing two net-negative filtered donors, but final account fell to `$1.10M` and DD stayed near -39%.
- v7 traded fewer times but improved PF to 1.90, peak DD to -32.33%, liquidations to five, and no unsafe liquidation-buffer exits.
- v7 is the current lower-DD branch; v5/v6 remain useful if the next goal prioritizes higher trade density or final account value.

## Reproduction

Run the exact commands in `commands.sh` from the repository root. Backtests are owner-run by policy; do not rerun automatically unless explicitly requested.
