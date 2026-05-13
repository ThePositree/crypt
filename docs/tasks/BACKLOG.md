# Backlog

Prioritised list of concrete items. Priority labels:

- **P0** — blocker, must do before MVP can run.
- **P1** — important, MVP feels incomplete without it.
- **P2** — nice-to-have, post-MVP.

Items move from here → `IN_PROGRESS.md` when work starts → `DONE.md` when
finished.

---

## P0 — needed for MVP wiring

- [ ] `pyproject.toml` and `uv` project setup with deps pinned to latest
      compatible majors (`ccxt`, `pandas`, `pandas-ta`, `pydantic`,
      `pydantic-settings`, `APScheduler`, `aiogram`, `loguru`, `pytest`,
      `ruff`, `mypy`, `pyarrow`).
- [ ] `src/crypt/config.py` — `pydantic-settings` loading `.env` + optional
      YAML weights config.
- [ ] `src/crypt/models.py` — `Candle`, `FundingSnapshot`, `OISnapshot`,
      `LongShortRatioSnapshot`, `TakerVolumeSnapshot`, `Regime`, `Signal`,
      `Verdict`.
- [ ] `src/crypt/exchange/base.py` — `ExchangeClient` Protocol.
- [ ] `src/crypt/exchange/okx.py` — OKX implementation via `ccxt`.
      Includes the implicit `rubik/stat` endpoints for long/short ratio and
      taker volume (ccxt does not expose these as unified methods).
- [ ] `src/crypt/data/store.py` — Parquet read/write per `data/<symbol>/`.
- [ ] `src/crypt/data/ingestor.py` — schedulable pull jobs per data type.
- [ ] `src/crypt/data/context.py` — build `EvaluationContext` from the store.
- [ ] `src/crypt/engines/base.py` — `BaseEngine` ABC with `evaluate(ctx)`.
- [ ] `src/crypt/engines/trend.py` — see `docs/engines/trend.md`.
- [ ] `src/crypt/engines/meanrev.py` — see `docs/engines/meanrev.md`.
- [ ] `src/crypt/engines/derivatives.py` — see `docs/engines/derivatives.md`.
- [ ] `src/crypt/engines/volatility.py` — see `docs/engines/volatility.md`.
- [ ] `src/crypt/engines/regime.py` — see `docs/engines/regime.md`.
- [ ] `src/crypt/aggregator/weights.py` + `ensemble.py` — see
      `docs/engines/aggregator.md`.
- [ ] `src/crypt/decision/filters.py` — confidence threshold + cooldown.
- [ ] `src/crypt/sinks/{telegram,jsonlog,console,execution_stub}.py`.
- [ ] `src/crypt/runtime/{scheduler,orchestrator}.py`.
- [ ] `src/crypt/__main__.py` — CLI: `uv run python -m crypt --symbols ...`.
- [ ] Per-engine synthetic-data unit tests under `tests/engines/`.
- [ ] Verify `XPL-USDT-SWAP` is a real OKX SWAP instrument; if not, ask
      owner for a replacement.

## P1 — MVP polish

- [ ] Initial `weights.yaml` — placeholder values, to be overwritten by M2.
- [ ] First-run bootstrap script: fetches the last ≥ 200 H4 candles per
      symbol on cold start so indicators have warm-up data.
- [ ] Graceful shutdown on `SIGTERM` / `SIGINT`.
- [ ] Health-check helper that proves OKX connectivity and Telegram works.
- [ ] Logging configuration (loguru): file + stdout, JSON in file.

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
