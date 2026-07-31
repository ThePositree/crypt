# Ideas

Owner-provided ideas to remember for later.

This file is intentionally separate from `BACKLOG.md`. Items here are not
approved work. Agents must not implement an idea from this file unless the
owner explicitly approves it in chat.

When an idea becomes relevant to the current work, remind the owner briefly,
explain why it may fit now or why it should wait, and ask for explicit approval
before moving it into `BACKLOG.md`, a spec, or code.

---

## 2026-06-12 — DSS optimizer research shortlist

**Status:** reference list for future backend selection.

**Context:** owner wants to run multiple searches in parallel, each with a
meaningfully different search algorithm. Current implemented backends are:
`directional`, `catcma_qd`, `island_qd`, `hyperband_qd`, and `smac_qd`.

**Research shortlist and fit:**

- **Hyperband / Successive Halving / DEHB-style QD** — implemented as
  `hyperband_qd` in ADR-0039.
- **SMAC-style conditional surrogate optimization** — implemented as
  `smac_qd` in ADR-0040 using `RandomForestRegressor`.
- **CatCMAwM mixed-variable search** — implemented in `catcma_qd` with the
  maintained `cmaes` package.
- **FuRBO / feasibility-driven trust-region BO** — attractive for mandate
  constraints after we find families near feasibility.
- **MOTPE / constrained TPE** — easy because Optuna exists, but less distinct
  from the retired DSS v1 Optuna path.
- **LLM-SAEA / LLM-guided surrogate-assisted EA** — interesting research idea
  but lower reproducibility and harder to test; keep for later.

**Remaining order:** FuRBO/feasibility-driven trust regions only after at least
one family is near mandate feasibility.

---

## 2026-06-03 — Cap outsized monthly backtest profits for calibration

**Status:** **approved** — moved to `docs/strategy_benchmark.md` and
ADR-0025 (2026-06-05).

**Policy:** `capped_monthly_return_pct = min(raw, 20%)` for ranking; pass/fail
uses raw `≥ 15%`. Implementation tracked in `BACKLOG.md`.

---

## 2026-06-08 — Expand strategy discovery trigger/filter catalog (v2+)

**Status:** **approved** — OHLCV-only v2 slice implemented 2026-06-08.

**Implemented (discovery-only, no donor conversion yet):**

- **+6 triggers:** `h1_ema_cross`, `h1_rsi_reversal`, `h1_bb_rejection`,
  `h1_engulfing`, `h1_inside_bar_breakout`, `h1_nr7_breakout`
- **+14 filters:** EMA stack, SMA20/RSI/ROC alignment, volatility low/high,
  BB squeeze/wide, candle anatomy, session London/NY, volume above median,
  trend strength max

**Catalog after v2:** 14 triggers + 33 filters. Spec: `docs/strategy_discovery.md` §7–8.

**Deferred (needs non-OHLCV data or ADR):** VWAP session, derivatives/OI,
BTC intermarket, execution-proxy filters, full SMC engine reuse, order flow.

**Remaining v2+ breadth** from the original inventory (~70–90 blocks) stays
queued in `BACKLOG.md` when owner wants the next expansion slice.

---
