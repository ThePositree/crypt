# Backlog

Prioritised list of concrete items. Priority labels:

- **P0** — blocker / safety / can break the project. Do first.
- **P1** — important; the milestone is incomplete without it.
- **P2** — nice-to-have; revisit when higher priorities are clear.

Items move from here → `IN_PROGRESS.md` when work starts → `DONE.md`
when finished.

> **Important reading:** the 2026-05-15 planning session created several
> specs under `docs/` that this backlog references repeatedly. Read them
> before starting work on any non-trivial item.

---

## Currently completed (M1 done)

The whole M1 (signal-only, manual trading) block is done and deployed.
See `docs/tasks/DONE.md` and the M1 entry in `CHANGELOG.md`.

The remaining items from the original P0/P1 reliability lists are all
checked-off; only post-M1 work is listed below.

---

## P0 — must do soon after the 14-day run ends

### CI / quality gates

- [ ] **GitHub Actions CI** — implement `.github/workflows/ci.yml` per
      `docs/operations/ci.md`. Required checks: `ruff check`, `ruff
      format --check`, `mypy --strict`, `pytest`, `uv lock --check`,
      `gitleaks`. Add branch protection on `master`.
- [ ] **Pre-commit hooks** — `.pre-commit-config.yaml` mirroring CI
      (ruff + mypy). README "Developer setup" snippet.

### Threshold transparency

- [ ] **`[UNCALIBRATED]` marker on Telegram alerts** — per
      ADR-0011. Add `Settings.uncalibrated: bool = True`; update
      `TelegramSink._format_message`; unit test for both flag states.
- [ ] **`config/weights.yaml` header comment** — make it explicit at
      the top of the file that values are placeholders pending M2
      calibration.

### Latent code issues from planning session

See `docs/post_m1_code_fixes.md` for the technical detail of each. The
priorities below are the BACKLOG view.

- [ ] **Closed-candle invariant** — `post_m1_code_fixes.md` §1. P0
      because it's a no-look-ahead-bias correctness risk.
- [ ] **Critical-inputs guard refactor** — `post_m1_code_fixes.md` §2.
      P0 because future engines will rely on it.

---

## P1 — high value, schedule into M2 milestone

### M2 — Backtest harness (replaces the old 3-bullet sketch)

Full spec: **`docs/backtest.md`** (must-read before starting).

- [ ] **Backfill CLI** — `docs/backtest.md` §14. New module
      `src/crypt/backfill/__main__.py`. Pagination, resume safety, rate
      limit, tqdm progress.
- [ ] **`ReplayParquetStore` look-ahead guard** — `docs/backtest.md`
      §5.1. Top priority of M2: write the test first, then the guard.
- [ ] **`BacktestRecorder` + `BacktestExecutionSimulator`** —
      `docs/backtest.md` §5.2, §7. Reused by paper trading (`docs/paper_trading.md`).
- [ ] **Forward-label loader** — `docs/backtest.md` §6. Loads
      `return_h4 / h24 / h96` and `mae / mfe`.
- [ ] **Fee + slippage model** — `docs/backtest.md` §7. CLI overrides.
- [ ] **Walk-forward CV** — `docs/backtest.md` §8. `--walk-forward-folds`
      default 5.
- [ ] **Weight optimiser** — `docs/backtest.md` §9. Grid + coordinate
      descent + sanity guard.
- [ ] **Bootstrap CI** — `docs/backtest.md` §10. 1000 resamples on every
      headline metric.
- [ ] **Baseline comparison** — `docs/backtest.md` §11. Buy-and-hold,
      always-hold, random-direction.
- [ ] **HTML report** — `docs/backtest.md` §12. Single `summary.html`,
      no server.
- [ ] **`weights.recommended.yaml` writer** — `docs/backtest.md` §13.
      Median over folds, max threshold.
- [ ] **`tests/backtest/*`** — `docs/backtest.md` §15. Look-ahead guard
      test is the most important.

### Engine specs that will follow M2 calibration

These engines have specs in `docs/engines/*` and are sequenced **after**
M2 produces calibrated weights for the existing 5 engines, so the new
engines are introduced one at a time with a fresh backtest each.

- [ ] **`btc_context` engine** — `docs/engines/btc_context.md`.
      Cheap; should land first.
- [ ] **`cross_symbol_confluence`** — `docs/engines/cross_symbol_confluence.md`.
      Pure meta-engine; no new data source needed.
- [ ] **`calendar` engine** — `docs/engines/calendar.md`. Manual
      `config/events.yaml`.
- [ ] **`liquidations` engine** — `docs/engines/liquidations.md`,
      ADR-0012. Default to Path B (Coinglass).
- [ ] **`sentiment` engine** — `docs/engines/sentiment.md`. After
      liquidations because the data pipeline pattern is shared.

### Decision-layer improvements

From `docs/post_m1_code_fixes.md`:

- [ ] **Anti-flip-flop guard** — `post_m1_code_fixes.md` §3.
- [ ] **`produced_at` vs wall-clock semantics + test** —
      `post_m1_code_fixes.md` §4.

### Operability

- [ ] **Telegram bot commands** — `docs/operations/telegram_commands.md`.
      `/status`, `/last`, `/explain`, `/health`, `/threshold`,
      `/pause`, `/resume`, `/help`. P1 because the operator currently
      has zero introspection on a live system.
- [ ] **Per-tick metrics jsonl** — `docs/operations/observability.md`
      Gap A. New `tick_metrics.jsonl` next to verdicts.jsonl.
- [ ] **Error webhook (loguru → Telegram)** — `docs/operations/observability.md`
      Gap B. Rate-limited to 1/60 s.
