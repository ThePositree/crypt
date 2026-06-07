# In progress

## Next steps — H1 trigger-first discovery reset

**Owner direction still applies:** stop-loss count limits and OHLCV coverage
preflight are canceled for the current search. Do not implement either unless
the owner explicitly revives them.

**New search protocol:** trigger-first reset. Start from raw H1 trigger
candidates, make them frequent enough to measure, then add filters one by one.
Use `rrr = 1.0` while searching for trigger/filter quality and treat PnL as
secondary. First-rank metrics are trade count, win rate, exit mix, and visual
plausibility in `trade_chart.html`. Only after a trigger/filter stack is stable
should agents search `rrr`, `ttl`, SL/TP, and trailing-stop parameters.

**What:** compare raw H1 trigger candidates one at a time:

- `strategies/backtester/crypt_ensemble_h1_trigger_raw_candle_confirm.json`
- `strategies/backtester/crypt_ensemble_h1_trigger_raw_sweep_reversal.json`
- `strategies/backtester/crypt_ensemble_h1_trigger_raw_structure_break.json`
- `strategies/backtester/crypt_ensemble_h1_trigger_raw_order_block_retest.json`

**Why now:** the latest structural H1 branch stayed sparse and below mandate
even after removing TTL and distance-filter hypotheses. Optimizing PnL on a
rare trigger is premature; the project needs a measurable entry event first.

**Expected gain:** identify whether any simple H1 trigger produces enough
trades and a usable win-rate baseline before spending more compute on filters
or execution parameters.

**Acceptance:** for each raw trigger candidate, produce owner-run
`compare-fixed` artifacts on the same reviewed windows with `rrr = 1.0`; write
a verdict that selects the next trigger to filter, or rejects this H1 premise
if all raw triggers remain too sparse or low quality.

Current raw candle-confirm artifact:

- `results/crypt_h1_trigger_raw_candle_confirm_r1/20260607_212807/`.
- Executed trades remained low because `max_positions = 1` throttled a much
  larger active-signal stream: SOL Jan `174` active signals -> `21` trades,
  SOL Mar `116` -> `21`, TON Feb `181` -> `23`.
- Win rate at `rrr = 1.0`: SOL Jan `38.10%`, SOL Mar `57.14%`, TON Feb
  `56.52%`.

Current higher-concurrency/no-TTL artifact:

- `results/crypt_h1_trigger_raw_candle_confirm_r1_pos5/20260607_213715/`.
- Ran with `ttl = 0`, `max_positions = 5`.
- Executed trades still remained too low for trigger discovery: TON Feb `21`,
  SOL Jan `46`, SOL Mar `30`.
- Conclusion: execution concurrency and TTL are not the main bottleneck. The
  current raw trigger configs still depend on H4 setup direction and context
  gating, so they are not raw enough for the owner-directed reset.

Next command template, no-setup raw H1 candle trigger:

```bash
uv run backtester compare-fixed \
    --data-dir data \
    --primary-timeframe 1h \
    --strategy strategies/backtester/crypt_ensemble_h1_raw_candle_confirm_no_setup.json \
    --window ton_2025_02:TON-USDT-SWAP:2025-02-01:2025-03-01 \
    --window sol_2025_01:SOL-USDT-SWAP:2025-01-01:2025-02-01 \
    --window sol_2025_03:SOL-USDT-SWAP:2025-03-01:2025-04-01 \
    --output results/crypt_h1_raw_candle_confirm_no_setup_r1_pos5 \
    --rrr 1.0 \
    --ttl 0 \
    --risk-percent 1.0 \
    --max-positions 5 \
    --risk-base-period monthly \
    --is-isolated-futures \
    --jobs 3
```

Relevant rejected-branch artifacts:

- Density baseline review:
  `results/crypt_h1_visual_review_baseline_density/20260607_210508/`.
- Density age6/noOB review:
  `results/crypt_h1_visual_review_age6_no_ob_density/20260607_211115/`.
- Baseline structural trigger:
  `results/crypt_ensemble_h1_structural_trigger_bounded_isolated/20260607_183249/`.
- Age-6 no-order-block diagnostic:
  `results/crypt_ensemble_h1_trigger_age6_no_ob_bounded/20260607_185632/`.
- Age-6 no-order-block with `2..4 ATR` signal stop-distance filter:
  `results/crypt_ensemble_h1_trigger_age6_no_ob_distance_2_4_bounded/20260607_191049/`.
- Tiny execution grid for the same diagnostic:
  `results/crypt_ensemble_h1_trigger_age6_no_ob_distance_2_4_grid/20260607_192915/`.
