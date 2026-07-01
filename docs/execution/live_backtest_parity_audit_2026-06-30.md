# Live/backtest parity audit — 2026-06-30

## Scope

This audit compared the active causal v3 Core4 backtester and OKX live
execution paths across signal generation, candle timing, risk sizing, margin,
leverage tiers, liquidation, entries, protection, trailing, fees, fills,
multiple positions, restart recovery, and tests.

## 2026-07-01 full-code re-audit

The precision/fee changes are deterministic and the functional suite passes,
but the re-audit found two unresolved P0 restart gaps. Live execution must not
be treated as unattended-safe until both are fixed and fault-injection tested.

### P0: `closing` positions are abandoned after restart

Fail-safe close persists `status="closing"` before submitting the reduce-only
market order. Startup reconciliation, position management, and exchange sync
only inspect `status="open"`. A crash in this window can therefore leave a
real position unmanaged, or leave a locally stuck record after the exchange
close succeeds.

Required fix: reconcile `closing` by deterministic close client ID, adopt a
confirmed fill, retry the reduce-only close when the side remains open, and
retain/repair protection until the close is confirmed.

### P0: persisted entry intent is not adopted after restart

The intent is now saved before submission, but startup only checks whether an
exchange side exists. It does not query the deterministic entry client ID,
replace planned entry/size/fee with the actual fill, or repair/close a position
whose required trailing protection was not placed before the crash.

Required fix: add an explicit entry lifecycle and startup adoption path:
`intent -> submitted -> filled -> protected`, with actual fill recovery by
client ID and fail-safe closure when required protection cannot be confirmed.

### P1: intrabar H1 execution remains materially ambiguous

- Liquidation is selected before the nearer structural stop whenever both
  levels appear in one H1 range. Under a continuous last-trade path the stop
  must be crossed first; exact OKX liquidation additionally needs mark-price
  candles.
- Native trailing updates its favorable extreme from the full H1 high/low and
  then tests the opposite extreme against the newly moved stop. This assumes
  a favorable intrabar order that H1 OHLC does not prove.
- Stop, trailing, and liquidation exits fill exactly at their trigger even
  when the bar opens through it.
- Same-side aggregate liquidation is recalculated only after every position
  has been evaluated for the bar, so one intrabar close cannot change another
  position's liquidation during that same bar.

These gaps mean the 144 liquidations and 1,439 trailing exits in artifact
`20260701_091336` are not execution-grade evidence without a finer path model.

### P1: additional live gaps

- Leverage setup writes both long and short sides although OKX isolated hedge
  leverage is side-specific. An unrelated opposite-side position/order can
  make a valid new entry fail.
- Entry fill confirmation waits only about two seconds; a later fill falls
  into the incomplete restart-adoption path.
- Drift is correctly alert-only for trade-set parity, but actual fill movement
  can increase stop-loss dollars above the configured risk because sizing and
  stop geometry are not revalidated against actual filled risk.
- Strategy/live parity validation does not compare maker/taker fees or the
  instrument precision policy, so environment overrides can silently diverge.
- Fill reconciliation matches client IDs but not stored exchange order IDs,
  has no explicit trade-ID deduplication, and only requests the latest 100
  fills.
- Health-check failures are log-only rather than Telegram execution errors.
- Direct parquet writes are non-atomic; a crash-corrupted file is treated as
  absent and a later write can replace history with only fresh rows.
- The WebSocket callback has no deadline. A hung callback remains `in_flight`,
  causing the `*:02` REST fallback to skip the same boundary.

### Repository quality and security

- Repository-wide Ruff reports 232 findings. Most are legacy style/dead-code
  debt, but unused production variables and mutable class defaults are mixed
  into the same unclean baseline.
- Strict mypy reports 280 errors in 24 files, concentrated in research,
  visualization, discovery, and `ExecutionSim`; focused live execution
  typing passes.
- Legacy SOM/forest strategies deserialize arbitrary pickle paths from
  configuration. Those configs and model files must be treated as trusted
  code, not user-supplied data.
- Dependency lock validation passes offline. No network vulnerability database
  scan was available in this audit.

## 2026-07-01 remediation

ADR-0055 resolves the deterministic findings:

- explicit entry lifecycle is persisted and actual fills/protection are
  adopted by client ID after restart;
- `closing` remains managed, complete/partial close fills are accumulated by
  order ID, and only the remaining reduce-only quantity is retried;
- leverage writes target only the requested OKX side and sync compares actual
  leverage/margin mode;
- fills match client or exchange order IDs and duplicate trade IDs are ignored;
- live rejects an exchange precision change that differs from the backtest
  policy, and strategy validation includes precision plus maker/taker fees;
- health failures reach the execution notifier, parquet replacement is atomic,
  corrupt parquet cannot be silently replaced, and H1 callbacks time out before
  the REST fallback;
- last-price H1 stops precede deeper liquidation, trailing cannot use a
  favorable-then-adverse same-bar path under `worst_case`, gap exits use the
  adverse open, aggregate liquidation refreshes after constituent closes, and
  triggered TP limits pay taker fees.

