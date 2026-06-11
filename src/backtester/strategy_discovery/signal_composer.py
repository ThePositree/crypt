"""SignalComposer — bridges a TrialConfig and the backtester.

Builds a ``generate_fn(StrategyData) -> pd.DataFrame`` from a TrialConfig.
The output schema matches the SignalRow spec in docs/discovery/signal_composer.md.

No I/O inside the returned generate function. All state is captured at build time.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import TYPE_CHECKING

import pandas as pd

from backtester.strategy_discovery.dss_config import TrialConfig
from backtester.strategy_discovery.events import DiscoveryEvent
from backtester.strategy_discovery.features import build_discovery_dataset
from backtester.strategy_discovery.parameterized_filters import parameterized_filter_catalog
from backtester.strategy_discovery.parameterized_triggers import parameterized_trigger_catalog

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

_CONTEXT_CONFIDENCE_BONUS: dict[str, float] = {
    "pf_context_aligned": 5.0,
    "pf_trend_ema_stack": 5.0,
}
_BASE_CONFIDENCE = 75.0
_MAX_CONFIDENCE = 95.0


class SignalComposer:
    """Converts a TrialConfig into a pure generate function."""

    def __init__(self) -> None:
        self._trigger_catalog = parameterized_trigger_catalog()
        self._filter_catalog = parameterized_filter_catalog()

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
        trigger_name = config.trigger_name
        if trigger_name not in self._trigger_catalog:
            available = sorted(self._trigger_catalog)
            raise ValueError(
                f"Unknown trigger_name {trigger_name!r}. Available: {available}"
            )
        for fn in config.filter_names:
            if fn not in self._filter_catalog:
                available = sorted(self._filter_catalog)
                raise ValueError(
                    f"Unknown filter_name {fn!r}. Available: {available}"
                )

        trigger_factory = self._trigger_catalog[trigger_name]
        trigger_fn = trigger_factory(config.trigger_params)

        filter_fns = [
            self._filter_catalog[fn](
                config.filter_params.get(fn, {})
            )
            for fn in config.filter_names
        ]

        rrr = config.rrr
        atr_sl_mult = config.atr_sl_mult
        filter_names_str = "+".join(config.filter_names) if config.filter_names else "no_filter"
        rationale_base = f"{trigger_name} | {filter_names_str}"

        confidence_bonus = min(
            sum(
                _CONTEXT_CONFIDENCE_BONUS.get(fn, 0.0)
                for fn in config.filter_names
            ),
            _MAX_CONFIDENCE - _BASE_CONFIDENCE,
        )
        confidence = min(_BASE_CONFIDENCE + confidence_bonus, _MAX_CONFIDENCE)

        def generate(data: StrategyInput) -> pd.DataFrame:
            from backtester.data_contracts import StrategyData

            symbol = ""
            if isinstance(data, StrategyData):
                symbol = str(data.metadata.get("symbol", ""))
            dataset = build_discovery_dataset(
                data=data,
                window_label="dss",
                symbol=symbol,
            )

            try:
                raw_events = trigger_fn(dataset)
            except Exception:
                logger.warning(
                    "Trigger %s raised during generate; returning empty DataFrame",
                    trigger_name,
                    exc_info=True,
                )
                return _empty_signal_df()

            surviving: list[dict] = []
            for event in raw_events:
                if not _apply_filters(event, dataset, filter_fns):
                    continue
                atr = _atr_at(dataset.primary, event.event_time)
                if atr is None or atr <= 0:
                    continue
                entry = event.entry_reference_price
                if event.side == "long":
                    stop = entry - atr * atr_sl_mult
                    tp = entry + (entry - stop) * rrr
                else:
                    stop = entry + atr * atr_sl_mult
                    tp = entry - (stop - entry) * rrr
                surviving.append(
                    {
                        "bar_time": event.event_time,
                        "symbol": event.symbol,
                        "side": event.side,
                        "confidence": confidence,
                        "rationale": rationale_base,
                        "entry_price": entry,
                        "stop_price": stop,
                        "tp_price": tp,
                    }
                )

            if not surviving:
                return _empty_signal_df()

            df = pd.DataFrame(surviving, columns=_SIGNAL_ROW_COLUMNS)
            df["bar_time"] = pd.to_datetime(df["bar_time"], utc=True)
            return df.sort_values("bar_time").reset_index(drop=True)

        return generate

    def validate_config(self, config: TrialConfig) -> list[str]:
        """Return a list of validation errors (empty = valid)."""
        errors: list[str] = []
        if config.trigger_name not in self._trigger_catalog:
            errors.append(f"Unknown trigger_name: {config.trigger_name!r}")
        for fn in config.filter_names:
            if fn not in self._filter_catalog:
                errors.append(f"Unknown filter_name: {fn!r}")
        return errors


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _apply_filters(event: DiscoveryEvent, dataset, filter_fns: list) -> bool:
    for filt in filter_fns:
        try:
            result = filt(event, dataset)
        except Exception:
            logger.debug("Filter raised for event %s; skipping event", event.event_id, exc_info=True)
            return False
        if not result.passed:
            return False
    return True


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
