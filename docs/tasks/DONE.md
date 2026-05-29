# Done

Reverse-chronological archive of completed work. Newest on top.

---

## 2026-05-29 — Coinglass backfill: spec + ADR (docs only)

- `docs/backfill.md` — backfill contract: OKX + Coinglass sources, CLI
  `--source`, endpoint mapping, tier limits, M2 operator workflow.
- `docs/decisions/0015-coinglass-historical-backfill.md` — accepted ADR.
- Cross-refs in `docs/backtest.md` §14/§16, `docs/decisions/0012`,
  `.env.example`, `README.md`, task tracking files.
- Implementation (`CoinglassClient`, CLI) deferred — see `IN_PROGRESS.md`.

---

## 2026-05-29 — M2 backtest harness: full pipeline — steps 4–11 (labels, metrics, walk-forward, optimizer, report, CLI)

- `src/crypt/backtest/labels.py` — forward-label loader (§6): return_h4/h24/h96, MAE, MFE, hit_* columns.
- `src/crypt/backtest/metrics.py` — port of ResultsAnalyzer with §18.4 fixes (equity-curve
  duplicate-exit fix, Sharpe warning < 6 months, trade-level Sharpe); bootstrap CI; hit-rate
  metrics; buy-and-hold / random-direction baselines.
- `src/crypt/backtest/walkforward.py` — expanding-window walk-forward CV; `FoldSpec`, `generate_folds`,
  `slice_verdicts`, `slice_trades`; hard no-overlap guarantee tested.
- `src/crypt/backtest/optimizer.py` — grid search + coordinate descent weight optimiser (§9);
  objective = `mean(pnl) - 0.5*std(pnl)`; sanity guards; `aggregate_weights_across_folds` (§13 median rule).
- `src/crypt/backtest/report.py` — static HTML report generator with embedded matplotlib charts (§12).
- `src/crypt/backtest/__main__.py` — full CLI entry point: precondition checks (§4), replay loop (§5),
  forward labels, ExecutionSim wiring, walk-forward, optimization, baseline comparison, HTML report.
- `tests/backtest/test_labels.py` — 8 tests for label computation, hit rates, drop-tail behaviour.
- `tests/backtest/test_walkforward.py` — 8 tests incl. regression: no test-slice timestamp in train.
- `tests/backtest/test_metrics.py` — 12 tests: basic metrics, equity-curve §18.4 fix, Sharpe warning,
  bootstrap CI, buy-and-hold, generate_metrics integration.
- `matplotlib>=3.8` added to runtime dependencies.

Stats: 97 tests (was 67); mypy 0 errors (12 backtest files); ruff clean.

---

## 2026-05-29 — M2 backtest harness: backfill CLI + replay infrastructure (steps 1–3)

- `src/crypt/backfill/__init__.py`, `__main__.py` — paginated backfill CLI for OKX
  OHLCV/funding/OI/LS-ratio/taker-vol; resume-safe; tqdm progress; `--from`, `--to`,
  `--data-types`, `--page-size`, `--max-rps`.
- `src/crypt/exchange/okx.py` — pagination methods added: `fetch_ohlcv_page`,
  `fetch_funding_history_page`, `fetch_oi_history_page`, `fetch_ls_ratio_range`,
  `fetch_taker_volume_range`. `fetch_ohlcv` gains optional `since_ms` param.
- `src/crypt/backtest/replay.py` — `ReplayParquetStore` (time-fence look-ahead guard)
  and `ReplayContextBuilder` (drop-in for `ContextBuilder` in replay loop).
- `tests/backtest/test_no_lookahead.py` — 8 tests: guard filters future data,
  naïve builder leaks it (proof the test would catch a real regression).
- `src/crypt/backtest/fee_model.py` — port of `StaticPercentFeeModel` with
  maker/taker asymmetry.
- `src/crypt/backtest/risk_model.py` — port of `BasicRiskModel` (ATR-distance sizer).
- `src/crypt/backtest/execution_sim.py` — port of `ExecutionSim` with all §18.4 fixes:
  `FundingRateModel` + `ZeroFundingModel` + `ParquetFundingModel` (🔴);
  multi-symbol capital pool via `symbol` column (🔴); SL gap-adjusted fill (🟡);
  `exit_time` off-by-one fixed (🟡).
- `src/crypt/backtest/recorder.py` — `BacktestRecorder` (verdict sink → Parquet).
- `src/crypt/backtest/__init__.py` — module exports.
- `pyproject.toml` — `tqdm>=4.66` added; `tqdm.*` added to mypy overrides.

Stats: 67 tests pass (was 59); mypy 0 errors (43 files); ruff clean.

---

## 2026-05-29 — Post-M1 P0 quality gates + post-mortem + ADR-0013

- `docs/post_mortems/2026-05-29-m1-run-summary.md` — M1 14-day run summary
  (255 verdicts, 0 crashes, 0 alerts, key observations).
- `.github/workflows/ci.yml` — GitHub Actions CI (ruff, mypy, pytest, uv lock,
  gitleaks).
- `.pre-commit-config.yaml` — pre-commit hooks (ruff + mypy).
- `[UNCALIBRATED]` Telegram marker — `Settings.uncalibrated`, `TelegramSink`,
  8 unit tests.
- Closed-candle invariant — time-based `closed` in OKXClient, ingestor filter,
  `save_candles` assertion, 4 unit tests.
- Critical-inputs guard refactor — `Signal.critical_missing`,
  `BaseEngine.critical_inputs`, per-engine declarations, filter updated, 5 new
  tests.
- ADR-0013 (`crypt` stdlib name conflict) — `pythonpath = ["src"]` in
  `pyproject.toml`; `uv run pytest` now works without `PYTHONPATH=src`.

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
