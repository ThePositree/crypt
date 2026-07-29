# Portfolio signal diagnostics

The backtester receives portfolio signals as one `signal_events` list per
primary-bar row. A row may contain zero, one, or several event dictionaries;
the legacy scalar `signal` column is not a reliable event count for donor
portfolios.

## Contract

- `signals.csv` keeps the original signal frame and adds
  `signal_event_count`, the number of valid dictionary events in that row.
- `signal_events.csv` is an event-level table. Each row contains
  `signal_time`, zero-based `event_index`, and every field present in the
  source event dictionary (`selected_strategy`, `signal`, `sl_price`, risk
  and exit parameters, and portfolio metadata when available).
- `signal_diagnostics.csv` reports `signal_events_count` (all events),
  `signal_event_rows` (bars with at least one event), and per-event counts for
  `signal`, `selected_strategy`, and `position_group` when those fields exist.
- Missing, `None`, non-list, and malformed event entries are treated as zero
  events and are not allowed to abort export.

The event table is intentionally separate from `signals.csv`: flattening
multiple events into one scalar would lose portfolio attribution and make
reconciliation ambiguous.
