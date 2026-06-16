# PineScript-derived DSS catalog v1

Status: accepted implementation spec

Date: 2026-06-16

## Purpose

The legacy DSS trigger/filter catalog has been heavily explored and keeps
returning the same families. `pinescript_v1` is a separate search space derived
from popular TradingView/PineScript ideas supplied under `pinescript/`.

The goal is not to port PineScript files line-for-line. The goal is to extract
OHLCV-safe trading primitives and implement them as native Python DSS triggers
and filters.

`pinescript_v1` must be selectable without mixing in the legacy catalog:

```bash
uv run backtester search-signals \
  --catalog pinescript_v1 \
  --stage-mode stage1 \
  --min-signals-per-week 4 \
  --data-dir data \
  --symbol SOL-USDT-SWAP \
  --windows 2023 \
  --n-trials 50000 \
  --n-jobs 4 \
  --seed 73023 \
  --output results/dss_sol_pinescript_v1_2023_seed73023
```

## Source ideas

| Source file | Extracted idea |
| --- | --- |
| `supertrend.pine` | ATR-band trend flip and state filter |
| `ut_bot_alerts.pine` | ATR trailing stop cross |
| `squeeze_momentum.pine` | Bollinger/Keltner squeeze release with momentum slope |
| `wavetrend_oscillator.pine` | WaveTrend cross from stretched oscillator zones |
| `MacD Custom Indicator-Multiple.pine` | MACD signal cross and histogram phase |
| `adx_di.pine` | ADX + DI directional trend regime |
| `williams_vif_fix_finds_market_bottoms.pine` | capitulation spike / bottom proxy |
| `support_resistance.pine` | pivot support/resistance break with volume |
| `trendlines_with_breaks.pine` | dynamic pivot trendline breakout |
| `ict_killzones_pivot.pine` | session/killzone high-low break concepts |
| `smc.pine` | later SMC slice: BOS/CHoCH, FVG, equal highs/lows, premium/discount |

## First implementation slice

Keep the first slice compact. Do not implement the whole SMC/ICT surface in
one step.

### Triggers

| Trigger | Logic |
| --- | --- |
| `pt_ps_supertrend_flip` | Long when close flips above prior Supertrend down band; short when close flips below prior up band. |
| `pt_ps_ut_trail_cross` | Long/short when close crosses an ATR trailing stop similar to UT Bot. |
| `pt_ps_squeeze_release` | Long/short when a BB/Keltner squeeze releases and linear-regression momentum points in the breakout direction. |
| `pt_ps_wavetrend_cross` | Long when WaveTrend fast crosses above slow from oversold; short inverse from overbought. |
| `pt_ps_macd_signal_cross` | Long/short on MACD signal cross with optional zero-line context. |
| `pt_ps_vixfix_reversal` | Long-only capitulation spike after Williams Vix Fix exceeds its band/percentile. |
| `pt_ps_pivot_volume_break` | Close breaks rolling pivot high/low with volume impulse. |
| `pt_ps_trendline_break` | Close breaks a simple pivot-derived sloped upper/lower trendline. |

### Filters

| Filter | Logic |
| --- | --- |
| `pf_ps_supertrend_state` | Event side must match current Supertrend state. |
| `pf_ps_adx_di_aligned` | ADX above threshold and DI side aligned. |
| `pf_ps_macd_hist_state` | MACD histogram sign and slope align with event side. |
| `pf_ps_squeeze_recent` | A squeeze occurred recently or is releasing now. |
| `pf_ps_wavetrend_zone` | Oscillator is/was in the side-appropriate stretched zone. |
| `pf_ps_vixfix_spike` | Capitulation spike is active/recent. |
| `pf_ps_killzone_session` | Event hour falls in Asia/London/NY AM/NY PM killzone. |
| `pf_ps_pivot_volume` | Volume oscillator/ratio is above threshold on level breaks. |
| `pf_ps_trendline_slope` | Trendline slope is side-compatible or steep enough. |

## Feature requirements

All features are computed from closed candles only. The feature value available
at event bar `t` must not use candle `t`'s final high/low/close unless the
trigger explicitly fires at the close of `t` and the entry is still next-open in
the donor path.

For DSS consistency, triggers may inspect the event candle close to create an
event, but indicator state used as filters should be shifted where it represents
pre-event context.

Required feature columns include:

- `ps_supertrend_dir`
- `ps_ut_trail`
- `ps_squeeze_on`, `ps_squeeze_release`, `ps_squeeze_momentum`,
  `ps_squeeze_momentum_slope`
- `ps_wt1`, `ps_wt2`
- `ps_macd`, `ps_macd_signal`, `ps_macd_hist`, `ps_macd_hist_slope`
- `ps_adx`, `ps_di_plus`, `ps_di_minus`
- `ps_vixfix`, `ps_vixfix_spike`
- `ps_pivot_high`, `ps_pivot_low`
- `ps_volume_osc`
- `ps_trendline_upper`, `ps_trendline_lower`,
  `ps_trendline_upper_slope`, `ps_trendline_lower_slope`

## Search policy

- `--catalog legacy` keeps current behavior.
- `--catalog pinescript_v1` uses only the new catalog.
- `--catalog all` combines both, for later comparison only.
- `--stage-mode stage1` stops after Stage 1 signal/barrier checks, writes
  `stage1_ranked.csv`, exports replayable research configs under
  `stage1_candidates/`, and does not run backtests.

The selected catalog is written into `dss_state.json` so resumed/inspected runs
can be tied back to the trigger/filter vocabulary that produced them.

The first real run should use `--catalog pinescript_v1` and one target window
(`2023`) in Stage 1-only mode to answer whether the new primitives produce a
healthier 2023 signal tail.

Use `--min-signals-per-week 4` for this catalog. A full-year window then needs
roughly 209 signals before barrier quality is considered. Candidates with only
20 signals/year are too sparse for this discovery phase.

Do not promote target-window candidates directly. They remain research
candidates until cross-window diagnostics and mandate `compare-fixed`
validation.
