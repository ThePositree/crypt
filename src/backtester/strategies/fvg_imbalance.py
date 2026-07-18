from __future__ import annotations

import logging

import numpy as np
import pandas as pd
from tqdm.auto import tqdm

from backtester.strategy import BaseStrategy

logger = logging.getLogger(__name__)


class FVGImbalanceStrategy(BaseStrategy):
    def suggest_params(self, trial):
        return {
            "lookback_hours": trial.suggest_int("lookback_hours", 10, 60, step=5),
            "sl_buffer_pct": 0,
            "min_fvg_range": trial.suggest_float("min_fvg_range", 0.01, 0.7, step=0.01),
            "structure_timeframe": trial.suggest_categorical(
                "structure_timeframe", [15, 30, 60, 120, 240]
            ),
            "max_fvg_count": trial.suggest_int("max_fvg_count", 1, 10),
            "risk_reward_ratio_threshold": trial.suggest_float(
                "risk_reward_ratio_threshold", 1.0, 10.0, step=0.1
            ),
        }

    def generate(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        df_3m — исходный DataFrame с таймфреймом 3 минуты.
        Стратегия:
          - Строит 1H из 3M,
          - Ищет FVG на 1H,
          - На 3M проверяет full fill этих FVG,
          - Генерирует сигнал на 3M с SL по границам 1H-FVG.
        """
        params = self.params
        lookback_hours = params.get("lookback_hours", 30)
        sl_buffer_pct = params.get("sl_buffer_pct", 0.0005)
        min_fvg_range = params.get("min_fvg_range", 0.05)
        structure_timeframe = params.get("structure_timeframe", 60)
        max_fvg_count = params.get("max_fvg_count", 2)

        df["signal"] = 0
        df["sl_price"] = 0.0

        df["volume_price_correlation"] = self.calculate_volume_price_correlation(
            df, window=10
        )
        df["long_risk_reward_ratio"] = self.calculate_risk_reward_ratio(df)
        df["short_risk_reward_ratio"] = self.calculate_risk_reward_ratio(df, short=True)
        df["volume_ratio"] = self.calculate_volume_ratio(df, window=20)
        df["consecutive_up"], df["consecutive_down"] = (
            self.calculate_consecutive_moves_efficient(df)
        )
        df["stoch_k"] = self.calculate_stoch_k(df, period=14)
        df["volatility_ratio"] = self.calculate_volatility_ratio(
            df, recent_window=10, historical_window=20
        )
        df["kurtosis"] = self.calculate_kurtosis(df, window=20)
        df["lower_shadow_ratio"] = self.calculate_lower_shadow_ratio(df)
        df["macd_histogram"] = self.calculate_macd_histogram(df)
        df["mfi"] = self.calculate_mfi(df, period=14)
        df["rsi_14"] = self.calculate_rsi_14(df)

        # === Шаг 1: Ресемплинг 3M → 1H ===
        df_1h = (
            df.resample(pd.Timedelta(minutes=structure_timeframe))
            .agg(
                {
                    "open": "first",
                    "high": "max",
                    "low": "min",
                    "close": "last",
                    "volume": "sum",
                }
            )
            .dropna()
        )

        df_1h["atr"] = self.calculate_atr(df_1h, period=14)

        # === Шаг 2: Найти все FVG на 1H ===
        fvg_list = []  # список: {start_time, end_time, bottom, top, type}
        for i in range(2, len(df_1h)):
            t = df_1h.index[i]
            t_prev2 = df_1h.index[i - 2]
            atr = df_1h["atr"].iloc[i]

            high_i = df_1h["high"].iloc[i]
            low_i = df_1h["low"].iloc[i]
            low_fvg = df_1h["low"].iloc[i - 1]
            high_fvg = df_1h["high"].iloc[i - 1]
            high_im2 = df_1h["high"].iloc[i - 2]
            low_im2 = df_1h["low"].iloc[i - 2]

            # Бычий FVG: low[i] > high[i-2]
            if low_i > high_im2:
                fvg = {
                    "start_time": t_prev2,
                    "end_time": t,
                    "bottom": high_im2,  # нижняя граница FVG
                    "top": low_i,  # верхняя граница FVG
                    "sl_price": high_fvg,
                    "type": "bullish",
                    "closed": False,
                }
            # Медвежий FVG: high[i] < low[i-2]
            elif high_i < low_im2:
                fvg = {
                    "start_time": t_prev2,
                    "end_time": t,
                    "bottom": high_i,  # нижняя граница FVG
                    "top": low_im2,  # верхняя граница FVG
                    "sl_price": low_fvg,
                    "type": "bearish",
                    "closed": False,
                }
            else:
                continue

            fvg_range = (fvg["top"] - fvg["bottom"]) / atr
            if fvg_range < min_fvg_range:
                continue

            fvg_list.append(fvg)

        if logger.isEnabledFor(logging.DEBUG):
            it = tqdm(
                total=len(df),
                desc="Signal generation",
                unit="bar",
                ascii=True,
            )
        # === Шаг 3: На 3M проверяем full fill каждого FVG ===
        for i in range(len(df)):
            if logger.isEnabledFor(logging.DEBUG):
                it.update(1)

            row = df.iloc[i]
            ts = row.name
            # пропускаем первые lookback_hours баров
            if ts < df.index.min() + pd.Timedelta(hours=lookback_hours):
                continue

            rsi_14 = row["rsi_14"]
            if rsi_14 > 60:
                continue

            current_low = row["low"]
            current_high = row["high"]
            current_open = row["open"]
            current_close = row["close"]
            volume_price_correlation = row["volume_price_correlation"]
            long_risk_reward_ratio = row["long_risk_reward_ratio"]
            short_risk_reward_ratio = row["short_risk_reward_ratio"]
            volume_ratio = row["volume_ratio"]
            consecutive_down = row["consecutive_down"]
            consecutive_up = row["consecutive_up"]
            stoch_k = row["stoch_k"]
            volatility_ratio = row["volatility_ratio"]
            kurtosis = row["kurtosis"]
            lower_shadow_ratio = row["lower_shadow_ratio"]
            macd_histogram = row["macd_histogram"]
            mfi = row["mfi"]
            cutoff_time = ts - pd.Timedelta(hours=lookback_hours)

            bullish_fvg = []
            bearish_fvg = []

            to_delete = []
            for i, fvg in enumerate(fvg_list):
                if fvg["end_time"] > ts:
                    continue

                if fvg["end_time"] < cutoff_time:
                    to_delete.append(i)
                    continue

                if fvg["closed"]:
                    to_delete.append(i)
                    continue

                if fvg["type"] == "bullish":
                    bullish_fvg.append(fvg)
                    continue

                if fvg["type"] == "bearish":
                    bearish_fvg.append(fvg)
                    continue

            for i in to_delete:
                fvg_list.pop(i)

            if len(bullish_fvg) > 0 and len(bullish_fvg) <= max_fvg_count:
                if abs(short_risk_reward_ratio) > 0.5:
                    continue

                if macd_histogram < -0.15:
                    continue

                if volatility_ratio <= 0.7:
                    continue

                if mfi < 5 or mfi > 60:
                    continue

                for fvg in bullish_fvg:
                    if current_low <= fvg["bottom"] and current_high > fvg["bottom"]:
                        fvg["closed"] = True
                        df.at[ts, "signal"] = -1
                        df.at[ts, "sl_price"] = fvg["sl_price"] * (1 + sl_buffer_pct)
                        break

            if len(bearish_fvg) > 0 and len(bearish_fvg) <= max_fvg_count:
                if consecutive_up >= 1:
                    continue

                for fvg in bearish_fvg:
                    if current_high >= fvg["top"] and current_low < fvg["top"]:
                        fvg["closed"] = True
                        df.at[ts, "signal"] = 1
                        df.at[ts, "sl_price"] = fvg["sl_price"] * (1 - sl_buffer_pct)
                        break

        return df

    def calculate_rsi_14(self, df: pd.DataFrame):
        delta = df["close"].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi

    def calculate_mfi(self, df: pd.DataFrame, period: int = 14):
        typical_price = (df["high"] + df["low"] + df["close"]) / 3
        money_flow = typical_price * df["volume"]
        positive_flow = (
            money_flow.where(typical_price > typical_price.shift(1), 0)
            .rolling(14)
            .sum()
        )
        negative_flow = (
            money_flow.where(typical_price < typical_price.shift(1), 0)
            .rolling(14)
            .sum()
        )
        return pd.Series(
            100 - (100 / (1 + positive_flow / negative_flow)), index=df.index
        )

    def calculate_macd_histogram(self, df: pd.DataFrame):
        ema_12 = df["close"].ewm(span=12).mean()
        ema_26 = df["close"].ewm(span=26).mean()
        macd_line = ema_12 - ema_26
        macd_signal = macd_line.ewm(span=9).mean()
        macd_histogram = macd_line - macd_signal
        return macd_histogram

    def calculate_lower_shadow_ratio(self, df: pd.DataFrame):
        total_range = df["high"] - df["low"]
        ratio = (df[["open", "close"]].min(axis=1) - df["low"]) / total_range
        return pd.Series(ratio, index=df.index)

    def calculate_atr(self, df: pd.DataFrame, period=14):
        high, low, close = df["high"], df["low"], df["close"]
        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(period).mean()
        return atr

    def calculate_kurtosis(self, df: pd.DataFrame, window: int = 20):
        """
        Вычисляет kurtosis для каждой свечи

        Parameters:
        -----------
        df : pd.Data.DataFrame
            DataFrame с колонкой 'close'
        window : int
            Размер окна для расчета (по умолчанию 20)

        Returns:
        --------
        pd.Series
            Kurtosis для каждой строки
        """
        returns = df["close"].pct_change()

        rolling_kurtosis = returns.rolling(window=window).kurt()

        rolling_kurtosis = rolling_kurtosis.fillna(0)

        return rolling_kurtosis

    def calculate_volatility_ratio(
        self, df: pd.DataFrame, recent_window: int = 10, historical_window: int = 20
    ):
        """
        Вычисляет volatility_ratio для каждой свечи
        """
        price_changes = df["close"].pct_change()

        recent_volatility = price_changes.rolling(window=recent_window).std()
        historical_volatility = price_changes.rolling(window=historical_window).std()

        volatility_ratio = recent_volatility / historical_volatility
        volatility_ratio = volatility_ratio.fillna(1.0)

        return volatility_ratio

    def calculate_stoch_k(self, df: pd.DataFrame, period: int = 14):
        lowest_low = df["low"].rolling(window=period).min()
        highest_high = df["high"].rolling(window=period).max()

        stoch_k = 100 * (df["close"] - lowest_low) / (highest_high - lowest_low)

        stoch_k = stoch_k.fillna(50)

        return stoch_k

    def calculate_consecutive_moves_efficient(self, df: pd.DataFrame):
        price_changes = df["close"].pct_change()

        up_groups = (price_changes <= 0).cumsum()
        down_groups = (price_changes >= 0).cumsum()

        consecutive_up = price_changes.groupby(up_groups).cumcount() + 1
        consecutive_down = price_changes.groupby(down_groups).cumcount() + 1

        consecutive_up = consecutive_up.where(price_changes > 0, 0)
        consecutive_down = consecutive_down.where(price_changes < 0, 0)

        return consecutive_up, consecutive_down

    def calculate_volume_ratio(self, df: pd.DataFrame, window: int = 20):
        volume_ma = df["volume"].rolling(window=window).mean()
        volume_ratio = df["volume"] / volume_ma
        volume_ratio = volume_ratio.fillna(1.0)
        return volume_ratio

    def calculate_risk_reward_ratio(
        self, df: pd.DataFrame, window: int = 20, short=False
    ):
        support, resistance = self.calculate_support_resistance_for_df(df, window)

        if short:
            risk_distance = (resistance - df["close"]) / df["close"]
            reward_distance = (df["close"] - support) / df["close"]
        else:
            risk_distance = (df["close"] - support) / df["close"]
            reward_distance = (resistance - df["close"]) / df["close"]

        risk_reward_ratio = np.where(
            risk_distance > 0, reward_distance / risk_distance, 0
        )

        return risk_reward_ratio

    def calculate_support_resistance_for_df(self, df: pd.DataFrame, window: int = 20):
        rolling_low = df["low"].rolling(window=window).min()
        rolling_high = df["high"].rolling(window=window).max()

        return rolling_low, rolling_high

    def calculate_volume_price_correlation(self, df: pd.DataFrame, window: int = 10):
        price_changes = df["close"].pct_change()
        volume_changes = df["volume"].pct_change()

        rolling_corr = price_changes.rolling(window=window).corr(volume_changes)

        return rolling_corr.fillna(0)
