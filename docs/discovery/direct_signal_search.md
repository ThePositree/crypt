# Direct Signal Search (DSS) v1 — superseded specification

> **Status**: superseded by ADR-0036
> **Introduced**: 2026-06-10
> **Depends on**: walk-forward (ADR-0034), mandate-aware Optuna (ADR-0031)

This document is historical. The NSGA-II full-trial implementation described
here is retired after the first long real SOL run collapsed into a local
EMA-cross family without producing any viable robust candidate. New work must
follow `docs/discovery/direct_signal_search_v2.md`.

---

## 1. Why

The existing `discover-strategies` beam search found NR4+VWAP, which only works in the
2024-2025 regime (confirmed by walk-forward, ADR-0034). Two root causes:

1. **Proxy objective**: beam search maximizes forward-label win-rate, not mandate_score.
2. **Fixed constants**: every trigger/filter has hardcoded thresholds — ATR window sizes,
   rolling periods, price ratios. The optimal threshold is undiscovered.

DSS replaces the beam search with a Optuna NSGA-II study that:
- optimizes **mandate_score** directly (same formula as optimizer.py and ADR-0031)
- searches **jointly** over trigger choice, filter combination, signal parameters, and
  execution parameters
- evaluates on **multiple independent time windows** in one study
- runs for hours or days, resumable, producing a Pareto front of regime-robust candidates

---

## 2. Module layout

```
src/backtester/strategy_discovery/
├── __init__.py                     (existing; no changes)
├── events.py                       (existing; no changes)
├── features.py                     (existing; no changes)
├── triggers.py                     (existing; no changes)
├── catalog_expansion.py            (existing; no changes)
├── filters.py                      (existing; no changes)
├── labeler.py                      (existing; no changes)
├── scoring.py                      (existing; no changes)
├── search.py                       (existing beam search; no changes)
├── convert.py                      (existing; no changes)
├── report.py                       (existing; no changes)
│
├── parameterized_triggers.py       [NEW] parameterized trigger factories
├── parameterized_filters.py        [NEW] parameterized filter factories
├── signal_composer.py              [NEW] builds generate() from TrialConfig
├── dss_config.py                   [NEW] DSSConfig + search space bounds
├── dss_objective.py                [NEW] Optuna objective: multi-window mandate_score
├── dss_cache.py                    [NEW] signal generation cache
└── dss_report.py                   [NEW] Pareto front reports + candidate JSON export
```

The CLI entry point is added to `src/backtester/__main__.py` as a new
`search-signals` subcommand. The CLI is the only owner-facing interface.

---

## 3. Data flow

```
backtester search-signals \
    --windows 2022,2023,2024,2025H1 \
    --n-trials 50000 \
    --output results/dss_run_01/ \
    [--resume results/dss_run_01/study.journal]

    1. Load OHLCV Parquet for each window into StrategyData objects.
    2. Create (or resume) Optuna JournalStorage study with NSGAIISampler.
    3. For each trial:
        a. Sample TrialConfig from Optuna (trigger + params + filters + params + exec params).
        b. Check signal cache: if (trigger, filters, signal_params) seen before,
           reuse pre-computed signal DataFrame for each window.
        c. Otherwise call SignalComposer.build(config) → generate_fn,
           then generate_fn(window_data) for each window.
        d. Run backtester on each (signal, exec_params, window_data).
        e. Compute mandate_score per window.
        f. Return [score_window_0, score_window_1, ...] to Optuna.
    4. After n_trials: extract Pareto front, filter dominated solutions,
       write DSSReport artifacts.
```

---

## 4. Key types

### 4.1 TrialConfig

Immutable snapshot of everything needed to reproduce a trial.

