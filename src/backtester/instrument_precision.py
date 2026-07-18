"""Versioned exchange instrument precision used by execution simulation."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_FLOOR, ROUND_HALF_UP, Decimal


@dataclass(frozen=True, slots=True)
class InstrumentPrecision:
    """Contract, amount, and price precision for one dated instrument snapshot."""

    contract_size: float
    amount_step: float
    min_amount: float
    price_tick: float

    def __post_init__(self) -> None:
        if min(self.contract_size, self.amount_step, self.min_amount, self.price_tick) <= 0:
            raise ValueError("Instrument precision values must be positive")

    def asset_size_to_contracts(self, asset_size: float) -> float:
        """Convert asset units to contracts and round down to the amount step."""
        raw_contracts = Decimal(str(asset_size)) / Decimal(str(self.contract_size))
        step = Decimal(str(self.amount_step))
        contracts = (raw_contracts / step).to_integral_value(rounding=ROUND_FLOOR) * step
        if contracts < Decimal(str(self.min_amount)):
            return 0.0
        return float(contracts)

    def contracts_to_asset_size(self, contracts: float) -> float:
        """Convert exchange contracts back to base-asset units."""
        return float(Decimal(str(contracts)) * Decimal(str(self.contract_size)))

    def round_price(self, price: float) -> float:
        """Round a price or price spread to the nearest exchange tick."""
        tick = Decimal(str(self.price_tick))
        rounded = (Decimal(str(price)) / tick).to_integral_value(rounding=ROUND_HALF_UP) * tick
        return float(rounded)


_POLICIES: dict[str, InstrumentPrecision] = {
    "okx_sol_usdt_swap_2026_07_01": InstrumentPrecision(
        contract_size=1.0,
        amount_step=0.01,
        min_amount=0.01,
        price_tick=0.01,
    ),
}


def instrument_precision_from_name(name: str | None) -> InstrumentPrecision | None:
    """Resolve a named precision snapshot, or disable rounding for ``None``."""
    if name is None:
        return None
    try:
        return _POLICIES[name]
    except KeyError as exc:
        raise ValueError(f"Unknown instrument precision policy: {name!r}") from exc
