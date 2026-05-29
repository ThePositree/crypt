# Post-mortem: M1 14-day continuous run summary

- **Date (UTC)**: 2026-05-15 → 2026-05-29
- **Severity**: P3 (latent risks discovered; no incidents)
- **Author(s)**: agent
- **Status**: resolved

## Summary

M1 ran for 14 continuous days on Railway (2026-05-15T10:04 → 2026-05-29T08:02 UTC)
without a single crash, error, or missed tick. All 255 verdict records are intact.
Zero Telegram alerts fired: max observed confidence was 52% against a 75% threshold,
confirming that the current placeholder weights under-produce high-confidence signals.
The Parquet data store is healthy (7 files × 3 symbols, all present). The run
satisfies the M1 exit criterion and clears the path to M2.

## Timeline (UTC)

- `2026-05-15 10:04` — process started on Railway; bootstrap complete in 10 s.
- `2026-05-15 10:04` — first tick executed; all 3 symbols evaluated.
- `2026-05-16 00:02` — first daily log rotation (all subsequent days identical).
- `2026-05-15 → 2026-05-29` — 82 full days of ticks (6/day per symbol); zero errors.
- `2026-05-29 08:02` — last observed tick at review time (run still active as of
  review).

## Impact

- Ticks missed: **0** (first day started at 10:04 UTC so had 4 ticks instead of 6;
  today's day is partial — expected).
- Verdicts wrong / suppressed: **0** known issues.
- Alerts mis-fired: **0**.
- Data lost or corrupted: **0**.
- Owner trades affected: none (no alerts fired).
- Time spent on response: review only.

## Statistics

### Tick completeness

| Symbol | Total ticks | Full days (6/day) | Partial days |
|---|---|---|---|
| SOL-USDT-SWAP | 85 | 13 | 2 (start + today) |
| TON-USDT-SWAP | 85 | 13 | 2 (start + today) |
| XPL-USDT-SWAP | 85 | 13 | 2 (start + today) |

### Decision distribution

| Symbol | BUY | SELL | HOLD | Max conf | Avg conf | Alerts |
|---|---|---|---|---|---|---|
| SOL-USDT-SWAP | 18 | 4 | 63 | 52% | 27.5% | 0 |
| TON-USDT-SWAP | 72 | 0 | 13 | 50% | 37.4% | 0 |
| XPL-USDT-SWAP | 0 | 1 | 84 | 31% | 17.4% | 0 |

### Regime distribution

| Symbol | TRENDING | RANGING | HIGH_VOL |
|---|---|---|---|
| SOL-USDT-SWAP | 47% | 49% | 4% |
| TON-USDT-SWAP | 86% | 14% | 0% |
| XPL-USDT-SWAP | 0% | 88% | 12% |

## Observations

### No alerts fired

The 75% confidence threshold was never reached. Max confidence across all 255 verdicts
was 52% (SOL-USDT-SWAP, 2026-05-16T12:02Z, BUY, TRENDING). This is a direct
consequence of placeholder engine weights that were not derived from historical data —
confirmed by ADR-0011, which explicitly recorded this risk.

The closest sequences to threshold:

- **TON-USDT-SWAP BUY streak (2026-05-24 → 2026-05-25)**: 7 consecutive ticks at
  confidence 50%, score 0.6–0.8. The trend engine and derivatives engine agreed
  strongly but the confidences were each capped at 0.5 (derivatives engine) and
  0.5 (trend engine in TRENDING regime with ADX just at the lower band). Under
  calibrated weights, this sequence would likely have produced alerts.

- **SOL-USDT-SWAP SELL pair (2026-05-29T00:02 + 04:02Z)**: both at 50%, score
  −0.31 to −0.33. The last two ticks before review. Suggestive of a trend change
  not yet strong enough to clear the threshold.

### XPL-USDT-SWAP is silent

XPL had HOLD on 84/85 ticks with max conf 31%. This is entirely explained by
XPL being a young instrument: the trend engine fired `ADX14 below threshold`
on nearly every tick (ADX historically low, insufficient bars for EMA200), and
the regime engine classified it as RANGING/HIGH_VOL throughout. This matches
the known XPL bootstrapping risk documented in `docs/post_m1_code_fixes.md` §6
— the symptom is latent but not a bug. The fix is a better `bootstrapping`
classification in the tick summary log (P1).

### Log hygiene

All 14 archived log files (`.log.gz`) are clean — zero ERROR, WARNING, or
CRITICAL log lines. The heartbeat / disk-space guard and OKX connectivity check
produced only INFO lines. Log rotation at 00:02 UTC worked correctly every day.

### Parquet data

All 21 Parquet files present and non-empty. Sizes are in the expected range
(5–32 KB). The store is ready to serve as M2 backtest input after backfill.

## What went well

- Zero crashes across 14 days and ~255 ticks.
- Daily log rotation ran on schedule without intervention.
- All three OKX data fetch paths (OHLCV, funding, OI, LS-ratio, taker vol)
  succeeded on every tick.
- Pydantic models caught no validation errors in 14 days of live data.
- The retry / backoff layer was never exercised (OKX was stable throughout).
- Disk-space guard fired INFO on first tick (4.5 GB free); never a warning.

## What went badly

- **Zero alerts** despite a clearly bullish TON run (24–25 May). With calibrated
  weights this would very likely have fired. The operator missed potential signal
  value during the calibration window — the exact risk ADR-0011 warned about.
- **No `[UNCALIBRATED]` marker in alerts**: the feature was designed but not
  shipped before the run started (Railway no-push rule during run). A non-issue
  since no alerts fired, but would have been a gap if threshold had been lower.
- **No Telegram introspection commands** (`/status`, `/last`, `/health`): the
  operator had no way to query system state without reading logs manually.
  Only noticed post-run.

## What we didn't know at the time

- Whether the 75% confidence threshold was too conservative for uncalibrated
  weights (answer: yes, apparently).
- Whether OKX would stay stable for 14 days (it did — no rate-limit errors, no
  endpoint changes).
- Whether Railway's persistent volume would survive the full run without
  filesystem issues (it did).

## Corrective actions

| # | Action | Owner | Priority | Target |
|---|--------|-------|----------|--------|
| 1 | Ship `[UNCALIBRATED]` marker in TelegramSink | next agent | P0 | now |
| 2 | Implement GitHub Actions CI + pre-commit hooks | next agent | P0 | now |
| 3 | Closed-candle invariant fix + test | next agent | P0 | now |
| 4 | Critical-inputs guard refactor | next agent | P0 | now |
| 5 | XPL bootstrapping classification in tick log | next agent | P1 | M2 |
| 6 | Telegram bot commands (`/status`, `/last`, `/health`) | future agent | P1 | M2 |
| 7 | Start M2 backtest harness (backfill CLI first) | next agent | P1 | M2 |

## Permanent fix vs band-aid

All corrective actions above are permanent fixes, not band-aids. The M2 calibration
will be the structural solution to the no-alerts problem.

## Lessons

Placeholder weights that underfire are preferable to placeholder weights that
overfire — the operator did not act on uncalibrated signals. But the 14-day window
is valuable training data only if M2 is started promptly; delay means more
unalerted signal value lost.

## Related

- ADR-0010 (Railway deployment — no-push rule during run)
- ADR-0011 (uncalibrated marker policy)
- `docs/post_m1_code_fixes.md`
- `docs/backtest.md` (M2 spec)
- `docs/tasks/BACKLOG.md`
