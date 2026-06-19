# Regime detection and portfolio routing

Status: **planned**.

This document is the contract for the future market-regime layer. The goal is
not to predict price directly. The goal is to detect which market regime is
active and route capital to the strategy portfolio that historically works in
that regime.

## 1. Goal

The system should answer two questions:

1. Which strategy or strategy portfolio should be active now?
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
need to pass the full investment mandate to be useful for the regime layer.
Profitable, weakly profitable, regime-specific, or otherwise interpretable
strategies should be archived when they add evidence about which market
conditions favor which strategy families.

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

## 4. Strategy Performance Matrix

The regime layer needs a matrix built from archived and active strategies.

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
- assign each historical bar or bucket a regime label;
- export training datasets for online detectors;
- preserve confidence or posterior probabilities when available.

The Labeler must not be used directly in live trading.

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

When confidence is low or probabilities are too flat, the regime is `unknown`.

Example:

```json
{
  "bull": 0.34,
  "range": 0.33,
  "bear": 0.33
}
```

`unknown` actions:

- reduce risk;
- reduce exposure;
- use a defensive portfolio;
- or temporarily disable entries.

## 9. Portfolio Router

The Portfolio Router maps regime probabilities to strategy allocations.

Example:

| Regime | Action |
| ------ | ------ |
| Bull | Bull portfolio |
| Bear | Bear portfolio |
| Range | Range portfolio |
| Unknown | Reduced exposure or no trade |

The router may use probability-weighted allocation:

```text
Bull 70%, Range 20%, Bear 10%
```

The router must export the chosen regime, probabilities, active strategies,
capital weights, and any reduced-risk reason.

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

