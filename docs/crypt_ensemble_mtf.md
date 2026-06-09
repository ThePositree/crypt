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
`strategies/backtester/crypt_ensemble_h1.json`; it uses D1 context filtering,
the H4 ensemble verdict as setup, and structural H1 trigger rules. The
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
    "trigger_rules": [
      "h1_sweep_reversal",
      "h1_structure_break",
      "h1_order_block_retest"
    ],
    "max_trigger_age_bars": 3,
    "min_context_confidence": 0.0,
    "min_setup_confidence": 0.0,
    "optimized_windows": true,
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
   - H1 trigger confirms the same direction with an explicit structural event,
     not just a green/red candle close.
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

## H1 trigger rules

H1 mode no longer treats candle colour as the default trigger. The earlier
`h1_candle_confirm` rule remains available only as an explicit legacy
diagnostic rule when listed in `trigger_rules`; do not treat it as a
production candidate trigger.

Default H1 rules:

- `h1_sweep_reversal`: a fresh H1 liquidity sweep on the protective side
  (`low` for long, `high` for short), followed by an H1 close in the setup
  direction.
- `h1_structure_break`: a fresh H1 BOS/CHOCH in the setup direction.
- `h1_order_block_retest`: an active H1 order block aligned with the setup
  direction is retested by the closed trigger candle, and that candle closes
  in the setup direction.

Freshness is controlled by `max_trigger_age_bars` (default `3`) and is
measured in trigger-timeframe bars. Every fired signal exports the exact
`trigger_type` so attribution reports can separate sweep, structure-break,
and order-block entries. If no configured rule fires, the row is neutralized
with `trigger_type = trigger_rejected`.

This separates:

- **H4 setup**: broad directional premise from the existing ensemble;
- **H1 trigger**: concrete market event that permits entry;
- **structural stop**: protective invalidation level selected after the
  trigger.

Do not use stop-anchor filters as a substitute for trigger design. Recent
bounded attribution showed anchor type and stop-distance buckets were not
stable across SOL March and TON February: SOL March favored pivots and tight
stops, while TON February favored order-block/pivot anchors and wider 2-4 ATR
stops. Anchor selection should support the setup, not define the entry edge by
itself.

## Trigger-first discovery reset

Owner direction on 2026-06-08 resets the H1 search workflow:

1. Start from raw H1 trigger candidates with side, anchor-type,
   anchor-freshness, context-reversal, and stop-distance filters disabled.
2. Use `rrr = 1.0` while searching for trigger/filter quality. Treat PnL as a
   secondary diagnostic at this stage.
3. Rank raw triggers first by trade count and win rate, then by exit mix,
   drawdown, and visual plausibility in `trade_chart.html`.
4. Add filters one at a time only after a raw trigger produces enough trades
   to measure. Keep filters that improve win rate or remove clearly bad chart
   patterns without collapsing trade count; reject filters that mostly reduce
   density or move losses elsewhere.
5. Only after the trigger plus filter stack is stable should agents search
   execution parameters such as `rrr`, `ttl`, stop distance, take profit, and
   trailing stop. Mandate PnL evaluation comes after this stage, not before.

Win rate is not a final promotion metric; it is a diagnostic for discovering
whether an entry trigger has a measurable edge before execution geometry is
optimized. Mandate compliance still uses the accepted investment gates in
`docs/investment_mandate.md`.

### Raw H1 diagnostic mode

`setup_source = "h1_raw"` is a diagnostic-only mode for the trigger-first
search. It bypasses the H4 setup gate so agents can measure raw H1 trigger
density before deciding which filters are useful.

Rules:

- H4 and D1 analysis may still be exported as diagnostics, but they do not
  neutralize the signal.
- `h1_candle_confirm` maps bullish H1 candles to long and bearish H1 candles
  to short.
- `h1_structure_break` maps fresh bullish BOS/CHOCH to long and fresh bearish
  BOS/CHOCH to short.
- `h1_sweep_reversal` maps fresh low sweeps with bullish closes to long and
  fresh high sweeps with bearish closes to short.
