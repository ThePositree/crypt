# Liquidation-safe leverage contract

## Scope

This contract applies to isolated USDT-margined linear perpetual positions in
both `ExecutionSim` and Core4 live execution.

## Inputs

- entry price;
- resolved structural stop;
- side;
- position notional;
- available margin cap;
- maximum allowed leverage;
- optional leverage already shared by active positions;
- maintenance margin rate;
- liquidation fee rate;
- liquidation safety buffer as a fraction of entry price.

## Liquidation estimate

Let:

- `E` = entry price;
- `L` = leverage;
- `m` = maintenance margin rate plus liquidation fee rate.

For a long:

```text
liq = E * (1 - 1/L) / (1 - m)
```

For a short:

```text
liq = E * (1 + 1/L) / (1 + m)
```

The estimate uses the same linear USDT-swap formula published by OKX. When
`maintenance_margin_tier_schedule` is configured, both backtester and live
execution resolve maintenance margin rate and maximum allowed leverage from the
position size before calculating liquidation. The current live SOL schedule is
`okx_sol_usdt_swap_2026_06_29`, matching the OKX public isolated SWAP tiers
observed on 2026-06-29:

- up to `5000` SOL contracts: MMR `0.004`, max leverage `100x`;
- `5000.01..10000`: MMR `0.005`, max leverage `66.66x`;
- `10000.01..20000`: MMR `0.0075`, max leverage `50x`;
- from tier 4 onward, max size increases by `20000` contracts per tier, MMR
  increases by `0.005` per tier, and max leverage follows the OKX initial
  margin tier cap.

## Safety rule

For a long:

```text
liq <= structural_sl - E * liquidation_buffer_pct
```

For a short:

```text
liq >= structural_sl + E * liquidation_buffer_pct
```

Search whole-number leverage from the configured maximum downward. Select the
first leverage that satisfies the safety rule and whose locked margin fits the
normal per-entry margin cap. Reject the trade if none exists.

When positions are already open on the same OKX side, do not change that side's
leverage implicitly. Reuse the same-side leverage only when it remains within
the aggregate size tier and is safe/affordable for the new entry; otherwise
reject the new entry. If the side has no open position, choose fresh leverage
from the current aggregate size tier. The opposite OKX side is independent in
long/short mode and does not force its leverage onto the new side.

OKX aggregates all positions for one instrument and position side. Before an
overlapping entry, both live and backtester calculate the size-weighted average
entry for that side, derive one aggregate liquidation price, and require it to
remain beyond every constituent structural stop plus its buffer. Closing one
constituent recomputes the remaining side liquidation price.

The aggregate liquidation calculation resolves the tier from the total same-side
size, not from each child entry independently.

## Outputs

Every accepted risk result and backtester trade exports:

- selected leverage;
- locked margin;
- estimated liquidation price;
- maintenance margin rate;
- maintenance margin tier schedule, when configured;
- liquidation fee rate;
- liquidation buffer percentage;
- structural stop price.

## Backtester liquidation exit

The simulator checks the estimated liquidation level on every position bar.
When the candle reaches both the structural stop and liquidation price, their
true intrabar order is unknown:

- `worst_case` records `exit_reason=liquidation` at the estimated liquidation
  price;
- `best_case` keeps the normal structural-stop result.

This is deliberately conservative. It makes liquidation visible in historical
results instead of assuming that a last-price stop always executes before
OKX's mark-price liquidation engine.

## Live validation

After OKX confirms an entry, fetch the exchange position and compare its
reported `liqPx` against every local stop on the same side. An unsafe exchange
liquidation price:

- sends an immediate Telegram execution error;
- blocks all new entries;
- never silently rewrites the structural stop or risk amount;
- requires explicit operator handling for the already-open position.

## Known approximation

OKX liquidates on mark price while the strategy's OHLCV and attached stop use
last price. Funding, manual margin adjustments, schedule changes after
`okx_sol_usdt_swap_2026_06_29`, and exchange rounding can move `liqPx`. The
configured buffer is therefore mandatory.
