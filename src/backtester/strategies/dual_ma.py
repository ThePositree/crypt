from __future__ import annotations

import pandas as pd
import pandas_ta as ta

from backtester.strategy import BaseStrategy


class DualMAStrategy(BaseStrategy):
    def suggest_params(self, trial):
        return {
            "fast": trial.suggest_int("fast", 5, 20),
            "slow": trial.suggest_int("slow", 30, 40),
            "atr_window": trial.suggest_int("atr_window", 15, 30),
            "avg_atr_window": trial.suggest_int("avg_atr_window", 90, 110),
            # "sl_atr_length": trial.suggest_int("sl_atr_length", 90, 110),
            # "sl_atr_mult": trial.suggest_float("sl_atr_mult", 0.5, 1.5),
            "min_atr_multiplier": trial.suggest_float("min_atr_multiplier", 1.3, 2),
            "strategy": trial.suggest_categorical("strategy", ["long", "short"]),
            "sl_dist_mult": trial.suggest_float("sl_dist_mult", 0.97, 0.999),
        }

    def generate(self, df: pd.DataFrame) -> pd.DataFrame:
        fast = self.params["fast"]
        slow = self.params["slow"]
        atr_window = self.params["atr_window"]
        avg_atr_window = self.params["avg_atr_window"]
        min_atr_mult = self.params["min_atr_multiplier"]
        sl_mult = self.params["sl_dist_mult"]
        df["sma_fast"] = df["close"].rolling(fast).mean()
        df["sma_slow"] = df["close"].rolling(slow).mean()

        # ATR
        df["atr"] = ta.atr(df["high"], df["low"], df["close"], length=atr_window)
        df["avg_atr"] = df["atr"].rolling(avg_atr_window).mean()

        df["signal"] = 0
        df["sl_price"] = 0.0

        if self.params["strategy"] == "long":
            # Long: crossover + high volatility
            long_cond = (
                (df["sma_fast"] > df["sma_slow"])
                & (df["sma_fast"].shift(1) <= df["sma_slow"].shift(1))
                & (df["atr"] > df["avg_atr"] * min_atr_mult)
            )
            df.loc[long_cond, "signal"] = 1
            df.loc[long_cond, "sl_price"] = df.loc[long_cond, "close"] * sl_mult
        else:
            # Short: death cross + high volatility
            short_cond = (
                (df["sma_fast"] < df["sma_slow"])
                & (df["sma_fast"].shift(1) >= df["sma_slow"].shift(1))
                & (df["atr"] > df["avg_atr"] * min_atr_mult)
            )
            df.loc[short_cond, "signal"] = -1
            df.loc[short_cond, "sl_price"] = df.loc[short_cond, "close"] * (2 - sl_mult)

        return df
