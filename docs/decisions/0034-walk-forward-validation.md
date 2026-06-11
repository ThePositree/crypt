# ADR-0034: Walk-forward validation methodology

- **Status**: accepted
- **Date**: 2026-06-10
- **Supersedes**: —
- **Related**: ADR-0025 (investment mandate), ADR-0031 (mandate-aware Optuna target)

---

## Context

After running the NR4+VWAP strategy on 3 years of SOL/TON data (2022–2025), the owner
observed that the strategy returns ~0 or small negative on the full 3-year horizon but
performs well in 2024–2025 (the Optuna training window). This raises the core question:

> **Is the strategy's edge real and generalizable, or is it an artifact of fitting
> parameters to a specific market regime (2024–2025 bull market)?**

Standard backtesting cannot answer this. Optimizing on a fixed window and then evaluating
on the same window always looks good. Re-optimizing on 3 years would just re-fit to
3 years. The only principled answer comes from **walk-forward analysis**:

1. Divide history into rolling IS (in-sample) + OOS (out-of-sample) windows.
2. Optimize parameters on each IS window.
3. Evaluate those parameters on the immediately following OOS window (unseen data).
4. Aggregate OOS results to assess whether the edge persists out-of-sample.

If OOS results are consistently positive across multiple windows and market regimes, the
concept has genuine edge. If OOS results are consistently negative, the strategy is
curve-fitting the training window and should be discarded or redesigned.

---

## Decisions

### 1. Rolling anchor-point windows

Each OOS period immediately follows its IS period with no gap. The IS window slides
forward by `oos_months` at each step (anchor-point walk-forward, most common variant).

```
is_months=12  oos_months=6  from=2022-01  to=2025-12

Window 1: IS 2022-01–2022-12 → OOS 2023-01–2023-06
Window 2: IS 2022-07–2023-06 → OOS 2023-07–2023-12
Window 3: IS 2023-01–2023-12 → OOS 2024-01–2024-06
Window 4: IS 2023-07–2024-06 → OOS 2024-07–2024-12
Window 5: IS 2024-01–2024-12 → OOS 2025-01–2025-06
Window 6: IS 2024-07–2025-06 → OOS 2025-07–2025-12
```

Rationale: This produces the maximum number of OOS windows for a given date range and
IS/OOS size, and ensures every OOS window tests generalization to a regime the optimizer
never saw.

### 2. Optuna optimization on IS, single backtest on OOS

Each IS window runs a fresh Optuna study (same target and search space as the main
`optimize` command) with a configurable number of trials. The OOS window is evaluated
exactly once with the IS-best params — no second optimization.

Rationale: Optimizing on OOS would defeat the purpose of the test.

### 3. Data sliced from a single loaded StrategyData

The full historical data is loaded once and sliced in memory for each IS/OOS window.
This avoids N×2 Parquet I/O calls and ensures the exact same bar set is used for
slicing as for the full-history backtester commands.

### 4. Evaluation metric: total_return_pct per OOS window + mandate_score if window ≥ 3 months

For OOS windows shorter than 3 months, `mandate_score` is not meaningful (too few
monthly data points). We report `total_return_pct`, `win_rate`, `max_drawdown`, and
`trades` for all windows; `mandate_score` only when `oos_months >= 3`.

### 5. IS→OOS degradation ratio

Each window reports `degradation = oos_return / is_return`. A ratio < 0 means the OOS
was negative regardless of IS sign. A ratio of 0.3–0.5 is typical for real edge.
Ratios > 1 are implausible at scale (IS was unusually bad, or luck in OOS).

### 6. Supported OOS-only mode (--trials 0)

When `--trials 0`, skip IS optimization and evaluate each OOS window with the base
strategy config params directly. This is a fast "per-year audit" — useful to diagnose
which calendar periods the strategy fails on with current params, without the overhead
of N optimization runs.

### 7. Output artifacts

```
results/walk_forward/<timestamp>/
├── summary.md          # Human-readable report with per-window table
├── summary.json        # Machine-readable: all window results
└── windows/
    └── <window_label>/
        ├── is_best_trial.json
        ├── is_trials.csv     (Optuna trials for the IS window)
        └── oos_metrics.json
```

---

## Consequences

- Adds `backtester walk-forward` CLI command.
- Walk-forward runs are expensive: N windows × M trials × backtest time.
  Typical run: 6 windows × 50 trials = ~300 backtests (minutes, not hours).
- The command is owner-run per standard backtest workflow (AGENTS.md §2).
- Walk-forward results directly answer the promote/archive/discard question for NR4.
