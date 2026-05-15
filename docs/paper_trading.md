# Paper trading (M3)

This document is the **contract** for the M3 milestone: running a paper
ledger in parallel with live alerts, producing a confidence-calibration
curve, and deciding whether the system is good enough to consider M4
(auto-execution).

Read this end-to-end before implementing. Cross-reference
`docs/backtest.md` (M2) — the same fill/slippage primitives are reused
between backtest and paper trading; the difference is replay vs live.

---

## 1. Goal

For every BUY/SELL verdict that fires during the M3 window:

1. Simulate **what would have happened** if the owner had taken the
   trade at the next H4 open.
2. Track entry, SL, TP, exit, and net P&L per trade.
3. Aggregate over ≥ 60 days to produce:
   - Hit rate by regime, by symbol, by engine-vote-pattern.
   - Expectancy with bootstrap CI.
   - Maximum drawdown and recovery time.
   - **Calibration curve**: bucket verdicts by reported confidence
     (60–69, 70–79, 80–89, 90–100) and measure the realised hit rate.
     A well-calibrated system has each bucket's realised hit rate near
     its bucket midpoint.

The owner uses the calibration curve to decide go/no-go on M4.

---

## 2. Non-goals

- Real order routing. That is M4 (`ExecutionSink`).
- Multi-leg structures (perp + spot hedge). Out of scope.
- Position sizing logic. Paper ledger sizes every trade at a unit (1.0
  notional); P&L is reported as a percentage. The sizing model belongs
  to M4 risk management.

---

## 3. Surface

A new sink `crypt/sinks/paper_ledger.py`:

```python
class PaperLedgerSink(BaseSink):
    """
    Records every alerted verdict as a simulated trade in a JSONL ledger.

    Runs in parallel with TelegramSink. The owner's actual manual trades
    are recorded separately (see §10) so we can compare paper vs human.
    """

    def __init__(self, ledger_path: Path, settings: PaperLedgerSettings) -> None: ...
    async def emit(self, verdict: Verdict, should_alert: bool) -> None: ...
    async def close(self) -> None: ...
```

Triggered for the same conditions as TelegramSink (i.e. when
`should_alert == True` AND `decision != HOLD`).

A **separate** lifecycle task in the orchestrator polls open trades:
once per H4 close, for each open trade in the ledger, check whether SL,
TP, or timeout has fired.

---

## 4. Ledger schema (`data/paper_ledger.jsonl`)

Append-only JSONL. Each line is one **state** of a trade. A trade
appears multiple times: once on open, then once on close.

```json
{"event": "open",  "trade_id": "uuid",  "verdict_id": "uuid",
 "symbol": "SOL-USDT-SWAP", "direction": "long", "alert_ts": "...Z",
 "entry_ts": "...Z", "entry_price": 145.30,
 "sl_price": 137.50,  "tp_price": 161.00,
 "atr_h4_at_alert": 3.80, "regime_at_alert": "TRENDING",
 "confidence_at_alert": 78,  "score_at_alert": 0.412,
 "uncalibrated": true}

{"event": "close", "trade_id": "uuid", "exit_ts": "...Z",
 "exit_price": 161.00, "exit_reason": "tp",
 "gross_return_pct": 0.108, "round_trip_cost_pct": 0.002,
 "net_return_pct": 0.106, "hold_hours": 32}
```

`event` values: `"open" | "close" | "update"`. `"update"` is reserved
for partial exits if we ever add them.

`exit_reason ∈ {"tp", "sl", "timeout", "manual_close"}`. `"manual_close"`
exists for future operator commands; not used initially.

A small helper `crypt/paper/ledger.py` provides `open_trade(verdict) ->
TradeOpen` and `close_trade(trade_id, ...) -> TradeClose` plus iterators
over open / closed trades.

---

## 5. Entry logic

When a verdict fires (`emit()` is called with `should_alert == True`):

1. Compute SL/TP:
   - `atr_h4 = atr14_h4`, fetched from the same closed-candle dataframe
     the engines used.
   - `sl_distance = SL_ATR_MULT * atr_h4`. Default `SL_ATR_MULT = 2.0`.
   - `tp_distance = TP_ATR_MULT * atr_h4`. Default `TP_ATR_MULT = 3.0`.
   - For `BUY`: `sl = entry - sl_distance`, `tp = entry + tp_distance`.
   - For `SELL`: `sl = entry + sl_distance`, `tp = entry - tp_distance`.
