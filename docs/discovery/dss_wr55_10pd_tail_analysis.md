# DSS WR55/10pd tail analysis

Date: 2026-06-16

Source archive: `dss_wr55_10pd_searches_20260616_142549_tar.gz` supplied by
the owner. The archive was inspected locally from `/tmp`; the raw `results/`
artifacts remain local and should not be committed.

## Inputs

The archive contains five SOL DSS Stage 1 searches with the path-aware barrier
gate, `barrier_win_rate >= 55%`, `tp_first > sl_first`, and the 10 signals/day
overtrading cap.

| Run | Rows inspected | Final Stage 1 survivors |
| --- | ---: | ---: |
| `dss_sol_v2_barrier_wr55_10pd_seed60616` | 1,200,000 | 0 |
| `dss_sol_v2_barrier_wr55_10pd_seed60617` | 648,423 | 0 |
| `dss_sol_v2_barrier_wr55_10pd_seed60618` | 646,390 | 0 |
| `dss_sol_v2_barrier_wr55_10pd_2023first_seed60619` | 61,747 | 0 |
| `dss_sol_v2_barrier_wr55_10pd_2023first_seed60620` | 61,862 | 0 |

`seed60617`, `seed60618`, `2023first_seed60619`, and
`2023first_seed60620` are partial snapshots. `seed60616` is the completed
1.2M-trial run.

## 2022-first result

The completed `seed60616` run found 31,241 configurations that passed the 2022
Stage 1 barrier gate. None also passed 2023.

Failure after passing 2022:

| Rejection after 2022 pass | Count |
| --- | ---: |
| `weak_barrier_win_rate:2023` | 30,784 |
| `overtrading:2023` | 457 |

Top repeated 2022-pass families:

| Trigger | Filters | Count |
| --- | --- | ---: |
| `pt_engulfing` | `pf_trend_ema_stack` | 923 |
| `pt_mean_revert_wick` | `pf_side_short_only` | 915 |
| `pt_engulfing` | `pf_side_short_only` | 906 |
| `pt_order_block_retest` | `pf_side_short_only` | 833 |
| `pt_vwap_reclaim` | `pf_side_short_only` | 780 |
| `pt_order_block_retest` | `pf_trend_ema_stack` | 728 |
| `pt_vwap_reclaim` | `pf_trend_ema_stack` | 609 |
| `pt_compression_breakout` | `pf_side_short_only` | 518 |

The best 2023 near-miss in the 2022-first run:

```text
candidate_id: dssv2_085986
trigger: pt_engulfing
filters: pf_body_to_range_min + pf_context_aligned + pf_side_short_only
2022: signals=20, barrier_win_rate=0.6000
2023: signals=127, barrier_win_rate=0.5354, tp_first=0.5354, sl_first=0.4646
rejection: weak_barrier_win_rate:2023
```

Interpretation: the 2022-pass tail is not empty or random. It is mostly
short/trend or short/context candidate families. Some are close to the 2023
WR55 threshold, but the best observed 2023 barrier win rate remained about
0.5354 after 1.2M trials.

## 2023-first result

Both 2023-first snapshots found the same 38 candidates that passed the 2023
barrier gate. None also passed 2022; all 38 were rejected with
`too_few_signals:2022`.

2023-pass trigger mix:

| Trigger | Count |
| --- | ---: |
| `pt_rsi_reversal` | 10 |
| `pt_engulfing` | 8 |
| `pt_bb_rejection` | 7 |
| `pt_nr4_breakout` | 6 |
| `pt_structure_break` | 4 |
| `pt_mean_revert_wick` | 1 |
| `pt_compression_breakout` | 1 |
| `pt_range_breakout` | 1 |

Representative 2023 specialists:

| Candidate | Trigger | Filters | 2023 signals | 2023 WR | 2022 signals |
| --- | --- | --- | ---: | ---: | ---: |
| `dssv2_017163` | `pt_compression_breakout` | `pf_bar_range_min + pf_side_long_only` | 21 | 0.7143 | 3 |
| `dssv2_061351` | `pt_nr4_breakout` | `pf_bb_width + pf_body_to_range_min + pf_volume_ratio` | 24 | 0.6250 | 4 |
| `dssv2_023651` | `pt_nr4_breakout` | `pf_rsi_zone + pf_side_short_only` | 21 | 0.6190 | 4 |
| `dssv2_011908` | `pt_mean_revert_wick` | `pf_anchor_age + pf_bb_width + pf_context_aligned` | 23 | 0.6087 | 1 |
| `dssv2_022236` | `pt_rsi_reversal` | `pf_bar_range_min + pf_session + pf_trend_strength` | 23 | 0.6087 | 0 |
| `dssv2_049501` | `pt_bb_rejection` | `pf_session + pf_volume_ratio + pf_vwap_proximity` | 25 | 0.6000 | 5 |

Common parameter shape in the 2023 specialist tail:

- many `rrr=1.5`, `ttl=24`, `atr_sl_mult=0.75` candidates;
- several session/volume specialists, especially `session=asia` with high
  `pf_volume_ratio`;
- more mean-reversion and compression/BB/RSI behavior than the 2022-pass tail;
- sparse 2022 activity, often 0-5 signals for the whole year.

## Conclusion

This is a regime-conflict finding, not a simple compute-budget failure.

The current all-window Stage 1 requirement assumes that one trigger/filter
recipe must produce enough signals and WR55 edge in every checked year before
it receives Stage 2 budget. The artifacts show a different structure:

- 2022 has many tradeable-looking specialists, often short/trend/context
  families.
- 2023 has rare specialists, often mean-reversion/compression/session-volume
  families.
- the overlap is absent under the current constructor and hard Stage 1 gate.

Adding more identical seeds is unlikely to change the conclusion. The next
implementation should make regime specialization explicit instead of forcing
all candidates through a single all-year Stage 1 gate.

## Next implementation choice

Add a DSS regime-specialist path before more owner-scale searches:

1. Stage 1 should be able to mark candidates as `balanced` or
   `specialist:<window>` instead of rejecting every candidate that lacks enough
   signals in one non-target window.
2. Specialist candidates must still pass strict signal count, overtrading, and
   barrier quality gates on their target window.
3. Specialists should enter a separate archive and report with
   `target_window`, cross-window signal counts, and cross-window barrier
   metrics.
4. Stage 2 should score specialists on the target window plus at least one
   adverse/check window as diagnostic, but not pretend they are all-window
   robust.
5. No specialist JSON should be promoted directly. A later routing layer or
   ensemble-composition step must decide when each specialist is allowed to
   trade.

This is not a sixth optimizer backend. It is a search contract change: preserve
regime-specific edge so the project can evaluate whether routing/composition is
viable.
