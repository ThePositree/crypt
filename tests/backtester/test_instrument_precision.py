import pytest

from backtester.instrument_precision import (
    InstrumentPrecision,
    instrument_precision_from_name,
)


def test_sol_snapshot_rounds_contracts_down_and_prices_half_up() -> None:
    precision = instrument_precision_from_name("okx_sol_usdt_swap_2026_07_01")

    assert precision is not None
    assert precision.asset_size_to_contracts(0.4164) == pytest.approx(0.41)
    assert precision.contracts_to_asset_size(0.41) == pytest.approx(0.41)
    assert precision.round_price(70.9484) == pytest.approx(70.95)
    assert precision.round_price(70.945) == pytest.approx(70.95)


def test_contract_amount_below_exchange_minimum_is_rejected() -> None:
    precision = InstrumentPrecision(
        contract_size=1.0,
        amount_step=0.01,
        min_amount=0.01,
        price_tick=0.01,
    )

    assert precision.asset_size_to_contracts(0.0099) == 0.0


def test_unknown_precision_policy_is_explicit_error() -> None:
    with pytest.raises(ValueError, match="Unknown instrument precision policy"):
        instrument_precision_from_name("missing")
