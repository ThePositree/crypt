# ADR-0025: Owner investment mandate and candidate gates

- **Status**: accepted
- **Date**: 2026-06-05
- **Owner**: owner (direction in chat); agent documented

## Context

Bounded H1 optimizer work produced incremental improvements (+10.12% summed
across seven independent one-month windows for the best short-only row) but no
clear promotion bar. Agents optimized execution geometry, margin diagnostics,
and filters without a written economic target, creating risk of endless search
loops.

The owner clarified the product direction:

- **Auto-trading** is the goal; execution code comes **after** a candidate passes
  gates.
- Minimum **+15% per calendar month** on a **$10 000** portfolio ($1 500/month).
- Max **10% drawdown inside any month**; months above that go to **archive**
  without investigation.
- Full **2025** continuous backtest on **SOL first**, then **TON** after SOL.
- Positive outlier months are **capped at 20%** for ranking; negative outliers
  are **not** capped but trigger review.
- Near-miss candidates (e.g. ~+10%/month) go to an **archive**, not production.
- Approved search features: **trailing stop** (`trail_activation_rrr`,
  `trail_distance_atr`) and **stop-loss count limits** as Optuna dimensions.
- **Full Optuna** (strategy params + daily limits + trading window + execution)
  is for borderline candidates, not heavy serial losers.

## Decision

Adopt the strategy benchmark document as the canonical candidate comparison
surface. The document was originally `docs/investment_mandate.md` and is now
`docs/strategy_benchmark.md`. All agents read it at session start
(`AGENTS.md`). Candidate reports must emit a benchmark verdict before strategy
selection or production discussion.

Key numeric gates:

- Month passes when `raw_monthly_return_pct ≥ 15%`.
- Up to **3** of 12 months may fail without discard.
- **3** consecutive losing months → discard; **2** → full Optuna eligible.
- Monthly max DD **> 10%** → archive immediately.
- Evaluation uses backtester fees and slippage.

## Alternatives considered

- **Keep informal BACKLOG acceptance only** — rejected; too easy for agents to
  reinterpret each session.
- **20% monthly floor** — rejected; owner chose **15%** ($1 500 on $10k).
- **Reject high peak margin always** — rejected; owner wants margin simulator
  fixed for realism, not used as a blanket disqualifier when returns pass.

## Consequences

- Current H1 short-only bounded results remain diagnostic only.
- New P0/P1 backlog items: mandate evaluation metrics, margin geometry fix,
  trailing stop, stop-limit Optuna dims, archive artifact convention.
- `IDEAS.md` capped-profit policy is approved with **N = 20%** and lives in
  the mandate.
- README and AGENTS surface the mandate so it is hard to miss.

## References

- `docs/strategy_benchmark.md`
- ADR-0024 — margin realism
- `docs/tasks/BACKLOG.md`
- `docs/tasks/IDEAS.md` — 2026-06-03 capped profits (approved)
