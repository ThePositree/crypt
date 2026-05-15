# Post-mortem: <title>

Use this template for every operational incident that affects the
running system (process crash, missed ticks, bad alerts, exchange
outage, data loss). One file per incident, named
`YYYY-MM-DD-short-title.md` in this directory.

Goal: capture enough that a future agent (and the owner) can review the
incident without paging the original responder. Honest about what we
did not know.

---

- **Date (UTC)**: YYYY-MM-DD
- **Severity**: P0 (system down) | P1 (degraded) | P2 (visible but
  benign) | P3 (latent risk discovered)
- **Author(s)**: agent | human + name/handle
- **Status**: open | resolved | won't-fix

## Summary

One paragraph that someone in a hurry can read. What happened, what
was the impact, what is the current state.

## Timeline (UTC)

Stick to facts. Include log timestamps where available.

- `HH:MM` — symptom first observed: …
- `HH:MM` — initial triage: …
- `HH:MM` — root cause identified: …
- `HH:MM` — mitigation applied: …
- `HH:MM` — fully resolved: …

## Impact

- Tick(s) missed: …
- Verdicts wrong / suppressed: …
- Alerts mis-fired: …
- Data lost or corrupted: …
- Owner trades affected: …
- Time spent on response: …

## Root cause

Plain prose. **Not** "Telegram failed" — go one level deeper. Why did
the system not handle the failure gracefully?

If the root cause is a code defect, link the commit / file lines.
If a third party (OKX, Telegram, Railway), link the vendor's status
page.

## What went well

- Heartbeat caught it before the owner did.
- Logs had the answer immediately.
- ...

## What went badly

- Alert took 30 min to surface because the heartbeat only checks
  liveness, not correctness.
- Logs had the answer but only after searching ~5k lines manually.
- The fix required a redeploy mid-run, breaking the no-downtime
  guarantee.
- ...

## What we didn't know at the time

- Whether the OKX rate-limit was IP-wide or symbol-specific.
- Whether the Telegram outage was global or chat-specific.
- ...

Be explicit. Pretending we had perfect information is a teaching
failure.

## Corrective actions

Concrete follow-ups, each with an owner and a target. Mirror these into
`docs/tasks/BACKLOG.md` with priority `P0`/`P1`/`P2`.

| # | Action | Owner | Priority | Target |
|---|--------|-------|----------|--------|
| 1 | Add health check for X | next agent | P1 | M2 |
| 2 | Document Y in runbook   | this session | P2 | done |

## Permanent fix vs band-aid

State explicitly: was the mitigation a permanent fix or a band-aid? If
band-aid, what is the permanent fix and when is it tracked?

## Lessons (one or two)

The single most-important takeaway. Don't pad — one sentence is fine.

## Related

- ADR-XXXX
- Other post-mortems
- Vendor status URLs
