# In progress

## Status as of 2026-06-01 (session 8)

**Active work:** SMC structure and order-block slices are implemented and
verified. Next: liquidity engine, then OHLCV backfill/backtest.

Owner direction: do not pay for historical derivatives/order-flow data until
the product demonstrates value. Use free OKX candle history first. ADR-0017
captures this decision.

---

## Next steps for the implementing agent

### 1. Implement next SMC engines (P0)

Specs written:

- `docs/engines/smc_core.md`
- `docs/engines/smc_structure.md`
- `docs/engines/smc_order_blocks.md`
- `docs/engines/smc_liquidity.md`

Completed:

- `src/crypt/structure/smc.py` — first deterministic analyser slice:
  confirmed pivots + BOS/CHoCH with `known_at` timing; now also creates and
  mitigates order-block zones from structure breaks.
- `src/crypt/engines/smc_structure.py` — first directional SMC engine.
- `src/crypt/engines/smc_order_blocks.py` — active order-block retest engine.
- Tests proving no-lookahead timing for pivot confirmation and structure
  signals, order-block creation/mitigation, and retest signals.

Next implementation order:

1. Extend `src/crypt/structure/smc.py` with equal highs/lows and sweeps.
2. Add `src/crypt/engines/smc_liquidity.py`.
3. Add synthetic no-lookahead tests for equal-level detection, sweep timing,
   and liquidity-engine output.
4. Before running the full backtest report, fix optimizer score recomputation
   from per-engine strengths (see `BACKLOG.md` P0).

### 2. Wire OHLCV-only M2 calibration (P0)

- `smc_structure` and `smc_order_blocks` are already wired into live/replay
  aggregation.
- `config/weights.yaml` already sets `derivatives: 0.0` for primary M2.
- Add `smc_liquidity` to `SCORING_ENGINES` only after its engine
  implementation and tests land.

### 3. Run candle backfill + backtest

Only OHLCV is required for the first M2 report:

```bash
for SYMBOL in SOL-USDT-SWAP TON-USDT-SWAP XPL-USDT-SWAP; do
    PYTHONPATH=src uv run python -m crypt.backfill \
        --symbol "$SYMBOL" \
        --from 2024-02-01 --to 2026-06-01 \
        --data-types ohlcv
done
```

Then:

```bash
PYTHONPATH=src uv run python -m crypt.backtest \
    --from 2024-06-01 --to 2026-06-01 \
    --symbols SOL-USDT-SWAP,TON-USDT-SWAP,XPL-USDT-SWAP \
    --walk-forward-folds 5 \
    --report-dir reports/backtest_2026-06/
```

### 4. After backtest report is reviewed

- Write **ADR-0014** — calibration result: final weights, expectancy CI,
  dataset window, and critique of weak/collapsed engines.
- Flip `Settings.uncalibrated = False` only if the report justifies it.
- Copy accepted `weights.recommended.yaml` → `config/weights.yaml`.

---

## Known limitations / caveats

- `pinescript/smc.pine` is a LuxAlgo CC BY-NC-SA reference. Do not copy code
  verbatim into proprietary Python modules. Implement the documented behaviour.
- PineScript MTF sections using `lookahead_on` must not be ported directly.
- `order_block`, `liquidity`, FVG, and Fibonacci can overfit easily; add one
  engine at a time and require synthetic no-lookahead tests.
- Context7 MCP was requested by project rules. In session 8 the Context7
  pandas lookup failed with `fetch failed`; no new libraries were added.

---

## Reading list

- `AGENTS.md`
- `docs/decisions/0017-ohlcv-only-m2-smc.md`
- `docs/engines/smc_core.md`
- `docs/engines/smc_structure.md`
- `docs/backtest.md`
- `pinescript/smc.pine`
