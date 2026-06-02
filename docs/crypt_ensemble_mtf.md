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
7. Use structural stop from H4 setup first. In H1 execution mode, also plan a
   stop from closed H1 structure and replace the H4 stop only when the H1 stop
   is valid, protective for the same signal, known at or before the H1 tick,
   and closer than the H4 stop by execution-timeframe ATR distance. If H1 has
   no valid aligned stop, keep the H4 stop; if neither timeframe has a valid
   structural stop, neutralize the signal as before.
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
- maximum stop distance in execution ATR. The H4 default may keep the current
  broad `8 ATR` guard, but H1 diagnostics should expose this as
  `max_sl_distance_atr` and start with a tighter `4 ATR` cap because the
  latest bounded smoke showed TTL-expired trades clustered around wider stops
  (`p50 = 4.107 ATR`, `p95 = 7.157 ATR`);
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
    --primary-timeframe 1h \
    --symbol SOL-USDT-SWAP \
    --from 2025-01-01 \
    --to 2025-02-01 \
    --strategy strategies/crypt_ensemble_h1.json \
    --output /tmp/crypt_donor_h1_mtf_smoke_bounded
```

After the bounded smoke exports clean diagnostics, run the same command without
`--from` / `--to` for full-history acceptance.

Implementation note: `--from` / `--to` should bound the primary/output frame
only. Context/setup candle frames must retain pre-start history up to `--to`,
otherwise H4/D1 engines lose warmup and the bounded smoke degenerates into
all-HOLD setup rows.

Latest bounded SOL result as of 2026-06-02 after the next-open entry fix:

- artifact:
  `/tmp/crypt_donor_h1_mtf_smoke_bounded_next_open/20260602_192846`;
- 745 H1 signal rows, 35 short trades, 0 long trades;
- H4 setup distribution: 124 BUY, 228 SELL, 393 HOLD;
- H1 trigger exported 176 `1h_candle_confirm` rows, of which 35 had valid H4
  structural stops and became tradeable short signals;
- final capital 9357.25 from 10000, `total_return_pct = -6.43`,
  `profit_factor = 0.04`, max drawdown `-6.27`;
- exit distribution: 21 `ttl_expired`, 14 `stop_loss`;
- sample trades confirm next-open execution
  (`signal_time = 2025-01-03 13:00:00+00:00`,
  `entry_time = 2025-01-03 14:00:00+00:00`);
- all stops used H4 order-block anchors (`sl_source_tf = 4h`), so H1 stop
  source behaviour remains unaccepted.

Latest bounded SOL result as of 2026-06-02 after H1 structural stop-source
selection:

- artifact:
  `/tmp/crypt_donor_h1_mtf_smoke_h1_stop_source/20260602_194225`;
- 745 H1 signal rows;
- signal distribution: 57 long, 102 short, 586 neutral;
- stop-source distribution among tradeable signals: 153 H1 stops, 6 H4 stops;
- 158 trades: 57 long, 101 short;
- final capital 9058.19 from 10000, `total_return_pct = -9.42`,
  `profit_factor = 0.66`, max drawdown `-10.44`;
- exit distribution: 79 `ttl_expired`, 51 `stop_loss`, 28 `take_profit`;
- H1 source behaviour is now contract-visible, but the metrics are diagnostic
  only. The H1 stop-source pass raised trade frequency to 6.27 trades/day and
  needs setup geometry, TTL/RRR, stop-distance caps, and performance review
  before full-history acceptance.

Latest bounded SOL result as of 2026-06-02 after adding
`max_sl_distance_atr = 4.0` to the H1 diagnostic config:

- artifact:
  `/tmp/crypt_donor_h1_mtf_smoke_h1_max4/20260602_195943`;
- 745 H1 signal rows;
- signal distribution: 39 long, 66 short, 640 neutral;
- 105 tradeable signals; all 98 executed trades used `sl_source_tf = 1h`;
- 98 trades: 39 long, 59 short;
- final capital 9947.0 from 10000, `total_return_pct = -0.53`,
  `profit_factor = 0.97`, max drawdown `-7.41`;
- exit distribution: 37 `ttl_expired`, 35 `stop_loss`, 26 `take_profit`;
- `ttl_expired` share improved from 50.0% to 37.8%, and trade frequency fell
  from 6.27 to 3.89 trades/day. This is still one bounded SOL diagnostic
  slice; do not treat it as full-history H1 acceptance or final calibration.

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
