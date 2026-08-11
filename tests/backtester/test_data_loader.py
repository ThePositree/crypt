import pandas as pd
import pytest

from backtester.data_contracts import StrategyData
from backtester.data_loader import (
    BaseDataLoader,
    BingxApiDataLoader,
    CryptParquetDataLoader,
    CsvDataLoader,
    DataFrameDataLoader,
    DataLoader,
    ParquetDataLoader,
    create_data_loader,
)


def test_csv_data_loader_roundtrip(tmp_path):
    df = pd.DataFrame(
        {
            "timestamp": [
                "2024-01-01 00:00:00",
                "2024-01-01 01:00:00",
            ],
            "open": [1.0, 2.0],
            "high": [1.5, 2.5],
            "low": [0.5, 1.5],
            "close": [1.2, 2.2],
            "volume": [10, 20],
        }
    )
    path = tmp_path / "data.csv"
    df.to_csv(path, index=False)

    loader = CsvDataLoader(filepath=str(path))
    result = loader.load()

    assert isinstance(result.index, pd.DatetimeIndex)
    assert {"open", "high", "low", "close", "volume"}.issubset(result.columns)


def test_dataframe_data_loader_roundtrip():
    df = pd.DataFrame(
        {
            "timestamp": [
                "2024-01-01 00:00:00",
                "2024-01-01 01:00:00",
            ],
            "open": [1.0, 2.0],
            "high": [1.5, 2.5],
            "low": [0.5, 1.5],
            "close": [1.2, 2.2],
            "volume": [10, 20],
        }
    )

    loader = DataFrameDataLoader(df=df)
    result = loader.load()

    assert isinstance(result.index, pd.DatetimeIndex)
    assert {"open", "high", "low", "close", "volume"}.issubset(result.columns)


def test_facade_data_loader_from_csv(tmp_path):
    df = pd.DataFrame(
        {
            "timestamp": [
                "2024-01-01 00:00:00",
                "2024-01-01 01:00:00",
            ],
            "open": [1.0, 2.0],
            "high": [1.5, 2.5],
            "low": [0.5, 1.5],
            "close": [1.2, 2.2],
            "volume": [10, 20],
        }
    )
    path = tmp_path / "data.csv"
    df.to_csv(path, index=False)

    loader = DataLoader()
    result = loader.from_csv(str(path))

    assert isinstance(result.index, pd.DatetimeIndex)
    assert {"open", "high", "low", "close", "volume"}.issubset(result.columns)


def test_facade_data_loader_from_dataframe():
    df = pd.DataFrame(
        {
            "timestamp": [
                "2024-01-01 00:00:00",
                "2024-01-01 01:00:00",
            ],
            "open": [1.0, 2.0],
            "high": [1.5, 2.5],
            "low": [0.5, 1.5],
            "close": [1.2, 2.2],
            "volume": [10, 20],
        }
    )

    loader = DataLoader()
    result = loader.from_dataframe(df)

    assert isinstance(result.index, pd.DatetimeIndex)
    assert {"open", "high", "low", "close", "volume"}.issubset(result.columns)


def test_create_data_loader_factory():
    csv_loader = create_data_loader("csv", filepath="x.csv")
    assert isinstance(csv_loader, CsvDataLoader)

    df_loader = create_data_loader("dataframe", df=pd.DataFrame({"timestamp": []}))
    assert isinstance(df_loader, DataFrameDataLoader)

    bingx_loader = create_data_loader(
        "bingx",
        symbol="BTC-USDT",
        interval="1h",
        start_time=1700000000000,
        end_time=1700086400000,
        api_key="k",
        api_secret="s",
    )
    assert isinstance(bingx_loader, BingxApiDataLoader)

    parquet_loader = create_data_loader("parquet", filepath="x.parquet")
    assert isinstance(parquet_loader, ParquetDataLoader)

    crypt_loader = create_data_loader(
        "crypt-parquet",
        data_dir="/tmp/data",
        symbol="SOL-USDT-SWAP",
    )
    assert isinstance(crypt_loader, CryptParquetDataLoader)
    assert crypt_loader.candle_timeframe is None


