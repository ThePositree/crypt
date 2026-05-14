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
- [ ] **Verify `XPL-USDT-SWAP` on OKX** — needs live network test.
- [ ] **Smoke-test against OKX live API** — run `--once`, check console output.
- [ ] **mypy clean pass** — run `uv run mypy src/` and fix type errors.

## P1 — MVP polish

- [x] Initial `weights.yaml` — placeholder values, to be overwritten by M2.
- [x] Bootstrap: `Orchestrator.bootstrap()` calls `ingest_all()` on cold start.
- [x] Graceful shutdown on `SIGTERM` / `SIGINT` — in `__main__.py`.
- [ ] Health-check helper that proves OKX connectivity and Telegram works.
- [ ] Logging configuration (loguru): file + stdout, JSON in file.
      (`__main__.py` has basic setup; needs the file sink wired up).

## P1 — M2 backtest harness

- [ ] `src/crypt/backtest/replay.py` — feeds historical Parquet into the
      same `EvaluationContext` builder.
- [ ] `src/crypt/backtest/report.py` — per-engine hit rate, ensemble
      expectancy, drawdown, regime breakdown.
- [ ] CLI: `uv run python -m crypt.backtest --from 2025-01-01 --to 2026-05-01`.

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
