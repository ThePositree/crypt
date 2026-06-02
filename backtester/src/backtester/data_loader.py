import logging
import os
from abc import ABC, abstractmethod
from datetime import datetime
from hashlib import sha256
from pathlib import Path
from typing import Any

import pandas as pd
import requests

from backtester.data_contracts import StrategyData, StrategyInput


class BaseDataLoader(ABC):
    """
    Abstract base class for OHLCV data loaders.

    All concrete implementations must return a standardized
    OHLCV :class:`pandas.DataFrame` with a :class:`pandas.DatetimeIndex`
    and ``['open', 'high', 'low', 'close', 'volume']`` columns. Project-aware
    loaders may return :class:`backtester.data_contracts.StrategyData`.
    """

    def __init__(self) -> None:
        self._logger = logging.getLogger(__name__)

    @abstractmethod
    def load(self) -> StrategyInput:
        """
        Load OHLCV data from the underlying source.

        Returns
        -------
        pandas.DataFrame | StrategyData
            DataFrame with DatetimeIndex and at least the following
            columns: ``open``, ``high``, ``low``, ``close``, ``volume``; or a
            StrategyData object whose primary frame follows the same contract.

        Raises
        ------
        ValueError
            If data is empty or required columns are missing.
        TypeError
            If the index is not a :class:`pandas.DatetimeIndex`.
        """

    def _rename_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Standardize column names to OHLCV format.

        Parameters
        ----------
        df : pandas.DataFrame
            Input DataFrame with potential column name variations.

        Returns
        -------
        pandas.DataFrame
            DataFrame with standardized column names.

        Raises
        ------
        ValueError
            If required OHLCV columns cannot be identified.
        """
        mapping = {
            "open": ["open", "Open", "OPEN", "o"],
            "high": ["high", "High", "HIGH", "h"],
            "low": ["low", "Low", "LOW", "l"],
            "close": ["close", "Close", "CLOSE", "price", "c"],
            "volume": ["volume", "Volume", "VOLUME", "vol", "v"],
        }

        renamed: dict[str, str] = {}

        for target, variants in mapping.items():
            for col in variants:
                if col in df.columns:
                    if target not in renamed:
                        renamed[target] = col
                    break

        if not renamed.get("open") or not renamed.get("close"):
            raise ValueError("Data must contain at least 'open' and 'close' columns")

        rename_dict = {v: k for k, v in renamed.items()}
        df.rename(columns=rename_dict, inplace=True)

        if "volume" not in df.columns:
            df["volume"] = 0.0

        return df

    def _default_validator(self, df: pd.DataFrame) -> None:
        """
        Perform basic validation on OHLCV data.

        Parameters
        ----------
        df : pandas.DataFrame
            DataFrame to validate.

        Raises
        ------
        ValueError
            If DataFrame is empty or required columns are missing.
        TypeError
            If index is not :class:`pandas.DatetimeIndex`.
        """
        if df.empty:
            raise ValueError("DataFrame is empty")

        if not isinstance(df.index, pd.DatetimeIndex):
            raise TypeError("Index must be DatetimeIndex")

        required = ["open", "high", "low", "close", "volume"]
        for col in required:
            if col not in df.columns:
                msg = f"Missing required column: {col}"
                raise ValueError(msg)

        if df.isnull().any().any():
            self._logger.warning("NaN values detected. Filling with pad method")
            df.ffill(inplace=True)

    def _standardize_ohlcv_frame(
        self,
        df: pd.DataFrame,
        *,
        timestamp_col: str | None = None,
    ) -> pd.DataFrame:
        frame = df.copy()
        frame = self._rename_columns(frame)

        if isinstance(frame.index, pd.DatetimeIndex):
            frame.index = pd.to_datetime(frame.index, utc=True)
        else:
            candidate = timestamp_col
            if candidate not in frame.columns:
                candidate = None
            for col in ("timestamp", "open_time", "time", "ts"):
                if candidate is None and col in frame.columns:
                    candidate = col
                    break
            if candidate is None or candidate not in frame.columns:
                raise ValueError(
                    "Data must contain a DatetimeIndex or timestamp/open_time column"
                )
            frame[candidate] = pd.to_datetime(frame[candidate], utc=True)
            frame.set_index(candidate, inplace=True)

        frame.sort_index(inplace=True)
        frame = frame[~frame.index.duplicated(keep="last")]
        self._default_validator(frame)
        return frame[["open", "high", "low", "close", "volume"]]


class CsvDataLoader(BaseDataLoader):
    """
    Load OHLCV data from a CSV file.

    Parameters
    ----------
    filepath : str
        Path to CSV file.
    timestamp_col : str, default \"timestamp\"
        Column name containing timestamps.
    time_format : str, optional
        Optional datetime format string for parsing.
    index_col : str, optional
        Optional column name to use as index (instead of timestamp).
    """

    def __init__(
        self,
        filepath: str,
        timestamp_col: str = "timestamp",
        time_format: str | None = None,
        index_col: str | None = None,
    ) -> None:
        super().__init__()
        self.filepath = filepath
        self.timestamp_col = timestamp_col
        self.time_format = time_format
        self.index_col = index_col

    def load(self) -> pd.DataFrame:
        """
        Load data from CSV file and return a standardized OHLCV DataFrame.

        Returns
        -------
        pandas.DataFrame
            Processed OHLCV DataFrame.

        Raises
        ------
        FileNotFoundError
            If the CSV file does not exist.
        ValueError
            If the timestamp column is missing.
        """
        if not os.path.exists(self.filepath):
            raise FileNotFoundError(f"File not found: {self.filepath}")

        df = pd.read_csv(self.filepath)
        df = self._rename_columns(df)

        if self.timestamp_col not in df.columns:
            msg = f"Timestamp column '{self.timestamp_col}' not found"
            raise ValueError(msg)

        if self.time_format:
            df[self.timestamp_col] = pd.to_datetime(
                df[self.timestamp_col],
                format=self.time_format,
            )
        else:
            df[self.timestamp_col] = pd.to_datetime(df[self.timestamp_col])

        df.set_index(self.timestamp_col, inplace=True)
        df.sort_index(inplace=True)

        if self.index_col and self.index_col != self.timestamp_col:
            df = df.reset_index().set_index(self.index_col)

        self._default_validator(df)
        return df


class DataFrameDataLoader(BaseDataLoader):
    """
    Wrap an in-memory :class:`pandas.DataFrame` with OHLCV data.

    Parameters
    ----------
    df : pandas.DataFrame
        Input DataFrame with OHLCV data.
    timestamp_col : str, default \"timestamp\"
        Column name containing timestamps.
    """

    def __init__(self, df: pd.DataFrame, timestamp_col: str = "timestamp") -> None:
        super().__init__()
        if not isinstance(df, pd.DataFrame):
            raise TypeError("Input must be pandas DataFrame")
        self._df = df.copy()
        self.timestamp_col = timestamp_col

    def load(self) -> pd.DataFrame:
        """
        Convert user-provided DataFrame to standardized OHLCV format.

        Returns
        -------
        pandas.DataFrame
            Standardized OHLCV DataFrame.

        Raises
        ------
        ValueError
            If the timestamp column is missing.
        """
        if self.timestamp_col not in self._df.columns:
            msg = f"Expected timestamp column '{self.timestamp_col}'"
            raise ValueError(msg)

        df = self._rename_columns(self._df)

        df[self.timestamp_col] = pd.to_datetime(df[self.timestamp_col])
        df.set_index(self.timestamp_col, inplace=True)
        df.sort_index(inplace=True)

        self._default_validator(df)
        return df


class ParquetDataLoader(BaseDataLoader):
    """Load one OHLCV Parquet file into the donor DataFrame contract."""

    def __init__(self, filepath: str, timestamp_col: str | None = None) -> None:
        super().__init__()
        self.filepath = filepath
        self.timestamp_col = timestamp_col

    def load(self) -> pd.DataFrame:
        if not os.path.exists(self.filepath):
            raise FileNotFoundError(f"File not found: {self.filepath}")

        df = pd.read_parquet(self.filepath)
        return self._standardize_ohlcv_frame(df, timestamp_col=self.timestamp_col)


class CryptParquetDataLoader(BaseDataLoader):
    """Load the crypt project Parquet layout for one symbol."""

    def __init__(
        self, data_dir: str, symbol: str, primary_timeframe: str = "4h"
    ) -> None:
        super().__init__()
        self.data_dir = data_dir
        self.symbol = symbol
        self.primary_timeframe = primary_timeframe

    def _load_candles(self, store: Any, timeframe: Any) -> pd.DataFrame:
        raw = store.load_candles(self.symbol, timeframe)
        if raw.empty:
            return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])
        return self._standardize_ohlcv_frame(raw, timestamp_col="open_time")

    def load(self) -> StrategyData:
        try:
            from crypt.data.store import ParquetStore
            from crypt.models import Timeframe
        except ImportError as exc:  # pragma: no cover - environment dependent
            raise RuntimeError(
                "crypt-parquet data source requires the parent crypt package "
                "on PYTHONPATH"
            ) from exc

        store = ParquetStore(Path(self.data_dir))
        h4 = self._load_candles(store, Timeframe.H4)
        if h4.empty:
            raise ValueError(
                f"crypt-parquet requires H4 candles for symbol {self.symbol!r}"
            )

        candles = {
            "H4": h4,
            "H1": self._load_candles(store, Timeframe.H1),
            "D1": self._load_candles(store, Timeframe.D1),
        }
        primary_key = _timeframe_key(self.primary_timeframe)
        if primary_key not in candles:
            raise ValueError(
                "crypt-parquet primary_timeframe must be one of: 1h, 4h, 1d"
            )
        primary = candles[primary_key]
        if primary.empty:
            raise ValueError(
                "crypt-parquet requires non-empty "
                f"{primary_key} candles for primary_timeframe"
            )

        extras = {
            "oi": store.load_oi(self.symbol),
            "ls_ratio": store.load_ls_ratio(self.symbol),
            "taker_volume": store.load_taker_volume(self.symbol),
        }

        return StrategyData(
            primary=primary,
            candles=candles,
            extras=extras,
            metadata={
                "symbol": self.symbol,
                "exchange": "OKX",
                "primary_timeframe": primary_key,
            },
        )


# Max klines per request for BingX (API limit).
_BINGX_KLINES_LIMIT = 1440


def _bingx_interval_to_ms(interval: str) -> int:
    """Convert BingX interval string (e.g. '1m', '1h') to milliseconds."""
    unit = interval[-1].lower()
    try:
        n = int(interval[:-1])
    except ValueError:
        raise ValueError(f"Invalid BingX interval: {interval!r}") from None
    if unit == "m":
        return n * 60 * 1000
    if unit == "h":
        return n * 3600 * 1000
    if unit == "d":
        return n * 24 * 3600 * 1000
    if unit == "w":
        return n * 7 * 24 * 3600 * 1000
    raise ValueError(f"Unknown interval unit: {unit!r}")


class BingxApiDataLoader(BaseDataLoader):
    """
    Load OHLCV data from the BingX Swap Kline/Candlestick REST API.

    This loader uses the ``/openApi/swap/v3/quote/klines`` endpoint,
    fetches the full range [start_time, end_time] in batches (API max 1440
    per request). The API returns data from newest to oldest, so iteration
    proceeds by decreasing end_time after each batch. Returns a standardized
    OHLCV :class:`pandas.DataFrame`.

    Parameters
    ----------
    symbol : str
        Trading pair symbol, e.g. ``\"BTC-USDT\"`` (note the hyphen).
    interval : str
        Kline interval supported by BingX, e.g. ``\"1m\"``, ``\"1h\"``.
    start_time : int
        Start timestamp in milliseconds since epoch (required).
    end_time : int
        End timestamp in milliseconds since epoch (required).
    api_key : str, optional
        BingX API key. Required.
    api_secret : str, optional
        BingX API secret used for request signing. Required.
    base_url : str, default \"https://open-api.bingx.com\"
        Base URL of the BingX API.
    time_zone : int, default 0
        Time zone offset; BingX supports 0 and 8.
    recv_window : int, default 30_000
        Request valid time window value in milliseconds.
    cache_dir : str, optional
        Optional directory path for on-disk caching. When provided, successful
        responses are stored as pickled :class:`pandas.DataFrame` instances and
        subsequent calls with the same parameters will be served from the cache
        without additional API requests. Cache entries do not expire
        automatically and must be invalidated manually by removing files.
    """

    _PATH = "/openApi/swap/v3/quote/klines"

    def __init__(
        self,
        symbol: str,
        interval: str,
        *,
        start_time: int,
        end_time: int,
        api_key: str | None = None,
        api_secret: str | None = None,
        base_url: str = "https://open-api.bingx.com",
        time_zone: int = 0,
        recv_window: int = 30_000,
        cache_dir: str | None = None,
    ) -> None:
        super().__init__()
        self.symbol = symbol
        self.interval = interval
        self.start_time = start_time
        self.end_time = end_time
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = base_url.rstrip("/")
        self.time_zone = time_zone
        self.recv_window = recv_window
        self.cache_dir = cache_dir

        if self.cache_dir is not None:
            os.makedirs(self.cache_dir, exist_ok=True)

    def _build_params(
        self,
        batch_end: int,
    ) -> dict[str, Any]:
        if self.api_key is None or self.api_secret is None:
            msg = "BingxApiDataLoader requires 'api_key' and 'api_secret'"
            raise ValueError(msg)

        params: dict[str, Any] = {
            "symbol": self.symbol,
            "interval": self.interval,
            "timeZone": self.time_zone,
            "limit": str(_BINGX_KLINES_LIMIT),
            "startTime": str(self.start_time),
            "endTime": str(batch_end),
        }
        return params

    def _cache_key(self) -> str:
        """
        Build a stable cache key string based on business parameters.

        The key intentionally does not include authentication credentials and is
        suitable for deriving a filesystem-safe file name via hashing.
        """
        parts = [
            f"symbol={self.symbol}",
            f"interval={self.interval}",
            f"start_time={self.start_time}",
            f"end_time={self.end_time}",
            f"base_url={self.base_url}",
            f"time_zone={self.time_zone}",
            f"recv_window={self.recv_window}",
        ]
        return "|".join(parts)

    def _cache_path(self) -> str | None:
        """Return absolute path to the cache file for current parameters."""
        if self.cache_dir is None:
            return None

        key = self._cache_key()
        digest = sha256(key.encode("utf-8")).hexdigest()
        filename = f"{digest}.pkl"
        return os.path.join(self.cache_dir, filename)

    def _sign(self, params: dict[str, Any]) -> tuple[str, str]:
        """Create BingX-compatible query string and signature."""
        import time
        import urllib.parse

        assert self.api_secret is not None

        sorted_keys = sorted(params)
        params_list: list[str] = []
        url_params_list: list[str] = []
        for key in sorted_keys:
            value = params[key]
            params_list.append(f"{key}={value}")

        timestamp = str(int(time.time() * 1000))
        params_str = "&".join(params_list)
        if params_str:
            params_str = f"{params_str}&timestamp={timestamp}"
        else:
            params_str = f"timestamp={timestamp}"

        contains_complex = "[" in params_str or "{" in params_str
        for key in sorted_keys:
            value = params[key]
            if contains_complex:
                encoded_value = urllib.parse.quote(str(value), safe="")
            else:
                encoded_value = str(value)
            url_params_list.append(f"{key}={encoded_value}")

        url_params_str = "&".join(url_params_list)
        if url_params_str:
            url_params_str = f"{url_params_str}&timestamp={timestamp}"
        else:
            url_params_str = f"timestamp={timestamp}"

        signature = self._hmac_sha256(self.api_secret, params_str)
        return url_params_str, signature

    @staticmethod
    def _hmac_sha256(secret: str, payload: str) -> str:
        import hmac

        signature = hmac.new(
            secret.encode("utf-8"),
            payload.encode("utf-8"),
            digestmod=sha256,
        ).hexdigest()
        return signature

    def _fetch_one_batch(self, batch_end_ms: int) -> list[dict[str, Any]]:
        """Request one batch of klines from BingX (up to _BINGX_KLINES_LIMIT)."""
        params = self._build_params(batch_end_ms)
        url_params_str, signature = self._sign(params)
        url = f"{self.base_url}{self._PATH}?{url_params_str}&signature={signature}"

        headers = {"X-BX-APIKEY": self.api_key or ""}
        self._logger.debug("Requesting BingX klines batch up to end %s", batch_end_ms)
        response = requests.get(url, headers=headers, timeout=30)

        if not response.ok:
            msg = f"BingX HTTP error {response.status_code}: {response.text}"
            raise RuntimeError(msg)

        payload = response.json()
        if not isinstance(payload, dict) or "code" not in payload:
            raise ValueError("Unexpected BingX response format")

        if payload.get("code") != 0:
            msg = f"BingX API error {payload.get('code')}: {payload.get('msg')}"
            raise RuntimeError(msg)

        data = payload.get("data", [])
        if not isinstance(data, list):
            raise ValueError("Unexpected BingX 'data' format")

        return data

    def load(self) -> pd.DataFrame:
        """
        Fetch OHLCV data from BingX for [start_time, end_time] in batches.

        Returns
        -------
        pandas.DataFrame
            Standardized OHLCV DataFrame.

        Raises
        ------
        RuntimeError
            If the HTTP request fails or BingX returns an error code.
        ValueError
            If the response format is unexpected or no data in range.
        """
        cache_path = self._cache_path()
        if cache_path is not None and os.path.exists(cache_path):
            self._logger.info("Loading BingX data from cache file %s", cache_path)
            try:
                df = pd.read_pickle(cache_path)
                self._default_validator(df)
                return df
            except Exception as exc:  # pragma: no cover - defensive
                self._logger.warning(
                    "Failed to load or validate BingX cache file %s, refetching: %s",
                    cache_path,
                    exc,
                )

        interval_ms = _bingx_interval_to_ms(self.interval)
        all_rows: list[dict[str, Any]] = []
        current_end = self.end_time

        while current_end >= self.start_time:
            batch = self._fetch_one_batch(current_end)
            if not batch:
                break

            all_rows.extend(batch)
            min_ts = min(row["time"] for row in batch)
            self._logger.debug(
                "Fetched %d rows from BingX, total rows: %d, oldest in batch: %s",
                len(batch),
                len(all_rows),
                datetime.fromtimestamp(min_ts / 1000).strftime("%Y-%m-%d %H:%M:%S"),
            )

            # Defensive guard: if the API returns klines at or beyond the
            # requested batch end, further pagination would never advance
            # and could lead to an infinite loop. Stop fetching in this case.
            if min_ts >= current_end:
                if min_ts > current_end:
                    self._logger.warning(
                        "BingX returned klines newer than requested end %s "
                        "(oldest in batch: %s); stopping pagination to avoid "
                        "an infinite loop.",
                        datetime.fromtimestamp(current_end / 1000).strftime(
                            "%Y-%m-%d %H:%M:%S"
                        ),
                        datetime.fromtimestamp(min_ts / 1000).strftime(
                            "%Y-%m-%d %H:%M:%S"
                        ),
                    )
                break

            if min_ts <= self.start_time:
                break
            current_end = min_ts - interval_ms

        if not all_rows:
            raise ValueError(
                "No data returned from BingX for the given start_time/end_time range"
            )

        df = pd.DataFrame(all_rows)
        df["time"] = pd.to_datetime(df["time"], unit="ms")
        df.rename(columns={"time": "timestamp"}, inplace=True)
        df.set_index("timestamp", inplace=True)
        df = df[~df.index.duplicated(keep="first")]
        df.sort_index(inplace=True)
        df = df.astype(float, copy=False)

        df = self._rename_columns(df)
        self._default_validator(df)
        if cache_path is not None:
            try:
                pd.to_pickle(df, cache_path)
            except Exception as exc:  # pragma: no cover - defensive
                self._logger.warning(
                    "Failed to write BingX cache file %s: %s",
                    cache_path,
                    exc,
                )

        return df


class DataLoader(BaseDataLoader):
    """
    Backwards-compatible facade over concrete data loaders.

    Supports:

    - :meth:`from_csv` for CSV files;
    - :meth:`from_dataframe` for in-memory :class:`pandas.DataFrame`.
    """

    def load(self) -> pd.DataFrame:  # pragma: no cover - not used directly
        msg = (
            "DataLoader is a facade; call 'from_csv' or 'from_dataframe' "
            "or use a concrete subclass like CsvDataLoader instead."
        )
        raise NotImplementedError(msg)

    def from_csv(
        self,
        filepath: str,
        timestamp_col: str = "timestamp",
        time_format: str | None = None,
        index_col: str | None = None,
    ) -> pd.DataFrame:
        """
        Load data from CSV file.

        This method preserves the original public API while internally
        delegating to :class:`CsvDataLoader`.

        Parameters
        ----------
        filepath : str
            Path to CSV file.
        timestamp_col : str, default \"timestamp\"
            Column name containing timestamps.
        time_format : str, optional
            Optional datetime format string for parsing.
        index_col : str, optional
            Optional column name to use as index (instead of timestamp).

        Returns
        -------
        pandas.DataFrame
            Processed OHLCV DataFrame.
        """
        loader = CsvDataLoader(
            filepath=filepath,
            timestamp_col=timestamp_col,
            time_format=time_format,
            index_col=index_col,
        )
        return loader.load()

    def from_dataframe(
        self,
        df: pd.DataFrame,
        timestamp_col: str = "timestamp",
    ) -> pd.DataFrame:
        """
        Convert user-provided DataFrame to standardized format.

        Parameters
        ----------
        df : pandas.DataFrame
            Input DataFrame with OHLCV data.
        timestamp_col : str, default \"timestamp\"
            Column name containing timestamps.

        Returns
        -------
        pandas.DataFrame
            Standardized OHLCV DataFrame.
        """
        loader = DataFrameDataLoader(df=df, timestamp_col=timestamp_col)
        return loader.load()


def create_data_loader(source: str, **kwargs: Any) -> BaseDataLoader:
    """
    Factory for creating concrete data loader instances.

    Parameters
    ----------
    source : str
        Data source identifier. Supported values:

        - ``\"csv\"`` - returns :class:`CsvDataLoader`
        - ``\"dataframe\"`` - returns :class:`DataFrameDataLoader`
        - ``\"bingx\"`` - returns :class:`BingxApiDataLoader`

    **kwargs : Any
        Keyword arguments forwarded to the concrete loader constructor.

    Returns
    -------
    BaseDataLoader
        Instance of a concrete data loader.

    Raises
    ------
    ValueError
        If the source value is unsupported.
    """
    normalized = source.lower()
    if normalized == "csv":
        return CsvDataLoader(**kwargs)
    if normalized == "dataframe":
        return DataFrameDataLoader(**kwargs)
    if normalized == "bingx":
        return BingxApiDataLoader(**kwargs)
    if normalized == "parquet":
        return ParquetDataLoader(**kwargs)
    if normalized == "crypt-parquet":
        return CryptParquetDataLoader(**kwargs)

    msg = f"Unsupported data source: {source!r}"
    raise ValueError(msg)


def _timeframe_key(value: str) -> str:
    normalized = str(value).strip().lower()
    aliases = {
        "h1": "H1",
        "1h": "H1",
        "h4": "H4",
        "4h": "H4",
        "d1": "D1",
        "1d": "D1",
    }
    return aliases.get(normalized, str(value).strip().upper())