def test_parquet_data_loader_accepts_donor_columns(tmp_path):
    df = pd.DataFrame(
        {
            "timestamp": [
                "2024-01-01 04:00:00",
                "2024-01-01 00:00:00",
            ],
            "open": [2.0, 1.0],
            "high": [2.5, 1.5],
            "low": [1.5, 0.5],
            "close": [2.2, 1.2],
            "volume": [20.0, 10.0],
        }
    )
    path = tmp_path / "donor.parquet"
    df.to_parquet(path)

    result = ParquetDataLoader(filepath=str(path), timestamp_col="timestamp").load()

    assert isinstance(result.index, pd.DatetimeIndex)
    assert list(result.columns) == ["open", "high", "low", "close", "volume"]
    assert list(result["close"]) == [1.2, 2.2]


def test_parquet_data_loader_accepts_project_columns(tmp_path):
    df = pd.DataFrame(
        {
            "open_time": [
                "2024-01-01 00:00:00+00:00",
                "2024-01-01 04:00:00+00:00",
            ],
            "o": [1.0, 2.0],
            "h": [1.5, 2.5],
            "l": [0.5, 1.5],
            "c": [1.2, 2.2],
            "v": [10.0, 20.0],
        }
    )
    path = tmp_path / "project.parquet"
    df.to_parquet(path)

    result = ParquetDataLoader(filepath=str(path)).load()

    assert isinstance(result.index, pd.DatetimeIndex)
    assert list(result.columns) == ["open", "high", "low", "close", "volume"]
    assert list(result["volume"]) == [10.0, 20.0]


def test_crypt_parquet_loader_uses_project_store_layout(monkeypatch):
    import sys
    import types

    symbol = "SOL-USDT-SWAP"
    h4 = pd.DataFrame(
        {
            "open_time": [pd.Timestamp("2024-01-01 00:00:00", tz="UTC")],
            "o": [1.0],
            "h": [1.5],
            "l": [0.5],
            "c": [1.2],
            "volume": [10.0],
        }
    )

    class FakeTimeframe:
        H4 = "H4"
        H1 = "H1"
        D1 = "D1"

    class FakeParquetStore:
        def __init__(self, data_dir):
            self.data_dir = data_dir

        def load_candles(self, loaded_symbol, timeframe):
            assert loaded_symbol == symbol
            if timeframe == FakeTimeframe.H4:
                return h4
            return pd.DataFrame(columns=["open_time", "o", "h", "l", "c", "volume"])

        def load_oi(self, loaded_symbol):
            assert loaded_symbol == symbol
            return pd.DataFrame(columns=["ts", "oi"])

        def load_ls_ratio(self, loaded_symbol):
            assert loaded_symbol == symbol
            return pd.DataFrame(columns=["ts", "long_ratio", "short_ratio"])

        def load_taker_volume(self, loaded_symbol):
            assert loaded_symbol == symbol
            return pd.DataFrame(columns=["ts", "buy_vol", "sell_vol"])

    crypt_mod = types.ModuleType("crypt")
    crypt_data_mod = types.ModuleType("crypt.data")
    crypt_store_mod = types.ModuleType("crypt.data.store")
    crypt_models_mod = types.ModuleType("crypt.models")
    crypt_store_mod.ParquetStore = FakeParquetStore
    crypt_models_mod.Timeframe = FakeTimeframe
    monkeypatch.setitem(sys.modules, "crypt", crypt_mod)
    monkeypatch.setitem(sys.modules, "crypt.data", crypt_data_mod)
    monkeypatch.setitem(sys.modules, "crypt.data.store", crypt_store_mod)
    monkeypatch.setitem(sys.modules, "crypt.models", crypt_models_mod)

    result = CryptParquetDataLoader(data_dir="/tmp/data", symbol=symbol).load()

    assert isinstance(result, StrategyData)
    assert result.metadata == {
        "symbol": symbol,
        "exchange": "OKX",
    }
    h4_frame = result.require_timeframe("H4")
    assert len(h4_frame) == 1
    assert list(h4_frame.columns) == ["open", "high", "low", "close", "volume"]
    assert result.candles_by_timeframe["H4"].equals(h4_frame)
    assert result.candles_by_timeframe["H1"].empty
    assert result.candles_by_timeframe["D1"].empty


