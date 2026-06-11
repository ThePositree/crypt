# ADR-0036: Replace DSS v1 with staged quality-diversity search

- **Status**: accepted
- **Date**: 2026-06-11
- **Supersedes**: ADR-0035
- **Related**: ADR-0025 (investment mandate), ADR-0031 (mandate-aware
  Optuna target), ADR-0034 (walk-forward validation)

---

## Context

ADR-0035 introduced Direct Signal Search (DSS) as a multi-objective Optuna
NSGA-II study over parameterized triggers, filters, and execution parameters.
It was the right architectural direction compared with the older beam-search
discovery because it optimized the mandate score directly and exposed hidden
constants as search dimensions.

The first long real SOL run showed that the implementation is still the wrong
search algorithm for this problem.

Observed run:

- Artifact: `results/dss_sol_run_5k/study.journal`
- Wall time at inspection: around 23 hours
- Completed trials at inspection: about 16.5k
- Windows: `2022`, `2023`, `2024`, `2025H1`
- Best robust score, measured as `min(score_window_i)`: **-4626.74**
- Trials with `min_score > -500`: **0**
- Trials with `min_score > 0`: **0**
- Best robust score stopped improving after about trial `7064`
- Top-50 trials collapsed almost entirely into one local family:
  - trigger: `pt_ema_cross` in 45/50
  - `rrr = 4.0` in 45/50
  - `atr_sl_mult = 2.25` or `2.5`
  - `position_ttl_bars` mostly `48` to `72`

Best observed trial:

```text
trial: 7064
scores: [-4626.74, -4273.06, -3946.31, -3175.80]
trigger: pt_ema_cross
filters: pf_body_to_range_min, pf_anchor_age, pf_volume_ratio
rrr: 4.0
ttl: 60
risk_percent: 2.0
atr_sl_mult: 2.25
```

This is not merely "not enough trials". The study already spent thousands of
trials after the best robust candidate without improving it, and the elite set
lost trigger-family diversity. Letting the same implementation run longer is
unlikely to discover a materially different strategy family.

The practical failure modes are:

1. **Flat full-cost evaluation**: every trial pays for full multi-window
   backtests even when the signal is obviously poor.
2. **No staged elimination**: weak trigger/filter families are not discarded
   cheaply, and promising families are not promoted through progressively
   harder budgets.
3. **No quality-diversity archive**: the search can collapse into one local
   family, such as EMA-cross, while other niches receive little pressure.
4. **Objective shape is hostile to discovery**: a four-objective Pareto front
   does not force robust `min_score` improvement and does not explicitly
   optimize the owner mandate gates as feasibility constraints.
5. **Conditional categorical space is under-modeled**: NSGA-II with default
   settings does not exploit the tree-structured relationship between trigger
   choice, trigger parameters, filter choices, filter parameters, and
   execution geometry.

---

## Decision

Replace the current implementation behind `backtester search-signals` with a
new **DSS v2 staged quality-diversity search**.

Do **not** keep the current NSGA-II implementation as an operator-facing mode.
The command name remains the same because owner workflow should not branch into
"old DSS" versus "new DSS". The command contract changes; the old behavior is
retired.

The new `search-signals` command must:

1. Use a staged evaluation pipeline:
   - Stage 0: stratified coverage of signal families
   - Stage 1: cheap signal viability scoring
   - Stage 2: proxy backtests on cheap budgets
   - Stage 3: full multi-window mandate backtests
   - Stage 4: holdout replay and export
2. Maintain a quality-diversity archive so each behavior niche keeps its best
   candidate instead of allowing one family to monopolize the search.
3. Optimize robust scalar fitness for ranking while still exporting per-window
   mandate diagnostics.
4. Treat mandate gate failures as constraints where possible, not only as large
   additive penalties.
5. Keep the existing owner-facing command simple. Prefer replacing defaults and
   internals over adding flags that expose algorithm experiments.

---

## Algorithmic basis

This decision is informed by several algorithm families:

- **BOHB / DEHB / MO-DEHB**: combine model-guided or evolutionary search with
  Hyperband-style staged budgets. Relevant because DSS trials are expensive and
  most candidates can be eliminated before full backtests.
- **SMAC-style algorithm configuration**: random-forest surrogate optimization
  handles conditional categorical spaces better than vanilla GP assumptions.
- **MOTPE / constrained TPE**: Optuna's TPE supports multi-objective studies,
  grouped multivariate conditional spaces, parallel constant-liar behavior, and
  constraints. This is a better in-repo first step than default NSGA-II.
- **MAP-Elites / Quality Diversity / BOP-Elites**: keep high-performing but
  behaviorally different solutions. Relevant because trading strategy discovery
  needs a portfolio of candidate families, not a single local optimum.
- **Local trust-region BO for mixed spaces**: Bounce/CASMOPOLITAN-style ideas
  support the longer-term direction if Optuna-native methods remain weak.

The immediate implementation should stay pragmatic and repo-native:

- no new heavy research dependency in the first v2 slice;
- no BoTorch/SMAC/DEHB integration until the staged archive proves useful;
- use simple deterministic archives, scalar robust ranking, and Optuna TPE
  where it fits cleanly.

---

## Consequences

- ADR-0035 remains historical documentation for DSS v1 but is no longer the
  target implementation.
- `docs/discovery/direct_signal_search_v2.md` becomes the implementation
  contract.
- The current `backtester search-signals` internals may be deleted or rewritten
  in place. Compatibility with v1 journal format is not required.
- Existing v1 artifacts under `results/dss_*` are diagnostic only. They should
  not be used for candidate promotion.
- Candidate JSON output should remain compatible with `compare-fixed` and
  `walk-forward`.
- The next implementation session should work from the v2 spec, not tune
  NSGA-II knobs.

---

## Acceptance

The decision is implemented when:

1. `backtester search-signals` runs the staged DSS v2 pipeline by default.
2. There is no operator-facing option that invokes the retired v1 NSGA-II path.
3. Reports show stage counts, archive occupancy, best candidate per niche, and
   robust score history.
4. A smoke run on synthetic data proves that:
   - weak candidates are eliminated before full backtest;
   - multiple trigger families survive into the archive;
   - output candidate JSONs replay through `DSSStrategy`.
5. A bounded owner-run SOL search produces a report that is interpretable even
   if no candidate passes the mandate.

