"""SignalComposer — bridges a TrialConfig and the backtester.

Builds a ``generate_fn(StrategyData) -> pd.DataFrame`` from a TrialConfig.
The output schema matches the SignalRow spec in docs/discovery/signal_composer.md.

No I/O inside the returned generate function. All state is captured at build time.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import replace
from typing import TYPE_CHECKING

import pandas as pd

from backtester.strategy_discovery.dss_config import DSSInstance, TrialConfig
from backtester.strategy_discovery.events import DiscoveryEvent
from backtester.strategy_discovery.features import (
    DiscoveryDataset,
    align_discovery_dataset_asof,
    build_timeframe_discovery_dataset,
)
from backtester.strategy_discovery.parameterized_filters import (
    FilterFn,
    parameterized_filter_catalog,
)
from backtester.strategy_discovery.parameterized_triggers import parameterized_trigger_catalog
from backtester.strategy_discovery.pinescript_catalog import (
    pinescript_filter_catalog,
    pinescript_trigger_catalog,
)

if TYPE_CHECKING:
    from backtester.data_contracts import StrategyInput

logger = logging.getLogger(__name__)

_SIGNAL_ROW_COLUMNS = [
    "bar_time",
    "symbol",
    "side",
    "confidence",
    "rationale",
    "entry_price",
    "stop_price",
    "tp_price",
]

GenerateFn = Callable[["StrategyInput"], pd.DataFrame]
SignalRow = dict[str, object]

_CONTEXT_CONFIDENCE_BONUS: dict[str, float] = {
    "pf_context_aligned": 5.0,
    "pf_trend_ema_stack": 5.0,
}
_BASE_CONFIDENCE = 75.0
_MAX_CONFIDENCE = 95.0


class SignalComposer:
    """Converts a TrialConfig into a pure generate function."""

    def __init__(self) -> None:
        self._trigger_catalog = {
            **parameterized_trigger_catalog(),
            **pinescript_trigger_catalog(),
        }
        self._filter_catalog = {
            **parameterized_filter_catalog(),
            **pinescript_filter_catalog(),
        }
        self._dataset_cache: dict[tuple[int, str, str, str], DiscoveryDataset] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def build(self, config: TrialConfig) -> GenerateFn:
        """Return a pure generate function for the given trial config.

        Raises
        ------
        ValueError
            If trigger_name or any filter_name is unknown.
        """
        self.validate_or_raise(config)

        def generate(data: StrategyInput) -> pd.DataFrame:
            from backtester.data_contracts import StrategyData

            symbol = ""
            if isinstance(data, StrategyData):
                symbol = str(data.metadata.get("symbol", ""))
            window_label = str(getattr(data, "metadata", {}).get("window_label", "dss"))
            dataset = self._cached_dataset(
                data=data,
                timeframe=config.trigger_instance.timeframe,
                window_label=window_label,
                symbol=symbol,
            )
            filter_datasets = {
                instance.label: self._cached_dataset(
                    data=data,
                    timeframe=instance.timeframe,
                    window_label=window_label,
                    symbol=symbol,
                )
                for instance in config.filter_instances
            }
            return self.generate_from_dataset(config, dataset, filter_datasets=filter_datasets)

        return generate

    def validate_or_raise(self, config: TrialConfig) -> None:
        """Raise when a DSS config references an unknown trigger or filter."""

        trigger_name = config.trigger_instance.name
        if trigger_name not in self._trigger_catalog:
            available = sorted(self._trigger_catalog)
            raise ValueError(f"Unknown trigger_name {trigger_name!r}. Available: {available}")
        for instance in config.filter_instances:
            if instance.name not in self._filter_catalog:
                available = sorted(self._filter_catalog)
                raise ValueError(f"Unknown filter_name {instance.name!r}. Available: {available}")

    def generate_from_dataset(
        self,
        config: TrialConfig,
        dataset: DiscoveryDataset,
        *,
        filter_datasets: dict[str, DiscoveryDataset] | None = None,
    ) -> pd.DataFrame:
        """Generate one DSS signal frame from an already-built shared dataset."""

        self.validate_or_raise(config)
        trigger_name = config.trigger_instance.name
        trigger_factory = self._trigger_catalog[trigger_name]
        trigger_fn = trigger_factory(config.trigger_params)

        filter_instances = config.filter_instances
        filter_fns = [
            (
                instance.label,
                self._filter_catalog[instance.name](instance.params),
            )
            for instance in filter_instances
        ]

        filter_labels = tuple(instance.label for instance in filter_instances)
        filter_names_str = "+".join(filter_labels) if filter_labels else "no_filter"
        rationale_base = f"{config.trigger_instance.label} | {filter_names_str}"

        confidence_bonus = min(
            sum(_CONTEXT_CONFIDENCE_BONUS.get(instance.name, 0.0) for instance in config.filter_instances),
            _MAX_CONFIDENCE - _BASE_CONFIDENCE,
        )
        confidence = min(_BASE_CONFIDENCE + confidence_bonus, _MAX_CONFIDENCE)

        try:
            raw_events = trigger_fn(dataset)
        except Exception:
            logger.warning(
                "Trigger %s raised during generate; returning empty DataFrame",
                trigger_name,
                exc_info=True,
            )
            return _empty_signal_df()

        aligned_filter_datasets = _align_filter_datasets(
            dataset=dataset,
            filter_instances=filter_instances,
            filter_datasets=filter_datasets or {},
        )
        surviving: list[SignalRow] = []
        for event in raw_events:
            if not _apply_filters(event, dataset, filter_fns, aligned_filter_datasets):
                continue
            entry = event.entry_reference_price
            surviving.append(
                {
                    "bar_time": event.event_time,
                    "symbol": event.symbol,
                    "side": event.side,
                    "confidence": confidence,
                    "rationale": rationale_base,
                    "entry_price": entry,
                    "stop_price": 0.0,
                    "tp_price": 0.0,
                }
            )

        if not surviving:
            return _empty_signal_df()

        df = pd.DataFrame(surviving, columns=_SIGNAL_ROW_COLUMNS)
        df["bar_time"] = pd.to_datetime(df["bar_time"], utc=True)
        return df.sort_values("bar_time").reset_index(drop=True)

    def validate_config(self, config: TrialConfig) -> list[str]:
        """Return a list of validation errors (empty = valid)."""
        errors: list[str] = []
        if config.trigger_instance.name not in self._trigger_catalog:
            errors.append(f"Unknown trigger_name: {config.trigger_instance.name!r}")
        try:
            filter_instances = config.filter_instances
        except ValueError as exc:
            errors.append(str(exc))
            return errors
        for instance in filter_instances:
            if instance.name not in self._filter_catalog:
                errors.append(f"Unknown filter_name: {instance.name!r}")
        return errors

    def _cached_dataset(
        self,
        *,
        data: StrategyInput,
        timeframe: str,
        window_label: str,
        symbol: str,
    ) -> DiscoveryDataset:
        key = (id(data), timeframe, window_label, symbol)
        cached = self._dataset_cache.get(key)
        if cached is not None:
            return cached
        dataset = build_timeframe_discovery_dataset(
            data=data,
            timeframe=timeframe,
            window_label=window_label,
            symbol=symbol,
        )
        self._dataset_cache[key] = dataset
        return dataset


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _apply_filters(
    event: DiscoveryEvent,
    dataset: DiscoveryDataset,
    filter_fns: list[tuple[str, FilterFn]],
    filter_datasets: dict[str, DiscoveryDataset],
) -> bool:
    for label, filt in filter_fns:
        filter_dataset = filter_datasets.get(label, dataset)
        filter_event = _event_with_dataset_metadata(event, filter_dataset)
        try:
            result = filt(filter_event, filter_dataset)
        except Exception:
            logger.debug(
                "Filter raised for event %s; skipping event", event.event_id, exc_info=True
            )
            return False
        if not result.passed:
            return False
    return True


def _event_with_dataset_metadata(
    event: DiscoveryEvent, dataset: DiscoveryDataset
) -> DiscoveryEvent:
    if event.event_time not in dataset.ohlcv.index or event.event_time not in dataset.features.index:
        return event
    metadata = dict(event.metadata)
    primary_row = dataset.ohlcv.loc[event.event_time]
    feature_row = dataset.features.loc[event.event_time]
    metadata.update(
        {
            "close": float(primary_row["close"]),
            "volume": float(primary_row["volume"]),
            "hour_utc": int(pd.Timestamp(event.event_time).hour),
        }
    )
    for key, value in feature_row.items():
        metadata[str(key)] = value
    return replace(event, metadata=metadata)


def _align_filter_datasets(
    *,
    dataset: DiscoveryDataset,
    filter_instances: tuple[DSSInstance, ...],
    filter_datasets: dict[str, DiscoveryDataset],
) -> dict[str, DiscoveryDataset]:
    aligned: dict[str, DiscoveryDataset] = {}
    for instance in filter_instances:
        label = instance.label
        source = filter_datasets.get(label)
        if source is None:
            aligned[label] = dataset
            continue
        aligned[label] = align_discovery_dataset_asof(source, pd.DatetimeIndex(dataset.ohlcv.index))
    return aligned


def _atr_at(primary: pd.DataFrame, bar_time: pd.Timestamp, window: int = 14) -> float | None:
    """Wilder ATR at bar_time on closed candles only.

    Returns None when there are insufficient bars or price data is missing.
    ATR = 0 is treated as invalid and returns None so the caller can discard.
    """
    if bar_time not in primary.index:
        return None
    idx = primary.index.get_loc(bar_time)
    if idx < 1:
        return None
    sl = primary.iloc[:idx] if idx < window else primary.iloc[idx - window : idx]

    if sl.empty:
        return None

    prev_close = sl["close"].shift(1)
    tr = pd.concat(
        [
            sl["high"] - sl["low"],
            (sl["high"] - prev_close).abs(),
            (sl["low"] - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)

    result = float(tr.mean())
    return result if result > 0 else None


def _empty_signal_df() -> pd.DataFrame:
    return pd.DataFrame(columns=_SIGNAL_ROW_COLUMNS)


def signal_df_to_ohlcv_aligned(
    signal_df: pd.DataFrame,
    primary: pd.DataFrame,
) -> pd.DataFrame:
    """Convert SignalRow DataFrame to OHLCV-aligned format for the backtester.

    ``ExecutionSim`` requires ``open``, ``high``, ``low``, ``close``, ``signal``,
    and ``sl_price`` on the same index as the primary OHLCV frame.

    Multiple signals at the same bar are resolved by keeping the last one
    (arbitrary but deterministic).
    """
    ohlcv_cols = [c for c in ("open", "high", "low", "close", "volume") if c in primary.columns]
    out = primary.loc[:, ohlcv_cols].copy()
    out["signal"] = 0
    out["sl_price"] = 0.0
    out["entry_price"] = float("nan")
    if signal_df.empty:
        return out

    signal_df = signal_df.copy()
    signal_df["bar_time"] = pd.to_datetime(signal_df["bar_time"], utc=True)

    for _, row in signal_df.iterrows():
        bt = row["bar_time"]
        if bt not in out.index:
            continue
        sig = 1 if row["side"] == "long" else -1
        out.at[bt, "signal"] = sig
        out.at[bt, "sl_price"] = float(row["stop_price"])
        out.at[bt, "entry_price"] = float("nan")

    return out
