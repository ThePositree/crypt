# In progress

## Status as of 2026-06-01 (session 12)

**Active work:** M2 OHLCV-only backtest report reviewed. The simulator bug from
session 11 is no longer the blocker; the optimizer sanity guard is a genuine
model/calibration failure on the first two out-of-sample folds.

Completed:

- Reviewed `reports/backtest_2026-06/` after the owner reran the full
  SOL/TON backtest.
- Wrote ADR-0014 rejecting promotion of the generated weights.
- Fixed `weights_to_yaml()` so future `weights.candidate.yaml` files are safe
  YAML without Python/numpy object tags.
- Rewrote the current `reports/backtest_2026-06/weights.candidate.yaml` with
  the safe serializer; weights are unchanged.
- Added regression coverage for numpy scalar YAML serialization.

### Next steps

Do not copy `reports/backtest_2026-06/weights.recommended.yaml` to
`config/weights.yaml`, and do not flip `uncalibrated = False`.

Recommended next implementation items:

1. Fix report artifact semantics: if any fold fires the sanity guard, do not
   present `weights.recommended.yaml` as promotable, and make
   `weights.candidate.yaml` contain an explicit aggregate candidate rather than
   the last fold's weights.
2. Investigate weak long signals before another calibration attempt. The
   reviewed report showed negative `h24` proxy expectancy on `SOL` BUY and
   `TON` BUY alerts.
3. Decide the next M2 modeling slice: either add cheap BTC/cross-symbol context
   or introduce a stricter long-side filter, then rerun the same walk-forward
   backtest.

---

## Status as of 2026-06-01 (session 11)

**Active work:** M2 backtest run exposed a multi-symbol execution simulator
bug. The simulator used the next global DataFrame row for next-open entries
and TTL exits, so same-timestamp SOL/TON rows could mix prices across
symbols. This produced impossible stop-loss validation messages such as
SOL entries paired with TON stop prices.

Fixed:

- `ExecutionSim.run()` now derives `next_open`, `next_time`, and bar number
  per symbol before simulating entries and TTL exits.
- Backtest sim frames now include `entry_price = close` so execution uses the
  closed signal candle explicitly.
- pandas `pct_change` and UTC datetime deprecation warnings are cleaned up.
- Regression coverage added in `tests/backtest/test_execution_sim.py`.

Verification:

- `uv run pytest -q` → 124 passed.
- `uv run ruff check src tests` → clean.
- `uv run mypy src` → clean.

### Next steps

Re-run the owner command and review the new report:

```bash
PYTHONPATH=src uv run python -m crypt.backtest \
    --from 2024-06-01 --to 2026-06-01 \
    --symbols SOL-USDT-SWAP,TON-USDT-SWAP \
    --walk-forward-folds 5 \
    --report-dir reports/backtest_2026-06/
```

If the optimizer guard still fires after this execution fix, treat that as a
model/calibration result rather than a simulator integrity bug and document it
in ADR-0014.

---

## Status as of 2026-06-01 (session 10)

**Active work:** SMC structure, order-block, and liquidity slices are
implemented and verified. Optimizer score recomputation is fixed. Next: run
OHLCV backfill/backtest.

Owner direction: do not pay for historical derivatives/order-flow data until
the product demonstrates value. Use free OKX candle history first. ADR-0017
captures this decision.

---

## Next steps for the implementing agent

### 1. SMC engines now implemented (P0)

Specs written:

- `docs/engines/smc_core.md`
- `docs/engines/smc_structure.md`
- `docs/engines/smc_order_blocks.md`
- `docs/engines/smc_liquidity.md`

Completed:

- `src/crypt/structure/smc.py` — first deterministic analyser slice:
  confirmed pivots + BOS/CHoCH with `known_at` timing; now also creates and
  mitigates order-block zones from structure breaks; now also emits equal
  high/low levels and liquidity sweeps.
- `src/crypt/engines/smc_structure.py` — first directional SMC engine.
- `src/crypt/engines/smc_order_blocks.py` — active order-block retest engine.
- `src/crypt/engines/smc_liquidity.py` — equal/swing high-low sweep engine.
- Tests proving no-lookahead timing for pivot confirmation, structure signals,
  order-block creation/mitigation/retest, equal-level detection, sweep timing,
  ambiguous double sweeps, and liquidity-engine output.

### 2. Wire OHLCV-only M2 calibration (P0)

- `smc_structure` and `smc_order_blocks` are already wired into live/replay
  aggregation.
- `smc_liquidity` is now wired into live/replay aggregation.
- `config/weights.yaml` already sets `derivatives: 0.0` for primary M2.
- `BacktestRecorder` now persists `strength_<engine>` columns, and
  `optimizer._apply_weights` recomputes candidate scores from those strengths
  before deriving decisions/objectives.

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
- Context7 MCP was requested by project rules. In sessions 9 and 10 pandas
  docs were resolved via Context7 before touching DataFrame-based SMC/backtest
  code; no new libraries were added.

---

## Reading list

- `AGENTS.md`
- `docs/decisions/0017-ohlcv-only-m2-smc.md`
- `docs/engines/smc_core.md`
- `docs/engines/smc_structure.md`
- `docs/backtest.md`
- `pinescript/smc.pine`
