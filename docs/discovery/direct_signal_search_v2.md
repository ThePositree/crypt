# Direct Signal Search v2 — staged quality-diversity search

> **Status**: accepted implementation spec  
> **Introduced**: 2026-06-11  
> **Supersedes**: `docs/discovery/direct_signal_search.md` / ADR-0035  
> **ADR**: ADR-0036

---

## 1. Purpose

DSS v2 replaces the first `backtester search-signals` implementation.

The goal is not to sample trillions of combinations uniformly. The goal is to
spend expensive full backtests only on candidates that survived cheaper,
diverse, and mandate-aware filters.

The command must search for SOL strategy candidates that can later be validated
with `compare-fixed` and `walk-forward` under the owner mandate:

- 2025 continuous holdout is the final SOL promotion check.
- Monthly raw return floor is 15%.
- Monthly drawdown limit is 10%.
- Ranking uses capped monthly return.
- Candidates must be robust across regimes, not only excellent in one year.

---

## 2. Why v1 is retired

DSS v1 used Optuna NSGA-II directly over trigger choice, filter combinations,
trigger/filter parameters, and execution parameters. Each trial evaluated all
configured windows with full backtests.

The first long run showed the following:

```text
artifact: results/dss_sol_run_5k/study.journal
completed trials inspected: about 16.5k
best robust min score: -4626.74
trials with min_score > -500: 0
trials with min_score > 0: 0
best robust score stopped improving around trial 7064
top-50 collapsed mostly into pt_ema_cross + rrr=4.0 + wide ATR stop
```

That means v1 is doing expensive local exploitation of "least bad" candidates.
The defect is structural:

- no staged budgets;
- no forced coverage of trigger/filter families;
- no quality-diversity archive;
- no robust scalar ranking pressure;
- no constraints-first handling of mandate failures;
- no conditional surrogate suited to the search space.

Do not add flags to keep v1 alive. Rewrite `search-signals` to the v2 contract.

---

## 3. Owner-facing command contract

The command name remains:

```bash
uv run backtester search-signals \
  --data-dir data \
  --symbol SOL-USDT-SWAP \
  --windows 2022,2023,2024,2025H1 \
  --n-trials 50000 \
  --n-jobs 4 \
  --output results/dss_sol_v2
```

Important contract changes:

- `--sampler` should be removed from the owner-facing command.
- The command chooses the v2 staged search internally.
- `--n-trials` means total generated candidate budget across stages, not "full
  full-backtest trials".
- `--windows` means training/evaluation windows used by staged search.
- Candidate export remains compatible with downstream replay.

CLI options to keep:

| Option | Meaning |
| --- | --- |
| `--algorithm` | `staged` default, experimental `catcma_qd`, `island_qd`, `hyperband_qd`, or `smac_qd`. |
| `--seed` | Candidate generator seed; useful for non-duplicative parallel runs. |
| `--data-dir` | Project data directory. |
| `--symbol` | Single symbol for now. Multi-symbol search remains out of scope. |
| `--windows` | Comma-separated training windows. Default can stay `2022,2023,2024,2025H1`. |
| `--primary-timeframe` | `1h` default. |
| `--n-trials` | Total candidate-generation budget. |
| `--n-jobs` | Parallel workers where safe. |
| `--output` | Output directory. |
| `--top-n` | Number of exported replay candidates. |
| `--min-trades` | Viability floor per full window. |
| `--capital` | Initial capital. |
| `--risk-base-period` | Default `monthly`. |
| `--max-positions` | Default `1`. |

CLI options to remove:

| Option | Reason |
| --- | --- |
| `--sampler` | The old sampler switch exposes implementation experiments and keeps the bad path alive. |
| `--accept-min-score` | Reporting thresholds should be part of v2 policy and report all archive state, not hide failed searches. |
| `--max-filters` | Filter complexity belongs to the internal stage policy; exposing it encourages blind huge-space runs. |
| `--resume` | Replace with automatic resume from `output/study_state.jsonl` and stage artifacts when `--output` already exists. |

