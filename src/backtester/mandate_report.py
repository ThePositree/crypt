from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd

RETURN_FLOOR_PCT = 15.0
CAP_RETURN_PCT = 20.0
MONTHLY_DD_LIMIT_PCT = -10.0
LARGE_LOSING_DAY_LIMIT = 10


@dataclass(frozen=True, slots=True)
class MandateReport:
    monthly: pd.DataFrame
    summary: pd.DataFrame


def build_mandate_report(
    trades: pd.DataFrame,
    *,
    initial_capital: float,
    start: str,
    end: str,
    large_losing_day_count: int = 0,
) -> MandateReport:
    if initial_capital <= 0:
        raise ValueError("initial_capital must be > 0")

    monthly = build_monthly_mandate_rows(
        trades,
        initial_capital=initial_capital,
        start=start,
        end=end,
    )
    summary = build_mandate_summary(
        monthly,
        large_losing_day_count=large_losing_day_count,
    )
    return MandateReport(monthly=monthly, summary=summary)


def build_monthly_mandate_rows(
    trades: pd.DataFrame,
    *,
    initial_capital: float,
    start: str,
    end: str,
) -> pd.DataFrame:
    months = _month_index(start=start, end=end)
    prepared = _prepare_trades(trades)
    rows: list[dict[str, Any]] = []

    for month in months:
        month_trades = (
            prepared[(prepared["mandate_month"] == month) & prepared["is_closed"]]
            if not prepared.empty
            else pd.DataFrame()
        )
        month_entries = (
            prepared[prepared["entry_month"] == month] if not prepared.empty else pd.DataFrame()
        )
        monthly_pnl = (
            float(month_trades["pnl_abs"].sum())
            if not month_trades.empty and "pnl_abs" in month_trades.columns
            else 0.0
        )
        raw_return = monthly_pnl / initial_capital * 100
        equity_points = (
            initial_capital + month_trades["pnl_abs"].cumsum()
            if not month_trades.empty and "pnl_abs" in month_trades.columns
            else pd.Series(dtype="float64")
        )
        max_drawdown_pct = _max_drawdown_pct(
            initial_capital=initial_capital,
            equity_points=equity_points,
        )
        stop_loss_count = (
            int((month_trades["exit_reason"] == "stop_loss").sum())
            if not month_trades.empty and "exit_reason" in month_trades.columns
            else 0
        )

        rows.append(
            {
                "month": str(month),
                "raw_monthly_return_pct": round(raw_return, 2),
                "capped_monthly_return_pct": round(min(raw_return, CAP_RETURN_PCT), 2),
                "excess_return_pct": round(max(raw_return - CAP_RETURN_PCT, 0.0), 2),
                "max_drawdown_pct": round(max_drawdown_pct, 2),
                "trade_count": int(len(month_entries)),
                "stop_loss_count": stop_loss_count,
                "passes_return_floor": bool(raw_return >= RETURN_FLOOR_PCT),
                "breaches_monthly_dd": bool(max_drawdown_pct < MONTHLY_DD_LIMIT_PCT),
                "is_losing_month": bool(raw_return < 0),
            }
        )

    return pd.DataFrame(rows)


def build_mandate_summary(
    monthly: pd.DataFrame,
    *,
    large_losing_day_count: int = 0,
) -> pd.DataFrame:
    if monthly.empty:
        verdict = "discard"
        rationale = "No monthly rows were available for mandate evaluation."
        return pd.DataFrame([_summary_row(verdict=verdict, rationale=rationale)])

    months_total = int(len(monthly))
    months_passing_floor = int(monthly["passes_return_floor"].sum())
    months_below_floor = months_total - months_passing_floor
    worst_losing_streak = _max_consecutive_true(monthly["is_losing_month"])
    dd_breach_months = int(monthly["breaches_monthly_dd"].sum())
    worst_monthly_drawdown_pct = float(monthly["max_drawdown_pct"].min())
    avg_capped_monthly_return_pct = float(monthly["capped_monthly_return_pct"].mean())
    sum_capped_monthly_return_pct = float(monthly["capped_monthly_return_pct"].sum())

    verdict, rationale = _mandate_verdict(
        months_passing_floor=months_passing_floor,
        months_below_floor=months_below_floor,
        worst_losing_streak=worst_losing_streak,
        dd_breach_months=dd_breach_months,
        large_losing_day_count=large_losing_day_count,
    )

    return pd.DataFrame(
        [
            {
                "verdict": verdict,
                "months_total": months_total,
                "months_passing_floor": months_passing_floor,
                "months_below_floor": months_below_floor,
                "worst_consecutive_losing_months": worst_losing_streak,
                "large_losing_day_count": int(large_losing_day_count),
                "dd_breach_months": dd_breach_months,
                "worst_monthly_drawdown_pct": round(worst_monthly_drawdown_pct, 2),
                "avg_capped_monthly_return_pct": round(avg_capped_monthly_return_pct, 2),
                "sum_capped_monthly_return_pct": round(sum_capped_monthly_return_pct, 2),
                "rationale": rationale,
            }
        ]
    )


