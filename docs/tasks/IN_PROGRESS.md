# In progress

## Next owner-run task — Run strategy discovery MVP

**Owner direction still applies:** backtests, optimizer runs, `compare-fixed`,
`compare-grid`, and `signal-quality` are owner-run by default. The
`discover-strategies` command is also intended as the next owner-run long job:
agents should inspect returned artifacts before asking for more manual
trigger/filter backtests.

**Current artifacts:**

- Contiguous first pass: `results/discovery_sol_h1/20260608_111656/`.
- Monthly stability pass: `results/discovery_sol_h1_monthly/20260608_112021/`.
- Monthly stability pass with robustness exports:
  `results/discovery_sol_h1_monthly/20260608_112946/`.
- Full SOL 2025 monthly discovery:
  `results/discovery_sol_h1_2025_monthly/20260608_113331/`.

**Review verdict:** do not convert the top score candidate. The score ranking
still prefers dense candle-confirm variants even when they have no edge:
monthly top score `h1_candle_confirm` had `2157` events, `1041` wins, `1049`
losses, `67` neutral, `49.81%` win rate.

The narrower high-win candidates are not stable enough yet:

- `h1_order_block_retest__atr_distance_1_2`: aggregate `55` events,
  `36/19/0`, `65.45%`, but February failed (`6/8`, `42.86%`).
- `h1_order_block_retest__atr_distance_1_2__trend_strength_min`: aggregate
  `47` events, `32/15/0`, `68.09%`, but it is rejected by the current
  `min_trades_total=50` gate and February failed (`6/7`, `46.15%`).
- `h1_range_breakout__atr_distance_0_1__h4_context_aligned`: aggregate `138`
  events, `80/58/0`, `57.97%`, but March failed (`19/25`, `43.18%`).
- `h1_range_breakout__atr_distance_0_1__h4_context_aligned__side_short_only__trend_strength_min`:
  aggregate `77` events, `46/31/0`, `59.74%`, but March failed (`11/14`,
  `44.00%`).
- The most stable checked profile was
  `h1_candle_confirm__h4_context_aligned__side_short_only__trend_strength_min__volatility_normal_only`:
  `286` events, `154/130/2`, `54.23%`, with all three months positive
  (`56.06%`, `53.47%`, `53.85%`). This is only a mild label edge, not enough
  to treat as an execution candidate yet.
- The robustness-export pass also surfaced
  `h1_structure_break__side_short_only`: `136` events, `73/60/3`, `54.89%`,
  with monthly win rates `57.50%`, `54.72%`, `52.50%`. This is cleaner than
  candle-confirm but still only a mild edge over three months.

**Full-year verdict:** no candidate passed the strict robust export
(`robust_min_window_win_rate_50.csv` is empty), so there is no clean
all-12-month label edge. The best practical shortlist family is:

```text
h1_momentum_burst__avoid_low_volume__block_context_reversal__side_short_only__trend_strength_min
```

It produced `325` labeled events, `180/143/2`, `55.73%` aggregate win rate,
all 12 months above `min_trades_per_window=10`, and 11 of 12 months at or
above `50%` win rate. The only weak month was July: `11/15/1`, `42.31%`.

Monthly label profile:

| Month | Events | W/L/N | Win rate |
| --- | ---: | --- | ---: |
| Jan | 25 | 13/12/0 | 52.00% |
| Feb | 39 | 22/17/0 | 56.41% |
| Mar | 25 | 13/12/0 | 52.00% |
| Apr | 22 | 11/11/0 | 50.00% |
| May | 24 | 14/10/0 | 58.33% |
| Jun | 29 | 18/11/0 | 62.07% |
| Jul | 27 | 11/15/1 | 42.31% |
| Aug | 20 | 15/5/0 | 75.00% |
| Sep | 28 | 17/11/0 | 60.71% |
| Oct | 28 | 14/14/0 | 50.00% |
| Nov | 32 | 18/13/1 | 58.06% |
| Dec | 26 | 14/12/0 | 53.85% |

The runner-up without `avoid_low_volume` is nearly identical:
`h1_momentum_burst__block_context_reversal__side_short_only__trend_strength_min`
with `327` events, `55.38%`, 11 of 12 months ≥50%, same July weakness.

**What:** implement the backlog conversion path for this selected discovery
candidate into a donor-executable diagnostic strategy config, or document
exactly why the current donor `crypt_ensemble` strategy cannot represent it.
Do not convert the score leaders or narrow sweep/order-block rows yet; they
failed monthly robustness despite high aggregate win rates.

**Why now:** manual H1 trigger/filter tinkering was burning owner/Codex tokens.
The strategy discovery constructor now exists, so the next useful step is a
single unattended discovery report instead of more one-off JSON branches.

**Expected gain:** test whether the only reasonably stable full-year label
edge survives donor execution mechanics: next-bar entry, structural stop
availability, RRR/TTL, overlap, margin, and fees.

**Acceptance:** add a checked-in strategy config or documented conversion
command for the selected candidate, plus focused tests. The next owner-run
handoff should be a `compare-fixed` command across SOL 2025 monthly windows,
not another discovery run.

Relevant context:

- Spec: `docs/strategy_discovery.md`.
- Implementation: `src/backtester/strategy_discovery/`.
- Tests: `tests/backtester/test_strategy_discovery.py`.
- Previous manual H1 raw-trigger branch is superseded by this discovery job
  unless the owner explicitly asks to resume one-off `compare-fixed` runs.
