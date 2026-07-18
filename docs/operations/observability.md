# Observability

Status: **proposed, post-M1 run** (BACKLOG P1, several sub-items).

Today's observability surface is sufficient to *survive* the 14-day run
but insufficient to *diagnose* what the system does well or badly across
that window. This document specifies the next layer.

Linked: `docs/operations/telegram_commands.md` (some observability
surfaces as bot commands).

---

## 1. What we already have

- Loguru JSON file at `data/logs/crypt.log` (rotated daily, 30 d
  retention, gz compressed).
- Tick summary log line: `Tick complete: 3/3 symbols OK, 0 partial, 0
  failed`.
- 30-min heartbeat log lines.
- 6-hour OKX health re-check.
- `data/verdicts.jsonl` with every verdict.
- Railway log viewer (7-day retention on Hobby plan).
- Disk-space guard at startup (warning if < 1 GB free).

---

## 2. Gaps we want to fill

### Gap A — Per-tick performance breakdown

Today's tick line is binary (`ok` / `partial` / `failed`). We don't see:

- Time spent in `ingest_all` vs in engine evaluation vs sink dispatch.
- Per-engine evaluation time. Cheap to add (each engine is < 50 ms in
  practice; sudden jump to 500 ms is a smell).
- Per-OKX-call latency (we silently retry behind `retry_with_backoff`,
  losing the latency signal).

Required: a `tick_metrics.jsonl` (one line per tick, separate from
verdicts.jsonl) with:

```json
{
  "tick_ts": "2026-05-15T12:00:00Z",
  "tick_duration_ms": 1432,
  "ingest_ms": 940,
  "engines_ms": 312,
  "sinks_ms": 180,
  "okx_latencies_ms": {
    "fetch_ohlcv": [45, 62, 58, 49, 51, 47, 60, 55, 53],
    "fetch_funding_history": [82, 110, 95],
    ...
  },
  "okx_retries_total": 0,
  "per_engine_ms": {"trend": 23, "meanrev": 18, ...},
  "per_engine_inputs_missing": {"trend": [], "derivatives": ["ls_ratio"]},
  "verdicts_emitted": 3,
  "alerts_fired":     1
}
```

Implementation note: use `time.perf_counter()` not `time.time()`. Log
once per tick, after `_run_engines_and_dispatch` completes.

### Gap B — Error webhook (no Sentry yet)

`Sentry` adds an external dependency we have not justified. Instead, a
zero-dep alternative:

- Add a Loguru sink that catches `ERROR`+ and POSTs to a configured
  Telegram chat (could be the same chat as alerts, or a separate
  `TELEGRAM_ERROR_CHAT_ID`).
- Rate-limit to 1 error per 60 s to avoid floods.

Once Sentry is justified by scale, swap the implementation. Until then,
this is enough.

### Gap C — Engine telemetry sample

For each tick, log at INFO one structured line per engine with its
computed indicators. Example:

```
ENGINE trend SOL  ema50=145.23  ema200=141.10  adx14=24.6  atr14=3.81  direction=bullish  strength=+0.62  conf=0.78
ENGINE meanrev SOL rsi14=48.2  bb_up=153.1  bb_low=137.4  direction=neutral  strength=0  conf=0.30
ENGINE derivatives SOL funding_z=+0.4  oi_d4h_pct=+0.012  ls_z=-0.2  strength=+0.14  conf=0.40
```

Cost: one line per (symbol × engine × tick) = 15 lines per tick. Over
14 days: 14 * 6 * 15 = 1260 lines. Negligible.

Benefit: when an alert looks wrong, the operator has the inputs in
plain text without parsing JSONL.

### Gap D — OKX rate-limit awareness

`ccxt.async_support.okx` with `enableRateLimit: True` self-throttles,
but does not expose how often. Wrap the OKX client in a thin metrics
layer:

```python
class InstrumentedOKXClient:
    def __init__(self, inner: OKXClient) -> None:
        self._inner = inner
        self._request_count = 0
        self._throttled_count = 0
    ...
```

Periodically (every heartbeat) dump:

```
OKX-stats: 124 requests since boot, 0 throttle waits, p95=92ms
```

If `throttled_count > 10` per heartbeat window, log WARNING and
consider increasing `OKX_RETRY_BASE_DELAY`.

### Gap E — Heartbeat enrichment

The heartbeat today just logs "alive at ...". Add:

- Memory RSS (`psutil` — already a transitive dep via aiogram? confirm).
- Disk free (re-use the existing guard).
- Number of open trades in paper ledger (M3 only).
- Number of alerts in the last 24h.

One log line per heartbeat. Useful both for Railway log viewer and the
data file.

---

## 3. Non-decisions (deliberately out of scope for now)

- **Prometheus / OpenTelemetry**. Adds an export endpoint + an
  agent/sidecar. No deployment target consumes this yet. **Deferred to
  M5+.**
- **Grafana dashboards**. Same reason.
- **Sentry**. Acknowledged useful, but adds an external vendor +
  account management for a 1-person project. Reconsider at M4.
- **Distributed tracing**. Single-process system. Trivially equivalent
  to structured logs.

---

## 4. Implementation order

1. Add `tick_metrics.jsonl` writing in `orchestrator.tick()` after the
   gather completes. Same JSON-lines convention as `verdicts.jsonl`.
2. Add the per-engine timing in `_run_engines_and_dispatch`.
3. Wrap OKX fetch calls with a lightweight metrics decorator
   (`@measured("fetch_ohlcv")`).
4. Add the Loguru error-webhook sink to `__main__.py`. Gate behind a
   new `TELEGRAM_ERROR_CHAT_ID` env var; if unset, skip.
5. Add the engine telemetry log lines. Behind a `LOG_TELEMETRY_LEVEL`
   env var (default `INFO`); set to `WARNING` in production if we want
   to silence them.
6. Enrich the heartbeat with memory / disk / counts.
7. Backlog: build a tiny offline `reports/tick_health.html` generator
   that ingests `tick_metrics.jsonl` and shows latency histograms.

---

## 5. Tests

`tests/runtime/test_observability.py`:

- After one synthetic tick, assert `tick_metrics.jsonl` has one line
  with the expected keys.
- Engine timing is monotonically positive.
- OKX metrics decorator increments `request_count`.
- Error webhook: simulate ERROR log, assert the test bot received one
  message; second ERROR within 60 s does NOT send.

---

## 6. Known weaknesses

- `tick_metrics.jsonl` will grow unbounded if no retention is added.
  Match Loguru's 30-day retention: a separate background coroutine
  prunes lines older than 30 days. Keep it simple — daily file rotate
  by month: `tick_metrics_2026-05.jsonl`.
- Memory measurement via `psutil` is cheap but ignores swap. Acceptable.
- Error webhook can itself fail (Telegram outage). Use the same retry
  primitive as `TelegramSink` and degrade silently — the error is
  already in the log file regardless.
- Adding the telemetry log lines will roughly 4x the file-log volume.
  Day-30-retention math: ~15 MB / day → 450 MB / month. Within
  Railway's 5 GB volume budget but worth keeping an eye.
