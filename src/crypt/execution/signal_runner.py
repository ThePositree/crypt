"""LiveSignalRunner — generates crypt_ensemble signals on live Parquet data.

Runs the same `CryptEnsembleStrategy.generate()` code path as the backtester
to guarantee signal parity. The strategy is instantiated once per symbol and
reused across ticks.

The runner first appends any new closed H1/H4/D1 bars from OKX to the local
Parquet files, then loads the full history and runs `generate()`. Only the
last closed bar's signal is returned to the caller.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pandas as pd

from backtester.data_loader import CryptParquetDataLoader
from backtester.strategies.crypt_ensemble import CryptEnsembleStrategy
from crypt.data.store import ParquetStore
from crypt.exchange.okx import OKXClient
from crypt.models import Timeframe

logger = logging.getLogger(__name__)

# How stale is "too stale" — if the newest H1 bar is older than this, the
# data pipeline has failed and we skip signal generation.
_MAX_DATA_STALENESS = timedelta(hours=3)

# Timeframes to refresh before running the signal.
_REFRESH_TIMEFRAMES = (Timeframe.H1, Timeframe.H4, Timeframe.D1)


@dataclass(frozen=True)
class SignalRow:
    """A single actionable signal from the last closed bar."""

    bar_time: datetime
    signal: int          # 1 = long, -1 = short
    sl_price: float
    bar_close: float     # close price of the signal bar (entry price proxy)
    rrr: float | None    # bar-level override if present
    risk_percent: float | None


def _load_strategy_config(path: Path) -> dict[str, Any]:
    """Load strategy JSON config from disk."""
    if not path.exists():
        raise FileNotFoundError(f"Strategy config not found: {path}")
    raw = json.loads(path.read_text(encoding="utf-8"))
    return dict(raw)


class LiveSignalRunner:
    """
    Fetches fresh OKX bars, runs `crypt_ensemble.generate()`, and
    returns the last closed bar's signal if actionable.

    Parameters
    ----------
    strategy_config_path : Path
        Path to the crypt_ensemble JSON strategy config.
    data_dir : Path
        Root directory for symbol Parquet files.
    okx_client : OKXClient
        Authenticated (or public) OKX client for fetching fresh candles.
    """

    def __init__(
        self,
        strategy_config_path: Path,
        data_dir: Path,
        okx_client: OKXClient,
    ) -> None:
        self._data_dir = data_dir
        self._okx = okx_client
        self._store = ParquetStore(data_dir)

        cfg = _load_strategy_config(strategy_config_path)
        # Disable tqdm progress bar for live execution (it would spam logs).
        params = dict(cfg.get("params", {}))
        params["progress"] = False
        self._strategy = CryptEnsembleStrategy(params)
        self._strategy_version = cfg.get("version", "unknown")

        logger.info(
            "LiveSignalRunner initialized with strategy version '%s'",
            self._strategy_version,
        )

    async def refresh_candles(self, symbol: str) -> None:
        """Fetch and store any new closed bars from OKX for the given symbol."""
        for tf in _REFRESH_TIMEFRAMES:
            candles = await self._okx.fetch_ohlcv(symbol, tf, limit=100)
            closed = [c for c in candles if c.closed]
            if closed:
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

    def _check_data_freshness(self, symbol: str) -> bool:
        """
        Return True if the H1 Parquet data is recent enough to generate signals.
        Logs a WARNING and returns False if data is stale.
        """
        h1_df = self._store.load_candles(symbol, Timeframe.H1, limit=1)
        if h1_df.empty:
            logger.warning("No H1 data for %s — skipping signal generation", symbol)
            return False

        last_bar_time = pd.Timestamp(h1_df["open_time"].iloc[-1], tz=UTC)
        age = datetime.now(UTC) - last_bar_time.to_pydatetime()
        if age > _MAX_DATA_STALENESS:
            logger.warning(
                "H1 data for %s is %.1f hours old (max %.0f h) — skipping",
                symbol,
                age.total_seconds() / 3600,
                _MAX_DATA_STALENESS.total_seconds() / 3600,
            )
            return False
        return True

    def get_latest_signal(self, symbol: str) -> SignalRow | None:
        """
        Run crypt_ensemble on the full Parquet history and return the last
        closed bar's signal if it is actionable (signal != 0, sl_price valid).

        Returns None if there is no signal, the data is stale, or the
        strategy produces an error.
        """
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
            logger.debug("Running crypt_ensemble.generate() for %s", symbol)
            signal_df = self._strategy.generate(strategy_data)
        except Exception:
            logger.exception("crypt_ensemble.generate() failed for %s", symbol)
            return None

        if signal_df.empty:
            return None

        # The last row corresponds to the most recent closed H1 bar.
        last = signal_df.iloc[-1]
        sig = int(last.get("signal", 0))
        if sig not in (1, -1):
            return None

        sl = float(last.get("sl_price", float("nan")))
        if pd.isna(sl) or sl <= 0:
            logger.debug("Signal at %s has invalid sl_price=%.4f — skipping", symbol, sl)
            return None

        bar_time_raw = signal_df.index[-1]
        if isinstance(bar_time_raw, pd.Timestamp):
            bar_time = bar_time_raw.to_pydatetime(warn=False).replace(tzinfo=UTC)
        else:
            bar_time = datetime.now(UTC)

        rrr_raw = last.get("rrr")
        rrr = float(rrr_raw) if rrr_raw is not None and not pd.isna(rrr_raw) else None

        rp_raw = last.get("risk_percent")
        risk_pct = float(rp_raw) if rp_raw is not None and not pd.isna(rp_raw) else None

        # Use the primary (H1) DataFrame close price as the entry price proxy.
        # The backtester uses next bar's open; bar close is the best available
        # approximation at the time of signal generation.
        bar_close_raw = strategy_data.primary.iloc[-1]["close"] if not strategy_data.primary.empty else 0.0
        bar_close = float(bar_close_raw) if bar_close_raw else 0.0

        logger.info(
            "Signal for %s: signal=%d sl_price=%.4f close=%.4f bar_time=%s",
            symbol,
            sig,
            sl,
            bar_close,
            bar_time.isoformat(),
        )
        return SignalRow(
            bar_time=bar_time,
            signal=sig,
            sl_price=sl,
            bar_close=bar_close,
            rrr=rrr,
            risk_percent=risk_pct,
        )
