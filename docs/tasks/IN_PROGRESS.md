# In progress

## Next steps — stop-loss count limits

The real SOL 2025 mandate validation for the current H1 short-only row is
complete and discarded:
`results/crypt_ensemble_h1_short_only_sol_2025_mandate/20260606_120001/`.

**Take next:** implement the P1 stop-loss count limits in `BACKLOG.md`:
`max_stop_losses_per_day`, `max_stop_losses_per_month`, and
`max_consecutive_stop_losses`.

**Why now:** the current fixed TP / short-only execution row failed the mandate
hard (`0/12` months passed the `+15%` floor), so further work should add the
approved risk-control search dimensions rather than re-running this same row.

**Expected gain:** future Optuna/full-candidate searches can pause entries
after clusters of stop-loss exits, reducing death-by-a-thousand-stops profiles
before mandate evaluation.

**Acceptance:** limits pause new entries per `docs/investment_mandate.md`
§6.2; exported trades or diagnostics show when limits are active; optimizer
and CLI wiring have focused tests.

Start from `src/backtester/execution_sim.py` and
`tests/backtester/test_execution_sim_run.py`.
