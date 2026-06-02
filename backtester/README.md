# Backtester: A Simple Trading Strategy Backtesting Framework

[![Python Version](https://img.shields.io/badge/python-3.12%20%7C%203.13-blue)](https://github.com/AuriumX/backtester)

A lightweight Python framework for backtesting trading strategies with realistic execution simulation, risk management, and detailed performance analysis.

## 🚀 Features

- 📈 **Realistic Trading Simulation**
  Includes:

  - **Risk-based position sizing**: size calculated as `risk_value / (entry_price - sl_price)`
  - **Reward/Risk Ratio (RRR)**: TP = entry + (entry - sl_price) \* rrr
  - **Configurable intra-bar TP/SL policy**: when both TP and SL lie within the same bar range, execution is resolved according to a user-configurable policy (`bar_exit_policy`) with conservative default
  - **Taker fee** (market orders) for entry and SL exit
  - **Maker fee** (limit orders) for TP exit
  - **Stop Loss and Take Profit levels** (SL taken from strategy output)
  - **Position time-to-live (TTL)** to prevent infinite holds
  - **Max simultaneous positions**
  - **Support for long and short positions** (`signal = 1` or `-1`)
  - **Leverage calculation** to avoid balance shortage
  - Protection against economically unviable entries

- 🧪 **Comprehensive Analysis**
  Generates:

  - Win rate, profit factor, max drawdown
  - Daily/weekly/monthly returns
  - Trade distribution by exit reason (TP, SL, TTL)
  - Capital curve and full trade history (CSV export)
  - **Separate metrics for long and short positions**

- 📦 **Flexible Data Handling**
  Supports:

  - Custom CSV files with OHLCV data
  - Standardized column renaming and validation
  - Pluggable data loaders for different sources (CSV, in-memory DataFrames,
    and BingX API via dedicated loader classes)

- 📁 **Easy Results Export**
  Saves full trade history, metrics, and equity curve in CSV format.

---

## ⚠️ Current Limitations

Planned features:

- Limit order support for entry
- Partial take profit
- Trailing stop

---

## 🛠 Installation

```bash
git clone https://github.com/AuriumX/backtester.git
cd backtester
pip install -e .
```

---

## ⚙️ Quick Start

Run with custom strategy config (JSON). Data can be loaded from a local CSV (default) or from the BingX API.

**From a CSV file (default):**

```bash
python -m backtester run \
  --csv data/SOLUSDT_1m.csv \
  --strategy strategies/dual_ma_v1.json \
  --output results/dual_ma_v1
```

**From BingX API:**

```bash
python -m backtester run \
  --data-source bingx \
  --bingx-symbol BTC-USDT \
  --bingx-interval 1h \
  --bingx-start-time "2024-01-01 00:00:00" \
  --bingx-end-time "2024-01-31 23:59:59" \
  --bingx-api-key YOUR_API_KEY \
  --bingx-api-secret YOUR_API_SECRET \
  --strategy strategies/dual_ma_v1.json \
  --output results/dual_ma_v1
```

Times for BingX are in UTC; format is `YYYY-MM-DD HH:MM:SS`. The loader fetches the full range in batches automatically.

🔧 Available CLI Commands

```bash
python -m backtester --help
```

`run` Command Options

| Option                 | Description                               | Default             |
| ---------------------- | ----------------------------------------- | ------------------- |
| --data-source         | Data source: `csv` or `bingx`             | csv                 |
| --csv                  | Path to OHLCV CSV file (required if --data-source=csv) | -            |
| --symbol               | Trading pair name (for report)            | SYMBOL/USDT         |
| --strategy             | path to JSON config                       | required            |
| --output               | Folder to save results                    | results/backtesting |
| --capital              | Initial capital                           | 10000.0             |
| --taker-fee            | Taker fee                                 | 0.0005              |
| --maker-fee            | Maker fee                                 | 0.0002              |
| --risk-percent         | Risk per trade as % of capital (%)        | 1.0                 |
| --rrr                  | Reward/Risk Ratio (e.g., 2.0 = 2:1)       | 2.0                 |
| --ttl                  | Max position duration (in bars)           | 0 (disabled)        |
| --max-positions        | Max simultaneous positions                | 0 (disabled)        |
| --max-allowed-leverage | Maximum allowed leverage for the strategy | 25.0                |
| --ts-col               | Timestamp column name in CSV              | timestamp           |
| --bar-exit-policy      | Intra-bar TP/SL policy (`best_case`/`worst_case`) | worst_case    |
| --analyze-conditions   | Analyze trade conditions & predictors     | false               |
| --top-predictors       | Number of top predictors to compute       | 10                  |
| --create-visualizations| Create predictor analysis visualizations  | false               |
| --create-dashboard     | Create summary dashboard                  | false               |
| --is-isolated-futures  | Enable isolated futures mode              | false               |
| --max-allowed-margin   | Max allowed margin (isolated futures)     | 1.0                 |

When `--data-source=bingx`, the following options are required: `--bingx-symbol`, `--bingx-interval`, `--bingx-start-time`, `--bingx-end-time`, `--bingx-api-key`, `--bingx-api-secret`. Optional: `--bingx-base-url`, `--bingx-time-zone`, `--bingx-recv-window`. BingX intervals: `1m`, `3m`, `5m`, `15m`, `30m`, `1h`, `2h`, `4h`, `6h`, `12h`, `1d`, `1w`.

---

## 📊 Example Output

After running a backtest, you'll get:

```
📁 Results saved to: results/dual_ma_v1_20240405_123046
│
├── trades.csv          # All individual trade records (with exit reason, fees, size, etc.)
├── metrics.csv         # Summary statistics (Win Rate, PnL, Drawdown, etc.)
└── equity_curve.csv    # Capital growth over time
```

Sample report output:

```
==================================================
📊 BACKTEST RESULTS
==================================================
Initial Capital:    $1000.0
Final Capital:      $12843.50
Total Return:       28.44%
Total PnL:          $2843.50
Win Rate:           61.90%
Profit Factor:      2.18
Max Drawdown:       -9.15%
Avg. Trade:         $124.30
Avg. Win:           $248.60
Avg. Loss:          -$93.20
Avg. Duration:      14.7 bars

Exit Distribution:
  take_profit: 26
  stop_loss: 16
  ttl_expired: 0

📈 LONG POSITIONS
----------------------------------------
  Count:      42
  Win Rate:   61.90%
  Total PnL:  $1243.50
  Avg PnL:    $29.61
  PF:         2.18

📉 SHORT POSITIONS
----------------------------------------
  Count:      28
  Win Rate:   57.14%
  Total PnL:  $-156.20
  Avg PnL:    $-5.58
  PF:         0.75

📅 Monthly Returns (%)
Month      Return (%)
-------------------------
2025-05    +12.30
2025-06    -3.20
2025-07    +15.25
==================================================
```

---

## 🧠 Strategies

✅ Built-in Strategies

All built-in strategies are registered in `backtester.registry.STRATEGIES` and can be used by name (see keys below):

1. `dual_ma` → `DualMAStrategy`
2. `liq_hunter` → `LiquidityHunter`
3. `som` → `SOMStrategy`
4. `forest` → `ForestStrategy`
5. `fvg_imbalance` → `FVGImbalanceStrategy`
6. `fractal_rejection` → `FractalRejectionStrategy`
7. `rejection` → `RejectionStrategy`
8. `meta` → `MetaStrategy`

🛠 Add Your Own Strategy

The project uses a **single source of truth** for strategy discovery: `backtester.registry.STRATEGIES`.

1. Create a class that inherits from `BaseStrategy` (usually in `backtester/strategies/`).
2. Implement **both** `generate()` (signals) and `suggest_params()` (Optuna support).
3. Register the strategy by adding it to `STRATEGIES` in `src/backtester/registry.py`.

```py
# src/backtester/registry.py
from backtester.strategies.my_strategy import MyOwnStrategyClass  # noqa: F401

STRATEGIES["my_strategy"] = MyOwnStrategyClass
```

### Strategy JSON config format

The `--strategy` file is a JSON object:

```json
{
  "name": "dual_ma",
  "version": "v1",
  "params": {},
  "backtest_args": {
    "risk_percent": 1.0,
    "rrr": 2.0
  }
}
```

- `name`: registry key from `backtester.registry.STRATEGIES`
- `params`: passed to the strategy constructor (`BaseStrategy(params)`)
- `backtest_args`: optional overrides for backtest parameters (capital, risk_percent, rrr, fees, ttl, max_positions, leverage, isolated futures, daily limits, trading window, etc.); any key present overrides the CLI default

### CLI/data flow (high-level)

`backtester run` orchestrates the pipeline:

1. Load and validate strategy config JSON → pick a strategy class from `backtester.registry.STRATEGIES`
2. Load OHLCV data via the selected source (`--data-source=csv` or `bingx`), using `CsvDataLoader` or `BingxApiDataLoader` (column renaming + basic validation), and build a `{symbol: DataFrame}` mapping
3. Run `Backtester.run(...)` which applies `strategy.generate(df)` and simulates execution via `ExecutionSim`
4. Build `ResultsAnalyzer` → print report → export CSVs to a timestamped output folder
5. Optional: `--analyze-conditions` computes trade-condition predictors; exports extra artifacts if predictors were found

---

## 📄 Input CSV Format

Your CSV file must contain at least these columns:

| Column Name | Description     |
| ----------- | --------------- |
| timestamp   | Datetime string |
| open        | Open price      |
| high        | High price      |
| low         | Low price       |
| close       | Close price     |
| volume      | Volume          |

Example format:

```csv
timestamp,open,high,low,close,volume
2024-01-01 00:00:00,30000,30500,29800,30200,100
2024-01-01 01:00:00,30200,30700,30100,30600,120
...
```

---

## 🔌 Data Loaders Overview

The project uses a small hierarchy around a common `BaseDataLoader` interface:

- `CsvDataLoader` – loads OHLCV data from CSV files.
- `DataFrameDataLoader` – wraps an in-memory `pandas.DataFrame`.
- `BingxApiDataLoader` – loads OHLCV data from the BingX Swap
  `/openApi/swap/v3/quote/klines` endpoint.

For convenience and backwards compatibility there is also a facade:

- `DataLoader` – exposes `from_csv(...)` and `from_dataframe(...)` methods and
  delegates to the concrete loaders internally.

You can also use the `create_data_loader(source, **kwargs)` factory to choose a
loader by string (e.g. `"csv"`, `"dataframe"`, `"bingx"`).

---

## 🧪 Development

🛠 Setup

```bash
hatch shell dev
```

⚙️ Run

```bash
hatch run dev:backtester
```

🧹 Linting & Typing

```bash
hatch fmt
```

🧪 Testing

Use the project test matrix via Hatch:

```bash
hatch test
```

This will run the full pytest suite, including integration tests for
`ExecutionSim` and unit tests for the pluggable risk/fee models.

📊 Coverage Report

WIP
