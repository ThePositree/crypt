# Regime detection and single-strategy routing

Status: **planned**.

This document is the contract for the future market-regime layer. The goal is
not to predict price directly. The goal is to detect which market regime is
active and select the archived strategy that historically works in that
regime.

## 1. Goal

The system should answer two questions:

1. Which single archived strategy should be active now?
2. How do we know that the market has changed?

Core principle:

```text
strategy + conditions where it works
```

There is no assumption that one universal strategy works across all market
conditions. The project should keep searching for temporary alphas and the
conditions that make them useful.

## 2. Target Architecture

```text
historical data
  -> strategy constructor
  -> strategy search
  -> Stage 1 fast signal labeling
  -> Stage 2 parameter optimization
  -> Stage 3 full backtest
  -> strategy performance matrix
  -> regime discovery
  -> regime labeler
  -> regime strategy portfolios
  -> online regime detector
  -> portfolio router
  -> auto-trading
```

Strategy search continues in parallel with feature work. Candidates do not
need to pass the full strategy benchmark to be useful for the regime layer.
Profitable, weakly profitable, regime-specific, or otherwise interpretable
strategies should be archived when they add evidence about which market
conditions favor which strategy families.

Archive discipline matters for this layer. Regime Discovery should consume
strategy behavior from archived candidates only, because archived candidates
carry frozen execution params, provenance, and a written verdict. Active
strategy JSONs may be added to exploratory matrices, but they should be
re-optimized and archived before their columns are used for label training or
router evaluation.

## 3. Regime Discovery

Regimes are not hand-labeled calendar periods. They are inferred from
historical strategy behavior.

Working hypothesis:

> If a group of strategies changes its return profile at the same time, the
> market likely moved into another regime.

Input shape:

```text
time x strategy metrics
```

Example:

| Period | Trend | Mean reversion | Breakout |
| ------ | ----- | -------------- | -------- |
| T1 | + | - | + |
| T2 | - | + | - |

Candidate methods:

- clustering;
- Hidden Markov Models;
- Gaussian Mixture Models;
- K-Means;
- Spectral Clustering.

Output labels are initially opaque:

```text
regime_1
regime_2
regime_3
```

After discovery, regimes are interpreted through market features and may
receive readable names such as:

- `trend_up_low_vol`;
- `trend_up_high_vol`;
- `trend_down_low_vol`;
- `trend_down_high_vol`;
- `range_low_vol`;
- `range_high_vol`;
- `unknown`.

Recommended number of active regimes: **4-8**.

First analysis result: exact strategy labels are too noisy for a hard
single-strategy classifier. See `docs/regime_label_analysis.md`. The next MVP
should use confidence-gated top-2 routing and treat low
`margin_to_second_pct` buckets as ambiguous labels.

## 4. Strategy Performance Matrix

The regime layer needs a matrix built from archived and active strategies.

For final label-grade artifacts, "active" means a strategy that has first been
converted into an archived candidate. A mixed archive+ad-hoc matrix is useful
for diagnostics, but it is not the training source of truth.

Rows are time buckets or bars. Columns are strategy metrics.

Minimum metrics:

- return per bucket;
- realized drawdown per bucket;
- trade count;
- win rate;
- profit factor;
- average trade;
- exposure;
- long/short split;
- exit reason distribution where available.

The matrix must record the strategy config version and execution params used
for each column. A strategy family with multiple execution variants can produce
multiple columns, but the family relationship must be preserved.

## 5. Regime Labeler

The Labeler is an offline historical labeling system.

It may use the full historical window, including future data relative to each
bar, because its job is to create retrospective ground truth for training and
analysis.

Responsibilities:

- consume Regime Discovery output;
- consume the archived strategy performance matrix;
- assign each historical bar or bucket a regime label;
- assign strategy-oracle labels such as `best_strategy`, `top_2`, and
  `margin_to_second`;
- export training datasets for online detectors;
- preserve confidence or posterior probabilities when available.

The Labeler must not be used directly in live trading.

### 5.1 Oracle Strategy Label Dataset MVP

The first labeler artifact is a monthly strategy-oracle dataset. It is not a
market-regime classifier yet; it is the supervised target that says which
archived strategy worked best in each bucket.

Inputs:

- `results/<matrix>/matrix_return_pct.csv`;
- OHLCV data for the same symbol/timeframe;
- the matrix bucket size, initially `month`.

Per bucket outputs:

- `best_strategy`;
- `best_return_pct`;
- `second_strategy`;
- `second_return_pct`;
- `margin_to_second_pct`;
- `positive_strategy_count`;
- `negative_strategy_count`;
- `return_dispersion_pct`;
- one `return_<strategy_id>` column per archived strategy;
- OHLCV features computed strictly before the bucket start.

The OHLCV features are detector-safe by construction: for bucket `2024-05`, the
feature row may use data up to the last closed bar before `2024-05-01 00:00
UTC`, but not any candle inside May 2024.

Initial OHLCV feature families:

- trailing returns over 7, 30, and 90 days;
- realized volatility over 30 and 90 days;
- ATR14 as percent of price and its trailing percentile;
- Bollinger width;
- volume ratio and volume percentile;
- price position vs SMA50/SMA200;
- SMA slope;
- Donchian position;
- trend efficiency;
- Choppiness Index.

