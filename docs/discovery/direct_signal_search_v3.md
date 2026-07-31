# Direct Signal Search v3 — persistent multi-timeframe search

> **Status**: implemented active search contract
> **Introduced**: 2026-07-30
> **Supersedes**: DSS v2 search, candidate shape, state, and export formats
> **ADR**: ADR-0062

---

## 1. Purpose

DSS remains the project name for automated signal discovery. DSS v3 extends
DSS v2 from a single-primary-timeframe search into a persistent
multi-timeframe research engine, and narrows DSS evaluation back to directional
labeling only.

The goal is to search for strategies where each trigger and filter can live on
the timeframe where it has edge:

- lower timeframes (`1m`, `5m`, `15m`) for entry timing, fast reclaim,
  local sweeps, and micro-impulse behavior;
- `H1` for the current main setup cadence and many existing donor families;
- `H4` and `D1` for regime, trend, volatility, risk throttles, and directional
  context.

Production promotion remains manual owner control. DSS v3 only writes
directional research artifacts and candidate configs. It does not run trading
geometry optimization or full mandate backtests.

DSS v3 is allowed to break DSS v2 internals and artifacts. The implementation
does not need backward compatibility with DSS v2 candidate JSONs, replay
backtest artifacts, state files, journals, candidate ids, reports, or backend
state. Old DSS v2 artifacts remain historical research evidence only.

## 2. Candidate model

DSS v3 treats a trigger or filter as an instance, not only a catalog name:

```text
trigger_instance = trigger_name + timeframe + params
filter_instance = filter_name + timeframe + params
```

The same filter name may appear multiple times in one candidate when the
timeframe or parameters differ:

```text
trigger:
  pt_vwap_reclaim@5m

filters:
  pf_rsi_zone@5m
  pf_rsi_zone@H1
  pf_rsi_zone@H4
  pf_volume_ratio@15m
  pf_trend_ema_stack@H4
```

Exact duplicate instances are not allowed:

```text
filter_name + timeframe + normalized_params
```

must be unique inside one candidate.

DSS v3 candidates do not contain trading geometry fields such as:

- `rrr`;
- `risk_percent`;
- `position_ttl_bars`;
- `atr_sl_mult`;
- trailing-stop parameters;
- portfolio sizing parameters.

Those belong to downstream strategy refinement after DSS has produced a strong
directional candidate.

## 3. Timeframe contract

Allowed initial timeframes:

```text
1m, 5m, 15m, H1, H4, D1
```

Current crypt-parquet loading supports `15m`, `H1`, `H4`, and `D1` candles in
normal DSS searches. `1m` is usable only when minute execution candles are
explicitly loaded into `StrategyData`. `5m` must fail as missing data until a
real source or resampling policy is added; DSS must not silently fall back to a
different timeframe.

Crypt-parquet start/end bounds apply to every loaded DSS candle frame, not only
the primary frame. Context loaders may read pre-window history internally, but
`StrategyData.candles` exposed to DSS search must not contain triggerable bars
outside the requested search window.

Each catalog block must declare:

- supported roles: `trigger`, `filter`, `context`, or a subset;
- supported timeframes;
- parameters and bounds by timeframe when they differ;
- missing-data behavior;
- whether it uses only closed candles;
- audit fields emitted into candidate reports.

The active CLI uses conservative catalog timeframe declarations when expanding
blocks into `name@timeframe` search labels. Entry-timing triggers and
session/VWAP filters are restricted to intraday labels; context and trend
filters may use `H4`/`D1`; unavailable `1m`/`5m` labels are not emitted by the
default crypt-parquet search space.

Signals and filters must not use an incomplete candle for their own timeframe.
At a lower-timeframe decision point, higher-timeframe features use the latest
closed higher-timeframe bar only.

The active implementation caches feature datasets by `(data, timeframe,
window, symbol)` inside the run-local `SignalComposer`. Trigger datasets are
built on the trigger timeframe; filter datasets are built on their own
timeframe and as-of aligned to trigger-event timestamps. Coarser filter
timeframes are shifted to their inferred close time before alignment, so a
lower-timeframe event cannot read an unfinished higher-timeframe candle.

## 4. Entry and alignment

A trigger instance emits an event on a closed candle of its own timeframe. The
entry model is:

```text
event at closed bar T on trigger timeframe -> enter at next open of that same
trigger timeframe
```

Higher-timeframe filters are aligned by as-of joins to their latest closed bar.
They may pass or reject a lower-timeframe event but must not move the event
time.

Existing H1 portfolio behavior remains representable as:

```text
trigger@H1 + filters@H1 + entry at next H1 open
```

## 5. Evaluation model

DSS v3 has one evaluator: directional labeling. DSS v3 removes the DSS v2
proxy/full backtest pipeline from search.

For every candidate and window, directional labeling:

1. generates trigger/filter events from closed candles only;
2. rejects overtrading candidates;
3. requires enough resolved labeled events;
4. labels each event by whether price reaches a fixed favorable barrier before
   a fixed adverse barrier;
5. reports directional metrics such as signal count, long/short ratio,
   `tp_first`, `sl_first`, `unresolved_tail`, barrier win rate, median MAE,
   median MFE, and bars to favorable barrier;
6. ranks and archives candidates by directional quality and behavior diversity.

Signal counts, overtrading checks, minimum-count checks, window duration, and
barrier labels are evaluated on the trigger timeframe frame. A `trigger@15m`
candidate must label against `15m` next-open/next-bars, even when the run's
primary timeframe is `H1` or `H4`.

The directional barriers are labeling tools, not proposed live SL/TP geometry.
They must not be exported as production stops or take-profits.

Full backtests, mandate reports, optimizer runs, RRR/TTL/risk searches, donor
portfolio assembly, and live promotion are downstream workflows outside DSS v3.

## 6. Frequency classes

DSS v3 must search sparse and frequent directional candidates in the same run.
The downstream strategy is a portfolio: frequent candidates can provide steady
trade flow, while sparse candidates can add rare high-quality regimes or
uncorrelated behavior.

Frequency is part of candidate behavior, not a single global minimum-trade
gate.

Default annualized frequency classes:

| Class | Resolved labeled events per year |
| --- | ---: |
| `sparse` | `20` to `59` |
| `medium` | `60` to `179` |
| `frequent` | `180` to `520` |
| `overactive` | `> 520` |

The exact thresholds may become CLI/config values, but the search must keep
separate quality-diversity archive cells by frequency class. A candidate that
is excellent but sparse must not be discarded only because it does not satisfy
a global frequent-candidate minimum.

Directional promotion and ranking must use class-aware rules:

- `sparse` candidates need enough resolved labels for statistical sanity, but
  may pass with far fewer events than frequent candidates;
- frequent candidates should be penalized for weak edge because they can
  dominate portfolio turnover;
- `overactive` candidates are usually rejected or heavily penalized unless an
  explicit aggressive-search profile permits them;
- export and archive ranking must keep independent per-frequency-class quotas;
  otherwise `min_signals_per_week=0` will let sparse high-win-rate candidates
  fill the shortlist, while a high global frequency floor will erase sparse
  candidates entirely;
- reports must show per-window event count and annualized frequency class so
  sparse specialists are not confused with broad high-frequency systems.

Portfolio assembly remains downstream. DSS v3 only preserves strong candidates
from different frequency classes so later portfolio construction can test
whether they complement each other.

## 7. Search backends

All DSS backends must understand the v3 candidate identity:

- `directional`
- `catcma_qd`
- `island_qd`
- `hyperband_qd`
- `smac_qd`

`catcma_qd` uses the maintained `cmaes.CatCMAwM` optimizer for the mixed
continuous/integer/categorical candidate encoding. It decodes CatCMAwM
solutions into DSS trigger/filter/timeframe candidates, accumulates evaluated
ask/tell pairs, and updates the optimizer only on full CatCMAwM population
batches. Deterministic one-choice dimensions are decoded locally instead of
being passed to CatCMAwM.

The preferred first large-run pressure is `hyperband_qd`, because most
multi-timeframe candidates should be killed cheaply by labeling before they
consume more search attention. `smac_qd` should receive an updated conditional
encoder so the surrogate can model `name@timeframe` instances and repeated
filter names across different timeframes.

Backends may differ in proposal generation and budget allocation, but none may
run DSS v2-style replay backtests inside DSS v3.

## 8. Forced novelty and random injection