- `h1_order_block_retest` maps touched bullish order blocks with bullish
  closes to long and touched bearish order blocks with bearish closes to short.
- If no configured raw trigger fires, export `trigger_type =
  raw_h1_trigger_rejected`.

Use raw mode only to rank trigger density, win rate, exit mix, and chart
plausibility. After a raw trigger has measurable edge, recreate it as a normal
MTF setup/filter candidate before mandate evaluation.

## Parameter retuning

H1 cannot inherit H4 parameters blindly.

Retune at minimum:

- `ttl`: use hours-equivalent values such as 12, 24, 36, 48 H1 bars;
- `rrr`: start with 1.0, 1.5, 2.0;
- `max_positions`: search finite values such as 1, 2, 3, and 5 after the
  margin-reporting surface is auditable; keep `0` only as an unconstrained
  diagnostic baseline;
- `trail_activation_rrr` and `trail_distance_atr`: keep
  `trail_activation_rrr = 0` for fixed TP, then compare bounded trailing values
  such as activation `0.5`, `0.75`, `1.0`, `1.25` and distance `0.5`, `1.0`,
  `1.5`, `2.0` ATR;
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
stable. First use bounded optimizer slices with strategy-param search disabled
and inspect exported diagnostics.

## Concurrent positions and margin realism

ADR-0024 adds a promotion guard for H1 candidates: short-only or any later H1
profile must not be promoted until concurrent-position and margin usage are
auditable.

`capital_before` / `capital_after` in donor trade exports are realized-equity
fields. They do not represent free margin while other positions are open. H1
reports now include separate margin fields:

- `locked_margin` for the new position;
- `available_balance_before`;
- `open_positions_before`;
- `total_locked_margin_before`;
- `total_locked_margin_after_entry`;
- peak simultaneous positions in the run;
- peak locked margin and peak locked-margin percentage.

The 2026-06-05 seven-window short-only margin audit at
`results/crypt_ensemble_h1_short_only_margin_audit/20260605_122841` shows why
this guard matters. With unconstrained `max_positions = 0`, the run still
totals `+3.96%`, but peak simultaneous positions reach `18`, peak locked
margin reaches `104.42%` of initial capital in TON January, and several
windows leave less than `$50` available before a new entry. That profile is a
diagnostic baseline, not promotable.

For H1 MTF, repeated H1 triggers inside the same H4 setup can behave like
pyramiding. That may be tradable, but only if it survives finite
`max_positions` and realistic isolated-margin checks. Search `max_positions`
as an execution/risk parameter with Optuna or bounded reports. Do not accept
an unconstrained `max_positions = 0` result as tradable unless a later ADR
explicitly justifies that policy.

The owner's intended high-leverage direction is isolated futures, where
liquidation may be treated as the effective stop if it is reached before the
structural stop. That requires explicit modeling. If liquidation is closer
than the structural stop, risk sizing and TP placement must use the liquidation
price as the effective stop; otherwise the backtest is scoring a risk distance
that the exchange would not allow the position to survive.

Current operator command for bounded execution-only H1 tuning:

```bash
MPLCONFIGDIR=/tmp/matplotlib \
UV_CACHE_DIR=/tmp/uv-cache \
uv run backtester optimize \
    --data-source crypt-parquet \
    --data-dir data \
    --primary-timeframe 1h \
    --symbol SOL-USDT-SWAP \
    --from 2025-01-01 \
    --to 2025-02-01 \
    --strategy strategies/backtester/crypt_ensemble_h1.json \
    --output /tmp/crypt_donor_h1_mtf_optuna_cli \
    --trials 12 \
    --study-name sol_h1_rrr_ttl \
    --target total_return_pct \
    --rrr-low 1.0 --rrr-high 2.0 --rrr-step 0.25 \
    --ttl-low 18 --ttl-high 42 --ttl-step 6 \
    --max-positions-values 1,2,3,5 \
    --risk-percent 1.0 \
    --no-strategy-param-search \
    --no-daily-limit-search \
    --no-trading-window-search \
    --export-best-run
```

