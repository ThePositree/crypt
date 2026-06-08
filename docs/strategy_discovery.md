# Strategy discovery constructor

Status: **implemented** (CLI `discover-strategies`, catalog v2: 14 triggers +
33 OHLCV-only filters). Donor conversion via `convert-discovery-strategy`.

This document is the contract for the M2 label-based search step. The goal is
to reduce owner/Codex back-and-forth by replacing manual JSON strategy tinkering
with one long-running strategy discovery job.

## 1. Goal

Build a self-contained trigger/filter discovery engine that:

1. Generates strategy candidates from exactly one trigger plus zero or more
   filters.
2. Labels each candidate event with a standardized forward outcome.
3. Runs staged / beam search in code, without asking the owner which
   candidate to try next.
4. Writes ranked reports and best candidate configs.
5. Leaves risk management, leverage, margin, SL/TP optimization, RRR, TTL, and
   trailing-stop tuning for a later Optuna stage.

The immediate purpose is to answer:

> Which H1 trigger plus filter stack produces the best directional signal
> quality, measured by win rate and enough trade count?

## 2. Non-goals

Do not implement auto-execution.

Do not optimize:

- `risk_percent`
- `max_positions`
- leverage
- margin policy
- SL/TP geometry
- `rrr`
- TTL
- trailing stop

Do not run full mandate promotion from this discovery engine. Its output is a
shortlist for the existing donor backtester and later Optuna.

## 3. Core entities

### 3.1 Trigger

A trigger produces raw candidate events from closed candles only.

Required event fields:

| Field | Meaning |
| --- | --- |
| `event_time` | Closed candle time that generated the event. |
| `side` | `long` or `short`. |
| `trigger_name` | Stable trigger id. |
| `entry_reference_price` | Price used for forward label reference, usually close or next open depending on implementation contract. |
| `metadata` | Trigger-specific diagnostics. |

Triggers must be pure functions over local OHLCV/derived state. Missing data
must produce no event, not an exception.

### 3.2 Filter

A filter evaluates one trigger event and returns:

| Field | Meaning |
| --- | --- |
| `passed` | `true` means keep the event. |
| `filter_name` | Stable filter id. |
| `reason` | Stable reject/pass reason for reports. |
| `metadata` | Filter-specific diagnostics. |

Filters are veto blocks. A strategy candidate passes an event only when all
selected filters pass.

### 3.3 Candidate

A candidate is:

```text
one trigger + ordered set of zero or more filters
```

Filter order is for deterministic reporting only. The same filter set must not
be evaluated twice in different order.

## 4. Forward labels

Discovery must not use the full execution simulator as the primary evaluator.
Execution simulation entangles trigger quality with SL/TP, TTL, margin, and
position overlap. This engine compares directional signal quality with one
fixed label rule.

Default label:

```text
horizon_bars = 24
atr_period = 14
atr_mult = 1.0
```

For a long event:

- `win` if price reaches `entry_reference_price + atr_mult * ATR` before
  reaching `entry_reference_price - atr_mult * ATR`.
- `loss` if price reaches the adverse barrier first.
- `neutral` if neither barrier is reached within `horizon_bars`.

For a short event, reverse the favorable/adverse barriers.

If both barriers are hit in the same bar, use a conservative default:

```text
same_bar_policy = loss
```

ATR must be computed on closed candles only and shifted so the event candle
does not see future data.

## 5. Ranking

Primary ranking must balance win rate and trade count. Do not sort only by raw
win rate.

Required output metrics per candidate:

- `raw_events`
- `passed_events`
- `wins`
- `losses`
- `neutral`
- `win_rate`
- `loss_rate`
- `neutral_rate`
- `trades_per_window`
- `windows_passing_min_trades`
- `score`
- reject counts by filter/reason

Initial score:

```text
score = wilson_lower_bound(win_rate, wins + losses) * log1p(passed_events)
        - neutral_penalty
        - concentration_penalty
```

Acceptable MVP simplification:

```text
score = win_rate * log1p(passed_events)
```

But the report must still include raw `win_rate` and `passed_events`.

Hard gates:

- `passed_events >= min_trades_total`
- each required window should be reported separately;
- candidates with good aggregate score but only one strong window must be
  penalized or clearly flagged.

## 6. Search algorithm

The code must perform staged / beam search. Do not require the owner or Codex
to manually choose the next candidate between rounds.

Algorithm:

1. Evaluate each trigger with no filters.
2. Drop triggers below `min_trades_total` unless `--keep-sparse-triggers` is
   explicitly set.
3. For each surviving trigger, evaluate every single filter.
4. Keep the top `beam_width` candidates for each trigger.
5. For depths `2..max_filter_depth`, extend each beam candidate with one
   unused filter and evaluate the new filter set.
