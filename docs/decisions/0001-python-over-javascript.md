# ADR-0001: Use Python (not JavaScript) as the implementation language

- **Status**: accepted
- **Date**: 2026-05-13
- **Owner**: agent (confirmed by owner)

## Context

Owner asked "Python or JS?" for a modular ensemble decision system for crypto
futures. Decision affects every downstream tooling choice.

## Decision

Python 3.11+.

## Alternatives considered

- **Node.js / TypeScript** — strong native async/WebSocket, weak quant
  ecosystem. Plausible for a thin streaming layer; insufficient for an
  ensemble with statistical tuning and (later) ML.
- **Rust** — best raw performance, immature TA/data-science ecosystem,
  steep cost for the prototype phase.

## Consequences

- Positive: access to `pandas`, `numpy`, `pandas-ta`, `scipy`, `scikit-learn`,
  `vectorbt`, mature `ccxt` Python bindings, and the broader quant ecosystem.
- Positive: lower iteration cost for the AI-first development style.
- Negative: GIL and slower per-op latency than Node/Rust. Irrelevant at the
  4h horizon (ADR-0003), would matter only if we add sub-second OF analytics
  later — in which case we extract that piece into Rust via PyO3.

## References

- `AGENTS.md`
- Owner chat decision, 2026-05-13.
