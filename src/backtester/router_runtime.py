"""Causal promoted-router replay primitives.

This module prepares all archived strategy signals from one shared feature
dataset, then exposes them bar-by-bar to the router replay. It never invokes a
nested backtest or a nested full-history strategy ``generate`` method.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd
from tqdm.auto import tqdm

from backtester.data_contracts import StrategyData, StrategyInput
from backtester.incremental_strategy import (
    IncrementalStrategyConfig,
    build_incremental_adapter,
)
from backtester.strategies import (
    crypt_ensemble_incremental as _crypt_ensemble_incremental,
)
from backtester.strategies import dss_incremental as _dss_incremental
from backtester.strategy_discovery.features import build_discovery_dataset

_BUILTIN_ADAPTER_MODULES = (
    _crypt_ensemble_incremental,
    _dss_incremental,
)


@dataclass(frozen=True, slots=True)
class ArchivedStrategySpec:
    """One archived strategy's signal and execution configuration."""

    strategy_id: str
    name: str
    params: dict[str, Any]
    execution: Any


@dataclass(frozen=True, slots=True)
class RouterBarDecision:
    """Composite signal selected for one closed primary bar."""

    timestamp: pd.Timestamp
    selected_strategy: str
    row: dict[str, Any]


@dataclass(slots=True)
class RouterRuntimeState:
    """Serializable chronological state shared by replay and live adapters."""

    last_timestamp: pd.Timestamp | None = None
    selected_strategy: str = ""
    processed_bars: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "last_timestamp": (
                self.last_timestamp.isoformat() if self.last_timestamp is not None else None
            ),
            "selected_strategy": self.selected_strategy,
            "processed_bars": self.processed_bars,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> RouterRuntimeState:
        raw_timestamp = payload.get("last_timestamp")
        timestamp = pd.Timestamp(raw_timestamp) if raw_timestamp is not None else None
        return cls(
            last_timestamp=timestamp,
            selected_strategy=str(payload.get("selected_strategy", "")),
            processed_bars=int(payload.get("processed_bars", 0)),
        )


class RouterReplayRuntime:
    """Expose prepared causal strategy rows through one-bar state transitions."""

    def __init__(
        self,
        *,
        frames: dict[str, pd.DataFrame],
        specs: dict[str, ArchivedStrategySpec],
        router_id: str,
        state: RouterRuntimeState | None = None,
    ) -> None:
        self._frames = frames
        self._specs = specs
        self._router_id = router_id
        self.state = state or RouterRuntimeState()

    def on_closed_bar(
        self,
        *,
        timestamp: pd.Timestamp,
        selected_strategy: str,
    ) -> RouterBarDecision:
        timestamp = pd.Timestamp(timestamp)
        previous = self.state.last_timestamp
        if previous is not None:
            if timestamp == previous:
                raise ValueError(f"Duplicate closed bar: {timestamp.isoformat()}")
            if timestamp < previous:
                raise ValueError(
                    "Closed bars must be strictly increasing: "
                    f"{timestamp.isoformat()} <= {previous.isoformat()}"
                )
        if selected_strategy not in self._frames:
            raise ValueError(f"Router selected unknown strategy: {selected_strategy}")
        frame = self._frames[selected_strategy]
        if timestamp not in frame.index:
            raise ValueError(f"Strategy frame missing closed bar: {timestamp.isoformat()}")
        spec = self._specs[selected_strategy]
        signal_row = frame.loc[timestamp]
        args = spec.execution
        row = {
            "signal": int(signal_row.get("signal", 0)),
            "sl_price": float(signal_row.get("sl_price", 0.0)),
            "entry_price": signal_row.get("entry_price", float("nan")),
            "risk_percent": args.risk_percent,
            "rrr": args.rrr,
            "position_ttl_bars": args.ttl,
            "trail_activation_rrr": args.trail_activation_rrr,
            "trail_distance_atr": args.trail_distance_atr,
            "exit_geometry": args.exit_geometry,
            "tp_move_pct": (args.tp_move_pct if args.tp_move_pct is not None else float("nan")),
            "structural_sl_mode": args.structural_sl_mode,
            "min_tp_move_pct": args.min_tp_move_pct,
            "router_id": self._router_id,
            "selected_strategy": selected_strategy,
            "position_group": selected_strategy,
            "drain_on_group_change": True,
        }
        self.state.last_timestamp = timestamp
        self.state.selected_strategy = selected_strategy
        self.state.processed_bars += 1
        return RouterBarDecision(
            timestamp=timestamp,
            selected_strategy=selected_strategy,
            row=row,
        )


def build_archived_signal_frames(
    *,
    data: StrategyInput,
    specs: list[ArchivedStrategySpec],
) -> dict[str, pd.DataFrame]:
    """Build all six archived signal streams from one shared feature dataset."""

    symbol = str(data.metadata.get("symbol", "")) if isinstance(data, StrategyData) else ""
    dataset = build_discovery_dataset(
        data=data,
        window_label="promoted_router",
        symbol=symbol,
    )
    output: dict[str, pd.DataFrame] = {}
    for spec in specs:
        adapter = build_incremental_adapter(spec.name)
        output[spec.strategy_id] = adapter.prepare_replay(
            data=data,
            dataset=dataset,
            config=IncrementalStrategyConfig(
                strategy_id=spec.strategy_id,
                params=spec.params,
                execution=spec.execution,
            ),
        )
    return output


def replay_selected_signals(
    *,
    primary: pd.DataFrame,
    selected: pd.Series,
    frames: dict[str, pd.DataFrame],
    specs: dict[str, ArchivedStrategySpec],
    router_id: str,
    progress: bool,
) -> pd.DataFrame:
    """Multiplex prepared causal signals in one chronological router pass."""

    output = primary.copy()
    output["signal"] = 0
    output["sl_price"] = 0.0
    output["risk_percent"] = 1.0
    output["rrr"] = 2.0
    output["position_ttl_bars"] = 0
    output["trail_activation_rrr"] = 0.0
    output["trail_distance_atr"] = 0.0
    output["exit_geometry"] = "sl_rrr"
    output["tp_move_pct"] = float("nan")
    output["structural_sl_mode"] = "cap"
    output["min_tp_move_pct"] = 0.004
    output["position_group"] = selected
    output["drain_on_group_change"] = True
    output["router_id"] = router_id
    output["selected_strategy"] = selected

    runtime = RouterReplayRuntime(
        frames=frames,
        specs=specs,
        router_id=router_id,
    )
    rows: list[RouterBarDecision] = []
    selected_items = tqdm(
        selected.items(),
        total=len(selected),
        desc="promoted_router replay",
        unit="bar",
        disable=not progress,
    )
    for timestamp, strategy_id in selected_items:
        rows.append(
            runtime.on_closed_bar(
                timestamp=pd.Timestamp(timestamp),
                selected_strategy=str(strategy_id),
            )
        )

    if any("entry_price" in decision.row for decision in rows):
        output["entry_price"] = float("nan")
    for decision in rows:
        for column, value in decision.row.items():
            output.at[decision.timestamp, column] = value
    return output
