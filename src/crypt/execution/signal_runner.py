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
from time import perf_counter
from typing import Any

import pandas as pd

from backtester.cli_runner import build_strategy_instance, load_strategy_config
from backtester.data_loader import CryptParquetDataLoader
from backtester.strategy import BaseStrategy
from backtester.trailing_policy import latest_entry_atr14
from crypt.data.store import ParquetStore
from crypt.exchange.okx import OKXClient
from crypt.models import Timeframe
from crypt.runtime.h1_websocket import H1Boundary

logger = logging.getLogger(__name__)

_MAX_DATA_STALENESS = timedelta(hours=3)
_REFRESH_TIMEFRAMES = (Timeframe.H1, Timeframe.H4, Timeframe.D1)
_TIMEFRAME_DELTA = {
    Timeframe.H1: timedelta(hours=1),
    Timeframe.H4: timedelta(hours=4),
    Timeframe.D1: timedelta(days=1),
}


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
    trail_entry_atr: float | None = None


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

    async def refresh_candles(
        self,
        symbol: str,
        websocket_boundary: H1Boundary | None = None,
    ) -> None:
        """Fetch and store any new closed bars from OKX for the given symbol."""
        if websocket_boundary is not None:
            if websocket_boundary.symbol != symbol:
                raise ValueError(
                    f"WebSocket boundary symbol {websocket_boundary.symbol} does not match {symbol}"
                )
            closed_by_timeframe: dict[Timeframe, list[Any]] = {}
            for candle in websocket_boundary.closed_candles:
                closed_by_timeframe.setdefault(candle.timeframe, []).append(candle)
            for candles in closed_by_timeframe.values():
                self._store.save_candles(candles)
            self._next_open_by_symbol[symbol] = (
                websocket_boundary.boundary_time,
                websocket_boundary.next_open,
            )
            for tf in _REFRESH_TIMEFRAMES:
                await self._validate_or_repair_continuity(symbol, tf)
            self._next_open_by_symbol[symbol] = (
                websocket_boundary.boundary_time,
                websocket_boundary.next_open,
            )
            logger.info(
                "Ingested OKX WebSocket boundary for %s at %s: closed=%s next_open=%.4f",
                symbol,
                websocket_boundary.boundary_time.isoformat(),
                [candle.timeframe.value for candle in websocket_boundary.closed_candles],
                websocket_boundary.next_open,
            )
            return
        for tf in _REFRESH_TIMEFRAMES:
            await self._refresh_timeframe(symbol, tf)
            self._validate_continuity(symbol, tf)

    async def _refresh_timeframe(self, symbol: str, tf: Timeframe) -> None:
        stored = self._store.load_candles(symbol, tf)
        since_ms = _refresh_since_ms(stored, tf)

        total_closed = 0
        for _ in range(1000):
            candles = await self._okx.fetch_ohlcv(
                symbol,
                tf,
                limit=300,
                since_ms=since_ms,
            )
            if not candles:
                if not stored.empty and tf is not Timeframe.H1:
                    logger.warning(
                        "OKX returned no %s candles for %s; keeping existing stored history",
                        tf.value,
                        symbol,
                    )
                    break
                raise RuntimeError(f"OKX returned no {tf.value} candles for {symbol}")

            closed = [c for c in candles if c.closed]
            forming = [c for c in candles if not c.closed]
            if closed:
                try:
                    self._store.save_candles(closed)
                except Exception as exc:
                    logger.exception("Failed to save candles for %s %s", symbol, tf.value)
                    raise RuntimeError(
                        f"failed to save refreshed {tf.value} candles for {symbol}"
                    ) from exc
                total_closed += len(closed)

            if tf == Timeframe.H1 and forming:
                first_forming = min(forming, key=lambda candle: candle.open_time)
                self._next_open_by_symbol[symbol] = (
                    first_forming.open_time.astimezone(UTC),
                    float(first_forming.o),
                )

            newest = max(candle.open_time for candle in candles)
            next_since_ms = int((newest + _TIMEFRAME_DELTA[tf]).timestamp() * 1000)
            if forming or next_since_ms <= (since_ms or 0):
                break
            since_ms = next_since_ms
        else:
            raise RuntimeError(f"{tf.value} candle refresh exceeded page limit for {symbol}")

        logger.info(
            "Refreshed %d closed %s bars for %s",
            total_closed,
            tf.value,
            symbol,
        )

    async def _validate_or_repair_continuity(self, symbol: str, tf: Timeframe) -> None:
        try:
            self._validate_continuity(symbol, tf)
        except RuntimeError as exc:
            logger.warning(
                "%s continuity check failed for %s after WebSocket ingest; repairing via REST: %s",
                tf.value,
                symbol,
                exc,
            )
            await self._refresh_timeframe(symbol, tf)
            self._validate_continuity(symbol, tf)

    def _validate_continuity(self, symbol: str, tf: Timeframe) -> None:
        frame = self._store.load_candles(symbol, tf)
        if frame.empty:
            raise RuntimeError(f"no stored {tf.value} candles for {symbol}")
        timestamps = (
            pd.to_datetime(frame["open_time"], utc=True).sort_values().reset_index(drop=True)
        )
        gaps = timestamps.diff() > _TIMEFRAME_DELTA[tf]
        if gaps.any():
            first_gap_index = int(gaps[gaps].index[0])
            gap_end = timestamps.iloc[first_gap_index]
            gap_start = timestamps.iloc[first_gap_index - 1]
            raise RuntimeError(
                f"{tf.value} candle gap for {symbol}: "
                f"{gap_start.isoformat()} -> {gap_end.isoformat()}"
            )

    def get_latest_signal_batch(self, symbol: str) -> SignalBatch | None:
        """Return latest closed-bar events using backtester next-open semantics."""
        if not self._check_data_freshness(symbol):
            raise RuntimeError(f"H1 data for {symbol} is missing or stale")

        try:
            loader = CryptParquetDataLoader(
                data_dir=str(self._data_dir),
                symbol=symbol,
                primary_timeframe="1h",
            )
            strategy_data = loader.load()
        except Exception as exc:
            logger.exception("Failed to load strategy data for %s", symbol)
            raise RuntimeError(f"failed to load strategy data for {symbol}") from exc

        try:
            logger.info("Running %s.generate() for %s", self._strategy_name, symbol)
            started_at = perf_counter()
            generate_latest = getattr(self._strategy, "generate_latest", None)
            if callable(generate_latest):
                signal_df = generate_latest(strategy_data)
                generation_mode = "latest-cache"
            else:
                signal_df = self._strategy.generate(strategy_data)
                generation_mode = "full"
            logger.info(
                "%s signal generation completed for %s in %.3fs mode=%s",
                self._strategy_name,
                symbol,
                perf_counter() - started_at,
                generation_mode,
            )
        except Exception as exc:
            logger.exception("%s.generate() failed for %s", self._strategy_name, symbol)
            raise RuntimeError(f"{self._strategy_name}.generate() failed for {symbol}") from exc

        if signal_df.empty:
            logger.info(
                "%s.generate() returned an empty signal frame for %s", self._strategy_name, symbol
            )
            raise RuntimeError(
                f"{self._strategy_name}.generate() returned an empty signal frame for {symbol}"
            )

        row = signal_df.iloc[-1]
        bar_time = _timestamp_to_utc(signal_df.index[-1])
        primary = strategy_data.primary
        primary_through_signal = primary.loc[primary.index <= pd.Timestamp(bar_time)]
        trail_entry_atr = latest_entry_atr14(primary_through_signal)
        next_open_info = self._next_open_by_symbol.get(symbol)
        if next_open_info is None:
            logger.warning(
                "No current forming H1 open for %s after refresh — skipping entries",
                symbol,
            )
            raise RuntimeError(f"current forming H1 open is unavailable for {symbol}")
        next_time, next_open = next_open_info
        if next_time <= bar_time:
            logger.warning(
                "Current H1 open %s is not after signal bar %s for %s — skipping",
                next_time.isoformat(),
                bar_time.isoformat(),
                symbol,
            )
            raise RuntimeError(f"forming H1 time is not after the signal bar for {symbol}")
        if next_open <= 0:
            logger.warning("No valid next_open for %s at %s", symbol, bar_time.isoformat())
            raise RuntimeError(f"forming H1 open price is invalid for {symbol}")

        events = [
            event
            for raw in _events_from_row(row)
            if (
                event := _signal_event_from_raw(
                    bar_time,
                    next_open,
                    raw,
                    trail_entry_atr=trail_entry_atr,
                )
            )
            is not None
        ]
        if not events:
            logger.info(
                "No actionable events for %s at closed H1 bar %s", symbol, bar_time.isoformat()
            )
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
    try:
        ts = pd.Timestamp(raw)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"cannot parse timestamp as UTC datetime: {raw!r}") from exc
    if pd.isna(ts):
        raise ValueError(f"cannot parse timestamp as UTC datetime: {raw!r}")
    ts = ts.tz_localize(UTC) if ts.tzinfo is None else ts
    dt: datetime = ts.to_pydatetime(warn=False)
    return dt.astimezone(UTC)


def _refresh_since_ms(stored: pd.DataFrame, tf: Timeframe) -> int | None:
    """Start at the first missing bar, or immediately after the latest bar."""
    if stored.empty:
        return None
    timestamps = pd.to_datetime(stored["open_time"], utc=True).sort_values().reset_index(drop=True)
    gaps = timestamps.diff() > _TIMEFRAME_DELTA[tf]
    if gaps.any():
        first_gap_index = int(gaps[gaps].index[0])
        start = _timestamp_to_utc(timestamps.iloc[first_gap_index - 1]) + _TIMEFRAME_DELTA[tf]
    else:
        start = _timestamp_to_utc(timestamps.iloc[-1]) + _TIMEFRAME_DELTA[tf]
    return int(start.timestamp() * 1000)


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
    *,
    trail_entry_atr: float | None = None,
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
        trail_entry_atr=trail_entry_atr,
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