2. Plan the entry **at the next H4 open**. The exact price is the open
   of the H4 candle that starts after the alert.
   - Justification: aligns paper trades with what a discretionary human
     can realistically execute when reading a Telegram alert.
3. Persist a pending entry in `data/paper_pending.json` (small JSON,
   re-read on restart).
4. On the next tick (which always coincides with a fresh H4 open in our
   architecture), the orchestrator's paper-trade loop reads the open
   price and writes the `open` event to the ledger.

If the alert was for `BUY` but the H4 open is **above** `sl_price`, the
trade still opens (this is the realistic case).

If the alert was for `SELL` but the H4 open is **below** `tp_price`
(i.e. the move already exhausted), open the trade anyway and let it
likely close immediately — the spec must reflect what the operator
would see.

---

## 6. Exit logic

Run on every tick (which is every H4 close). For each open trade:

1. Look at the H4 candle that just closed.
2. **SL check**: did `low` (BUY) or `high` (SELL) cross `sl_price`?
   - If yes: exit at `sl_price` with `exit_reason="sl"`. Pessimistic
     fill assumption — assume the SL fills at the SL price exactly, not
     better. Adds a small bias against the system.
3. **TP check**: did `high` (BUY) or `low` (SELL) cross `tp_price`?
   - If yes and SL did not fire in the same bar: exit at `tp_price`
     with `exit_reason="tp"`.
   - If both fired in the same bar: this is an ambiguous fill. Our
     default: **assume SL fires first** (worst case for the system).
     Configurable via `PaperLedgerSettings.same_bar_resolution`.
4. **Timeout**: if neither SL nor TP fires within `TIMEOUT_HOURS`
   (default `7 * 24 = 168 hours`), close at the next H4 open with
   `exit_reason="timeout"`.
5. Compute `gross_return_pct = (exit_price / entry_price - 1) * direction`.
   `round_trip_cost_pct` = same constants as backtest (`0.20%`).
   `net_return_pct = gross_return_pct - round_trip_cost_pct`.

---

## 7. Settings

`PaperLedgerSettings` (loaded from env via pydantic):

```python
class PaperLedgerSettings(BaseModel):
    enabled: bool = True
    sl_atr_mult: float = 2.0
    tp_atr_mult: float = 3.0
    timeout_hours: int = 168
    same_bar_resolution: Literal["sl_first", "tp_first", "split"] = "sl_first"
    round_trip_cost_pct: float = 0.002  # 0.20%
    ledger_path: Path = Path("data/paper_ledger.jsonl")
    pending_path: Path = Path("data/paper_pending.json")
```

Defaults match `docs/backtest.md` so paper and backtest are directly
comparable.

---

## 8. Calibration curve

Reported in the M3 final report. Procedure:

1. Iterate closed trades in the ledger.
2. Bucket by `confidence_at_alert`:
   - `[60, 70)`, `[70, 80)`, `[80, 90)`, `[90, 100]`.
3. For each bucket, compute realised hit rate
   (`net_return_pct > 0`) and mean `net_return_pct`.
