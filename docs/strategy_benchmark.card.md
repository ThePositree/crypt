# Strategy Benchmark Card

Full source: `docs/strategy_benchmark.md`

Use this card for strategy quality, optimizer targets, and owner-facing money
verdicts.

Benchmark target:

- `$10,000` reference capital.
- `+15%` monthly return floor.
- Positive ranking cap: `+20%` per month.
- Main SOL check: continuous 2025 backtest.
- Report after fees and slippage.

Risk checks:

- Monthly drawdown is measured from month-start capital using realized equity.
- Worse than `-10%` monthly below-start drawdown is a major risk breach.
- Three consecutive losing months are a discard-level warning.

Important policy:

- This benchmark is not a hard production gate.
- The owner may run a benchmark-failing strategy live.
- If live config is owner-promoted, document risks once and continue from the
  active runtime config.
