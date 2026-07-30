# Strategy configs

Strategy JSONs are executable configuration, not status documentation.

| Path | Role |
| ---- | ---- |
| `backtester/` | Research/backtester configs used for experiments and conversion |
| `archive/` | Frozen configs for preserved candidates, portfolios, and owner-selected production lineages |

For live execution, the source of truth is the runtime config/env, primarily
`EXECUTION_STRATEGY_CONFIG`, and the JSON actually loaded by the executor. If
that runtime source and prose docs disagree, stop and ask the owner.

Use `docs/archive/candidates/` to understand why an archived strategy was kept
and which local `results/` artifacts support it.
