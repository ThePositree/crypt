# Backtester Regression Card

Full source: `docs/backtester_regression.md`

Use this card when checking whether backtester behavior drifted.

Canonical strict checks:

- Current production v6 full replay:
  - from `2021-12-18T00:00:00Z`
  - to `2026-06-29T14:00:00Z`
  - expected final capital `$1,237,819.83`
  - expected `1544` trades and `0` liquidation exits
- Live phase B replay:
  - from `2026-07-18T00:00:00Z`
  - to `2026-07-27T23:00:00Z`
  - capital `$102.34`
  - expected final capital `$101.48`
  - expected `17` trades
- Live phase C replay:
  - load from `2026-07-13T00:00:00Z`
  - account from `2026-07-29T12:00:00Z`
  - to `2026-08-10T22:00:00Z`
  - capital `$83.09804366087424`
  - expected final capital `$72.30`
  - expected `20` trades

Phase C fails if the replay misses the `2026-07-29T12:00:00Z` signal, exits
the `2026-08-03T17:00:00Z` trade on `2026-08-06` instead of
`2026-08-04T00:58Z`, or diverges from the listed raw SL values without an
audited reason.

Read the full doc before running or updating pass/fail targets.