```python
@dataclass(frozen=True, slots=True)
class TrialConfig:
    trigger_name: str
    trigger_params: dict[str, float | int]
    filter_names: tuple[str, ...]            # sorted for canonical identity
    filter_params: dict[str, dict[str, float | int]]  # keyed by filter_name
    rrr: float
    risk_percent: float
    position_ttl_bars: int

    @property
    def signal_cache_key(self) -> str:
        """Key covering signal shape only (not exec params)."""
        return hashlib.sha1(
            json.dumps(
                {
                    "trigger": self.trigger_name,
                    "trigger_params": self.trigger_params,
                    "filters": list(self.filter_names),
                    "filter_params": self.filter_params,
                },
                sort_keys=True,
            ).encode()
        ).hexdigest()
```

### 4.2 SignalRow (output of generate_fn)

The generate function must return a `pd.DataFrame` with exactly these columns
(same schema as all other generate functions in the project):

| column | dtype | notes |
|---|---|---|
| `bar_time` | datetime64[ns, UTC] | closed candle time |
| `symbol` | str | |
| `side` | Literal["long","short"] | |
| `confidence` | float | 0..100 |
| `rationale` | str | brief human-readable |
| `entry_price` | float | |
| `stop_price` | float | ATR-based SL from SignalComposer |
| `tp_price` | float | entry ± (entry–stop) × rrr |

`stop_price` and `tp_price` are computed by `SignalComposer` using the
parameterized `atr_sl_mult` parameter.

### 4.3 WindowSpec

```python
@dataclass(frozen=True, slots=True)
class WindowSpec:
    label: str          # "2022", "2023", "2024", "2025H1"
    symbol: str         # "SOLUSDT" etc.
    start: str          # "2022-01-01"
    end: str            # "2022-12-31"
```

---

## 5. Parameterized triggers

### Signature

```python
ParameterizedTriggerFn = Callable[
    [DiscoveryDataset, TriggerParams], list[DiscoveryEvent]
]
```

where `TriggerParams` is a `dict[str, float | int]`.

Each parameterized trigger exposes a `param_space()` static method:

```python
def param_space() -> dict[str, ParamDef]:
    return {
        "window":    IntParam(low=4,  high=24,  step=1),
        "threshold": FloatParam(low=0.3, high=3.0, step=None),
    }
```

`ParamDef` variants: `IntParam(low, high, step)`, `FloatParam(low, high)`,
`CategoricalParam(choices)`.

### Parameterized trigger catalog

| name | key params | notes |
|---|---|---|
| `pt_sweep_reversal` | `window` [6,24] | prior low/high lookback |
| `pt_structure_break` | `window` [8,40] | structure lookback |
| `pt_range_breakout` | `window` [8,48] | Donchian width |
| `pt_momentum_burst` | `threshold` [1.0,4.0] | ATR mult for body |
| `pt_mean_revert_wick` | `window` [4,24], `threshold` [0.3,2.0] | |
| `pt_ema_cross` | `fast` [4,20], `slow` [20,100] | |
| `pt_rsi_reversal` | `period` [7,21], `oversold` [20,40], `overbought` [60,80] | |
| `pt_bb_rejection` | `period` [14,28], `std` [1.5,2.5] | |
| `pt_engulfing` | `body_ratio` [0.6,1.0] | min engulf pct |
| `pt_nr4_breakout` | `lookback` [3,8] | NR-N generalization |
| `pt_nr14_breakout` | `lookback` [8,20] | |
| `pt_vwap_reclaim` | `tolerance` [0.001,0.02] | proximity tolerance |
| `pt_compression_breakout` | `window` [8,24], `threshold` [0.3,1.5] | ATR compression |
| `pt_pivot_reclaim` | `window` [12,48] | |
| `pt_volume_spike` | `mult` [1.5,5.0] | vol/median |
| `pt_hammer` | `shadow_ratio` [1.5,4.0], `body_ratio` [0.05,0.3] | |
| `pt_pin_bar` | `shadow_ratio` [2.0,5.0] | |
| `pt_candle_confirm` | `body_ratio` [0.1,0.8] | min body |
| `pt_order_block_retest` | `tolerance` [0.3,1.0] | midpoint tolerance ATR |
| `pt_double_bottom_sweep` | `window` [4,16], `tolerance` [0.1,0.5] | |

