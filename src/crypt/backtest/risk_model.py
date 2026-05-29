# Adapted from backtester/src/backtester/risk_model.py
# Original: https://github.com/AuriumX/backtester
from __future__ import annotations

import math
from dataclasses import dataclass

from loguru import logger


@dataclass
class EntryContext:
    """Per-bar context for risk-based position sizing."""

    signal: int
    sl_price: float
    entry_price: float
    capital: float
    total_locked_margin: float
    risk_percent: float
    rrr: float


@dataclass
class RiskResult:
    """Result of risk-based position sizing."""

    size: float
    position_value: float
    required_leverage: float
    locked_margin: float
    risk_value: float
    sl_dist: float
    tp_price: float
    is_long: bool
    available_balance: float


class RiskModel:
    """Abstract interface for risk models."""

    def calculate_position(self, ctx: EntryContext) -> RiskResult | None:
        raise NotImplementedError


class BasicRiskModel(RiskModel):
    """
    Default ATR-distance position sizer.

    Reproduces the original ExecutionSim sizing logic:
        risk_value = available_balance * (risk_percent / 100)
        size = risk_value / sl_dist
        position_value = size * entry_price
    """

    def __init__(
        self,
        *,
        max_allowed_margin: float,
        max_positions: int,
        max_allowed_leverage: float,
    ) -> None:
        self._max_allowed_margin = max_allowed_margin
        self._max_positions = max_positions
        self._max_allowed_leverage = max_allowed_leverage

    def calculate_position(self, ctx: EntryContext) -> RiskResult | None:
        signal = ctx.signal
        if signal not in (1, -1):
            return None

        is_long = signal == 1
        entry_price = ctx.entry_price
        sl_price = ctx.sl_price

        sl_dist = (entry_price - sl_price) if is_long else (sl_price - entry_price)
        if sl_dist <= 0:
            logger.debug("Invalid SL {} >= entry {}, skipping", sl_price, entry_price)
            return None

        available_balance = ctx.capital - ctx.total_locked_margin
        risk_value = available_balance * (ctx.risk_percent / 100)

        size = risk_value / sl_dist
        position_value = size * entry_price

        max_margin = self._max_allowed_margin
        if self._max_positions > 0 and self._max_allowed_margin == 0:
            max_margin = 1 / self._max_positions

        max_allowed_margin_value = available_balance * max_margin
        if max_allowed_margin_value <= 0:
            max_allowed_margin_value = available_balance

        leverage = position_value / max_allowed_margin_value
        required_leverage = max(1, math.ceil(leverage))

        if required_leverage > self._max_allowed_leverage:
            logger.debug(
                "Leverage {} > {}, skipping", required_leverage, self._max_allowed_leverage
            )
            return None

        tp_price = (
            (entry_price + sl_dist * ctx.rrr) if is_long else (entry_price - sl_dist * ctx.rrr)
        )
        locked_margin = position_value / required_leverage

        return RiskResult(
            size=size,
            position_value=position_value,
            required_leverage=required_leverage,
            locked_margin=locked_margin,
            risk_value=risk_value,
            sl_dist=sl_dist,
            tp_price=tp_price,
            is_long=is_long,
            available_balance=available_balance,
        )