Every backend must include a shared novelty-injection policy so the search does
not get trapped in one local family.

Default target mix:

```text
70-85% backend-native proposals
10-20% random unseen valid candidates
5-10% novelty mutations or crossovers from archive elites
```

Random and novelty candidates must be valid, unseen, and auditable:

- candidate hash has not been evaluated before;
- exact duplicate filter instances are absent;
- repeated filter names are allowed only when timeframe or params differ;
- max complexity limits are respected;
- the candidate writes the same directional labeling artifacts as backend-native
  proposals.

Novelty dimensions should include at least:

- trigger family;
- trigger timeframe;
- filter timeframe layout;
- frequency class;
- long/short bias;
- holding-time bucket;
- window specialist versus generalist behavior.

## 9. Persistent endless mode

When `--n-trials` is omitted, `backtester search-signals` runs in endless mode.
When `--n-trials` is provided, it remains a bounded run.

The default owner workflow is endless. In normal DSS research commands, omit
`--n-trials` so journals can be migrated between machines and the search can
continue indefinitely across the large multi-timeframe candidate space. Use
`--n-trials` only for smoke tests, debugging, short audits, or intentionally
bounded comparison runs.

`backtester search-signals-matrix` follows the same contract: by default it
launches each child `search-signals` backend without `--n-trials`. If
`--n-trials` is provided to the matrix command, that bounded per-algorithm
budget is passed to every child backend.

`--n-trials` counts unique candidates that reach directional evaluation.
Duplicate candidate hashes are journaled and skipped without consuming the
evaluated budget. If a finite or endless run cannot find a new unseen candidate
for a batch because the configured search space is exhausted, the runner writes
current progress and exits the loop instead of spinning.

Endless mode requirements:

- automatic resume from the existing `--output` directory;
- durable seen-candidate registry;
- append-only candidate journal;
- backend state checkpoints;
- quality-diversity archive checkpoints;
- periodic reports and heartbeat/progress files;
- single-writer lock for the output directory;
- safe shutdown on interrupt without corrupting state.

Stopping and starting the command with the same arguments and output directory
must continue from the last durable checkpoint rather than restart exploration.
Endless mode refreshes ranked/export/archive reports after each completed
batch, so an operator can inspect current `directional_ranked.csv` and
`directional_candidates/` without stopping the search.

Search workers must be isolated from live-money execution: no trading keys, no
automatic strategy promotion, and no writes to live runtime strategy config.

## 10. Required artifacts

DSS v3 runs must write:

- `candidates.jsonl`;
- `candidate_journal.jsonl`;
- `seen_candidates.jsonl`;
- `backend_state/`;
- `archive/`;
- `heartbeat.json`;
- `progress.json`;
- `directional_viability.csv`;
- `directional_rejections.csv`;
- `directional_survivors.jsonl`;
- `directional_ranked.csv`;
- `directional_near_misses.csv`;
- `directional_specialists.csv` and `directional_specialists.jsonl` when
  specialist windows are enabled;
- `archive/directional_frequency_archive.csv`;
- replayable candidate JSONs under `directional_candidates/`.

Candidate hashes must be stable across process restarts and independent of JSON
key order.

Current DSS v3 runners read and write only the current directional artifact
names. New output must use only the current directional artifact names.

## 11. Implementation status

The active implementation includes the v3 candidate schema, stable hashing,
multi-timeframe feature/cache plumbing, repeated filter instances by
timeframe/params, directional-only evaluation, durable runtime state, duplicate
skipping, random/novelty injection, bounded and endless runner modes, and
directional artifact exports.

`catcma_qd` is backed by `cmaes.CatCMAwM`; its backend state summary records
the optimizer identity, population/tell counters, pending feedback, and current
categorical probabilities where exposed by the dependency.

Use a new DSS v3 output directory for clean searches. Historical DSS v2
research directories remain historical evidence, not a supported migration
target.

## 12. Open questions

- Whether `1m` should be enabled in the first large DSS v3 run or held behind
  an aggressive-search flag.
- Whether `max_filters` should become an internal complexity budget or remain
  owner-configurable for v3 experiments.
- Whether sparse candidate pass thresholds should require higher barrier win
  rate than frequent candidates to offset lower sample size.
