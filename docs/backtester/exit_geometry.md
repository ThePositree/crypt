# Exit geometry (TP-first mode)

Contract for donor execution sizing and TP/SL placement in the backtester.

## Modes

| Mode | CLI / JSON | Primary knob | SL source | TP source |
| --- | --- | --- | --- | --- |
| **SL-first** (default) | `exit_geometry=sl_rrr` | `rrr` | Strategy `sl_price` (structural) | `entry ± sl_dist × rrr` |
| **TP-first** | `exit_geometry=tp_pct` | `tp_move_pct` | Derived from TP and `rrr` | `entry × (1 ± tp_move_pct)` |

Both modes keep **risk-based sizing**: `size = risk_value / sl_dist`.

## TP-first formulas

Long (`signal = 1`):

```
tp_dist   = entry_price × tp_move_pct
tp_price  = entry_price + tp_dist
sl_dist   = tp_dist / rrr
sl_price  = entry_price - sl_dist   (after structural policy)
```

Short: mirror signs.

`tp_move_pct` is a **gross price move** decimal (e.g. `0.015` = 1.5%).

### Breakeven floor

Skip the entry when `tp_move_pct < min_tp_move_pct` (default `0.004` = 0.4%),
aligned with the working round-trip friction floor in BACKLOG.

## Execution context in strategy.generate

CLI / optimizer / compare-fixed flags are propagated into
`strategy.generate()` via `StrategyData.metadata["execution_context"]`
(`StrategyExecutionContext` in `src/backtester/execution_context.py`):

| Field | Source flag |
| --- | --- |
| `exit_geometry` | `--exit-geometry` |
| `tp_move_pct` | `--tp-move-pct` |
| `structural_sl_mode` | `--structural-sl-mode` |
| `min_tp_move_pct` | `--min-tp-move-pct` |

Strategies may read this context and change signal emission. `crypt_ensemble`
skips the structural SL **entry gate** when `exit_geometry=tp_pct`: trigger +
discovery-mapped filters still apply; order-block / pivot anchors are not
required to emit `signal != 0`. ExecutionSim still applies TP-first geometry
on entry.

### Structural SL policy (exit layer)

Strategy still emits `sl_price` (structural). In TP-first mode it constrains
derived SL:

| `structural_sl_mode` | Behaviour |
| --- | --- |
| `cap` (default) | `sl_dist = min(derived_sl_dist, structural_sl_dist)` when structural is valid; otherwise derived only |
| `ignore` | use derived SL only |
| `reject` | skip trade when derived SL is wider than structural SL |

When `cap` binds, TP stays at the target move; effective RRR becomes
`tp_dist / sl_dist ≥ rrr`.

## Optuna

When `--tp-move-pct-low` and `--tp-move-pct-high` are set on `backtester optimize`,
trials search `tp_move_pct` and execution runs in `tp_pct` mode. `rrr` remains
searchable in parallel (SL distance is derived).

Fixed runs (`backtester run`, `compare-fixed`) use `--exit-geometry tp_pct`
and `--tp-move-pct`.

## Backward compatibility

Default `exit_geometry=sl_rrr` preserves existing behaviour. Strategy JSON
`backtest_args` may override any execution field.
