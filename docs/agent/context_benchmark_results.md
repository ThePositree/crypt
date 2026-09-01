# Agent Context Benchmark Results

Baseline date: 2026-08-11

Command:

```bash
UV_CACHE_DIR=/tmp/uv-cache uv run python scripts/agent_context.py benchmark
```

Deterministic routed-markdown baseline:

| Metric | Result |
|---|---:|
| Questions | `19` |
| Source hits | `19 / 19` |
| Source hit rate | `100%` |
| Required-term hits | `19 / 19` |
| Required-term hit rate | `100%` |

Token-budget smoke:

```bash
UV_CACHE_DIR=/tmp/uv-cache uv run python scripts/agent_context.py budget --route backtester_regression
UV_CACHE_DIR=/tmp/uv-cache uv run python scripts/agent_context.py budget --route docs_ai_context
```

| Route | Eager approx tokens | Routed approx tokens | Savings |
|---|---:|---:|---:|
| `backtester_regression` | `15553` | `9235` | `40.62%` |
| `docs_ai_context` | `15553` | `78148` | `-402.46%` |

Rules for future retrieval experiments:

- A vector DB must point back to canonical markdown paths and match or beat the
  `100%` source-hit and required-term baseline before becoming a default
  workflow.
- Text-as-image may be tested only on archive/reference docs and must not hold
  hard rules, current state, live-money truth, or phase checkpoints.
- If a future retriever gets lower token usage but loses any required source or
  term, reject it or keep it as an optional discovery aid only.