If a removed option is still passed, fail fast with a clear message telling the
operator the command was replaced by DSS v2.

---

## 4. High-level design

DSS v2 is a staged quality-diversity search:

```text
candidate generator
  -> Stage 0: stratified coverage
  -> Stage 1: signal viability
  -> Stage 2: cheap proxy backtests
  -> Stage 3: full multi-window mandate scoring
  -> Stage 4: holdout replay + export
  -> quality-diversity archive + reports
```

Each candidate has:

- a signal recipe: trigger, trigger params, filters, filter params;
- execution params: `rrr`, `risk_percent`, `position_ttl_bars`,
  `atr_sl_mult`;
- stage metrics;
- behavior descriptors;
- final replay config if exported.

The archive is not a Pareto front. It is a behavior map. Each cell keeps a
small elite list.

### 4.1 Experimental CatCMA-QD backend

ADR-0037 adds an opt-in `catcma_qd` backend for running a materially different
search from the default staged generator. It keeps the same Stage 1/2/3/4
evaluation contracts but changes candidate generation:

```text
population distribution over mixed variables
  -> sample candidate population
  -> DSS stage evaluation
  -> select proxy/full-score survivors
  -> update trigger/filter/parameter probabilities
  -> repeat until n_trials budget is spent
```

The implementation is a lightweight CatCMA-inspired adaptation, not a full
paper reproduction. It is acceptable because the goal is exploratory search
diversity, while final promotion remains governed by `compare-fixed`,
`walk-forward`, and ADR-0025.

To keep long owner runs bounded, CatCMA-QD evaluates Stage 1 for every generated
candidate but sends only the top cheap-scored, behavior-diverse slice of each
population batch into Stage 2 proxy backtests. This preserves adaptive feedback
without making every viable signal recipe pay the expensive backtest cost.

### 4.2 Experimental Island-QD backend

ADR-0038 adds `--algorithm island_qd` for Railway-scale exploratory runs. It is
designed for the failure mode observed in CatCMA-QD where all-window robustness
was dominated by `2022` and no candidate reached Stage 3.

Island-QD rotates population batches across configured windows:

```text
island 2022    -> Stage 2 scores only 2022
island 2023    -> Stage 2 scores only 2023
island 2024    -> Stage 2 scores only 2024
island 2025H1  -> Stage 2 scores only 2025H1
periodic robust check -> Stage 3 scores all windows
```

The output adds `island_scores.csv` and per-window
`island_qd_state_<window>.csv` files. Exported candidates still require
`compare-fixed` validation before any mandate decision.

### 4.3 Experimental Hyperband-QD backend

ADR-0039 adds `--algorithm hyperband_qd` for budgeted quality-diversity search.
It is the next distinct backend after staged, CatCMA-QD, and Island-QD:

```text
large candidate population
  -> Stage 1 viability for all candidates
  -> Rung 1 one-window proxy score for a behavior-diverse top fraction
  -> Rung 2 multi-window proxy score for a smaller fraction
  -> Rung 3 all-window Stage 3 score for the final fraction
```

The output adds `hyperband_rungs.csv` and `hyperband_qd_state.csv` while keeping
normal DSS `stage1_viability.csv`, `stage2_proxy.csv`, `stage3_full_scores.csv`,
archive, manifest, and candidate JSON artifacts. Exported candidates still
require `compare-fixed` validation.

### 4.4 Experimental SMAC-QD backend

ADR-0040 adds `--algorithm smac_qd`, a SMAC-style conditional surrogate backend
using `sklearn.ensemble.RandomForestRegressor`.

The backend keeps a fixed conditional encoding of each candidate:

- one-hot trigger choice;
- one-hot filter presence;
- filter depth;
- execution parameters (`rrr`, `risk_percent`, `position_ttl_bars`,
  `atr_sl_mult`);
- trigger/filter parameter features, with inactive conditional parameters
  encoded as `-1`.

It runs random-design bootstrap evaluations first, then repeatedly:

```text
sample large proposal pool
  -> encode candidates
  -> RF predicts robust score mean
  -> tree prediction dispersion estimates uncertainty
  -> acquisition = mean + uncertainty weight * std
  -> evaluate selected infill candidates through DSS Stage 1/2/3
  -> refit RF on observed stage scores
```

The output adds `smac_qd_proposals.csv`, `smac_qd_observations.csv`, and
`smac_qd_state.csv` while preserving normal DSS archive, manifest, and
candidate JSON artifacts. Exported candidates still require `compare-fixed`
validation.

---

## 5. Candidate representation

Keep `TrialConfig` or replace it with an equivalent immutable dataclass.

Required fields:

```python
@dataclass(frozen=True, slots=True)
class DSSCandidate:
    candidate_id: str
    trigger_name: str
    trigger_params: dict[str, float | int | str]
    filter_names: tuple[str, ...]
    filter_params: dict[str, dict[str, float | int | str]]
    rrr: float
    risk_percent: float
    position_ttl_bars: int
    atr_sl_mult: float
    generation: int
    parent_ids: tuple[str, ...] = ()
```

Required derived keys:

- `signal_cache_key`: trigger + trigger params + filters + filter params +
  `atr_sl_mult`
- `execution_key`: `rrr`, `risk_percent`, `position_ttl_bars`, max positions,
  risk base period, costs
- `candidate_key`: signal cache key + execution key

No naked dict should cross module boundaries. JSON serialization is fine at
artifact boundaries.

---

## 6. Behavior descriptors

Every candidate reaching Stage 2 must get behavior descriptors. These drive the
quality-diversity archive.

Descriptors:

| Descriptor | Values | Why |
| --- | --- | --- |
| `trigger_family` | trigger name or coarse family | Prevents EMA-cross monopoly. |
| `side_profile` | `long_only`, `short_only`, `mixed_long_bias`, `mixed_short_bias`, `balanced` | Side specialization can be real edge. |
| `trade_count_bucket` | `low`, `medium`, `high`, `too_high` | Separates sparse high-conviction from noisy frequent signals. |
| `hold_time_bucket` | `short`, `medium`, `long` from TTL and realized exits | Prevents all elites becoming same holding horizon. |
| `risk_geometry` | `tight_sl`, `medium_sl`, `wide_sl` from ATR stop | Wide-stop profiles dominated v1. |
| `regime_strength` | best training window label or `balanced` | Makes regime specialists visible without letting them masquerade as robust. |
| `filter_depth` | `0`, `1`, `2`, `3plus` | Captures complexity pressure. |

Archive cell key:

```text
(trigger_family, side_profile, trade_count_bucket, risk_geometry, filter_depth)
```

Each cell keeps at most `K=3` elites:

1. best robust fitness;
2. best average fitness;
3. best low-drawdown fitness.

If a cell is full, replace the weakest elite only if the new candidate improves
one of those roles.

---

## 7. Fitness and constraints

Stage 3 ranking uses a robust scalar fitness, not raw multi-objective Pareto
rank.

Required per-window score:

```text
mandate_score = same formula as ADR-0031
```

Required robust aggregate:

```text
robust_score =
    min(window_scores)
    + 0.25 * median(window_scores)
    - 0.10 * stdev(window_scores)
    + archive_novelty_bonus
    - complexity_penalty
```

Novelty bonus:

- small, bounded, and only used for tie-breaking or near ties;
- suggested range: `0` to `50`;
- do not let novelty hide economic failure.

Complexity penalty:

```text
complexity_penalty =
    5 * number_of_filters
    + 10 * duplicate_filter_penalty
```

Hard feasibility constraints:

| Constraint | Stage | Handling |
| --- | --- | --- |
| no signals | Stage 1 | reject |
| too few signals in any required window | Stage 1/3 | reject or mark infeasible |
| more than 10 signals per day | Stage 1 | reject noisy overtrading |
| any full-window score is `_EMPTY_SIGNAL_PENALTY` | Stage 3 | infeasible |
| unreplayable candidate JSON | Stage 4 | reject export |

Soft feasibility constraints:

