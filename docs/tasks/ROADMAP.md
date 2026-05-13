# Roadmap

Owner-defined global milestones. Agents may **suggest** edits in chat but do
not silently rewrite this file. Implementation details belong to
`BACKLOG.md`.

---

## M0 — Project scaffold ✅

Repository structure, AI-first process, ADRs, engine specs. No code yet.

## M1 — MVP (signal-only, manual trading)

Working pipeline that runs locally and emits Telegram alerts on closed `H4`
candles for `SOL-USDT-SWAP`, `TON-USDT-SWAP`, `XPL-USDT-SWAP`.

Scope:

- Data layer (OKX REST via ccxt): OHLCV (H4 + H1 + D1), funding, OI history,
  long/short ratio, taker volume.
- Engines: trend, mean-reversion, derivatives, volatility, regime detector.
- Aggregator with regime-conditional weighted sum, confidence ∈ [0, 100].
- Decision filters: confidence threshold (default 75), per-symbol cooldown,
  inputs-missing guard.
- Sinks: Telegram + JSONL log + console.
- Configurable via `.env` and one YAML.

Exit criteria: live system runs for ≥ 14 days without crash, with at least
one verdict per symbol per `H4` and Telegram alerts visible when threshold
is crossed.

## M2 — Backtest harness and weight calibration

Replay engines over the last ≥ 6 months of OKX H4 history. Calibrate
per-regime weights. Produce a written report: per-engine hit rate, ensemble
expectancy, drawdown, regime-by-regime breakdown.

Exit criteria: documented `weights.yaml` derived from history, with a
critique of where the model is fragile.

## M3 — Paper trading and validation

Run the live system in parallel with a paper-trading ledger. Owner trades
manually based on alerts; the paper ledger tracks "what if I had taken
every alert" with realistic fees and slippage.

Exit criteria: ≥ 60 days of live + paper-trading data. Owner decides
go/no-go for M4.

## M4 — Auto-execution (conditional)

Replace `ExecutionSink` stub with a real OKX order router. Position sizing,
stop-loss, take-profit. Strict per-day loss limits.

This milestone only starts if M3 produced a track record the owner is
satisfied with.

## M5+ (not committed)

Candidates: sentiment engine, liquidation collector + engine, ML meta-
aggregator, additional symbols, VPS deployment, Streamlit dashboard.