6. De-duplicate candidates by `(trigger_name, sorted_filter_names)`.
7. Stop when depth reaches `max_filter_depth` or no extension improves score.
8. Export the top global candidates and a full search trace.

Default search controls:

| Parameter | Default |
| --- | --- |
| `beam_width` | `20` |
| `max_filter_depth` | `4` |
| `min_trades_total` | `50` |
| `min_trades_per_window` | `10` |
| `label_horizon_bars` | `24` |
| `label_atr_mult` | `1.0` |

## 7. Trigger catalog

### v1 (MVP)

- `h1_candle_confirm`
- `h1_sweep_reversal`
- `h1_structure_break`
- `h1_order_block_retest`
- `h1_pivot_reclaim`
- `h1_range_breakout`
- `h1_momentum_burst`
- `h1_mean_revert_wick`

### v2 (OHLCV-only expansion)

All v2 triggers use closed H1 candles and derived OHLCV features only. No
derivatives, order book, or session VWAP.

- `h1_ema_cross` — EMA9/21 golden or death cross (shifted, no look-ahead).
- `h1_rsi_reversal` — RSI14 extreme (<35 / >65) with reversal candle.
- `h1_bb_rejection` — touch lower/upper Bollinger band (20, 2σ) + reversal.
- `h1_engulfing` — bullish/bearish engulfing of prior opposite candle body.
- `h1_inside_bar_breakout` — inside bar relative to mother bar, breakout close.
- `h1_nr7_breakout` — narrowest 7-bar range + directional close.

If a trigger is expensive or unclear, implement a simple deterministic version
and document its exact rule in the module docstring and generated report.

## 8. Filter catalog

### v1 (MVP)

- `side_long_only`
- `side_short_only`
- `d1_context_aligned`
- `h4_context_aligned`
- `block_context_reversal`
- `volatility_normal_only`
- `trend_strength_min`
- `atr_distance_0_1`
- `atr_distance_1_2`
- `atr_distance_2_4`
- `atr_distance_4_plus`
- `anchor_pivot_only`
- `anchor_order_block_only`
- `anchor_no_liquidity_sweep`
- `anchor_age_max_24h`
- `anchor_age_max_72h`
- `avoid_after_large_move`
- `avoid_low_volume`

### v2 (OHLCV-only expansion)

Trend / mean-reversion:

- `trend_ema_stack_aligned` — long: EMA9>EMA21>EMA50; short: reversed stack.
- `sma20_side_aligned` — close above SMA20 for long, below for short.
- `rsi_side_aligned` — long RSI 25–55; short RSI 45–75.
- `trend_strength_max` — `trend_strength_atr <= 1.5` (ranging fade).
- `roc_side_aligned` — ROC10 sign matches side.

Volatility / Bollinger:

- `volatility_low_only` — ATR percentile rank ≤ 0.2.
- `volatility_high_only` — ATR percentile rank ≥ 0.8.
- `bb_squeeze` — Bollinger width ≤ 4% of mid.
- `bb_wide` — Bollinger width ≥ 8% of mid.

Candle anatomy:

- `body_to_range_min` — body/range ≥ 0.55.
- `avoid_doji` — body/range ≥ 0.15.
- `bar_range_min_atr` — bar range ≥ 0.35 ATR.

Session / volume:

- `session_london` — hour UTC in [7, 15).
- `session_ny` — hour UTC in [13, 21).
- `volume_above_median` — volume ≥ 20-bar median (not the 0.5× floor).

**Catalog size:** 14 triggers + 33 filters (v1 + v2).

Donor conversion currently supports only the v1 subset documented in §13.
v2 blocks are discovery-only until mapped in `convert.py`.

Filters that need metadata unavailable for a given trigger/event must reject
with a stable reason such as `missing_anchor_metadata`, or be marked
`not_applicable` and excluded consistently. Pick one policy and document it in
the implementation.

## 9. CLI

Add a root backtester CLI command:

```bash
uv run backtester discover-strategies \
    --data-dir data \
    --primary-timeframe 1h \
    --symbol SOL-USDT-SWAP \
    --from 2025-01-01 \
    --to 2025-04-01 \
    --output results/discovery_sol_h1 \
    --label-horizon-bars 24 \
    --label-atr-mult 1.0 \
    --beam-width 20 \
    --max-filter-depth 4 \
    --min-trades-total 50 \
    --min-trades-per-window 10
```

The command must run to completion without asking the owner for intermediate
decisions.

Support multiple explicit windows if this is cheap to implement:

```bash
--window sol_2025_01:SOL-USDT-SWAP:2025-01-01:2025-02-01
```

If multi-window support does not fit the first implementation slice, implement
one contiguous `--from` / `--to` run and write a TODO in `BACKLOG.md`.

## 10. Artifacts

Write one timestamped output directory:

```text
results/discovery_sol_h1/<timestamp>/
  config.json
  candidates.csv
  candidates.md
  candidate_windows.csv
  candidate_windows.md
  search_trace.csv
  rejected.csv
  top_score.csv
  top_score.md
  top_win_rate_min_50.csv
  top_win_rate_min_100.csv
  top_win_rate_min_200.csv
  top_win_rate_min_500.csv
  robust_min_window_win_rate_50.csv
  best_candidates/
    rank_001_strategy.json
    rank_001_events.csv
    rank_001_report.md
    rank_002_strategy.json
    ...
    top_score/
    top_win_rate_min_50/
    top_win_rate_min_100/
    top_win_rate_min_200/
    top_win_rate_min_500/
    robust_min_window_win_rate_50/
```

`candidates.csv` must contain one row per evaluated candidate, including
aggregate metrics and robustness summary columns such as min/max per-window
win rate and minimum per-window event count. `candidate_windows.csv` must
contain one row per candidate per explicit window with events, wins, losses,
neutral count, and win rate. `search_trace.csv` must include depth, parent
candidate id, added filter, score before/after, and status.

The root shortlist CSV/Markdown files and matching `best_candidates/`
subdirectories must include:

- top candidates by score;
- top candidates by win rate at minimum sample thresholds (`50`, `100`, `200`,
  `500`);
- robust candidates where every window passes the minimum trade count and
  minimum per-window win-rate floor.

`rank_N_strategy.json` should be compatible with the current donor
`crypt_ensemble` strategy config when possible. If direct compatibility is too
large for the first session, export a discovery-native JSON with trigger and
filter names and document how to convert it later.

## 11. Suggested implementation layout

Implement as one coherent module. Do not scatter one-off scripts.

```text
src/backtester/strategy_discovery/
  __init__.py
  events.py
  triggers.py
  filters.py
  labeler.py
  search.py
  scoring.py
  report.py
```

Wire it into `src/backtester/__main__.py` as `discover-strategies`.

Focused tests:

- trigger output uses closed candles only;
- labeler handles win/loss/neutral/same-bar policy;
- filters pass/reject with stable reasons;
- beam search de-duplicates filter sets;
- score penalizes tiny samples;
- CLI writes `candidates.csv`, `search_trace.csv`, and best candidate files.

## 13. Donor conversion

Discovery-native `rank_*_strategy.json` files are not donor-executable directly.
Convert them with:

```bash
uv run backtester convert-discovery-strategy \
    --input results/discovery_sol_h1_2025_monthly/20260608_113331/best_candidates/rank_001_strategy.json \
    --output strategies/backtester/my_candidate.json
```

The checked-in reference configs:

```text
strategies/backtester/crypt_ensemble_h1_discovery_momentum_burst_short.json
strategies/backtester/crypt_ensemble_h1_discovery_nr7_bb_squeeze_h4.json
```

Conversion rules:

- all discovery triggers use `setup_source = h1_raw` (no H4 setup gate);
- `block_context_reversal` maps to `block_d1_h4_context_reversal` using the
  same D1/H4 SMA alignment rule as discovery, not the MTF
  `block_context_reversal` filter that blocks D1 SMC bias opposing the signal;
- `h4_context_aligned` maps to `require_h4_context_aligned = true`;
- `bb_squeeze` maps to `max_bb_width_pct = 0.04`;
- `trend_strength_min` maps to `min_trend_strength_atr = 0.5`;
- `avoid_low_volume` maps to `min_volume_median_ratio = 0.5`;
- converted raw configs enable `allow_atr_sl_fallback = true` because discovery
  triggers such as `h1_momentum_burst` and `h1_nr7_breakout` do not provide
  structural stop anchors.

Faithful conversion is intended for `h1_candle_confirm`, `h1_momentum_burst`,
and `h1_nr7_breakout` when paired with mapped discovery filters. Structural
discovery triggers (`h1_sweep_reversal`, `h1_structure_break`,
`h1_order_block_retest`) use simplified OHLCV rules in discovery but
SMC-backed raw rules in donor execution; convert those only for diagnostic
experiments, not label-parity claims.

After conversion, validate with owner-run `compare-fixed` across SOL 2025 monthly
windows before any Optuna work.

### Discovery vs donor trade counts

Discovery `passed_events` counts labeled trigger events after filters **without**
donor execution. Donor trade counts are lower when:

- structural SL entry gate applies (`exit_geometry=sl_rrr`, default);
- concurrent position / margin limits reject entries;
- `min_tp_move_pct` or structural exit policy skips trades.

With `exit_geometry=tp_pct` and ADR-0028 execution context, NR7 Jan 2025
aligns at **~11 trades** (discovery-filter parity for that month), not the
full-year **222** labeled events (those span all months and include neutral
labels). A future **donor-eligibility gate** in discovery (BACKLOG P1) should
approximate executable counts before ranking.