| Constraint | Handling |
| --- | --- |
| more than 3 months below floor | strong penalty in mandate score |
| DD breach months | strong penalty in mandate score and report |
| 3 consecutive losing months | strong penalty and report |
| extreme one-window specialization | stdev penalty + archive descriptor |

The report must show constraints separately from score. Do not hide why a
candidate failed.

### 7.1 Regime-specialist follow-up

The 2026-06-16 WR55/10pd tail analysis showed that a hard all-window Stage 1
gate can discard useful evidence before Stage 2:

- the completed 2022-first run found 31,241 candidates that passed 2022, but
  none passed 2023;
- the 2023-first snapshots found 38 candidates that passed 2023, but all were
  rejected by `too_few_signals:2022`;
- the 2022-pass tail was mostly short/trend/context behavior, while the
  2023-pass tail was sparse mean-reversion, compression, BB/RSI, and
  session-volume behavior.

Future DSS work must distinguish two candidate classes:

| Class | Stage 1 requirement | Archive/report handling |
| --- | --- | --- |
| `balanced` | passes signal count, overtrading, and barrier gates on all required windows | eligible for normal robust Stage 2/3 scoring and export |
| `specialist:<window>` | passes strict gates on an explicitly requested specialist window; non-target windows may be diagnostic only | stored in specialist artifacts; not eligible for direct promotion |

Specialist candidates are research artifacts until a routing or composition
layer exists. They may be scored on one or more adverse windows for diagnostics,
but reports must never label them all-window robust.

Keep specialist capture opt-in. The normal all-window Stage 1 path must retain
early rejection on the first failed window so owner-scale DSS runs remain
practical. For first-pass specialist discovery, prefer a single target window
such as `--windows 2023`; run cross-window diagnostics afterward on a smaller
candidate set.

Reference analysis: `docs/discovery/dss_wr55_10pd_tail_analysis.md`.

---

## 8. Stage 0 — stratified coverage

Purpose: ensure all trigger families and basic filter depths are explored before
the optimizer exploits local winners.

Inputs:

- selected trigger catalog (`legacy`, `pinescript_v1`, or `all`);
- selected filter catalog (`legacy`, `pinescript_v1`, or `all`);
- search-space bounds;
- `n_trials` budget.

Output:

- initial candidate stream.

Policy:

1. Allocate a minimum coverage quota per trigger family.
2. Within each trigger family, sample:
   - filter depth `0`;
   - filter depth `1`;
   - filter depth `2`;
   - filter depth `3+` if budget allows.
3. Sample execution geometry from a low-discrepancy or stratified grid:
   - `rrr`: include low/mid/high, not only high endpoint;
   - `atr_sl_mult`: include tight/mid/wide;
   - `ttl`: include short/mid/long;
   - `risk_percent`: keep broad, but do not let risk rescue bad signals.

Implementation note:

- This stage can be deterministic with a seeded RNG.
- It does not need Optuna.
- It should write `stage0_candidates.jsonl`.

Acceptance:

- A small run has at least one candidate per trigger family unless the budget is
  smaller than the number of families.
- The report shows coverage by trigger and filter depth.

---

## 9. Stage 1 — signal viability

Purpose: reject candidates that cannot produce a plausible signal stream before
running expensive backtests.

For each candidate and each configured window:

1. Build signals via `SignalComposer`.
2. Count raw signals.
3. Count side distribution.
4. Estimate ATR stop distance distribution.
5. Count duplicate or near-duplicate signal timestamps.
6. Compute cheap path-aware barrier metrics.

Reject if:

- any required training window has fewer than `min_trades`;
- total trades are too high for H1 swing/intraday system;
- side filters contradict generated sides;
- stop distances are invalid or mostly non-finite;
- too few signals reach the favorable barrier before the adverse barrier;
- signal generation raises.

Suggested overtrading guard:

```text
max_signals_per_day = 10
```

This is a search hygiene guard, not a mandate rule. It prevents candidate
families that fire too frequently from consuming backtest budget while still
allowing intraday strategies with up to 10 candidate entries per day.

Artifacts:

- `stage1_viability.csv`
- `stage1_rejections.csv`
- `stage1_specialists.csv`
- `stage1_specialists.jsonl`
- `stage1_survivors.jsonl`

Required columns:

- `candidate_id`
- `trigger_name`
- `filter_names`
- `candidate_class`
- `target_window`
- `signals_<window>`
- `long_ratio_<window>`
- `median_stop_atr_<window>`
- `barrier_tp_first_rate_<window>`
- `barrier_sl_first_rate_<window>`
- `barrier_timeout_rate_<window>`
- `barrier_win_rate_<window>`
- `barrier_median_mae_atr_<window>`
- `barrier_median_bars_to_tp_<window>`
- `rejection_reason`

### 9.1 Path-aware barrier label

The original directional discovery label asked whether price eventually moved
in the predicted direction by at least `N ATR`. That is useful as a cheap
directional edge screen, but it is not sufficient for strategy search because
price can move favorably only after first moving far enough against the entry to
hit a realistic stop.

Stage 1 therefore computes a cheap **path-aware barrier label** before any
donor backtest:

```text
LONG:
  TP barrier = entry + (atr_sl_mult * rrr * ATR)
  SL barrier = entry - (atr_sl_mult * ATR)

SHORT:
  TP barrier = entry - (atr_sl_mult * rrr * ATR)
  SL barrier = entry + (atr_sl_mult * ATR)

Look forward at most position_ttl_bars closed bars.
Outcome is tp_first, sl_first, or timeout.
If TP and SL are touched in the same bar, count SL first.
```

For each signal, also record:

- `MAE_ATR`: maximum adverse excursion before outcome, divided by entry ATR;
- `MFE_ATR`: maximum favorable excursion before outcome, divided by entry ATR;
- bars to TP when TP is reached first.

This label is not a final trading verdict. It is a cheap gate that prevents the
search from spending Stage 2/3 backtest budget on candidates whose "correct"
directional moves are usually not tradeable before adverse excursion.

Default policy:

```text
min_barrier_tp_first_rate = 0.05
min_barrier_win_rate = 0.55
tp_first must be greater than sl_first
```

`barrier_win_rate` is computed over resolved TP/SL outcomes only:
`tp_first / (tp_first + sl_first)`. Timeouts remain visible in
`barrier_timeout_rate` but do not count as wins. The TP-first rate floor rejects
empty/no-edge candidates, while the win-rate floor requires a directional
candidate to be better than a coin flip before it receives Stage 2 budget.

Acceptance:

- Synthetic tests cover empty signals, too few signals, overtrading, invalid
  stops, adverse-before-favorable barrier rejection, same-bar SL-first
  conservatism, and survivor pass-through.

---

## 10. Stage 2 — cheap proxy backtests

Purpose: spend a small backtest budget to estimate whether the candidate has any
economic promise before full multi-window mandate scoring.

Budget options:

- evaluate only one anchor year plus one adverse year;
- evaluate a downsampled subset of signals;
- evaluate first N months of each window;
- evaluate lower-cost monthly chunks.

MVP policy:

1. Run full backtest on two windows:
   - one recent favorable regime, default `2024`;
   - one older/adverse regime, default `2022` or first configured window.
2. Compute:
   - total return;
   - max drawdown;
   - trade count;
   - rough mandate score;
   - proxy robust score = min(two scores).
3. Promote only top candidates per archive cell.

Promotion rule:

```text
promote_to_stage3 if:
    candidate is top M in its archive cell
    or candidate is top global P by proxy_robust_score
```

Suggested defaults:

- `M = 2`
- `P = max(20, n_trials * 0.02)`

Artifacts:

- `stage2_proxy.csv`
- `stage2_archive.json`
- `stage2_survivors.jsonl`

Acceptance:

- Tests prove that a globally mediocre but cell-best candidate can survive.
- Tests prove that one trigger family cannot fill the whole survivor set.

---

## 11. Stage 3 — full multi-window mandate scoring

Purpose: run the expensive canonical objective only on candidates worth the
cost.

For each Stage 2 survivor:

