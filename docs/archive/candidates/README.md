# Archived strategy candidates

Git-tracked archive per `docs/backtester/candidate_archive.md`.
Full backtest artifacts live under `results/` (not in git).

The archive is also the future training/evidence base for regime discovery.
Strategies may be kept as `regime_seed` or `research_seed` when they are useful
for understanding where a signal family works, even if they do not pass the
full production mandate.

| candidate_id | Archived | Reason | Best evidence | Superseded by |
| ------------ | -------- | ------ | ------------- | ------------- |
| [dssv2_013321_macd_squeeze_recent](dssv2_013321_macd_squeeze_recent/) | 2026-06-18 | near_miss | +161.09% (SOL 2023 mandate_score Optuna) | — |
| [nr7_bb_squeeze_h4](nr7_bb_squeeze_h4/) | 2026-06-09 | superseded | +58.82% (tp_pct Optuna) | NR4 vwap band |
| [vwap_reclaim_robust](vwap_reclaim_robust/) | 2026-06-09 | superseded | +50.26% (tp_pct Optuna) | NR4 vwap band |

**Active candidate:** `strategies/backtester/crypt_ensemble_h1_discovery_nr4_vwap_robust.json`
— see `docs/tasks/IN_PROGRESS.md`.
