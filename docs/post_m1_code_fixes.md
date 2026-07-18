# Post-M1 code fixes

Latent code issues identified during the 14-day-run planning session
(2026-05-15). These are **not** active bugs blocking the run, but they
are correctness/clarity risks that should be addressed once the 14-day
window closes and pushes become safe.

Each item has:
- A short title.
- Files involved (with line ranges where possible).
- Why it matters.
- Proposed fix.
- Test that should be added.

Items here are duplicated as line items in `docs/tasks/BACKLOG.md` so
they appear in the prioritised view. **This file is the technical
detail; BACKLOG is the priorities.**

---

## 1. `closed=True` invariant for stored OHLCV is not enforced

### Files
- `src/crypt/data/store.py` (`save_candles`, `_upsert`)
- `src/crypt/data/ingestor.py` (`_ingest_ohlcv`)
- `src/crypt/exchange/okx.py` (`fetch_ohlcv`)

### Why it matters
`ParquetStore.load_candles` filters by `closed`. The ingestor and the
exchange client both produce `Candle(closed=True)` by default, but the
chain does not assert this. If a future change to the exchange layer
ever returns a partial bar with `closed=False`, the upsert step would
overwrite the most recent **closed** bar with a half-formed one and
the closed-filter would then drop it from engines, silently regressing
the look-ahead invariant in the *opposite* direction (engines would see
slightly less data than expected).

### Proposed fix
- In `OKXClient.fetch_ohlcv`, set `closed=True` only when the bar's
  `open_time + timeframe <= now - safety_buffer` (e.g. 5 s). OKX's
  REST OHLCV typically excludes the currently forming bar but verify in
  Context7 at fix time — the behaviour has changed in past CCXT
  versions.
- In `Ingestor._ingest_ohlcv`, filter to `closed=True` before
  `save_candles`. Cheap belt-and-suspenders.
- Add an assertion in `ParquetStore.save_candles`: every candle must
  have `closed == True`. If a non-closed candle ever gets there, raise
  loudly.

### Test
`tests/data/test_store_closed_invariant.py`:
- Synthesise a candle with `closed=False` → `save_candles` raises
  `ValueError`.
- Synthesise a mixed list → ingestor's pre-filter drops the open one.

---

## 2. Critical-inputs guard is hard-coded to `candles[H4]`

### Files
- `src/crypt/decision/filters.py` (`_has_critical_missing`)
- `docs/engines/decision.md` §3

### Why it matters
The decision guard demotes a verdict to `HOLD` if any engine reports
`inputs_missing` containing `candles[H4]`. This is correct today
because all directional engines depend on H4 candles. But when new
engines join (sentiment, liquidations, btc_context), each defines its
own "critical" inputs. A `derivatives`-style engine that loses `oi`
would not trigger the guard even if `oi` is its critical input.

The single-source-of-truth pattern is broken: spec lists "critical
inputs" per engine; the guard ignores them.

### Proposed fix
- Promote a `critical_inputs: ClassVar[list[str]]` field on each
  `BaseEngine` subclass.
- Each engine, when it computes `inputs_missing`, populates a sibling
  `critical_missing: list[str]` field on its `Signal`.
- `_has_critical_missing` reads `critical_missing` from every signal
  rather than substring-matching `"candles[H4]"`.

### Test
- New `Signal` field `critical_missing` defaults to empty.
- Trend engine with missing H4 → `critical_missing=["candles[H4]"]`,
  guard triggers.
- Sentiment engine (when implemented) with stale data → `critical_missing=[]`
  but `inputs_missing=["sentiment_fresh"]`, guard does NOT trigger.

---

## 3. Anti-flip-flop guard for direction whipsaws

### Files
- `src/crypt/decision/filters.py` (`should_alert`)
- New behaviour, not currently implemented.

### Why it matters
The decision filter only enforces cooldown when the **same** direction
fires again within the window. A `BUY` followed by a `SELL` (and vice
versa) is allowed through with full confidence. In `RANGING` regime
near regime boundaries, this produces alert whiplash. The operator
gets two alerts in a row, in opposite directions, and is supposed to
flat the first and open the second. Real-world feedback says this is
where humans lose money.

### Proposed fix
Add a flip-history check: if `(BUY → SELL)` or `(SELL → BUY)` happens
within `flip_dampen_hours` (default 12 h), multiply the second
verdict's confidence by `flip_confidence_multiplier` (default `0.7`).
If the dampened confidence drops below threshold, the alert is
suppressed (cleanly handled by existing threshold filter).

Settings:
```python
flip_dampen_hours: int = 12
flip_confidence_multiplier: float = 0.7
```

### Test
- `BUY` at `T`, `SELL` at `T+8h` with raw confidence `80` → after
  multiplier `56` → alert suppressed (below `75`).
- `BUY` at `T`, `SELL` at `T+13h` → no dampening; alert proceeds.
- Same direction sequence (`BUY` → `BUY`) → existing cooldown wins,
  no flip-multiplier involved.

---

## 4. `produced_at` vs wall-clock in cooldown

### Files
- `src/crypt/decision/filters.py` (cooldown comparison uses
  `verdict.produced_at`)

### Why it matters
In live the cooldown is based on `Verdict.produced_at`, which is set
to `datetime.now(tz=UTC)` by the orchestrator inside `tick()`. So in
live, `produced_at` is effectively wall-clock. In backtest replay
however, `produced_at = tick_time`, which is historical. Both modes
work the same way because we picked `produced_at` consistently, but
this is currently undocumented and any future code that uses
`datetime.now()` in the filter would silently break backtest.

