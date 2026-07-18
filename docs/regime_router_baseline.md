# Regime router baseline

Status: **MVP analysis**.

Source artifact:
`results/regime_matrix_archive_sol_2022_2025/oracle_labels/router_baseline_report.md`

This document summarizes the first portfolio-router baseline over the monthly
archive-only SOL 2022-2025 matrix.

## Validation

Walk-forward window:

- train/update state on all prior months;
- test from 2024-01 through 2025-12;
- monthly strategy returns come from `oracle_labels.csv`;
- no router can use same-month or future performance when selecting weights.

## Routers Tested

- `oracle`: impossible upper bound; uses the known best strategy for the month.
- `equal_weight_all`: equal weight across all archived strategies.
- `rolling_best_mean`: single strategy with best prior average monthly return.
- `rolling_top2_mean_60_40`: top two strategies by prior average return,
  weighted 60/40.
- `feature_knn_top2_gated`: five nearest prior months by OHLCV features, then
  top two strategies from those neighbors.

## Results

| Router | Final capital | Total return | Max DD | Avg month | Losing months | Switches |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `oracle` | $186,307.22 | +1763.07% | 0.00% | +13.34% | 0 | 20 |
| `rolling_top2_mean_60_40` | $16,650.74 | +66.51% | -12.58% | +2.26% | 4 | 0 |
| `equal_weight_all` | $14,536.72 | +45.37% | -18.69% | +1.67% | 8 | 0 |
| `feature_knn_top2_gated` | $14,209.04 | +42.09% | -6.00% | +1.52% | 7 | 18 |
| `rolling_best_mean` | $13,717.35 | +37.17% | -21.36% | +1.71% | 9 | 0 |

## Interpretation

The monthly OHLCV feature router is not ready as the main allocator. It lowers
drawdown, but it does not beat the simpler rolling top-2 mean portfolio on
return and it switches too often.

Current benchmark to beat:

```text
rolling_top2_mean_60_40
```

It is simple, live-safe, and does not require a fragile classifier:

```text
each month:
  compute prior average return for every archived strategy
  choose top two
  allocate 60% to top1 and 40% to top2
```

The feature-based router should remain a diagnostic baseline until it improves
return after switching and drawdown penalties.

## Next Router Step

Build a risk-gated rolling top-2 router:

1. Start from `rolling_top2_mean_60_40`.
2. Use OHLCV features only to reduce risk or abstain when the market is outside
   known training regimes.
3. Penalize switching and unknown exposure in the utility function.
4. Compare against `rolling_top2_mean_60_40`, `equal_weight_all`, and oracle.

Plan B remains rolling daily labels with raw per-strategy trades if monthly
data stays too coarse.
