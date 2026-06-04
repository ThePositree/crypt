from __future__ import annotations

import logging

import numpy as np
import pandas as pd
from tqdm.auto import tqdm

from backtester.strategy import BaseStrategy

logger = logging.getLogger(__name__)


class RejectionStrategy(BaseStrategy):
    """Стратегия на основе rejection blocks"""

    def suggest_params(self, trial):
        return {
            "rejection_block_bars": trial.suggest_int("rejection_block_bars", 2, 4),
            "min_body_overlap": trial.suggest_float(
                "min_body_overlap", 0.1, 0.9, step=0.1
            ),
            "structure_timeframe": trial.suggest_categorical(
                "structure_timeframe", [15, 30, 60, 240]
            ),
            "body_level_tolerance": trial.suggest_float(
                "body_level_tolerance", 0.05, 0.3, step=0.05
            ),
        }

    def generate(self, df: pd.DataFrame) -> pd.DataFrame:
        """Генерирует сигналы стратегии"""
        rejection_block_bars = self.params["rejection_block_bars"]
        min_body_overlap = self.params["min_body_overlap"]
        structure_timeframe = self.params["structure_timeframe"]
        body_level_tolerance = self.params["body_level_tolerance"]

        # Инициализируем колонки
        df["signal"] = 0
        df["sl_price"] = 0.0

        # Создаем высокий таймфрейм для поиска структуры
        htf_df = self._create_htf_dataframe(df, structure_timeframe)

        # Создаем маппинг LTF -> HTF
        htf_to_ltf = self._create_htf_ltf_mapping(htf_df, df)

        iters = htf_df.index
        if logger.isEnabledFor(logging.DEBUG):
            iters = tqdm(iters, desc="Processing HTF bars", unit="bar", ascii=True)

        for htf_time in iters:
            htf_i = htf_df.index.get_loc(htf_time)
            signal, sl_price = self._check_rejection_htf(
                htf_df,
                htf_i,
                rejection_block_bars,
                min_body_overlap,
                body_level_tolerance,
            )

            if signal != 0:
                if htf_i == len(htf_df) - 1:
                    continue

                next_htf_time = htf_df.index[htf_i + 1]
                ltf_pos = htf_to_ltf.get(next_htf_time)
                if ltf_pos is None:
                    continue

                ltf_time = df.index[ltf_pos]
                df.loc[ltf_time, "signal"] = signal
                df.loc[ltf_time, "sl_price"] = sl_price

        return df

    def _create_htf_dataframe(self, df: pd.DataFrame, htf_minutes: int) -> pd.DataFrame:
        """Создает высокий таймфрейм из исходных данных"""
        freq = pd.Timedelta(minutes=htf_minutes)

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

    def _create_htf_ltf_mapping(
        self, htf_df: pd.DataFrame, ltf_df: pd.DataFrame
    ) -> dict:
        """Создает маппинг из HTF в LTF индексы (векторизованная версия)

        Для каждой HTF свечи возвращает следующую LTF свечу.
        Например: HTF 00:10 -> LTF 00:11
        """
        htf_times = htf_df.index.to_numpy()
        ltf_times = ltf_df.index.to_numpy()

        positions = np.searchsorted(ltf_times, htf_times, side="right")
        return {
            htf_time: min(pos, len(ltf_times) - 1)
            for htf_time, pos in zip(htf_times, positions, strict=True)
        }

    def _check_rejection_htf(
        self,
        htf_df: pd.DataFrame,
        htf_i: int,
        rejection_block_bars: int,
        min_body_overlap: float,
        body_level_tolerance: float,
    ) -> tuple:
        """Проверяет наличие rejection block на HTF"""
        if htf_i < rejection_block_bars:
            return 0, 0.0

        current_htf_bar = htf_df.iloc[htf_i]
        previous_htf_bar = htf_df.iloc[htf_i - 1]

        # Проверяем, что свеча медвежья
        if current_htf_bar["close"] < current_htf_bar["open"]:
            body_top = float(max(current_htf_bar["open"], current_htf_bar["close"]))
            if self._has_rejection_block(
                htf_df,
                htf_i,
                rejection_block_bars,
                min_body_overlap,
                body_top,
                body_level_tolerance,
            ):
                return -1, max(current_htf_bar["high"], previous_htf_bar["high"])

        # Проверяем, что свеча бычья
        if current_htf_bar["close"] > current_htf_bar["open"]:
            body_bottom = float(min(current_htf_bar["open"], current_htf_bar["close"]))
            if self._has_rejection_block(
                htf_df,
                htf_i,
                rejection_block_bars,
                min_body_overlap,
                body_bottom,
                body_level_tolerance,
            ):
                return 1, min(current_htf_bar["low"], previous_htf_bar["low"])

        return 0, 0.0

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
