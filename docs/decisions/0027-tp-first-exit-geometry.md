# ADR-0027: TP-first exit geometry for donor execution

- **Status**: accepted
- **Date**: 2026-06-08
- **Owner**: agent

## Context

Donor backtests use structural `sl_price` from `crypt_ensemble` and set TP as
`sl_dist × rrr`. Wide structural stops (often 4–8 ATR) push TP even farther;
many trades exit via TTL before TP. Owner direction: fix **target profit %** on
the position and derive SL from TP using `rrr`, with structural SL as a risk
cap (`cap` mode).

## Decision

Add execution mode `exit_geometry=tp_pct`:

1. `tp_price = entry × (1 ± tp_move_pct)`
2. `sl_dist = tp_dist / rrr`, then apply `structural_sl_mode` (default `cap`)
3. Position size unchanged: `risk_value / sl_dist`
4. Register `tp_move_pct` in Optuna when `--tp-move-pct-low/high` are provided
5. Default remains `exit_geometry=sl_rrr` for backward compatibility

## Alternatives considered

- **Widen TTL only** — treats symptom; TP still unreachable.
- **Fixed SL % and fixed TP % independently** — drops structural anchor entirely.
- **Strategy emits tp_price** — mixes signal layer with execution economics.

## Consequences

- Positive: realistic intraday TP distances; Optuna can search `tp_move_pct` with `rrr` and `ttl`.
- Negative: when `cap` binds, effective RRR exceeds configured `rrr`; reports should use realized distances.
- Revisit: combine with round-trip friction floor (BACKLOG P1) for net-after-cost gates.

## References

- `docs/backtester/exit_geometry.md`
- `src/backtester/exit_geometry.py`, `src/backtester/risk_model.py`
