# Investment mandate

Owner-defined economic and risk targets for **auto-trading** candidates.
Agents must read this file at every session start (see `AGENTS.md`).

This document is the **north star** for candidate search, backtest
interpretation, Optuna scope, and promotion decisions. Engineering tasks in
`BACKLOG.md` exist to support these gates — not to replace them.

**Status:** accepted 2026-06-05 (owner direction in chat; ADR-0025).

---

## 1. Product goal

1. Find a **strategy candidate** that passes the gates below on a **full-year
   continuous backtest** (after fees and slippage).
2. Only then implement **auto-execution** (M4 / `ExecutionSink`).
3. Do **not** build live order routing while searching for a candidate.

Universe order:

1. **SOL-USDT-SWAP** — search first on calendar **2025**.
2. **TON-USDT-SWAP** — search only **after** a SOL candidate is promoted or
   explicitly archived with a written handoff.

Each symbol uses a **separate $10 000 portfolio** (not one shared pool).

---

## 2. Economic floor (hard minimum)

| Parameter | Value |
| --------- | ----- |
| Starting capital | $10 000 per symbol |
| Minimum monthly return | **+15%** (`raw_monthly_return_pct ≥ 15`) |
| Minimum monthly profit | **$1 500** (equivalent at $10k) |
| Evaluation period | Full calendar **2025**, continuous backtest |
| Costs | **After** backtester fee and slippage model |

A calendar month **passes** when `raw_monthly_return_pct ≥ 15`.

Up to **3 of 12** months may fail the 15% floor without automatic rejection.
More than 3 failing months → **discard** (unless owner overrides in chat).

There is **no separate annual return floor** beyond the monthly rules above.

---

## 3. Risk limits

### 3.1 Monthly drawdown

- Measure **max drawdown inside each calendar month** on the equity curve.
- If any month has **max DD > 10%** → **archive immediately** (no deep dive).
- Months with DD ≤ 10% may still be investigated when other flags fire.

### 3.2 Consecutive losing months

| Count | Action |
| ----- | ------ |
| **3** consecutive months with `raw_monthly_return_pct < 0` | **Discard** |
| **2** consecutive losing months | Eligible for **full Optuna** (see §6) if not otherwise discarded |

### 3.3 Large losing days

- Up to **10** days in 12 months where intraday equity drops sharply are
  acceptable without automatic rejection.
- More than **10** such days → **candidate under review** (investigate news /
  regime); not auto-promoted until resolved.

Negative outliers are **not** clipped for evaluation. Positive outliers are
capped (§4).

---

## 4. Positive outlier cap (approved from `IDEAS.md`)

Do not let one exceptional month pretend to carry weak months.

For each calendar month:

```text
capped_monthly_return_pct = min(raw_monthly_return_pct, 20%)
```

Rules:

- **Pass/fail** still uses **raw** `≥ 15%` (not capped).
- **Ranking and yearly summaries** use **capped** monthly returns (average or
  sum of capped values) so a +100% month does not rescue eleven weak months.
- Always export **both** `raw_monthly_return_pct` and
  `capped_monthly_return_pct` plus `excess_return_pct =
  max(raw - 20%, 0)`.

---

## 5. Candidate outcomes

### 5.1 Promote

Passes **all** of:

- Continuous **2025** backtest on the symbol;
- At least **9 of 12** months with `raw ≥ 15%`;
- No month with max DD **> 10%**;
- No **3** consecutive losing months;
- Large losing-day count **≤ 10** (or reviewed and accepted by owner);
- Margin simulator allows **both** high and low peak margin paths (§7) — no
  one-sided geometry artifact.

→ Candidate is eligible for **auto-trading implementation** after owner sign-off.

### 5.2 Archive

Too good to delete, not good enough for production. Example profile:

- Average **capped** monthly return roughly **+8% to +14%**;
- No **3** consecutive losing months;
- Every month max DD **≤ 10%**.

Archived candidates are stored with full artifacts and a short written verdict.
They are **not** promoted and **not** auto-traded unless the owner revives them.

### 5.3 Discard

