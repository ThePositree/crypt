# Distant take-profit diagnostics

This document is both the analysis contract and the contract for the optional
runtime policy. The policy changes only take-profit geometry: it never removes
the signal, changes the structural SL, or changes risk-based position sizing.
It is disabled unless the portfolio explicitly mounts the component at
`params.components.distant_tp` or uses the older `params.tp_policy` alias.

## Inputs

- the backtest `trades.csv`, including `selected_strategy` (or
  `position_group`), `entry_time`, `entry_price`, `sl_price`, `tp_price`,
  `exit_reason`, `pnl_abs`, and `holding_bars`;
- the matching run's `ohlcv.csv` for historical price context.

## Per-trade metrics

For every trade with a valid entry and TP:

- `tp_distance_pct = abs(tp_price - entry_price) / entry_price`;
- `sl_distance_pct = abs(sl_price - entry_price) / entry_price`;
- `tp_to_sl_ratio = tp_distance_pct / sl_distance_pct`;
- historical recency: number of H1 bars since the last pre-entry bar whose
  high/low range touched the TP level (direction-aware); missing history is
  reported as `unknown`, never as zero;
- outcome: `exit_reason`, realized `pnl_abs`, win/loss, and holding duration.

At signal time the strategy may also attach `tp_last_touch_bars`, calculated
from candles already closed before the entry. Live execution recomputes the
distance from the actual fill; it does not use future price or realized PnL.

An “improbable TP” cohort must be defined from entry-known information only.
The first report uses both a fixed review floor (`tp_distance_pct >= 5%`)
and a distributional view (top 10% of TP distances); it must also show the
raw distance so the threshold can be changed without rerunning the backtest.

## Required report

Report total count, win rate, total/average PnL, profit factor, exit-reason
distribution, holding duration, and strategy-level breakdown for the full
cohort, the improbable-TP cohort, and the complement. No TP rule is changed
until the cohort is sufficiently populated and its out-of-sample effect is
reviewed.

## Optional dynamic TP policy

The canonical mount is `params.components.distant_tp`. The older
`params.tp_policy` key remains a backward-compatible alias for research copies.
The component has these fields:

```json
{
  "enabled": false,
  "min_original_rrr": 4.0,
  "min_tp_distance_pct": 0.07,
  "min_last_touch_bars": 720,
  "adjusted_rrr": 3.0,
  "strategies": {}
}
```

With the component mounted at portfolio scope, `strategies` may contain
per-donor overrides using the same fields. A donor override with
`"enabled": false` unmounts the component for that donor; with no portfolio
mount, an enabled donor entry mounts it only for that donor. An entry is
adjusted only when its original RRR is at least `min_original_rrr` and at least
one configured reachability condition is true: the original TP distance is at
least `min_tp_distance_pct`, or the last-touch age is at least
`min_last_touch_bars`. Missing age data cannot satisfy the age condition.
`adjusted_rrr` is clamped to the original RRR and must remain positive.

The event and trade audit expose `original_rrr`, `effective_rrr`,
`tp_adjusted`, `tp_adjustment_reason`, `tp_distance_pct`, and
`tp_last_touch_bars`. The live position keeps the same values in its
`signal_event` payload, and the entry notification explains an adjustment in
plain language. The default-disabled setting keeps old strategy files and
deployments behavior-compatible until an owner-approved comparison selects a
policy configuration.

## Current owner-selected narrow mount

The current owner-selected production v6 portfolio keeps the component
disabled globally and mounts it only on donor
`freq_4pw_r03_catcma_011465`:

- `min_original_rrr = 4.0`
- `min_tp_distance_pct = 0.06`
- `min_last_touch_bars = null` / disabled
- `adjusted_rrr = 3.0`

This is an owner-selected production mount, not proof that the component is
globally useful. Do not widen it to other donors without a new comparison
showing better dollars and drawdown.
