from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np
import pandas as pd

ExitFamily = Literal["sl_rrr", "sl_rrr_trailing", "tp_pct"]


def _empty_fast_mandate_attrs() -> dict[str, object]:
    return {
        "mandate_score": -float("inf"),
        "min_monthly_return": -100.0,
        "monthly_shortfall_pct": 0.0,
        "mandate_months_passing_floor": 0,
        "mandate_months_below_floor": 0,
        "mandate_dd_breach_months": 0,
        "mandate_worst_consecutive_losing_months": 0,
        "mandate_worst_monthly_drawdown_pct": 0.0,
        "mandate_avg_capped_monthly_return_pct": 0.0,
        "mandate_sum_capped_monthly_return_pct": 0.0,
        "mandate_verdict": "discard",
    }


def _max_consecutive_true(values: list[bool]) -> int:
    best = 0
    current = 0
    for value in values:
        if value:
            current += 1
            best = max(best, current)
        else:
            current = 0
    return best


def _fast_mandate_score(
    *,
    total_return_pct: float,
    max_drawdown_pct: float,
    peak_to_trough_drawdown_pct: float,
    sum_capped_monthly_return_pct: float,
    monthly_shortfall_pct: float,
    dd_excess_pct: float,
    months_below_floor: int,
    dd_breach_months: int,
    worst_consecutive_losing_months: int,
) -> float:
    downside_dd_pct = abs(min(max_drawdown_pct, 0.0))
    peak_to_trough_dd_pct = abs(min(peak_to_trough_drawdown_pct, 0.0))
    excess_failed_months = max(months_below_floor - 12, 0)
    excess_losing_streak = max(worst_consecutive_losing_months - 2, 0)
    return (
        total_return_pct * 100.0
        + sum_capped_monthly_return_pct * 10.0
        - monthly_shortfall_pct * 1.5
        - dd_excess_pct * 35.0
        - dd_breach_months * 150.0
        - excess_failed_months * 75.0
        - excess_losing_streak * 250.0
        - (downside_dd_pct**2) * 85.0
        - peak_to_trough_dd_pct * 35.0
    )


@dataclass(frozen=True, slots=True)
class FastExitEvaluation:
    metrics: dict[str, object]
    mandate_attrs: dict[str, object]