All `pt_*` triggers are parallel reimplementations of their `h1_*` counterparts with
params exposed. The existing `h1_*` triggers remain unchanged and discoverable by the
beam search.

---

## 6. Parameterized filters

### Signature

```python
ParameterizedFilterFn = Callable[
    [DiscoveryEvent, DiscoveryDataset, FilterParams], FilterResult
]
FilterParams = dict[str, float | int]
```

Each parameterized filter also exposes `param_space()`.

### Parameterized filter catalog

| name | key params | notes |
|---|---|---|
| `pf_atr_distance_band` | `low_mult` [0.0,3.0], `high_mult` [0.5,6.0] | ATR distance from close |
| `pf_body_to_range_min` | `ratio` [0.05,0.7] | body/range threshold |
| `pf_trend_strength` | `min_atr` [0.2,2.0] | EMA slope |
| `pf_rsi_zone` | `low` [20,60], `high` [40,80] | RSI band |
| `pf_volume_ratio` | `min_ratio` [0.5,3.0] | vol/median |
| `pf_bb_width` | `max_width_pct` [0.01,0.08] | squeeze threshold |
| `pf_vwap_proximity` | `max_dist_pct` [0.003,0.05] | |
| `pf_context_aligned` | `timeframe` categorical["h4","d1"] | |
| `pf_session` | `session` categorical["london","ny","asia"] | |
| `pf_anchor_age` | `max_hours` [4,120] | |
| `pf_avoid_large_move` | `threshold_atr` [1.5,5.0] | last N bars move |
| `pf_trend_ema_stack` | `fast` [8,20], `mid` [20,50], `slow` [50,200] | |
| `pf_bar_range_min` | `min_atr_mult` [0.2,1.5] | |
| `pf_no_liquidity_sweep` | *(binary — no params)* | fixed, no params |
| `pf_side_long_only` | *(binary)* | |
| `pf_side_short_only` | *(binary)* | |

---

## 7. SignalComposer

`SignalComposer` bridges a `TrialConfig` and the backtester.

### Contract

```python
class SignalComposer:
    def build(self, config: TrialConfig) -> GenerateFn:
        """
        Returns a generate function compatible with all downstream tooling:
            generate_fn(data: StrategyData) -> pd.DataFrame
        The returned function is pure (no I/O, no global state).
        """
```

### Internal steps of `build()`

1. Look up `trigger_factory(config.trigger_name)` from parameterized catalog.
2. Bind trigger params: `trigger_fn = partial(trigger_factory, params=config.trigger_params)`.
3. For each filter name in `config.filter_names`, look up filter factory, bind params.
4. Build `atr_sl_mult` from `config.trigger_params.get("atr_sl_mult", 1.0)`.
5. Return a closure that:
   a. Calls `build_discovery_dataset(data)` to get `DiscoveryDataset`.
   b. Runs trigger to get `list[DiscoveryEvent]`.
   c. For each event, runs all filters; drops event if any filter fails.
   d. Computes ATR at event time.
   e. Constructs `stop_price = entry ∓ atr × atr_sl_mult` (direction-aware).
   f. Constructs `tp_price = entry ± (entry - stop) × rrr`.
   g. Returns DataFrame with SignalRow schema.

See `docs/discovery/signal_composer.md` for the full contract.

---

## 8. DSSObjective (Optuna objective)