def test_crypt_parquet_loader_can_use_h1_as_primary(monkeypatch):
    import sys
    import types

    symbol = "SOL-USDT-SWAP"
    h4 = pd.DataFrame(
        {
            "open_time": [pd.Timestamp("2024-01-01 00:00:00", tz="UTC")],
            "o": [1.0],
            "h": [1.5],
            "l": [0.5],
            "c": [1.2],
            "volume": [10.0],
        }
    )
    h1 = pd.DataFrame(
        {
            "open_time": [pd.Timestamp("2024-01-01 01:00:00", tz="UTC")],
            "o": [2.0],
            "h": [2.5],
            "l": [1.5],
            "c": [2.2],
            "volume": [20.0],
        }
    )

    class FakeTimeframe:
        H4 = "H4"
        H1 = "H1"
        D1 = "D1"

    class FakeParquetStore:
        def __init__(self, data_dir):
            self.data_dir = data_dir

        def load_candles(self, loaded_symbol, timeframe):
            assert loaded_symbol == symbol
            if timeframe == FakeTimeframe.H4:
                return h4
            if timeframe == FakeTimeframe.H1:
                return h1
            return pd.DataFrame(columns=["open_time", "o", "h", "l", "c", "volume"])

        def load_oi(self, loaded_symbol):
            assert loaded_symbol == symbol
            return pd.DataFrame(columns=["ts", "oi"])

        def load_ls_ratio(self, loaded_symbol):
            assert loaded_symbol == symbol
            return pd.DataFrame(columns=["ts", "long_ratio", "short_ratio"])

        def load_taker_volume(self, loaded_symbol):
            assert loaded_symbol == symbol
            return pd.DataFrame(columns=["ts", "buy_vol", "sell_vol"])

    crypt_mod = types.ModuleType("crypt")
    crypt_data_mod = types.ModuleType("crypt.data")
    crypt_store_mod = types.ModuleType("crypt.data.store")
    crypt_models_mod = types.ModuleType("crypt.models")
    crypt_store_mod.ParquetStore = FakeParquetStore
    crypt_models_mod.Timeframe = FakeTimeframe
    monkeypatch.setitem(sys.modules, "crypt", crypt_mod)
    monkeypatch.setitem(sys.modules, "crypt.data", crypt_data_mod)
    monkeypatch.setitem(sys.modules, "crypt.data.store", crypt_store_mod)
    monkeypatch.setitem(sys.modules, "crypt.models", crypt_models_mod)

    result = CryptParquetDataLoader(
        data_dir="/tmp/data",
        symbol=symbol,
        candle_timeframe="1h",
    ).load()

    assert result.require_timeframe("H1").equals(result.candles_by_timeframe["H1"])
    assert not result.candles_by_timeframe["H4"].empty


