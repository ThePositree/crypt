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
`staged`, `catcma_qd`, `island_qd`, `hyperband_qd`, and `smac_qd`.

**Research shortlist and fit:**

- **Hyperband / Successive Halving / DEHB-style QD** — implemented as
  `hyperband_qd` in ADR-0039.
- **SMAC-style conditional surrogate optimization** — implemented as
  `smac_qd` in ADR-0040 using `RandomForestRegressor`.
- **Full CatCMAwM** — useful for mixed categorical/integer/continuous mechanics
  but not enough by itself if windows conflict.
- **FuRBO / feasibility-driven trust-region BO** — attractive for mandate
  constraints after we find families near feasibility.
- **MOTPE / constrained TPE** — easy because Optuna exists, but less distinct
  from the retired DSS v1 Optuna path.
- **LLM-SAEA / LLM-guided surrogate-assisted EA** — interesting research idea
  but lower reproducibility and harder to test; keep for later.

**Remaining order:** full CatCMAwM only if current runs show promising families
that need better local mixed-variable tuning; FuRBO/feasibility-driven trust
regions only after at least one family is near mandate feasibility.

---

## 2026-06-11 — Full CatCMAwM optimizer backend for DSS

**Status:** idea for later — not approved for implementation yet.

**Idea:** replace or supplement the current lightweight `catcma_qd`
implementation with a fuller CatCMA with Margin style optimizer for Direct
Signal Search. The current backend is intentionally CatCMA-inspired: adaptive
weights over triggers, filters, and discrete execution params while reusing
DSS stages. A fuller implementation would add:

- fixed genome encoding/decoding for conditional trigger/filter spaces;
- continuous mean/covariance/step-size adaptation similar to CMA-ES;
- integer handling with margin so probabilities do not collapse too early;
- categorical probability updates with margin;
- population ranking from DSS Stage 1/2/3 outcomes;
- resumable optimizer state, e.g. `catcmawm_state.json`;
- optional quality-diversity archive integration as `catcmawm_qd`.

**Why it may fit:** DSS search is a mixed-variable expensive black-box problem:
categorical trigger/filter choices, integer lookbacks/TTL, continuous
thresholds and execution params, and expensive backtest-based scores.

**Why it should wait:** the lightweight `catcma_qd` backend is already
available for a non-duplicative home run while the work machine continues the
default DSS v2 run. Full CatCMAwM should be considered after comparing those
artifacts, unless the owner explicitly asks to prioritize optimizer research
over running current searches.

**Reference:** CatCMA with Margin for Single- and Multi-Objective
Mixed-Variable Black-Box Optimization, arXiv:2504.07884.

---

## 2026-06-03 — Cap outsized monthly backtest profits for calibration

**Status:** **approved** — moved to `docs/investment_mandate.md` §4 and
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
