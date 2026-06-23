# Archived strategy candidates

Git-tracked archive per `docs/backtester/candidate_archive.md`.
Full backtest artifacts live under `results/` (not in git).

The archive is also the future training/evidence base for regime discovery.
Strategies may be kept as `regime_seed` or `research_seed` when they are useful
for understanding where a signal family works, even if they do not pass the
full production mandate.

| candidate_id | Archived | Reason | Best evidence | Superseded by |
| ------------ | -------- | ------ | ------------- | ------------- |
| [nr4_vwap_robust](nr4_vwap_robust/) | 2026-06-22 | research_seed | +148.71% (SOL 2022-2024 Optuna best-run, discard) | — |
| [island_2023_021396_engulfing_bb_trend](island_2023_021396_engulfing_bb_trend/) | 2026-06-22 | research_seed | +375.80% (SOL 2022-2024 Optuna best-run, discard) | — |
| [smac_003335_double_bottom_body_to_range](smac_003335_double_bottom_body_to_range/) | 2026-06-22 | research_seed | +258.21% (SOL 2022-2024 Optuna best-run, discard) | — |
| [dssv2_013321_macd_squeeze_recent](dssv2_013321_macd_squeeze_recent/) | 2026-06-18 | near_miss | +161.09% (SOL 2023 mandate_score Optuna) | — |
| [nr7_bb_squeeze_h4](nr7_bb_squeeze_h4/) | 2026-06-09 | superseded | +58.82% (tp_pct Optuna) | NR4 vwap band |
| [vwap_reclaim_robust](vwap_reclaim_robust/) | 2026-06-09 | superseded | +50.26% (tp_pct Optuna) | NR4 vwap band |
