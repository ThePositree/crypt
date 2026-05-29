# Changelog

All notable changes to this project will be recorded here, session by session.

Format: keep entries terse. Date in `YYYY-MM-DD`. Newest on top.

---

## 2026-05-29 — Post-M1 run: P0 quality gates, post-mortem, stdlib name fix

M1 14-day run completed successfully (255 verdicts, 0 errors, 0 alerts). All P0
post-run work shipped in this session.

### Post-mortem

- `docs/post_mortems/2026-05-29-m1-run-summary.md` — full 14-day run analysis:
  tick completeness, decision distribution, regime breakdown, key observations
  (zero alerts, TON BUY streak at conf 50%, XPL bootstrapping behaviour).

### P0 quality gates (all 5 shipped)

- **GitHub Actions CI** — `.github/workflows/ci.yml`: ruff lint, ruff format,
  mypy strict, pytest, uv lock check, gitleaks secret scan.
- **Pre-commit hooks** — `.pre-commit-config.yaml`: ruff (with auto-fix) +
  mypy. README "Developer setup" section added.
- **`[UNCALIBRATED]` marker** — `Settings.uncalibrated: bool = True` added to
  `config.py`; `TelegramSink._format_message` now appends `⚠️ [UNCALIBRATED]`
  to the alert title when flag is True; wired through `Orchestrator._build_sinks`.
  Unit tests in `tests/sinks/test_telegram.py` (8 tests).
- **Closed-candle invariant** — `OKXClient.fetch_ohlcv` now uses time-based
  `closed` determination (bar_close + 5s safety buffer). `Ingestor._ingest_ohlcv`
  pre-filters to closed candles before `save_candles`. `ParquetStore.save_candles`
  raises `ValueError` on any non-closed candle. Tests in
  `tests/data/test_store_closed_invariant.py` (4 tests).
- **Critical-inputs guard refactor** — `Signal.critical_missing: list[str]`
  field added. `BaseEngine.critical_inputs: ClassVar[list[str]] = []` declared;
  TrendEngine, MeanRevEngine, VolatilityEngine, RegimeEngine declare
  `critical_inputs = ["candles[H4]"]`; DerivativesEngine keeps `[]`.
  `DecisionFilter._has_critical_missing` now reads `sig.critical_missing`
  instead of substring-matching `"candles[H4]"` in `inputs_missing`. New tests
  in `tests/decision/test_filters.py` (+5 tests).

### `crypt` stdlib name conflict fix (ADR-0013)

- `pyproject.toml` — `[tool.pytest.ini_options]` gets `pythonpath = ["src"]`;
  `uv run pytest` now works out of the box without `PYTHONPATH=src`.
- `docs/decisions/0013-crypt-stdlib-name-conflict.md` — ADR documenting root
  cause, fixes applied, agent instructions, what was deliberately NOT done.
- `docs/deploy/railway.md` — troubleshooting table updated with ADR-0013 link.

### Stats

- Tests: 59 passed (was 42); mypy 0 errors (36 files); ruff clean.
- New files: 8 (`ci.yml`, `.pre-commit-config.yaml`, post-mortem, ADR-0013,
  `test_telegram.py`, `test_store_closed_invariant.py`, `tests/sinks/__init__.py`,
  `tests/data/__init__.py`).
- Modified files: `config.py`, `sinks/telegram.py`, `runtime/orchestrator.py`,
  `exchange/okx.py`, `data/store.py`, `data/ingestor.py`, `models.py`,
  `engines/base.py`, `engines/trend.py`, `engines/meanrev.py`,
  `engines/volatility.py`, `engines/regime.py`, `decision/filters.py`,
  `pyproject.toml`, `README.md`, `docs/deploy/railway.md`,
  `docs/tasks/IN_PROGRESS.md`, `docs/tasks/BACKLOG.md`, `docs/tasks/DONE.md`.

ADRs introduced: 0013.