### Proposed fix
Add a docstring + a test that asserts:
- In live: `verdict.produced_at` ≈ now.
- In backtest: `verdict.produced_at == tick_time`.

No code change strictly required; documentation + regression test.

### Test
- Two backtest verdicts at historical timestamps 1 h apart → second is
  suppressed by cooldown even though the wall clock is "now".

---

## 5. `Signal.confidence ∈ [0,1]` vs `Verdict.confidence ∈ [0,100]`

### Files
- `src/crypt/models.py` (`Signal`, `Verdict`)
- All engines
- `src/crypt/aggregator/ensemble.py`

### Why it matters
Two different scales for "confidence" are easy to mix up, especially
when reading log lines or writing new engines. The Pydantic constraints
catch the mistake at runtime but only when an out-of-range value is
constructed; an engine that accidentally returns `confidence=75`
instead of `confidence=0.75` would pass validation (`75` is not in
`[0, 1]`, it raises) — but reverse case (Verdict gets `0.78` instead
of `78`) silently rounds to `0` because `Verdict.confidence` is `int`.

### Proposed fix
- Use `pydantic` `confloat(ge=0, le=1)` for `Signal.confidence` and
  `conint(ge=0, le=100)` for `Verdict.confidence` (they already are).
- Add a property `Signal.confidence_pct -> int` for cross-talk:
  `round(confidence * 100)`.
- Add property tests (Hypothesis): generated `Signal` configs with
  random `confidence ∈ [0, 1]` always round-trip through aggregator
  to a `Verdict.confidence ∈ [0, 100]`.

### Test
- Random property-based test as above.
- Snapshot test: a deliberately constructed Signal with
  `confidence=0.78` produces a Verdict line whose human-readable form
  shows `78%` not `0.78%`.

---

## 6. XPL warm-up cliff

### Files
- `src/crypt/data/ingestor.py` (no special handling for young symbols)
- `src/crypt/engines/*` (graceful `neutral` on insufficient history)

### Why it matters
XPL-USDT-SWAP is a young instrument with fewer than 200 H4 bars
available. All engines currently return `neutral` with
`inputs_missing=["candles[H4]"]` for it. This is the *intended*
behaviour in MVP but means XPL alerts will never fire until ~33 days
of history accumulate.

We should make this fact **visible** rather than silent: tick summary
logs already show `partial` count, but it's not obvious whether
"partial" means "data is fine but engine is bootstrapping".

### Proposed fix
Distinguish in the tick summary log:
- `bootstrapping`: symbol exists but lacks history.
- `partial`: data fetch failed or returned less than expected.
- `failed`: hard error.

Each is its own counter. Add a stickier WARNING at process start that
lists symbols with `len(candles[H4]) < 200` so the operator knows
which ones are silent during warm-up.

### Test
- `tests/runtime/test_warm_up_classification.py` — synthesise a store
  with 50 H4 candles for one symbol; assert tick summary classifies
  that symbol as `bootstrapping`, not `partial`.

---

## 7. Combined-multiplier cap missing in aggregator

### Files
- `src/crypt/aggregator/ensemble.py`

### Why it matters
Several upcoming engines (btc_context, calendar) multiply the final
verdict confidence by a factor. Today's aggregator applies one
multiplier (the vol-regime one). When we add more, multipliers
compound. A `[BTC disagree=0.85] * [FOMC in 6h=0.6] * [Vol high=0.85]`
collapses confidence to 43% of nominal — possibly correct, possibly
over-suppressing.

### Proposed fix
- Aggregator computes the **product** of all filter multipliers.
- Clamp the product to `[0.5, 1.5]` before applying.
- Log the multiplier and its components.

### Test
- Apply three filters: `0.8, 0.7, 0.85`. Product = `0.476`, clamped to
  `0.5`. Verdict reports `multiplier=0.5` with rationale "clamped".

---

## 8. `inputs_missing` granularity

### Files
- `src/crypt/engines/*.py`

### Why it matters
The current `inputs_missing` is a flat `list[str]`. Engines use ad-hoc
strings: `"candles[H4]"`, `"oi"`, `"ls_ratio"`, `"funding"`,
`"bollinger"` (latter is computed, not an input — terminology slip).

Two consequences:
- Filtering (item #2 above) becomes fragile substring matching.
- Reports cannot reliably bucket "which inputs are missing most often".

### Proposed fix
Replace `inputs_missing: list[str]` with a typed enum:

```python
class InputKey(StrEnum):
    CANDLES_H4 = "candles[H4]"
    CANDLES_D1 = "candles[D1]"
    FUNDING    = "funding"
    OI         = "oi"
    LS_RATIO   = "ls_ratio"
    TAKER_VOL  = "taker_volume"
    SENTIMENT  = "sentiment"
    LIQUIDATIONS = "liquidations"
    BTC_CANDLES_H4 = "btc_candles[H4]"
```

Engines must emit `InputKey` members, not raw strings. Backward-compat:
the JSON serialisation is identical (StrEnum).

### Test
- Engine that emits a raw string instead of an enum → mypy fails at
  build time. Pydantic also rejects at runtime.

---

## How to use this document

When the 14-day run completes:

1. Triage in priority order (items #1, #2 are higher-priority than #6,
   #7; #8 is a nice cleanup).
2. Each fix is its own PR. Reference this file in the PR description
   and in the commit message.
3. Strike through the item here (do not delete — keep historical
   visibility).
4. Update `BACKLOG.md` and `CHANGELOG.md` per AGENTS.md §3.

If during the run an additional latent issue is discovered, append it
to this document immediately.
