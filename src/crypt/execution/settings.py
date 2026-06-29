"""ExecutionSettings — pydantic-settings config for the M4 live execution module.

All keys are prefixed EXECUTION_ in the environment / .env file.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class ExecutionSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="EXECUTION_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        # Accept EXECUTION_SYMBOLS=SOL-USDT-SWAP,TON-USDT-SWAP instead of
        # requiring a JSON array in shell/env files.
        enable_decoding=False,
    )

    # ── master switches ────────────────────────────────────────────────────
    enabled: bool = Field(
        default=False,
        description="Set EXECUTION_ENABLED=true to activate the module.",
    )
    dry_run: bool = Field(
        default=True,
        description=(
            "When true, orders are logged but not placed. "
            "Set EXECUTION_DRY_RUN=false for real money."
        ),
    )
    dry_run_capital: float = Field(
        default=0.0,
        ge=0.0,
        description=(
            "Optional sizing capital used only when EXECUTION_DRY_RUN=true. "
            "0 means use the real OKX balance."
        ),
    )

    # ── strategy ───────────────────────────────────────────────────────────
    strategy_config: Path = Field(
        default=Path(
            "strategies/archive/filtered_donor_portfolio_causal_v4_core4_no_island_long_riskx0p85.json"
        ),
        description="Path to the backtester strategy JSON config.",
    )
    data_dir: Path = Field(default=Path("data"))
    state_path: Path = Field(default=Path("data/live_positions.json"))

    # ── execution parameters (must match the mandate-validated backtest) ───
    exit_geometry: str = Field(default="sl_rrr")
    tp_move_pct: float = Field(default=0.016, gt=0.0)
    structural_sl_mode: str = Field(default="cap")
    min_tp_move_pct: float = Field(default=0.004, gt=0.0)
    rrr: float = Field(default=2.0, gt=0.0)
    ttl_bars: int = Field(default=0, ge=0)
    risk_percent: float = Field(default=1.0, gt=0.0)
    trail_activation_rrr: float = Field(default=0.0, ge=0.0)
    trail_distance_atr: float = Field(default=0.0, ge=0.0)
    max_positions: int = Field(default=0, ge=0)
    max_leverage: float = Field(default=25.0, gt=0.0)
    risk_base_period: str = Field(default="monthly")

    # ── fee model (mirrors StaticPercentFeeModel defaults) ────────────────
    taker_fee: float = Field(default=0.0005)
    maker_fee: float = Field(default=0.0002)

    # ── safety guards ──────────────────────────────────────────────────────
    max_capital_risk_pct: float = Field(
        default=10.0,
        description=(
            "Circuit breaker: skip new entries when total locked margin "
            "exceeds this percentage of available balance."
        ),
    )
    min_net_exposure: float = Field(default=0.01)
    max_allowed_margin: float = Field(default=1.0)
    require_exchange_sync: bool = Field(
        default=True,
        description="Block live entries when local state does not match OKX state.",
    )

    # ── symbols ────────────────────────────────────────────────────────────
    symbols: list[str] = Field(
        default_factory=lambda: ["SOL-USDT-SWAP"],
        description="Symbols to execute on. Comma-separated in env.",
    )

    @field_validator("symbols", mode="before")
    @classmethod
    def _parse_symbols(cls, v: object) -> list[str]:
        if isinstance(v, str):
            return [s.strip() for s in v.split(",") if s.strip()]
        if not isinstance(v, list):
            raise TypeError(f"symbols must be a list or comma-separated string, got {type(v)}")
        return [str(item) for item in v]

    @field_validator("exit_geometry")
    @classmethod
    def _validate_exit_geometry(cls, v: str) -> str:
        allowed = {"sl_rrr", "tp_pct"}
        if v not in allowed:
            raise ValueError(f"exit_geometry must be one of {sorted(allowed)}")
        return v

    @field_validator("structural_sl_mode")
    @classmethod
    def _validate_structural_sl_mode(cls, v: str) -> str:
        allowed = {"cap", "ignore", "reject"}
        if v not in allowed:
            raise ValueError(f"structural_sl_mode must be one of {sorted(allowed)}")
        return v

    @field_validator("risk_base_period")
    @classmethod
    def _validate_risk_base_period(cls, v: str) -> str:
        allowed = {"trade", "weekly", "monthly", "backtest"}
        if v not in allowed:
            raise ValueError(f"risk_base_period must be one of {sorted(allowed)}")
        return v
