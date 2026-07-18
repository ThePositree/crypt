# Strategy configs

| Path | Role |
| ---- | ---- |
| `backtester/` | **Active** candidates for donor backtests and Optuna |
| `archive/` | Frozen copies of shelved candidates (see `docs/archive/candidates/`) |

Re-run an archived candidate using the JSON under `archive/` and the
`execution_params.json` in its archive folder.
