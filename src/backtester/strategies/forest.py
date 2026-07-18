from __future__ import annotations

import logging
import pickle

import numpy as np
import optuna
import pandas as pd
from tqdm.auto import tqdm

from backtester.strategies.som import SOMStrategy
from backtester.strategy import BaseStrategy

logger = logging.getLogger(__name__)


class ForestStrategy(BaseStrategy):
    model_cache = None

    # Параметры для 3-минутного таймфрейма
    SHORT_BARS = 8  # ~24 минуты (чувствительность к краткосрочным движениям)
    MEDIUM_BARS = 60  # ~3 часа (основной трендовый контекст)
    LONG_BARS = 480  # ~1 день (долгосрочная перспектива)
    LOOKBACK_VOL = 2016  # ~4.2 дня (неделя может быть слишком много — 2016 = 3 дня)

    HTF_1H_BARS = 20  # 1 час = 20 свечей по 3 минуты
    HTF_4H_BARS = 80  # 4 часа = 80 свечей
    HTF_1D_BARS = LONG_BARS  # 1 день = 480 свечей

    def __init__(self, params):
        super().__init__(params)

        self.model = ForestStrategy.model_cache
        if self.model is None:
            with open(params["model_path"], "rb") as f:
                self.model = pickle.load(f)
                ForestStrategy.model_cache = self.model

        with open(params["scaler_path"], "rb") as f:
            self.scaler = pickle.load(f)

        self.feature_columns = [
            "body_ratio",
            "upper_shadow_ratio",
            "lower_shadow_ratio",
            "is_green",
            "lower_shadow_long_ratio",
            "volume_ma_ratio",
            "price_position_in_range",
            "dist_to_sma_pct",
            "price_below_sma",
            "adaptive_trend_angle",
            "trend_risk_reward",
            "rsi_14",
            "breakout_high_5",
            "breakout_low_5",
            "fakeout_down",
            "volume_drop_before_break",
            "vol_price_corr",
            "fvg_signed_strength",
            "fvg_signed_strength_max",
            "ob_size_ratio_to_atr",
            "ob_retests",
            "ob_impulse_confirmation",
            "ob_liquidity_proximity",
            "adx",
            "plus_di",
            "minus_di",
            "adx_slope",
            "adx_accel",
            "trend_impulse_score",
            "bull_bear_score",
            "volatility_regime",
            "efficiency_ratio",
            "chop_index",
            "trend_stability",
            "liquidity_dist_to_hh_atr",
            "liquidity_dist_to_ll_atr",
            "liquidity_grab_recent",
            "liquidity_imbalance_score",
            "liquidity_approach_accel_to_hh",
            "liquidity_approach_accel_to_ll",
            "liquidity_approach_score",
            "multitimeframe_bull_score",
        ]

    @staticmethod
    def suggest_params(trial: optuna.Trial):
        return {
            "model_path": "data/forest/model.pkl",
            "scaler_path": "data/forest/scaler_3.pkl",
            "sl_mult": trial.suggest_float("sl_mult", 1.0, 8.0, step=0.5),
            "cooldown": trial.suggest_int("cooldown", 1, 10),
            "atr_window": trial.suggest_int("atr_window", 10, 30),
        }

    def generate(self, df: pd.DataFrame) -> pd.DataFrame:
        # logger.setLevel(logging.DEBUG)
        atr_window = self.params.get("atr_window", 14)
        cooldown = self.params.get("cooldown", 5)
        sl_mult = self.params.get("sl_mult", 2)
        first_ignore = 50
        structure_timeframe = self.params.get("structure_timeframe", 3)

        df = df.resample(pd.Timedelta(minutes=structure_timeframe)).agg(
            {
                "open": "first",
                "high": "max",
                "low": "min",
                "close": "last",
                "volume": "sum",
            }
        )
        atr = SOMStrategy.calculate_atr(df, atr_window)

        logger.debug("Processing features...")
        df = ForestStrategy.create_features_from_scratch(df)
        X = df[self.feature_columns]
        logger.debug("Features head:")
        logger.debug(X.head())

        X_scaled = self.scaler.transform(X)

        y = self.model.predict(X_scaled).astype(int)
        i = 0
        if logger.isEnabledFor(logging.DEBUG):
            it = tqdm(
                total=len(y),
                desc="Strategy signal generation",
                unit="bar",
                ascii=True,
            )
        while i < len(y):
            if logger.isEnabledFor(logging.DEBUG):
                it.update(1)
            if i < first_ignore:
                i += 1
                y[i] = 0
                continue

            if y[i] == 0:
                i += 1
                continue

            y[i + 1 : i + cooldown] = 0
            i += cooldown

        if logger.isEnabledFor(logging.DEBUG):
            it.close()

        logger.debug("Strategy generated signal: {}".format(len(y)))
        df["signal"] = y

        sl_mult = np.where(
            df["signal"] == 1, -sl_mult, np.where(df["signal"] == -1, sl_mult, 0)
        )
        df["sl_price"] = df["close"] + sl_mult * atr

        return df

    @staticmethod
    def create_features_from_scratch(df: pd.DataFrame):
        feat = df.copy()

        # 1. Базовые соотношения цен
        logger.debug("Base features...")
        feat["body"] = df["close"] - df["open"]
        feat["upper_shadow"] = df["high"] - df[["open", "close"]].max(axis=1)
        feat["lower_shadow"] = df[["open", "close"]].min(axis=1) - df["low"]
        feat["range"] = df["high"] - df["low"]

        # 2. Относительные размеры
        logger.debug("Relative size features...")
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
        logger.debug("Direction and type features...")
        feat["is_green"] = (df["close"] > df["open"]).astype(int)
        feat["lower_shadow_long_ratio"] = feat["lower_shadow"] / (
            feat["upper_shadow"] + feat["lower_shadow"]
        )

        # 4. Объём
        logger.debug("Volume features...")
        feat["volume_ma_ratio"] = (
            df["volume"] / df["volume"].rolling(ForestStrategy.MEDIUM_BARS).mean()
        )

        # 6. Тренд (скользящие средние)
        logger.debug("Trend features...")
        feat["price_position_in_range"] = (df["close"] - df["low"]) / (
            df["high"] - df["low"] + 1e-6
        )

        logger.debug("SMA features...")
        sma_medium = df["close"].rolling(ForestStrategy.MEDIUM_BARS).mean()

        atr = SOMStrategy.calculate_atr(df, period=14)
        # Расстояние до SMA в % и в пунктах
        logger.debug("Distance to SMA features...")
        feat["dist_to_sma_pct"] = (df["low"] - sma_medium) / atr
        feat["price_below_sma"] = (df["close"] < sma_medium).astype(int)

        def rolling_slope(series, w=20):
            x = np.arange(w)
            slopes = []
            iters = range(len(series))
            if logger.isEnabledFor(logging.DEBUG):
                iters = tqdm(
                    iters,
                    desc="Rolling slope",
                    unit="bar",
                    ascii=True,
                )
            for i in iters:
                if i < w:
                    slopes.append(0.0)
                    continue
                y = series.iloc[i - w : i].values
                if np.isnan(y).any():
                    slopes.append(0.0)
                    continue
                # Линейная регрессия: y = kx + b
                k = np.polyfit(x, y, 1)[0]
                slopes.append(k)
            return pd.Series(slopes, index=series.index)

        def adaptive_slope(series: pd.Series, atr: pd.Series, base_window=20):
            slopes = []
            iters = range(len(series))
            if logger.isEnabledFor(logging.DEBUG):
                iters = tqdm(
                    iters,
                    desc="Adaptive slope",
                    unit="bar",
                    ascii=True,
                )

            for i in iters:
                if i < base_window:
                    slopes.append(0.0)
                    continue
                # Динамическое окно: чем выше волатильность, тем длиннее окно
                window = base_window * (
                    1 + atr.iloc[i] / atr.iloc[max(0, i - base_window) : i].mean()
                )
                if np.isnan(window) or window in [np.inf, -np.inf]:
                    window = 0

                window = max(10, int(window))
                window = min(window, i)
                x = np.arange(window)
                y = series.iloc[i - window : i].values
                if not np.isnan(y).any() and len(y) > 1:
                    k = np.polyfit(x, y, 1)[0]
                    slopes.append(k / atr.iloc[i])  # нормализуем по ATR
                else:
                    slopes.append(0.0)
            return pd.Series(slopes, index=series.index)

        atr = SOMStrategy.calculate_atr(df, period=20)
        logger.debug("Adaptive trend angle features...")
        feat["adaptive_trend_angle"] = adaptive_slope(
            df["close"], atr, base_window=2 * ForestStrategy.SHORT_BARS
        )

        logger.debug("Trend risk reward features...")
        trend_slope_short = rolling_slope(df["close"], 2 * ForestStrategy.SHORT_BARS)
        feat["trend_risk_reward"] = trend_slope_short / atr  # риск-вознаграждение угла

        def rsi_fast(series: pd.Series, period=14):
            delta = series.diff()
            gain = (delta.where(delta > 0, 0)).rolling(period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
            rs = gain / loss.replace(0, 1e-6)
            return 100 - (100 / (1 + rs))

        logger.debug("RSI features...")
        feat["rsi_14"] = rsi_fast(df["close"], 14) / 100

        logger.debug("Breakout high 5 features...")
        feat["breakout_high_5"] = (
            df["high"] > df["high"].rolling(ForestStrategy.SHORT_BARS).max().shift(1)
        ).astype(int)

        logger.debug("Breakout low 5 features...")
        feat["breakout_low_5"] = (
            df["low"] < df["low"].rolling(ForestStrategy.SHORT_BARS).min().shift(1)
        ).astype(int)

        logger.debug("Fakeout down features...")
        feat["fakeout_down"] = (
            (df["low"] < df["low"].rolling(ForestStrategy.SHORT_BARS).min().shift(1))
            & (
                df["close"]
                > df["low"].rolling(ForestStrategy.SHORT_BARS).min().shift(1)
            )
        ).astype(int)

        logger.debug("Volume drop before break features...")
        feat["volume_drop_before_break"] = (
            (
                df["volume"]
                < df["volume"].rolling(2 * ForestStrategy.SHORT_BARS).mean() * 0.5
            )
            & feat["breakout_high_5"]
        ).astype(int)

        price_mid = (df["high"] + df["low"]) / 2
        logger.debug("Volume price correlation features...")
        feat["vol_price_corr"] = (
            feat["volume"]
            .rolling(ForestStrategy.SHORT_BARS)
            .corr(price_mid, numeric_only=True)
            .replace(np.inf, np.nan)
            .replace(-np.inf, np.nan)
        )

        logger.debug("FVG signed strength features...")
        feat["fvg_signed_strength"] = SOMStrategy.calculate_fvg_signed_strength(
            df, atr_period=2 * ForestStrategy.SHORT_BARS
        )

        logger.debug("FVG signed strength max features...")
        feat["fvg_signed_strength_max"] = (
            feat["fvg_signed_strength"].rolling(ForestStrategy.MEDIUM_BARS).max()
        )

        logger.debug("Order blocks features...")
        ob, ob_zone_high, ob_zone_low = SOMStrategy.detect_order_blocks(df, lookback=3)

        logger.debug("OB size ratio to ATR features...")
        feat["ob_size_ratio_to_atr"] = SOMStrategy.calculate_ob_size_ratio_to_atr(
            df,
            ob,
            atr_period=14,
            ob_zone_high=ob_zone_high,
            ob_zone_low=ob_zone_low,
        )

        logger.debug("OB retests features...")
        feat["ob_retests"] = SOMStrategy.detect_ob_retest(
            df, ob, ob_zone_high, ob_zone_low
        )

        logger.debug("OB impulse confirmation features...")
        feat["ob_impulse_confirmation"] = (
            SOMStrategy.calculate_ob_impulse_confirmation_signed_atr(
                df, ob, atr_period=14
            )
        )

        logger.debug("OB liquidity proximity features...")
        feat["ob_liquidity_proximity"] = SOMStrategy.calculate_ob_liquidity_proximity(
            df, ob, ob_zone_high, ob_zone_low, atr_period=14
        )

        logger.debug("ADX features...")
        adx, plus_di, minus_di = SOMStrategy.calculate_adx(
            df, period=2 * ForestStrategy.MEDIUM_BARS
        )
        feat["adx"] = adx
        feat["plus_di"] = plus_di
        feat["minus_di"] = minus_di

        adx_norm = feat["adx"].clip(0, 50) / 50

        di_direction = (feat["plus_di"] - feat["minus_di"]) / (
            feat["plus_di"] + feat["minus_di"] + 1e-6
        )

        adx_slope, adx_accel = SOMStrategy.calculate_adx_slope(
            df, adx, slope_window=2 * ForestStrategy.SHORT_BARS
        )
        feat["adx_slope"] = adx_slope
        feat["adx_accel"] = adx_accel

        logger.debug("Trend impulse score features...")
        feat["trend_impulse_score"] = (
            adx_norm
            * di_direction
            * (1 + np.tanh(feat["adx_slope"] * 10))
            * (1 + np.tanh(feat["adx_accel"] * 100))
        )

        logger.debug("Bull bear score features...")
        feat["bull_bear_score"] = SOMStrategy.calculate_bull_bear_score(
            df,
            trend_slope_short,
            adx,
            plus_di,
            minus_di,
            long_window=2 * ForestStrategy.MEDIUM_BARS,
            short_window=ForestStrategy.SHORT_BARS,
        )

        logger.debug("Volatility regime features...")
        feat["volatility_regime"] = ForestStrategy.calculate_volatility_regime(
            df,
            atr_period=ForestStrategy.SHORT_BARS,
            lookback=ForestStrategy.LOOKBACK_VOL,
        )

        logger.debug("Efficiency ratio features...")
        feat["efficiency_ratio"] = ForestStrategy.calculate_efficiency_ratio(
            df, window=ForestStrategy.MEDIUM_BARS
        )

        logger.debug("Chop index features...")
        feat["chop_index"] = ForestStrategy.calculate_chop_index(
            df, window=ForestStrategy.SHORT_BARS
        )

        logger.debug("Trend stability features...")
        feat["trend_stability"] = ForestStrategy.calculate_trend_stability(
            df,
            short_span=ForestStrategy.SHORT_BARS,
            long_span=ForestStrategy.MEDIUM_BARS,
            window=ForestStrategy.MEDIUM_BARS,
        )

        logger.debug("Recent liquidity zones features...")
        dist_to_hh, dist_to_ll, _, _ = ForestStrategy.detect_recent_liquidity_zones(
            df, ForestStrategy.SHORT_BARS, ForestStrategy.MEDIUM_BARS
        )

        logger.debug("Liquidity dist to HH ATR features...")
        feat["liquidity_dist_to_hh_atr"] = dist_to_hh
        feat["liquidity_dist_to_ll_atr"] = dist_to_ll

        logger.debug("Liquidity grab recent features...")
        feat["liquidity_grab_recent"] = ForestStrategy.detect_liquidity_grab(
            df, ForestStrategy.SHORT_BARS, ForestStrategy.MEDIUM_BARS
        )

        logger.debug("Liquidity imbalance score features...")
        feat["liquidity_imbalance_score"] = (
            ForestStrategy.calculate_liquidity_imbalance(
                df, ForestStrategy.SHORT_BARS, ForestStrategy.MEDIUM_BARS
            )
        )

        logger.debug("Liquidity approach speed features...")
        speed_hh, speed_ll, accel_hh, accel_ll = (
            ForestStrategy.calculate_liquidity_approach_speed(
                df,
                short_bars=ForestStrategy.SHORT_BARS,
                medium_bars=ForestStrategy.MEDIUM_BARS,
            )
        )

        logger.debug("Liquidity approach accel to HH features...")
        feat["liquidity_approach_accel_to_hh"] = accel_hh

        logger.debug("Liquidity approach accel to LL features...")
        feat["liquidity_approach_accel_to_ll"] = accel_ll

        logger.debug("Liquidity approach score features...")
        feat["liquidity_approach_score"] = np.where(
            feat["liquidity_dist_to_hh_atr"] < feat["liquidity_dist_to_ll_atr"],
            speed_hh,
            speed_ll,
        )

        logger.debug("Multitimeframe bull score features...")
        feat["multitimeframe_bull_score"] = (
            ForestStrategy.create_multitimeframe_feature(df)
        )

        feat = feat.bfill().ffill()

        return feat

    @staticmethod
    def calculate_volatility_regime(df: pd.DataFrame, atr_period=14, lookback=100):
        """
        Нормализованная волатильность: 0 = низкая, 1 = высокая (перцентиль за lookback)
        """
        atr = SOMStrategy.calculate_atr(df, period=atr_period)
        volatility = atr / df["close"]  # ATR в % от цены

        volatility_regime = volatility.rolling(lookback, min_periods=50).rank(pct=True)
        return volatility_regime.fillna(0.5)  # если мало данных — среднее

    @staticmethod
    def calculate_efficiency_ratio(df: pd.DataFrame, window=20):
        """
        ER = |цена[t] - цена[t-window]| / сумма|изменений за окно|
        → 1 = чистый тренд, 0 = боковик/шум
        """
        price = df["close"]
        direction = (price - price.shift(window)).abs()
        volatility = price.diff().abs().rolling(window).sum()
        er = direction / (volatility + 1e-8)
        return er.fillna(0.0)

    @staticmethod
    def calculate_chop_index(df: pd.DataFrame, window=14):
        """
        Чем выше значение — тем больше "пила" (боковик).
        Формула: 100 * log10( (sum(ATR, window) / (max(high, window) - min(low, window))) ) / log10(window)
        """
        atr = SOMStrategy.calculate_atr(df, period=1)
        sum_atr = atr.rolling(window).sum()
        range_window = (
            df["high"].rolling(window).max() - df["low"].rolling(window).min()
        )

        chop = (
            100.0
            * np.log10((sum_atr / (range_window + 1e-8)) + 1e-8)
            / np.log10(window)
        )
        chop = chop.clip(0, 100)  # 0 = тренд, 100 = макс. пила
        return 1.0 - (chop / 100.0)  # 1 = тренд, 0 = пила

    @staticmethod
    def calculate_trend_stability(
        df: pd.DataFrame, short_span=12, long_span=26, window=20
    ):
        """
        Насколько стабильно соотношение быстрых и медленных EMA.
        Низкая стабильность = частые пересечения = боковик.
        """
        ema_short = df["close"].ewm(span=short_span).mean()
        ema_long = df["close"].ewm(span=long_span).mean()

        ema_diff = ema_short - ema_long
        stability = 1.0 - (
            ema_diff.rolling(window).std()
            / (ema_diff.rolling(window).std().rolling(window).mean() + 1e-8)
        )
        return stability.fillna(0.5)

    @staticmethod
    def detect_recent_liquidity_zones(df: pd.DataFrame, short_bars=8, medium_bars=60):
        """
        Находит ближайшие зоны ликвидности:
            - recent_high: последний HH за medium_bars
            - recent_low: последний LL за medium_bars
        Возвращает расстояния до них в ATR.
        """
        atr = SOMStrategy.calculate_atr(df, period=short_bars)

        hh = df["high"].rolling(medium_bars, center=False).max()
        ll = df["low"].rolling(medium_bars, center=False).min()

        dist_to_hh_atr = (hh - df["high"]) / atr
        dist_to_ll_atr = (df["low"] - ll) / atr

        return dist_to_hh_atr, dist_to_ll_atr, hh, ll

    @staticmethod
    def detect_liquidity_grab(df: pd.DataFrame, short_bars=8, medium_bars=60):
        """
        Определяет, был ли недавний fakeout (забор ликвидности):
            - Пробой HH/LL, но быстрое возвращение внутрь диапазона
        """
        _, _, hh, ll = ForestStrategy.detect_recent_liquidity_zones(
            df, short_bars, medium_bars
        )

        broke_high = df["high"] > hh.shift(1)
        reentered_after_broke = broke_high.shift(short_bars).fillna(False) & (
            df["close"] < hh.shift(short_bars)
        )

        broke_low = df["low"] < ll.shift(1)
        reentered_after_broke_low = broke_low.shift(short_bars).fillna(False) & (
            df["close"] > ll.shift(short_bars)
        )

        liquidity_grab = (reentered_after_broke | reentered_after_broke_low).astype(int)
        return liquidity_grab

    @staticmethod
    def calculate_liquidity_imbalance(df: pd.DataFrame, short_bars=8, medium_bars=60):
        """
        Оценивает дисбаланс ликвидности:
            - Если цена ближе к HH, чем к LL → медвежий дисбаланс (ликвидность сверху)
            - И наоборот
        Возвращает нормализованный скор от -1 (медвежий) до +1 (бычий).
        """
        dist_to_hh, dist_to_ll, _, _ = ForestStrategy.detect_recent_liquidity_zones(
            df, short_bars, medium_bars
        )

        total_dist = dist_to_hh.abs() + dist_to_ll.abs() + 1e-6
        imbalance = (dist_to_ll - dist_to_hh) / total_dist

        return imbalance.clip(-1, 1)

    @staticmethod
    def calculate_liquidity_approach_speed(
        df: pd.DataFrame, short_bars=8, medium_bars=60
    ):
        """
        Рассчитывает скорость и ускорение цены при приближении к зонам ликвидности (HH/LL).

        Возвращает:
            - approach_speed_to_hh: скорость приближения к верхней ликвидности (положительная = движемся вверх)
            - approach_speed_to_ll: скорость приближения к нижней ликвидности (отрицательная = движемся вниз)
            - approach_accel_to_hh, approach_accel_to_ll: ускорение
        Все значения нормализованы по ATR.
        """
        atr = SOMStrategy.calculate_atr(df, period=short_bars)

        hh = df["high"].rolling(medium_bars, min_periods=1).max()
        ll = df["low"].rolling(medium_bars, min_periods=1).min()

        dist_to_hh = hh - df["high"]
        dist_to_ll = df["low"] - ll

        speed_to_hh = -dist_to_hh.diff() / atr
        speed_to_ll = -dist_to_ll.diff() / atr

        accel_to_hh = speed_to_hh.diff()
        accel_to_ll = speed_to_ll.diff()

        speed_to_hh = speed_to_hh.fillna(0)
        speed_to_ll = speed_to_ll.fillna(0)
        accel_to_hh = accel_to_hh.fillna(0)
        accel_to_ll = accel_to_ll.fillna(0)

        return speed_to_hh, speed_to_ll, accel_to_hh, accel_to_ll

    @staticmethod
    def create_multitimeframe_feature(df: pd.DataFrame):
        """
        Создаёт мульти-таймфреймовые признаки для 3-минутного графика.
        Имитирует 1H, 4H и 1D таймфреймы через агрегацию.
        """
        feat = pd.DataFrame(index=df.index)

        htf_1h_close = (
            df["close"]
            .rolling(ForestStrategy.HTF_1H_BARS)
            .apply(lambda x: x.iloc[-1], raw=False)
        )
        htf_1h_high = df["high"].rolling(ForestStrategy.HTF_1H_BARS).max()
        htf_1h_low = df["low"].rolling(ForestStrategy.HTF_1H_BARS).min()

        ema_1h_fast = htf_1h_close.ewm(span=8).mean()
        ema_1h_slow = htf_1h_close.ewm(span=24).mean()
        feat["htf_1h_trend"] = (ema_1h_fast > ema_1h_slow).astype(float)

        htf_1h_range = htf_1h_high - htf_1h_low
        feat["htf_1h_price_position"] = (df["close"] - htf_1h_low) / (
            htf_1h_range + 1e-8
        )

        htf_4h_close = (
            df["close"]
            .rolling(ForestStrategy.HTF_4H_BARS)
            .apply(lambda x: x.iloc[-1], raw=False)
        )
        htf_4h_high = df["high"].rolling(ForestStrategy.HTF_4H_BARS).max()
        htf_4h_low = df["low"].rolling(ForestStrategy.HTF_4H_BARS).min()

        ema_4h_fast = htf_4h_close.ewm(span=6).mean()
        ema_4h_slow = htf_4h_close.ewm(span=18).mean()
        feat["htf_4h_trend"] = (ema_4h_fast > ema_4h_slow).astype(float)

        atr = SOMStrategy.calculate_atr(df, period=20)
        feat["htf_4h_dist_to_support_atr"] = (df["low"] - htf_4h_low) / (atr + 1e-8)
        feat["htf_4h_dist_to_resistance_atr"] = (htf_4h_high - df["high"]) / (
            atr + 1e-8
        )

        htf_1d_close = (
            df["close"]
            .rolling(ForestStrategy.HTF_1D_BARS)
            .apply(lambda x: x.iloc[-1], raw=False)
        )
        htf_1d_high = df["high"].rolling(ForestStrategy.HTF_1D_BARS).max()
        htf_1d_low = df["low"].rolling(ForestStrategy.HTF_1D_BARS).min()

        htf_1d_mid = (htf_1d_high + htf_1d_low) / 2
        feat["htf_1d_above_mid"] = (df["close"] > htf_1d_mid).astype(float)

        htf_1d_range_pct = (htf_1d_high - htf_1d_low) / htf_1d_close
        feat["htf_1d_volatility"] = htf_1d_range_pct.rolling(
            ForestStrategy.HTF_1D_BARS
        ).rank(pct=True)

        return (
            feat["htf_1h_trend"] * 0.3
            + feat["htf_4h_trend"] * 0.4
            + feat["htf_1d_above_mid"] * 0.3
        )
