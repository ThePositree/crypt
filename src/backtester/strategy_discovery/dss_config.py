"""DSS configuration data types.

Defines TrialConfig, DSSWindowSpec, ParamDef variants, DSSConfig and
DSSSearchSpace used across all DSS modules.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, cast

# ---------------------------------------------------------------------------
# Parameter space definitions
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class IntParam:
    low: int
    high: int
    step: int = 1


@dataclass(frozen=True, slots=True)
class FloatParam:
    low: float
    high: float
    step: float | None = None


@dataclass(frozen=True, slots=True)
class CategoricalParam:
    choices: tuple[str | int | float, ...]


ParamDef = IntParam | FloatParam | CategoricalParam

ParamValue = float | int | str
TriggerParams = dict[str, ParamValue]
FilterParams = dict[str, ParamValue]

FloatRange = tuple[float, float, float]
IntRange = tuple[int, int, int]


# ---------------------------------------------------------------------------
# Trial configuration
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class TrialConfig:
    """Immutable snapshot of everything needed to reproduce one DSS trial."""

    trigger_name: str
    trigger_params: dict[str, ParamValue]
    filter_names: tuple[str, ...]
    filter_params: dict[str, dict[str, ParamValue]]
    rrr: float
    risk_percent: float
    position_ttl_bars: int
    atr_sl_mult: float = 1.0

    @property
    def signal_cache_key(self) -> str:
        """Hash covering signal shape only (trigger + filters, not exec params)."""
        payload = {
            "trigger": self.trigger_name,
            "trigger_params": dict(sorted(self.trigger_params.items())),
            "filters": sorted(self.filter_names),
            "filter_params": {
                k: dict(sorted(v.items())) for k, v in sorted(self.filter_params.items())
            },
            "atr_sl_mult": self.atr_sl_mult,
        }
        return hashlib.sha1(json.dumps(payload, sort_keys=True).encode()).hexdigest()

    def to_dict(self) -> dict[str, object]:
        """Serialize for JSON export."""
        return {
            "trigger_name": self.trigger_name,
            "trigger_params": dict(self.trigger_params),
            "filter_names": list(self.filter_names),
            "filter_params": {k: dict(v) for k, v in self.filter_params.items()},
            "rrr": self.rrr,
            "risk_percent": self.risk_percent,
            "position_ttl_bars": self.position_ttl_bars,
            "atr_sl_mult": self.atr_sl_mult,
        }

    @classmethod
    def from_dict(cls, d: dict[str, object]) -> TrialConfig:
        """Deserialize from JSON."""
        trigger_params_raw = cast(dict[str, ParamValue], d.get("trigger_params") or {})
        filter_names_raw = cast(list[object], d.get("filter_names") or [])
        filter_params_raw = cast(
            dict[str, dict[str, ParamValue]],
            d.get("filter_params") or {},
        )
        return cls(
            trigger_name=str(d["trigger_name"]),
            trigger_params=dict(trigger_params_raw),
            filter_names=tuple(str(n) for n in filter_names_raw),
            filter_params={k: dict(v) for k, v in filter_params_raw.items()},
            rrr=float(cast(Any, d["rrr"])),
            risk_percent=float(cast(Any, d["risk_percent"])),
            position_ttl_bars=int(cast(Any, d["position_ttl_bars"])),
            atr_sl_mult=float(cast(Any, d.get("atr_sl_mult", 1.0))),
        )


@dataclass(frozen=True, slots=True)
class DSSCandidate:
    """Immutable DSS v2 candidate with reproducible signal and execution shape."""

    candidate_id: str
    trigger_name: str
    trigger_params: dict[str, float | int | str]
    filter_names: tuple[str, ...]
    filter_params: dict[str, dict[str, float | int | str]]
    rrr: float
    risk_percent: float
    position_ttl_bars: int
    atr_sl_mult: float
    generation: int
    parent_ids: tuple[str, ...] = ()

    @property
    def trial_config(self) -> TrialConfig:
        return TrialConfig(
            trigger_name=self.trigger_name,
            trigger_params=dict(self.trigger_params),
            filter_names=self.filter_names,
            filter_params={name: dict(params) for name, params in self.filter_params.items()},
            rrr=self.rrr,
            risk_percent=self.risk_percent,
            position_ttl_bars=self.position_ttl_bars,
            atr_sl_mult=self.atr_sl_mult,
        )

    @property
    def signal_cache_key(self) -> str:
        return self.trial_config.signal_cache_key

    @property
    def execution_key(self) -> str:
        payload = {
            "rrr": self.rrr,
            "risk_percent": self.risk_percent,
            "position_ttl_bars": self.position_ttl_bars,
        }
        return hashlib.sha1(json.dumps(payload, sort_keys=True).encode()).hexdigest()

    @property
    def candidate_key(self) -> str:
        return hashlib.sha1(f"{self.signal_cache_key}:{self.execution_key}".encode()).hexdigest()

    def to_dict(self) -> dict[str, object]:
        return {
            "candidate_id": self.candidate_id,
            "trigger_name": self.trigger_name,
            "trigger_params": dict(self.trigger_params),
            "filter_names": list(self.filter_names),
            "filter_params": {k: dict(v) for k, v in self.filter_params.items()},
            "rrr": self.rrr,
            "risk_percent": self.risk_percent,
            "position_ttl_bars": self.position_ttl_bars,
            "atr_sl_mult": self.atr_sl_mult,
            "generation": self.generation,
            "parent_ids": list(self.parent_ids),
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> DSSCandidate:
        trigger_params_raw = cast(dict[str, ParamValue], data.get("trigger_params") or {})
        filter_names_raw = cast(list[object], data.get("filter_names") or [])
        filter_params_raw = cast(
            dict[str, dict[str, ParamValue]],
            data.get("filter_params") or {},
        )
        parent_ids_raw = cast(list[object], data.get("parent_ids") or [])
        return cls(
            candidate_id=str(data["candidate_id"]),
            trigger_name=str(data["trigger_name"]),
            trigger_params=dict(trigger_params_raw),
            filter_names=tuple(str(v) for v in filter_names_raw),
            filter_params={str(k): dict(v) for k, v in filter_params_raw.items()},
            rrr=float(cast(Any, data["rrr"])),
            risk_percent=float(cast(Any, data["risk_percent"])),
            position_ttl_bars=int(cast(Any, data["position_ttl_bars"])),
            atr_sl_mult=float(cast(Any, data.get("atr_sl_mult", 1.0))),
            generation=int(cast(Any, data.get("generation", 0))),
            parent_ids=tuple(str(v) for v in parent_ids_raw),
        )


@dataclass(frozen=True, slots=True)
class DSSBehavior:
    trigger_family: str
    side_profile: str
    trade_count_bucket: str
    hold_time_bucket: str
    risk_geometry: str
    regime_strength: str
    filter_depth: str

    @property
    def cell_key(self) -> tuple[str, str, str, str, str]:
        return (
            self.trigger_family,
            self.side_profile,
            self.trade_count_bucket,
            self.risk_geometry,
            self.filter_depth,
        )

    def to_label(self) -> str:
        return "|".join(self.cell_key)


# ---------------------------------------------------------------------------
# Window specification
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class DSSWindowSpec:
    """One evaluation window for DSS."""

    label: str
    symbol: str
    start: str
    end: str

    @classmethod
    def from_year(cls, year: int, symbol: str) -> DSSWindowSpec:
        """Create a full-calendar-year window."""
        return cls(
            label=str(year),
            symbol=symbol,
            start=f"{year}-01-01",
            end=f"{year}-12-31",
        )

    @classmethod
    def from_half_year(cls, year: int, half: int, symbol: str) -> DSSWindowSpec:
        """Create H1 (Jan-Jun) or H2 (Jul-Dec) window."""
        if half == 1:
            return cls(label=f"{year}H1", symbol=symbol, start=f"{year}-01-01", end=f"{year}-06-30")
        return cls(label=f"{year}H2", symbol=symbol, start=f"{year}-07-01", end=f"{year}-12-31")

    @classmethod
    def parse(cls, spec: str, symbol: str) -> DSSWindowSpec:
        """Parse a CLI window spec like '2022', '2025H1'.

        Accepted formats:
          YYYY          → full-year window
          YYYYH1/H2     → half-year window
          label:start:end → explicit start/end (YYYY-MM-DD)
        """
        spec = spec.strip()
        if ":" in spec:
            parts = spec.split(":")
            if len(parts) != 3:
                raise ValueError(f"Window spec must be 'label:start:end', got: {spec!r}")
            return cls(label=parts[0], symbol=symbol, start=parts[1], end=parts[2])
        if spec.endswith(("H1", "H2")):
            half = int(spec[-1])
            year = int(spec[:-2])
            return cls.from_half_year(year, half, symbol)
        year = int(spec)
        return cls.from_year(year, symbol)


# ---------------------------------------------------------------------------
# Search space
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DSSSearchSpace:
    """Bounds for all search dimensions in one study."""

    trigger_names: tuple[str, ...]
    filter_names: tuple[str, ...]
    trigger_param_bounds: dict[str, dict[str, ParamDef]]
    filter_param_bounds: dict[str, dict[str, ParamDef]]
    max_filters: int = 4
    rrr_range: FloatRange = (1.5, 4.0, 0.25)
    risk_percent_range: FloatRange = (1.0, 3.0, 0.25)
    position_ttl_bars_range: IntRange = (24, 72, 4)
    atr_sl_mult_range: FloatRange = (0.5, 2.5, 0.25)


# ---------------------------------------------------------------------------
# Main DSS configuration
# ---------------------------------------------------------------------------


@dataclass
class DSSConfig:
    """Master configuration for a DSS run."""

    output: Path
    windows: list[DSSWindowSpec]
    n_trials: int = 50_000
    n_jobs: int = 1
    max_filters: int = 4
    min_trades_per_window: int = 20
    min_signals_per_week: float = 0.0
    resume_journal: Path | None = None
    sampler: Literal["nsga2", "tpe", "random"] = "nsga2"
    accept_min_score_per_window: float = -500.0
    top_n_candidates: int = 20
    initial_capital: float = 10_000.0
    taker_fee: float = 0.0005
    maker_fee: float = 0.0002
    max_positions: int = 1
    risk_base_period: str = "monthly"
    signal_cache_max_entries: int = 2_000
    algorithm: Literal["staged", "catcma_qd", "island_qd", "hyperband_qd", "smac_qd"] = "staged"
    catalog: Literal["legacy", "pinescript_v1", "all"] = "legacy"
    stage_mode: Literal["full", "stage1"] = "full"
    seed: int = 36
    min_barrier_tp_first_rate: float = 0.05
    min_barrier_win_rate: float = 0.55
    specialist_windows: tuple[str, ...] = ()
