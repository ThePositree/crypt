# In progress

## Status as of 2026-05-15

- M1 is fully implemented and **deployed to Railway** for a 14-day
  continuous run (started 2026-05-15, ends ~2026-05-29).
- No code changes are being made during the run (Railway redeploys
  cause downtime when a volume is attached — see ADR-0010).
- This planning session (2026-05-15) produced a large amount of
  documentation for the agents who will work after the run completes.
  See `CHANGELOG.md` for that day's entry.

## What the next agent should do

### If the 14-day run is still in progress

You are most likely here because:
- The owner pasted a runtime / deploy error → **incident response**
  per AGENTS.md §2. Reproduce, minimal fix, document. Be aware that
  pushing to `master` causes a Railway redeploy (downtime). Coordinate
  with the owner before merging.
- The owner asked to expand specs further → continue from
  `docs/tasks/BACKLOG.md` P0/P1 items that are documentation-only
  (engine specs, ADRs, operations docs). No code merges.

### If the 14-day run has ended

Recommended order:

1. **Extract data and logs from Railway** per `docs/deploy/railway.md`
   Step 7. Save `data_export.tar.gz` and the full `crypt.log` somewhere
   safe — this is the dataset M2 will use.

2. **Open a post-mortem** even if nothing went wrong:
   `docs/post_mortems/2026-MM-DD-m1-run-summary.md` using the template
   at `docs/post_mortems/_template.md`. Document:
   - tick success rate over 14 days,
   - number of alerts fired by symbol,
   - any incidents,
   - any surprises in the verdict pattern.

3. **Ship the P0 quality gates** in this order:
   - GitHub Actions CI (`docs/operations/ci.md`).
   - Pre-commit hooks.
   - `[UNCALIBRATED]` marker on Telegram alerts (ADR-0011).
   - Closed-candle invariant fix (`docs/post_m1_code_fixes.md` §1).
   - Critical-inputs guard refactor (`docs/post_m1_code_fixes.md` §2).

   All five are independent and can land in 5 separate PRs.

4. **Start M2** — `docs/backtest.md`. Begin with:
   - `src/crypt/backfill/__main__.py` (need history first).
   - `ReplayParquetStore` with the look-ahead guard test.
   - The recorder, then the optimiser.

   The look-ahead test is the most important single test in the whole
   M2 milestone; write it before any reporting code.

5. **After M2 produces calibrated `weights.yaml`**:
   - Write ADR-0013 capturing the calibration result.
   - Flip `Settings.uncalibrated = False`.
   - Add the next engine in sequence: `btc_context` (cheapest,
     `docs/engines/btc_context.md`).
   - Re-run the M2 harness with the new engine in the ensemble.

## Reading list for an agent jumping in cold

In addition to the AGENTS.md §1 mandatory reading:

- `docs/post_m1_code_fixes.md` — every latent issue we know about.
- `docs/backtest.md` — the M2 contract.
- `docs/paper_trading.md` — the M3 contract.
- `docs/operator.md` — what the owner sees.
- `docs/operations/{ci,observability,telegram_commands}.md` —
  cross-cutting work that should land in parallel with M2.
- ADR-0011 and ADR-0012.

## Hard blockers (currently none)

If a hard blocker appears (e.g. Railway returns a billing-account
issue, OKX changes an API that breaks ingestion), record it here as the
first bullet so it is impossible to miss.
