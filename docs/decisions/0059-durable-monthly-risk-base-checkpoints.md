# ADR-0059: Durable monthly risk-base checkpoints

- **Status**: accepted
- **Date**: 2026-07-28
- **Owner**: agent (owner approved implementation in chat)

## Context

The 2026-07 live reconciliation found that the live monthly risk base changed
from `$104.77` to `$102.3381502678064` inside the same UTC month during a
sequence of Railway deployments. The sizing formula was correct: the state
file was absent or replaced, so the executor treated the next entry as the
first entry of a new month and silently anchored risk to the then-current OKX
balance.

`live_positions.json` is necessary for position lifecycle recovery, but one
mutable file is not a sufficient source of truth for a month-level economic
anchor. A missing state file must never authorize a new live entry with a new
same-month risk base.

## Decision

For `risk_base_period = monthly`, live execution keeps one immutable checkpoint
per UTC calendar month under the durable execution data directory:

```text
<EXECUTION_RISK_BASE_CHECKPOINT_DIR>/YYYY-MM.json
<EXECUTION_RISK_BASE_CHECKPOINT_DIR>/YYYY-MM.backup.json
```

Each record contains the UTC month, exact unrounded risk base, creation time,
source, configured state path, and a mandatory payload checksum. The primary
and backup are created with an exclusive write and are never silently
overwritten. Both copies must exist, validate, agree byte-for-byte, and bind to
the configured canonical state path; a partial
pair is fail-closed rather than being treated as a healthy checkpoint.

Before a new live entry, the executor must resolve its risk base through this
checkpoint:

1. An existing validated checkpoint pair is authoritative. A missing or replaced state file
   is repaired from it before sizing.
2. A state/checkpoint month or value mismatch blocks new entries and sends an
   explicit operator alert. Position synchronization, protection repair, TTL
   closes, and other risk-reducing work continue.
3. A normal UTC-month rollover may create the new checkpoint pair only after
   the previous persisted month is itself backed by a matching checkpoint pair
   and the current exchange sync is clean, independently of the ordinary
   `EXECUTION_REQUIRE_EXCHANGE_SYNC` setting.
4. A current-month state with no checkpoint is not silently adopted in live
   money mode. A one-deploy operator migration flag may explicitly adopt an
   already synchronized existing state only when it also supplies the exact
   expected UTC month and unrounded base. It cannot bootstrap an empty state,
   a state recovered from the previous snapshot, a later month, or a different
   base. Previous-snapshot provenance is persisted with the recovered state and
   clears only after an authoritative checkpoint is applied or a verified new
   checkpoint pair is created from a previously verified month.
5. An empty state plus no current-month checkpoint is fail-closed for new
   live entries. The operator must restore a checkpoint or resolve the incident
   explicitly.

The mutable state file gains a durable write protocol: a generation counter,
payload checksum, fsync-backed atomic replacement, and a previous valid
snapshot. The checkpoint is still the authoritative risk anchor; the snapshot
only improves position-state recovery.

The first new-month checkpoint is intentionally fixed at the first post-sync
actionable H1 batch that reaches monthly risk sizing, before per-event
precision/leverage rejection. This preserves the existing backtester timing;
it is neither a midnight balance snapshot nor evidence that an order was
ultimately accepted.

The July 2026 migration intentionally adopts the currently persisted
`$102.3381502678064` anchor rather than rewriting historical July sizing. The
backtest reconciliation remains split at the proven state epoch; the new rule
starts a clean, auditable continuity chain for August and later.

## Alternatives considered

- **Continue using only `live_positions.json`** — rejected because the exact
  July failure already showed that absence of this file can silently alter the
  dollars at risk.
- **Automatically use the current OKX balance whenever state is absent** —
  rejected because it repeats the same failure mode.
- **Replace all execution state with SQLite now** — attractive for future
  transactional order/event history, but larger than the immediate reliability
  fix. The immutable checkpoint plus durable JSON snapshot closes the proven
  risk-base failure without changing order lifecycle semantics.

## Consequences

- A bad deployment or state-path change can pause new entries, but cannot
  silently change the month's position sizing.
- A partial/corrupt checkpoint pair pauses new entries until the operator
  restores both exact copies; the executor never repairs a partial pair by
  guessing a balance.
- The first live deploy after this ADR needs a one-time explicit adoption of
  the existing July state with the exact migration manifest, followed by
  verification of both checkpoint files and removal of those migration values.
- Operators gain a compact, exportable audit trail for every monthly sizing
  base.
- A future SQLite state repository can supersede the mutable JSON snapshot;
  it must retain the immutable checkpoint contract or formally supersede this
  ADR.

## References

- ADR-0019: monthly risk base for donor sizing
- ADR-0048: live execution parity and exchange sync
- ADR-0055: durable order recovery
- `docs/execution/live_execution.md`
- `docs/execution/live_backtest_reconciliation_2026-07-28.md`
- `src/crypt/execution/position_state.py`
