# Router archive layout

Contract for preserving router candidates that are useful research baselines
but are not accepted for production.

Router archives are separate from strategy archives:

```text
docs/archive/routers/
  README.md
  <router_id>/
    README.md
    utility_snapshot.csv
    offset_snapshot.csv
    provenance.json

routers/archive/
  <router_id>.json
```

Full search artifacts stay under `results/` and are referenced from
`provenance.json`.

## Router identity

Archive IDs describe behavior, not the temporary search row number:

```text
<scoring>_<lookback>d_<switch_policy>
```

Example:

```text
rolling_median_120d_switch_margin_3
```

## Required contract

Archived routers:

- score the full archived strategy set;
- select exactly one strategy at every decision point;
- never split capital between strategies;
- never select cash;
- use only completed prior labels where `label_end <= asof`;
- preserve the exact search config and validation artifact.

## Archive reasons

| Reason | Meaning |
| --- | --- |
| `research_seed` | useful baseline or distinct routing family |
| `near_miss` | strong economics but not production-safe |
| `superseded` | replaced by a stronger router of the same family |

Archiving stops local optimization of that candidate. Future searches may use
it as a benchmark, but should explore broader router families unless the owner
explicitly revives it.

