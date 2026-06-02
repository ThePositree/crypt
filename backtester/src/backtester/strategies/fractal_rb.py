from __future__ import annotations

from typing import Any

import pandas as pd

from backtester.strategy import BaseStrategy


class FractalRbStrategy(BaseStrategy):
    """Fractal + Rejection Block strategy ported from Pine Script.

    This strategy reproduces the core entry logic of the TradingView
    ``Fractal+RB`` script with limit orders:

    - Tracks up/down fractal levels.
    - Waits for wick-based touches of those levels.
    - Confirms setups with two-bar rejection-block conditions.
    - For each valid setup, creates a *virtual limit order*:
        - long: limit at setup candle body_upper;
        - short: limit at setup candle body_lower.
    - On subsequent bars, when price reaches the limit level, the strategy
      emits a signal on that bar while keeping the original SL from the
      setup candle.

    Notes
    -----
    - This implementation intentionally does *not* include:
      daily profit/loss limits, session filters or limits on the number
      of simultaneous trades. Those risk controls are handled by
      :class:`backtester.execution_sim.ExecutionSim` via its parameters
      (``max_daily_profit``, ``max_daily_loss``, ``trading_begin``,
      ``trading_end``, ``max_positions``, etc.).
    - The strategy outputs only:
      - ``signal``: -1 (short), 0 (flat), 1 (long).
      - ``sl_price``: stop-loss price for the signal.
    """

    def suggest_params(self, trial) -> dict[str, Any]:
        """Suggest hyperparameters compatible with the original Pine script."""
        fractal_bars = trial.suggest_categorical("fractal_bars", [3, 5])
        return {
            "fractal_bars": fractal_bars,
            "min_wick_pips": trial.suggest_float(
                "min_wick_pips", 50.0, 1000.0, step=25.0
            ),
            "pips_scale": trial.suggest_int("pips_scale", 1000, 20000, step=1000),
        }

    def generate(self, df: pd.DataFrame) -> pd.DataFrame:
        """Generate signals based on Fractal+RB logic.

        Parameters
        ----------
        df:
            Input OHLCV data indexed by timestamp. Must contain at least
            ``open``, ``high``, ``low``, ``close`` columns.

        Returns
        -------
        pd.DataFrame
            Same ``df`` with added/overwritten columns:

            - ``signal``: -1 (short), 0 (flat), 1 (long).
            - ``sl_price``: stop-loss price for the entry bar.
        """
        if df.empty:
            return df

        # Extract parameters with Pine-aligned defaults.
        params = self.params or {}
        fractal_bars = int(params.get("fractal_bars", 3))
        if fractal_bars not in (3, 5):
            raise ValueError("fractal_bars must be either 3 or 5")

        min_wick_pips = float(params.get("min_wick_pips", 250.0))
        pips_scale = float(params.get("pips_scale", 10000.0))

        # Prepare output columns.
        df = df.copy()
        df["signal"] = 0
        df["sl_price"] = pd.NA
        df["entry_price"] = pd.NA

        opens = df["open"].to_numpy()
        highs = df["high"].to_numpy()
        lows = df["low"].to_numpy()
        closes = df["close"].to_numpy()

        # Middle bar of the completed fractal window (same bar as Pine's pivot).
        half = fractal_bars // 2

        # Active fractal levels (values only, newest appended at the end).
        dn_levels: list[float] = []
        up_levels: list[float] = []

        # Pending virtual limit orders created on setup bars.
        pending_longs: list[dict[str, float]] = []
        pending_shorts: list[dict[str, float]] = []

        prev_dn_touch = False
        prev_up_touch = False

        prev_wick_upper_pips = 0.0
        prev_wick_lower_pips = 0.0

        length = len(df)
        for i in range(length):
            open_i = float(opens[i])
            high_i = float(highs[i])
            low_i = float(lows[i])

            # 1) Check fills for previously created limit orders (T+1 or later).
            filled_this_bar = False
            if i > 0:
                # Long limits: filled when low <= entry_price.
                j = 0
                while j < len(pending_longs) and not filled_this_bar:
                    order = pending_longs[j]
                    ep = order["entry_price"]
                    if ep >= high_i:
                        ep = high_i

                    if low_i <= ep:
                        idx = df.index[i]
                        df.at[idx, "signal"] = 1
                        df.at[idx, "sl_price"] = order["sl_price"]
                        df.at[idx, "entry_price"] = ep
                        pending_longs.pop(j)
                        filled_this_bar = True
                    else:
                        j += 1

                # Short limits: filled when high >= entry_price.
                j = 0
                while j < len(pending_shorts) and not filled_this_bar:
                    order = pending_shorts[j]
                    ep = order["entry_price"]
                    if ep <= low_i:
                        ep = low_i

                    if high_i >= ep:
                        idx = df.index[i]
                        df.at[idx, "signal"] = -1
                        df.at[idx, "sl_price"] = order["sl_price"]
                        df.at[idx, "entry_price"] = ep
                        pending_shorts.pop(j)
                        filled_this_bar = True
                    else:
                        j += 1

            # 2) Compute body and wick metrics for the current bar.
            close_i = float(closes[i])
            body_lower = min(close_i, open_i)
            body_upper = max(close_i, open_i)

            wick_upper = high_i - body_upper
            wick_lower = body_lower - low_i

            wick_upper_pips = wick_upper * pips_scale
            wick_lower_pips = wick_lower * pips_scale

            wick_upper_pips_around = (
                max(wick_upper_pips, prev_wick_upper_pips)
                if i > 0
                else wick_upper_pips
            )
            wick_lower_pips_around = (
                min(wick_lower_pips, prev_wick_lower_pips)
                if i > 0
                else wick_lower_pips
            )

            # 3) Detect new fractals using the same inequalities as in Pine.
            dn_fractal = False
            up_fractal = False
            center = i - half
            if i >= fractal_bars - 1 and center + half < length:
                if fractal_bars == 5:
                    if (
                        highs[center - 2] < highs[center]
                        and highs[center - 1] < highs[center]
                        and highs[center + 1] < highs[center]
                        and highs[center + 2] < highs[center]
                    ):
                        dn_fractal = True
                    if (
                        lows[center - 2] > lows[center]
                        and lows[center - 1] > lows[center]
                        and lows[center + 1] > lows[center]
                        and lows[center + 2] > lows[center]
                    ):
                        up_fractal = True
                elif fractal_bars == 3:
                    if highs[center - 1] < highs[center] and highs[center + 1] < highs[center]:
                        dn_fractal = True
                    if lows[center - 1] > lows[center] and lows[center + 1] > lows[center]:
                        up_fractal = True

            if dn_fractal:
                dn_levels.append(float(highs[center]))
            if up_fractal:
                up_levels.append(float(lows[center]))

            # 4) Process down fractal levels: check for touch by current bar wick.
            dn_touch = False
            if dn_levels:
                j = 0
                while j < len(dn_levels):
                    level = dn_levels[j]
                    death = high_i > level
                    if death:
                        if level > body_upper:
                            dn_touch = True
                        dn_levels.pop(j)
                        break
                    j += 1

            # 5) Process up fractal levels: check for touch by current bar wick.
            up_touch = False
            if up_levels:
                j = 0
                while j < len(up_levels):
                    level = up_levels[j]
                    death = low_i < level
                    if death:
                        if level < body_lower:
                            up_touch = True
                        up_levels.pop(j)
                        break
                    j += 1

            dn_touch_around = dn_touch or prev_dn_touch
            up_touch_around = up_touch or prev_up_touch

            # 6) Rejection block (RB) conditions require previous bar.
            bullish_rb = False
            bearish_rb = False
            if i > 0:
                prev_open = float(opens[i - 1])
                prev_close = float(closes[i - 1])
                bullish_rb = prev_close < close_i and prev_open > open_i
                bearish_rb = prev_close > close_i and prev_open < open_i

            # 7) Around-high/low logic uses current and previous bar extremes.
            if i > 0:
                high_prev = float(highs[i - 1])
                low_prev = float(lows[i - 1])
                high_around = max(high_i, high_prev)
                low_around = min(low_i, low_prev)
            else:
                high_prev = high_i
                low_prev = low_i
                high_around = high_i
                low_around = low_i

            long_cond = (
                up_touch_around
                and bullish_rb
                and wick_lower_pips_around > min_wick_pips
            )
            short_cond = (
                dn_touch_around
                and bearish_rb
                and wick_upper_pips_around > min_wick_pips
            )

            # 8) For valid setups, create virtual limit orders instead of
            #    emitting immediate signals.
            if long_cond:
                sl_dist = body_lower - low_around
                if sl_dist > 0:
                    pending_longs.append(
                        {
                            "entry_price": body_lower,
                            "sl_price": low_around,
                        }
                    )
            if short_cond:
                sl_dist = high_around - body_upper
                if sl_dist > 0:
                    pending_shorts.append(
                        {
                            "entry_price": body_upper,
                            "sl_price": high_around,
                        }
                    )

            prev_dn_touch = dn_touch
            prev_up_touch = up_touch
            prev_wick_upper_pips = wick_upper_pips
            prev_wick_lower_pips = wick_lower_pips

        return df