**Optimizer target vs mandate:** default `--target total_return_pct` optimizes
full-year compound return on one continuous backtest. Mandate promote/archive
uses per-month floors and intra-month DD on fixed windows (`compare-fixed`).
Trials can rank well on `total_return_pct` yet fail mandate — use mandate
reports for final decisions; mandate-aware targets are tracked in BACKLOG (P1).

The command writes:

- `trials.csv`;
- `best_trial.json`;
- the Optuna journal log;
- `best_run/` with normal donor exports (`trades.csv`, `metrics.csv`,
  `trade_diagnostics.csv`, `signals.csv`, `signal_diagnostics.csv`,
  `equity_curve.csv` when trades exist, `ohlcv.csv`, `trade_chart.html`, and
  legacy per-trade `trade_candles/` slices).

When only execution parameters (`rrr`, `position_ttl_bars`, fixed risk and
execution filters) are searched, `ParameterOptimizer` caches the generated
`crypt_ensemble` signal frame by strategy params. Repeated trials and
`best_run/` export must reuse that frame instead of rerunning the ensemble.
Changing strategy params such as `max_sl_distance_atr`, SL buffer, or
`min_confidence` creates new signal-cache keys and is expected to be slower.
Changing only `max_positions` reuses the same precomputed signal frame because
it affects execution/margin behavior, not signal generation.

Bounded SOL H1 diagnostic on 2026-06-03:

- slice: `2025-01-01` to `2025-02-01`, 745 H1 signal rows;
- trials: 12 execution-only Optuna trials over `rrr = 1.0..2.0` and
  `ttl = 18..42`;
- first signal build: about 3 minutes 59 seconds;
- cached trial runtime after the first build: about 0.05 seconds each;
- `signal_cache_size = 1`;
- best tiny diagnostic: `rrr = 1.25`, `position_ttl_bars = 30`,
  `total_return_pct = 2.46`, `profit_factor = 1.14`,
  `max_drawdown = -5.7`, 97 trades;
- signal distribution: 39 long, 66 short, 640 neutral;
- exit distribution: 38 stop-loss, 35 take-profit, 24 TTL-expired;
- long PnL `+304.88`, short PnL `-58.48`.

This is still a bounded in-sample setup-geometry diagnostic, not accepted
calibration.

## Performance optimization contract

Optimization work normally must preserve the current strategy semantics. The
safe first target is data preparation, not trading logic:

- keep the existing per-bar `CryptEnsembleStrategy.generate()` semantics as the
  reference implementation;
- add optimized helpers only for selecting already-closed candle windows and
  timestamp-bounded extras;
- preserve the rule `open_time + timeframe <= tick_time` for candles and
  `ts < tick_time` for extras;
- keep `EvaluationContext`, engine calls, aggregation, trigger rules,
  structural stop planning, and donor execution output unchanged;
- do not cache H4 verdicts across H1 bars in the H4 default mode;
- do not change `analyse_smc_cached` keying or SMC internals without dedicated
  no-lookahead and parity tests for future-known structural objects.

Every optimized path must have a reference-vs-optimized parity harness before
it is used for tuning or Optuna. The harness compares the old reference path
against the optimized path on the same `StrategyData`, strategy parameters, and
monkeypatched deterministic verdicts or real bounded data.

Required parity columns:

- `signal`;
- `sl_price`;
- `entry_price`;
- `confidence`;
- `score`;
- `regime`;
- `decision`;
- `rationale`;
- `sl_anchor_type`;
- `sl_anchor_level`;
- `sl_anchor_known_at`;
- `sl_distance_atr`;
- `context_tf`;
- `setup_tf`;
- `trigger_tf`;
- `context_bias`;
- `setup_direction`;
- `trigger_type`;
- `trigger_known_at`;
- `sl_source_tf`;
- all `strength_<engine>` columns exported from the verdict breakdown.

Floating values should be compared with exact equality where possible and
otherwise with a tight numerical tolerance. Any mismatch in `signal`,
`decision`, stop source/type, trigger type, or known-at fields is a hard
failure. Bounded SOL H1 smokes may be used as runtime diagnostics, but unit
parity is the acceptance gate for code-level performance changes.

## H4 setup snapshot cache

