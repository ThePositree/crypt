# Adapted from backtester/src/backtester/fee_model.py
# Original: https://github.com/AuriumX/backtester
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ExitContext:
    """Context for exit-fee calculation."""

    exit_reason: str


class FeeModel:
    """Abstract interface for commission models."""

    def calculate_entry_fee(self, position_value: float, ctx: EntryContext) -> float:
        raise NotImplementedError

    def calculate_exit_fee(
        self,
        exit_value: float,
        *,
        is_maker: bool,
        ctx: ExitContext,
    ) -> float:
        raise NotImplementedError


class StaticPercentFeeModel(FeeModel):
    """
    Percentage-based fee model.

    Applies taker_fee to entries and SL/TTL exits; maker_fee to TP exits.
    OKX perpetual swap defaults: taker=0.05%, maker=0.02%.
    """

    def __init__(self, *, taker_fee: float, maker_fee: float) -> None:
        self._taker_fee = taker_fee
        self._maker_fee = maker_fee

    def calculate_entry_fee(self, position_value: float, ctx: EntryContext) -> float:
        del ctx
        return position_value * self._taker_fee

    def calculate_exit_fee(
        self,
        exit_value: float,
        *,
        is_maker: bool,
        ctx: ExitContext,
    ) -> float:
        del ctx
        return exit_value * (self._maker_fee if is_maker else self._taker_fee)


# Avoid circular import: EntryContext lives in risk_model but is referenced above.
from crypt.backtest.risk_model import EntryContext  # noqa: E402
