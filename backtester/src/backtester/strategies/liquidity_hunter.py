from __future__ import annotations

from typing import Any

import numpy as np
import optuna
import pandas as pd

from backtester.strategy import BaseStrategy


class RegimeDetector:
    """
    Детектор режимов рынка: тренд vs боковик.
    Использует комбинацию волатильности, тренда и автокорреляции.
    """

    @staticmethod
    def detect(
        df: pd.DataFrame,
        window: int = 50,
        adx_threshold: float = 25,
        atr_vol_ratio_quantile: float = 0.7,
        autocorr_lag: int = 5,
    ) -> pd.Series:
        """
        Возвращает бинарный режим:
            1 — трендовый режим (торгуем)
            0 — боковик (не торгуем или снижаем риск)
        """
        close = df["close"]
        high = df["high"]
        low = df["low"]

        # === 1. Волатильность: нормализованный ATR ===
        atr = RegimeDetector._atr(close, high, low, window)
        atr_ratio = atr / close  # волатильность как % от цены

        # Высокая волатильность? (не боковик)
        high_vol = atr_ratio > atr_ratio.rolling(window * 3).quantile(
            atr_vol_ratio_quantile
        )

        # === 2. Трендовость: ADX + угол EMA ===
        # ADX (уже реализован)
        adx = RegimeDetector._adx(close, high, low, window)
        strong_trend = adx >= adx_threshold

        # Угол 50-EMA (в градусах)
        ema_fast = close.ewm(span=50, adjust=False).mean()
        ema_angle = np.degrees(np.arctan((ema_fast - ema_fast.shift(5)) / 5))
        trending_ema = np.abs(ema_angle) > 2  # больше 2 градусов

        # Комбинированный тренд
        trending = strong_trend | trending_ema

        # === 3. Автокорреляция (подтверждение боковика) ===
        # Низкая автокорреляция → хаос / боковик
        autocorr = (
            close.pct_change()
            .rolling(window)
            .apply(
                lambda x: x.autocorr(lag=autocorr_lag) if len(x) >= autocorr_lag else 0,
                raw=False,
            )
        )
        mean_autocorr = autocorr.rolling(window * 3).mean()
        above_avg_autocorr = autocorr >= mean_autocorr

        # === 4. ФИНАЛЬНЫЙ РЕЖИМ ===
        # Боковик, если:
        # - низкая волатильность ИЛИ
        # - слабый тренд И
        # - низкая автокорреляция
        ranging = (~high_vol) | ((~trending) & (~above_avg_autocorr))

        # Режим: 1 — торговать, 0 — не торговать
        regime = (~ranging).astype(int)

        return regime

    @staticmethod
    def _adx(
        close: pd.Series, high: pd.Series, low: pd.Series, window: int
    ) -> pd.Series:
        tr = pd.DataFrame(
            {
                "hl": high - low,
                "hc": np.abs(high - close.shift()),
                "lc": np.abs(low - close.shift()),
            }
        ).max(axis=1)
        tr_ema = tr.ewm(alpha=1 / window, adjust=False).mean()

        plus_dm = high.diff().clip(lower=0)
        minus_dm = (-low.diff()).clip(upper=0)
        plus_di = 100 * (
            plus_dm.ewm(alpha=1 / window, adjust=False).mean() / (tr_ema + 1e-8)
        )
        minus_di = 100 * (
            minus_dm.ewm(alpha=1 / window, adjust=False).mean() / (tr_ema + 1e-8)
        )

        dx = 100 * np.abs(plus_di - minus_di) / (plus_di + minus_di + 1e-8)
        return dx.ewm(alpha=1 / window, adjust=False).mean()

    @staticmethod
    def _atr(
        close: pd.Series, high: pd.Series, low: pd.Series, window: int
    ) -> pd.Series:
        tr = pd.DataFrame(
            {
                "hl": high - low,
                "hc": np.abs(high - close.shift(1)),
                "lc": np.abs(low - close.shift(1)),
            }
        ).max(axis=1)
        return tr.rolling(window, min_periods=window).mean()