def test_crypt_parquet_loader_missing_primary_suggests_backfill(monkeypatch):
    import sys
    import types

    symbol = "SOL-USDT-SWAP"
    h4 = pd.DataFrame(
        {
            "open_time": [pd.Timestamp("2024-01-01 00:00:00", tz="UTC")],
            "o": [1.0],
            "h": [1.5],
            "l": [0.5],
            "c": [1.2],
            "volume": [10.0],
        }
    )

    class FakeTimeframe:
        H4 = "H4"
        H1 = "H1"
        D1 = "D1"

    class FakeParquetStore:
        def __init__(self, data_dir):
            self.data_dir = data_dir

        def load_candles(self, loaded_symbol, timeframe):
            assert loaded_symbol == symbol
            if timeframe == FakeTimeframe.H4:
                return h4
            return pd.DataFrame(columns=["open_time", "o", "h", "l", "c", "volume"])

        def load_oi(self, loaded_symbol):
            assert loaded_symbol == symbol
            return pd.DataFrame(columns=["ts", "oi"])

        def load_ls_ratio(self, loaded_symbol):
            assert loaded_symbol == symbol
            return pd.DataFrame(columns=["ts", "long_ratio", "short_ratio"])

        def load_taker_volume(self, loaded_symbol):
            assert loaded_symbol == symbol
            return pd.DataFrame(columns=["ts", "buy_vol"])

    crypt_mod = types.ModuleType("crypt")
    crypt_data_mod = types.ModuleType("crypt.data")
    crypt_store_mod = types.ModuleType("crypt.data.store")
    crypt_models_mod = types.ModuleType("crypt.models")
    crypt_store_mod.ParquetStore = FakeParquetStore
    crypt_models_mod.Timeframe = FakeTimeframe
    monkeypatch.setitem(sys.modules, "crypt", crypt_mod)
    monkeypatch.setitem(sys.modules, "crypt.data", crypt_data_mod)
    monkeypatch.setitem(sys.modules, "crypt.data.store", crypt_store_mod)
    monkeypatch.setitem(sys.modules, "crypt.models", crypt_models_mod)

    loader = CryptParquetDataLoader(
        data_dir="/tmp/data",
        symbol=symbol,
        candle_timeframe="1h",
        start="2024-01-01",
        end="2024-01-05",
    )

    with pytest.raises(ValueError, match=r"python -m crypt\.backfill") as exc_info:
        loader.load()

    message = str(exc_info.value)
    assert "--symbol SOL-USDT-SWAP" in message
    assert "--from 2024-01-01" in message
    assert "--to 2024-01-06" in message
    assert "--data-types ohlcv" in message


def test_crypt_parquet_loader_filters_candles_by_date_range(monkeypatch):
    import sys
    import types

    symbol = "SOL-USDT-SWAP"
    h4 = pd.DataFrame(
        {
            "open_time": pd.date_range(
                "2024-01-01 00:00:00",
                periods=4,
                freq="4h",
                tz="UTC",
            ),
            "o": [1.0, 2.0, 3.0, 4.0],
            "h": [1.5, 2.5, 3.5, 4.5],
            "l": [0.5, 1.5, 2.5, 3.5],
            "c": [1.2, 2.2, 3.2, 4.2],
            "volume": [10.0, 20.0, 30.0, 40.0],
        }
    )
    h1 = pd.DataFrame(
        {
            "open_time": pd.date_range(
                "2024-01-01 00:00:00",
                periods=10,
                freq="1h",
                tz="UTC",
            ),
            "o": range(10),
            "h": range(1, 11),
            "l": range(10),
            "c": range(1, 11),
            "volume": range(10, 20),
        }
    )

    class FakeTimeframe:
        H4 = "H4"
        H1 = "H1"
        D1 = "D1"

    class FakeParquetStore:
        def __init__(self, data_dir):
            self.data_dir = data_dir

        def load_candles(self, loaded_symbol, timeframe):
            assert loaded_symbol == symbol
            if timeframe == FakeTimeframe.H4:
                return h4
            if timeframe == FakeTimeframe.H1:
                return h1
            return pd.DataFrame(columns=["open_time", "o", "h", "l", "c", "volume"])

        def load_oi(self, loaded_symbol):
            assert loaded_symbol == symbol
            return pd.DataFrame(columns=["ts", "oi"])

        def load_ls_ratio(self, loaded_symbol):
            assert loaded_symbol == symbol
            return pd.DataFrame(columns=["ts", "long_ratio", "short_ratio"])

        def load_taker_volume(self, loaded_symbol):
            assert loaded_symbol == symbol
            return pd.DataFrame(columns=["ts", "buy_vol", "sell_vol"])

    crypt_mod = types.ModuleType("crypt")
    crypt_data_mod = types.ModuleType("crypt.data")
    crypt_store_mod = types.ModuleType("crypt.data.store")
    crypt_models_mod = types.ModuleType("crypt.models")
    crypt_store_mod.ParquetStore = FakeParquetStore
    crypt_models_mod.Timeframe = FakeTimeframe
    monkeypatch.setitem(sys.modules, "crypt", crypt_mod)
    monkeypatch.setitem(sys.modules, "crypt.data", crypt_data_mod)
    monkeypatch.setitem(sys.modules, "crypt.data.store", crypt_store_mod)
    monkeypatch.setitem(sys.modules, "crypt.models", crypt_models_mod)

    result = CryptParquetDataLoader(
        data_dir="/tmp/data",
        symbol=symbol,
        candle_timeframe="1h",
        start="2024-01-01 02:00:00",
        end="2024-01-01 06:00:00",
    ).load()

    assert list(result.require_timeframe("H1").index) == list(
        pd.date_range("2024-01-01 02:00:00", periods=5, freq="1h", tz="UTC")
    )
    assert list(result.candles_by_timeframe["H1"].index) == list(
        pd.date_range("2024-01-01 02:00:00", periods=5, freq="1h", tz="UTC")
    )
    assert list(result.candles_by_timeframe["H4"].index) == list(
        pd.date_range("2024-01-01 04:00:00", periods=1, freq="4h", tz="UTC")
    )


