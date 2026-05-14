# Done

Reverse-chronological archive of completed work. Newest on top.

---

## 2026-05-14 — Session 6: Railway deployment config

Railway deployment for the M1 14-day continuous run.

- Researched Railpack (Railway's build system), Railway Volumes, log retention, billing,
  GitHub auto-deploy, and file extraction methods.
- Created `docs/decisions/0010-railway-deployment.md` (ADR; status: accepted).
- Created `railway.toml` — Railpack builder, `uv sync --all-extras --no-dev` build command,
  `uv run --no-dev python -m crypt` start command (avoids default `dev` group on `uv run`),
  `ON_FAILURE` restart policy.
- Created `.python-version` — pins Python 3.12 for Railpack.
- Added `log_dir: Path` field to `Settings` (`config.py`); updated `__main__.py` to accept
  it in `_configure_logging`. On Railway: `LOG_DIR=data/logs` puts log files on the
  persistent volume alongside parquet files. Stderr Loguru uses `isatty()` so colorize and
  `enqueue` apply only in a real terminal (immediate logs on Railway).
- Updated `.env.example` with `LOG_DIR` documentation.
- Created `docs/deploy/railway.md` — step-by-step owner checklist (8 steps, including
  volume setup, env vars, monitoring, and exact file-extraction commands).

---

## 2026-05-14 — Session 5: reliability hardening

All P0/P1/P2 reliability BACKLOG items completed.

- `src/crypt/utils/retry.py` — `retry_with_backoff` helper (full-jitter exponential backoff).
- `src/crypt/exchange/okx.py` — retry applied to all 5 fetch methods; `timeout: 30s`.
- `src/crypt/data/ingestor.py` — exceptions from `asyncio.gather` logged at ERROR.
- `src/crypt/runtime/orchestrator.py` — gather exceptions logged; tick summary line;
  `_evaluate_symbol` returns status; sink exceptions logged.
- `src/crypt/runtime/health.py` — disk-space guard (`< 1 GB` → WARNING).
- `src/crypt/__main__.py` — daily log rotation + gz; heartbeat task (30 min liveness
  + 6 h OKX health check); clean shutdown of heartbeat task.
- `src/crypt/sinks/telegram.py` — jitter in backoff retry.
- `src/crypt/config.py` — `OKX_MAX_RETRIES`, `OKX_RETRY_BASE_DELAY`, `OKX_RETRY_MAX_DELAY`.
- `.env.example` — retry/backoff params documented.
- `deploy/crypt.service` — systemd unit with `Restart=always`, `RestartSec=10`.
- `README.md` — "Running as a service" section.

mypy 0 errors / 36 files. ruff clean. 42/42 tests pass.

---

## 2026-05-14 — Session 3: M1 validation (smoke test + mypy + health check)

### What was done

- **mypy clean pass** — fixed 12 type errors across 8 files:
  - Added `pandas.*` and `pyarrow.*` to `[[tool.mypy.overrides]]` in `pyproject.toml`.
  - `store.py`: typed lambda list as `list[Callable[[], Path]]`; added `type: ignore[no-untyped-call]` for pyarrow bundled-stub gap.
  - `engines/derivatives.py`: explicit `Direction` annotation on `direction` variable; typed `_ls_signal` arg to `list[LongShortRatioSnapshot]`; added `Direction` import.
  - `engines/trend.py`, `engines/meanrev.py`: explicit `Direction` annotation on direction variables.
  - `engines/meanrev.py`: `std=2.0` (float) + `type: ignore[arg-type]` for pandas-ta bundled-stub gap.
  - `engines/volatility.py`: `npt.NDArray[Any]` for `_rank_pct` signature.
  - `config.py`: `return list(v)` to avoid `Returning Any`.
- **OKX rubik stat API fix** — `/rubik/stat/contracts/long-short-account-ratio` and `/rubik/stat/taker-volume` require `ccy` (base currency), not `instId`. Fixed both methods in `okx.py`.
- **Scheduler stop guard** — `H4Scheduler.stop()` now checks `self._scheduler.running` before calling `shutdown()` to avoid `SchedulerNotRunningError` when `--once` is used.
- **Logging**: `logs/` directory is created at startup before the loguru file sink is added.
- **Health-check helper** (`src/crypt/runtime/health.py`) — on startup checks OKX API reachability, verifies each configured symbol exists in OKX market list (by raw `instId`), and optionally pings the Telegram bot.
- **Symbol verification** — all three configured symbols confirmed live on OKX: `SOL-USDT-SWAP` ✓, `TON-USDT-SWAP` ✓, `XPL-USDT-SWAP` ✓.
- **Smoke test** — `uv run python -m crypt --once` completes cleanly (exit 0, no unclosed connectors). Verdicts produced for all 3 symbols.

ADRs introduced: none.

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
