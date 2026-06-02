# `crypt_ensemble` multi-timeframe strategy

## Purpose

Move `crypt_ensemble` from a hard-coded H4 strategy to a reusable
multi-timeframe strategy contract.

The owner wants top-down confirmation:

1. D1 context: find broad market bias and forbid weak counter-context trades.
2. H4 setup: find the structural setup, zone, sweep, order block, or trend
   condition.
3. H1 trigger: find the actual entry trigger.

The design must be generic enough that a future 15m trigger can be added
quickly without rewriting the strategy again.

## Current behaviour

Implementation status as of 2026-06-02 session 24: the first additive MTF
slice is implemented, but H1 full-history smoke is not accepted yet. H4 remains
the default mode. H1 can be selected through `--primary-timeframe 1h` plus
`backtester/strategies/crypt_ensemble_h1.json`; it uses D1 context filtering,
the H4 ensemble verdict as setup, and an H1 candle-confirm trigger. The
attempted SOL H1 smoke loaded 21517 H1 bars and started correctly but did not
reach export before the session process ended, so diagnostics from a completed
run are still missing.

The current donor `crypt_ensemble` is not a true D1 -> H4 -> H1 model.

- Primary execution timeframe is effectively H4.
- `CryptEnsembleStrategy.generate()` builds `tick_time` as H4
  `open_time + 4h`.
- Engines evaluate closed H4 slices, with D1 as partial confluence in some
  engines.
- H1 candles may be loaded by `crypt-parquet`, but there is no distinct H1
  trigger layer.
- SMC event age rules, sweep freshness, ATR stop distance, and `ttl` semantics
  are all H4-oriented.

This means a simple "use H1 instead of H4" change would either repeat the same
H4 setup more often or introduce noisy H1 entries without a proper contract.

## Design goal

Introduce a small strategy-timeframe abstraction:

```json
{
  "timeframes": {
    "context": ["1d"],
    "setup": ["4h"],
    "trigger": "1h",
    "execution": "1h"
  }
}
```

The same structure should support a later 15m trigger:

```json
{
  "timeframes": {
    "context": ["1d"],
    "setup": ["4h", "1h"],
    "trigger": "15m",
    "execution": "15m"
  }
}
```

The strategy should not assume that the execution timeframe is H4.

## Timeframe roles

### Context timeframe

Default: D1.

Purpose:

- broad directional bias;
- volatility/regime context;
- optional trade filter against strong higher-timeframe structure.

Context output should be a typed summary, not a naked dict:

- `bias`: bullish, bearish, neutral;
- `confidence`: 0..1;
- `regime`: trending, ranging, volatile, defensive, or current enum;
- `known_at`: close time of the newest candle used;
- `rationale`: compact text.

Missing context data must not raise. It should degrade to neutral context with
low confidence.

### Setup timeframe

Default: H4.

Purpose:

- detect the actual trade idea;
- locate structural stop anchors;
- identify SMC order blocks, pivots, sweeps, BOS/CHoCH, trend and mean-revert
  setup state.

Setup output:

- `direction`: long, short, neutral;
- `setup_type`: order_block_retest, sweep_reversal, trend_continuation,
  mean_reversion, or similar;
- `anchor`: stop anchor level and type;
- `zone`: optional entry zone;
- `known_at`;
- `confidence`;
- `rationale`.

### Trigger timeframe

Default: H1 for the first experiment.

Purpose:

- confirm that the setup is actionable now;
- avoid entering every H4 directional verdict at the H4 close;
- provide the actual donor `signal`, `entry_price`, and initial `sl_price`.

Possible first H1 trigger rules:

- H1 close confirms setup direction after H4 setup is known;
- H1 sweep in the protective direction followed by close back inside range;
- H1 CHoCH/BOS aligned with D1/H4 bias;
- H1 retest of H4 order-block zone with rejection candle.

Do not implement all trigger rules at once. The first slice should implement
one or two explicit trigger types and export diagnostics.

### Execution timeframe

Default: same as trigger timeframe.

Purpose:

- donor OHLCV frame used by `ExecutionSim`;
- entry on the next execution bar open after a closed trigger candle;
- TP/SL/TTL are measured in execution bars.

If execution is H1, `ttl = 24` means 24 hours. If execution is 15m,
`ttl = 96` means 24 hours. Do not reuse H4 `ttl = 6` blindly.

## No-lookahead rules

For an execution tick at time `T`:

- D1 context may only use D1 candles with `open_time + 1d <= T`.
- H4 setup may only use H4 candles with `open_time + 4h <= T`.
- H1 trigger may only use H1 candles with `open_time + 1h <= T`.
- 15m trigger may only use 15m candles with `open_time + 15m <= T`.
- Entry occurs on the next execution bar open, never on the same candle used to
  produce the signal.
- Any structural object must keep `known_at <= T`.
- Pivot confirmation must account for right-side bars on the object's own
  timeframe.

No engine may use the current forming candle from any timeframe.

## Data contract

Extend donor `StrategyData` usage without breaking existing strategies.

Current project data already has H1/H4/D1 Parquet for SOL and TON. XPL has a
shorter H1 window and must be treated as insufficient for long H1 experiments
until backfilled.

Required next changes:

- allow `crypt-parquet` to choose `primary_timeframe`;
- when `primary_timeframe = "1h"`, set `StrategyData.primary` to H1 and keep
  H4/D1 under `candles`;
- preserve the existing H4 mode as the default until the H1 smoke is accepted;
- eventually support lower timeframes such as `15m` by using the same contract,
  not by adding a special-case strategy branch.

Expected config shape:

```json
{
  "name": "crypt_ensemble",
  "version": "0.2.0-mtf",
  "params": {
    "timeframes": {
      "context": ["1d"],
      "setup": ["4h"],
      "trigger": "1h",
      "execution": "1h"
    },
    "trigger_rules": ["h1_structure_confirm"],
    "min_context_confidence": 0.0,
    "min_setup_confidence": 0.0,
    "progress": true
  },
  "backtest_args": {
    "ttl": 24,
    "rrr": 1.5,
    "risk_percent": 1.0,
    "risk_base_period": "monthly"
  }
}
```

## Suggested implementation architecture

Do not add one-off H1 branches throughout `crypt_ensemble`.

Add small internal helpers with explicit data contracts:

```python
@dataclass(frozen=True)
class TimeframeRoleConfig:
    context: tuple[Timeframe, ...]
    setup: tuple[Timeframe, ...]
    trigger: Timeframe
    execution: Timeframe


@dataclass(frozen=True)
class MTFState:
    tick_time: datetime
    context: dict[Timeframe, TimeframeAnalysis]
    setup: dict[Timeframe, TimeframeAnalysis]
    trigger: TimeframeAnalysis
```

`TimeframeAnalysis` should contain:

- closed candles for that timeframe;
- SMC state for that timeframe;
- ATR for that timeframe;
- bias/direction/confidence;
- newest candle close time;
- diagnostics.

Implementation should reuse existing `crypt.structure.smc.analyse_smc_cached`
and existing engines where they still make sense. If an existing engine is too
H4-specific, wrap it behind a timeframe-aware adapter or keep it only on H4
until it is retuned.

## First H1 slice

Keep the first slice intentionally narrow.

1. Add `primary_timeframe` and `timeframes` params to `crypt_ensemble`.
2. Make `crypt-parquet` load H1 as `StrategyData.primary` when requested.
3. Preserve current H4 mode as the default.
4. Build closed-candle contexts for D1/H4/H1 at each H1 tick.
5. Compute SMC state separately for H4 and H1.
6. Gate entries:
   - D1 context is not strongly opposite;
   - H4 setup direction is BUY/SELL;
   - H1 trigger confirms the same direction.
7. Use structural stop from H4 setup first; if too wide, allow H1 structure to
   provide a closer protective stop only when it is aligned with the H4 setup.
8. Export diagnostics:
   - `context_tf`;
   - `setup_tf`;
   - `trigger_tf`;
   - `context_bias`;
   - `setup_direction`;
   - `trigger_type`;
   - `trigger_known_at`;
   - `sl_source_tf`;
   - `sl_distance_atr_execution`;
   - existing `sl_anchor_type` and confidence fields.

## Parameter retuning

H1 cannot inherit H4 parameters blindly.

Retune at minimum:

- `ttl`: use hours-equivalent values such as 12, 24, 36, 48 H1 bars;
- `rrr`: start with 1.0, 1.5, 2.0;
- sweep freshness: measure in each timeframe's own bars;
- SMC event staleness;
- maximum stop distance in execution ATR;
- trigger confidence thresholds;
- long-side filters, because recent SOL smokes show long trades are the main
  drag.

Do not run broad Optuna until the MTF data contract and diagnostics are
stable. First use small smoke grids and inspect exported diagnostics.

## Tests required

Add focused tests before a full smoke:

- H4 default mode still produces the same tick index and basic output shape.
- H1 mode uses H1 as primary/execution and D1/H4 as context/setup.
- D1 current forming candle is excluded at an H1 tick.
- H4 current forming candle is excluded at an H1 tick.
- H1 signal uses only the closed H1 candle and enters on next H1 open.
- A future-known H4 pivot/order block is ignored.
- H1 trigger does not fire when D1 context is strongly opposite.
- H1 trigger does not fire when H4 setup is neutral.
- Stop source diagnostics correctly identify H4 vs H1 stop anchors.
- Existing no-trade and missing-data graceful behavior remains intact.

## Smoke plan

First smoke:

```bash
cd backtester
PYTHONPATH=src:../src uv run --extra dev backtester run \
    --data-source crypt-parquet \
    --data-dir ../data \
    --symbol SOL-USDT-SWAP \
    --strategy strategies/crypt_ensemble_h1.json \
    --output /tmp/crypt_donor_h1_mtf_smoke
```

Inspect:

- `signals.csv`: how many H4 setups were filtered by H1 trigger;
- `trade_diagnostics.csv`: exit reason distribution and trades/day;
- `trades.csv`: long vs short PnL, trigger type, stop source, stop distance;
- `signal_diagnostics.csv`: decision/confidence/regime distribution.

Target diagnostic acceptance, not production acceptance:

- output is non-empty and auditable;
- no-lookahead tests pass;
- trade frequency can approach about 2 trades/day on the target symbol set
  without simply opening every H1 bar;
- TTL exits are explainable by setup geometry, not by missing TP/SL logic;
- long-side drag is visible by diagnostics before optimizer work.

## Future 15m path

If H1 MTF is implemented through `TimeframeRoleConfig` and `MTFState`, adding
15m should be mostly:

1. backfill/load 15m Parquet;
2. set `trigger = "15m"` and `execution = "15m"`;
3. retune `ttl`, trigger freshness, ATR distance caps, and slippage;
4. add the same no-lookahead tests for 15m close times.

If adding 15m requires editing every engine or duplicating the whole strategy,
the H1 implementation was too special-cased.

## Non-goals for the first slice

- Do not rewrite donor `ExecutionSim`.
- Do not add portfolio-level multi-symbol simulation.
- Do not optimize weights before the MTF output contract is stable.
- Do not remove the current H4 strategy mode.
- Do not make H1 live alerts the default until a smoke report is reviewed.
