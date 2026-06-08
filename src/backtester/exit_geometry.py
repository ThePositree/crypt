from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

ExitGeometryMode = Literal["sl_rrr", "tp_pct"]
StructuralSlMode = Literal["cap", "ignore", "reject"]


@dataclass(frozen=True, slots=True)
class ExitGeometryConfig:
    mode: ExitGeometryMode = "sl_rrr"
    tp_move_pct: float | None = None
    structural_sl_mode: StructuralSlMode = "cap"
    min_tp_move_pct: float = 0.004

    def __post_init__(self) -> None:
        if self.mode not in ("sl_rrr", "tp_pct"):
            msg = f"Unsupported exit geometry mode: {self.mode!r}"
            raise ValueError(msg)
        if self.structural_sl_mode not in ("cap", "ignore", "reject"):
            msg = f"Unsupported structural_sl_mode: {self.structural_sl_mode!r}"
            raise ValueError(msg)
        if self.mode == "tp_pct" and self.tp_move_pct is None:
            raise ValueError("tp_move_pct is required when exit_geometry mode is tp_pct")
        if self.tp_move_pct is not None and self.tp_move_pct <= 0:
            raise ValueError("tp_move_pct must be > 0")
        if self.min_tp_move_pct <= 0:
            raise ValueError("min_tp_move_pct must be > 0")


@dataclass(frozen=True, slots=True)
class ResolvedExitLevels:
    sl_price: float
    tp_price: float
    sl_dist: float
    tp_dist: float
    effective_rrr: float
    structural_sl_capped: bool


def exit_geometry_config_from_args(
    *,
    exit_geometry: str,
    tp_move_pct: float | None,
    structural_sl_mode: str = "cap",
    min_tp_move_pct: float = 0.004,
) -> ExitGeometryConfig:
    mode = exit_geometry.strip().lower()
    if mode not in ("sl_rrr", "tp_pct"):
        msg = f"Unsupported exit_geometry: {exit_geometry!r}"
        raise ValueError(msg)
    structural_mode = structural_sl_mode.strip().lower()
    if structural_mode not in ("cap", "ignore", "reject"):
        msg = f"Unsupported structural_sl_mode: {structural_sl_mode!r}"
        raise ValueError(msg)
    return ExitGeometryConfig(
        mode=mode,  # type: ignore[arg-type]
        tp_move_pct=tp_move_pct,
        structural_sl_mode=structural_mode,  # type: ignore[arg-type]
        min_tp_move_pct=min_tp_move_pct,
    )


def resolve_exit_levels(
    *,
    signal: int,
    entry_price: float,
    structural_sl_price: float,
    rrr: float,
    config: ExitGeometryConfig,
) -> ResolvedExitLevels | None:
    if signal not in (1, -1):
        return None
    if rrr <= 0:
        return None

    is_long = signal == 1
    if config.mode == "sl_rrr":
        return _resolve_sl_rrr(
            entry_price=entry_price,
            structural_sl_price=structural_sl_price,
            rrr=rrr,
            is_long=is_long,
        )
    assert config.tp_move_pct is not None
    return _resolve_tp_pct(
        entry_price=entry_price,
        structural_sl_price=structural_sl_price,
        rrr=rrr,
        tp_move_pct=config.tp_move_pct,
        structural_sl_mode=config.structural_sl_mode,
        min_tp_move_pct=config.min_tp_move_pct,
        is_long=is_long,
    )


def _resolve_sl_rrr(
    *,
    entry_price: float,
    structural_sl_price: float,
    rrr: float,
    is_long: bool,
) -> ResolvedExitLevels | None:
    sl_dist = _structural_sl_dist(
        entry_price=entry_price,
        structural_sl_price=structural_sl_price,
        is_long=is_long,
    )
    if sl_dist is None:
        return None
    tp_dist = sl_dist * rrr
    if is_long:
        tp_price = entry_price + tp_dist
        sl_price = entry_price - sl_dist
    else:
        tp_price = entry_price - tp_dist
        sl_price = entry_price + sl_dist
    return ResolvedExitLevels(
        sl_price=sl_price,
        tp_price=tp_price,
        sl_dist=sl_dist,
        tp_dist=tp_dist,
        effective_rrr=rrr,
        structural_sl_capped=False,
    )


def _resolve_tp_pct(
    *,
    entry_price: float,
    structural_sl_price: float,
    rrr: float,
    tp_move_pct: float,
    structural_sl_mode: StructuralSlMode,
    min_tp_move_pct: float,
    is_long: bool,
) -> ResolvedExitLevels | None:
    if tp_move_pct < min_tp_move_pct:
        return None

    tp_dist = entry_price * tp_move_pct
    derived_sl_dist = tp_dist / rrr
    structural_dist = _structural_sl_dist(
        entry_price=entry_price,
        structural_sl_price=structural_sl_price,
        is_long=is_long,
    )

    if structural_sl_mode == "ignore":
        sl_dist = derived_sl_dist
        structural_sl_capped = False
    elif structural_dist is None:
        if structural_sl_mode == "reject":
            return None
        sl_dist = derived_sl_dist
        structural_sl_capped = False
    elif structural_sl_mode == "reject" and derived_sl_dist > structural_dist:
        return None
    elif structural_sl_mode == "cap":
        sl_dist = min(derived_sl_dist, structural_dist)
        structural_sl_capped = sl_dist < derived_sl_dist - 1e-12
    else:
        sl_dist = derived_sl_dist
        structural_sl_capped = False

    if sl_dist <= 0:
        return None

    if is_long:
        tp_price = entry_price + tp_dist
        sl_price = entry_price - sl_dist
    else:
        tp_price = entry_price - tp_dist
        sl_price = entry_price + sl_dist

    effective_rrr = tp_dist / sl_dist
    return ResolvedExitLevels(
        sl_price=sl_price,
        tp_price=tp_price,
        sl_dist=sl_dist,
        tp_dist=tp_dist,
        effective_rrr=effective_rrr,
        structural_sl_capped=structural_sl_capped,
    )


def _structural_sl_dist(
    *,
    entry_price: float,
    structural_sl_price: float,
    is_long: bool,
) -> float | None:
    if is_long:
        sl_dist = entry_price - structural_sl_price
    else:
        sl_dist = structural_sl_price - entry_price
    if sl_dist <= 0:
        return None
    return sl_dist