class LiquidityHunter(BaseStrategy):
    """
    LiquidityHunter — SMC-стратегия, выявляющая действия smart money
    через ложные пробои (stop hunts), объемные всплески и сдвиги структуры рынка.

    Работает на 1-минутных барах. Сигнал генерируется по завершённому бару.
    """

    def generate(self, df: pd.DataFrame) -> pd.DataFrame:
        close = df["close"]
        high = df["high"]
        low = df["low"]
        open_ = df["open"]
        volume = df["volume"]

        p = self.params

        window_fast = p["window_fast"]  # 20-30 баров — краткосрочная адаптация
        window_slow = p["window_slow"]  # 100-200 баров — базовый режим

        # === 1. ИНДИКАТОРЫ ===
        atr = self._calculate_atr(close, high, low, p["atr_window"])
        adx = self._calculate_adx(close, high, low, p["adx_window"])
        ema = close.ewm(span=p["ema_period"], adjust=False).mean()
        trend_direction = np.where(close > ema, 1, -1)

        # === 2. АДАПТИВНЫЕ ПОРОГИ ===

        # --- Адаптивный объем ---
        vol_rol = volume.rolling(window_fast)
        vol_mean = vol_rol.mean()
        vol_std = vol_rol.std()
        volume_zscore = (volume - vol_mean) / (vol_std + 1e-8)

        # Объем считается "высоким", если входит в топ X%
        volume_quantile = volume.rolling(window_slow).quantile(p["volume_quantile"])
        significant_volume = (volume > volume_quantile) & (
            volume_zscore > p["min_volume_zscore"]
        )

        # --- Адаптивный wick ratio ---
        body = np.abs(close - open_)
        wick_ratio = (high - low) / np.where(body == 0, 1e-8, body)
        # Порог — высокий перцентиль (редкие stop hunts)
        wick_threshold = wick_ratio.rolling(window_slow).quantile(p["wick_quantile"])
        false_break = (wick_ratio > wick_threshold) & (volume > vol_mean)

        # --- Адаптивный ADX (фильтр режима) ---
        adx_med = adx.rolling(window_slow).median()
        trending_regime = adx >= adx_med  # рынок в тренде, если ADX выше медианы

        # --- Адаптивный стоп-лосс ---
        # В высокой волатильности — шире стопы
        atr_ratio = atr / close
        volatility_regime = atr_ratio > atr_ratio.rolling(window_slow).median()
        sl_atr_mult = np.where(
            volatility_regime,
            p["sl_atr_multiplier_high"],  # 1.0
            p["sl_atr_multiplier_low"],  # 0.5
        )

        # === 3. СДВИГ СТРУКТУРЫ (MSS) ===
        higher_high = high > high.rolling(p["mss_window"]).max().shift(1)
        lower_low = low < low.rolling(p["mss_window"]).min().shift(1)
        price_up = close > close.shift(1)
        price_down = close < close.shift(1)
        market_structure_shift = ((trend_direction == 1) & higher_high & price_up) | (
            (trend_direction == -1) & lower_low & price_down
        )

        # === 4. ГЕНЕРАЦИЯ СИГНАЛОВ ===
        signal = pd.Series(0, index=df.index)

        long_condition = (
            significant_volume
            & false_break.shift(1)
            & (close > open_)
            & market_structure_shift
            & (trend_direction == 1)
            & trending_regime
        )
        signal.loc[long_condition] = 1

        short_condition = (
            significant_volume
            & false_break.shift(1)
            & (close < open_)
            & market_structure_shift
            & (trend_direction == -1)
            & trending_regime
        )
        signal.loc[short_condition] = -1

        # === 5. СТОП-ЛОСС (динамический) ===
        sl_price = pd.Series(0.0, index=df.index)

        recent_low_min = low.rolling(p["mss_window"]).min()
        sl_long = recent_low_min - sl_atr_mult * atr
        sl_price.loc[long_condition] = sl_long[long_condition]

        recent_high_max = high.rolling(p["mss_window"]).max()
        sl_short = recent_high_max + sl_atr_mult * atr
        sl_price.loc[short_condition] = sl_short[short_condition]

        # === ДЕТЕКЦИЯ РЕЖИМА ===
        regime = RegimeDetector.detect(
            df, window=50, adx_threshold=25, atr_vol_ratio_quantile=0.7
        )

        # === ФИЛЬТР СИГНАЛОВ ===
        signal.loc[regime == 0] = 0  # молчим в боковике

        sl_price = sl_price.fillna(0)
        df["signal"] = signal
        df["sl_price"] = sl_price

        return df

    def suggest_params(self, trial: optuna.Trial) -> dict[str, Any]:
        return {
            "window_fast": trial.suggest_int("window_fast", 10, 30, step=5),
            "window_slow": trial.suggest_int("window_slow", 40, 200, step=20),
            "volume_quantile": trial.suggest_float(
                "volume_quantile", 0.70, 0.99, step=0.01
            ),
            "min_volume_zscore": trial.suggest_float(
                "min_volume_zscore", 1.0, 2.0, step=0.01
            ),
            "wick_quantile": trial.suggest_float("wick_quantile", 0.8, 0.99, step=0.01),
            "atr_window": trial.suggest_int("atr_window", 10, 40, step=5),
            "sl_atr_multiplier_high": trial.suggest_float(
                "sl_atr_multiplier_high",
                0.8,
                1.5,
                step=0.05,
            ),
            "sl_atr_multiplier_low": trial.suggest_float(
                "sl_atr_multiplier_low",
                0.3,
                0.7,
                step=0.05,
            ),
            "ema_period": trial.suggest_int("ema_period", 30, 100, step=10),
            "adx_window": trial.suggest_int("adx_window", 10, 60, step=10),
            "mss_window": trial.suggest_int("mss_window", 6, 20, step=2),
        }

    @staticmethod
    def _calculate_atr(
        close: pd.Series, high: pd.Series, low: pd.Series, window: int
    ) -> pd.Series:
        tr = pd.DataFrame(
            {
                "hl": high - low,
                "hc": np.abs(high - close.shift(1)),
                "lc": np.abs(low - close.shift(1)),
            }
        ).max(axis=1)
        return tr.rolling(window, min_periods=window).mean()

    @staticmethod
    def _calculate_adx(
        close: pd.Series, high: pd.Series, low: pd.Series, window: int
    ) -> pd.Series:
        tr = pd.DataFrame(
            {
                "hl": high - low,
                "hc": np.abs(high - close.shift()),
                "lc": np.abs(low - close.shift()),
            }
        ).max(axis=1)
        tr_ema = tr.ewm(alpha=1 / window, adjust=False).mean()

        plus_dm = high.diff().clip(lower=0)
        minus_dm = (-low.diff()).clip(upper=0)
        plus_di = 100 * (
            plus_dm.ewm(alpha=1 / window, adjust=False).mean() / (tr_ema + 1e-8)
        )
        minus_di = 100 * (
            minus_dm.ewm(alpha=1 / window, adjust=False).mean() / (tr_ema + 1e-8)
        )

        dx = 100 * np.abs(plus_di - minus_di) / (plus_di + minus_di + 1e-8)
        return dx.ewm(alpha=1 / window, adjust=False).mean()

    def generate_pine_script(self) -> str:
        p = self.params

        return f"""
//@version=5
strategy("LiquidityHunter - Smart Money Liquidity Hunter", overlay=true, margin_long=100, margin_short=100, pyramiding=0)

// ——————— ПАРАМЕТРЫ ———————
volume_sma_window      = input.int({p["volume_sma_window"]}, "Volume SMA Window", minval=5)
volume_ratio_threshold = input.float({p["volume_ratio_threshold"]:.2f}, "Volume Ratio Threshold", step=0.1)
min_volume_zscore      = input.float({p["min_volume_zscore"]:.2f}, "Min Volume Z-Score", step=0.1)
atr_window             = input.int({p["atr_window"]}, "ATR Window", minval=5)
sl_atr_multiplier      = input.float({p["sl_atr_multiplier"]:.2f}, "SL ATR Multiplier", step=0.1)
wick_ratio_threshold   = input.float({p["wick_ratio_threshold"]:.2f}, "Wick Ratio Threshold", step=0.1)
ema_period             = input.int({p["ema_period"]}, "EMA Period", minval=10)
adx_window             = input.int({p["adx_window"]}, "ADX Window", minval=5)
adx_smooth             = input.int(1, "ADX Smooth", minval=1, maxval=3)
adx_threshold          = input.float({p["adx_threshold"]:.2f}, "ADX Threshold", step=0.1)
mss_window             = input.int({p["mss_window"]}, "MSS Window", minval=3)

// ——————— ADX через ta.dmi ———————
get_adx(len, s) =>
    [_, _, adx] = ta.dmi(len, s)
    adx
adx = get_adx(adx_window, adx_smooth)

// ——————— Адаптивный объём ———————
vol_sma = ta.sma(volume, volume_sma_window)
vol_std = ta.stdev(volume, volume_sma_window)
volume_zscore = (volume - vol_sma) / math.max(vol_std, 0.0001)
significant_volume = (volume / vol_sma >= volume_ratio_threshold) and (volume_zscore >= min_volume_zscore)

// ——————— Ложный пробой ———————
body = math.abs(close - open)
true_body = math.max(body, 0.0001)
wick_ratio = (high - low) / true_body
false_break = (wick_ratio >= wick_ratio_threshold) and (volume > vol_sma)

// ——————— Тренд и структура ———————
atr = ta.atr(atr_window)
ema_val = ta.ema(close, ema_period)
trend_up = close > ema_val

// MSS: сдвиг структуры
prev_high_max = ta.highest(high[1], mss_window)
prev_low_min = ta.lowest(low[1], mss_window)
higher_high = high > prev_high_max
lower_low = low < prev_low_min
price_up = close > close[1]
price_down = close < close[1]
mss_bull = trend_up and higher_high and price_up
mss_bear = not trend_up and lower_low and price_down
market_structure_shift = mss_bull or mss_bear

// ——————— Сигналы (в одной строке) ———————
long_condition = significant_volume and false_break[1] and (close > open) and market_structure_shift and trend_up and (adx >= adx_threshold)
short_condition = significant_volume and false_break[1] and (close < open) and market_structure_shift and (not trend_up) and (adx >= adx_threshold)

// ——————— Стоп-лоссы ———————
sl_long = ta.lowest(low, mss_window) - sl_atr_multiplier * atr
sl_short = ta.highest(high, mss_window) + sl_atr_multiplier * atr

// ——————— Визуализация ———————
plotshape(long_condition,  "Long",  shape.triangleup,   location.belowbar, color.green,  text="LONG",  size=size.small)
plotshape(short_condition, "Short", shape.triangledown, location.abovebar, color.red,    text="SHORT", size=size.small)

plot(long_condition ? sl_long : na, "Long SL", color.new(color.green, 0), 2, plot.style_linebr)
plot(short_condition ? sl_short : na, "Short SL", color.new(color.red, 0), 2, plot.style_linebr)

// ——————— Исполнение ———————
if long_condition
    strategy.entry("Long", strategy.long)
    strategy.exit("Long Exit", "Long", stop=sl_long)

if short_condition
    strategy.entry("Short", strategy.short)
    strategy.exit("Short Exit", "Short", stop=sl_short)
"""
