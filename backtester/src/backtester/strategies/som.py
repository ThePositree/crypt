from __future__ import annotations

import logging
import pickle

import numpy as np
import optuna
import pandas as pd
from tqdm.auto import tqdm

from backtester.strategy import BaseStrategy

logger = logging.getLogger(__name__)


class SOMStrategy(BaseStrategy):
    def __init__(self, params):
        super().__init__(params)

        with open(params["som_path"], "rb") as f:
            self.som = pickle.load(f)

        with open(params["scaler_path"], "rb") as f:
            self.scaler = pickle.load(f)

        with open(params["dens_map_path"], "rb") as f:
            self.dens_map = pickle.load(f)

        self.feature_columns = [
            "body_ratio",
            "is_green",
            "volume_ma_ratio",
            "price_position_in_range",
            "dist_to_sma_pct",
            "price_below_sma",
            "trend_risk_reward",
            "rsi_14",
            "breakout_high_5",
            "breakout_low_5",
            "fakeout_down",
            "volume_drop_before_break",
            "fvg_signed_strength",
            "ob_size_ratio_to_atr",
            "ob_retests",
            "ob_impulse_confirmation",
            "ob_liquidity_proximity",
            "bull_bear_score",
        ]

    @staticmethod
    def suggest_params(trial: optuna.Trial):
        return {
            "som_path": "data/som/som_2.pkl",
            "scaler_path": "data/som/scaler_2.pkl",
            "dens_map_path": "data/som/dens_map_2.pkl",
            "sl_mult": trial.suggest_float("sl_mult", 1.0, 8.0, step=0.5),
            "cooldown": trial.suggest_int("cooldown", 1, 10),
            "atr_window": trial.suggest_int("atr_window", 10, 30),
            "dens_threshold": trial.suggest_float(
                "dens_threshold", 0.3, 0.5, step=0.01
            ),
        }

    def generate(self, df: pd.DataFrame) -> pd.DataFrame:
        atr_window = self.params.get("atr_window", 14)
        dens_threshold = self.params.get("dens_threshold", 0.5)
        cooldown = self.params.get("cooldown", 5)
        sl_mult = self.params.get("sl_mult", 2)

        atr = self.calculate_atr(df, atr_window)

        logger.debug("Retrieving signal clusters...")
        signal_clusters = set()
        for x, y in zip(*np.where(self.dens_map >= dens_threshold)):
            signal_clusters.add((x, y))

        logger.debug("Processing features...")
        df = SOMStrategy.create_features_from_scratch(df)
        X = df[self.feature_columns]
        logger.debug("Features head:")
        logger.debug(X.head())

        X_scaled = self.scaler.transform(X)

        logger.debug("Labeling SOM...")
        i = 0
        y = []
        if logger.isEnabledFor(logging.DEBUG):
            it = tqdm(
                total=len(X_scaled),
                desc="SOM signal generation",
                unit="bar",
                ascii=True,
            )
        while i < len(X_scaled):
            signal = self.som.winner(X_scaled[i]) in signal_clusters
            if signal:
                i += max(1, cooldown)
                y.append(1)
                y.extend([0] * (cooldown - 1))
            else:
                i += 1
                y.append(0)

            if logger.isEnabledFor(logging.DEBUG):
                it.update(1)

        logger.debug("SOM strategy generated signal: {}".format(len(y)))
        df["signal"] = y
        df["sl_price"] = df["close"] - sl_mult * atr

        return df

    @staticmethod
    def calculate_atr(df: pd.DataFrame, period=14):
        high, low, close = df["high"], df["low"], df["close"]
        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(period).mean()
        return atr

    @staticmethod
    def calculate_fvg_signed_strength(df: pd.DataFrame, atr_period=14):
        """
        Рассчитывает силу FVG, нормализованную относительно ATR, с направлением:
            - Положительное значение: бычий FVG (low[i] > high[i-2])
            - Отрицательное значение: медвежий FVG (high[i] < low[i-2])
            - 0: FVG отсутствует

        Возвращает: pd.Series — процент от ATR со знаком
        """
        # Рассчитываем ATR, если его ещё нет
        atr = SOMStrategy.calculate_atr(df, period=atr_period)

        # Инициализируем признак
        fvg_signed_strength = pd.Series(
            np.zeros(len(df)), dtype=float, name="fvg_signed_strength", index=df.index
        )

        # Бычий FVG: low[i] > high[i-2] → gap = low[i] - high[i-2] → положительный
        bull_fvg_mask = df["low"] > df["high"].shift(2)
        bull_gap = df["low"] - df["high"].shift(2)
        fvg_signed_strength.loc[bull_fvg_mask] = bull_gap / atr

        # Медвежий FVG: high[i] < low[i-2] → gap = low[i-2] - high[i] → отрицательный
        bear_fvg_mask = df["high"] < df["low"].shift(2)
        bear_gap = df["low"].shift(2) - df["high"]
        fvg_signed_strength.loc[bear_fvg_mask] = -(bear_gap / atr)

        return fvg_signed_strength

    @staticmethod
    def detect_order_blocks(df: pd.DataFrame, lookback=3):
        """
        Order Block (OB) — Блок ордеров
        Бычий OB: последняя восходящая свеча перед резким падением (медвежий импульс)
        Медвежий OB: последняя нисходящая свеча перед резким ростом (бычий импульс)

        Возвращает:
            - 1: бычий OB (зона поддержки)
            - -1: медвежий OB (зона сопротивления)
            - 0: нет OB
        """
        body = df["close"] - df["open"]
        is_bullish = body > 0
        is_bearish = body < 0

        atr = SOMStrategy.calculate_atr(df, period=14)

        # Импульс: сильное движение после свечи
        impulse_down = (
            df["low"].rolling(window=lookback).min().shift(-2) < df["low"] - atr * 1.5
        )
        impulse_up = (
            df["high"].rolling(window=lookback).max().shift(-2) > df["high"] + atr * 1.5
        )

        # Бычий OB: бычья свеча -> затем медвежий импульс
        bullish_ob = is_bullish & impulse_down.shift(1)
        # Медвежий OB: медвежья свеча -> затем бычий импульс
        bearish_ob = is_bearish & impulse_up.shift(1)

        ob = pd.Series(np.zeros(len(df)), dtype=int, name="ob", index=df.index)
        ob.loc[bullish_ob] = 1
        ob.loc[bearish_ob] = -1

        # Дополнительно: зона OB — это high/low самой свечи OB
        ob_zone_high = pd.Series(
            np.full(len(df), np.nan), dtype=float, name="ob_zone_high", index=df.index
        )
        ob_zone_low = pd.Series(
            np.full(len(df), np.nan), dtype=float, name="ob_zone_low", index=df.index
        )
        ob_zone_high.loc[ob != 0] = df["high"]
        ob_zone_low.loc[ob != 0] = df["low"]

        return ob, ob_zone_high, ob_zone_low

    @staticmethod
    def calculate_ob_size_ratio_to_atr(
        df: pd.DataFrame, order_blocks: pd.Series, atr_period=14
    ):
        """
        Рассчитывает отношение размера OB-свечи к ATR на момент её формирования.
        Размер OB = high - low свечи, на которой сформировался OB.

        Возвращает: pd.Series — отношение (0 если OB нет)
        """
        atr = SOMStrategy.calculate_atr(df, period=atr_period)

        # Размер OB-свечи
        df["ob_range"] = df["high"] - df["low"]

        # Отношение к ATR
        df["ob_size_ratio_to_atr"] = np.where(
            (order_blocks != 0) & (atr > 0), df["ob_range"] / atr, 0.0
        )

        return df["ob_size_ratio_to_atr"]

    def detect_ob_retest(
        df: pd.DataFrame,
        order_blocks: pd.Series,
        ob_zone_high: pd.Series,
        ob_zone_low: pd.Series,
    ):
        """
        Определяет, вернулась ли цена в зону Order Block (ретест).
        Значение 1 присваивается на момент ПЕРВОГО касания OB-зоны после её формирования.
        Без lookahead — использует только прошлые и текущие данные.

        Возвращает: pd.Series — 1 если на текущей свече произошел ретест OB, 0 иначе
        """
        # Инициализируем признак
        ob_has_retest = pd.Series(
            np.zeros(len(df)), dtype=int, name="ob_has_retest", index=df.index
        )

        # Создаем словарь: для каждого OB храним его зону и флаг, был ли ретест
        # Формат: {index: {'high': value, 'low': value, 'retested': False}}
        active_ob_zones = {}

        for i in range(len(df)):
            idx = df.index[i]
            current_ob = order_blocks[idx]
            current_high = df.at[idx, "high"]
            current_low = df.at[idx, "low"]

            # Если на текущей свече сформировался OB — добавляем в активные зоны
            if current_ob != 0:
                ob_high = ob_zone_high[idx]
                ob_low = ob_zone_low[idx]
                active_ob_zones[idx] = {
                    "pos": i,
                    "high": ob_high,
                    "low": ob_low,
                }

            # Проверяем все активные OB-зоны (сформированные РАНЕЕ)
            for ob_idx, zone in sorted(
                active_ob_zones.items(), key=lambda item: item[1]["pos"], reverse=True
            ):
                if idx == ob_idx:
                    # Пропускаем текущую свечу — она уже проверена
                    continue

                # Проверяем, касается ли текущая свеча OB-зоны
                touches_ob = (current_low <= zone["high"]) and (
                    current_high >= zone["low"]
                )

                if touches_ob:
                    # Первое касание — ставим 1 на текущей свече
                    ob_has_retest[idx] = 1

                    # После касания — удаляем OB из активных
                    del active_ob_zones[ob_idx]

        return ob_has_retest

    @staticmethod
    def calculate_ob_impulse_confirmation_signed_atr(
        df: pd.DataFrame, ordered_blocks: pd.Series, impulse_bars=3, atr_period=14
    ):
        """
        Рассчитывает силу импульса после формирования Order Block (OB), нормализованную по ATR.
        Значение появляется на свече impulse_bars после OB — без lookahead.

        Формула:
            impulse = close[i + impulse_bars] - close[i]
            normalized = (impulse / atr[i])
            signed = normalized * ob_direction

        Возвращает: pd.Series — направленная сила импульса в % от ATR (0 если OB нет или данных недостаточно)
        """
        atr = SOMStrategy.calculate_atr(df, period=atr_period)

        # Инициализируем признак
        result = pd.Series(
            np.zeros(len(df)),
            index=df.index,
            name="ob_impulse_confirmation_signed_atr_pct",
        )

        # Находим индексы, где есть OB
        ob_indices = df.index[ordered_blocks != 0].tolist()

        for idx in ob_indices:
            current_pos = df.index.get_loc(idx)
            future_pos = current_pos + impulse_bars

            # Проверяем, что не вышли за границы
            if future_pos >= len(df):
                continue

            future_idx = df.index[future_pos]

            entry_close = df.at[idx, "close"]
            future_close = df.at[future_idx, "close"]
            atr_at_ob = atr[idx]
            ob_direction = ordered_blocks[idx]

            # Считаем импульс
            impulse = future_close - entry_close

            # Нормализуем по ATR на момент OB
            if atr_at_ob > 0:
                normalized_impulse = impulse / atr_at_ob
            else:
                normalized_impulse = 0.0

            # Применяем знак направления OB
            signed_impulse = normalized_impulse * ob_direction

            # Записываем значение НА СВЕЧЕ ИМПУЛЬСА (i + impulse_bars)
            result.at[future_idx] = signed_impulse

        return result

    @staticmethod
    def calculate_ob_liquidity_proximity(
        df: pd.DataFrame,
        ordered_blocks: pd.Series,
        ob_zone_high: pd.Series,
        ob_zone_low: pd.Series,
        atr_period=14,
    ):
        """
        Рассчитывает расстояние от Order Block до ближайшей зоны ликвидности (последний HH/LL),
        нормализованное по ATR, со знаком.

        Для бычьего OB: расстояние до последнего LL → положительное (ликвидность снизу)
        Для медвежьего OB: расстояние до последнего HH → отрицательное (ликвидность сверху)

        Возвращает: pd.Series — расстояние от ATR (0 если OB нет или ликвидность не найдена)
        """
        atr = SOMStrategy.calculate_atr(df, period=atr_period)

        # Инициализируем признак
        result = pd.Series(
            np.zeros(len(df)),
            dtype=float,
            index=df.index,
            name="ob_proximity_to_liquidity_zone",
        )

        # Создаем колонки для HH и LL
        is_hh = (df["high"] > df["high"].shift(1)) & (
            df["high"].shift(1) > df["high"].shift(2)
        )
        is_ll = (df["low"] < df["low"].shift(1)) & (
            df["low"].shift(1) < df["low"].shift(2)
        )

        last_hh_val = np.nan
        last_ll_val = np.nan

        # Рассчитываем признак для каждого OB
        for i in range(len(df)):
            idx = df.index[i]

            ob_direction = ordered_blocks[idx]
            if ob_direction == 0:
                continue

            ob_high = ob_zone_high[idx]
            ob_low = ob_zone_low[idx]
            atr_val = atr[idx]

            if pd.isna(ob_high) or pd.isna(ob_low) or atr_val <= 0:
                continue

            if is_hh[idx]:
                last_hh_val = df.at[idx, "high"]
            if is_ll[idx]:
                last_ll_val = df.at[idx, "low"]

            distance = np.nan
            signed_distance = np.nan

            if ob_direction == 1:  # Бычий OB → ищем расстояние до последнего LL
                if pd.notna(last_ll_val) and last_ll_val < ob_low:
                    distance = ob_low - last_ll_val
                    signed_distance = distance  # Положительное — ликвидность снизу
                else:
                    continue
            elif ob_direction == -1:  # Медвежий OB → ищем расстояние до последнего HH
                if pd.notna(last_hh_val) and last_hh_val > ob_high:
                    distance = last_hh_val - ob_high
                    signed_distance = -distance  # Отрицательное — ликвидность сверху
                else:
                    continue

            # Нормализуем по ATR
            normalized = signed_distance / atr_val
            result.at[idx] = normalized

        return result

    @staticmethod
    def calculate_adx(df: pd.DataFrame, period=14):
        """
        Рассчитывает ADX, +DI, -DI.

        Параметры:
        - df: DataFrame с 'high', 'low', 'close'
        - period: период сглаживания (обычно 14)

        Возвращает:
        - DataFrame с колонками: 'adx', '+di', '-di'
        """
        high = df["high"]
        low = df["low"]
        close = df["close"]

        # 1. True Range (TR)
        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

        # 2. +DM и -DM
        plus_dm = high.diff()
        minus_dm = low.diff().abs()

        # Только если рост больше предыдущего минимума
        plus_dm = np.where((plus_dm > minus_dm) & (plus_dm > 0), plus_dm, 0)

        minus_dm = np.where((minus_dm > plus_dm) & (minus_dm > 0), minus_dm, 0)

        # 3. Сглаживаем TR, +DM, -DM (Wilders Smoothing)
        def wilder_smooth(series: pd.Series, period: int):
            smoothed = np.zeros(len(series))
            smoothed[period - 1] = series[:period].mean()  # начальное значение
            for i in range(period, len(series)):
                smoothed[i] = (smoothed[i - 1] * (period - 1) + series[i]) / period
            return smoothed

        tr_smooth = wilder_smooth(tr.values, period)
        plus_dm_smooth = wilder_smooth(plus_dm, period)
        minus_dm_smooth = wilder_smooth(minus_dm, period)

        # 4. +DI и -DI
        plus_di = pd.Series(plus_dm_smooth / tr_smooth, index=df.index, name="plus_di")
        minus_di = pd.Series(
            minus_dm_smooth / tr_smooth, index=df.index, name="minus_di"
        )

        # 5. DX и ADX
        dx = abs(plus_di - minus_di) / (plus_di + minus_di + 1e-6)
        adx = pd.Series(data=wilder_smooth(dx, period), index=df.index, name="adx")

        return adx, plus_di, minus_di

    @staticmethod
    def calculate_adx_slope(df: pd.DataFrame, adx: pd.Series, slope_window=5):
        def rolling_slope(series: pd.Series, window=slope_window):
            x = np.arange(window)
            slopes = []
            for i in range(len(series)):
                if i < window:
                    slopes.append(0.0)
                    continue
                y = series.iloc[i - window : i].values
                if np.isnan(y).any() or len(y) < 2:
                    slopes.append(0.0)
                    continue
                # Линейная регрессия: y = kx + b
                k = np.polyfit(x, y, 1)[0]
                slopes.append(k)
            return pd.Series(slopes, index=series.index)

        adx_series = pd.Series(adx, index=df.index)
        adx_slope = rolling_slope(adx_series, window=slope_window)

        # 3. Ускорение наклона (вторая производная — опционально)
        adx_accel = adx_slope.diff()
        return adx_slope, adx_accel

    @staticmethod
    def calculate_bull_bear_score(
        df: pd.DataFrame,
        price_slope: pd.Series,
        adx: pd.Series,
        plus_di: pd.Series,
        minus_di: pd.Series,
        long_window=60,
        short_window=14,
    ):
        """
        Возвращает единый признак от -1 до +1:
        +1 = сильно бычий, -1 = сильно медвежий.
        """
        score = pd.Series(0.0, index=df.index)

        # 1. Направление скользящей средней (долгосрочное)
        ema_fast = df["close"].ewm(span=short_window).mean()
        ema_slow = df["close"].ewm(span=long_window).mean()
        ma_trend = (ema_fast > ema_slow).astype(int) * 2 - 1

        # 2. Угол тренда (наклон линейной регрессии)
        slope_norm = (price_slope - price_slope.rolling(long_window).min()) / (
            price_slope.rolling(long_window).max()
            - price_slope.rolling(long_window).min()
            + 1e-6
        )
        slope_score = slope_norm * 2 - 1  # [-1, 1]

        # 3. ADX: направление и сила
        di_diff = (plus_di - minus_di) / (plus_di + minus_di + 1e-6)
        adx_strength = adx / 0.5  # нормализуем (ADX ~ 50 = макс. сила)
        di_score = di_diff * (adx_strength.clip(upper=1.0))

        # 4. Закрытие относительно диапазона
        close_pos = (df["close"] - df["low"]) / (df["high"] - df["low"] + 1e-6)
        range_score = (close_pos - 0.5) * 2

        # 5. Объём в зелёных/красных свечах
        up_volume = pd.Series(
            np.where(df["close"] > df["open"], df["volume"], 0), index=df.index
        )
        down_volume = pd.Series(
            np.where(df["close"] < df["open"], df["volume"], 0), index=df.index
        )
        vol_ratio = (up_volume.rolling(10).sum() - down_volume.rolling(10).sum()) / (
            up_volume.rolling(10).sum() + down_volume.rolling(10).sum() + 1e-6
        )
        vol_score = vol_ratio.fillna(0)

        score = (
            0.3 * ma_trend
            + 0.2 * slope_score
            + 0.25 * di_score
            + 0.15 * range_score
            + 0.1 * vol_score
        )

        score = score.clip(-1, 1)

        return score

    @staticmethod
    def create_features_from_scratch(df: pd.DataFrame):
        feat = df.copy()

        # 1. Базовые соотношения цен
        feat["body"] = df["close"] - df["open"]
        feat["upper_shadow"] = df["high"] - df[["open", "close"]].max(axis=1)
        feat["lower_shadow"] = df[["open", "close"]].min(axis=1) - df["low"]
        feat["range"] = df["high"] - df["low"]

        # 2. Относительные размеры
        feat["body_ratio"] = np.where(
            feat["range"] > 0, feat["body"] / feat["range"], 0
        )
        feat["upper_shadow_ratio"] = np.where(
            feat["range"] > 0, feat["upper_shadow"] / feat["range"], 0
        )
        feat["lower_shadow_ratio"] = np.where(
            feat["range"] > 0, feat["lower_shadow"] / feat["range"], 0
        )

        # 3. Направление и тип свечи
        feat["lower_shadow_long_ratio"] = feat["lower_shadow"] / (
            feat["upper_shadow"] + feat["lower_shadow"]
        )

        # 4. Объём
        feat["volume_ma_ratio"] = df["volume"] / df["volume"].rolling(20).mean()

        # 6. Тренд (скользящие средние)
        feat["price_position_in_range"] = (df["close"] - df["low"]) / (
            df["high"] - df["low"] + 1e-6
        )

        sma_20 = df["close"].rolling(20).mean()

        feat["dist_to_sma_pct"] = (df["low"] - sma_20) / sma_20
        feat["price_below_sma"] = (df["close"] < sma_20).astype(int)

        def rolling_slope(series, w=20):
            x = np.arange(w)
            slopes = []
            for i in range(len(series)):
                if i < w:
                    slopes.append(0.0)
                    continue
                y = series.iloc[i - w : i].values
                if np.isnan(y).any():
                    slopes.append(0.0)
                    continue
                k = np.polyfit(x, y, 1)[0]
                slopes.append(k)
            return pd.Series(slopes, index=series.index)

        atr = SOMStrategy.calculate_atr(df, period=20)

        trend_slope_20 = rolling_slope(df["close"], 20)
        feat["trend_risk_reward"] = trend_slope_20 / atr

        def rsi_fast(series: pd.Series, period=14):
            delta = series.diff()
            gain = (delta.where(delta > 0, 0)).rolling(period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
            rs = gain / loss.replace(0, 1e-6)
            return 100 - (100 / (1 + rs))

        feat["rsi_14"] = rsi_fast(df["close"], 14) / 100

        feat["breakout_high_5"] = (
            df["high"] > df["high"].rolling(5).max().shift(1)
        ).astype(int)
        feat["breakout_low_5"] = (
            df["low"] < df["low"].rolling(5).min().shift(1)
        ).astype(int)
        feat["fakeout_down"] = (
            (df["low"] < df["low"].rolling(5).min().shift(1))
            & (df["close"] > df["low"].rolling(5).min().shift(1))
        ).astype(int)
        feat["volume_drop_before_break"] = (
            (df["volume"] < df["volume"].rolling(10).mean() * 0.5)
            & feat["breakout_high_5"]
        ).astype(int)

        price_mid = (df["high"] + df["low"]) / 2
        feat["vol_price_corr"] = (
            feat["volume"]
            .rolling(5)
            .corr(price_mid, numeric_only=True)
            .replace(np.inf, np.nan)
            .replace(-np.inf, np.nan)
        )

        feat["fvg_signed_strength"] = SOMStrategy.calculate_fvg_signed_strength(
            df, atr_period=14
        )
        feat["fvg_signed_strength_max"] = feat["fvg_signed_strength"].rolling(20).max()

        ob, ob_zone_high, ob_zone_low = SOMStrategy.detect_order_blocks(df, lookback=3)

        feat["ob_size_ratio_to_atr"] = SOMStrategy.calculate_ob_size_ratio_to_atr(
            df, ob, atr_period=14
        )
        feat["ob_retests"] = SOMStrategy.detect_ob_retest(
            df, ob, ob_zone_high, ob_zone_low
        )
        feat["ob_impulse_confirmation"] = (
            SOMStrategy.calculate_ob_impulse_confirmation_signed_atr(
                df, ob, atr_period=14
            )
        )
        feat["ob_liquidity_proximity"] = SOMStrategy.calculate_ob_liquidity_proximity(
            df, ob, ob_zone_high, ob_zone_low, atr_period=14
        )

        adx, plus_di, minus_di = SOMStrategy.calculate_adx(df, period=60)
        feat["adx"] = adx
        feat["plus_di"] = plus_di
        feat["minus_di"] = minus_di

        adx_slope, adx_accel = SOMStrategy.calculate_adx_slope(df, adx, slope_window=20)
        feat["adx_slope"] = adx_slope
        feat["adx_accel"] = adx_accel

        adx_norm = feat["adx"].clip(0, 50) / 50

        di_direction = (feat["plus_di"] - feat["minus_di"]) / (
            feat["plus_di"] + feat["minus_di"] + 1e-6
        )

        feat["trend_impulse_score"] = (
            adx_norm
            * di_direction
            * (1 + np.tanh(feat["adx_slope"] * 10))
            * (1 + np.tanh(feat["adx_accel"] * 100))
        )

        feat["bull_bear_score"] = SOMStrategy.calculate_bull_bear_score(
            df,
            trend_slope_20,
            adx,
            plus_di,
            minus_di,
            long_window=60,
            short_window=14,
        )

        feat = feat.bfill().ffill()

        return feat
