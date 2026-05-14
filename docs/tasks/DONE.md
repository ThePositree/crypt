# Done

Reverse-chronological archive of completed work. Newest on top.

---

## 2026-05-14 — M1 code layer

Implemented the full M1 pipeline. All 42 synthetic-data unit tests pass;
`ruff` reports no errors.

### What was built

- **`pyproject.toml`** — `requires-python` updated to `>=3.12` (pandas-ta
  constraint); `uv sync` run; `uv.lock` generated.
- **`src/crypt/config.py`** — `pydantic-settings` `Settings` class + YAML
  weights loader.
- **`src/crypt/models.py`** — all typed contracts: `Timeframe`, `Regime`,
  `Candle`, `FundingSnapshot`, `OISnapshot`, `LongShortRatioSnapshot`,
  `TakerVolumeSnapshot`, `Signal`, `Verdict`, `EvaluationContext`.
- **`src/crypt/exchange/`** — `ExchangeClient` Protocol + `OKXClient` backed
  by `ccxt.async_support.okx`. Covers OHLCV, funding history, OI history,
  L/S ratio, taker volume (including OKX-specific `rubik/stat` endpoints).
- **`src/crypt/data/`** — `ParquetStore` (Parquet read/write, upsert, trim),
  `Ingestor` (parallel async pulls for all symbols), `ContextBuilder`
  (assembles `EvaluationContext` from store).
- **`src/crypt/engines/`** — `BaseEngine` ABC + five engines:
  `TrendEngine`, `MeanRevEngine`, `DerivativesEngine`, `VolatilityEngine`,
  `RegimeEngine`. Bug fixed: `_rank_pct` returns 0 on zero-variance series.
- **`src/crypt/aggregator/`** — `WeightsConfig` (YAML loader with hard-coded
  fallback) + `ensemble.aggregate()` (regime-conditional weighted sum → Verdict).
- **`src/crypt/decision/filters.py`** — `DecisionFilter` (confidence
  threshold, cooldown, inputs-missing guard).
- **`src/crypt/sinks/`** — `BaseSink`, `TelegramSink` (aiogram, retry),
  `JsonLogSink` (JSONL append), `ConsoleSink`, `ExecutionStub`.
- **`src/crypt/runtime/`** — `H4Scheduler` (APScheduler 4h-aligned cron) +
  `Orchestrator` (wires all components, drives tick loop).
- **`src/crypt/__main__.py`** — CLI entry point with `--once`, `--symbols`,
  `--no-bootstrap` flags; graceful `SIGTERM`/`SIGINT` shutdown.
- **`config/weights.yaml`** — placeholder regime-conditional weights.
- **`tests/`** — 42 synthetic-data unit tests covering all engines,
  aggregator, and decision filter.

ADRs introduced: none (all decisions covered by ADRs 0001–0008).

---

## 2026-05-13 — M0 scaffold

- Decided language (Python), exchange (OKX-only), horizon (4h), storage
  (Parquet), data layer (REST), aggregator (regime-conditional weighted
  sum), scope (no order flow, no liquidations in MVP).
- ADRs 0001–0008 written.
- Architecture document `docs/architecture.md` written.
- Engine specs scaffolded under `docs/engines/`.
- Task tracking initialised: `ROADMAP.md`, `BACKLOG.md`, `IN_PROGRESS.md`,
  this file.
- Cursor rules created under `.cursor/rules/`.
- Root files created: `README.md`, `AGENTS.md`, `CHANGELOG.md`,
  `.gitignore`, `.env.example`.
- Verified via Context7 that OKX exposes everything needed for MVP through
  public REST (OHLCV, funding, OI, long/short ratio, taker volume).
  Liquidations are WS-only and deferred (ADR-0006).
