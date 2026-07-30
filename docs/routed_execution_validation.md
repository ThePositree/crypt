# Routed execution validation

## Purpose

Convert a router's daily single-strategy selections into one continuous
portfolio built from the archived strategy trade exports.

This is the validation layer between rolling-label router search and the
strategy benchmark. Rolling-label returns are research scores; only routed
trade execution can produce mandate-style monthly rows.

## Inputs

- `router_search_predictions.csv` from a completed router search;
- one `router` search-row id;
- an archived performance matrix containing `strategy_trades/*.csv`;
- half-open validation window `[start, end)`;
- initial capital;
- maximum allowed locked-margin fraction.

Required prediction columns:

- `router`;
- `asof`;
- `selected_strategy`.

Required source-trade columns:

- `signal_time` or `entry_time`;
- `entry_time`;
- `exit_time`;
- `pnl_abs`;
- `risk_base_capital`;
- `locked_margin`.

## Selection contract

- The router always names exactly one strategy.
- `cash`, empty, and unknown strategy selections are invalid.
- A source trade is eligible only when its strategy is selected at the
  trade's signal timestamp.
- Selection uses the latest prediction with `asof <= signal_time`.
- The last prediction is carried forward through the validation end. The
  report exposes maximum selection staleness.

## Switch and position contract

Switch policy is `drain`:

1. positions already opened by the previous strategy remain until their
   recorded exits;
2. while those positions remain open, entries from a newly selected strategy
   are rejected;
3. after the portfolio is flat, the selected strategy may open positions.

This preserves recorded exit geometry without inventing a mark-to-market
forced-close price and guarantees that positions from two strategies are never
open simultaneously.

Multiple positions from the same selected strategy remain allowed when its
archived execution produced them.

## Capital and margin replay

Source trades were generated in separate strategy portfolios. Monetary trade
fields are rescaled into the routed portfolio:

```text
scale = routed_month_start_risk_base / source_risk_base_capital
routed_pnl = source_pnl_abs * scale
routed_locked_margin = source_locked_margin * scale
```

The routed risk base resets on the first accepted entry of each calendar month,
matching the archived strategies' `risk_base_period=monthly`.

An entry is rejected when total routed locked margin after entry would exceed
`current_capital * max_allowed_margin`.

## Outputs

- `routed_trades.csv`: accepted routed trades with source and routed monetary
  fields;
- `rejected_entries.csv`: drain and margin rejections;
- `selection_timeline.csv`: router selections used in the window;
- `execution_summary.csv`: return, capital, trade, switch, staleness, and
  margin diagnostics;
- `monthly_mandate.csv`;
- `mandate_summary.csv`;
- `report.md`.

## Limitations

- This is a deterministic replay of archived trades, not a fresh multi-strategy
  OHLCV simulation.
- Rejected entries do not alter later source-strategy signals or exits.
- December selections are carried forward from the last available prediction
  when rolling labels stop before year end.
- Large losing-day count remains zero until a canonical intraday equity
  threshold is defined; this matches the current mandate reporter behavior.
