# SignalComposer — specification

> **Module**: `src/backtester/strategy_discovery/signal_composer.py`
> **Status**: pending implementation (ADR-0035, DSS phase P2)

---

## Purpose

`SignalComposer` converts a `TrialConfig` (trigger name + params + filter names + params
+ execution params) into a callable `generate_fn(StrategyData) -> pd.DataFrame`.

This generate function is the **bridge** between the DSS search engine and the
backtester. Its output schema must be identical to `crypt_ensemble.generate()` so that
`compare-fixed`, `walk-forward`, and `optimize` all work without modification.

---

## Public API

```python
class SignalComposer:
    def __init__(self) -> None:
        self._trigger_catalog = parameterized_trigger_catalog()   # dict[str, TriggerFactory]
        self._filter_catalog  = parameterized_filter_catalog()    # dict[str, FilterFactory]

    def build(self, config: TrialConfig) -> GenerateFn:
        """
        Returns a pure generate function.

        The returned function:
        - accepts a StrategyData (or bare DataFrame)
        - applies the trigger to get raw events
        - applies each filter in order; drops event if any filter returns passed=False
        - computes ATR-based stop_price and tp_price for surviving events
        - returns a pd.DataFrame with the SignalRow schema

        Thread-safe: the returned function captures only the config and the
        catalog function references. No shared mutable state.
        """

    def validate_config(self, config: TrialConfig) -> list[str]:
        """
        Returns a list of validation errors (empty = valid).
        Checks: trigger_name exists, filter_names exist, params within declared bounds.
        """
```

`GenerateFn = Callable[[StrategyInput], pd.DataFrame]`

---

## Output DataFrame schema (SignalRow)

Every row in the returned DataFrame represents one signal (entry opportunity).

| column | dtype | constraint |
|---|---|---|
| `bar_time` | `datetime64[ns, UTC]` | timestamp of the **closed** candle that triggered the signal |
| `symbol` | `str` | matches `StrategyData.symbol` |
| `side` | `str` | `"long"` or `"short"` |
| `confidence` | `float` | 0.0 to 100.0; see confidence section below |
| `rationale` | `str` | human-readable one-liner: `"{trigger} filtered by {filters}"` |
| `entry_price` | `float` | reference entry price (usually `close` of trigger candle) |
| `stop_price` | `float` | ATR-based SL: `entry ∓ atr(bar_time) × atr_sl_mult` |
| `tp_price` | `float` | derived: `entry ± (entry - stop) × rrr` |

No other columns are required. Columns in this list must be present with the exact names
and dtype families shown above.

### Confidence assignment

DSS signals have a uniform `confidence` of **75.0** unless the filter stack includes
`pf_context_aligned` (adds +5) or `pf_trend_ema_stack` (adds +5), capped at 95.0.
This is a placeholder; confidence tuning is a separate backlog item.

---

## ATR computation

`atr(bar_time)` = Wilder ATR over `atr_window` (default 14) bars of the H1 OHLCV,
computed only on **closed** candles (never the forming candle), evaluated at `bar_time`.

```python
def _atr_at(primary: pd.DataFrame, bar_time: pd.Timestamp, window: int) -> float:
    idx = primary.index.get_loc(bar_time)
    if idx < window:
        # fall back to simple range average when not enough history
        return primary["high"].iloc[:idx+1].sub(primary["low"].iloc[:idx+1]).mean()
    window_slice = primary.iloc[idx - window + 1 : idx + 1]
    return _wilder_atr(window_slice)
```

If ATR is zero or NaN, the signal is discarded (no stop can be placed).

---

## SL and TP derivation

```
side == "long":
    entry_price = close at bar_time
    stop_price  = entry_price - atr × atr_sl_mult
    tp_price    = entry_price + (entry_price - stop_price) × rrr

side == "short":
    entry_price = close at bar_time
    stop_price  = entry_price + atr × atr_sl_mult
    tp_price    = entry_price - (entry_price - stop_price) × rrr
```

`atr_sl_mult` and `rrr` come from `TrialConfig`.

---

## Internal flow

```
build(config)
    │
    ├─ lookup trigger factory → bind trigger_params  → trigger_fn(dataset) → list[DiscoveryEvent]
    │
    ├─ for each filter_name in config.filter_names:
    │       lookup filter factory → bind filter_params[filter_name] → filter_fn(event, dataset)
    │
    └─ return closure:
            generate_fn(data: StrategyInput) -> pd.DataFrame
                │
                ├─ build_discovery_dataset(data, window_label="dss", symbol=...)
                ├─ trigger_fn(dataset) → raw_events
                ├─ for event in raw_events:
                │       for filter_fn in filter_fns:
                │           result = filter_fn(event, dataset)
                │           if not result.passed: drop event; break
                ├─ for surviving events:
                │       atr = _atr_at(primary, event.event_time, window=14)
                │       if atr <= 0: skip
                │       compute stop_price, tp_price
                │       append SignalRow to output list
                └─ return pd.DataFrame(output_list)  [may be empty]
```

