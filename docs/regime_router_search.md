# Regime router search

Status: **MVP implemented and first full search completed**.

The router is a live-safe single-strategy selector. It does not split capital
between strategies.

```text
all archived strategies
  -> score every available strategy from completed prior labels
  -> select exactly one strategy
  -> apply switching policy
  -> score by offset-robust regret to the single-strategy oracle
```

## Contract

The router consumes `rolling_labels.csv` from `backtester rolling-regime-labels`.
Each row contains:

- `asof` and `label_end`;
- one `return_<strategy_id>` column per archived strategy;
- oracle columns such as `best_strategy`, `best_return_pct`, and
  `margin_to_second_pct`;
- detector-safe market features computed strictly before `asof`.

The router may train only on rows where `label_end <= asof`.

## PineScript-derived features

`rolling-regime-labels` now exports `router_ps_*` features derived from the
local PineScript idea set through the native Python feature implementation in
`src/backtester/strategy_discovery/features.py`. PineScript files are reference
material, not runtime code.

Current feature families:

- Supertrend direction and flip age;
- ADX/DI strength and side;
- BB/Keltner squeeze state, release age, and momentum;
- WaveTrend spread, zone, and cross age;
- MACD histogram phase and slope;
- Williams Vix Fix spike and age;
- pivot trendline break side and slopes;
- ICT killzone code;
- SMC internal/swing bias, structure events, FVG, equal levels,
  premium/discount zone, and order-block state.

## Catalog

Search candidates combine:

- scoring method: rolling mean, rolling median, mean minus drawdown, mean minus
  negative-rate, feature-KNN mean/median/return-DD, same-state mean/return-DD;
- lookback: 30, 60, 90, 120, 180, 270, 365, 540 days;
- feature set: OHLCV, PineScript-derived, or mixed;
- switching policy: minimum hold days and required improvement over the current
  held strategy.

The output strategy set is fixed to all archived strategies. The search does
not optimize the universe.

## Command

```bash
uv run backtester router-search \
  --labels results/regime_matrix_archive_sol_2022_2025_trades/rolling_labels_day_30d_router_ps/rolling_labels.csv \
  --validation-start 2024-01-01 \
  --validation-end 2025-01-01 \
  --min-available-strategies 6 \
  --max-configs 2000 \
  --output results/regime_matrix_archive_sol_2022_2025_trades/rolling_labels_day_30d_router_ps/router_search
```

Artifacts:

- `router_search_predictions.csv`;
- `router_search_dense_scores.csv`;
- `router_offset_sensitivity.csv`;
- `router_utility_scores.csv`;
- `router_shortlist.csv`;
- `router_search_report.md`.

Utility score:

```text
- median(offset mean regret)
- p90(offset mean regret)
- 0.25 * median(offset worst regret)
- 0.10 * abs(worst offset drawdown)
- 0.10 * median(offset switches)
```

The oracle selects exactly one strategy per forward window using future
strategy returns. `regret = best_return_pct - selected_return_pct`. Strategy-id
hit rate and compounded oracle capture ratio are diagnostics; regret is the
ranking target.

`--validation-end` is exclusive. Use it to keep 2025 outside candidate search;
2025 oracle values may evaluate the frozen shortlist but may not rank or tune
it.

The search also writes `router_shortlist.csv`, merging the highest-ranked
utility rows with their complete frozen router parameters.

## Staged validation

Mass oracle-regret search is only stage 1. Validate every retained candidate
through the archived continuous shared-capital replay:

```bash
uv run backtester router-validate-shortlist \
  --predictions <search-output>/router_search_predictions.csv \
  --shortlist <search-output>/router_shortlist.csv \
  --matrix-dir results/regime_matrix_archive_sol_2022_2025_trades \
  --from 2025-01-01 \
  --to 2026-01-01 \
  --capital 10000 \
  --output <search-output>/routed_shortlist
```

This writes one routed report per router plus
`shortlist_execution_summary.csv`. The final stage is exact composite OHLCV
backtesting of the highest-ranked routed candidates.

## Complete v1 catalog result

Artifact:
`results/regime_matrix_archive_sol_2022_2025_trades/rolling_labels_day_30d_router_ps/router_search/`

Command:

