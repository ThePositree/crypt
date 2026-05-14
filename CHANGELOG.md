# Changelog

All notable changes to this project will be recorded here, session by session.

Format: keep entries terse. Date in `YYYY-MM-DD`. Newest on top.

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