---

## 2026-05-29 — Fix Railway data export docs (`railway run` vs `railway ssh`)

`railway run` runs commands locally with injected env vars; `/app/data` exists only
inside the deployed container where the volume is mounted. Step 7 in the deploy guide
incorrectly used `railway run`, causing `find: '/app/data': No such file or directory`.

- `docs/deploy/railway.md` — Step 7 now uses `railway ssh`; added prerequisites,
  extract commands, and troubleshooting rows.
- `docs/operator.md`, `docs/decisions/0010-railway-deployment.md` — aligned references.

---

## 2026-05-15 — Planning session: post-M1 docs / specs / backlog refresh

Pure documentation session. **No code changes.** The M1 14-day Railway
run is in progress; pushes to `master` would trigger a redeploy and
downtime (ADR-0010), so all work landed under `docs/` only.

Owner asked the agent to brainstorm and document what else can land
during and after the 14-day window, with extra detail so future agents
can implement without re-deriving the design.

### New documents

- `docs/backtest.md` — full M2 harness spec (CLI, data preconditions,
  no-look-ahead guard, walk-forward CV, weight optimiser with sanity
  guards, bootstrap CI, baseline comparisons, HTML report, backfill
  CLI, tests).
- `docs/paper_trading.md` — full M3 spec (ledger schema, entry / exit
  logic, SL/TP via ATR, restart recovery, P&L attribution, calibration
  curve, owner ledger via Telegram commands, tests).
- `docs/operator.md` — owner-facing runbook (anatomy of an alert,
  red / green flags, post-calibration recipe, escalation).
- `docs/operations/telegram_commands.md` — `/status`, `/last`,
  `/explain`, `/health`, `/threshold`, `/pause`, `/trade`, etc.
- `docs/operations/observability.md` — per-tick metrics jsonl,
  error-to-Telegram webhook, engine telemetry log lines, OKX
  instrumentation, heartbeat enrichment.
- `docs/operations/ci.md` — GitHub Actions workflow, branch
  protection, pre-commit hooks.
- `docs/post_mortems/_template.md` — incident post-mortem template.
- `docs/post_m1_code_fixes.md` — 8 latent issues to address after the
  run (closed-flag invariant, critical-inputs guard, anti-flip-flop,
  produced_at semantics, confidence-scale mismatch, XPL warm-up,
  multiplier cap, `InputKey` enum).

### New engine specs (no code yet — implement post-M2)

- `docs/engines/sentiment.md` — CryptoPanic-backed (background polling,
  graceful degrade, vote-weight calibration in M2).
- `docs/engines/liquidations.md` — three implementation paths; default
  Path B (Coinglass).
- `docs/engines/btc_context.md` — BTC-as-leader alignment multiplier +
  crisis filter; not part of weighted-sum score.
- `docs/engines/calendar.md` — `config/events.yaml` manual schedule;
  pre- and post-event confidence suppression curve.
- `docs/engines/cross_symbol_confluence.md` — meta-engine, runs in
  aggregator layer.

### New ADRs

- `0011-thresholds-rationale-and-uncalibrated-marker.md` — explains why
  the current threshold values are placeholders and mandates an
  `[UNCALIBRATED]` tag on Telegram alerts until M2 calibration.
- `0012-liquidations-roadmap.md` — complements (does not supersede)
  ADR-0006; promotes liquidation engine to BACKLOG P1 post-M2 with
  three implementation paths. ADR-0006 status line updated to point
  here.

### Task tracking

- `docs/tasks/BACKLOG.md` — full rewrite with P0/P1/P2 sections
  cross-referencing all new specs. M2 (backtest) decomposed from 3
  bullets into 12; M3 decomposed; new engines sequenced; operability
  and observability tracks added.
- `docs/tasks/IN_PROGRESS.md` — explicit next-steps block for the agent
  picking up after the 14-day run, ordered: extract data → write
  post-mortem → P0 quality gates → M2 starting with the no-look-ahead
  test.