def test_base_data_loader_is_abstract():
    class Dummy(BaseDataLoader):
        def load(self):
            return pd.DataFrame()

    dummy = Dummy()
    assert isinstance(dummy, BaseDataLoader)


def test_bingx_loader_uses_file_cache(tmp_path, monkeypatch):
    # Prepare a fake BingX response payload
    fake_rows = [
        {
            # Use end_time so the batching loop terminates after a single request.
            "time": 1700003600000,
            "open": 1.0,
            "high": 1.5,
            "low": 0.5,
            "close": 1.2,
            "volume": 10.0,
        },
    ]

    class DummyResponse:
        ok = True

        def __init__(self, payload):
            self._payload = payload
            self.status_code = 200
            self.text = "OK"

        def json(self):
            return self._payload

    calls = {"count": 0}

    def fake_get(*_args, **_kwargs):
        calls["count"] += 1
        return DummyResponse({"code": 0, "data": fake_rows})

    monkeypatch.setattr("backtester.data_loader.requests.get", fake_get)

    cache_dir = tmp_path / "cache"

    loader = BingxApiDataLoader(
        symbol="BTC-USDT",
        interval="1h",
        start_time=1700000000000,
        end_time=1700003600000,
        api_key="k",
        api_secret="s",
        cache_dir=str(cache_dir),
    )

    # First call should hit the API and create a cache file.
    df1 = loader.load()
    assert not df1.empty
    assert calls["count"] == 1

    # Second loader with the same parameters should read from cache without HTTP calls.
    loader2 = BingxApiDataLoader(
        symbol="BTC-USDT",
        interval="1h",
        start_time=1700000000000,
        end_time=1700003600000,
        api_key="k",
        api_secret="s",
        cache_dir=str(cache_dir),
    )
    df2 = loader2.load()

    assert not df2.empty
    assert df1.equals(df2)
    assert calls["count"] == 1


def test_bingx_loader_without_cache_dir_does_not_touch_fs(monkeypatch):
    fake_rows = [
        {
            # Use end_time so the batching loop terminates after a single request.
            "time": 1700003600000,
            "open": 1.0,
            "high": 1.5,
            "low": 0.5,
            "close": 1.2,
            "volume": 10.0,
        },
    ]

    class DummyResponse:
        ok = True

        def __init__(self, payload):
            self._payload = payload
            self.status_code = 200
            self.text = "OK"

        def json(self):
            return self._payload

    calls = {"count": 0}

    def fake_get(*_args, **_kwargs):
        calls["count"] += 1
        return DummyResponse({"code": 0, "data": fake_rows})

    monkeypatch.setattr("backtester.data_loader.requests.get", fake_get)

    loader = BingxApiDataLoader(
        symbol="BTC-USDT",
        interval="1h",
        start_time=1700000000000,
        end_time=1700003600000,
        api_key="k",
        api_secret="s",
    )

    df = loader.load()
    assert not df.empty
    assert calls["count"] == 1
