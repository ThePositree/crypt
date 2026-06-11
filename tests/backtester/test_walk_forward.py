"""Unit tests for walk-forward window generation and report helpers."""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from backtester.walk_forward import (
    WalkForwardWindow,
    WalkForwardWindowResult,
    WindowMetrics,
    _add_months,
    _build_markdown_report,
    _degradation,
    generate_windows,
)

# ---------------------------------------------------------------------------
# _add_months
# ---------------------------------------------------------------------------


def test_add_months_basic() -> None:
    assert _add_months(date(2022, 1, 1), 12) == date(2023, 1, 1)


def test_add_months_clamps_to_last_day_of_month() -> None:
    # Jan-31 + 1 month should clamp to Feb-28 (non-leap).
    assert _add_months(date(2023, 1, 31), 1) == date(2023, 2, 28)


def test_add_months_negative() -> None:
    assert _add_months(date(2023, 3, 1), -3) == date(2022, 12, 1)


# ---------------------------------------------------------------------------
# generate_windows — window count and boundaries
# ---------------------------------------------------------------------------


def test_generate_windows_count() -> None:
    """is=12, oos=6, 4-year range → 6 windows."""
    windows = generate_windows(
        symbol="SOL-USDT-SWAP",
        from_date="2022-01-01",
        to_date="2025-12-31",
        is_months=12,
        oos_months=6,
    )
    assert len(windows) == 6


def test_generate_windows_no_overlap() -> None:
    """OOS end of window N must be strictly before OOS start of window N+1."""
    windows = generate_windows(
        symbol="SOL-USDT-SWAP",
        from_date="2022-01-01",
        to_date="2025-12-31",
        is_months=12,
        oos_months=6,
    )
    for i in range(len(windows) - 1):
        assert windows[i].oos_end < windows[i + 1].oos_start


def test_generate_windows_is_end_before_oos_start() -> None:
    """IS end must always be one day before OOS start."""
    windows = generate_windows(
        symbol="SOL-USDT-SWAP",
        from_date="2022-01-01",
        to_date="2025-12-31",
        is_months=12,
        oos_months=6,
    )
    for w in windows:
        is_end = date.fromisoformat(w.is_end)
        oos_start = date.fromisoformat(w.oos_start)
        assert oos_start == is_end + timedelta(days=1), (
            f"Gap between IS end and OOS start for window {w.label}"
        )


def test_generate_windows_first_is_start() -> None:
    """First IS window starts 12 months before the first OOS start."""
    windows = generate_windows(
        symbol="SOL-USDT-SWAP",
        from_date="2022-01-01",
        to_date="2025-12-31",
        is_months=12,
        oos_months=6,
    )
    assert windows[0].is_start == "2022-01-01"
    assert windows[0].oos_start == "2023-01-01"


def test_generate_windows_oos_within_range() -> None:
    """All OOS end dates must be <= to_date."""
    to_date = "2025-12-31"
    windows = generate_windows(
        symbol="SOL-USDT-SWAP",
        from_date="2022-01-01",
        to_date=to_date,
        is_months=12,
        oos_months=6,
    )
    for w in windows:
        assert w.oos_end <= to_date, f"OOS end {w.oos_end} exceeds to_date {to_date}"


def test_generate_windows_range_too_small() -> None:
    """When range < is+oos months, return empty list."""
    windows = generate_windows(
        symbol="SOL-USDT-SWAP",
        from_date="2024-01-01",
        to_date="2024-06-30",
        is_months=12,
        oos_months=6,
    )
    assert windows == []


def test_generate_windows_annual_oos_exact() -> None:
    """is=24, oos=12, 4-year range → exactly 2 windows."""
    windows = generate_windows(
        symbol="SOL-USDT-SWAP",
        from_date="2022-01-01",
        to_date="2025-12-31",
        is_months=24,
        oos_months=12,
    )
    assert len(windows) == 2


# ---------------------------------------------------------------------------
# _degradation
# ---------------------------------------------------------------------------


def test_degradation_positive_is_positive_oos() -> None:
    assert _degradation(50.0, 25.0) == pytest.approx(0.5, abs=1e-3)


def test_degradation_negative_oos() -> None:
    assert _degradation(50.0, -10.0) == pytest.approx(-0.2, abs=1e-3)


def test_degradation_near_zero_is() -> None:
    assert _degradation(0.3, 5.0) is None


# ---------------------------------------------------------------------------
# _build_markdown_report
# ---------------------------------------------------------------------------


def _make_result(
    is_ret: float,
    oos_ret: float,
    oos_trades: int = 20,
    optimized: bool = True,
) -> WalkForwardWindowResult:
    window = WalkForwardWindow(
        label="IS_202201_202212_OOS_202301_202306",
        symbol="SOL-USDT-SWAP",
        is_start="2022-01-01",
        is_end="2022-12-31",
        oos_start="2023-01-01",
        oos_end="2023-06-30",
    )
    is_m = WindowMetrics(
        total_return_pct=is_ret,
        trades=30,
        win_rate=0.55,
        max_drawdown=-10.0,
        profit_factor=1.5,
        sharpe_ratio=1.2,
        mandate_score=-float("inf"),
    )
    oos_m = WindowMetrics(
        total_return_pct=oos_ret,
        trades=oos_trades,
        win_rate=0.50,
        max_drawdown=-8.0,
        profit_factor=1.2,
        sharpe_ratio=0.9,
        mandate_score=-float("inf"),
    )
    return WalkForwardWindowResult(
        window=window,
        best_params={"rrr": 2.0},
        is_metrics=is_m,
        oos_metrics=oos_m,
        optimized=optimized,
    )


def test_report_positive_pct() -> None:
    results = [_make_result(50.0, 20.0), _make_result(40.0, 15.0), _make_result(30.0, -5.0)]
    md = _build_markdown_report(
        results,
        symbol="SOL-USDT-SWAP",
        is_months=12,
        oos_months=6,
        from_date="2022-01-01",
        to_date="2024-12-31",
    )
    assert "2/3" in md
    assert "67%" in md


def test_report_empty_results() -> None:
    md = _build_markdown_report(
        [],
        symbol="SOL-USDT-SWAP",
        is_months=12,
        oos_months=6,
        from_date="2022-01-01",
        to_date="2024-12-31",
    )
    assert "No windows completed" in md


def test_report_poor_oos_verdict() -> None:
    results = [_make_result(50.0, -10.0) for _ in range(4)]
    md = _build_markdown_report(
        results,
        symbol="SOL-USDT-SWAP",
        is_months=12,
        oos_months=6,
        from_date="2022-01-01",
        to_date="2025-12-31",
    )
    assert "Poor" in md or "Weak" in md