## 6. Online Regime Detector

The Detector is the live or backtest-time model that estimates the current
regime using only past and current data.

It must not use future data.

Pipeline:

```text
features
  -> rules or ML model
  -> smoothing
  -> confidence score
  -> market regime
```

MVP should start rule-based. ML models can be introduced after the labeling and
portfolio-utility loop is measurable.

The first walk-forward detector baseline over monthly labels did not beat a
rolling-majority baseline on exact strategy accuracy. A detector may still
report low confidence or `unknown` as a diagnostic, but ADR-0042 requires the
router to choose one strategy anyway.

The first monthly router baseline is documented in
`docs/regime_router_baseline.md`. The current benchmark to beat is a live-safe
`rolling_top2_mean_60_40` portfolio. The OHLCV feature-KNN router reduced
drawdown but did not beat that benchmark on return.

The first partial daily rolling router baseline is documented in
`docs/regime_rolling_router_baseline.md`. It validates the rolling-label and
router-evaluation pipeline, but it should not be used for final detector
training because the available strategy universe changes between 2022-2024 and
2025. The next label-grade artifact must come from a fresh full archive-only
matrix with raw `strategy_trades/` for all archived strategies.

The first router constructor is documented in `docs/regime_router_search.md`.
It searches single-strategy selectors over all archived strategies. Candidate
routers always select one strategy and never allocate capital to multiple
strategy portfolios.

Allowed detector families:

- rule-based models;
- Random Forest;
- XGBoost;
- LightGBM;
- HMM;
- clustering-based online assignment;
- neural networks, only after simpler models fail with evidence.

## 7. Detector Features

MVP uses OHLCV only over the currently available 2022-2025 history.

Trend:

- EMA slope;
- SMA slope;
- close vs EMA200;
- linear regression slope;
- ADX;
- Supertrend.

Volatility:

- ATR percentile;
- historical volatility;
- Bollinger width;
- Keltner width.

Volume:

- volume MA ratio;
- volume percentile;
- volume spike;
- OBV slope.

Market structure:

- Choppiness Index;
- Trend Efficiency Ratio;
- Donchian position.

Future optional features:

- BTC correlation;
- breadth indicators;
- cross-asset volatility;
- funding rate;
- open interest;
- open interest change;
- long/short ratio;
- basis;
- liquidation volume;
- taker buy/sell ratio.

Missing non-OHLCV data must degrade to lower confidence or `unknown`, not crash
the pipeline.

## 8. Smoothing and Unknown Regime

The detector must avoid noisy regime flipping.

Allowed smoothing methods:

- majority vote;
- EMA smoothing;
- hysteresis;
- minimum regime duration;
- confidence threshold.

Example rule:

```text
accept a new regime only after N consecutive confirmed bars
```

Detector output should include probabilities:

```json
{
  "bull": 0.72,
  "range": 0.18,
  "bear": 0.10
}
```

When confidence is low or probabilities are too flat, the detector may report
the diagnostic regime `unknown`.

Example:

```json
{
  "bull": 0.34,
  "range": 0.33,
  "bear": 0.33
}
```

`unknown` does not create a cash state. The router still selects the
highest-utility archived strategy under its fallback rule.

## 9. Portfolio Router

The Portfolio Router maps regime probabilities and current market state to one
selected strategy. It always scores the full archived strategy set and returns
exactly one strategy.

Example:

| Regime | Action |
| ------ | ------ |
| Bull | Best bull-regime strategy |
| Bear | Best bear-regime strategy |
| Range | Best range-regime strategy |
| Unknown | Best fallback strategy |

The router must export the chosen regime, probabilities, selected strategy,
score margin, switch decision, and handoff state. It never exports capital
weights because capital is not split.

## 10. Detector Search

Detector search is analogous to strategy search:

- feature catalog;
- rule/model catalog;
- hyperparameter space;
- staged optimization;
- scoring;
- candidate archive.

Stages:

| Stage | Purpose |
| ----- | ------- |
| D1 | Generate detector candidates. |
| D2 | Compare candidates with Labeler output. |
| D3 | Evaluate portfolio utility. |
| D4 | Walk-forward validation. |
| D5 | Paper trading. |
| D6 | Low-capital trading. |

Classification metrics are diagnostics, not the primary objective:

- precision;
- recall;
- F1 score;
- confusion matrix.

Primary score is portfolio utility:

```text
score =
  portfolio_return
  - drawdown_penalty
  - switching_penalty
  - uncertainty_penalty
  - detection_delay_penalty
```

The score must account for:

- return;
- max drawdown;
- number of regime switches;
- average regime duration;
- stability;
- delay in detecting regime changes.

## 11. Constraints

Forbidden:

- future data in the online Detector;
- calendar-year regime labels as ground truth;
- frequent regime flipping without penalty;
- excessive number of regimes.

Required:

- Labeler and Detector are separate components;
- every detector candidate reports both classification quality and portfolio
  utility;
- every router backtest is reproducible from archived strategy configs and
  regime labels.