- More than **3** months below the 15% floor;
- **3** consecutive losing months;
- Any month with max DD **> 10%**;
- Severe sustained losses with no Optuna rescue path.

### 5.4 Full Optuna (second chance)

When a candidate **does not promote** but is **not discarded**:

- No **3** consecutive losing months;
- Not disqualified by monthly DD > 10%.

Run **full Optuna**:

- `--strategy-param-search`
- daily-limit search
- trading-window search
- execution parameters (`rrr`, `ttl`, `risk_percent`, `max_positions`, …)
- trailing-stop parameters (§6.1)

Borderline candidates that only **weakly** lose may enter this path. Candidates
that **strongly** lose in a row are discarded without full Optuna.

---

## 6. Search features (implementation backlog)

These are **approved** for candidate search; specs and code follow in
`BACKLOG.md`.

### 6.1 Trailing stop (optional, Optuna)

Keep fixed SL + fixed TP by default. When trailing is enabled:

1. Until price reaches `trail_activation_rrr × sl_distance` in profit, use
   normal fixed SL and fixed TP (`rrr`).
2. After activation, disable fixed TP; exit on trailing stop:
   - **Short:** `lowest_favorable_price + trail_distance_atr × ATR`
   - **Long:** `highest_favorable_price - trail_distance_atr × ATR`
3. SL before activation does not move.

Optuna dimensions (initial ranges, adjust in spec):

| Parameter | `0` meaning | Example search values |
| --------- | ----------- | --------------------- |
| `trail_activation_rrr` | trailing disabled (fixed TP only) | `0, 0.5, 0.75, 1.0, 1.25` |
| `trail_distance_atr` | ignored when activation is 0 | `0.5, 1.0, 1.5, 2.0` |

Report exit mix: `trailing_stop` vs `take_profit` vs `stop_loss` vs
`ttl_expired`.

### 6.2 Stop-loss count limits (canceled)

Owner direction on 2026-06-06 canceled the stop-loss count limit task for the
current candidate search. Do not implement or optimize these parameters unless
the owner explicitly revives the idea.

| Parameter | `0` meaning | Role |
| --------- | ----------- | ---- |
| `max_stop_losses_per_day` | no daily cap | stop trading for rest of day |
| `max_stop_losses_per_month` | no monthly cap | stop trading for rest of month |
| `max_consecutive_stop_losses` | no streak cap | pause until next day or month (document in spec) |

---

## 7. Margin and leverage

- High **peak locked margin** does **not** auto-disqualify a candidate if all
  economic gates pass.
- The simulator must allow **low** peak margin as well as high usage. ADR-0026
  fixed the old minimum-leverage geometry that pinned tight-stop profiles near
  ~100% even when `risk_percent` was reduced; re-run bounded grids after that
  change before promotion decisions.
- Isolated futures assumption; liquidation-aware leverage remains ADR-0024
  follow-up when stops and liquidation disagree.

---

## 8. Reporting requirements

Any candidate evaluation report for mandate compliance must include:

- Per-month: `raw_monthly_return_pct`, `capped_monthly_return_pct`,
  `max_drawdown_pct` (intra-month), trade count, stop-loss count.
- Year summary: count of months ≥ 15%, count below floor, worst consecutive
  losing streak, large losing-day count.
- Verdict: **promote** / **archive** / **discard** / **full Optuna** with one
  paragraph rationale.
- Reference strategy params, symbol, window `2025-01-01` → `2026-01-01`, and
  artifact paths.

---

## 9. Current baseline vs mandate

The best bounded H1 short-only row (`rrr = 1.5`, `ttl = 42`, `max_positions =
1`) summed **+10.12%** across seven **independent** one-month windows — far
below the **+15%/month** floor. It is **not** a promote candidate under this
mandate.

---

## References

- ADR-0025 — mandate acceptance
- ADR-0024 — margin realism
- `docs/tasks/BACKLOG.md` — implementation tasks
- `docs/paper_trading.md` — M3 validation after promotion
- `docs/tasks/IDEAS.md` — capped profits origin (now approved here)
