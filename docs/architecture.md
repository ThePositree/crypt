# Architecture

This document describes the high-level architecture of `crypt`. It is the
source of truth for module boundaries. Engine-specific details live under
`docs/engines/`. Concrete decisions and trade-offs live under
`docs/decisions/` (ADRs).

---

## 1. System overview

```
                ┌───────────────────────────────┐
                │  Config (env + YAML)          │
                └───────────────┬───────────────┘
                                │
┌───────────────────────────┐   │   ┌────────────────────────────┐
│  ExchangeClient (ccxt)    │◀──┼──▶│  Optional fallback clients │
│  OKX REST                 │   │   │  (Bybit/Binance, future)   │
└──────────┬────────────────┘   │   └────────────────────────────┘
           │                    │
           ▼                    │
┌───────────────────────────────▼────────┐
│  Data Layer                            │
│   - Ingestor    (REST polling)         │
│   - Normalizer  (typed models)         │
│   - Store       (Parquet cache)        │
└───────────────┬────────────────────────┘
                │   typed events: Candle, FundingSnapshot,
                │   OISnapshot, RatioSnapshot, ...
                ▼
┌────────────────────────────────────────┐
│  EvaluationContext (per symbol, per    │
│  tick) — immutable, fully populated    │
│  before any engine runs                │
└───────────────┬────────────────────────┘
                │
   ┌────────────┼────────────┬────────────┬────────────┐
   ▼            ▼            ▼            ▼            ▼
┌──────┐   ┌────────┐   ┌────────┐   ┌────────┐   ┌────────┐
│Trend │   │MeanRev │   │ Deriv  │   │  Vol   │   │ Regime │
│Engine│   │ Engine │   │ Engine │   │ Engine │   │detector│
└──┬───┘   └────┬───┘   └────┬───┘   └────┬───┘   └────┬───┘
   │ Signal     │ Signal     │ Signal     │ Signal     │ Regime
   └────────────┴────────────┴────────────┴────────────┘
                                │
                                ▼
                  ┌──────────────────────────┐
                  │  Aggregator              │
                  │  weighted sum, regime-   │
                  │  conditional weights     │
                  └─────────────┬────────────┘
                                ▼
                  ┌──────────────────────────┐
                  │  Decision layer          │
                  │  thresholds, cooldown,   │
                  │  liquidity / spread guard│
                  └─────────────┬────────────┘
                                ▼
                  ┌──────────────────────────┐
                  │  Sinks                   │
                  │   - TelegramSink         │
                  │   - JsonLogSink          │
                  │   - ConsoleSink          │
                  │   - ExecutionSink (stub) │
                  └──────────────────────────┘
```

Cross-cutting: `logging` (loguru), config, tests, backtest harness.

---

## 2. Module map (`src/crypt/`)

```
src/crypt/
├── __init__.py
├── __main__.py            # CLI entrypoint
├── config.py              # pydantic-settings: env + YAML
├── models.py              # Candle, FundingSnapshot, OISnapshot, Ratio*, Signal,
│                          #   Verdict, Regime
├── exchange/
│   ├── __init__.py
│   ├── base.py            # ExchangeClient protocol
│   └── okx.py             # ccxt-backed OKX implementation
├── data/
│   ├── __init__.py
│   ├── ingestor.py        # async REST polling
│   ├── normalizer.py      # raw → typed models
│   ├── store.py           # Parquet cache (history) + in-memory state
│   └── context.py         # EvaluationContext builder
├── engines/
│   ├── __init__.py
│   ├── base.py            # BaseEngine ABC
│   ├── trend.py
│   ├── meanrev.py
│   ├── derivatives.py
│   ├── volatility.py
│   └── regime.py
├── aggregator/
│   ├── __init__.py
│   ├── weights.py         # static + regime-conditional weights
│   └── ensemble.py        # weighted-sum → Verdict
├── decision/
│   ├── __init__.py
│   └── filters.py         # confidence threshold, cooldown, spread guard
├── sinks/
│   ├── __init__.py
│   ├── base.py
│   ├── telegram.py
│   ├── jsonlog.py
│   ├── console.py
│   └── execution_stub.py
├── backtest/
│   ├── __init__.py
│   ├── replay.py          # historical Parquet → EvaluationContext stream
│   └── report.py
└── runtime/
    ├── __init__.py
    ├── scheduler.py       # APScheduler, 4h-aligned cron
    └── orchestrator.py    # main loop
```

