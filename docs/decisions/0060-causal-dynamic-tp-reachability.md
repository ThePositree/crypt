# ADR-0060: Causal dynamic TP reachability policy

- Status: accepted
- Date: 2026-07-29

## Context

The v6 portfolio contains donors whose geometric RRR produces targets far
outside the recent SOL range. A 2025 review found a negative top-distance
cohort, but a global RRR cap reduced total PnL materially. Removing those
signals would also reduce the portfolio's intended frequency.

## Decision

Implement an optional, shared pure policy used by both backtest and live
execution. After the actual entry price is known, the policy may lower only the
effective RRR when the original RRR is above a configured floor and either the
TP distance or causal target recency exceeds a configured threshold. Structural
SL, risk percentage, position sizing, and signal admission remain unchanged.

The policy is disabled by default and is configured in a portfolio's
`params.tp_policy`, with optional per-donor overrides. Every decision records
the original/effective RRR, trigger reason, distance, and recency. Runtime must
never use realized PnL or future candles to decide.

## Consequences

- Backtest and Railway runtime can be compared with the same event payload.
- Operators can validate a targeted rule without deleting donor strategies.
- A policy configuration still requires an untouched-range comparison before
  being enabled in production.
- Existing strategy files preserve behavior because the default is disabled.
