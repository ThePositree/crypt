# Strategy benchmark

This document defines the main money benchmark used to compare automated crypto
strategies. It replaces the old "investment mandate" framing.

The benchmark is an optimization and reporting target. It is not a hard policy
that blocks the owner from production-promoting a strategy. The owner may put a
strange, incomplete, or benchmark-failing strategy into live production at any
time. Agents must treat that as a normal owner override: document the evidence,
the known risks, the active source of truth, and the next verification step.

Status: accepted benchmark, derived from ADR-0025.

## Product target

Find strategies and portfolios that can be automated with acceptable money
results and operational risk. The strongest comparison target remains:

- SOL first, then other symbols when useful.
- `$10,000` reference capital per symbol/portfolio.
- Full continuous calendar-year evaluation, especially 2025 for SOL.
- Results after the backtester fee/slippage model.

Live execution is part of the project. A live strategy can be owner-promoted
even when it does not pass this benchmark. That live status does not by itself
prove that the strategy is benchmark-quality.

## Benchmark floor

| Parameter | Value |
| --------- | ----- |
| Starting capital | `$10,000` |
| Monthly return target | `+15%` |
| Monthly profit target | `$1,500` |
| Positive outlier cap for ranking | `+20%` per month |
| Main SOL check | Continuous 2025 backtest |
| Costs | After fees and slippage |

A month passes the floor when `raw_monthly_return_pct >= 15`.

For ranking, cap positive months:

```text
capped_monthly_return_pct = min(raw_monthly_return_pct, 20)
```

Pass/fail still uses raw monthly return. Negative outliers are not capped.

## Risk checks

- Monthly drawdown is measured inside each calendar month from the
  month-start capital using realized equity from closed trades.
- A month with benchmark drawdown worse than `-10%` is a major risk breach.
- Three consecutive losing months are a discard-level warning for benchmark
  evaluation.
- Peak-to-trough drawdown is still reported separately because it describes
  the account path, but it does not replace the below-start monthly benchmark
  metric.

## Benchmark verdicts

These verdicts describe research quality. They do not override the owner's
right to run a strategy live.

- **Promote-quality:** roughly 9+ of 12 months pass the 15% floor, no monthly
  drawdown breach, no three consecutive losing months, and execution/margin
  behavior is understood.
- **Archive-quality:** useful evidence or regime behavior, but not strong
  enough for the benchmark target.
- **Discard-quality:** too many weak months, severe drawdown, repeated losses,
  or invalid/superseded assumptions.
- **Needs more work:** not enough evidence, unresolved data/reconciliation
  gaps, or owner wants more exploration before deciding.

If the owner promotes a benchmark-failing strategy, write that plainly in the
relevant task/execution docs and continue from the active runtime config.

## Required reporting

Any serious strategy comparison should include:

- strategy/config path and symbol/window;
- artifact path;
- starting and final capital;
- total PnL in dollars and percent;
- monthly raw and capped returns;
- monthly below-start drawdown;
- peak-to-trough drawdown;
- trade count, win rate, profit factor, exit mix;
- liquidation/unsafe-exit count when relevant;
- verdict against this benchmark;
- explicit owner override if the strategy is live despite benchmark failure.

## Owner override rule

The benchmark guides optimization. Production selection belongs to the owner.

When the owner selects a strategy for live production:

1. Treat the selected runtime config as the operational source of truth.
2. Do not keep arguing the same benchmark objection.
3. Record material risks and benchmark failures once, clearly.
4. Continue with verification, reconciliation, safety, and improvement work.
5. If docs and active config disagree, stop and ask the owner.

## References

- ADR-0025 — original benchmark/mandate acceptance.
- ADR-0030 — drawdown from window-start capital.
- ADR-0032 — continuous evaluation for benchmark reports.
- ADR-0057 — distinguish below-start and peak-to-trough drawdown.
- `docs/tasks/BACKLOG.md`
- `docs/tasks/IN_PROGRESS.md`