ADRs introduced: 0011, 0012. ADR-0006 annotated.

Files touched (directory level): `docs/`, `docs/engines/`,
`docs/decisions/`, `docs/operations/`, `docs/post_mortems/`,
`docs/tasks/`.

No `src/` or `tests/` changes. No `pyproject.toml` / `uv.lock` changes.

---

## 2026-05-15 — Fix: all log levels tagged `[err]` in Railway

**Root cause:** Loguru writes all levels to `sys.stderr` by default. Railway
labels every byte from stderr as `[err]`, regardless of log level.

**Fix:** Split the console sink in `_configure_logging`:
- `DEBUG` / `INFO` → `sys.stdout` (Railway: `[inf]`)
- `WARNING` and above → `sys.stderr` (Railway: `[err]`, correct)

File log (`crypt.log`) unchanged — still receives all levels.

Files touched: `src/crypt/__main__.py`, `CHANGELOG.md`

---

## 2026-05-15 — Fix: aiogram 3.7.0 broke `Bot` initializer (`parse_mode` removed)

**Root cause:** aiogram 3.7.0 removed `parse_mode`, `disable_web_page_preview`,
and `protect_content` from the `Bot.__init__` signature. Passing `parse_mode`
directly raised `TypeError` on every startup, crashing the process in a
Railway crash-loop.

**Fix:** Replaced `Bot(token=..., parse_mode=ParseMode.HTML)` with
`Bot(token=..., default=DefaultBotProperties(parse_mode=ParseMode.HTML))`
as required by aiogram ≥ 3.7.0.

Files touched: `src/crypt/sinks/telegram.py`, `CHANGELOG.md`

---

## 2026-05-15 — Fix: `SettingsError` on Railway when `SYMBOLS` env var is empty

**Root cause:** pydantic-settings v2 tries `json.loads()` on every `list[str]`
field before calling `field_validator`. `SYMBOLS=` (empty string) → empty
`json.loads("")` → `JSONDecodeError` → process crash.

**Fix:**
- Added `enable_decoding=False` to `SettingsConfigDict`: pydantic-settings now
  passes the raw string to the `field_validator` instead of trying JSON first.
- Updated `_parse_symbols` validator to fall back to `_DEFAULT_SYMBOLS` when
  the env var is empty/blank.
- Added troubleshooting row to `docs/deploy/railway.md`.

Files touched: `src/crypt/config.py`, `docs/deploy/railway.md`, `CHANGELOG.md`

---

## 2026-05-15 — Fix: `ModuleNotFoundError: No module named 'crypt.data'` on Railway

**Root cause:** `.gitignore` contained `data/` (no leading slash), which matched any
directory named `data` anywhere in the tree — including `src/crypt/data/`.
Railway builds from the git repo, so the entire Python package `crypt.data`
(context, ingestor, store) was absent from the container.

**Fix:** Changed `data/` → `/data/` and `logs/` → `/logs/` in `.gitignore`
(leading slash limits the rule to the repository root only).
Added `src/crypt/data/__init__.py`, `context.py`, `ingestor.py`, `store.py`
to git tracking.

Files touched: `.gitignore`, `CHANGELOG.md`

---

## 2026-05-15 — Fix: slow shutdown (SIGINT did not interrupt in-flight awaits)

### What broke
SIGINT only set `stop_event`, but long-running coroutines (`run_health_check`,
`bootstrap`, `tick`) were awaited directly with no cancellation path.
Shutdown took up to ~30 s because those operations ran to completion before
`stop_event.wait()` was ever reached.

### Fix
Signal handler now also calls `main_task.cancel()` on the main asyncio task.
`CancelledError` is raised at the current `await` point and propagates up
through `asyncio.gather` chains; `except asyncio.CancelledError: pass` in
`_main()` ensures the `finally` cleanup block still runs.