ADR-0022 changes the H1 MTF execution semantics deliberately: the H4 setup
verdict is a snapshot known at the latest closed H4 candle, not a verdict that
is recomputed on every H1 trigger bar with a different H1 `tick_time`.

For an H1 execution tick `T`:

- find `setup_time = max(H4 close_time <= T)`;
- build the H4 setup context at `setup_time`;
- evaluate the ensemble once for that H4 setup snapshot;
- reuse that verdict for all H1 execution ticks until the next H4 candle
  closes;
- keep H1 trigger, H1 structural stop selection, and H1 execution-bar timing
  evaluated at the actual H1 `T`.

The cache key must include at least:

- symbol;
- setup timeframe;
- `setup_time`;
- closed H4 candle boundary;
- closed D1 context boundary used by the H4 setup context.

The H4 setup snapshot cache is not required to match the old per-H1 verdict
path byte-for-byte, because the old path let H4 SMC age/freshness drift inside
an H4 setup window. Required tests instead prove the new contract:

- repeated H1 ticks inside one H4 setup window call `_evaluate_context()` only
  once;
- H1 trigger decisions can still differ by H1 candle;
- H1 structural stops are still selected using the actual H1 tick context;
- the next H4 close invalidates the setup snapshot and evaluates a new H4
  verdict.

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
uv run backtester run \
    --data-source crypt-parquet \
    --data-dir data \
    --primary-timeframe 1h \
    --symbol SOL-USDT-SWAP \
    --from 2025-01-01 \
    --to 2025-02-01 \
    --strategy strategies/backtester/crypt_ensemble_h1.json \
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

As of 2026-06-03, the H1 diagnostic config also sets
`optimized_windows = true`. This enables the parity-tested closed-window cache
for context preparation only. It does not cache verdicts, SMC states, trigger
decisions, or structural stops across bars. The reference path remains
available by setting `optimized_windows = false`.

Bounded SOL result after enabling `optimized_windows`:

- artifact:
  `/tmp/crypt_donor_h1_mtf_smoke_optimized_windows/20260603_083245`;
- runtime: about 5 minutes 3 seconds for 745 H1 bars, versus about 6 minutes
  35 seconds for the previous max-4 reference smoke;
- 98 trades, final capital 9947.0, `total_return_pct = -0.53`,
  `profit_factor = 0.97`, max drawdown `-7.41`;
- exit distribution: 37 `ttl_expired`, 35 `stop_loss`, 26 `take_profit`;
- long PnL -45.67, short PnL -7.33. This remains a bounded diagnostic, not
  H1 acceptance.

Bounded SOL Optuna speed check after ADR-0022 H4 setup snapshots and
`ParameterOptimizer` signal caching:

- artifact:
  `/tmp/crypt_donor_h1_mtf_optuna_speed_check`;
- 3 execution-only trials over the same SOL H1 bounded slice with
  `optimize_strategy_params = false`;
- first trial built the 745-row `crypt_ensemble` signal frame in about
  226.9 seconds;
- the next two `rrr` / `position_ttl_bars` trials reused the cached signal
  frame and completed in about 0.05 seconds each;
- tiny diagnostic best: `rrr = 1.75`, `position_ttl_bars = 30`,
  `total_return_pct = 0.18`;
- this proves the optimizer speed path for execution-only tuning, not final
  calibration.

Inspect:

- `signals.csv`: how many H4 setups were filtered by H1 trigger;
- `trade_diagnostics.csv`: exit reason distribution and trades/day;
- `trades.csv`: long vs short PnL, trigger type, stop source, stop distance;
- `signal_diagnostics.csv`: decision/confidence/regime distribution.

## H1 signal-quality diagnostics

Before adding more execution grids, use a report-only diagnostic command over
bounded H1 windows. The purpose is to explain why candidate A failed across
SOL/TON full-history and monthly windows before changing signal logic.

The report must build the `crypt_ensemble` signal frame once per
symbol/window, run one fixed execution profile only to attach realized PnL, and
then write CSV/Markdown summaries. It must not tune parameters or mutate the
strategy.

Default diagnostic windows:

