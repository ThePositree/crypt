# crypt

Modular ensemble decision system for crypto perpetual futures markets.

> Continuously monitors a small basket of OKX perpetual contracts, runs several
> independent "trader views" (trend, mean-reversion, derivatives positioning,
> volatility regime, ...), aggregates them into a single weighted verdict
> (`BUY` / `SELL` / `HOLD` + confidence + rationale) and pushes alerts to
> Telegram.
>
> Goal of v1: signal generation for the owner to trade manually.
> Goal of vN: automated execution once the signal track-record is proven.

This is **not** a trading bot. It is a research-and-alerting system.

## Status

**M1 ready for 14-day continuous run.**
All engines, aggregator, decision layer, sinks, and runtime are implemented,
tested, and hardened. Reliability features complete: retry with backoff on all
OKX fetch calls, 30 s ccxt timeout, heartbeat loop, daily log rotation, systemd
unit, disk-space guard, and tick summary logging.

42 synthetic-data unit tests pass; mypy 0 errors (36 files); ruff clean.

**Owner action required:**
1. Fill `.env` with `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID`.
2. Run `uv run python -m crypt --once` — confirm Telegram alert arrives.
3. Start continuous run (see "Running as a service" below or quick-start).

See `docs/tasks/ROADMAP.md` for milestones and `docs/tasks/IN_PROGRESS.md` for
next steps.

## Stack

- Python 3.11+
- [`ccxt`](https://github.com/ccxt/ccxt) — OKX market data (REST)
- `pandas` + `pandas-ta` — indicators
- `pydantic` v2 + `pydantic-settings` — typed config
- `APScheduler` — periodic 4h-aligned loop
- `aiogram` — Telegram alerts
- `loguru` — logging
- `pytest` — tests
- `ruff` + `mypy` — lint / type check
- `uv` — package manager

No database, no Redis, no Docker in MVP.

## How it is developed

This repository is built **AI-first**. The owner sets global goals in chat;
agents own implementation planning, scaffolding and documentation.

Anyone (human or agent) contributing should first read:

1. `AGENTS.md`
2. `.cursor/rules/ai-first-workflow.mdc`
3. `docs/tasks/IN_PROGRESS.md`
4. `docs/tasks/ROADMAP.md`
5. The most recent entries in `CHANGELOG.md`

## Quick start

```bash
uv sync --all-extras
cp .env.example .env   # fill TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID

# One-shot tick (bootstrap + evaluate once, no scheduler):
uv run python -m crypt --once

# Live loop (runs every 4h):
uv run python -m crypt

# Custom symbols:
uv run python -m crypt --symbols SOL-USDT-SWAP,TON-USDT-SWAP
```

## Running as a service

The `deploy/crypt.service` systemd unit runs the process under your user account
with automatic restart on crash.

```bash
# Install (adjust User/WorkingDirectory paths inside the file first if needed)
sudo cp deploy/crypt.service /etc/systemd/system/crypt.service
sudo systemctl daemon-reload
sudo systemctl enable --now crypt

# Check status / live logs
systemctl status crypt
journalctl -u crypt -f
```

The unit sets `Restart=always` with a 10-second cool-down, so a Python crash or
OOM kill will automatically restart the process within 10 seconds.

## Layout

```
crypt/
├── AGENTS.md                # agent operating manual
├── CHANGELOG.md             # session-by-session log
├── README.md                # this file
├── .cursor/rules/           # always-on rules for AI agents
├── docs/
│   ├── architecture.md      # high-level design
│   ├── decisions/           # ADRs (one decision per file)
│   ├── engines/             # per-engine specs (signal contracts, logic, thresholds)
│   └── tasks/               # ROADMAP / BACKLOG / IN_PROGRESS / DONE
├── src/crypt/               # source
└── tests/                   # pytest
```

## License

Private. No license granted.