Files touched: `src/crypt/__main__.py`.

---

## 2026-05-15 — Fix: root cause of silent zero-exit (stdlib crypt.py name collision)

Package name `crypt` collides with the deprecated Python 3.12 stdlib module
`crypt.py`. In Python's module resolution order, stdlib comes before
site-packages and the editable-install `src/` path. So `python -m crypt`
silently executed the stdlib module (no `__main__` block → exit 0, no output).

Fix: prefix the start command with `PYTHONPATH=/app/src` (railway.toml).
This puts `src/` at the front of `sys.path` before stdlib, so our package
is found first. Same fix required locally: `PYTHONPATH=src` in `.env`.

Files:
- `railway.toml`
- `.env.example`
- `docs/deploy/railway.md`
- `CHANGELOG.md`

---

## 2026-05-14 — Fix: pandas-ta 0.4.x numba/LLVM hang on Railway

pandas-ta>=0.4 (only version available for Python 3.12+) added numba as a
hard dependency. numba initialises LLVM via llvmlite at Python import time —
before logging is even configured — causing a complete silent hang in
CPU-constrained Railway containers.

Fix: `NUMBA_DISABLE_JIT=1` is now documented as a required Railway Variable
(and added to `.env.example`). With JIT disabled numba functions fall back to
plain Python; indicators remain correct, just slightly slower.

The `<0.4` constraint was tried but is not available for Python 3.12+ on PyPI.

Files:
- `pyproject.toml` (reverted <0.4 constraint, added explanatory comment)
- `.env.example` (NUMBA_DISABLE_JIT=1 added)
- `docs/deploy/railway.md` (moved to Required variables table)
- `CHANGELOG.md`

---

## 2026-05-14 — Fix: silent container on Railway deploy (output buffering + health check hang)

Three issues caused the process to appear dead after bytecode compilation:
1. `python -u` not set → Python buffered stderr in non-TTY container, log lines never flushed.
2. Health check created `ccxt.okx` without `"timeout": 30_000` → `load_markets()` could hang indefinitely.
3. Railpack auto-detects start command without `--no-dev` → dev packages (mypy/ruff) installed on every start, adding ~30-60 s delay before Python even booted.

Fixes: `railway.toml` start command changed to `uv run --no-dev python -u -m crypt`; `health.py` ccxt instance gets explicit 30 s timeout; `railway.md` updated with `PYTHONUNBUFFERED=1` recommendation and expanded troubleshooting table.

Files:
- `railway.toml`
- `src/crypt/runtime/health.py`
- `docs/deploy/railway.md`
- `CHANGELOG.md`

---

## 2026-05-14 — Railway: `uv run --no-dev` + immediate stderr logs

`uv run` includes the `dev` group by default, so every deploy was reinstalling
mypy/ruff before the app started. Start command now passes `--no-dev`. Stderr
logging uses colorize/enqueue only when stderr is a TTY so Railway log streams
see lines immediately.

Files:
- `railway.toml`
- `src/crypt/__main__.py`
- `docs/deploy/railway.md`
- `CHANGELOG.md`

---

## 2026-05-14 — Fix Railway `railway.toml` parse error

Removed invalid TOML line `$schema = ...` (that key belongs in `railway.json` only;
bare TOML keys cannot start with `$`). Railway deploy config now parses.

Files:
- `railway.toml`
- `CHANGELOG.md`

---

## 2026-05-14 — AGENTS: incident / "fix this" workflow

Clarified AI-first behaviour when the owner starts a session with errors or
CI logs instead of "continue": chat overrides stale assumptions, reproduce
before refactor, minimal fix + tests, and which task/changelog docs to touch.

Files:
- `AGENTS.md`
- `.cursor/rules/ai-first-workflow.mdc`

---

## 2026-05-14 — Session 6: Railway deployment

Railway deployment config for the M1 14-day continuous run.

