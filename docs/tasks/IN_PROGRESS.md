# In progress

## Status as of 2026-05-29

M1 14-day run is complete (ended 2026-05-29). All P0 post-run quality gates are
shipped. The system is stopped (or can be stopped — owner decides).

## Next steps for the next agent

### Priority order

1. **Start M2 backtest harness** — spec in `docs/backtest.md`.

   Recommended order within M2:
   1. `src/crypt/backfill/__main__.py` — backfill CLI (pagination, resume
      safety, rate limit, tqdm). This fetches H4/H1/D1 history for the last
      ≥ 6 months from OKX.
   2. `ReplayParquetStore` with **look-ahead guard test** — write the test
      first (`tests/backtest/test_lookahead_guard.py`), then the guard.
      This is the most important single test in the whole M2 milestone.
   3. `BacktestRecorder` + `BacktestExecutionSimulator`.
   4. Forward-label loader (`return_h4 / h24 / h96`, `mae / mfe`).
   5. Fee + slippage model.
   6. Walk-forward CV (default 5 folds).
   7. Weight optimiser (grid + coordinate descent).
   8. Bootstrap CI (1000 resamples).
   9. Baseline comparison (buy-and-hold, always-hold, random-direction).
   10. HTML report.
   11. `weights.recommended.yaml` writer.

2. **P1 operability items** (can run in parallel with M2):
   - Telegram bot commands (`/status`, `/last`, `/health`, etc.) —
     `docs/operations/telegram_commands.md`.
   - Per-tick metrics JSONL — `docs/operations/observability.md` Gap A.
   - Error webhook (loguru → Telegram) — Gap B.

3. **After M2 produces calibrated `weights.yaml`**:
   - Write ADR-0014 (calibration result: dataset window, expectancy, CI,
     weight values).
   - Flip `Settings.uncalibrated = False` default in `config.py`.
   - Add `btc_context` engine — `docs/engines/btc_context.md`.
   - Re-run M2 harness with new engine.

## Hard blockers (currently none)

If a hard blocker appears (e.g. Railway billing issue, OKX API change), record
it here as the first bullet so it is impossible to miss.

## Reading list for an agent jumping in cold

- `AGENTS.md` (mandatory)
- `docs/backtest.md` (M2 contract — read before writing any backtest code)
- `docs/post_mortems/2026-05-29-m1-run-summary.md` (what the 14-day run showed)
- `docs/post_m1_code_fixes.md` (remaining P1 latent issues)
- `docs/decisions/0013-crypt-stdlib-name-conflict.md` (important: always use
  `uv run pytest` not bare `python`; always `PYTHONPATH=src uv run python -m crypt`)
- `docs/paper_trading.md` (M3 contract — for context)
