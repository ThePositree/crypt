# Live/backtest parity audit — 2026-06-30

## Scope

This audit compared the active causal v3 Core4 backtester and OKX live
execution paths across signal generation, candle timing, risk sizing, margin,
leverage tiers, liquidation, entries, protection, trailing, fees, fills,
multiple positions, restart recovery, and tests.

The validated live signal cache remains signal-neutral: the owner-run
39,711-bar parity run produced byte-identical CSV artifacts to canonical run
`20260629_160832`. That result proves signal/cache parity only. It does not
prove exchange-execution parity.

## Confirmed parity

- Complete and cached latest-signal paths agree before the live cache is used.
- Signals use closed H1/H4/D1 candles and enter on the next H1 boundary.
- Backtest and live share exit geometry, risk sizing, monthly risk base,
  liquidation-safe whole-number leverage selection, SOL size tiers, same-side
  aggregate liquidation, and native trailing geometry.
- Existing same-side positions retain their exchange leverage; a lower current
  tier cap is applied only to new aggregate exposure.
- TTL identity is anchored to the H1 entry boundary in both paths.
- Client IDs make ambiguous HTTP entry and trailing-order retries recoverable.
- The non-hanging unit suite passes.

## P0 safety findings

### Non-atomic post-fill state

The exchange entry fills before the local `LivePosition` is persisted.
Contract-size lookup, liquidation calculations, trailing calculations, or a
process crash can occur in that gap. Exchange sync then sees an orphan
position, blocks new entries, but cannot reconstruct or manage the trade.

Required fix: persist an entry intent before submission and adopt the actual
order/position by deterministic client ID after success, timeout, or restart.

### TTL can leave an unprotected position

TTL handling cancels TP, trailing, and SL before submitting the reduce-only
market close. If close submission fails, the position is reset to `open` but
has no protection until the next H1 cycle.

Required fix: submit/confirm the close before cancelling surviving protection,
or immediately restore protection when close confirmation fails.

### Failed trailing placement is not fail-safe

After a filled entry, native trailing is placed as a second order. A trailing
failure only sends an alert; the live trade remains open with behavior that no
longer matches the backtest.

Required fix: retry/recover by client ID and close the new position immediately
if required protection cannot be confirmed.

### Unsafe post-fill conditions only alert

Actual fill drift can make aggregate liquidation unsafe or cross a leverage
tier after the order is filled. Current code sends an execution error but
leaves the unsafe position open.

Required fix: treat post-fill safety failure as a compensating close, with
state and fill reconciliation.

### Ambiguous fill attribution

When OKX omits client/algo IDs, fill matching falls back to side subtype and
ultimately accepts any fill. Multiple same-side local trades are one aggregate
OKX position, so one partial close can be attributed to more than one local
trade.

Required fix: allocate fills once by stable order/algo identity and consumed
quantity. Never use an unconditional match in multi-position mode.

## Backtest/live model differences requiring a new canonical backtest

### Instrument precision

Live rounds asset size down to the OKX amount step and rounds SL, TP, trailing
activation, and callback spread to the tick. The backtester uses continuous
values.

In canonical output:

- all 3,418 sizes are off the `0.01 SOL` live step;
- 3,323 SL values and 3,364 TP values are off the `0.01 USDT` tick;
- 3,287 trailing activation prices are off tick.

At `$10,000` the mean size reduction is only `0.0020%`, but at the current
roughly `$105` balance it can be materially larger. Precision must become a
shared pre-trade policy, then v3 must be rerun.

### Funding

Historical funding data exists, but neither backtest PnL nor live per-trade PnL
classification includes funding. OKX cash balance does include actual funding,
so later risk sizing can diverge even when reported trade PnL appears matched.

Required fix: debit/credit funding at historical settlement timestamps in the
backtest and attribute actual OKX funding to live positions.

### Entry-fee timing

OKX deducts the entry fee immediately. The backtester leaves it in capital
until exit, although it includes the fee in final closed PnL. Overlapping
position eligibility and sizing can therefore diverge.

Required fix: debit entry fees on entry and add only gross price PnL minus exit
fee at close.

### Entry and exit execution prices

The backtester enters exactly at the H1 open. Live enters several seconds later
at market and rejects quotes beyond `0.1%` drift. This already rejected a
historical backtest entry at `0.934%` drift. Market slippage and the drift gate
cannot be reproduced from H1 OHLC alone.

Fixed take-profit is always charged as maker in the backtest, while an OKX
triggered limit can execute as taker. Live correctly stores actual fees.

Required fix: define an explicit execution model. Exact exchange parity needs
sub-minute/tick data; otherwise backtest results must be presented as an H1
model with measured live slippage and rejection stress.

### Liquidation trigger source and intrabar order

OKX `liqPx` is a mark-price threshold. The backtester checks last-trade H1
high/low. Its worst-case policy can choose liquidation when one H1 bar also
touches the structural stop, even though a continuous price path would cross
the nearer stop first. The current 147 liquidation exits are conservative but
not exact OKX simulations.

Required fix: use historical mark-price candles and document/resolve remaining
same-bar ambiguity with finer data.

### Static SOL tier table

The SOL tier table is a dated snapshot. Live sync checks actual `liqPx`, but it
does not compare actual exchange leverage/margin/tier metadata with the local
model.

Required fix: refresh/version public tiers and reconcile actual leverage and
margin on every snapshot.

## Operational differences

- Telegram entry-attempt delivery is awaited before risk and order placement.
  Telegram retries can delay the market order after the one existing drift
  check. Notifications must be non-blocking, and price safety must be checked
  again immediately before submission.
- Position-open logs print planned contracts, liquidation, and margin rather
  than actual rounded/fill values.
- One executor test reaches its passing assertion but hangs during shutdown
  after `run_in_executor`; the full suite cannot currently terminate without
  excluding that test.
- Repository-wide Ruff and strict mypy are not clean. Focused live execution
  lint is clean; `ExecutionSim` has existing type errors.

## Verification evidence

- Owner-run cache parity: all seven CSV artifacts byte-identical.
- Unit tests: all tests pass when
  `test_on_h1_close_rechecks_sync_after_marking_missing_position_closed` is
  excluded.
- The excluded test prints a pass marker but is still alive after 20 seconds
  and is terminated by timeout.
- Focused mypy: 9 errors, all in `src/backtester/execution_sim.py`.
- Focused Ruff: 6 findings in legacy backtester files; repository-wide Ruff:
  232 findings.

## Verdict

Signal parity is proven. Risk-policy parity is substantially implemented.
Execution parity and crash safety are not yet sufficient for unattended live
trading. Complete the P0 safety fixes first, then implement shared precision,
fee timing, and funding before treating a new v3 backtest as the live economic
baseline.