Files created/modified:
- `railway.toml` — Railpack builder, production install, start command, restart policy.
- `.python-version` — pins Python 3.12.
- `src/crypt/config.py` — added `log_dir` field (env: `LOG_DIR`, default `logs/`).
- `src/crypt/__main__.py` — `_configure_logging` now accepts `log_dir` from settings.
- `.env.example` — documented `LOG_DIR`.
- `docs/decisions/0010-railway-deployment.md` — ADR (accepted).
- `docs/deploy/railway.md` — 8-step owner deployment guide with file extraction commands.
- `docs/tasks/DONE.md`, `docs/tasks/IN_PROGRESS.md`, `docs/tasks/BACKLOG.md` — updated.

ADRs introduced: 0010.

---

## 2026-05-14 — Session 5: reliability hardening

All P0/P1/P2 reliability items from BACKLOG completed. System is now ready
for the 14-day continuous run.

### What was done

- **`src/crypt/utils/retry.py`** (new) — `retry_with_backoff` coroutine helper
  with full-jitter exponential backoff (`uniform(0, min(max_delay, base*2^n))`).
- **`src/crypt/exchange/okx.py`** — all 5 fetch methods wrapped with
  `retry_with_backoff`; `"timeout": 30_000` added to ccxt config.
- **`src/crypt/data/ingestor.py`** — `ingest_all` and `_ingest_symbol`
  now log `BaseException` items from `asyncio.gather(return_exceptions=True)`.
- **`src/crypt/runtime/orchestrator.py`** — `tick()` logs exceptions from
  gather; sink exceptions logged by name; `_evaluate_symbol` returns
  `"ok"/"partial"/"failed"` status; tick summary log line at end.
  `Timeframe` added to imports.
- **`src/crypt/runtime/health.py`** — `_check_disk_space` added (logs WARNING
  if < 1 GB free on `data_dir` filesystem).
- **`src/crypt/__main__.py`** — log rotation changed to `rotation="00:00"` +
  `compression="gz"`; `_heartbeat_loop` background task (30-min liveness log +
  6h OKX health re-check); heartbeat task cancelled cleanly on shutdown.
- **`src/crypt/sinks/telegram.py`** — backoff jitter: `random.uniform(0.5, 1.5)`
  multiplier on retry wait.
- **`src/crypt/config.py`** — `okx_max_retries`, `okx_retry_base_delay`,
  `okx_retry_max_delay` settings exposed.
- **`.env.example`** — retry/backoff params documented (commented out).
- **`deploy/crypt.service`** (new) — systemd unit with `Restart=always`,
  `RestartSec=10`, `EnvironmentFile`, `WorkingDirectory`.
- **`README.md`** — "Running as a service" section added.

Results: mypy 0 errors / 36 files. ruff clean. 42/42 tests pass.

ADRs introduced: none.

---

## 2026-05-14 — Session 3: M1 validation

All M1 P0/P1 items resolved. System runs against live OKX without errors.

Files changed:

- `pyproject.toml` — added `pandas.*`, `pyarrow.*` to mypy overrides.
- `src/crypt/exchange/okx.py` — fixed `fetch_ls_ratio` and `fetch_taker_volume`: OKX rubik stat endpoints require `ccy` (base currency), not `instId`.
- `src/crypt/runtime/health.py` — **new**: startup health-check (OKX ping, symbol existence via market `id`, optional Telegram bot ping).
- `src/crypt/runtime/scheduler.py` — `stop()` guarded with `running` check.
- `src/crypt/__main__.py` — import `run_health_check`; call it before bootstrap; create `logs/` directory before file sink.
- `src/crypt/data/store.py` — typed lambda list; pyarrow `type: ignore`.
- `src/crypt/engines/derivatives.py` — `Direction` annotation; typed `_ls_signal` param; added imports.
- `src/crypt/engines/trend.py` — `Direction` annotation; `Direction` import.
- `src/crypt/engines/meanrev.py` — `Direction` annotation; `std=2.0`; `type: ignore[arg-type]`.
- `src/crypt/engines/volatility.py` — `npt.NDArray[Any]` for `_rank_pct`.
- `src/crypt/config.py` — `return list(v)` to silence mypy `no-any-return`.
- `docs/tasks/DONE.md`, `docs/tasks/IN_PROGRESS.md`, `docs/tasks/BACKLOG.md` — updated.

