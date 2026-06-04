# In progress

## Next steps — validate a narrow H1 short-only candidate

**What:** run a bounded candidate validation using
`strategies/backtester/crypt_ensemble_h1_filter_short_only.json`, not the full
`crypt_ensemble_h1_filtered.json` combination.

**Why now:** base-vs-filtered diagnostics and two ablations are complete. The
full filter improved aggregate return by deleting longs, but it also worsened
SOL January and underperformed the short-only ablation. `no_liquidity_sweep`
alone stayed negative because harmful longs remained.

**Expected gain:** decide whether short-only is a tradable H1 candidate worth a
long owner-run check, or whether SOL March / TON March failures require signal
logic work before any filter is promoted.

**Acceptance:** produce one timestamped `compare-fixed` or equivalent
candidate report over the default SOL Jan/Feb/Mar and TON Jan/Feb/Mar/Apr
windows, summarize return/PF/drawdown/trades by window, and explicitly state
whether short-only is promoted, rejected, or needs a smaller follow-up.

Start from these artifacts:

- base: `results/crypt_ensemble_h1_signal_quality_base/20260604_141103`
- full filter: `results/crypt_ensemble_h1_signal_quality_filtered/20260604_142009`
- short-only ablation:
  `results/crypt_ensemble_h1_signal_quality_filter_short_only/20260604_143218`
- no-liquidity-sweep ablation:
  `results/crypt_ensemble_h1_signal_quality_filter_no_liquidity_sweep/20260604_144227`

Suggested command:

```bash
MPLCONFIGDIR=/tmp/matplotlib \
UV_CACHE_DIR=/tmp/uv-cache \
uv run backtester compare-fixed \
    --data-dir data \
    --primary-timeframe 1h \
    --strategy strategies/backtester/crypt_ensemble_h1_filter_short_only.json \
    --output results/crypt_ensemble_h1_short_only_candidate \
    --rrr 1.25 \
    --ttl 36 \
    --risk-percent 1.0 \
    --jobs 3
```

Use the root-integrated backtester commands from `README.md` and
`docs/backtester_migration.md`; do not use the removed `crypt.backtest`
harness.
