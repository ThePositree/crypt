from __future__ import annotations

import logging
from collections import namedtuple

import numpy as np
import pandas as pd
from tqdm.auto import tqdm

from backtester.strategy import BaseStrategy

logger = logging.getLogger(__name__)


# Namedtuple для хранения информации о фракталах
FractalInfo = namedtuple("FractalInfo", ["time", "value", "index"])


class FractalRejectionStrategy(BaseStrategy):
    """Стратегия на основе снятия фракталов и rejection blocks"""

    def suggest_params(self, trial):
        return {
            "fractal_period": trial.suggest_int("fractal_period", 3, 7),
            "rejection_block_bars": trial.suggest_int("rejection_block_bars", 2, 4),
            "min_body_overlap": trial.suggest_float(
                "min_body_overlap", 0.1, 0.9, step=0.1
            ),
            "trading_start_hour": trial.suggest_int("trading_start_hour", 5, 8),
            "trading_end_hour": trial.suggest_int("trading_end_hour", 18, 22),
            "structure_timeframe": trial.suggest_categorical(
                "structure_timeframe", [15, 30, 60, 240]
            ),
            "fractal_lookup": trial.suggest_int("fractal_lookup", 10, 50, step=5),
            "body_level_tolerance": trial.suggest_float(
                "body_level_tolerance", 0.05, 0.3, step=0.05
            ),
        }

    def generate(self, df: pd.DataFrame) -> pd.DataFrame:
        """Генерирует сигналы стратегии"""
        fractal_period = self.params["fractal_period"]
        rejection_block_bars = self.params["rejection_block_bars"]
        min_body_overlap = self.params["min_body_overlap"]
        trading_start_hour = self.params["trading_start_hour"]
        trading_end_hour = self.params["trading_end_hour"]
        structure_timeframe = self.params["structure_timeframe"]
        fractal_lookup = self.params["fractal_lookup"]
        body_level_tolerance = self.params["body_level_tolerance"]

        # Инициализируем колонки
        df["signal"] = 0
        df["sl_price"] = 0.0

        df["macd_histogram"] = self.calculate_macd_histogram(df)
        df["mfi"] = self.calculate_mfi(df, period=14)
        df["bb_position"] = self.calculate_bb_position(df, period=20)

        # Создаем высокий таймфрейм для поиска структуры
        htf_df = self._create_htf_dataframe(df, structure_timeframe)

        # Вычисляем фракталы на высоком таймфрейме
        htf_df["fractal_high"] = self._calculate_fractals(
            htf_df["high"], fractal_period, "high"
        )
        htf_df["fractal_low"] = self._calculate_fractals(
            htf_df["low"], fractal_period, "low"
        )

        # Создаем систему отслеживания активных фракталов
        active_fractals = {
            "high": [],  # [FractalInfo(time, value, index), ...]
            "low": [],  # [FractalInfo(time, value, index), ...]
        }

        # Определяем торговые часы
        df["hour"] = df.index.hour
        trading_hours = (df["hour"] >= trading_start_hour) & (
            df["hour"] <= trading_end_hour
        )

        ltf_to_htf = self._create_ltf_htf_mapping(df, htf_df)

        iters = df[trading_hours].index
        if logger.isEnabledFor(logging.DEBUG):
            iters = tqdm(iters, desc="Processing LTF bars", unit="bar", ascii=True)

        for ltf_idx in iters:
            # Получаем соответствующий HTF индекс
            htf_i = ltf_to_htf.get(ltf_idx)
            if htf_i is None:
                continue

            # Проверяем снятие фракталов на HTF
            signal, sl_price = self._check_fractal_break_and_rejection_htf_online(
                htf_df,
                htf_i,
                fractal_period,
                fractal_lookup,
                rejection_block_bars,
                min_body_overlap,
                body_level_tolerance,
                active_fractals,
            )

            if signal != 0:
                df.loc[ltf_idx, "signal"] = signal
                df.loc[ltf_idx, "sl_price"] = sl_price

        return df

    def _calculate_fractals(
        self, series: pd.Series, period: int, fractal_type: str
    ) -> pd.Series:
        """Вычисляет фракталы"""
        fractals = pd.Series(False, index=series.index)

        for i in range(period, len(series) - period):
            if fractal_type == "high":
                # Проверяем, является ли точка локальным максимумом
                is_fractal = True
                for j in range(1, period + 1):
                    if (
                        series.iloc[i] <= series.iloc[i - j]
                        or series.iloc[i] <= series.iloc[i + j]
                    ):
                        is_fractal = False
                        break
            else:  # low
                # Проверяем, является ли точка локальным минимумом
                is_fractal = True
                for j in range(1, period + 1):
                    if (
                        series.iloc[i] >= series.iloc[i - j]
                        or series.iloc[i] >= series.iloc[i + j]
                    ):
                        is_fractal = False
                        break

            fractals.iloc[i] = is_fractal

        return fractals

    def _create_htf_dataframe(self, df: pd.DataFrame, htf_minutes: int) -> pd.DataFrame:
        """Создает высокий таймфрейм из исходных данных"""
        # Используем pd.Timedelta для точного resample
        freq = pd.Timedelta(minutes=htf_minutes)

        # Resample данные
        htf_df = (
            df.resample(freq)
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

        return htf_df

    def _create_ltf_htf_mapping(
        self, ltf_df: pd.DataFrame, htf_df: pd.DataFrame
    ) -> dict:
        """Создает маппинг между LTF и HTF индексами (векторизованная версия)"""
        htf_times = htf_df.index.to_numpy()
        ltf_times = ltf_df.index.to_numpy()

        # Vectorized search for next LTF candle for each HTF candle
        positions = np.searchsorted(ltf_times, htf_times, side="right")
        return {
            htf_time: min(pos, len(ltf_times) - 1)
            for htf_time, pos in zip(htf_times, positions, strict=True)
        }

    def _check_fractal_break_and_rejection_htf_online(
        self,
        htf_df: pd.DataFrame,
        htf_i: int,
        fractal_period: int,
        fractal_lookup: int,
        rejection_block_bars: int,
        min_body_overlap: float,
        body_level_tolerance: float,
        active_fractals: dict,
    ) -> tuple:
        """Проверяет снятие фрактала на HTF с онлайн-отслеживанием активных фракталов"""
        if htf_i < fractal_period + rejection_block_bars:
            return 0, 0.0

        current_htf_bar = htf_df.iloc[htf_i]
        current_time = htf_df.index[htf_i]

        # Обновляем список активных фракталов
        self._update_active_fractals(
            htf_df,
            htf_i,
            fractal_period,
            fractal_lookup,
            active_fractals,
            current_time,
        )

        # Проверяем снятие верхнего фрактала на HTF (для short)
        if self._check_fractal_break_online(
            htf_df, htf_i, "high", active_fractals["high"]
        ):
            # Проверяем, что свеча, снявшая фрактал, была медвежьей
            if current_htf_bar["close"] < current_htf_bar["open"]:
                body_top = max(current_htf_bar["open"], current_htf_bar["close"])
                if self._has_rejection_block(
                    htf_df,
                    htf_i,
                    rejection_block_bars,
                    min_body_overlap,
                    body_top,
                    body_level_tolerance,
                ):
                    return -1, current_htf_bar["high"]  # Short signal

        # Проверяем снятие нижнего фрактала на HTF (для long)
        if self._check_fractal_break_online(
            htf_df, htf_i, "low", active_fractals["low"]
        ):
            if current_htf_bar["close"] > current_htf_bar["open"]:
                body_bottom = min(current_htf_bar["open"], current_htf_bar["close"])
                if self._has_rejection_block(
                    htf_df,
                    htf_i,
                    rejection_block_bars,
                    min_body_overlap,
                    body_bottom,
                    body_level_tolerance,
                ):
                    return 1, current_htf_bar["low"]  # Long signal

        return 0, 0.0

    def _update_active_fractals(
        self,
        htf_df: pd.DataFrame,
        current_idx: int,
        fractal_period: int,
        fractal_lookup: int,
        active_fractals: dict,
        current_time: pd.Timestamp,
    ):
        """Обновляет список активных фракталов"""
        if current_idx < fractal_period:
            return

        cutoff_time = current_time - pd.Timedelta(
            minutes=fractal_lookup * htf_df.index.freq.delta.total_seconds() / 60
        )

        for fractal_type in active_fractals.keys():
            to_delete = []
            fractals = active_fractals[fractal_type]
            for i in range(len(fractals)):
                if fractals[i].time < cutoff_time:
                    to_delete.append(i)

            deleted = 0
            for i in to_delete:
                fractals.pop(i - deleted)
                deleted += 1

        prev_bar = htf_df.iloc[current_idx - 1]
        if prev_bar["fractal_high"]:
            fractal_time = prev_bar.name
            fractal_value = prev_bar["high"]
            active_fractals["high"].append(
                FractalInfo(fractal_time, fractal_value, current_idx - 1)
            )

        if prev_bar["fractal_low"]:
            fractal_time = prev_bar.name
            fractal_value = prev_bar["low"]
            active_fractals["low"].append(
                FractalInfo(fractal_time, fractal_value, current_idx - 1)
            )

    def _check_fractal_break_online(
        self,
        htf_df: pd.DataFrame,
        current_idx: int,
        fractal_type: str,
        active_fractals_list: list,
    ) -> bool:
        """Проверяет снятие активных фракталов"""
        current_htf_bar = htf_df.iloc[current_idx]

        for i, fractal in enumerate(active_fractals_list):
            if fractal.index >= current_idx:
                continue

            broken = False
            if fractal_type == "high":
                if (
                    current_htf_bar["high"] > fractal.value
                    and current_htf_bar["close"] < fractal.value
                ):
                    broken = True
            else:  # low
                if (
                    current_htf_bar["low"] < fractal.value
                    and current_htf_bar["close"] > fractal.value
                ):
                    broken = True

            if broken:
                active_fractals_list.pop(i)
                return True

        return False

    def _has_rejection_block(
        self,
        df: pd.DataFrame,
        current_idx: int,
        block_bars: int,
        min_overlap: float,
        body_level: float,
        body_level_tolerance: float,
    ) -> bool:
        """Проверяет наличие rejection block и уровень тела свечи (оптимизированная версия)"""
        if current_idx < block_bars:
            return False

        # Получаем тела свечей для анализа (векторизованно)
        start_idx = current_idx - block_bars
        end_idx = current_idx

        opens = df["open"].iloc[start_idx:end_idx].values
        closes = df["close"].iloc[start_idx:end_idx].values

        body_tops = np.maximum(opens, closes)
        body_bottoms = np.minimum(opens, closes)

        if len(body_tops) < 2:
            return False

        max_bottom = np.max(body_bottoms)
        min_top = np.min(body_tops)

        if min_top <= max_bottom:
            return False

        overlap_size = min_top - max_bottom
        total_range = np.max(body_tops) - np.min(body_bottoms)
        overlap_ratio = overlap_size / total_range if total_range > 0 else 0

        if overlap_ratio < min_overlap:
            return False

        avg_body_top = np.mean(body_tops)
        avg_body_bottom = np.mean(body_bottoms)

        distance_to_top = abs(body_level - avg_body_top)
        distance_to_bottom = abs(body_level - avg_body_bottom)

        if distance_to_top < distance_to_bottom:
            body_top_range = np.max(body_tops) - np.min(body_tops)
            return body_top_range <= total_range * body_level_tolerance
        else:
            body_bottom_range = np.max(body_bottoms) - np.min(body_bottoms)
            return body_bottom_range <= total_range * body_level_tolerance

    def calculate_macd_histogram(self, df: pd.DataFrame):
        ema_12 = df["close"].ewm(span=12).mean()
        ema_26 = df["close"].ewm(span=26).mean()
        macd_line = ema_12 - ema_26
        macd_signal = macd_line.ewm(span=9).mean()
        macd_histogram = macd_line - macd_signal
        return macd_histogram

    def calculate_mfi(self, df: pd.DataFrame, period: int = 14):
        typical_price = (df["high"] + df["low"] + df["close"]) / 3
        money_flow = typical_price * df["volume"]
        positive_flow = (
            money_flow.where(typical_price > typical_price.shift(1), 0)
            .rolling(period)
            .sum()
        )
        negative_flow = (
            money_flow.where(typical_price < typical_price.shift(1), 0)
            .rolling(period)
            .sum()
        )
        return pd.Series(
            100 - (100 / (1 + positive_flow / negative_flow)), index=df.index
        )

    def calculate_bb_position(self, df: pd.DataFrame, period: int = 20):
        bb_middle = df["close"].rolling(period).mean()
        bb_std = df["close"].rolling(period).std()
        bb_upper = bb_middle + (bb_std * 2)
        bb_lower = bb_middle - (bb_std * 2)
        bb_position = (df["close"] - bb_lower) / (bb_upper - bb_lower)
        return bb_position
