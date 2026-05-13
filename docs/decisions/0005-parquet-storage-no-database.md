# ADR-0005: Parquet files + JSON logs, no database in MVP

- **Status**: accepted
- **Date**: 2026-05-13
- **Owner**: agent

## Context

The project runs locally on the owner's machine, monitors 3 symbols at 4h
horizon, and has a 0$ infrastructure budget. A database would add
operational weight (running Postgres/Redis, migrations, backups) without
meaningful benefit at this scale.

## Decision

- Historical market data is persisted as Parquet files under `data/<symbol>/`
  partitioned by data type (`ohlcv_h4.parquet`, `funding.parquet`,
  `oi_1h.parquet`, ...).
- Reads use `pandas.read_parquet` (or `polars` if we hit a performance wall).
- Live state needed across ticks (last verdict per symbol, last alert time
  for cooldown) lives in a single JSON file `data/state.json`, atomically
  written.
- Verdicts are appended to `data/verdicts.jsonl` (newline-delimited JSON).

## Alternatives considered

- **SQLite**: avoided to keep the cache fully columnar (Parquet is faster
  for time-series scans and zero-ops).
- **TimescaleDB**: overkill at 3 symbols × 4h candles.
- **DuckDB-backed**: attractive (SQL on Parquet without a server), but the
  bare `pandas` + Parquet path is simpler. Revisit when the dataset crosses
  a few hundred MB.

## Consequences

- Positive: zero infrastructure. `git clone && uv sync && uv run ...`.
- Positive: trivially portable to a VPS later.
- Negative: no SQL-style ad-hoc analytics. Mitigation: load Parquet into
  DuckDB or `pandas` interactively when needed.
- Negative: no concurrent writers. Acceptable — there is exactly one
  scheduler.

## References

- Owner chat, 2026-05-13 (0$ budget).