def _prepare_trades(trades: pd.DataFrame) -> pd.DataFrame:
    if trades.empty:
        return pd.DataFrame(
            columns=["entry_time", "exit_time", "pnl_abs", "mandate_month", "entry_month"]
        )
    if "exit_time" not in trades.columns:
        raise ValueError("trades must include exit_time")
    if "pnl_abs" not in trades.columns:
        raise ValueError("trades must include pnl_abs")

    prepared = trades.copy()
    prepared["exit_time"] = pd.to_datetime(prepared["exit_time"], errors="coerce", utc=True)
    if "entry_time" in prepared.columns:
        prepared["entry_time"] = pd.to_datetime(prepared["entry_time"], errors="coerce", utc=True)
    else:
        prepared["entry_time"] = prepared["exit_time"]
    prepared["pnl_abs"] = pd.to_numeric(prepared["pnl_abs"], errors="coerce").fillna(0.0)
    prepared = prepared.dropna(subset=["entry_time"])
    if "execution_sequence" in prepared.columns:
        sequence = pd.to_numeric(prepared["execution_sequence"], errors="coerce")
    else:
        sequence = pd.Series(range(len(prepared)), index=prepared.index, dtype=float)
    prepared["_execution_sequence"] = sequence.fillna(
        pd.Series(range(len(prepared)), index=prepared.index, dtype=float)
    )
    prepared = prepared.sort_values(
        ["exit_time", "_execution_sequence"],
        kind="mergesort",
        na_position="last",
    )
    prepared["entry_month"] = prepared["entry_time"].dt.tz_convert(None).dt.to_period("M")
    prepared["is_closed"] = prepared["exit_time"].notna()
    if "exit_reason" in prepared.columns:
        prepared["is_closed"] = prepared["is_closed"] & (prepared["exit_reason"] != "open")
    prepared["mandate_month"] = prepared["exit_time"].dt.tz_convert(None).dt.to_period("M")
    return prepared


def _month_index(*, start: str, end: str) -> pd.PeriodIndex:
    start_ts = pd.Timestamp(start)
    end_ts = pd.Timestamp(end)
    if end_ts <= start_ts:
        raise ValueError("end must be after start")
    return pd.period_range(
        start=start_ts.to_period("M"),
        end=(end_ts - pd.Timedelta(days=1)).to_period("M"),
        freq="M",
    )


def _max_drawdown_pct(*, initial_capital: float, equity_points: pd.Series) -> float:
    """Worst drawdown from window-start capital using closed-trade equity only."""
    if initial_capital <= 0:
        return 0.0
    if equity_points.empty:
        return 0.0
    realized = pd.concat(
        [
            pd.Series([initial_capital], dtype="float64"),
            pd.to_numeric(equity_points, errors="coerce").dropna().astype("float64"),
        ],
        ignore_index=True,
    )
    min_equity = float(realized.min())
    if min_equity >= initial_capital:
        return 0.0
    return (min_equity - initial_capital) / initial_capital * 100


def _mandate_verdict(
    *,
    months_passing_floor: int,
    months_below_floor: int,
    worst_losing_streak: int,
    dd_breach_months: int,
    large_losing_day_count: int,
) -> tuple[str, str]:
    if months_below_floor > 3:
        return (
            "discard",
            f"{months_below_floor} months are below the 15% floor; mandate allows at most 3.",
        )
    if worst_losing_streak >= 3:
        return (
            "discard",
            f"{worst_losing_streak} consecutive losing months trigger discard.",
        )
    if dd_breach_months > 0:
        return (
            "archive",
            f"{dd_breach_months} month(s) breach the 10% intra-month drawdown limit.",
        )
    if months_passing_floor >= 9 and large_losing_day_count <= LARGE_LOSING_DAY_LIMIT:
        return (
            "promote",
            "Return floor, drawdown, losing-streak, and large-losing-day gates pass.",
        )
    return (
        "full_optuna",
        "Candidate is not promoted but avoids discard/archive gates.",
    )


def _max_consecutive_true(values: pd.Series) -> int:
    best = 0
    current = 0
    for value in values:
        if bool(value):
            current += 1
            best = max(best, current)
        else:
            current = 0
    return best


def _summary_row(*, verdict: str, rationale: str) -> dict[str, Any]:
    return {
        "verdict": verdict,
        "months_total": 0,
        "months_passing_floor": 0,
        "months_below_floor": 0,
        "worst_consecutive_losing_months": 0,
        "large_losing_day_count": 0,
        "dd_breach_months": 0,
        "worst_monthly_drawdown_pct": 0.0,
        "avg_capped_monthly_return_pct": 0.0,
        "sum_capped_monthly_return_pct": 0.0,
        "rationale": rationale,
    }
