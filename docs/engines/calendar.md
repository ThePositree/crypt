# Engine: calendar

Status: **proposed, post-M2** (BACKLOG P1 — cheap, defensible safety
filter).

A calendar engine reduces confidence on directional verdicts when a
known high-impact event is imminent. It is not predictive; it does not
say "FOMC tomorrow → bullish". It says "FOMC tomorrow → we don't know
which way it will go, so trade less aggressively". This is a **risk
filter**, not an alpha engine.

---

## Purpose

Crypto markets, despite being 24/7, react sharply to scheduled
macro/regulatory events:

- FOMC rate decisions (8 per year).
- US CPI, NFP releases (monthly).
- ECB policy meetings.
- SEC filings deadlines (ETF cycles).
- Major exchange listings / delistings affecting a specific symbol.

In the 6h–24h window around these events:

- Volatility spikes (sometimes by 5x baseline).
- Spot/perp basis decouples.
- Existing engines fire as usual but their signal-to-noise drops.

A simple suppression rule near events is cheap and known to help.

---

## Data source

**No free API gives a clean, machine-readable, crypto-relevant event
calendar.** Two pragmatic paths, listed in priority order:

### Path A — Local YAML schedule, manually curated

- Owner-maintained `config/events.yaml`:
  ```yaml
  - utc: 2026-06-12T18:00:00Z
    label: FOMC rate decision
    impact: high
    scope: global         # applies to all symbols
  - utc: 2026-06-15T12:30:00Z
    label: US CPI release
    impact: high
    scope: global
  - utc: 2026-07-01T00:00:00Z
    label: XPL token unlock 5%
    impact: medium
    scope: [XPL-USDT-SWAP]
  ```
- Pro: zero external dependency.
- Pro: trivial to add new events.
- Con: requires manual upkeep. Mitigate by writing the upcoming-12-month
  calendar of FOMC/CPI dates at engine launch time (they are scheduled
  long in advance).

### Path B — TradingEconomics / ForexFactory scraping

- Pro: automated.
- Con: TOS-questionable, fragile selectors, off-topic for a crypto
  system (90% of events on these calendars are irrelevant to us).
- Verdict: **rejected** for MVP of this engine. Revisit if we hit
  enough hand-curation friction.

**Decision: Path A.** If the agent implements it, also fill in the next
12 months of FOMC + CPI + NFP + ECB dates from public sources at
creation time.

---

## Inputs

- `ctx.events` — list of `Event` objects spanning the next 7 days,
  filtered to events with `scope == "global"` or `ctx.symbol in
  scope`.

```python
@dataclass(frozen=True)
class Event:
    utc: datetime
    label: str
    impact: Literal["low", "medium", "high"]
    scope: Literal["global"] | list[str]
```

Loaded once at process start from `config/events.yaml`. No periodic
fetch.

---

## Output (`Signal`)

- `engine`: `"calendar"`
- `direction`: always `neutral`.
- `strength`: always `0`.
- `confidence`: always `0`.
- `rationale`: list of upcoming events with hours-until.
- `meta`:
  ```python
  {
      "upcoming_hours_to_event": float | None,
      "upcoming_impact":         "high" | "medium" | "low" | None,
      "confidence_multiplier":   float,   # applied by aggregator
  }
  ```

---

## Logic

```text
now = ctx.tick_time
upcoming = [e for e in ctx.events if 0 <= (e.utc - now).total_hours() <= 24]
if not upcoming:
    multiplier = 1.0
else:
    e = min(upcoming, key=lambda e: e.utc)
    hours_left = (e.utc - now).total_hours()
    if e.impact == "high":
        # Suppress harder the closer we are: 6h → 0.6, 24h → 0.9
        multiplier = 0.5 + 0.4 * (hours_left / 24)
    elif e.impact == "medium":
        multiplier = 0.75 + 0.25 * (hours_left / 24)
    else:                                        # low
        multiplier = 0.90 + 0.10 * (hours_left / 24)
multiplier = clip(multiplier, 0.50, 1.00)
```

A six-hour-out FOMC → multiplier `0.60`. A 23-hour-out CPI → `0.88`.

For events that have **already passed within the last 2h**, apply the
same suppression curve symmetrically (post-event volatility is just as
bad as pre-event):

```text
post = [e for e in ctx.events if -2 <= (e.utc - now).total_hours() < 0]
```

---

## Aggregator integration

Same pattern as `btc_context`: aggregator reads `meta.confidence_multiplier`
and applies it to the final verdict confidence (capped per the
combined-filter rule in `btc_context.md` §Known weaknesses).

---

## Decision-layer integration

No new decision filter. The confidence multiplier suffices — verdicts
that drop below `ALERT_CONFIDENCE_THRESHOLD` will be auto-suppressed by
the existing decision layer.

---

## Edge cases

- `config/events.yaml` missing → engine emits no-op signal with
  `multiplier = 1.0`. Log WARNING once at process start.
- `config/events.yaml` malformed → same fallback; log ERROR with the
  parse error.
- Multiple events in the next 24h → use the **earliest** event (most
  imminent). Document the choice in rationale: "next event: FOMC in
  4h (high)".
- An event whose `utc` is in the past beyond 2h → ignored.
- Timezone confusion → all event timestamps are `UTC` with `Z` suffix;
  the loader rejects anything without explicit tz.

---

## Tests

`tests/engines/test_calendar.py`:

- Empty event list → `multiplier = 1.0`.
- FOMC in 6h, impact=high → `multiplier ≈ 0.60`.
- CPI in 30h → no event in 24h window → `multiplier = 1.0`.
- FOMC 1h ago → post-event suppression triggered.
- Malformed YAML → engine returns no-op with WARNING; pipeline doesn't
  crash.
- Event scoped to `[XPL-USDT-SWAP]`, evaluated for `SOL-USDT-SWAP` →
  ignored.

---

## Owner workflow

- Once a month: owner edits `config/events.yaml` to add the next
  rolling 12 months of FOMC/CPI/NFP/ECB dates.
- Per token: as token-specific events become known (unlocks, hard
  forks), owner adds them.
- This becomes a Telegram bot command (`/event add ...`) in a future
  iteration — out of scope for the initial calendar engine.

---

## Known weaknesses

- The "important events" list is the owner's opinion. Events thought
  important may be priced in already; events thought unimportant may
  blow up. M2 should run with and without calendar to see if it helps.
- 24h window is a guess. Some events (FOMC) have ripple effects for
  72h+; some (a single CPI print) decay in hours. Per-event-type
  windows could be added; not in MVP.
- Manual maintenance can fall out of date. Add a daily WARNING if
  `max(e.utc for e in events) < now + 30d` — "calendar is empty for
  the next 30 days, owner please refresh".
- This engine is "smart enough to be dangerous": agents reviewing
  alerts could rationalise post-hoc ("the FOMC explained the bad
  trade"). The calendar should be evidence in a journal, not an excuse.