Historical mark-price candles and measured live slippage remain empirical
calibration work, not deterministic code defects.

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

Implemented on 2026-07-01: intent and deterministic IDs are saved before
submission; actual fill data is adopted afterward.

### TTL can leave an unprotected position

TTL handling cancels TP, trailing, and SL before submitting the reduce-only
market close. If close submission fails, the position is reset to `open` but
has no protection until the next H1 cycle.

Required fix: submit/confirm the close before cancelling surviving protection,
or immediately restore protection when close confirmation fails.

Implemented on 2026-07-01: TTL closes first, persists the confirmed close, then
cancels only surviving protection.

### Failed trailing placement is not fail-safe

After a filled entry, native trailing is placed as a second order. A trailing
failure only sends an alert; the live trade remains open with behavior that no
longer matches the backtest.

Required fix: retry/recover by client ID and close the new position immediately
if required protection cannot be confirmed.

Implemented on 2026-07-01: an unconfirmed trailing order triggers a
deterministic reduce-only fail-safe close before notification retries.

### Unsafe post-fill conditions only alert

Actual fill drift can make aggregate liquidation unsafe or cross a leverage
tier after the order is filled. Current code sends an execution error but
leaves the unsafe position open.

Required fix: treat post-fill safety failure as a compensating close, with
state and fill reconciliation.

Implemented on 2026-07-01 for liquidation and leverage-tier failures.

### Ambiguous fill attribution

When OKX omits client/algo IDs, fill matching falls back to side subtype and
ultimately accepts any fill. Multiple same-side local trades are one aggregate
OKX position, so one partial close can be attributed to more than one local
trade.

Required fix: allocate fills once by stable order/algo identity and consumed
quantity. Never use an unconditional match in multi-position mode.

Implemented on 2026-07-01: each fill is allocated to at most one exact
client/algo identity; ambiguous or unidentified multi-position fills remain
unknown instead of being guessed.

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
roughly `$105` balance it can be materially larger. ADR-0053 defines the dated
`okx_sol_usdt_swap_2026_07_01` policy from public OKX metadata:
`contractSize=1`, amount step/minimum `0.01`, and price tick `0.01`.

### Funding

Funding remains outside this parity scope by explicit owner decision on
2026-07-01. Neither side attributes funding to individual strategy trades.

### Entry-fee timing

OKX deducts the entry fee immediately. The backtester leaves it in capital
until exit, although it includes the fee in final closed PnL. Overlapping
position eligibility and sizing can therefore diverge.

ADR-0053 requires debiting entry fees on entry and adding only gross price PnL
minus exit fee at close.

### Entry and exit execution prices

The backtester enters exactly at the H1 open. Live enters several seconds later
at market. The former `0.1%` rejection already skipped a historical backtest
entry at `0.934%` drift. ADR-0054 removed that structural mismatch: the
threshold now logs and alerts on actual H1-to-fill drift but never blocks an
otherwise valid entry. Market slippage still cannot be reproduced exactly from
H1 OHLC alone.

Fixed take-profit is always charged as maker in the backtest, while an OKX
triggered limit can execute as taker. Live correctly stores actual fees.

Remaining work: measure actual H1-to-fill slippage and stress it against the H1
baseline. Exact exchange parity needs sub-minute/tick data.

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
  check. Entry-attempt delivery is now scheduled without waiting for Telegram;
  fail-safe closes also run before their error notification.
- One executor test reaches its passing assertion but hangs during shutdown
  after `run_in_executor`; the full suite cannot currently terminate without
  excluding that test.
- Repository-wide Ruff and strict mypy are not clean. Focused live execution
  lint is clean; `ExecutionSim` has existing type errors.

## Verification evidence

- Owner-run cache parity: all seven CSV artifacts byte-identical.
- Owner-run precision/fee canonical artifact:
  `results/core4_v3_precision_fee_parity_20260701/20260701_091336/`.
  Its signals, signal diagnostics, and OHLCV are byte-identical to canonical
  `20260629_160832`; only execution outcomes changed.
- The new artifact has 3,420 entries, zero off-step sizes/prices, final capital
  `$588,744.28`, 144 liquidations, and two open-position entry fees totalling
  `$190.4181`. Final capital reconciles exactly as initial capital plus closed
  net PnL minus those open entry fees.
- Unit tests: all tests pass when
  `test_on_h1_close_rechecks_sync_after_marking_missing_position_closed` is
  excluded.
- The excluded test prints a pass marker but is still alive after 20 seconds
  and is terminated by timeout.
- Focused changed live code passes strict mypy and Ruff. Repository-wide Ruff
  retains 229 legacy findings; strict mypy retains 280 errors in 24
  research/legacy files.

## Verdict

Signal parity is proven and deterministic audit defects are remediated.
Funding is intentionally excluded. Artifact `20260701_091336` is superseded:
conservative trailing, stop/liquidation ordering, gap fills, and TP fees change
money outcomes. Live must remain stopped until the owner produces and reviews
the new canonical Core4 v3 artifact. Historical mark-price liquidation and
measured market slippage remain explicit empirical uncertainty.
