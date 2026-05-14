# Changelog

All notable changes to this project will be recorded here, session by session.

Format: keep entries terse. Date in `YYYY-MM-DD`. Newest on top.

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
