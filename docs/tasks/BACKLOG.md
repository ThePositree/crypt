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

- [x] **GitHub Actions CI** — `.github/workflows/ci.yml` (2026-05-29).
- [x] **Pre-commit hooks** — `.pre-commit-config.yaml` (2026-05-29).

### Threshold transparency

- [x] **`[UNCALIBRATED]` marker on Telegram alerts** — ADR-0011; shipped
      2026-05-29. Removed when M2 calibration lands (ADR-0014).
- [ ] **`config/weights.yaml` header comment** — make it explicit at
      the top of the file that values are placeholders pending M2
      calibration.

### Latent code issues from planning session

See `docs/post_m1_code_fixes.md` for the technical detail of each. The
priorities below are the BACKLOG view.

- [x] **Closed-candle invariant** — `post_m1_code_fixes.md` §1. Shipped 2026-05-29.
- [x] **Critical-inputs guard refactor** — `post_m1_code_fixes.md` §2. Shipped 2026-05-29.

### Package name / stdlib conflict

- [x] **`crypt` vs Python stdlib `crypt`** — ADR-0013; `pythonpath = ["src"]`
      in `pyproject.toml` (2026-05-29). `uv run pytest` now works without
      manual `PYTHONPATH=src`.

---

## P1 — high value, schedule into M2 milestone

### M2 — Backtest harness (replaces the old 3-bullet sketch)

Full spec: **`docs/backtest.md`** (must-read before starting).

- [x] **Backfill CLI** — `src/crypt/backfill/__main__.py` (2026-05-29).
- [x] **`ReplayParquetStore` look-ahead guard** — `src/crypt/backtest/replay.py`;
      8 tests in `tests/backtest/test_no_lookahead.py` (2026-05-29).
- [x] **`BacktestRecorder` + `BacktestExecutionSimulator`** —
      `src/crypt/backtest/{recorder,execution_sim,fee_model,risk_model}.py`
      with all §18.4 fixes (2026-05-29).
- [x] **Forward-label loader** — `src/crypt/backtest/labels.py` (2026-05-29).
- [x] **Fee + slippage model** — `docs/backtest.md` §7. Wired into `__main__.py` (2026-05-29).
- [x] **Walk-forward CV** — `src/crypt/backtest/walkforward.py` (2026-05-29).
- [x] **Weight optimiser** — `src/crypt/backtest/optimizer.py` (2026-05-29).
- [x] **Bootstrap CI** — `src/crypt/backtest/metrics.py` (2026-05-29).
- [x] **Baseline comparison** — `src/crypt/backtest/metrics.py` + `__main__.py` (2026-05-29).
- [x] **HTML report** — `src/crypt/backtest/report.py` (2026-05-29).
- [x] **`weights.recommended.yaml` writer** — `optimizer.py` + `__main__.py` (2026-05-29).
- [x] **`tests/backtest/*`** — labels, walkforward, metrics tests added (2026-05-29).
- [x] **Coinglass backfill spec + ADR-0015** — superseded by ADR-0016 (2026-06-01).
      Coinglass not needed; funding dropped; OI/LS from OKX native endpoints.
- [x] **Fix OI endpoint** — `src/crypt/exchange/okx.py`: replaced with
      direct `publicGetRubikStatContractsOpenInterestHistory` call (2026-06-01).
- [x] **Remove funding from `DerivativesEngine`** — weights OI 0.67 / LS 0.33;
      removed from `EvaluationContext`, `context.py`, `store.py`, backfill CLI,
      `replay.py`, `backtest/__main__.py` (2026-06-01).
- [x] **ADR-0017: OHLCV-only M2 calibration** — primary M2 backtest uses
      free OKX candles only; derivatives weight is `0` until deep OI/LS is
      proven useful (2026-06-01).
- [x] **SMC core analyser** — `docs/engines/smc_core.md`; deterministic
      Python implementation of pivots, BOS/CHoCH, order blocks, equal
      highs/lows, sweeps; first slice covers pivots + BOS/CHoCH with
      no-lookahead tests (2026-06-01).
- [x] **`smc_structure` engine** — `docs/engines/smc_structure.md`; first
      candle-only SMC directional engine (2026-06-01).
- [x] **`smc_order_blocks` engine** — `docs/engines/smc_order_blocks.md`;
      retest signal from active order-block zones.
- [x] **`smc_liquidity` engine** — `docs/engines/smc_liquidity.md`;
      equal high/low and swing-level sweep signal (2026-06-01).