class FastExitGeometryEvaluator:
    """Fast optimizer-only evaluator for fixed-entry signal strategies.

    This intentionally covers the default DSS exit-geometry search path. It is
    used to rank many Optuna trials quickly, while the exported best run still
    goes through the full `ExecutionSim` backtester.
    """

    def __init__(
        self,
        *,
        signal_df: pd.DataFrame,
        initial_capital: float,
        taker_fee: float,
        candle_timeframe: str,
        risk_base_period: str,
        risk_free_rate_annual: float,
    ) -> None:
        if not isinstance(signal_df.index, pd.DatetimeIndex):
            raise ValueError("fast exit evaluator requires a DatetimeIndex")
        required = {"open", "high", "low", "signal", "sl_price"}
        missing = required.difference(signal_df.columns)
        if missing:
            raise ValueError(f"fast exit evaluator missing columns: {sorted(missing)}")
        self.signal_df = signal_df
        self.initial_capital = float(initial_capital)
        self.taker_fee = float(taker_fee)
        self.candle_timeframe = candle_timeframe
        self.risk_base_period = risk_base_period.strip().lower()
        if self.risk_base_period not in {"trade", "weekly", "monthly", "backtest"}:
            raise ValueError(
                "Unsupported risk_base_period "
                f"{risk_base_period!r}. Expected one of "
                "['backtest', 'monthly', 'trade', 'weekly']."
            )
        self.risk_free_rate_annual = float(risk_free_rate_annual)
        self.index = pd.DatetimeIndex(signal_df.index)
        self.open = pd.to_numeric(signal_df["open"], errors="coerce").to_numpy(dtype="float64")
        self.high = pd.to_numeric(signal_df["high"], errors="coerce").to_numpy(dtype="float64")
        self.low = pd.to_numeric(signal_df["low"], errors="coerce").to_numpy(dtype="float64")
        self.close = pd.to_numeric(signal_df["close"], errors="coerce").to_numpy(dtype="float64")
        self.signal = pd.to_numeric(signal_df["signal"], errors="coerce").fillna(0).to_numpy(
            dtype="int64"
        )
        self.sl_price = pd.to_numeric(signal_df["sl_price"], errors="coerce").to_numpy(
            dtype="float64"
        )
        self.entry_price_column = (
            pd.to_numeric(signal_df["entry_price"], errors="coerce").to_numpy(dtype="float64")
            if "entry_price" in signal_df.columns
            else None
        )
        self.trail_atr = self._trail_atr_values(signal_df)
        self.signal_indices = np.flatnonzero((self.signal == 1) | (self.signal == -1))
        month_ordinals = self.index.year * 12 + self.index.month
        self._first_month_ordinal = int(month_ordinals.min())
        self._month_count = int(month_ordinals.max() - month_ordinals.min() + 1)
        self._month_positions = (month_ordinals - self._first_month_ordinal).to_numpy(
            dtype="int64"
        )

    @staticmethod
    def _trail_atr_values(signal_df: pd.DataFrame) -> np.ndarray:
        if "trail_atr" in signal_df.columns:
            return pd.to_numeric(signal_df["trail_atr"], errors="coerce").to_numpy(
                dtype="float64"
            )
        prev_close = signal_df["close"].shift(1)
        true_range = pd.concat(
            [
                signal_df["high"] - signal_df["low"],
                (signal_df["high"] - prev_close).abs(),
                (signal_df["low"] - prev_close).abs(),
            ],
            axis=1,
        ).max(axis=1)
        return true_range.rolling(14, min_periods=14).mean().shift(1).to_numpy(dtype="float64")

    def evaluate(
        self,
        *,
        risk_percent: float,
        rrr: float,
        exit_family: ExitFamily,
        position_ttl_bars: int,
        trail_distance_atr: float,
        tp_move_pct: float | None,
    ) -> FastExitEvaluation:
        capital = self.initial_capital
        risk_window_key: tuple[int, int] | None = None
        risk_window_capital = self.initial_capital
        pnl_values: list[float] = []
        capital_after_values: list[float] = []
        exit_month_positions: list[int] = []
        for signal_index in self.signal_indices:
            entry_index = signal_index + 1
            if entry_index >= len(self.open):
                continue
            side = int(self.signal[signal_index])
            entry_price = self._entry_price(signal_index, entry_index)
            sl_price = float(self.sl_price[signal_index])
            if not np.isfinite(entry_price) or not np.isfinite(sl_price):
                continue
            risk_distance = abs(entry_price - sl_price)
            if risk_distance <= 0:
                continue
            tp_price = self._tp_price(
                entry_price=entry_price,
                sl_price=sl_price,
                side=side,
                rrr=rrr,
                exit_family=exit_family,
                tp_move_pct=tp_move_pct,
            )
            if exit_family == "sl_rrr_trailing" and trail_distance_atr > 0:
                entry_atr = float(self.trail_atr[entry_index])
                if not np.isfinite(entry_atr) or entry_atr <= 0:
                    continue
            entry_time = self.index[entry_index]
            risk_base_capital, risk_window_key, risk_window_capital = (
                self._risk_base_capital_for_entry(
                    entry_time=entry_time,
                    current_capital=capital,
                    risk_window_key=risk_window_key,
                    risk_window_capital=risk_window_capital,
                )
            )
            risk_value = risk_base_capital * (float(risk_percent) / 100.0)
            size = risk_value / risk_distance
            if size <= 0 or not np.isfinite(size):
                continue
            exit_index, exit_price, _exit_reason = self._resolve_exit(
                entry_index=entry_index,
                entry_price=entry_price,
                sl_price=sl_price,
                tp_price=tp_price,
                side=side,
                rrr=rrr,
                exit_family=exit_family,
                position_ttl_bars=position_ttl_bars,
                trail_distance_atr=trail_distance_atr,
            )
            fee_entry = abs(size * entry_price) * self.taker_fee
            fee_exit = abs(size * exit_price) * self.taker_fee
            gross = (exit_price - entry_price) * size * side
            pnl_abs = gross - fee_entry - fee_exit
            capital += pnl_abs
            pnl_values.append(pnl_abs)
            capital_after_values.append(capital)
            exit_month_positions.append(
                int(self._month_positions[min(exit_index + 1, len(self.index) - 1)])
            )
            if capital <= 1:
                break
        metrics, mandate_attrs = self._fast_metrics(
            pnl_values=pnl_values,
            capital_after_values=capital_after_values,
            exit_month_positions=exit_month_positions,
            final_capital=capital,
        )
        return FastExitEvaluation(
            metrics=metrics,
            mandate_attrs=mandate_attrs,
        )

    def _risk_base_capital_for_entry(
        self,
        *,
        entry_time: pd.Timestamp,
        current_capital: float,
        risk_window_key: tuple[int, int] | None,
        risk_window_capital: float,
    ) -> tuple[float, tuple[int, int] | None, float]:
        if self.risk_base_period == "trade":
            return current_capital, risk_window_key, risk_window_capital

        if self.risk_base_period == "backtest":
            return self.initial_capital, risk_window_key, risk_window_capital

        if self.risk_base_period == "weekly":
            iso = entry_time.isocalendar()
            window_key = (int(iso.year), int(iso.week))
        else:
            window_key = (int(entry_time.year), int(entry_time.month))

        if risk_window_key != window_key:
            return current_capital, window_key, current_capital
        return risk_window_capital, risk_window_key, risk_window_capital

    def _fast_metrics(
        self,
        *,
        pnl_values: list[float],
        capital_after_values: list[float],
        exit_month_positions: list[int],
        final_capital: float,
    ) -> tuple[dict[str, object], dict[str, object]]:
        if not pnl_values:
            return {"error": "no_trades", "total_trades": 0}, _empty_fast_mandate_attrs()
        pnl = np.asarray(pnl_values, dtype="float64")
        capital_after = np.asarray(capital_after_values, dtype="float64")
        wins = pnl > 0
        gross_profit = float(pnl[pnl > 0].sum())
        gross_loss = abs(float(pnl[pnl < 0].sum()))
        profit_factor: float | str = (
            "inf" if gross_loss == 0 else round(gross_profit / gross_loss, 2)
        )
        equity = np.concatenate(([self.initial_capital], capital_after))
        max_drawdown = min(float(equity.min() - self.initial_capital), 0.0) / self.initial_capital
        running_peak = np.maximum.accumulate(equity)
        peak_to_trough = float(((equity - running_peak) / running_peak).min())
        monthly_pnl = np.zeros(self._month_count, dtype="float64")
        monthly_min_equity = np.full(self._month_count, self.initial_capital, dtype="float64")
        monthly_running_equity = np.full(
            self._month_count,
            self.initial_capital,
            dtype="float64",
        )
        for pnl_abs, month_pos in zip(pnl_values, exit_month_positions, strict=True):
            if month_pos < 0 or month_pos >= self._month_count:
                continue
            monthly_pnl[month_pos] += pnl_abs
            monthly_running_equity[month_pos] += pnl_abs
            monthly_min_equity[month_pos] = min(
                monthly_min_equity[month_pos],
                monthly_running_equity[month_pos],
            )
        raw_returns = []
        capped_returns = []
        dd_values = []
        losing_flags = []
        passing_floor = 0
        dd_breaches = 0
        for month_pos in range(self._month_count):
            raw_return = monthly_pnl[month_pos] / self.initial_capital * 100.0
            capped = min(raw_return, 20.0)
            month_dd = min(
                (monthly_min_equity[month_pos] - self.initial_capital)
                / self.initial_capital
                * 100.0,
                0.0,
            )
            raw_returns.append(raw_return)
            capped_returns.append(capped)
            dd_values.append(month_dd)
            losing_flags.append(raw_return < 0)
            passing_floor += int(raw_return >= 15.0)
            dd_breaches += int(month_dd < -10.0)
        months_below = self._month_count - passing_floor
        worst_losing_streak = _max_consecutive_true(losing_flags)
        worst_monthly_dd = min(dd_values) if dd_values else 0.0
        sum_capped = float(sum(capped_returns))
        monthly_shortfall = float(sum(max(15.0 - value, 0.0) for value in raw_returns))
        dd_excess = float(sum(max(-10.0 - value, 0.0) for value in dd_values))
        total_return_pct = (final_capital - self.initial_capital) / self.initial_capital * 100.0
        max_drawdown_pct = max_drawdown * 100.0
        peak_to_trough_drawdown_pct = peak_to_trough * 100.0
        mandate_score = _fast_mandate_score(
            total_return_pct=total_return_pct,
            max_drawdown_pct=max_drawdown_pct,
            peak_to_trough_drawdown_pct=peak_to_trough_drawdown_pct,
            sum_capped_monthly_return_pct=sum_capped,
            monthly_shortfall_pct=monthly_shortfall,
            dd_excess_pct=dd_excess,
            months_below_floor=months_below,
            dd_breach_months=dd_breaches,
            worst_consecutive_losing_months=worst_losing_streak,
        )
        metrics: dict[str, object] = {
            "total_trades": len(pnl_values),
            "closed_trades": len(pnl_values),
            "open_trades": 0,
            "win_rate": round(float(wins.mean() * 100.0), 2),
            "total_pnl_abs": round(float(pnl.sum()), 2),
            "total_return_pct": round(total_return_pct, 2),
            "profit_factor": profit_factor,
            "max_drawdown": round(max_drawdown_pct, 2),
            "peak_to_trough_drawdown": round(peak_to_trough_drawdown_pct, 2),
            "sharpe_ratio": 0.0,
            "final_capital": round(final_capital, 2),
        }
        mandate_attrs: dict[str, object] = {
            "mandate_score": mandate_score,
            "min_monthly_return": round(min(raw_returns) if raw_returns else -100.0, 2),
            "monthly_shortfall_pct": round(monthly_shortfall, 2),
            "mandate_months_passing_floor": passing_floor,
            "mandate_months_below_floor": months_below,
            "mandate_dd_breach_months": dd_breaches,
            "mandate_worst_consecutive_losing_months": worst_losing_streak,
            "mandate_worst_monthly_drawdown_pct": round(worst_monthly_dd, 2),
            "mandate_avg_capped_monthly_return_pct": round(float(np.mean(capped_returns)), 2),
            "mandate_sum_capped_monthly_return_pct": round(sum_capped, 2),
            "mandate_verdict": "candidate",
        }
        return metrics, mandate_attrs

    def _entry_price(self, signal_index: int, entry_index: int) -> float:
        if self.entry_price_column is not None:
            candidate = float(self.entry_price_column[signal_index])
            if np.isfinite(candidate):
                return candidate
        return float(self.open[entry_index])

    @staticmethod
    def _tp_price(
        *,
        entry_price: float,
        sl_price: float,
        side: int,
        rrr: float,
        exit_family: ExitFamily,
        tp_move_pct: float | None,
    ) -> float:
        if exit_family == "tp_pct" and tp_move_pct is not None:
            return entry_price * (1.0 + side * tp_move_pct)
        return entry_price + side * abs(entry_price - sl_price) * rrr

    def _resolve_exit(
        self,
        *,
        entry_index: int,
        entry_price: float,
        sl_price: float,
        tp_price: float,
        side: int,
        rrr: float,
        exit_family: ExitFamily,
        position_ttl_bars: int,
        trail_distance_atr: float,
    ) -> tuple[int, float, str]:
        max_exit_index = min(entry_index + max(position_ttl_bars, 1) - 1, len(self.open) - 2)
        trail_active = False
        best_favorable = entry_price
        trail_stop = sl_price
        trail_spread = 0.0
        activation_price = entry_price + side * abs(entry_price - sl_price) * rrr
        if exit_family == "sl_rrr_trailing" and trail_distance_atr > 0:
            entry_atr = float(self.trail_atr[entry_index])
            if np.isfinite(entry_atr) and entry_atr > 0:
                trail_spread = trail_distance_atr * entry_atr
            else:
                return entry_index, entry_price, "invalid_trailing_atr"

        for idx in range(entry_index, max_exit_index + 1):
            bar_open = float(self.open[idx])
            bar_high = float(self.high[idx])
            bar_low = float(self.low[idx])
            if side == 1:
                if trail_spread > 0:
                    original_sl_hit = bar_low <= sl_price
                    activation_hit = bar_high >= activation_price
                    if not trail_active:
                        if original_sl_hit and not activation_hit:
                            return idx, min(sl_price, bar_open), "stop_loss"
                        if not activation_hit:
                            fixed_tp_hit = tp_price < activation_price and bar_high >= tp_price
                            if fixed_tp_hit:
                                return idx, tp_price, "take_profit"
                            if original_sl_hit:
                                return idx, min(sl_price, bar_open), "stop_loss"
                            continue
                        trail_active = True
                        best_favorable = max(best_favorable, bar_high)
                        trail_stop = max(sl_price, best_favorable - trail_spread)
                    else:
                        previous_stop = trail_stop
                        if bar_low <= previous_stop:
                            return idx, min(previous_stop, bar_open), "trailing_stop"
                        best_favorable = max(best_favorable, bar_high)

                    trail_stop = max(sl_price, best_favorable - trail_spread)
                    if bar_low <= trail_stop:
                        return idx, min(trail_stop, bar_open), "trailing_stop"
                    continue

                tp_hit = bar_high >= tp_price
                sl_hit = bar_low <= sl_price
                if tp_hit and sl_hit:
                    return idx, min(sl_price, bar_open), "stop_loss"
                if sl_hit:
                    return idx, min(sl_price, bar_open), "stop_loss"
                if tp_hit:
                    return idx, tp_price, "take_profit"
            else:
                if trail_spread > 0:
                    original_sl_hit = bar_high >= sl_price
                    activation_hit = bar_low <= activation_price
                    if not trail_active:
                        if original_sl_hit and not activation_hit:
                            return idx, max(sl_price, bar_open), "stop_loss"
                        if not activation_hit:
                            fixed_tp_hit = tp_price > activation_price and bar_low <= tp_price
                            if fixed_tp_hit:
                                return idx, tp_price, "take_profit"
                            if original_sl_hit:
                                return idx, max(sl_price, bar_open), "stop_loss"
                            continue
                        trail_active = True
                        best_favorable = min(best_favorable, bar_low)
                        trail_stop = min(sl_price, best_favorable + trail_spread)
                    else:
                        previous_stop = trail_stop
                        if bar_high >= previous_stop:
                            return idx, max(previous_stop, bar_open), "trailing_stop"
                        best_favorable = min(best_favorable, bar_low)

                    trail_stop = min(sl_price, best_favorable + trail_spread)
                    if bar_high >= trail_stop:
                        return idx, max(trail_stop, bar_open), "trailing_stop"
                    continue

                tp_hit = bar_low <= tp_price
                sl_hit = bar_high >= sl_price
                if tp_hit and sl_hit:
                    return idx, max(sl_price, bar_open), "stop_loss"
                if sl_hit:
                    return idx, max(sl_price, bar_open), "stop_loss"
                if tp_hit:
                    return idx, tp_price, "take_profit"
        return max_exit_index, float(self.open[max_exit_index + 1]), "ttl_expired"
