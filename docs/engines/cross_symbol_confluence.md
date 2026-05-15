# Engine: cross_symbol_confluence

Status: **proposed, post-M2** (BACKLOG P1 — extremely cheap to add).

This is a **meta-engine**: it does not look at price/funding/news; it
looks at the directions the *other* directional engines emitted for the
*other* symbols in the same tick. It is implemented at the orchestrator
level rather than as a standard engine because each engine sees only one
symbol at a time.

---

## Purpose

When SOL, TON, and (where data permits) XPL all point the same way at
the same tick, the move is more likely to be a sector-wide swing rather
than symbol-specific noise. Conversely, when they disagree, one symbol's
strong-but-isolated signal is probably noise.

Examples of what we want to capture:

- All three symbols bullish on the same tick → confidence bonus per
  symbol. The market is breathing in.
- SOL bullish, TON neutral, XPL bearish → no bonus, no penalty.
- SOL strongly bullish, TON & XPL strongly bearish → penalty on SOL's
  confidence; the SOL signal is probably idiosyncratic noise.

This is similar in spirit to "breadth" indicators in TradFi (advancing
vs declining issues).

---

## Implementation surface

Not a `BaseEngine` subclass. Implemented in
`crypt/aggregator/cross_symbol.py`:

```python
def apply_confluence(
    verdicts: dict[str, Verdict],   # one per symbol in the current tick
) -> dict[str, Verdict]:
    """
    Returns new Verdicts with confidence adjusted by the
    cross-symbol-confluence rule. Decisions are NEVER changed by this
    function — only confidence.
    """
```

Called by `Orchestrator.tick()` **after** per-symbol aggregation, before
the decision filter:

```python
verdicts = {sym: aggregate(...) for sym in symbols}
verdicts = apply_confluence(verdicts)
for sym, v in verdicts.items():
    guarded = decision_filter.apply_guard(v)
    ...
```

Reason for placement: applying confluence after decision filter would
risk silencing the confidence multiplier if the verdict was already
guarded to HOLD. Doing it on raw verdicts keeps the math simple.

---

## Inputs

- `verdicts: dict[str, Verdict]` — one verdict per configured symbol
  in the current tick. May be a subset (some symbols failed evaluation).

A minimum of **3 symbols** is required for the engine to do anything.
With 2 or fewer, return verdicts unchanged.

---

## Logic

```text
# Quantify each verdict's directional intent.
def signed(v: Verdict) -> int:
    if v.decision == "BUY":  return +1
    if v.decision == "SELL": return -1
    return 0  # HOLD or neutral score

intents = {sym: signed(v) for sym, v in verdicts.items()}
n_total = len(intents)
n_dir   = sum(1 for x in intents.values() if x != 0)

if n_dir < 2:
    return verdicts  # not enough directional context

agree_long  = sum(1 for x in intents.values() if x > 0)
agree_short = sum(1 for x in intents.values() if x < 0)

# Confluence ratio: dominant-side count / total directional count.
dominant_side = +1 if agree_long >= agree_short else -1
dominant_count = max(agree_long, agree_short)
minority_count = min(agree_long, agree_short)
confluence_ratio = dominant_count / max(n_dir, 1)   # in [0.5, 1.0]
```

Per-symbol adjustment:

```text
for sym, v in verdicts.items():
    if signed(v) == 0:
        continue                          # HOLD untouched
    if signed(v) == dominant_side and confluence_ratio >= 0.66:
        # Agrees with majority → bonus
        v.confidence = min(100, v.confidence * 1.15)
    elif signed(v) != dominant_side and minority_count >= 1:
        # Goes against majority → penalty
        v.confidence = max(0,   v.confidence * 0.80)
    # else: tied or unclear → no change
```

Thresholds (`0.66`, `1.15`, `0.80`) are placeholders; calibrate in M2.

`v.rationale` gets one extra line:

```
Confluence: 3/3 BUY (bonus +15%) — cross-symbol agreement
```

or

```
Confluence: 1/3 BUY vs 2/3 SELL (penalty -20%)
```

---

## Symbol set considerations

The cross-symbol-confluence assumes the symbols are at least somewhat
correlated. Putting BTC + DOGE + a stablecoin pair into the universe
would produce nonsense.

The current MVP universe (SOL, TON, XPL) is acceptable: all three are
mid-cap alt perpetuals with BTC-correlation in the 0.4–0.8 range.

When future universes deviate (e.g. owner adds RUNE + SUI + ETH), this
engine should be **disabled** until a per-cluster confluence is added.
Add a Settings flag `cross_symbol_confluence_enabled: bool = True` so
the operator can toggle without redeploy.

---

## Edge cases

- All three verdicts HOLD → no-op, no adjustment.
- Two BUY + one HOLD (n_dir = 2, agree_long = 2) → confluence_ratio =
  1.0, but `n_dir < 3`; we still apply the +15% bonus because both
  directional verdicts agree (no minority to penalise).
- One HOLD + one BUY + one SELL → `confluence_ratio = 0.5` → no
  adjustment (tied).
- Failed evaluation (verdict absent for one symbol) → use the available
  subset; the rule degrades gracefully.

---

## Tests

`tests/aggregator/test_cross_symbol.py`:

- 3 BUY → all three get +15%.
- 2 BUY + 1 SELL → 2 BUYs get +15%, 1 SELL gets -20%.
- 1 BUY + 1 SELL + 1 HOLD → no adjustment (tied).
- 3 HOLD → no-op.
- 1 BUY + 1 HOLD (n_dir = 1) → returned unchanged.
- 2 BUY (no third symbol because evaluation failed) → both get +15%.
- Confidence saturation: BUY with conf 95 + bonus → clamped to 100, not
  >100.

---

## Cooldown interaction

The decision filter already enforces per-symbol cooldown. Cross-symbol
confluence runs **before** the cooldown check, so:

- A boosted-confidence verdict can pass the threshold and trigger an
  alert that would not have triggered without the bonus.
- A penalised-confidence verdict can drop below threshold and the alert
  is suppressed — but it is *still recorded* in JsonLogSink.

This is the intended behaviour: confluence amplifies what the
decision filter does, it does not bypass it.

---

## Known weaknesses

- "Confluence implies real swing" assumes symbol set is correlated.
  Adding a cluster of uncorrelated symbols will break the assumption
  silently. Mitigation: the toggle flag in Settings.
- Three symbols is a tiny sample; with 3, the confluence-ratio is only
  three values (0.33 / 0.5 / 0.67 / 1.0). As we grow the universe, the
  ratio becomes more meaningful but the **per-symbol idiosyncrasy gets
  larger relative to the herd**, which actually reduces the engine's
  edge. M2 should re-test as universe grows.
- The +15% bonus is symmetric in absolute terms but asymmetric in
  effect (because higher confidences cross the alert threshold more
  often). Worth tuning in M2.
- The cross_symbol_confluence path **runs after** the per-symbol
  `cooldown` check would otherwise live. Take care in implementation:
  the decision filter must observe the *post-confluence* confidence,
  not the pre-confluence one. The placement above (between aggregate
  and filter) handles this.