- [x] **Fix optimizer score recomputation** — P0 before trusting M2
      calibration. Fixed 2026-06-01: recorder persists `strength_<engine>`
      columns and optimizer recomputes candidate score/decision/objective from
      them before accepting `weights.recommended.yaml`.
- [x] **Run OHLCV backfill + full backtest** — OKX candles only.
      SOL/TON report reviewed in ADR-0014 (2026-06-01); generated weights
      rejected by sanity guard.
- [x] **ADR-0014** — calibration result after M2 report is reviewed. Written
      2026-06-01; weights rejected, not accepted.
- [ ] **Flip `uncalibrated = False`** — only after a future calibration ADR
      accepts weights that pass the sanity guard.
- [ ] **Fix guarded-report artifact semantics** — P1. If any walk-forward
      fold fires the optimizer sanity guard, do not present
      `weights.recommended.yaml` as promotable and make `weights.candidate.yaml`
      clearly represent the aggregate non-promotable candidate rather than the
      last fold's weights.
- [ ] **Investigate weak long-side signals** — P1. ADR-0014 report review
      showed negative `h24` proxy expectancy on `SOL` BUY and `TON` BUY
      alerts; add a filter or context engine before the next calibration run.

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
      ADR-0012. Default to Path B (Coinglass). Reuse `CoinglassClient`
      from ADR-0015 backfill work.
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

- [x] **Extract `data/*.parquet` and `data/logs/`** — done; files in `prod/`
      (2026-05-29).
- [ ] **Decide retention** — Pro plan if we ever want > 7 days of
      cloud-side logs. Currently logs are on the persistent volume so
      this is mostly cosmetic.
- [ ] **Stop / pause Railway service** — owner action; Parquet data already
      extracted to `prod/`.

### Product output: entry / SL / TP in Verdict

From session 5 discussion: the system's goal is to output a complete trade
setup (direction + entry + stop-loss + take-profit), not just BUY/SELL/HOLD.
Proposed design for M3+:

- **Entry price**: close of the H4 candle that triggered the signal.
- **SL**: `Entry − 1.5 × ATR14(H4)` for longs (reversed for shorts).
  ATR is already computed in `VolatilityEngine`; needs to be exported via
  `Signal.meta` or a new field.
- **TP**: `Entry + 2 × (Entry − SL)` — fixed 2:1 R:R (mechanical, per owner request).

Implementation tasks (post-M2 calibration):

- [ ] **Export ATR in `VolatilityEngine.meta`** — add `atr14_h4` to
      `Signal.meta` so the aggregator can use it.
- [ ] **Add `entry`, `sl`, `tp` to `Verdict`** — optional fields, populated
      when `decision != HOLD`. Aggregator computes from entry + ATR-based SL.
- [ ] **Update `TelegramSink`** — include entry/SL/TP in alert message.
- [ ] **Update `JsonlSink` + backtest recorder** — log new Verdict fields.

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

The product vision (session 5) is to aggregate **all** trader tools into one
verdict — indicators, structure, volume, price action — so the owner gets
in seconds what takes a trader hours to assemble manually.

Planned engine categories (post-M2, one at a time with fresh backtest each):

**Structural / level engines** (give price zones, feed future SL logic):
- [ ] **`support_resistance` engine** — classical S/R via pivot highs/lows
      on D1/H4. Lower priority now because ADR-0017 starts with SMC
      structure/order-block/liquidity engines.
- [ ] **`vwap` engine** — daily + weekly VWAP with ±1σ bands. Price position
      relative to VWAP as mean-reversion signal.
- [ ] **`volume_profile` engine** — POC, VAH, VAL from recent session volume.
      Requires tick-or-minute data; defer until data pipeline supports it.
- [ ] **`fibonacci` engine** — auto-drawn Fib retracements on the last
      significant swing. Defer until SMC core can provide reliable impulse
      legs; first use as confluence, not standalone direction.

**Volume / order-flow engines:**
- [ ] **`volume_delta` engine** — CVD (cumulative volume delta) / taker
      buy-sell volume imbalance. Directional pressure signal. Uses existing
      `taker_vol` data if backfilled.
- [ ] **`obv` engine** — On-Balance Volume trend confirmation.

**Price action / structure engines:**
- [x] **SMC specs** — `smc_core`, `smc_structure`, `smc_order_blocks`,
      `smc_liquidity` written for ADR-0017 (2026-06-01).
- [ ] **`fvg` engine** — Fair Value Gaps (imbalance candles). Defer until
      the PineScript `lookahead_on` MTF logic is rewritten safely.
- [ ] **`smc_premium_discount` engine** — premium/equilibrium/discount zones
      from the latest confirmed swing range. Defer until after first SMC report.

**Meta:**
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
