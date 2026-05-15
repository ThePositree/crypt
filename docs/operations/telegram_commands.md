# Telegram bot commands

Status: **proposed, post-M1 run** (BACKLOG P1).

A small command surface on the existing Telegram bot. The bot already
sends alerts (one-way). This spec extends it to a two-way interaction so
the owner can query state and record trades without leaving the chat.

Implementation note: aiogram 3.x supports `Dispatcher` + handlers
naturally. The current code uses only `Bot.send_message`. To accept
incoming commands, we need a long-poll `Dispatcher` running in a
background task on the existing event loop (no webhooks — Railway free
plan does not give a stable inbound URL anyway).

---

## 1. Authorisation

Only `TELEGRAM_CHAT_ID` is allowed to issue commands. Every other
`chat.id` is silently ignored (no error reply — we are not advertising
the bot).

```python
@dp.message(F.text.startswith("/"))
async def _gate(msg: Message) -> None:
    if str(msg.chat.id) != settings.telegram_chat_id:
        return
    ...
```

A new env var `TELEGRAM_ADMIN_CHAT_IDS: list[str] = []` allows
multiple authorised IDs (useful for an audit reader account). If empty,
fall back to the single `telegram_chat_id`.

---

## 2. Command set (MVP)

Every command echoes a short result back to the same chat.

### `/status`

Replies with:
- Process uptime.
- Last 5 ticks' summary (`ok/partial/failed` counts).
- Configured symbols.
- Current regime per symbol (latest verdict).
- Current alert threshold + cooldown.

Example reply:
```
crypt — up 3d 7h 12m
Last tick: 2026-05-15 12:00:00Z — 3/3 OK
Symbols: SOL TON XPL
Regime: SOL=TRENDING, TON=RANGING, XPL=HIGH_VOL
Threshold: 75   Cooldown: 4h
```

### `/last [N]`

Replies with the last `N` verdicts (default `N=5`, max `N=20`) for all
symbols, newest first. Each verdict on one line:

```
2026-05-15 12:00Z  SOL  BUY  conf=78  score=+0.41  alerted=yes
2026-05-15 12:00Z  TON  HOLD conf=42  score=-0.12  alerted=no
...
```

Reads from `data/verdicts.jsonl` (tail-N parse).

### `/explain <symbol>`

Replies with the full rationale of the **latest** verdict for the
symbol. Same content as the alert message, but always returned (no
threshold / cooldown gate).

Useful when a verdict was logged but no Telegram alert fired and the
owner wants to know why.

### `/health`

Runs the on-startup health check inline (`run_health_check`) and reports
the result. Useful when the owner suspects OKX or Telegram connectivity
issues without redeploying.

### `/threshold <0-100>`

Runtime override of `ALERT_CONFIDENCE_THRESHOLD` for the current process
only (not persisted — env var still wins on restart). Confirms with:

```
Threshold set to 80 (was 75). Effective until next restart.
```

### `/pause [duration]` / `/resume`

`/pause 4h` — suppress all alerts for the given duration (parse a small
range of units: `15m`, `4h`, `1d`). Persisted in `data/state.json` so
restarts honour it.

`/resume` — clear any pause.

Sinks other than Telegram continue normally; only Telegram is gagged.
This is the safe operator switch when "the system is going haywire" and
they don't want a flood while debugging.

### `/help`

Lists all commands with one-line descriptions. Generated from the
docstrings, not hard-coded.

---

## 3. Paper-ledger commands (M3 era)

These commands appear only after `PaperLedgerSink` is wired up (see
`docs/paper_trading.md`).

### `/trade <SYMBOL> <long|short> <entry_price> [size]`

Records the owner's actual trade into `data/owner_ledger.jsonl`.
`size` defaults to `1` (unit).

```
/trade SOL long 145.30
```

Reply:
```
Recorded owner trade trade_id=abc123: SOL long @ 145.30
```

### `/close <SYMBOL|trade_id> <exit_price> <reason>`

Closes the most recent open owner trade for the symbol (or the explicit
`trade_id`).

```
/close SOL 161.00 tp
```

Reasons: `tp | sl | timeout | manual_close`.

### `/positions`

Lists owner's open positions (from `owner_ledger.jsonl`).

### `/pnl [period]`

Aggregate P&L over the period (`7d`, `30d`, `all`). Pulls from paper
ledger by default; `/pnl owner 30d` switches to owner ledger.

---

## 4. Implementation guidance

- The dispatcher runs in a background task started by `__main__.py`
  inside the same event loop as the orchestrator. It must not block
  `tick()`.
- All command handlers must complete in < 5 s. If a handler needs to
  hit OKX (e.g. `/health`), wrap it in `asyncio.wait_for` so a hung
  network does not freeze the bot.
- All replies must be `<` 4000 chars (Telegram limit). For `/last 50`
  that means paginating or trimming.
- Use `aiogram.utils.markdown` helpers for safe HTML escaping; user
  trade prices come from chat input.
- Store all command-driven state changes through a `BotState` Pydantic
  model serialised to `data/state.json`. This is the **one** state file;
  resist scattering `pause.txt`, `threshold.txt`, etc.

---

## 5. Tests

`tests/sinks/test_telegram_commands.py`:

- Auth gate: command from non-admin chat → handler short-circuits, no
  call to the data layer.
- `/status` happy path with synthetic verdicts file.
- `/last 5` returns last 5 verdicts in newest-first order.
- `/threshold 80` mutates state; subsequent `/status` shows the new
  threshold.
- `/pause 30m` followed by an alert attempt → alert suppressed (mock
  TelegramSink); `/resume` restores.
- Unknown command → `/help` is replied.

Mock the bot via aiogram's test helpers; do not hit Telegram in tests.

---

## 6. Known weaknesses

- Long polling on Railway free plan costs nothing but adds a steady
  HTTPS connection. Confirmed acceptable (< 1 MB/day egress).
- We give the owner runtime knobs (`/threshold`, `/pause`) that
  override persisted config. This can drift from `.env` and confuse
  future agents. Mitigation: every override is logged at WARNING with
  the current value, and `data/state.json` is mentioned in the runbook.
- aiogram updates regularly break minor APIs (e.g. the 3.7.0
  `Bot.__init__` change we just patched). Pin a tested minor and lock
  the upgrade behind an explicit test step.
- Telegram has a 30 msg/sec global rate limit for a bot. We are far
  below it, but the implementation should still serialise replies (the
  default aiogram dispatcher does this).
