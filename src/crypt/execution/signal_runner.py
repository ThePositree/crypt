"""Live signal runner for backtester strategies.

The runner loads the same strategy JSON and calls the same ``generate`` method
as historical backtests. Its live-specific job is only to refresh closed
Parquet candles and expose the latest closed-bar entry events.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pandas as pd

from backtester.cli_runner import build_strategy_instance, load_strategy_config
from backtester.data_loader import CryptParquetDataLoader
from backtester.strategy import BaseStrategy
from crypt.data.store import ParquetStore
from crypt.exchange.okx import OKXClient
from crypt.models import Timeframe

logger = logging.getLogger(__name__)

_MAX_DATA_STALENESS = timedelta(hours=3)
_REFRESH_TIMEFRAMES = (Timeframe.H1, Timeframe.H4, Timeframe.D1)


@dataclass(frozen=True)
class SignalEvent:
    """One actionable event emitted by a closed signal bar."""

    bar_time: datetime
    signal: int
    sl_price: float
    next_open: float
    rrr: float | None
    risk_percent: float | None
    position_ttl_bars: int | None
    trail_activation_rrr: float | None
    trail_distance_atr: float | None
    exit_geometry: str | None
    tp_move_pct: float | None
    structural_sl_mode: str | None
    min_tp_move_pct: float | None
    selected_strategy: str
    position_group: str
    raw_event: dict[str, Any]
    drain_on_group_change: bool = False


@dataclass(frozen=True)
class SignalBatch:
    """All actionable events emitted by one closed bar."""

    bar_time: datetime
    next_time: datetime
    next_open: float
    events: list[SignalEvent]


class LiveSignalRunner:
    """Refresh live data and run a backtester registry strategy."""

    def __init__(
        self,
        strategy_config_path: Path,
        data_dir: Path,
        okx_client: OKXClient,
    ) -> None:
        self._data_dir = data_dir
        self._okx = okx_client
        self._store = ParquetStore(data_dir)
        self._next_open_by_symbol: dict[str, tuple[datetime, float]] = {}

        cfg = load_strategy_config(str(strategy_config_path), logger)
        if cfg is None:
            raise ValueError(f"Invalid strategy config: {strategy_config_path}")

        params = dict(cfg.params)
        params["progress"] = False
        strategy = build_strategy_instance(cfg.name, params, logger=logger)
        if strategy is None:
            raise ValueError(f"Unsupported strategy config: {strategy_config_path}")

        self._strategy: BaseStrategy = strategy
        self._strategy_name = cfg.name
        self._strategy_version = cfg.version

        logger.info(
            "LiveSignalRunner initialized with strategy %s version '%s'",
            self._strategy_name,
            self._strategy_version,
        )

    async def refresh_candles(self, symbol: str) -> None:
        """Fetch and store any new closed bars from OKX for the given symbol."""
        for tf in _REFRESH_TIMEFRAMES:
            candles = await self._okx.fetch_ohlcv(symbol, tf, limit=100)
            closed = [c for c in candles if c.closed]
            if tf == Timeframe.H1:
                forming = [c for c in candles if not c.closed]
                if forming:
                    first_forming = sorted(forming, key=lambda c: c.open_time)[0]
                    self._next_open_by_symbol[symbol] = (
                        first_forming.open_time.astimezone(UTC),
                        float(first_forming.o),
                    )
            if not closed:
                continue
            try:
                self._store.save_candles(closed)
                logger.debug(
                    "Refreshed %d closed %s bars for %s",
                    len(closed),
                    tf.value,
                    symbol,
                )
            except Exception:
                logger.exception("Failed to save candles for %s %s", symbol, tf.value)

    def get_latest_signal_batch(self, symbol: str) -> SignalBatch | None:
        """Return latest closed-bar events using backtester next-open semantics."""
        if not self._check_data_freshness(symbol):
            return None

        try:
            loader = CryptParquetDataLoader(
                data_dir=str(self._data_dir),
                symbol=symbol,
                primary_timeframe="1h",
            )
            strategy_data = loader.load()
        except Exception:
            logger.exception("Failed to load strategy data for %s", symbol)
            return None

        try:
            logger.info("Running %s.generate() for %s", self._strategy_name, symbol)
            signal_df = self._strategy.generate(strategy_data)
        except Exception:
            logger.exception("%s.generate() failed for %s", self._strategy_name, symbol)
            return None

        if signal_df.empty:
            logger.info("%s.generate() returned an empty signal frame for %s", self._strategy_name, symbol)
            return None

        row = signal_df.iloc[-1]
        bar_time = _timestamp_to_utc(signal_df.index[-1])
        next_open_info = self._next_open_by_symbol.get(symbol)
        if next_open_info is None:
            logger.warning(
                "No current forming H1 open for %s after refresh — skipping entries",
                symbol,
            )
            return None
        next_time, next_open = next_open_info
        if next_time <= bar_time:
            logger.warning(
                "Current H1 open %s is not after signal bar %s for %s — skipping",
                next_time.isoformat(),
                bar_time.isoformat(),
                symbol,
            )
            return None
        if next_open <= 0:
            logger.warning("No valid next_open for %s at %s", symbol, bar_time.isoformat())
            return None

        events = [
            event
            for raw in _events_from_row(row)
            if (event := _signal_event_from_raw(bar_time, next_open, raw)) is not None
        ]
        if not events:
            logger.info("No actionable events for %s at closed H1 bar %s", symbol, bar_time.isoformat())
            return None

        logger.info(
            "Signal batch for %s: events=%d bar_time=%s next_time=%s next_open=%.4f",
            symbol,
            len(events),
            bar_time.isoformat(),
            next_time.isoformat(),
            next_open,
        )
        return SignalBatch(
            bar_time=bar_time,
            next_time=next_time,
            next_open=next_open,
            events=events,
        )

    def get_latest_signal(self, symbol: str) -> SignalEvent | None:
        """Backward-compatible helper returning the first event in a batch."""
        batch = self.get_latest_signal_batch(symbol)
        if batch is None:
            return None
        return batch.events[0] if batch.events else None

    def _check_data_freshness(self, symbol: str) -> bool:
        h1_df = self._store.load_candles(symbol, Timeframe.H1, limit=1)
        if h1_df.empty:
            logger.warning("No H1 data for %s — skipping signal generation", symbol)
            return False

        last_bar_time = _timestamp_to_utc(h1_df["open_time"].iloc[-1])
        age = datetime.now(UTC) - last_bar_time
        if age > _MAX_DATA_STALENESS:
            logger.warning(
                "H1 data for %s is %.1f hours old (max %.0f h) — skipping",
                symbol,
                age.total_seconds() / 3600,
                _MAX_DATA_STALENESS.total_seconds() / 3600,
            )
            return False
        return True


def _timestamp_to_utc(raw: Any) -> datetime:
    if isinstance(raw, pd.Timestamp):
        ts = raw.tz_localize(UTC) if raw.tzinfo is None else raw
        dt: datetime = ts.to_pydatetime(warn=False)
        return dt.astimezone(UTC)
    if isinstance(raw, datetime):
        return raw.replace(tzinfo=UTC) if raw.tzinfo is None else raw.astimezone(UTC)
    return datetime.now(UTC)


def _events_from_row(row: pd.Series) -> list[dict[str, Any]]:
    raw_events = row.get("signal_events")
    if isinstance(raw_events, list):
        return [dict(event) for event in raw_events if isinstance(event, dict)]

    signal = int(row.get("signal", 0))
    if signal not in (1, -1):
        return []
    sl_price = float(row.get("sl_price", float("nan")))
    if pd.isna(sl_price) or sl_price <= 0:
        return []

    event: dict[str, Any] = {"signal": signal, "sl_price": sl_price}
    for key in (
        "rrr",
        "risk_percent",
        "position_ttl_bars",
        "trail_activation_rrr",
        "trail_distance_atr",
        "exit_geometry",
        "tp_move_pct",
        "structural_sl_mode",
        "min_tp_move_pct",
        "selected_strategy",
        "position_group",
        "drain_on_group_change",
    ):
        if key in row.index and not pd.isna(row[key]):
            value = row[key]
            event[key] = value.item() if hasattr(value, "item") else value
    return [event]


def _signal_event_from_raw(
    bar_time: datetime,
    next_open: float,
    raw: dict[str, Any],
) -> SignalEvent | None:
    signal = int(raw.get("signal", 0))
    if signal not in (1, -1):
        return None
    sl_price = float(raw.get("sl_price", float("nan")))
    if pd.isna(sl_price) or sl_price <= 0:
        return None
    return SignalEvent(
        bar_time=bar_time,
        signal=signal,
        sl_price=sl_price,
        next_open=next_open,
        rrr=_optional_float(raw, "rrr"),
        risk_percent=_optional_float(raw, "risk_percent"),
        position_ttl_bars=_optional_int(raw, "position_ttl_bars"),
        trail_activation_rrr=_optional_float(raw, "trail_activation_rrr"),
        trail_distance_atr=_optional_float(raw, "trail_distance_atr"),
        exit_geometry=_optional_str(raw, "exit_geometry"),
        tp_move_pct=_optional_float(raw, "tp_move_pct"),
        structural_sl_mode=_optional_str(raw, "structural_sl_mode"),
        min_tp_move_pct=_optional_float(raw, "min_tp_move_pct"),
        selected_strategy=str(raw.get("selected_strategy", "")),
        position_group=str(raw.get("position_group", raw.get("selected_strategy", ""))),
        drain_on_group_change=bool(raw.get("drain_on_group_change", False)),
        raw_event=dict(raw),
    )


def _optional_float(raw: dict[str, Any], key: str) -> float | None:
    value = raw.get(key)
    if value is None or pd.isna(value):
        return None
    return float(value)


def _optional_int(raw: dict[str, Any], key: str) -> int | None:
    value = raw.get(key)
    if value is None or pd.isna(value):
        return None
    return int(value)


def _optional_str(raw: dict[str, Any], key: str) -> str | None:
    value = raw.get(key)
    if value is None or pd.isna(value):
        return None
    return str(value)