---

## 3. Data contracts (canonical types)

Defined once in `crypt.models`. Engines and sinks must import from there.

### `Candle`
- `symbol: str` (e.g. `"SOL-USDT-SWAP"`)
- `timeframe: Timeframe` (enum: `M15`, `H1`, `H4`, `D1`)
- `open_time: datetime` (UTC, of the candle's open)
- `o, h, l, c: Decimal`
- `volume: Decimal`
- `closed: bool` — engines must filter `closed=True` only

### `FundingSnapshot`, `OISnapshot`, `LongShortRatioSnapshot`, `TakerVolumeSnapshot`
Each carries `symbol`, `ts`, value(s). Optional: `None` if the endpoint failed.

### `Regime` (enum)
- `TRENDING`
- `RANGING`
- `HIGH_VOL`

### `Signal` (engine output)
- `engine: str` — engine name, e.g. `"trend"`
- `symbol: str`
- `direction: Literal["bullish", "bearish", "neutral"]`
- `strength: float` — in `[-1.0, +1.0]`, sign mirrors direction
- `confidence: float` — in `[0.0, 1.0]`
- `rationale: list[str]` — human-readable bullets
- `inputs_missing: list[str]` — which inputs were unavailable
- `produced_at: datetime`

### `Verdict` (aggregator output)
- `symbol: str`
- `decision: Literal["BUY", "SELL", "HOLD"]`
- `confidence: int` — 0..100
- `score: float` — weighted sum in `[-1, +1]`
- `regime: Regime`
- `breakdown: list[Signal]`
- `rationale: str` — formatted explanation
- `produced_at: datetime`

---

## 4. Execution model

- **Loop-based**, 4h-aligned via `APScheduler`.
- On each tick: for each `symbol`, the orchestrator builds an
  `EvaluationContext`, runs all engines in parallel (`asyncio.gather`),
  hands signals to the aggregator, then the decision layer, then sinks.
- Inter-tick polling for fast-moving data (funding next-fund-time check,
  intra-candle OI) lives in `data/ingestor.py` but engines only run on the
  4h boundary.

Why not event-driven for v1: at 4h horizon there is no benefit; the cost is
significant complexity. We re-evaluate if we add liquidation analytics
(WS-only — see ADR 0006).

---

## 5. Failure model

- Network failure on a single endpoint ⇒ the related field is `None` in the
  `EvaluationContext`. Engines that depend on it emit `neutral, conf=0` with
  `inputs_missing` populated. The aggregator down-weights or skips that
  engine.
- Total exchange failure ⇒ tick is logged and skipped; no verdict emitted.
- Telegram failure ⇒ retry with backoff; verdict is always persisted to
  `JsonLogSink` regardless.

---

## 6. Backtest

The backtest harness feeds historical Parquet data through the **same**
`EvaluationContext` builder, engines, aggregator and decision layer. The only
difference is that sinks are replaced with a `BacktestRecorder` that
collects verdicts for offline analysis.

This is intentional: it is the only honest way to tune weights.

---

## 7. What is **not** here yet

- OrderFlow / tape engines — explicitly out of scope (ADR 0008).
- Sentiment engine — deferred (BACKLOG, P2).
- Liquidation analytics — deferred (ADR 0006).
- ML meta-aggregator — deferred (BACKLOG, P2).
- Web dashboard, Postgres, Redis, Docker — out of scope for MVP.
