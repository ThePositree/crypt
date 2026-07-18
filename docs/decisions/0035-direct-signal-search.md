# ADR-0035: Direct Signal Search (DSS) — parameterized multi-objective strategy discovery

- **Status**: superseded by ADR-0036
- **Date**: 2026-06-10
- **Supersedes**: —
- **Related**: ADR-0025 (investment mandate), ADR-0031 (mandate-aware Optuna),
  ADR-0034 (walk-forward), ADR-0023 (backtester integration)

---

## Supersession note

ADR-0036 replaces this design after the first long real SOL run showed that the
NSGA-II DSS implementation collapses into a local trigger family and does not
improve robust mandate score after thousands of trials. This ADR remains as
historical context only. New implementation work must follow
`docs/discovery/direct_signal_search_v2.md`.

## Context

Walk-forward validation (ADR-0034) confirmed that NR4+VWAP is regime-dependent: it
only works in the 2024-2025 bull market. No parameter tuning fixes structural
regime-specificity. The conclusion: the discovery pipeline that produced NR4 has two
fundamental limitations that must be addressed before investing more time in candidates.

### Limitation 1 — Forward-label proxy, not PnL

The current `discover-strategies` beam search optimizes a **forward-label win-rate**
(price reaches ATR×1.0 target before adverse ATR×1.0). This is a useful proxy but does
not align with the actual mandate criterion (consistent monthly PnL after fees, leverage,
position sizing, and drawdown constraints). A signal with 58% forward win-rate can still
fail the mandate because:

- winning trades are small, losing trades are large (asymmetric)
- it fires many times during a drawdown month, compounding losses
- fees and spread erode the edge when trading frequently

### Limitation 2 — Hardcoded trigger/filter constants

Every trigger and filter has constants baked in (e.g., `rolling(12)`, `atr_mult=1.0`,
`window=20`). These constants were chosen by judgment, not searched. A trigger that
barely misses the mandate with `rolling(12)` might pass with `rolling(8)` or `rolling(16)`.
By not parameterizing thresholds, we discard a large part of the search space.

### Limitation 3 — Greedy beam search

Beam search fixes a trigger, then greedily adds filters by marginal win-rate improvement.
It cannot discover combinations where **filter A alone hurts** but **filter A + filter B
together improve** (interaction effects). It also does not search execution parameters
(rrr, ttl, risk_percent) jointly with signal parameters; these are optimized separately
after discovery, introducing a sequential bias.

---

## Decision

Build **Direct Signal Search (DSS)** — a new discovery mode that:

1. **Evaluates directly on mandate_score**, not forward labels.
2. **Parameterizes triggers and filters** (thresholds as float/int Optuna variables).
3. **Searches signal + execution jointly** in one Optuna study.
4. **Uses multi-objective optimization** (NSGA-II) across ≥3 independent time windows.
5. **Runs for hours/days** with a persistent Optuna journal so it can be interrupted
   and resumed.

---

## Architecture

```
backtester search-signals
        │
        ├─ DSS Config (windows, search space, n_trials, output)
        │
        ├─ Optuna NSGA-II study  ←──── persistent Journal (resumable)
        │       │
        │       └─ trial: suggest signal config + params
        │               │
        │               ├─ SignalComposer.build(config)
        │               │       → generate(StrategyData) → pd.DataFrame
        │               │
        │               ├─ signal cache (keyed by signal_config hash)
        │               │       → skip re-generation when only exec params differ
        │               │
        │               └─ for each window:
        │                       Backtester.run(signal, exec_params)
        │                       → mandate_score(result)
        │
        └─ Pareto front report
                ├─ pareto_front.json  (all non-dominated solutions)
                ├─ summary.md        (top candidates per "regime" cluster)
                └─ candidates/       (one JSON per top-N candidate, ready for compare-fixed)
```

### Trial space

Each Optuna trial suggests:

```
signal_config:
    trigger_name          categorical  (~40 choices)
    n_filters             int          [0, 4]
    filter_{i}            categorical  (~50 choices each)
    trigger_params:
        window            int          [4, 24]    # rolling window for most triggers
        threshold         float        [0.5, 3.0] # ATR multiplier / pct threshold
    filter_params:
        atr_mult_low      float        [0.0, 2.0] # ATR distance band low
        atr_mult_high     float        [1.0, 6.0] # ATR distance band high
        body_ratio        float        [0.1, 0.6] # min body-to-range
        vwap_dist_max     float        [0.005, 0.03]
        ...

exec_params:
    rrr                   float        [1.5, 4.0, step=0.25]
    risk_percent          float        [1.0, 3.0, step=0.25]
    position_ttl_bars     int          [24, 60]
```

### Objective (multi-objective)

For N windows (typically 3-4 calendar years), return a score vector:

```python
objectives = [mandate_score(run(window_i)) for i in range(N)]
```

`NSGAIISampler` finds the Pareto front: solutions where no window can be improved
without degrading another. A candidate is only useful if it is non-dominated and has
mandate_score > ACCEPT_THRESHOLD (e.g. -500) on **all** windows simultaneously.

### Signal caching

Signal generation (trigger + filters applied to OHLCV) is the expensive step. Within
one trial, the same signal config can be reused for all windows (just sliced differently).
Across trials, if two trials share the same signal config (but different exec params),
signal generation is cached. Cache key = `hash(trigger_name, filter_names_sorted, trigger_params, filter_params)`.

---

## New components

| Component | Path | Responsibility |
|---|---|---|
| `ParameterizedTrigger` | `strategy_discovery/parameterized_triggers.py` | Trigger factories with float/int params |
| `ParameterizedFilter` | `strategy_discovery/parameterized_filters.py` | Filter factories with float/int params |
| `SignalComposer` | `strategy_discovery/signal_composer.py` | Builds `generate()` from trial config |
| `DSSObjective` | `strategy_discovery/dss_objective.py` | Optuna objective: run → mandate_score per window |
| `DSSConfig` | `strategy_discovery/dss_config.py` | Search space bounds, window list, n_trials |
| `DSSReport` | `strategy_discovery/dss_report.py` | Pareto front, cluster summary, candidate JSONs |
| `search_signals` CLI | `backtester/__main__.py` | `backtester search-signals` entry point |

---

## Compatibility

- Existing `discover-strategies` command is **not modified or removed**.
- `SignalComposer` produces `generate(StrategyData) -> pd.DataFrame` output identical to
  `crypt_ensemble.generate()`, so all downstream tooling (compare-fixed, optimize,
  walk-forward) works without changes.
- Candidate JSON files output by DSS follow the same schema as existing
  `strategies/backtester/*.json` configs (via the existing `convert.py` translation layer).

---

## Consequences

- New `backtester search-signals` CLI command.
- DSS runs are expensive and owner-run (same rule as all backtester commands per AGENTS.md).
- The Optuna Journal is persistent: runs can be interrupted and resumed with `--resume`.
- A completed DSS study produces candidate configs that feed directly into `compare-fixed`
  and `walk-forward` for final mandate validation.
- Implementation estimate: ~2 weeks (parameterized catalog ~3 days,
  SignalComposer ~2 days, DSSObjective + study ~3 days, report ~2 days, CLI ~1 day,
  tests ~3 days).
