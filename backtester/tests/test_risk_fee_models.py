
import pytest

from backtester.fee_model import ExitContext, StaticPercentFeeModel
from backtester.risk_model import BasicRiskModel, EntryContext


def test_basic_risk_model_long_position_sizing():
    capital = 1000.0
    total_locked_margin = 0.0
    risk_percent = 1.0
    rrr = 2.0
    entry_price = 101.0
    sl_price = 95.0

    model = BasicRiskModel(
        max_allowed_margin=1.0,
        max_positions=1,
        max_allowed_leverage=100.0,
    )

    ctx = EntryContext(
        signal=1,
        sl_price=sl_price,
        entry_price=entry_price,
        capital=capital,
        risk_base_capital=capital,
        total_locked_margin=total_locked_margin,
        risk_percent=risk_percent,
        rrr=rrr,
    )

    result = model.calculate_position(ctx)
    assert result is not None

    risk_value = capital * (risk_percent / 100.0)
    sl_dist = entry_price - sl_price
    size = risk_value / sl_dist
    position_value = size * entry_price

    assert result.size == pytest.approx(size)
    assert result.position_value == pytest.approx(position_value)
    assert result.sl_dist == pytest.approx(sl_dist)

    tp_price = entry_price + sl_dist * rrr
    assert result.tp_price == pytest.approx(tp_price)
    assert result.is_long is True
    assert result.available_balance == pytest.approx(capital)


def test_basic_risk_model_sizes_from_risk_base_capital():
    model = BasicRiskModel(
        max_allowed_margin=1.0,
        max_positions=1,
        max_allowed_leverage=100.0,
    )

    ctx = EntryContext(
        signal=1,
        sl_price=95.0,
        entry_price=100.0,
        capital=980.0,
        risk_base_capital=1000.0,
        total_locked_margin=0.0,
        risk_percent=2.0,
        rrr=2.0,
    )

    result = model.calculate_position(ctx)

    assert result is not None
    assert result.available_balance == pytest.approx(980.0)
    assert result.risk_value == pytest.approx(20.0)
    assert result.size == pytest.approx(4.0)


def test_basic_risk_model_rejects_invalid_sl():
    model = BasicRiskModel(
        max_allowed_margin=1.0,
        max_positions=1,
        max_allowed_leverage=100.0,
    )

    # Long with SL >= entry should be rejected
    ctx = EntryContext(
        signal=1,
        sl_price=105.0,
        entry_price=101.0,
        capital=1000.0,
        risk_base_capital=1000.0,
        total_locked_margin=0.0,
        risk_percent=1.0,
        rrr=2.0,
    )
    assert model.calculate_position(ctx) is None


def test_basic_risk_model_respects_max_leverage():
    # Configure model so that leverage requirement is very high
    model = BasicRiskModel(
        max_allowed_margin=0.01,
        max_positions=1,
        max_allowed_leverage=2.0,
    )

    ctx = EntryContext(
        signal=1,
        sl_price=95.0,
        entry_price=101.0,
        capital=1000.0,
        risk_base_capital=1000.0,
        total_locked_margin=0.0,
        risk_percent=10.0,
        rrr=2.0,
    )

    result = model.calculate_position(ctx)
    assert result is None


def test_static_percent_fee_model_entry_and_exit():
    taker_fee = 0.001
    maker_fee = 0.0002
    model = StaticPercentFeeModel(taker_fee=taker_fee, maker_fee=maker_fee)

    position_value = 1000.0
    entry_ctx = EntryContext(
        signal=1,
        sl_price=95.0,
        entry_price=101.0,
        capital=1000.0,
        risk_base_capital=1000.0,
        total_locked_margin=0.0,
        risk_percent=1.0,
        rrr=2.0,
    )

    entry_fee = model.calculate_entry_fee(position_value, entry_ctx)
    assert entry_fee == pytest.approx(position_value * taker_fee)

    exit_value = 1200.0
    exit_ctx = ExitContext(exit_reason="take_profit")

    # Maker exit
    exit_fee_maker = model.calculate_exit_fee(
        exit_value,
        is_maker=True,
        ctx=exit_ctx,
    )
    assert exit_fee_maker == pytest.approx(exit_value * maker_fee)

    # Taker exit
    exit_fee_taker = model.calculate_exit_fee(
        exit_value,
        is_maker=False,
        ctx=exit_ctx,
    )
    assert exit_fee_taker == pytest.approx(exit_value * taker_fee)
