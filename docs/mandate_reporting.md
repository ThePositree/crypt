# Mandate reporting

## Purpose

Automate ADR-0025 candidate-gate interpretation for donor backtest artifacts.
Candidate search must not rely on ad hoc CSV reading when deciding whether a
full-year run is promoted, archived, discarded, or eligible for full Optuna.

## Inputs

The reporter accepts completed donor trades from a single continuous candidate
run, or an ordered set of non-overlapping fixed windows for the same candidate.
When a `compare-fixed` report contains multiple symbols, each symbol is
evaluated independently because ADR-0025 assigns a separate `$10 000` portfolio
per symbol.

Required trade columns:

- `exit_time`: timestamp used to assign closed PnL to a calendar month.
- `pnl_abs`: realized PnL after fees and slippage.

Optional trade columns:

- `capital_before`: used to infer initial capital when not supplied.
- `capital_after`: used for equity snapshots when present.
- `exit_reason`: used for stop-loss counts.

The caller supplies `initial_capital`, normally `$10 000`.

## Monthly output

`monthly_mandate.csv` has one row per symbol and calendar month in the
evaluation window:

- `symbol`: candidate symbol.
- `month`: `YYYY-MM`.
- `raw_monthly_return_pct`: monthly realized PnL divided by initial capital.
- `capped_monthly_return_pct`: `min(raw_monthly_return_pct, 20)`.
- `excess_return_pct`: `max(raw_monthly_return_pct - 20, 0)`.
- `max_drawdown_pct`: worst intra-month drawdown on the realized equity curve.
- `trade_count`: number of trades closed during the month.
- `stop_loss_count`: number of trades with `exit_reason = stop_loss`.
- `passes_return_floor`: whether raw monthly return is at least `15%`.
- `breaches_monthly_dd`: whether intra-month drawdown is worse than `-10%`.
- `is_losing_month`: whether raw monthly return is negative.

When a month has no trades, return and drawdown are `0`, trade counts are `0`,
and the month fails the `15%` return floor.

## Summary output

`mandate_summary.csv` has one row per symbol with:

- `symbol`: candidate symbol.
- month counts above and below the `15%` floor;
- worst consecutive losing-month streak;
- count of large losing days;
- average and sum of capped monthly returns;
- worst monthly drawdown;
- final verdict: `promote`, `archive`, `discard`, or `full_optuna`;
- one compact rationale string.

`mandate_summary.md` mirrors the same summary for quick inspection.

## Verdict logic

1. `discard` if more than three months fail the `15%` floor.
2. `discard` if three or more consecutive months are losing.
3. `archive` if any month has max drawdown worse than `-10%`.
4. `promote` if at least nine months pass the return floor, no month breaches
   drawdown, no three-month losing streak exists, and large losing days are at
   most ten.
5. `full_optuna` when the candidate is not promoted but also not discarded or
   archived.

Large losing-day counting is currently conservative: it is `0` unless a caller
supplies a daily equity source. The monthly return and drawdown gates remain
the primary automated acceptance surface.
