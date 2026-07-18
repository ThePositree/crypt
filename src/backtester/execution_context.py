from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from backtester.data_contracts import StrategyData, StrategyInput

EXECUTION_CONTEXT_METADATA_KEY = "execution_context"


@dataclass(frozen=True, slots=True)
class StrategyExecutionContext:
    """Donor execution flags propagated from CLI / optimizer into strategy.generate."""

    exit_geometry: str = "sl_rrr"
    tp_move_pct: float | None = None
    structural_sl_mode: str = "cap"
    min_tp_move_pct: float = 0.004

    def __post_init__(self) -> None:
        mode = self.exit_geometry.strip().lower()
        if mode not in ("sl_rrr", "tp_pct"):
            msg = f"Unsupported exit_geometry: {self.exit_geometry!r}"
            raise ValueError(msg)
        structural_mode = self.structural_sl_mode.strip().lower()
        if structural_mode not in ("cap", "ignore", "reject"):
            msg = f"Unsupported structural_sl_mode: {self.structural_sl_mode!r}"
            raise ValueError(msg)
        if self.min_tp_move_pct <= 0:
            raise ValueError("min_tp_move_pct must be > 0")

    @property
    def skips_structural_entry_gate(self) -> bool:
        return self.exit_geometry == "tp_pct"

    @classmethod
    def from_metadata(cls, metadata: dict[str, Any]) -> StrategyExecutionContext | None:
        raw = metadata.get(EXECUTION_CONTEXT_METADATA_KEY)
        if raw is None:
            return None
        if isinstance(raw, StrategyExecutionContext):
            return raw
        if isinstance(raw, dict):
            return cls(
                exit_geometry=str(raw.get("exit_geometry", "sl_rrr")),
                tp_move_pct=raw.get("tp_move_pct"),
                structural_sl_mode=str(raw.get("structural_sl_mode", "cap")),
                min_tp_move_pct=float(raw.get("min_tp_move_pct", 0.004)),
            )
        return None

    def cache_key_payload(self) -> dict[str, Any]:
        return {
            "exit_geometry": self.exit_geometry,
            "structural_sl_mode": self.structural_sl_mode,
        }


def execution_context_from_run_kwargs(
    *,
    exit_geometry: str = "sl_rrr",
    tp_move_pct: float | None = None,
    structural_sl_mode: str = "cap",
    min_tp_move_pct: float = 0.004,
) -> StrategyExecutionContext:
    return StrategyExecutionContext(
        exit_geometry=exit_geometry,
        tp_move_pct=tp_move_pct,
        structural_sl_mode=structural_sl_mode,
        min_tp_move_pct=min_tp_move_pct,
    )


def attach_execution_context(
    data: StrategyInput,
    context: StrategyExecutionContext,
) -> StrategyInput:
    if isinstance(data, StrategyData):
        metadata = dict(data.metadata)
        metadata[EXECUTION_CONTEXT_METADATA_KEY] = context
        return StrategyData(
            primary=data.primary,
            candles=data.candles,
            extras=data.extras,
            metadata=metadata,
        )
    frame = data.copy()
    frame.attrs[EXECUTION_CONTEXT_METADATA_KEY] = context
    return frame


def read_execution_context(data: StrategyInput) -> StrategyExecutionContext | None:
    if isinstance(data, StrategyData):
        return StrategyExecutionContext.from_metadata(data.metadata)
    raw = data.attrs.get(EXECUTION_CONTEXT_METADATA_KEY)
    if raw is None:
        return None
    if isinstance(raw, StrategyExecutionContext):
        return raw
    if isinstance(raw, dict):
        return StrategyExecutionContext.from_metadata({EXECUTION_CONTEXT_METADATA_KEY: raw})
    return None