---

## Error handling

| situation | behaviour |
|---|---|
| unknown trigger_name | `ValueError` raised in `build()` immediately (never silently) |
| unknown filter_name | `ValueError` raised in `build()` immediately |
| params out of declared range | logged at WARNING; params clamped to bounds before use |
| trigger raises during generate | caught; event skipped; WARNING logged with trigger name + bar_time |
| ATR = 0 or NaN | event discarded; no warning (can be frequent near start of data) |
| all events filtered out | returns empty DataFrame; caller handles empty case |

No exception from `generate_fn` propagates to the Optuna objective. If the whole
call fails, the objective catches it and returns worst-case scores.

---

## Parameterized trigger factories

A trigger **factory** takes params and returns a `TriggerFn`:

```python
TriggerFactory = Callable[[TriggerParams], TriggerFn]
# where TriggerFn = Callable[[DiscoveryDataset], list[DiscoveryEvent]]
```

Trigger factories live in `parameterized_triggers.py`. Each factory:
1. Validates params against its `param_space()`.
2. Returns a closure that uses the bound params.

Example:

```python
def pt_nr4_breakout_factory(params: TriggerParams) -> TriggerFn:
    lookback = int(params.get("lookback", 4))   # NR-N generalization

    def _trigger(dataset: DiscoveryDataset) -> list[DiscoveryEvent]:
        df = dataset.ohlcv
        ranges = (df["high"] - df["low"]).rolling(lookback).min().shift(1)
        is_nr = (df["high"] - df["low"]) <= ranges
        long_mask = is_nr & (df["close"] > df["high"].shift(1))
        short_mask = is_nr & (df["close"] < df["low"].shift(1))
        return _events_from_masks(dataset, f"pt_nr{lookback}_breakout", long_mask, short_mask)

    return _trigger
```

---

## Parameterized filter factories

A filter **factory** takes params and returns a `FilterFn`:

```python
FilterFactory = Callable[[FilterParams], FilterFn]
# where FilterFn = Callable[[DiscoveryEvent, DiscoveryDataset], FilterResult]
```

Example:

```python
def pf_atr_distance_band_factory(params: FilterParams) -> FilterFn:
    low_mult  = float(params.get("low_mult",  0.3))
    high_mult = float(params.get("high_mult", 2.0))

    def _filter(event: DiscoveryEvent, dataset: DiscoveryDataset) -> FilterResult:
        features = dataset.features
        atr_dist = abs(features.loc[event.event_time, "atr_dist_close"])
        passed = low_mult <= atr_dist <= high_mult
        reason = f"atr_dist={atr_dist:.3f} in [{low_mult:.2f},{high_mult:.2f}]"
        return FilterResult(passed=passed, filter_name="pf_atr_distance_band", reason=reason, metadata={})

    return _filter
```

---

## Catalog registration

Both catalogs follow the same pattern:

```python
def parameterized_trigger_catalog() -> dict[str, TriggerFactory]:
    return {
        "pt_sweep_reversal":      pt_sweep_reversal_factory,
        "pt_structure_break":     pt_structure_break_factory,
        "pt_nr4_breakout":        pt_nr4_breakout_factory,
        ...
    }

def parameterized_filter_catalog() -> dict[str, FilterFactory]:
    return {
        "pf_atr_distance_band":   pf_atr_distance_band_factory,
        "pf_body_to_range_min":   pf_body_to_range_min_factory,
        ...
    }
```

---

## Tests

`tests/backtester/test_signal_composer.py` must cover:

| test | assertion |
|---|---|
| `test_build_returns_callable` | `build(config)` returns a callable |
| `test_generate_empty_when_no_events` | no signals when trigger never fires |
| `test_generate_schema_matches` | output columns match SignalRow spec |
| `test_stop_tp_long_consistency` | `stop < entry < tp` for all long rows |
| `test_stop_tp_short_consistency` | `tp < entry < stop` for all short rows |
| `test_unknown_trigger_raises` | `ValueError` on bad trigger_name |
| `test_filter_drops_events` | fewer rows when restrictive filter added |
| `test_filter_ordering_deterministic` | same config → same output every time |
| `test_atr_zero_discards_event` | flat-price candles produce no signals |