```python
class DSSObjective:
    def __init__(
        self,
        windows: list[WindowSpec],
        window_data: dict[str, StrategyData],   # keyed by WindowSpec.label
        search_space: DSSSearchSpace,
        signal_cache: DSSSignalCache,
        execution_context: StrategyExecutionContext,
    ) -> None: ...

    def __call__(self, trial: optuna.Trial) -> tuple[float, ...]:
        config = _sample_trial_config(trial, self.search_space)
        scores: list[float] = []
        for spec in self.windows:
            signal_df = self.signal_cache.get_or_compute(config, spec.label)
            if signal_df.empty:
                scores.append(-10_000.0)   # penalize zero-signal configs heavily
                continue
            result = _run_backtest(signal_df, config, self.window_data[spec.label], self.execution_context)
            scores.append(_mandate_score(result))
        return tuple(scores)
```

### mandate_score formula

Aligned with the money/drawdown-aware optimizer target:

```
score = total_return_pct × 100.0
      + sum_capped_monthly_return_pct × 10.0
      - monthly_shortfall_pct × 1.5
      - dd_excess_pct × 35.0
      - dd_breach_months × 150.0
      - max(months_below_floor - 12, 0) × 75.0
      - excess_losing_streak × 250.0
      - downside_drawdown_pct² × 85.0
```

### Empty signal penalty

If the trial config generates < `min_trades_per_window` (default 20) signals in any
window, that window score is `-10_000.0`. This prevents the sampler from wasting trials
on combinations that never fire.

---

## 9. DSSConfig

```python
@dataclass(frozen=True)
class DSSConfig:
    output: Path
    windows: list[WindowSpec]
    n_trials: int                         = 50_000
    n_jobs: int                           = 1        # parallel Optuna workers
    max_filters: int                      = 4
    min_trades_per_window: int            = 20
    resume_journal: Path | None           = None     # --resume flag
    sampler: Literal["nsga2","tpe","random"] = "nsga2"
    accept_min_score_per_window: float    = -500.0   # filter threshold for report
    top_n_candidates: int                 = 20       # candidates to export to JSON
```

### Search space bounds (DSSSearchSpace)

Stored in `dss_config.py` as a frozen dataclass with per-param ranges. All bounds are
hardcoded with clear names; they can be overridden from CLI flags.

```python
@dataclass(frozen=True)
class DSSSearchSpace:
    trigger_names: tuple[str, ...]    # all keys from parameterized_trigger_catalog()
    filter_names: tuple[str, ...]     # all keys from parameterized_filter_catalog()
    trigger_param_bounds: dict[str, ParamDef]
    filter_param_bounds: dict[str, ParamDef]
    rrr_range: FloatRange             = (1.5, 4.0, 0.25)
    risk_percent_range: FloatRange    = (1.0, 3.0, 0.25)
    position_ttl_bars_range: IntRange = (24, 72, 4)
    atr_sl_mult_range: FloatRange     = (0.5, 2.5, 0.25)
```

---

## 10. DSSSignalCache

```python
class DSSSignalCache:
    """LRU cache for signal DataFrames, keyed by (signal_cache_key, window_label)."""
    def __init__(self, max_entries: int = 2_000) -> None: ...
    def get_or_compute(
        self,
        config: TrialConfig,
        window_label: str,
        compute_fn: Callable[[], pd.DataFrame],
    ) -> pd.DataFrame: ...
```

The cache is per-process (not shared between parallel workers, since each worker has its
own Python process). Max 2_000 entries prevents OOM on long runs.

---

## 11. DSSReport

After `n_trials`, the report writer:

1. Extracts all trials with `state == COMPLETE`.
2. Computes Pareto front (`optuna.visualization.plot_pareto_front` internally,
   but the raw front is written as JSON).
3. Filters to solutions where `all(score > accept_min_score_per_window)`.
4. Clusters by regime "specialty" (best on which window) — 3-4 clusters.
5. Selects top-N by `min(scores)` (most robust across all windows).
6. Exports each top-N candidate as a `strategies/backtester/*.json` compatible config.

### Output artifacts

```
results/dss_run_01/
├── study.journal               # Optuna JournalStorage (resumable)
├── pareto_front.json           # all non-dominated complete trials
├── summary.md                  # human-readable top-N table
├── score_history.png           # per-window score over trials (optional)
└── candidates/
    ├── dss_001_sol_trigger_pt_nr4_rrr2.5.json
    ├── dss_002_sol_trigger_pt_vwap_reclaim_rrr2.0.json
    └── ...
```

