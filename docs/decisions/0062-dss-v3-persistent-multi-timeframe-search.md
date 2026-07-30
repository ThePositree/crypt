# ADR-0062: DSS v3 persistent multi-timeframe search

- **Status**: accepted
- **Date**: 2026-07-30
- **Supersedes**: DSS v2 search, candidate shape, state, and export formats
- **Related**: ADR-0036, ADR-0037, ADR-0038, ADR-0039, ADR-0040, ADR-0061

## Context

Current DSS candidates are primarily searched on one primary timeframe. The
active v6 portfolio already showed that trading logic is not naturally
single-horizon: entry triggers, local filters, context filters, and regime
controls can each have different useful timeframes.

The owner wants to keep the DSS name, but evolve DSS into a larger
multi-timeframe research engine. The search space is intentionally expected to
be huge. The key question is not avoiding that size, but making the search
infrastructure persistent, resumable, diverse, and capable of continuing for
long periods alongside live execution.

The owner clarified that DSS must remain a fast directional candidate search:
it should not optimize or score trading geometry such as RRR, risk percent,
TTL, ATR stop multiplier, trailing stops, or portfolio sizing. Candidate
quality is checked by Stage 1 labeling only.

The owner also approved breaking DSS v2. DSS v3 does not need compatibility
with DSS v2 candidate JSONs, Stage 2/3 artifacts, state files, journals,
candidate ids, reports, or backend state.

The current DSS controls also make it difficult to search for both frequent
and sparse candidates in one run. A single global minimum signal count can
reject useful sparse strategies, while a low minimum can let weak frequent
strategies flood reports. The downstream product is a portfolio, so DSS must
preserve both strong high-frequency candidates and rare high-quality candidates
for later combination tests.

## Decision

DSS v3 will make timeframe a first-class part of every trigger and filter
instance:

```text
trigger_instance = trigger_name + timeframe + params
filter_instance = filter_name + timeframe + params
```

The same filter name may appear multiple times in one candidate when the
timeframe or parameters differ. Exact duplicate instances remain invalid.

DSS v3 may replace DSS v2 internals in place. Old DSS v2 artifacts remain
historical research evidence only and are not required to resume or replay
through the DSS v3 search command.

DSS v3 removes the DSS v2 Stage 2/3 proxy/full backtest pipeline from DSS
search. Stage 1 directional labeling is the only DSS evaluator. Full backtests,
mandate reports, optimizer runs, RRR/TTL/risk searches, donor portfolio
assembly, and live promotion are downstream workflows outside DSS.

DSS v3 will replace the single global min-trade gate with frequency classes.
At minimum, the quality-diversity archive must distinguish sparse, medium,
frequent, and overactive candidates. Sparse candidates may pass Stage 1 with
far fewer events than frequent candidates when their directional labels are
strong enough, and reports must show the class explicitly.

Frequency classes must also have independent archive/export quotas. A low
global frequency floor tends to let sparse high-win-rate candidates fill the
shortlist, while a high floor erases sparse candidates. DSS v3 should preserve
both classes in one run.

All search backends must add forced novelty:

- backend-native proposals remain the majority;
- random unseen valid candidates are injected periodically;
- archive mutations/crossovers periodically force exploration away from local
  optima.

When `--n-trials` is omitted, `backtester search-signals` will run in endless
mode. It must persist journals, seen-candidate registry, backend state,
quality-diversity archive, heartbeat/progress files, and resume automatically
from the same output directory after restart.

The live execution process and search worker remain separate. DSS v3 may write
research candidates, but production strategy promotion remains an explicit
owner decision.

## Consequences

- The search can represent strategies such as `trigger@5m` with
  `filter@5m`, `filter@H1`, and `filter@H4` in the same candidate.
- DSS v3 candidates are intentionally incomplete strategy candidates: they
  contain signal logic, not trade geometry.
- Sparse and frequent candidates can be found in the same run instead of
  needing separate command configurations.
- Stage 1 reports become more portfolio-aware because candidate frequency is a
  behavior descriptor rather than only a hard rejection gate.
- Implementation can remove DSS v2 compatibility code instead of carrying
  migration adapters.
- The search space grows substantially, so caching, stable hashing, duplicate
  prevention, and staged budget allocation become mandatory infrastructure.
- `hyperband_qd` should be the first backend updated for v3 because it is a
  good fit for allocating Stage 1 labeling attention over huge candidate
  spaces without running full backtests.
- `smac_qd` needs a v3 conditional encoder before its surrogate can model
  timeframe-aware repeated filter instances correctly.
- Continuous search becomes a normal background research mode, but it must not
  write live runtime config or use trading credentials.

## References

- `docs/discovery/direct_signal_search_v3.md`
- `docs/discovery/direct_signal_search_v2.md`
- `docs/tasks/BACKLOG.md`