Results: mypy 0 errors / 34 files. ruff clean. 42/42 tests pass.
Smoke test: `uv run python -m crypt --once` exits 0, verdicts for all 3 symbols.
Symbol check: SOL-USDT-SWAP ✓, TON-USDT-SWAP ✓, XPL-USDT-SWAP ✓.

ADRs introduced: none.

---

## 2026-05-14 — Session 2: M1 implementation

Full M1 code layer implemented. Context7 was unavailable; proceeded with
in-context library knowledge.

Files created:

- `src/crypt/config.py`, `models.py`, `__main__.py`
- `src/crypt/exchange/__init__.py`, `base.py`, `okx.py`
- `src/crypt/data/__init__.py`, `store.py`, `ingestor.py`, `context.py`
- `src/crypt/engines/__init__.py`, `base.py`, `trend.py`, `meanrev.py`,
  `derivatives.py`, `volatility.py`, `regime.py`
- `src/crypt/aggregator/__init__.py`, `weights.py`, `ensemble.py`
- `src/crypt/decision/__init__.py`, `filters.py`
- `src/crypt/sinks/__init__.py`, `base.py`, `telegram.py`, `jsonlog.py`,
  `console.py`, `execution_stub.py`
- `src/crypt/runtime/__init__.py`, `scheduler.py`, `orchestrator.py`
- `src/crypt/backtest/__init__.py`
- `config/weights.yaml`
- `tests/conftest.py`, `tests/engines/test_{trend,meanrev,derivatives,
  volatility,regime}.py`, `tests/aggregator/test_ensemble.py`,
  `tests/decision/test_filters.py`

Also updated: `pyproject.toml` (`requires-python` bump to `>=3.12`),
`uv.lock` generated.

All 42 tests pass; `ruff` clean.

Next: live smoke test, `XPL-USDT-SWAP` existence check, mypy pass.

ADRs introduced: none.

---

## 2026-05-13 — Session 1: project bootstrap

Owner pinned down the high-level requirements: Python, OKX-only, 4h intraday,
3 starting symbols (`SOL-USDT-SWAP`, `TON-USDT-SWAP`, `XPL-USDT-SWAP`),
Telegram alerts, 0$ data budget, local execution, weighted-sum aggregator,
confidence threshold 75%, AI-first development.

Created the project scaffold:

- `README.md`, `AGENTS.md`, this `CHANGELOG.md`, `.gitignore`, `.env.example`
- `.cursor/rules/` — `project-context.mdc`, `ai-first-workflow.mdc`,
  `coding-standards.mdc`
- `docs/architecture.md`
- `docs/decisions/` — ADRs 0001–0008
- `docs/tasks/` — `ROADMAP.md`, `BACKLOG.md`, `IN_PROGRESS.md`, `DONE.md`
- `docs/engines/` — specs for `trend`, `meanrev`, `derivatives`, `volatility`,
  `regime`, `aggregator`, `decision`
- `pyproject.toml`, `src/crypt/__init__.py`, `tests/`

OKX API capabilities verified via Context7 (`/websites/okx_docs-v5_en` and
`/ccxt/ccxt`):

- OHLCV, funding rate (current + history), open interest history, long/short
  account ratio, taker volume — all available via public REST.
- Liquidations — only via WebSocket; deferred (ADR 0006).

No code yet. Next session: implement data layer + signal contracts (see
`docs/tasks/IN_PROGRESS.md`).

ADRs introduced: 0001..0008.
