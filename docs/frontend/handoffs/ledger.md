# Frontend Phase Control Ledger

Append-only evidence for D3 phase-control transitions. Do not rewrite or delete
existing event rows. Normal phase startup reads only the rows referenced by
`docs/frontend/handoffs/current.md`; the Final Instruction Audit reads the full
ledger.

| Timestamp | Handoff ID | Event | Phase | Predecessor | Successor | Mode | Repository state | Owner decision or waiver | Evidence or blocker |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
