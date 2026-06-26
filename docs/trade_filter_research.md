# Trade filter research

## Purpose

Trade filter research tries to improve existing strategy or router artifacts by
learning a `take` / `skip` rule over already generated trades. It does **not**
search for new entries, exits, or routers. The first MVP intentionally searches
single entry-known rules before any heavier model is considered.

The goal is to answer:

> Which bad trades could have been skipped using only information known at
> entry time, and does that improvement survive forward validation?

## Anti-overfit split policy

All trainable research entities use the same chronological split:

| Split | Window | Role |
| --- | --- | --- |
| Train | `2022-01-01` inclusive → `2024-01-01` exclusive | Fit/select rules. |
| Validation | `2024-01-01` inclusive → `2025-01-01` exclusive | Choose among train-discovered rules. |
| Stress | `2025-01-01` inclusive → latest available closed trade/bar | Final forward stress test. |

If a shorter artifact is supplied, the command still emits all three split
rows; empty splits get zero-trade metrics. A rule is not considered useful just
because it improves the same period it was fit on.

## Inputs

Required:

- one or more `trades.csv` files from completed backtester runs;
- `entry_time`;
- `exit_time`;
- `pnl_abs`.

Optional:

- `initial_capital`, default `$10,000`;
- custom split boundaries;
- minimum train trades retained by a filter.

The command may use columns that are known at or before entry, for example:

- `selected_strategy`;
- `position_group`;
- `is_long`;
- `entry_price`;
- `sl_price`;
- `tp_price`;
- `position_ttl_bars`;
- `trail_activation_rrr`;
- `trail_distance_atr`;
- derived `entry_hour`, `entry_dayofweek`, `stop_distance_pct`,
  `tp_distance_pct`, and `reward_to_risk`.

Optional `--group-by <column>` runs the same search independently inside each
trade group. The first intended use is `--group-by selected_strategy`, so each
strategy inside a routed/composite artifact gets its own candidate filter set.
The grouping column itself is removed from candidate features for grouped
searches, because otherwise every group would learn a trivial constant rule.

Optional `--include-catalog-features --ohlcv <path>` attaches closed-candle
discovery/catalog-style features at each trade entry time. These features are
computed from OHLCV only and joined with `merge_asof(..., direction="backward")`
so a trade can only see the latest candle state available at entry. The first
supported catalog-like features include ATR percent, volatility rank, trend
strength, RSI, Bollinger width/squeeze/wide flags, body/range, bar range in ATR,
volume ratio, EMA-stack flags, ROC, and London/New York session flags.

Portfolio-state fields are excluded by default because they can proxy time,
capital growth, and equity-curve state rather than market edge:

- `size`;
- `capital_before`;
- `risk_base_capital`;
- `locked_margin`;
- `available_balance_before`;
- `open_positions_before`;
- `total_locked_margin_before`;
- `total_locked_margin_after_entry`;
- `leverage`.

They may be enabled explicitly for risk-allocator research, but such results
must not be treated as alpha filters without exact re-simulation.

Absolute price and fee fields are also excluded from normal filter search:

- `entry_price`;
- `sl_price`;
- `tp_price`;
- `fee_entry`.

They can proxy calendar time or price level rather than trade quality. Use
derived geometry such as `stop_distance_pct`, `tp_distance_pct`, and
`reward_to_risk` instead.

## Leakage guard

The filter search must not use post-entry outcome fields as features.

Blocked columns include:

- `exit_time`, `exit_price`, `exit_reason`;
- `pnl_abs`, `pnl_rel`;
- `fee_exit`;
- `capital_after`;
- `holding_bars`;
- `exit_bar_index`;
- trailing state observed after entry, such as `trail_active` and
  `trail_stop_price`.

The output records every feature used by a rule so leakage is auditable.

## Search logic

MVP candidate rules:

- numeric threshold rules: `feature <= threshold`, `feature >= threshold`;
- categorical equality rules: `feature == value`, `feature != value`.
- two-rule conjunctions: `(rule_a) AND (rule_b)`.

Thresholds are generated from train split quantiles only. Validation and stress
never influence candidate generation.

Each rule is evaluated by applying it as:

```text
take_trade = rule(entry_known_trade_row)
```

The remaining trades are then scored as if skipped trades never happened.
This is a research approximation, not an exact portfolio re-simulation: skipped
trades can change later capital, margin, and overlap state. Any promising rule
must later be implemented inside the strategy/router and re-run through the
normal backtester.

Grouped search is still a research approximation. It answers whether a strategy
has a stable take/skip filter in isolation. It does not decide capital
allocation and does not prove the combined portfolio result. A useful grouped
filter must be embedded in the strategy/router and exact-tested by the normal
backtester.

## Outputs

The command writes:

- `filter_candidates.csv` — every tested rule with train/validation/stress
  metrics;
- `baseline_by_split.csv` — unfiltered performance for each split;
- `top_filters.csv` — top train-discovered rules ranked by robust forward
  score, with validation/stress deltas versus baseline visible;
- `report.md` — compact human summary and warnings.

Metrics per split:

- trade count;
- total PnL;
- return on initial capital;
- win rate;
- profit factor;
- mandate verdict;
- months passing the 15% floor;
- months below floor;
- worst monthly drawdown;
- train-derived research score.

## Acceptance

A filter is worth exact implementation only if it improves validation and
stress metrics versus the unfiltered baseline without relying on leaky fields.
The default robust-forward guard requires:

- validation score delta > 0;
- stress score delta > 0;
- validation return delta > 0;
- stress return delta > 0;
- stress floor-month count no worse than baseline;
- stress monthly drawdown no worse than baseline.

Exact promotion still requires a normal backtester run with the filter
integrated into the strategy/router.