```bash
uv run backtester router-search \
  --labels results/regime_matrix_archive_sol_2022_2025_trades/rolling_labels_day_30d_router_ps/rolling_labels.csv \
  --validation-start 2024-01-01 \
  --min-available-strategies 6 \
  --max-configs 2000 \
  --output results/regime_matrix_archive_sol_2022_2025_trades/rolling_labels_day_30d_router_ps/router_search
```

The deterministic v1 catalog contains 7040 configs. It was evaluated in four
chunks: offsets 0, 2000, 4000, and 6000. Search performance was improved with
NumPy feature matrices and vectorized non-overlap offset selection.

Top utility router:

| router | scoring | lookback | feature set | switch margin | median return | min return | worst DD | median negative periods | median switches |
| --- | --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `router_001190` | rolling median | 120d | none | 3.0 | +258.13% | +186.37% | -17.34% | 5.0 | 2.0 |

Main selected strategies for `router_001190`:

| selected strategy | dense rows |
| --- | ---: |
| `island_2023_021396_engulfing_bb_trend` | 480 |
| `crypt_ensemble_h1_discovery_nr7_bb_squeeze_h4` | 182 |
| `crypt_ensemble_h1_discovery_vwap_reclaim_robust` | 39 |

Interpretation:

- the first full constructor run found robust single-strategy selectors that
  beat the earlier simple baselines on offset median return;
- the best router is still a simple rolling-performance family, not a
  PineScript feature router;
- PineScript `same_state_mean_minus_dd` routers reached the top-20, so the
  indicator-state catalog is useful but not yet dominant;
- worst offset DD around -17% means this is a research shortlist, not a
  production/promotion decision.

Best risk-qualified router from the complete catalog:

| router | scoring | lookback | features | hold | margin | median return | min return | worst DD |
| --- | --- | ---: | --- | ---: | ---: | ---: | ---: | ---: |
| `router_005807` | same-state mean minus DD | 120d | PineScript | 30d | 1.0 | +192.80% | +141.63% | -6.52% |

It is archived as
`pinescript_same_state_mean_dd_120d_hold30_margin1`. The equivalent `mixed`
row produced identical decisions, so only the simpler PineScript config was
archived.

The v1 catalog is exhausted. Further search should add new router families,
not more local parameter combinations around either archived seed.

## Router Catalog v2

V2 is a broad deterministic constructor search. It keeps the production shape
fixed:

- all archived strategies are always available;
- exactly one strategy is selected;
- no capital split;
- no cash state;
- training rows must satisfy `label_end <= asof`.

### Performance score families

- arithmetic mean and median;
- exponentially weighted mean with configurable half-life;
- downside-adjusted mean;
- mean minus drawdown;
- median minus drawdown;
- mean minus negative-period rate;
- lower quantiles (`q25`, `q40`);
- consistency score: mean minus standard deviation;
- mean divided by downside deviation;
- recent-minus-long momentum;
- short/long horizon blended mean;
- short/long horizon blended median.

### Market-state matching families

- no state matching;
- exact match on a selected state subset;
- minimum matching-state count;
- weighted Hamming similarity over discrete PineScript states using equal,
  trend-heavy, momentum-heavy, or structure-heavy profiles;
- numeric nearest-neighbor matching over OHLCV, PineScript, or mixed features;
- inverse-distance weighted KNN scores.

### PineScript state subsets

The constructor searches named subsets rather than always requiring one full
exact-state conjunction:

- trend: Supertrend, DI side, ADX strength;
- momentum: WaveTrend zone, MACD phase;
- volatility: squeeze state and release context;
- structure: SMC internal/swing bias, zone, order-block side;
- session: killzone;
- breakout: trendline break side;
- trend + momentum;
- trend + volatility;
- trend + structure;
- momentum + structure;
- volatility + structure;
- trend + momentum + volatility;
- trend + momentum + structure;
- all core state columns.

### Temporal dimensions

- lookback: 30, 45, 60, 90, 120, 180, 270, 365, 540, 720 days;
- recent horizon: 15, 30, 45, 60, 90 days;
- long horizon: 120, 180, 270, 365, 540 days;
- EWM half-life: 7, 14, 30, 60, 90, 180 days;
- minimum history samples: 3, 5, 10, 20, 30;
- minimum hold: 0, 3, 7, 14, 21, 30, 45, 60 days;
- switch margin: 0, 0.5, 1, 1.5, 2, 3, 5, 7.5, 10 points.

