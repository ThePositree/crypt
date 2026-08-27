# Retired root-native backtest harness

The old `crypt.backtest` harness was removed on 2026-06-04 by ADR-0023.

M2 backtesting now uses the root-integrated donor package:

- package: `src/backtester/`;
- CLI: `uv run backtester ...`;
- strategy configs: `strategies/backtester/`;
- tests: `tests/backtester/`;
- migration handoff: `docs/backtester_migration.md`.

The removed harness under `src/crypt/backtest/` was an earlier attempt to port
selected donor pieces into `crypt`. It is no longer the canonical path and
must not receive new feature work unless the owner explicitly reverses
ADR-0023.

Use `docs/backtester_migration.md` for current M2 commands and contracts.