- [ ] **Engine telemetry log lines** — `docs/operations/observability.md`
      Gap C.
- [ ] **OKX instrumentation** — `docs/operations/observability.md`
      Gap D. Request counters + p95 latency in heartbeat.
- [ ] **Heartbeat enrichment** — `docs/operations/observability.md`
      Gap E. Memory, disk, alert counts.

### Type-safety / correctness

From `docs/post_m1_code_fixes.md`:

- [ ] **Property-based aggregator tests (Hypothesis)** —
      `post_m1_code_fixes.md` §5.
- [ ] **`InputKey` enum for `inputs_missing`** —
      `post_m1_code_fixes.md` §8.
- [ ] **Combined-multiplier cap in aggregator** —
      `post_m1_code_fixes.md` §7.
- [ ] **XPL bootstrapping classification** —
      `post_m1_code_fixes.md` §6.

### Documentation hygiene

- [ ] **Operator runbook in production** — `docs/operator.md`. Mostly
      written; verify against the post-14-day Telegram experience and
      refine the "red flags" section.
- [ ] **First post-mortem(s)** — use `docs/post_mortems/_template.md`
      for any incident during the run. Even no-incident-period gets a
      single "summary" post-mortem at end of run.
- [ ] **Pin `aiogram>=3.7`** in `pyproject.toml` + note that
      `DefaultBotProperties(parse_mode=...)` is required since 3.7
      (carried over from earlier P1 dep-hygiene item).

### Railway post-run hygiene

- [ ] **Extract `data/*.parquet` and `data/logs/`** via `railway run`
      per `docs/deploy/railway.md` Step 7.
- [ ] **Decide retention** — Pro plan if we ever want > 7 days of
      cloud-side logs. Currently logs are on the persistent volume so
      this is mostly cosmetic.

---

## P1 — M3 (paper trading) once M2 weights are calibrated

Full spec: **`docs/paper_trading.md`**.

- [ ] **`crypt/paper/ledger.py`** — JSONL ledger primitives.
- [ ] **`PaperLedgerSink`** — `docs/paper_trading.md` §3, §5.
- [ ] **Exit-check task** — `docs/paper_trading.md` §6.
- [ ] **`PaperLedgerSettings`** — `docs/paper_trading.md` §7.
- [ ] **Restart recovery** — `docs/paper_trading.md` §11.
- [ ] **Direction-flip handling** — `docs/paper_trading.md` §11.
- [ ] **`crypt/paper/report.py`** + HTML — `docs/paper_trading.md` §13.
- [ ] **Owner ledger via `/trade` / `/close`** — depends on Telegram
      commands shipping first.
- [ ] **Calibration curve** — `docs/paper_trading.md` §8. The output
      the owner cares about.
- [ ] **P&L attribution by engine** — `docs/paper_trading.md` §9.

---

## P2 — later / opportunistic

### Data layer

- [ ] **DuckDB-over-Parquet read helper** — for ad-hoc analysis in
      Jupyter. No code change to the live pipeline.
- [ ] **Universe rotation** — auto-pick top-N OKX SWAPs by volume.
      Needs an ADR because it breaks reproducibility between deploys.
- [ ] **Data quality monitor** — assert no gaps > `2 * timeframe`; auto
      repair when ingestion catches up.
- [ ] **Parquet partitioning by month** — when dataset crosses ~100 MB.

### Risk management (pre-M4)

- [ ] **Drawdown circuit breaker spec** — after N losses in paper
      ledger, send alert "strategy in drawdown".
- [ ] **Daily loss limit (info-only until M4)**.
- [ ] **Position sizing spec** — Kelly fraction, vol-targeting; before
      M4 is more than a stub.

### Engines further out

- [ ] **ML meta-aggregator** — LightGBM on engine outputs. Decide
      after M3 paper trading shows reproducible expectancy.
- [ ] **Higher-frequency engine** (M15 or M5) — only if M3 data
      suggests sub-H4 information is being missed.

### Observability later

- [ ] **Sentry integration** — when the project scales beyond
      one operator. Until then, the error webhook in
      `docs/operations/observability.md` Gap B suffices.
- [ ] **Prometheus / OTLP exports** — once a metrics consumer exists.
- [ ] **Grafana dashboards** — depends on Prometheus.

### Operability later

- [ ] **Streamlit dashboard** — local-only browser UI over the
      JSONL/Parquet artefacts. Useful but adds maintenance.
- [ ] **`/event add ...` Telegram command** — manage
      `config/events.yaml` from chat.

### Deployment later

- [ ] **Docker compose** for an eventual self-hosted VPS deployment.
- [ ] **Railway Pro upgrade decision** — only if log retention > 7 d
      is needed mid-run.

---

## Known unknowns / things to verify before implementing

- **CryptoPanic free tier** — confirm endpoint + rate limit via
  Context7 before writing `docs/engines/sentiment.md` code. Spec
  describes the expected surface but APIs drift.
- **Coinglass freemium** — same. Confirm endpoints + rate limit before
  Path B in ADR-0012.
- **OKX REST liquidation endpoint** — ADR-0006 says WS-only as of MVP.
  Re-verify at implementation time; OKX has been known to add REST
  endpoints quietly.
- **OKX OI snapshot timing** — affects `derivatives` engine sensitivity;
  M2 should expose this in the report.
- **`pandas-ta` 0.4.x stability on Python 3.13+** — if we ever move off
  3.12, this stack may break (numba/llvmlite). Switching to plain
  `ta` is the fallback; would need an ADR.
- **`aiogram` 3.x release cadence** — they break minor APIs (e.g. the
  3.7.0 `Bot.__init__` change). Pin precisely.