1. Run all configured training windows.
2. Compute per-window mandate report.
3. Compute robust scalar fitness.
4. Update the quality-diversity archive.

This stage replaces the v1 NSGA-II full-trial loop.

Required outputs:

- `stage3_full_scores.csv`
- `archive.json`
- `archive.md`
- `score_history.csv`

Required `stage3_full_scores.csv` columns:

- `candidate_id`
- `trigger_name`
- `filter_names`
- `behavior_cell`
- `robust_score`
- `score_min`
- `score_median`
- `score_mean`
- `score_stdev`
- `score_<window>` for each window
- `trades_<window>` for each window
- `months_passing_floor_<window>` if available
- `dd_breach_months_<window>` if available
- `worst_monthly_drawdown_pct_<window>` if available
- `rrr`
- `risk_percent`
- `position_ttl_bars`
- `atr_sl_mult`

Acceptance:

- The report can explain a failed search by showing whether the blocker was
  no signals, overtrading, low returns, DD, or regime instability.

---

## 12. Stage 4 — holdout replay and candidate export

Purpose: export only candidates that replay cleanly and are worth owner
validation.

Stage 4 is not full promotion. It prepares candidates for downstream owner-run
validation.

For each archive elite selected for export:

1. Serialize candidate JSON compatible with `DSSStrategy`.
2. Replay the generated JSON on at least one short deterministic smoke window.
3. Verify signal count and trades are stable.
4. Write the candidate to `candidates/`.

Output:

```text
results/dss_sol_v2/
├── candidates/
│   ├── dss_v2_001_<trigger>_<cell>.json
│   └── ...
├── candidate_manifest.csv
└── candidate_manifest.md
```

Candidate manifest columns:

- `rank`
- `candidate_path`
- `candidate_id`
- `behavior_cell`
- `robust_score`
- `score_min`
- `trigger_name`
- `filter_names`
- `rrr`
- `risk_percent`
- `ttl`
- `atr_sl_mult`
- `validation_command`

The manifest must include exact next commands for owner validation:

```bash
uv run backtester compare-fixed \
  --data-dir data \
  --symbol SOL-USDT-SWAP \
  --strategy <candidate_path> \
  --from 2025-01-01 \
  --to 2025-12-31 \
  --output results/dss_v2_eval_2025
```

---

## 13. Search loop

MVP implementation loop:

```python
def run_search(config: DSSV2Config) -> DSSV2Result:
    data = load_windows(config)
    archive = DSSArchive()
    state = DSSState.load_or_create(config.output)

    for candidate in generate_stage0_candidates(config, state):
        state.record_generated(candidate)

        viability = evaluate_stage1(candidate, data, config)
        state.record_stage1(candidate, viability)
        if not viability.passed:
            continue

        proxy = evaluate_stage2(candidate, data, config)
        state.record_stage2(candidate, proxy)
        archive.consider_proxy(candidate, proxy)

        if not should_promote_to_stage3(candidate, proxy, archive, config):
            continue

        full = evaluate_stage3(candidate, data, config)
        state.record_stage3(candidate, full)
        archive.consider_full(candidate, full)

    exported = export_stage4_candidates(archive, data, config)
    write_report(state, archive, exported, config)
    return DSSV2Result(archive=archive, exported=exported)
```

The implementation may batch Stage 1/2/3 work for efficiency, but persisted
artifacts must still expose these stages.

---

## 14. Resume behavior

There should be no `--resume` flag.

If `--output` exists and contains DSS v2 state, the command resumes
automatically:

- read `state.json`;
- read completed candidate IDs from stage JSONL/CSV artifacts;
- skip already completed candidate-stage pairs;
- continue until `--n-trials` generated candidates have been reached;
- rewrite summary reports from full persisted state.

State files:

```text
state.json
stage0_candidates.jsonl
stage1_viability.csv
stage1_survivors.jsonl
stage2_proxy.csv
stage2_survivors.jsonl
stage3_full_scores.csv
archive.json
```

If existing output is from DSS v1 (`study.journal` without v2 state), fail fast:

