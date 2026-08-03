"""Tests for CLI data source selection (build_cli_data_loader, load_ohlcv_via_loader)."""

import logging

import pandas as pd

from backtester.cli_runner import (
    build_cli_data_loader,
    load_ohlcv_via_loader,
    parse_utc_datetime_to_ms,
)
from backtester.data_loader import (
    BingxApiDataLoader,
    CryptParquetDataLoader,
    CsvDataLoader,
    ParquetDataLoader,
)


def test_parse_utc_datetime_to_ms():
    ms = parse_utc_datetime_to_ms("2024-01-01 00:00:00")
    assert isinstance(ms, int)
    assert ms == 1704067200000  # UTC


def test_build_cli_data_loader_csv():
    loader = build_cli_data_loader(
        "csv",
        csv_path="/tmp/sample.csv",
        ts_col="timestamp",
    )
    assert isinstance(loader, CsvDataLoader)
    assert loader.filepath == "/tmp/sample.csv"
    assert loader.timestamp_col == "timestamp"
    assert loader.time_format == "%Y-%m-%d %H:%M:%S"


def test_build_cli_data_loader_csv_missing_path_raises():
    import pytest

    with pytest.raises(ValueError, match="CSV data source requires"):
        build_cli_data_loader("csv", csv_path=None)


def test_build_cli_data_loader_bingx():
    loader = build_cli_data_loader(
        "bingx",
        bingx_symbol="BTC-USDT",
        bingx_interval="1h",
        bingx_start_time_ms=1700000000000,
        bingx_end_time_ms=1700086400000,
        bingx_api_key="key",
        bingx_api_secret="secret",
        bingx_cache_dir="/tmp/bingx-cache",
    )
    assert isinstance(loader, BingxApiDataLoader)
    assert loader.symbol == "BTC-USDT"
    assert loader.interval == "1h"
    assert loader.start_time == 1700000000000
    assert loader.end_time == 1700086400000
    assert loader.api_key == "key"
    assert loader.api_secret == "secret"
    assert loader.cache_dir == "/tmp/bingx-cache"


def test_build_cli_data_loader_bingx_missing_params_raises():
    import pytest

    with pytest.raises(ValueError, match="BingX data source requires"):
        build_cli_data_loader(
            "bingx",
            bingx_symbol="BTC-USDT",
            bingx_interval="1h",
            bingx_start_time_ms=1700000000000,
            bingx_end_time_ms=1700086400000,
            bingx_api_key=None,
            bingx_api_secret="s",
        )


def test_build_cli_data_loader_parquet():
    loader = build_cli_data_loader(
        "parquet",
        parquet_path="/tmp/sample.parquet",
        ts_col="open_time",
    )
    assert isinstance(loader, ParquetDataLoader)
    assert loader.filepath == "/tmp/sample.parquet"
    assert loader.timestamp_col == "open_time"


def test_build_cli_data_loader_parquet_missing_path_raises():
    import pytest

    with pytest.raises(ValueError, match="Parquet data source requires"):
        build_cli_data_loader("parquet", parquet_path=None)


def test_build_cli_data_loader_crypt_parquet():
    loader = build_cli_data_loader(
        "crypt-parquet",
        data_dir="/tmp/data",
        symbol="SOL-USDT-SWAP",
    )
    assert isinstance(loader, CryptParquetDataLoader)
    assert loader.data_dir == "/tmp/data"
    assert loader.symbol == "SOL-USDT-SWAP"
    assert loader.candle_timeframe is None


def test_build_cli_data_loader_crypt_parquet_candle_timeframe():
    loader = build_cli_data_loader(
        "crypt-parquet",
        data_dir="/tmp/data",
        symbol="SOL-USDT-SWAP",
        candle_timeframe="1h",
    )

    assert isinstance(loader, CryptParquetDataLoader)
    assert loader.candle_timeframe == "1h"


def test_build_cli_data_loader_crypt_parquet_date_range():
    loader = build_cli_data_loader(
        "crypt-parquet",
        data_dir="/tmp/data",
        symbol="SOL-USDT-SWAP",
        start="2024-01-01",
        end="2024-01-31 23:00:00",
    )

    assert isinstance(loader, CryptParquetDataLoader)
    assert loader.start == pd.Timestamp("2024-01-01 00:00:00", tz="UTC")
    assert loader.end == pd.Timestamp("2024-01-31 23:00:00", tz="UTC")


def test_build_cli_data_loader_crypt_parquet_full_aliases():
    loader = build_cli_data_loader(
        "crypt-parquet",
        data_dir="/tmp/data",
        symbol="SOL-USDT-SWAP",
        start="full",
        end="all",
    )

    assert isinstance(loader, CryptParquetDataLoader)
    assert loader.start is None
    assert loader.end is None


def test_build_cli_data_loader_crypt_parquet_missing_params_raises():
    import pytest

    with pytest.raises(ValueError, match="crypt-parquet data source requires"):
        build_cli_data_loader("crypt-parquet", data_dir="/tmp/data", symbol=None)


def test_build_cli_data_loader_unsupported_source_raises():
    import pytest

    with pytest.raises(ValueError, match="Unsupported data source"):
        build_cli_data_loader("invalid")


def test_load_ohlcv_via_loader_csv(tmp_path):
    df = pd.DataFrame(
        {
            "timestamp": ["2024-01-01 00:00:00", "2024-01-01 01:00:00"],
            "open": [1.0, 2.0],
            "high": [1.5, 2.5],
            "low": [0.5, 1.5],
            "close": [1.2, 2.2],
            "volume": [10, 20],
        }
    )
    path = tmp_path / "data.csv"
    df.to_csv(path, index=False)

    loader = build_cli_data_loader("csv", csv_path=str(path), ts_col="timestamp")
    logger = logging.getLogger("test")
    result = load_ohlcv_via_loader(loader, logger=logger)
    assert result is not None
    assert len(result) == 2
    assert list(result.columns) == ["open", "high", "low", "close", "volume"]