4. Plot the realised hit rate vs the bucket midpoint:
   - Ideal: linear, on the diagonal.
   - Over-confident: realised below diagonal (system "knows less than
     it claims").
   - Under-confident: realised above diagonal (system "is humble").
5. Compute Brier score: `mean((p_predicted - hit)**2)`.

The owner reads this plot together with `expectancy_by_regime` and
`drawdown` to decide on M4.

---

## 9. P&L attribution

Per closed trade, compute each engine's **contribution** to the verdict
that triggered the trade:

```text
contribution_i = sign(strength_i) * weight[regime, engine_i] * |strength_i|
```

Aggregate over the ledger:

- `pnl_by_engine[engine_i] = sum over trades of pnl_per_trade *
  (contribution_i / sum_j contribution_j)`

This is a linear allocation; not perfect (signals interact), but
honest. M3 report shows `pnl_by_engine` and `pnl_by_regime` tables.

---

## 10. Operator's actual trades (optional but recommended)

We provide a Telegram command (`/trade SOL long 145.30`, see
`docs/operations/telegram_commands.md`) for the owner to record what
they actually traded. This produces a **second ledger**
`data/owner_ledger.jsonl` with the same schema.

The M3 report compares paper vs owner:
- Slippage delta (owner fill price vs paper fill price).
- Owner skipped alerts (which ones, why — operator notes).
- Owner-added trades (off-system intuition).

This is informative for M4 design: if the owner consistently overrides
toward "skip", we learn what to filter out.

---

## 11. Failure modes

- Process restart mid-trade: pending trades are persisted in
  `data/paper_pending.json` and re-read on startup. Open trades live in
  the JSONL ledger and the orchestrator reconstructs the open set by
  scanning the ledger backward.
- Symbol delisted mid-trade: close at the last available H4 close,
  `exit_reason="manual_close"`, log WARNING.
- Missing H4 candle for one tick (data ingestion gap): postpone exit
  checks for that symbol; do not assume the prior bar's high/low were
  the cross. Log WARNING.
- Two alerts back-to-back in the same direction within cooldown
  window: the second alert is suppressed by the decision filter
  (existing behaviour); no second paper trade opens. This is the
  *correct* behaviour for paper trading too.
- Direction-flip alert (BUY then SELL in < 4h, which breaks cooldown):
  open the SELL but **also close the BUY** at the SELL's entry price
  (with `exit_reason="manual_close"`). Same logic mirrored. We do NOT
  net positions (no spread / hedge).

---

## 12. Tests

`tests/paper/`:

- `test_open_and_close.py` — synthetic verdict + synthetic next H4
  candle that crosses TP → ledger has one `open` + one `close` event
  with `exit_reason="tp"`, `net_return_pct > 0`.
- `test_sl_first_same_bar.py` — H4 bar low and high both cross SL/TP
  → exit at SL (default resolution).
- `test_timeout.py` — neither SL nor TP fires; after 168h exit at
  next H4 open.
- `test_restart_recovery.py` — restart process mid-trade; open set is
  reconstructed.
- `test_direction_flip.py` — open BUY, then SELL alert within
  cooldown-breaking interval → BUY closes, SELL opens.
- `test_calibration_curve.py` — generate 1000 synthetic closed trades
  with known per-bucket hit rates; assert the report bucketing matches
  ground truth.

---

## 13. Reporting

A separate CLI:

```bash
uv run python -m crypt.paper.report \
    --from 2026-06-01 \
    --to   2026-08-01 \
    --out reports/paper_2026-08/
```

Produces:
- `summary.html` — single-page report.
- `trades.parquet` — all closed trades.
- `figures/calibration.png`, `figures/equity_curve.png`,
  `figures/by_regime.png`.

`summary.html` content:
1. Top-line: total return, expectancy per trade, max drawdown.
2. By regime, by symbol breakdown with bootstrap CI.
3. Calibration curve (the one chart the owner cares about).
4. P&L attribution by engine.
5. Owner vs paper diff (if `owner_ledger.jsonl` is non-empty).
6. Critique paragraph.

---

## 14. Implementation order

1. Write `crypt/paper/ledger.py` (data structures + persistence).
2. Write `PaperLedgerSink` (entry logic).
3. Write the exit-check task in the orchestrator (or as a separate
   coroutine in `__main__.py`).
4. Write `crypt/paper/report.py` (CLI).
5. Write tests as above.
6. Add the `/trade ...` Telegram commands (separate spec).
7. Run for ≥ 60 days. M3 exit criteria says "owner decides".

---

## 15. Known weaknesses

- **Pessimistic SL** (assumes SL fills at SL price exactly) — small
  systematic bias against the system. We accept this. Real SL fills can
  be slightly worse (gap through SL) or better (improved fill); the
  asymmetry favours assuming the worse case.
- **Same-bar SL/TP resolution** is opaque. The default `sl_first`
  resolution is unfavourable for the system; M2/M3 ablation should
  re-run with `tp_first` and `split` to see how much it costs.
- **No partial exits / trailing stop**. Realistic discretionary trading
  often uses trailing stops; we explicitly do not — paper ledger is a
  measurement instrument, not a trading strategy. M4 may add a
  trailing-stop variant.
- **Confidence buckets** at 10-point width with the existing 75
  threshold give us only 3–4 buckets. As the system matures, narrow
  buckets to 5 points.
- **Calibration is sensitive to regime drift**: a system calibrated in
  a trending market will be over-confident in a ranging market. M3 must
  show calibration **per regime**, not just globally.
