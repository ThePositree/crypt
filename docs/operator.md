# Operator runbook

For the human reading Telegram alerts and (optionally) taking trades by
hand. This file is owner-facing; agents update it whenever new
operator-visible behaviour is added.

Linked documents:
- `docs/decisions/0011-thresholds-rationale-and-uncalibrated-marker.md`
  — why the `[UNCALIBRATED]` tag exists and when it goes away.
- `docs/paper_trading.md` — the parallel ledger that records "what would
  have happened".
- `docs/operations/telegram_commands.md` — the bot commands you can use.

---

## 1. What you actually see

A Telegram message like this:

```
🟢 SOL-USDT-SWAP — BUY ⚠️ [UNCALIBRATED]
Confidence: 78%   Score: +0.412
Regime: TRENDING

trend:       bullish  strength=+0.62  weight=0.55
meanrev:     neutral  strength= 0.00  weight=0.05
derivatives: bullish  strength=+0.31  weight=0.30
volatility:  vol_regime=normal
regime:      TRENDING (ADX_h4=24, ADX_d1=22)
```

Anatomy:
- Emoji + symbol + decision in the first line.
- `[UNCALIBRATED]` tag is present until M2 calibration is shipped and
  ADR-0011's flag flips off. Treat alerts as **informational** during
  this period. Do not size trades to them yet.
- `Confidence` — 0..100. Below 75 alerts are suppressed (default
  placeholder threshold); a 78 only means it passed the current alert gate,
  not that it is a calibrated probability.
- `Score` — weighted-sum across engines, in `[-1, +1]`. The sign matches
  the decision.
- `Regime` — `TRENDING / RANGING / HIGH_VOL`. Decides which weight set
  the aggregator used.
- Per-engine breakdown: which trader views agreed, with what strength
  and weight.

---

## 2. Red flags — do not trade these even when calibrated

- **`[UNCALIBRATED]` is still on the message.** The numbers are not yet
  validated against history.
- **`Regime: HIGH_VOL`** and confidence only barely above the current alert
  gate. The threshold is still a placeholder, and HIGH_VOL alerts have not
  been validated.
- **One engine alone is doing the work** (e.g. only `derivatives:
  strength=+0.9, weight=0.3` while trend and meanrev are neutral) —
  single-engine alerts have not been validated to be useful.
- **`inputs_missing` present in any engine breakdown.** The system is
  flying partially blind.
- **Two consecutive alerts with opposite direction within < 8h** (BUY
  then SELL or vice versa). A whipsaw period — the regime detector is
  probably mid-transition. Sit it out.
- **The system has just restarted** (check Telegram for the previous
  heartbeat; if heartbeats stopped briefly and the alert is on the
  first tick after restart, treat the alert with extra suspicion).

---

## 3. Green flags — a "good" alert profile

- `Confidence ≥ 80` *and* the breakdown shows **≥ 2 engines agree** on
  direction with non-trivial strength.
- `Regime: TRENDING` for `BUY` / `SELL` *and* the direction matches the
  trend regime (i.e. you are not fighting a trend with mean-reversion).
- `Regime: RANGING` for a `meanrev`-dominated `SELL` near a known
  resistance (visually corroborated on chart).
- No `inputs_missing`.

---

## 4. Standard recipe (post-calibration)

(Don't use this until `[UNCALIBRATED]` is gone.)

1. **Sizing**: risk no more than 0.5% of account per trade. Calculate
   the unit size from `ATR(14, H4)` once you know which symbol.
2. **Entry**: market order, accepting up to 0.05% slippage. If price
   is already > 0.3% past where the alert fired, **skip the alert** —
   the move you would chase is the move the system reacted to.
3. **Stop loss**: `entry ± 2 * ATR(14, H4)`.
4. **Take profit**: `entry ± 3 * ATR(14, H4)`.
5. **Timeout**: if neither SL nor TP is hit in 7 days, close at market.
6. **Direction flip alert** for the same symbol arrives while you have
   an open position: close the existing position, open the new one. Do
   not hedge.

These match the paper-ledger logic in `docs/paper_trading.md` exactly,
so paper performance is directly comparable to what you actually did.

---

## 5. Recording your trades

Use the Telegram bot to record what you actually did:

```
/trade SOL long 145.30        # opens
/close SOL 161.00 tp           # closes
```

(See `docs/operations/telegram_commands.md` for the full command set
once it is implemented.)

The owner ledger sits alongside the paper ledger. Discrepancies between
the two are the most informative signal we will get for M4 design.

---

## 6. When something goes wrong

### "Heartbeats stopped"
If you stop seeing the 30-minute `Heartbeat: alive at …` line on
Telegram (or in Railway logs), the process is hung or dead. Steps:
1. Check Railway dashboard → service → status. If status is "deployed"
   but no heartbeats, the loop hung. Restart the service from the
   dashboard.
2. If Railway shows the service stopped/crashed and restart policy
   didn't recover it, check the deploy logs for the last error and
   open a chat with an agent to triage.

### "Telegram alert never arrives"
1. `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` set correctly? Test with
   `/health` Telegram command.
2. `ALERT_CONFIDENCE_THRESHOLD` higher than 75? Confidence might not
   pass.
3. JSON log (`data/verdicts.jsonl`) shows a `BUY`/`SELL` with
   `"alerted": false`? Cooldown or guard suppressed it. The reason is
   in the log line.

### "All alerts say HIGH_VOL and low confidence"
We are in a turbulent market. Sit out. This is the intended behaviour.

### "OKX API down"
The retry logic should ride through transient outages. If retries
exhaust, you'll see `OKX connectivity check failed: …` in logs and the
tick continues with cached data, producing `inputs_missing` flags.
Severe outages mean a tick may be skipped entirely; that's fine.

---

## 7. Daily / weekly routine

### Daily
- Glance at the day's verdicts in Telegram. If you took any trade,
  record it (`/trade …`).
- If `[UNCALIBRATED]` is still on: write nothing in the trade ledger
  yet — keep an eye, do not trade.

### Weekly
- Skim Railway logs for `WARNING`/`ERROR` patterns. A handful per week
  is normal; a flood is not.
- Eyeball `data/verdicts.jsonl` (or download via `railway ssh` per the
  deploy guide) — does the regime mix look sane?
- Note any time the system "got it wrong" in obvious ways — these
  observations are what M3 paper-trading analysis exists for.

### End of the 14-day run
Follow `docs/deploy/railway.md` Step 7 to extract data and logs. After
that, the next agent works on M2 backtest.

---

## 8. Escalation

If something breaks that this runbook does not cover:

1. Open a new chat session.
2. Paste the failing log line(s) verbatim.
3. The agent will follow the AGENTS.md incident workflow (reproduce,
   minimal fix, document).

Do **not** edit code yourself unless you want a chat session afterwards
to walk through what changed — agents own the code and the docs, you
own the strategic direction and the trades.
