# ADR-0011: Thresholds rationale and `[UNCALIBRATED]` marker policy

- **Status**: superseded by ADR-0020 for `ALERT_CONFIDENCE_THRESHOLD = 75`
  rationale; accepted for the `[UNCALIBRATED]` marker policy
- **Date**: 2026-05-15
- **Owner**: agent

## Context

Throughout the codebase and configuration, several numeric thresholds
shape the behaviour of the system:

- `ALERT_CONFIDENCE_THRESHOLD = 75` — minimum verdict confidence to fire
  a Telegram alert.
- Per-regime decision thresholds in `config/weights.yaml`:
  `TRENDING: 0.25 | RANGING: 0.30 | HIGH_VOL: 0.45`.
- Per-regime engine weights in `config/weights.yaml`.
- Per-engine internal thresholds: ADX gate `18` / `22` / `25`; RSI
  `30`/`70`; funding z-score gate `3σ`; OI `5%` step; LS-ratio `3σ`.

All of these were chosen as **plausible defaults**, not derived from
historical data. None has been backtested. The owner, reading a Telegram
alert with "Confidence: 78%", currently has no signal that this 78% is
not yet a calibrated probability.

This creates two related risks:

1. **Trust risk** — the owner may start trading on uncalibrated signals
   during the 14-day continuous run before M2 has produced weights.
2. **Documentation risk** — future agents may reasonably assume the
   numbers are intentional and refuse to change them.

This ADR exists to make both explicit.

## Decision

### Part A — Threshold rationale (placeholder values, explicitly)

The thresholds listed below are placeholders, recorded here so future
agents understand the reasoning *and* know they are free to recalibrate
in M2.

- `ALERT_CONFIDENCE_THRESHOLD = 75`. Rationale: we wanted a default
  that's high enough to fire roughly 1–3 alerts per symbol per day at
  4h cadence, low enough that the operator gets meaningful volume during
  the 14-day calibration window. Empirically, with placeholder weights
  and the engines as specified, this number happens to fire ~25% of
  ticks.
- Per-regime thresholds. Rationale:
  - `TRENDING: 0.25` — trends emit consistent same-direction signals
    from multiple engines; lower threshold trades off precision for
    recall (we are happy to fire often during a clear trend).
  - `RANGING: 0.30` — meanrev is a noisier engine, so we require a
    slightly larger score before alerting.
  - `HIGH_VOL: 0.45` — slippage and noise are large; only act on
    consensus.
- Engine internal thresholds (`ADX 18/22/25`, `RSI 30/70`, `funding z`
  `3σ`, `OI 5%`) — textbook values chosen for interpretability. The
  engine specs (`docs/engines/*.md`) document them.

**None of the above has been tested against history.** M2 must
recalibrate weights and thresholds together; an ADR-XXXX will be
written when calibrated values are committed to `config/weights.yaml`.

### Part B — `[UNCALIBRATED]` marker policy

Until M2 produces a calibrated `weights.yaml` and an ADR ratifies it,
every Telegram alert must carry an explicit marker so the operator
cannot reasonably forget the signals are not yet trustworthy.

Marker format (added in `TelegramSink._format_message`):

```
🟢 SOL-USDT-SWAP — BUY ⚠️ [UNCALIBRATED]
Confidence: 78%   Score: +0.412
Regime: TRENDING

<rationale>
```

The `[UNCALIBRATED]` tag is **removed** only when:

1. `config/weights.yaml` has been replaced by an output of the M2 backtest
   harness (see `docs/backtest.md`).
2. An ADR (call it ADR-0013 or later) records the M2 calibration:
   dataset window, backtest report path, weight values, expectancy and
   CI.
3. A code change in `TelegramSink` flips the marker off (a flag in
   `Settings`, default `False` post-calibration).

A `Settings.uncalibrated: bool = True` field, defaulting to `True`, is
the on/off switch. The agent who completes M2 calibration must:

- Toggle the default to `False` in code.
- Add a unit test that asserts the marker is present when the flag is
  `True` and absent when `False`.

## Alternatives considered

### Burying the warning in the README only

Pro: zero code change.
Con: the operator does not read the README every time a verdict fires;
the marker has to be in the message itself. **Rejected.**

### Suppressing alerts entirely until calibration

Pro: fully eliminates the trust risk.
Con: the 14-day run is precisely the dataset M2 will use. If we
suppress all alerts during this window we don't get to observe the
system's behaviour at scale; the operator also loses the muscle memory
of seeing alerts arrive. **Rejected.**

### Per-engine `[UNCALIBRATED:engine]` tags in rationale

Pro: more granular.
Con: visual noise in the Telegram message. The single tag at the top
already signals "do not trade on these yet". **Rejected.**

## Consequences

### Positive
- Operator cannot mistake placeholder confidence for calibrated
  probability.
- Future agents have one ADR to point at when explaining why specific
  numbers exist and that they are negotiable.
- Removing the marker becomes a deliberate, ADR-gated step rather than
  drift.

### Negative
- The Telegram message gets one extra line. Minor.
- The `uncalibrated` flag is a global on/off and does not differentiate
  between "engine weights calibrated but new sentiment engine not yet"
  and "everything calibrated". This is fine for MVP; a richer scheme
  can come in a later ADR if needed.

### To revisit later
- After M2: write the calibration ADR and flip the flag.
- After M3 paper trading: consider per-engine markers (e.g.
  `[UNCALIBRATED: sentiment]`) when one engine has been retro-fitted
  but the rest are settled.

## References

- `docs/engines/aggregator.md` (existing threshold definitions).
- `docs/backtest.md` (M2 calibration spec).
- `config/weights.yaml` (current placeholder values).
- `src/crypt/sinks/telegram.py` (where the marker must be added).
- `src/crypt/config.py` (where the `uncalibrated` flag must be added).