`pareto_front.json` schema:

```jsonc
{
  "study_name": "dss_run_01",
  "n_trials": 50000,
  "n_pareto": 312,
  "windows": ["2022", "2023", "2024", "2025H1"],
  "solutions": [
    {
      "trial_number": 14827,
      "params": { "trigger_name": "pt_nr4_breakout", "window": 5, "rrr": 2.5, ... },
      "scores": { "2022": -120.3, "2023": 41.8, "2024": 213.4, "2025H1": 88.2 },
      "min_score": -120.3,
      "candidate_id": "dss_001_sol_trigger_pt_nr4_rrr2.5"
    },
    ...
  ]
}
```

Candidate JSON format is identical to existing `strategies/backtester/*.json`
configs so `compare-fixed` and `walk-forward` work without changes.

---

## 12. CLI reference

```
backtester search-signals [OPTIONS]

  --symbol TEXT            Symbol to search on (can repeat: --symbol SOLUSDT --symbol TONUSDT)
  --windows TEXT           Comma-separated window specs: YYYY or YYYYHH. Default: 2022,2023,2024,2025H1
  --n-trials INT           Total Optuna trials. Default: 50000
  --n-jobs INT             Parallel Optuna workers. Default: 1
  --max-filters INT        Max filters per candidate. Default: 4
  --sampler [nsga2|tpe|random]  Default: nsga2
  --resume PATH            Resume from existing journal file.
  --output PATH            Output directory. Default: results/dss_{timestamp}/
  --top-n INT              Candidates to export. Default: 20
  --accept-min-score FLOAT Minimum per-window score to include in report. Default: -500
  --min-trades INT         Minimum signals per window to not penalize. Default: 20
```

Example — 1-week run on SOL, 4 windows, 8 parallel workers:

```bash
backtester search-signals \
  --symbol SOLUSDT \
  --windows 2022,2023,2024,2025H1 \
  --n-trials 500000 \
  --n-jobs 8 \
  --output results/dss_sol_maxrun/
```

To resume after interruption:

```bash
backtester search-signals \
  --symbol SOLUSDT \
  --windows 2022,2023,2024,2025H1 \
  --n-trials 500000 \
  --n-jobs 8 \
  --resume results/dss_sol_maxrun/study.journal \
  --output results/dss_sol_maxrun/
```

---

## 13. Integration with downstream tooling

After a DSS run, the owner validates top candidates with:

```bash
# Quick multi-window comparison
backtester compare-fixed \
  --candidates results/dss_sol_maxrun/candidates/ \
  --output results/compare_dss_top20/

# Deep walk-forward for top 3
backtester walk-forward \
  --config results/dss_sol_maxrun/candidates/dss_001.json \
  --is-months 12 --oos-months 3 --trials 200 \
  --output results/wf_dss_001/
```

If a candidate passes walk-forward, it follows the normal promote flow (ADR-0025):
gate-1 check → PR → merge to `strategies/` → live monitoring.

---

## 14. Implementation sequence

| Phase | Scope | Est. |
|---|---|---|
| P1 — Parameterized catalog | `parameterized_triggers.py`, `parameterized_filters.py`, `param_space()` on each | 3 days |
| P2 — SignalComposer | `signal_composer.py`, unit tests | 2 days |
| P3 — DSSObjective + study | `dss_config.py`, `dss_objective.py`, `dss_cache.py` | 3 days |
| P4 — Report + CLI | `dss_report.py`, CLI in `__main__.py` | 2 days |
| P5 — Integration tests | end-to-end with 100 trials on fake data | 2 days |
| **Total** | | **~12 days** |

All phases have independent tests. P3 depends on P1+P2. P4 depends on P3. P5 is final.
