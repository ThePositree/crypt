# Exact live-trade replay

## Purpose

After one live position closes and its OKX fills are persisted, replay the same
entry, exchange protection geometry, leverage, liquidation price, and H1 path
through the canonical exit resolver.

## Input

- one closed `LivePosition` from `data/live_positions.json`;
- closed H1 candles covering entry through exit;
- the configured intrabar policy.

The replay uses actual average entry, filled size, entry/exit fees, structural
SL, placed TP, native trailing activation/callback (when it was actually
placed), TTL, and aggregate liquidation price. A legacy position with trailing
parameters but no persisted native trailing geometry is replayed as the fixed
SL/TP order set that really existed on OKX.

## Output

The diagnostic reports actual and expected exit reason, trigger price,
actual fill price, price difference, actual realized PnL, reconstructed PnL,
and `matched`.

Do not add a dedicated CLI for this diagnostic. Invoke `replay_position`
ephemerally from `python -c`, loading the selected state position and H1
candles through existing project functions.

`matched=true` requires the exit reason to match. Trigger and fill prices are
reported separately because OKX market SL/trailing orders may slip after the
trigger; a limit TP should normally fill at its limit or better.