### Long-run output policy

Large searches must use summary-only mode. The evaluator writes dense and
utility summaries for every candidate, then retains full daily predictions and
30-offset detail only for a bounded top shortlist. This prevents a 50k+
candidate run from creating tens of millions of in-memory rows.

### Search backends

Router Catalog v2 can be traversed by independent search algorithms:

- `grid`: deterministic catalog slice, useful for exhaustive coverage and
  resumable offsets;
- `random`: uniform reservoir sample over the full catalog;
- `island_qd`: balanced samples from separate scoring, lookback, and
  state-matching islands to preserve behavioral diversity;
- `hyperband_qd`: draws a larger proposal pool, scores it on progressively
  denser temporal proxies, and advances the strongest candidates;
- `smac_qd`: bootstraps proxy observations, fits a random-forest surrogate,
  and proposes candidates by predicted score plus model uncertainty.

`--seed` makes stochastic searches reproducible.
`--proposal-multiplier` controls the proposal pool used by `hyperband_qd` and
`smac_qd`. Every backend ultimately evaluates the selected candidates through
the same full offset-robust router objective.

The current v2 catalog contains **4,640,400** deterministic configs. A local
benchmark over 500 configs took about 92 seconds and 303 MB peak RSS. A
100,000-config summary-only slice is therefore the recommended approximately
five-hour exhaustive owner run:

```bash
MPLCONFIGDIR=/tmp/matplotlib \
UV_CACHE_DIR=/tmp/uv-cache \
uv run backtester router-search \
  --labels results/regime_matrix_archive_sol_2022_2025_trades/rolling_labels_day_30d_router_ps/rolling_labels.csv \
  --validation-start 2024-01-01 \
  --min-available-strategies 6 \
  --catalog-version v2 \
  --summary-only \
  --top-predictions 30 \
  --config-offset 0 \
  --max-configs 100000 \
  --output results/router_search_v2_first_100k
```

The deterministic ordering interleaves lookbacks across scoring families, so
the first 100k slice covers all rolling and EWM horizons plus a broad first
slice of state-subset routers. Continue later with
`--config-offset 100000`, `200000`, and so on.

For algorithm diversity, launch four independent v2 searches concurrently:

```bash
MPLCONFIGDIR=/tmp/matplotlib \
UV_CACHE_DIR=/tmp/uv-cache \
uv run backtester router-search-matrix \
  --labels results/regime_matrix_archive_sol_2022_2025_trades/rolling_labels_day_30d_router_ps/rolling_labels.csv \
  --validation-start 2024-01-01 \
  --min-available-strategies 6 \
  --algorithms random,island_qd,hyperband_qd,smac_qd \
  --max-configs 25000 \
  --proposal-multiplier 8 \
  --top-predictions 30 \
  --output-root results/router_search_matrix_v2_25k
```

This evaluates 25,000 final candidates per algorithm, 100,000 total. The
processes run concurrently, so elapsed time depends on available CPU and may be
longer than the sequential 100k benchmark on a constrained machine. Each
algorithm writes its own report, CSV artifacts, and `run.log` below the output
root.

Long-running search phases display evaluated/total candidates, elapsed time,
processing rate, and ETA. `router-search-matrix` keeps each child's progress
bar on a dedicated terminal row while redirecting normal output to that
algorithm's `run.log`. Logs can also be monitored with:

```bash
tail -f results/router_search_oracle_regret_v3_25k/*/run.log
```

## V2 algorithm matrix result

The 2026-06-24 owner run completed all four 25,000-candidate searches:

- 100,000 evaluations;
- 98,599 unique router configs;
- 1,401 duplicate evaluations across algorithms.

Two distinct frontier routers were archived:

| Search row | Algorithm | Median return | Minimum return | Worst DD | Role |
| --- | --- | ---: | ---: | ---: | --- |
| `router_v2_4252951` | Hyperband-QD | +425.17% | +202.21% | -6.11% | high-return frontier |
| `router_v2_3216811` | random | +310.56% | +281.26% | -3.80% | robustness frontier |

Their daily selected strategies agree on only 45.2% of validation rows. The
older full-state mean-DD router is superseded by `router_v2_3216811`.

These remain rolling-label research results. The next gate is continuous
routed execution per `docs/routed_execution_validation.md`.