- SOL January, February, March 2025;
- TON January, February, March, April 2025.

Required output files:

- `signals.csv` / `signals.md`: one row per window with signal counts,
  setup/trigger/context distributions, confidence quantiles, stop-source and
  anchor counts, and stale/reversal markers;
- `groups.csv` / `groups.md`: grouped trade attribution by side, setup month,
  confidence bucket, anchor type, anchor source timeframe, anchor freshness,
  context/setup alignment, trigger type, reversal marker, and stale-anchor
  marker;
- `setup_attribution.csv` / `setup_attribution.md`: grouped setup-row
  attribution for both tradeable and rejected setup rows by setup snapshot time,
  trigger type, context bias, context/setup alignment, anchor type, anchor
  source timeframe, stop-distance bucket, anchor freshness, realized outcome,
  and signal filter reason;
- `errors.csv` / `errors.md` when a window cannot load or execute.

Definitions:

- `side`: `long` for `is_long = true`, otherwise `short`;
- `setup_month`: month of `signal_time` when available, otherwise
  `entry_time`;
- `confidence_bucket`: `[0,25)`, `[25,40)`, `[40,55)`, `[55,70)`, `[70,85)`,
  `[85,101]`;
- `anchor_age_hours`: `signal_time - sl_anchor_known_at` when both timestamps
  exist;
- `anchor_age_bucket`: `fresh_0_6h`, `recent_6_24h`, `stale_24_72h`,
  `old_72h_plus`, or `unknown`;
- `stale_anchor`: true when `anchor_age_hours > 72`;
- `reversal_marker`: true when D1 `context_bias` opposes
  `setup_direction`/trade side.
- `setup_snapshot_time`: the H4 setup snapshot close used for H1 MTF rows when
  setup snapshots are enabled; otherwise the row's trigger/tick time.
- `stop_distance_bucket`: `0_1_atr`, `1_2_atr`, `2_3_atr`, `3_4_atr`,
  `4_atr_plus`, or `unknown`.
- `realized_outcome`: `win`, `loss`, `flat`, or `no_trade` after joining
  executed trades back to their `signal_time`.

This diagnostic is deliberately report-only. It may justify later filters, but
it must not by itself accept a calibration candidate.

## H1 setup and anchor filters

The first filter slice must be parameterized and default-off unless the H1
diagnostic strategy config explicitly enables it. Filters are evaluated after
the H1 trigger and structural stop selection, so diagnostics still show why a
row was neutralized.

Initial filter params:

- `allowed_sides`: optional list containing `long`, `short`, or both. When
  omitted, both sides are allowed. When a side is disallowed, the row emits
  `signal = 0` with a rationale suffix.
- `blocked_sl_anchor_types`: optional list of anchor types to reject, for
  example `["liquidity_sweep"]`.
- `allowed_sl_anchor_types`: optional list of anchor types to allow. When set,
  rows whose selected structural stop anchor is not in the list are
  neutralized. This is a diagnostic allow-list for attribution follow-ups; do
  not combine it with `blocked_sl_anchor_types` unless the intent is
  explicitly documented.
- `max_anchor_age_hours`: optional positive number. Rows with a structural
  stop anchor older than this at `trigger_known_at` are neutralized. Rows with
  unknown anchor age are not rejected by this filter because missing anchors
  are already neutralized by stop planning.
- `min_signal_sl_distance_atr`: optional positive number. Rows with selected
  stop distance below this execution-ATR multiple are neutralized after stop
  planning.
- `max_signal_sl_distance_atr`: optional positive number. Rows with selected
  stop distance above this execution-ATR multiple are neutralized after stop
  planning. This is distinct from `max_sl_distance_atr`, which is the broader
  structural-stop validity guard used before filter diagnostics.
- `block_context_reversal`: optional boolean. When true, rows whose D1 context
  opposes the setup/trade side are neutralized even if they passed the earlier
  trigger path.

The accepted implementation must preserve H4 default behaviour, export
diagnostic columns for filter decisions, and include focused tests for each
filter. Bounded SOL/TON windows should then be compared with the filter config
before any broad Optuna search resumes.

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
