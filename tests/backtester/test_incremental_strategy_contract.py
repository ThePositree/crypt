from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import numpy as np
import pandas as pd
import pytest

from backtester.data_contracts import StrategyData
from backtester.execution_context import (
    StrategyExecutionContext,
    attach_execution_context,
)
from backtester.incremental_strategy import (
    IncrementalStrategyConfig,
    build_incremental_adapter,
)
from backtester.registry import STRATEGIES
from backtester.strategies import (
    crypt_ensemble_incremental as _crypt_ensemble_incremental,
)
from backtester.strategies import dss_incremental as _dss_incremental
from backtester.strategy_discovery.features import build_discovery_dataset

_BUILTIN_ADAPTER_MODULES = (
    _crypt_ensemble_incremental,
    _dss_incremental,
)


def _primary(periods: int = 360) -> pd.DataFrame:
    index = pd.date_range("2024-01-01", periods=periods, freq="h", tz="UTC")
    phase = np.arange(periods, dtype=float)
    close = 100.0 + np.sin(phase / 9.0) * 3.0 + phase * 0.01
    open_ = close - np.sin(phase / 3.0) * 0.4
    return pd.DataFrame(
        {
            "open": open_,
            "high": np.maximum(open_, close) + 0.8 + (phase % 7) * 0.03,
            "low": np.minimum(open_, close) - 0.8 - (phase % 5) * 0.02,
            "close": close,
            "volume": 1_000.0 + (phase % 24) * 20.0,
        },
        index=index,
    )


def _strategy_data(primary: pd.DataFrame) -> StrategyData:
    aggregations = {
        "open": "first",
        "high": "max",
        "low": "min",
        "close": "last",
        "volume": "sum",
    }
    return StrategyData(
        primary=primary,
        candles={
            "H1": primary,
            "H4": primary.resample("4h").agg(aggregations).dropna(),
            "D1": primary.resample("1D").agg(aggregations).dropna(),
        },
        extras={},
        metadata={"symbol": "SOL-USDT-SWAP"},
    )


def _portfolio_configs() -> list[tuple[str, dict[str, object]]]:
    router = json.loads(Path("strategies/archive/router_v2_2687609.json").read_text())
    configs: list[tuple[str, dict[str, object]]] = []
    for strategy_id, raw_path in router["params"]["strategy_paths"].items():
        payload = json.loads(Path(raw_path).read_text())
        configs.append((strategy_id, payload))
    return configs


def _mapping(payload: dict[str, object], key: str) -> dict[str, Any]:
    value = payload.get(key, {})
    if not isinstance(value, dict):
        raise TypeError(f"{key} must be a mapping")
    return value


@pytest.mark.parametrize(
    ("strategy_id", "payload"),
    _portfolio_configs(),
    ids=lambda value: str(value) if isinstance(value, str) else None,
)
def test_registered_strategy_adapter_contract(
    strategy_id: str,
    payload: dict[str, object],
) -> None:
    full_primary = _primary()
    prefix_primary = full_primary.iloc[:300].copy()
    full_data = _strategy_data(full_primary)
    prefix_data = _strategy_data(prefix_primary)
    adapter = build_incremental_adapter(str(payload["name"]))
    execution = SimpleNamespace()
    config = IncrementalStrategyConfig(
        strategy_id=strategy_id,
        params=_mapping(payload, "params"),
        execution=execution,
    )

    full = adapter.prepare_replay(
        data=full_data,
        dataset=build_discovery_dataset(
            data=full_data,
            window_label="contract",
            symbol="SOL-USDT-SWAP",
        ),
        config=config,
    )
    prefix = adapter.prepare_replay(
        data=prefix_data,
        dataset=build_discovery_dataset(
            data=prefix_data,
            window_label="contract",
            symbol="SOL-USDT-SWAP",
        ),
        config=config,
    )

    assert full.index.equals(full_primary.index)
    assert {"signal", "sl_price"}.issubset(full.columns)
    assert set(full["signal"].dropna().astype(int).unique()).issubset({-1, 0, 1})
    pd.testing.assert_series_equal(
        full.loc[prefix.index, "signal"],
        prefix["signal"],
    )
    actionable = prefix["signal"].ne(0)
    np.testing.assert_allclose(
        full.loc[prefix.index[actionable], "sl_price"].to_numpy(),
        prefix.loc[actionable, "sl_price"].to_numpy(),
        rtol=0,
        atol=1e-10,
    )


@pytest.mark.parametrize(
    ("strategy_id", "payload"),
    _portfolio_configs(),
    ids=lambda value: str(value) if isinstance(value, str) else None,
)
def test_registered_adapter_matches_canonical_strategy_rows(
    strategy_id: str,
    payload: dict[str, object],
) -> None:
    primary = _primary(periods=120)
    data = _strategy_data(primary)
    backtest_args = _mapping(payload, "backtest_args")
    canonical_input = attach_execution_context(
        data,
        StrategyExecutionContext(
            exit_geometry=str(backtest_args.get("exit_geometry", "sl_rrr")),
            tp_move_pct=backtest_args.get("tp_move_pct"),
            structural_sl_mode=str(backtest_args.get("structural_sl_mode", "cap")),
            min_tp_move_pct=float(backtest_args.get("min_tp_move_pct", 0.004)),
        ),
    )
    strategy = STRATEGIES[str(payload["name"])](_mapping(payload, "params"))
    canonical = strategy.generate(canonical_input).reset_index(drop=True)

    adapter = build_incremental_adapter(str(payload["name"]))
    adapted = adapter.prepare_replay(
        data=canonical_input,
        dataset=build_discovery_dataset(
            data=canonical_input,
            window_label="canonical-parity",
            symbol="SOL-USDT-SWAP",
        ),
        config=IncrementalStrategyConfig(
            strategy_id=strategy_id,
            params=_mapping(payload, "params"),
            execution=SimpleNamespace(),
        ),
    ).reset_index(drop=True)

    pd.testing.assert_series_equal(
        adapted["signal"].astype(int),
        canonical["signal"].astype(int),
        check_names=False,
    )
    actionable = canonical["signal"].astype(int).ne(0)
    np.testing.assert_allclose(
        adapted.loc[actionable, "sl_price"].to_numpy(),
        canonical.loc[actionable, "sl_price"].to_numpy(),
        rtol=0,
        atol=1e-10,
    )