```text
Output directory contains DSS v1 artifacts. DSS v2 cannot resume this run.
Use a new output directory.
```

---

## 15. Module layout

The next implementation can rewrite or replace the v1 modules.

Recommended layout:

```text
src/backtester/strategy_discovery/
├── dss_config.py              # v2 config + candidate dataclasses
├── dss_archive.py             # quality-diversity archive
├── dss_generator.py           # Stage 0 candidate generation
├── dss_viability.py           # Stage 1
├── dss_proxy.py               # Stage 2
├── dss_objective.py           # Stage 3 mandate scoring helpers
├── dss_state.py               # resumable artifacts
├── dss_report.py              # summary/report/export
├── signal_composer.py         # keep/reuse, fix as needed
├── parameterized_triggers.py  # keep/reuse
└── parameterized_filters.py   # keep/reuse
```

Existing modules that can be reused:

- `parameterized_triggers.py`
- `parameterized_filters.py`
- `signal_composer.py`
- `DSSStrategy` replay path, if candidate JSON format remains compatible
- `compute_mandate_score`, after moving it to a shared helper if needed

Existing modules likely to rewrite:

- `dss_objective.py`
- `dss_report.py`
- `dss_config.py`
- `__main__.py` search-signals command body

---

## 16. Tests

Required tests:

1. Candidate serialization round-trip.
2. Signal cache key excludes execution params but includes signal-shaping params.
3. Stage 1 rejects empty signals.
4. Stage 1 rejects too few signals in one window.
5. Stage 1 rejects overtrading.
6. Stage 2 promotes at least one candidate per occupied archive cell.
7. Archive keeps separate elites for different trigger families.
8. Archive replacement preserves best robust candidate.
9. Robust score penalizes high cross-window dispersion.
10. Stage 4 exported JSON replays through `DSSStrategy`.
11. Existing DSS v1 output directory fails resume with a clear message.
12. Existing DSS v2 output directory resumes without duplicating completed
    candidates.
13. CLI help no longer exposes `--sampler`.
14. CLI rejects removed v1-only options with a clear message.

Recommended smoke:

```bash
PYTHONPATH=src uv run pytest \
  tests/backtester/test_dss.py \
  tests/backtester/test_signal_composer.py \
  -q
```

Full relevant suite:

```bash
PYTHONPATH=src uv run pytest tests/backtester -q
```

---

## 17. Reporting

`summary.md` must start with an operator verdict:

```text
Verdict: no candidate / diagnostic only / candidates exported
Reason: short explanation
Generated candidates: N
Stage 1 survivors: N
Stage 2 survivors: N
Stage 3 full evaluations: N
Archive occupied cells: N
Exported candidates: N
Best robust score: X
Best candidate path: ...
```

Then include:

- stage funnel table;
- trigger family coverage;
- rejection reasons;
- archive occupancy by descriptor;
- top candidates by robust score;
- top candidates by archive cell;
- best score history;
- next owner commands.

If no candidate is good, the report is still useful. It should say which
families failed and why.

---

## 18. Implementation plan for the next agent

Do this as one coherent implementation, not as another research session.

1. Read ADR-0036 and this spec.
2. Replace the `search-signals` command internals; do not preserve v1 sampler
   paths.
3. Add/replace v2 dataclasses in `dss_config.py`.
4. Implement `dss_archive.py`.
5. Implement Stage 0 generation.
6. Implement Stage 1 viability.
7. Implement Stage 2 proxy backtest.
8. Implement Stage 3 full mandate scoring.
9. Implement Stage 4 export and replay smoke.
10. Implement v2 state/resume.
11. Rewrite report output.
12. Update tests.
13. Update README only if command examples or public output paths change.
14. Do not run owner-scale backtests. Provide the owner the exact command.

Acceptance for the next session:

- `uv run backtester search-signals --help` shows the simplified v2 command.
- Tests pass for DSS v2.
- A small synthetic or tiny real-data smoke writes all stage artifacts.
- The final chat reply gives the owner one bounded command for a real SOL v2
  search and the expected artifact paths.
