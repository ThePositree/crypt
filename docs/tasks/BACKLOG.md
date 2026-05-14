# Backlog

Prioritised list of concrete items. Priority labels:

- **P0** — blocker, must do before MVP can run.
- **P1** — important, MVP feels incomplete without it.
- **P2** — nice-to-have, post-MVP.

Items move from here → `IN_PROGRESS.md` when work starts → `DONE.md` when
finished.

---

## P0 — needed for MVP wiring

- [x] `pyproject.toml` and `uv` project setup — done.
- [x] `src/crypt/config.py` — done.
- [x] `src/crypt/models.py` — done.
- [x] `src/crypt/exchange/base.py` + `okx.py` — done.
- [x] `src/crypt/data/store.py` + `ingestor.py` + `context.py` — done.
- [x] `src/crypt/engines/` — all five engines done.
- [x] `src/crypt/aggregator/` — done.
- [x] `src/crypt/decision/filters.py` — done.
- [x] `src/crypt/sinks/` — done.
- [x] `src/crypt/runtime/` + `__main__.py` — done.
- [x] Per-engine unit tests (42 tests) — done.
- [x] **Verify `XPL-USDT-SWAP` on OKX** — confirmed present.
- [x] **Smoke-test against OKX live API** — passes cleanly, all 3 symbols produce verdicts.
- [x] **mypy clean pass** — 0 errors in 34 source files.

## P1 — MVP polish

- [x] Initial `weights.yaml` — placeholder values, to be overwritten by M2.
- [x] Bootstrap: `Orchestrator.bootstrap()` calls `ingest_all()` on cold start.
- [x] Graceful shutdown on `SIGTERM` / `SIGINT` — in `__main__.py`.
- [x] Health-check helper that proves OKX connectivity and Telegram works.
- [x] Logging configuration (loguru): file + stdout, JSON in file.
      (`logs/` dir created at startup; file sink with `serialize=True`).

## P0 — reliability hardening before 14-day run

These items must be done before starting the continuous 14-day run.
Motivation: without them a transient OKX API blip, a hung connection, or a
single Python crash can silently end the run in hours, not days.

- [x] **`src/crypt/utils/retry.py`** — done.
- [x] **ccxt request timeout** — done (`"timeout": 30_000`).
- [x] **Log discarded exceptions from `gather(return_exceptions=True)`** — done.
- [x] **systemd unit file** — `deploy/crypt.service` created; README updated.

## P1 — reliability polish (do before or shortly after starting the run)

- [x] **Jitter in Telegram backoff** — done.
- [x] **Daily log rotation** — done (`rotation="00:00"`, `compression="gz"`).
- [x] **Heartbeat task** — done (30-min background loop).
- [x] **Periodic OKX health check** — done (every 6 h inside heartbeat).
- [x] **Disk-space guard on startup** — done (< 1 GB → WARNING).

## P1 — M2 backtest harness

- [ ] `src/crypt/backtest/replay.py` — feeds historical Parquet into the
      same `EvaluationContext` builder.
- [ ] `src/crypt/backtest/report.py` — per-engine hit rate, ensemble
      expectancy, drawdown, regime breakdown.
- [ ] CLI: `uv run python -m crypt.backtest --from 2025-01-01 --to 2026-05-01`.

## P2 — nice-to-have reliability

- [x] **Retry/backoff params in `Settings`** — done (`OKX_MAX_RETRIES`,
  `OKX_RETRY_BASE_DELAY`, `OKX_RETRY_MAX_DELAY` in `config.py` + `.env.example`).

- [x] **Tick summary log line** — done.

## P2 — later

- [ ] Sentiment engine (CryptoPanic freemium).
- [ ] Liquidation collector (background WS process) + engine.
- [ ] ML meta-aggregator (LightGBM on engine outputs).
- [ ] Streamlit dashboard.
- [ ] Docker compose for the eventual VPS deployment.
- [ ] Prometheus metrics + Grafana.

## Known unknowns

- OKX long/short ratio history retention — docs mention "data time range is
  up to March 22, 2024", which may be either an "available since" or
  "available until" statement. Confirm at implementation time.
- `XPL-USDT-SWAP` exists on OKX — to be verified before fetch.
