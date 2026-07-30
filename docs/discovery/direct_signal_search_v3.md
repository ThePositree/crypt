# Direct Signal Search v3 — persistent multi-timeframe search

> **Status**: proposed implementation spec
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
does not need backward compatibility with DSS v2 candidate JSONs, Stage 2/3
artifacts, state files, journals, candidate ids, reports, or backend state. Old
DSS v2 artifacts remain historical research evidence only.

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

Each catalog block must declare:

- supported roles: `trigger`, `filter`, `context`, or a subset;
- supported timeframes;
- parameters and bounds by timeframe when they differ;
- missing-data behavior;
- whether it uses only closed candles;
- audit fields emitted into candidate reports.

Signals and filters must not use an incomplete candle for their own timeframe.
At a lower-timeframe decision point, higher-timeframe features use the latest
closed higher-timeframe bar only.

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

DSS v3 has one evaluator: Stage 1 directional labeling. DSS v3 removes the DSS
v2 Stage 2/3 proxy/full backtest pipeline from search.

For every candidate and window, Stage 1:

1. generates trigger/filter events from closed candles only;
2. rejects overtrading candidates;
3. requires enough resolved labeled events;
4. labels each event by whether price reaches a fixed favorable barrier before
   a fixed adverse barrier;
5. reports directional metrics such as signal count, long/short ratio,
   `tp_first`, `sl_first`, `unresolved_tail`, barrier win rate, median MAE,
   median MFE, and bars to favorable barrier;
6. ranks and archives candidates by directional quality and behavior diversity.

The Stage 1 barriers are labeling tools, not proposed live SL/TP geometry.
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

Stage 1 promotion and ranking must use class-aware rules:

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

- `staged`
- `catcma_qd`
- `island_qd`
- `hyperband_qd`
- `smac_qd`

The preferred first large-run pressure is `hyperband_qd`, because most
multi-timeframe candidates should be killed cheaply by labeling before they
consume more search attention. `smac_qd` should receive an updated conditional
encoder so the surrogate can model `name@timeframe` instances and repeated
filter names across different timeframes.

Backends may differ in proposal generation and budget allocation, but none may
run DSS v2-style Stage 2/3 backtests inside DSS v3.

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
- the candidate writes the same Stage 1 labeling artifacts as backend-native
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

Search workers must be isolated from live-money execution: no trading keys, no
automatic strategy promotion, and no writes to live runtime strategy config.

## 10. Required artifacts

DSS v3 runs must write:

- `candidate_journal.jsonl`;
- `seen_candidates.*`;
- `backend_state/`;
- `archive/`;
- `heartbeat.json`;
- `progress.json`;
- Stage 1 labeling reports for all generated, rejected, promoted, and exported
  candidates;
- frequency-class archive reports;
- replayable candidate JSONs for promoted candidates.

Candidate hashes must be stable across process restarts and independent of JSON
key order.

## 11. Implementation order

1. Add the v3 candidate schema and stable hashing.
2. Add multi-timeframe feature loading and cache by
   `(symbol, timeframe, window)`.
3. Update trigger/filter catalog declarations to include role and timeframe
   support.
4. Permit repeated filter names when timeframe or params differ.
5. Replace the single global min-trade gate with frequency-class-aware Stage 1
   ranking and quality-diversity archive cells.
6. Remove DSS v2 Stage 2/3 backtest evaluation from the DSS v3 search path.
7. Add seen registry, random unseen injection, and novelty mutation as a shared
   sampler layer.
8. Update `hyperband_qd` first, then `smac_qd`, then the remaining backends.
9. Add endless mode and resumable backend/archive checkpoints.
10. Run bounded smoke searches before any long owner-run search.

Backward-compatible migration from DSS v2 artifacts is explicitly out of scope.
Use a new DSS v3 output directory for new searches.

## 12. Open questions

- Whether `1m` should be enabled in the first large DSS v3 run or held behind
  an aggressive-search flag.
- Whether `max_filters` should become an internal complexity budget or remain
  owner-configurable for v3 experiments.
- Whether sparse candidate pass thresholds should require higher barrier win
  rate than frequent candidates to offset lower sample size.
