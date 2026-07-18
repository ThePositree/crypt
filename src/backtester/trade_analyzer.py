import logging
from typing import Dict, Optional

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats
from scipy.stats import entropy
from sklearn.feature_selection import mutual_info_classif
from sklearn.metrics import roc_auc_score
from sklearn.preprocessing import MinMaxScaler


class TradeAnalyzer:
    """
    Анализатор условий сделок для поиска метрик, которые лучше всего
    разделяют распределения для успешных (TP) и неуспешных (SL) сделок.
    """

    def __init__(self, trades_df: pd.DataFrame, ohlcv_df: pd.DataFrame):
        """
        Инициализация анализатора.

        Parameters
        ----------
        trades_df : pd.DataFrame
            DataFrame с историей сделок от ExecutionSim.
        ohlcv_df : pd.DataFrame
            OHLCV данные по одному инструменту (DatetimeIndex).
        """
        self.trades = trades_df.copy()
        self.ohlcv_df = ohlcv_df
        self.entry_metrics = None
        self.separation_results = None
        self.precomputed_metrics_df = None  # Кэш предвычисленных метрик
        self._logger = logging.getLogger(__name__)

    def precompute_all_metrics(self):
        """
        Предварительно вычисляет все метрики по OHLCV данным.
        Значительно ускоряет извлечение метрик для сделок.
        """
        import time

        n_bars = len(self.ohlcv_df)
        self._logger.info("🚀 Precomputing metrics for %d bars...", n_bars)

        # Копия DataFrame для добавления метрик
        df = self.ohlcv_df.copy()
        start_time = time.time()

        # 1. Базовые метрики
        cat_start = time.time()
        df["price_change"] = df["close"].pct_change()
        df["high_low_range"] = df["high"] - df["low"]
        df["body_size"] = abs(df["close"] - df["open"])
        self._logger.debug(
            "⏱️  Базовые метрики: %.3fs", time.time() - cat_start
        )

        # 2. Скользящие средние и волатильность
        cat_start = time.time()
        df["sma_20"] = df["close"].rolling(20).mean()
        df["sma_50"] = df["close"].rolling(50).mean()
        df["ema_9"] = df["close"].ewm(span=9).mean()
        df["ema_21"] = df["close"].ewm(span=21).mean()
        df["ema_50"] = df["close"].ewm(span=50).mean()
        self._logger.debug(
            "⏱️  Скользящие средние: %.3fs", time.time() - cat_start
        )

        # 3. ATR
        cat_start = time.time()
        high_low = df["high"] - df["low"]
        high_close = (df["high"] - df["close"].shift(1)).abs()
        low_close = (df["low"] - df["close"].shift(1)).abs()
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        df["atr_14"] = tr.rolling(14).mean()
        df["atr_20"] = tr.rolling(20).mean()
        self._logger.debug("⏱️   ATR: %.3fs", time.time() - cat_start)

        # 4. RSI
        cat_start = time.time()
        delta = df["close"].diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        df["rsi_14"] = 100 - (100 / (1 + rs))
        self._logger.debug("⏱️   RSI: %.3fs", time.time() - cat_start)

        # 5. Stochastic
        cat_start = time.time()
        df["low_14"] = df["low"].rolling(14).min()
        df["high_14"] = df["high"].rolling(14).max()
        df["stoch_k"] = (
            100 * (df["close"] - df["low_14"]) / (df["high_14"] - df["low_14"])
        )
        self._logger.debug(
            "⏱️   Stochastic: %.3fs", time.time() - cat_start
        )

        # 6. Bollinger Bands
        cat_start = time.time()
        df["bb_middle"] = df["close"].rolling(20).mean()
        df["bb_std"] = df["close"].rolling(20).std()
        df["bb_upper"] = df["bb_middle"] + (df["bb_std"] * 2)
        df["bb_lower"] = df["bb_middle"] - (df["bb_std"] * 2)
        df["bb_position"] = (df["close"] - df["bb_lower"]) / (
            df["bb_upper"] - df["bb_lower"]
        )
        df["bb_width"] = (df["bb_upper"] - df["bb_lower"]) / df["close"]
        self._logger.debug(
            "⏱️   Bollinger Bands: %.3fs", time.time() - cat_start
        )

        # 7. Volume metrics
        cat_start = time.time()
        if "volume" in df.columns:
            df["volume_ma_20"] = df["volume"].rolling(20).mean()
            df["volume_ratio"] = df["volume"] / df["volume_ma_20"]

            # Volume imbalance
            df["volume_imbalance"] = (
                df["volume"] * (df["close"] - df["open"])
            ).rolling(5).sum() / df["volume"].rolling(5).sum()

            # Volume-Price correlation
            df["volume_price_corr"] = (
                df["close"].pct_change().rolling(10).corr(df["volume"].pct_change())
            )
        self._logger.debug(
            "⏱️   Volume metrics: %.3fs", time.time() - cat_start
        )

        # 8. MACD
        cat_start = time.time()
        df["ema_12"] = df["close"].ewm(span=12).mean()
        df["ema_26"] = df["close"].ewm(span=26).mean()
        df["macd_line"] = df["ema_12"] - df["ema_26"]
        df["macd_signal"] = df["macd_line"].ewm(span=9).mean()
        df["macd_histogram"] = df["macd_line"] - df["macd_signal"]
        self._logger.debug("⏱️   MACD: %.3fs", time.time() - cat_start)

        # 9. Williams %R
        cat_start = time.time()
        df["williams_r"] = (
            -100 * (df["high_14"] - df["close"]) / (df["high_14"] - df["low_14"])
        )
        self._logger.debug(
            "⏱️   Williams %%R: %.3fs", time.time() - cat_start
        )

        # 10. CCI
        cat_start = time.time()
        typical_price = (df["high"] + df["low"] + df["close"]) / 3
        sma_tp = typical_price.rolling(20).mean()
        # Векторизованное вычисление mean deviation без apply
        mean_deviation = typical_price.rolling(20).std() * np.sqrt(
            20 / 19
        )  # Приближение
        df["cci"] = (typical_price - sma_tp) / (0.015 * mean_deviation)
        self._logger.debug("⏱️   CCI: %.3fs", time.time() - cat_start)

        # 11. Volatility metrics
        cat_start = time.time()
        df["recent_volatility"] = df["price_change"].rolling(10).std()
        df["historical_volatility"] = df["price_change"].rolling(20).std()
        df["volatility_ratio"] = (
            df["recent_volatility"] / df["historical_volatility"]
        )
        self._logger.debug(
            "⏱️   Volatility metrics: %.3fs", time.time() - cat_start
        )

        # 12. Momentum metrics
        cat_start = time.time()
        df["momentum_5"] = (df["close"] - df["close"].shift(5)) / df["close"]
        df["momentum_10"] = (df["close"] - df["close"].shift(10)) / df["close"]
        df["momentum_20"] = (df["close"] - df["close"].shift(20)) / df["close"]
        self._logger.debug(
            "⏱️   Momentum metrics: %.3fs", time.time() - cat_start
        )

        # 13. Support/Resistance levels
        cat_start = time.time()
        df["support_level"] = df["low"].rolling(20).min()
        df["resistance_level"] = df["high"].rolling(20).max()
        self._logger.debug(
            "⏱️   Support/Resistance: %.3fs", time.time() - cat_start
        )

        # 14. Consecutive moves
        cat_start = time.time()
        df["consecutive_up"] = (
            (df["price_change"] > 0)
            .astype(int)
            .groupby((df["price_change"] <= 0).cumsum())
            .cumsum()
        )
        df["consecutive_down"] = (
            (df["price_change"] < 0)
            .astype(int)
            .groupby((df["price_change"] >= 0).cumsum())
            .cumsum()
        )
        self._logger.debug(
            "⏱️   Consecutive moves: %.3fs", time.time() - cat_start
        )

        # 15. Distance from extremes
        cat_start = time.time()
        df["distance_from_high"] = (
            df["high"].rolling(20).max() - df["close"]
        ) / df["close"]
        df["distance_from_low"] = (df["close"] - df["low"].rolling(20).min()) / df[
            "close"
        ]
        self._logger.debug(
            "⏱️   Distance from extremes: %.3fs", time.time() - cat_start
        )

        # 16. Distribution metrics
        cat_start = time.time()
        df["price_skewness"] = df["price_change"].rolling(20).skew()
        df["price_kurtosis"] = df["price_change"].rolling(20).kurt()
        self._logger.debug(
            "⏱️   Distribution metrics: %.3fs", time.time() - cat_start
        )

        # 17. Advanced Oscillators
        cat_start = time.time()
        # ADX (Average Directional Index) - сила тренда
        high_diff = df["high"].diff()
        low_diff = df["low"].diff()
        plus_dm = high_diff.where((high_diff > low_diff) & (high_diff > 0), 0)
        minus_dm = -low_diff.where((low_diff > high_diff) & (low_diff > 0), 0)

        atr_14 = df["atr_14"]
        plus_di = 100 * (plus_dm.rolling(14).mean() / atr_14)
        minus_di = 100 * (minus_dm.rolling(14).mean() / atr_14)
        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
        df["adx"] = dx.rolling(14).mean()
        df["plus_di"] = plus_di
        df["minus_di"] = minus_di
        df["di_cross_up"] = (plus_di > minus_di) & (
            plus_di.shift(1) <= minus_di.shift(1)
        )
        df["di_cross_down"] = (plus_di < minus_di) & (
            plus_di.shift(1) >= minus_di.shift(1)
        )

        # ADX slope and acceleration
        df["adx_slope"] = df["adx"].diff(5)
        df["adx_accel"] = df["adx_slope"].diff(3)
        self._logger.debug(
            "⏱️   Advanced Oscillators: %.3fs", time.time() - cat_start
        )

        # 18. Ichimoku Cloud Components
        cat_start = time.time()
        # Tenkan-sen (9-period)
        df["tenkan_sen"] = (
            df["high"].rolling(9).max() + df["low"].rolling(9).min()
        ) / 2
        # Kijun-sen (26-period)
        df["kijun_sen"] = (
            df["high"].rolling(26).max() + df["low"].rolling(26).min()
        ) / 2
        # Senkou Span A (leading span A)
        df["senkou_span_a"] = ((df["tenkan_sen"] + df["kijun_sen"]) / 2).shift(26)
        # Senkou Span B (leading span B)
        df["senkou_span_b"] = (
            (df["high"].rolling(52).max() + df["low"].rolling(52).min()) / 2
        ).shift(26)
        # Chikou Span is visually plotted 26 periods back, but at decision
        # time only the lagged close is known. Keep the exported predictor
        # causal so filter research cannot rank a future close.
        df["chikou_span"] = df["close"].shift(26)

        # Ichimoku signals
        df["price_above_cloud"] = (df["close"] > df["senkou_span_a"]) & (
            df["close"] > df["senkou_span_b"]
        )
        df["price_below_cloud"] = (df["close"] < df["senkou_span_a"]) & (
            df["close"] < df["senkou_span_b"]
        )
        df["cloud_thickness"] = (
            abs(df["senkou_span_a"] - df["senkou_span_b"]) / df["close"]
        )
        df["tenkan_kijun_cross"] = (df["tenkan_sen"] > df["kijun_sen"]) & (
            df["tenkan_sen"].shift(1) <= df["kijun_sen"].shift(1)
        )
        self._logger.debug(
            "⏱️   Ichimoku Cloud: %.3fs", time.time() - cat_start
        )

        # 19. Advanced Volume Analysis
        cat_start = time.time()
        if "volume" in df.columns:
            # On-Balance Volume (OBV)
            df["obv"] = (
                df["volume"]
                * np.where(
                    df["close"] > df["close"].shift(1),
                    1,
                    np.where(df["close"] < df["close"].shift(1), -1, 0),
                )
            ).cumsum()

            # Volume Rate of Change
            df["volume_roc"] = df["volume"].pct_change(10)

            # Accumulation/Distribution Line
            df["ad_line"] = (
                ((df["close"] - df["low"]) - (df["high"] - df["close"]))
                / (df["high"] - df["low"])
                * df["volume"]
            ).cumsum()

            # Money Flow Index (MFI)
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
            df["mfi"] = 100 - (100 / (1 + positive_flow / negative_flow))

            # Volume Weighted Average Price (VWAP)
            df["vwap"] = (df["close"] * df["volume"]).rolling(20).sum() / df[
                "volume"
            ].rolling(20).sum()
            df["price_vs_vwap"] = (df["close"] - df["vwap"]) / df["vwap"]
        self._logger.debug(
            "⏱️   Advanced Volume Analysis: %.3fs", time.time() - cat_start
        )

        # 20. Market Microstructure
        cat_start = time.time()
        # Bid-Ask Spread proxy (using high-low range as spread indicator)
        df["spread_proxy"] = (df["high"] - df["low"]) / df["close"]
        df["spread_ma_ratio"] = (
            df["spread_proxy"] / df["spread_proxy"].rolling(20).mean()
        )

        # Price efficiency (how much price moved vs range)
        df["price_efficiency"] = abs(df["close"] - df["open"]) / (
            df["high"] - df["low"]
        )

        # Gap analysis
        df["gap_up"] = (df["open"] > df["high"].shift(1)).astype(int)
        df["gap_down"] = (df["open"] < df["low"].shift(1)).astype(int)
        df["gap_size"] = (df["open"] - df["close"].shift(1)) / df["close"].shift(1)
        self._logger.debug(
            "⏱️   Market Microstructure: %.3fs", time.time() - cat_start
        )

        # 21. Advanced Trend Analysis
        cat_start = time.time()
        # Parabolic SAR approximation
        df["psar_approx"] = (
            df["low"].rolling(10).min()
            if df["close"].iloc[-1] > df["close"].iloc[-10]
            else df["high"].rolling(10).max()
        )

        # Trend strength using multiple timeframes
        df["trend_5"] = np.where(df["close"] > df["close"].shift(5), 1, -1)
        df["trend_10"] = np.where(df["close"] > df["close"].shift(10), 1, -1)
        df["trend_20"] = np.where(df["close"] > df["close"].shift(20), 1, -1)
        df["trend_consensus"] = df["trend_5"] + df["trend_10"] + df["trend_20"]

        # Trend acceleration
        df["trend_acceleration"] = df["close"].diff(5) - df["close"].diff(10)
        self._logger.debug(
            "⏱️   Advanced Trend Analysis: %.3fs", time.time() - cat_start
        )

        # 22. Volatility Regime Detection
        cat_start = time.time()
        # GARCH-like volatility clustering
        df["volatility_cluster"] = (
            df["price_change"].abs()
            > df["price_change"].abs().rolling(20).mean() * 1.5
        ).astype(int)

        # Volatility breakout
        df["vol_breakout_up"] = (
            df["high"] > df["high"].rolling(20).max().shift(1)
        ).astype(int)
        df["vol_breakout_down"] = (
            df["low"] < df["low"].rolling(20).min().shift(1)
        ).astype(int)

        # Volatility compression/expansion
        df["vol_compression"] = (
            df["atr_14"] < df["atr_14"].rolling(20).mean() * 0.8
        ).astype(int)
        df["vol_expansion"] = (
            df["atr_14"] > df["atr_14"].rolling(20).mean() * 1.2
        ).astype(int)
        self._logger.debug(
            "⏱️   Volatility Regime Detection: %.3fs", time.time() - cat_start
        )

        # 23. Market Regime Indicators
        cat_start = time.time()
        # Bull/Bear market detection
        sma_50 = df["sma_50"]
        sma_200 = df["close"].rolling(200).mean()
        df["bull_market"] = (sma_50 > sma_200).astype(int)
        df["bear_market"] = (sma_50 < sma_200).astype(int)

        # Market regime strength
        df["regime_strength"] = abs(sma_50 - sma_200) / sma_200

        # Sideways market detection
        df["sideways_market"] = (df["regime_strength"] < 0.02).astype(int)
        self._logger.debug(
            "⏱️   Market Regime Indicators: %.3fs", time.time() - cat_start
        )

        # 24. Advanced Price Action
        cat_start = time.time()
        # Inside/Outside bars
        df["inside_bar"] = (
            (df["high"] < df["high"].shift(1)) & (df["low"] > df["low"].shift(1))
        ).astype(int)
        df["outside_bar"] = (
            (df["high"] > df["high"].shift(1)) & (df["low"] < df["low"].shift(1))
        ).astype(int)

        # Engulfing patterns
        df["bullish_engulfing"] = (
            (df["close"] > df["open"])
            & (df["close"].shift(1) < df["open"].shift(1))
            & (df["open"] < df["close"].shift(1))
            & (df["close"] > df["open"].shift(1))
        ).astype(int)
        df["bearish_engulfing"] = (
            (df["close"] < df["open"])
            & (df["close"].shift(1) > df["open"].shift(1))
            & (df["open"] > df["close"].shift(1))
            & (df["close"] < df["open"].shift(1))
        ).astype(int)

        # Pin bar detection
        body_size = abs(df["close"] - df["open"])
        total_range = df["high"] - df["low"]
        df["pin_bar_up"] = (
            (body_size / total_range < 0.3)
            & ((df["high"] - df[["open", "close"]].max(axis=1)) / total_range > 0.6)
        ).astype(int)
        df["pin_bar_down"] = (
            (body_size / total_range < 0.3)
            & ((df[["open", "close"]].min(axis=1) - df["low"]) / total_range > 0.6)
        ).astype(int)
        self._logger.debug(
            "⏱️   Advanced Price Action: %.3fs", time.time() - cat_start
        )

        # 25. Time-based Features
        cat_start = time.time()
        # Session-based features
        df["hour"] = df.index.hour
        df["day_of_week"] = df.index.dayofweek
        df["is_weekend"] = (df["day_of_week"] >= 5).astype(int)

        # Market session strength
        df["asian_session"] = ((df["hour"] >= 0) & (df["hour"] <= 8)).astype(int)
        df["london_session"] = ((df["hour"] >= 8) & (df["hour"] <= 16)).astype(int)
        df["ny_session"] = ((df["hour"] >= 13) & (df["hour"] <= 21)).astype(int)
        df["overlap_session"] = ((df["hour"] >= 13) & (df["hour"] <= 16)).astype(
            int
        )

        # Time-based volatility
        df["session_volatility"] = (
            df["price_change"].abs().groupby(df["hour"]).transform("mean")
        )
        self._logger.debug(
            "⏱️   Time-based Features: %.3fs", time.time() - cat_start
        )

        # 26. Advanced Statistical Features
        cat_start = time.time()
        # Упрощенные статистические метрики без сложных вычислений
        # Заменяем медленные Hurst Exponent и Fractal Dimension на быстрые альтернативы

        # Простой тренд persistence (замена Hurst Exponent)
        price_diff = df["close"].diff()
        # Векторизованное вычисление без apply
        positive_changes = (price_diff > 0).rolling(20).sum()
        total_changes = price_diff.rolling(20).count()
        trend_persistence = (positive_changes / total_changes - 0.5) * 2
        df["trend_persistence"] = trend_persistence

        # Простая фрактальная сложность (замена Fractal Dimension)
        price_range = df["high"] - df["low"]
        complexity = price_range.rolling(20).std() / price_range.rolling(20).mean()
        df["price_complexity"] = complexity

        self._logger.debug(
            "⏱️   Advanced Statistical Features: %.3fs", time.time() - cat_start
        )

        # 27. Risk Metrics
        cat_start = time.time()
        # Value at Risk (VaR) approximation
        df["var_95"] = df["price_change"].rolling(20).quantile(0.05)
        df["var_99"] = df["price_change"].rolling(20).quantile(0.01)

        # Упрощенный Expected Shortfall без apply
        # Используем простое приближение через квантили
        df["expected_shortfall"] = (
            df["price_change"].rolling(20).quantile(0.025)
        )  # Приближение

        # Maximum Drawdown
        rolling_max = df["close"].rolling(20).max()
        df["drawdown"] = (df["close"] - rolling_max) / rolling_max
        df["max_drawdown"] = df["drawdown"].rolling(20).min()
        self._logger.debug(
            "⏱️   Risk Metrics: %.3fs", time.time() - cat_start
        )

        # 28. Cross-Asset Correlations (if multiple symbols)
        cat_start = time.time()
        # This would require data from other symbols, so we'll add placeholder
        df["correlation_placeholder"] = (
            0  # To be implemented with multi-symbol data
        )
        self._logger.debug(
            "⏱️   Cross-Asset Correlations: %.3fs", time.time() - cat_start
        )

        # Очищаем все бесконечные и NaN значения
        df = df.replace([np.inf, -np.inf], np.nan)
        df = df.bfill().ffill()

        # Сохраняем предвычисленные метрики
        self.precomputed_metrics_df = df
        total_time = time.time() - start_time
        self._logger.info(
            "✅ Computed %d metrics in %.3fs", len(df.columns), total_time
        )
        self._logger.info("🎉 All metrics precomputed successfully!")

    def extract_entry_metrics(self) -> pd.DataFrame:
        """
        Извлекает метрики на момент входа для каждой сделки.

        Returns:
        --------
        pd.DataFrame
            DataFrame с метриками на момент входа для каждой сделки
        """
        if self.trades.empty:
            self._logger.warning("No trades to analyze")
            return pd.DataFrame()

        # Предвычисляем метрики если еще не сделано
        if self.precomputed_metrics_df is None:
            self.precompute_all_metrics()

        self._logger.info(
            f"🔍 Starting entry metrics extraction for {len(self.trades)} trades..."
        )
        metrics_list = []

        for i, (_, trade) in enumerate(self.trades.iterrows()):
            if i % 10 == 0:  # Логируем каждые 10 сделок
                self._logger.info(f"📊 Processing trade {i + 1}/{len(self.trades)}...")

            # нужно брать на одну свечу раньше
            entry_time = trade["entry_time"] - pd.Timedelta(minutes=1)
            metrics_df = self.precomputed_metrics_df

            # Находим индекс бара входа
            try:
                entry_idx = metrics_df.index.get_loc(entry_time)
            except KeyError:
                self._logger.warning(
                    "Entry time %s not found in metrics data", entry_time
                )
                continue

            if entry_idx < 20:  # Минимум данных для расчета индикаторов
                self._logger.debug(
                    f"Insufficient data for trade {i + 1}: {entry_idx} bars (need 20+)"
                )
                continue

            # Извлекаем метрики на момент входа
            metrics = self._extract_metrics_from_precomputed(
                metrics_df, entry_idx, trade
            )
            metrics_list.append(metrics)

        self._logger.info(f"✅ Extracted metrics for {len(metrics_list)} trades")
        self.entry_metrics = pd.DataFrame(metrics_list)
        return self.entry_metrics

    def _extract_metrics_from_precomputed(
        self, metrics_df: pd.DataFrame, entry_idx: int, trade: pd.Series
    ) -> Dict:
        """
        Извлекает метрики из предвычисленных данных для конкретной сделки.
        Это намного быстрее чем пересчитывать все метрики заново.
        """
        current = metrics_df.iloc[entry_idx]
        entry_price = trade["entry_price"]
        is_long = trade["is_long"]

        # Базовые метрики
        metrics = {
            "trade_id": trade.name,
            "entry_time": trade["entry_time"],
            "exit_reason": trade["exit_reason"],
            "pnl_abs": trade["pnl_abs"],
            "is_long": is_long,
            "entry_price": entry_price,
        }

        # Извлекаем предвычисленные метрики
        metric_mapping = {
            # Волатильность
            "atr_14": current.get("atr_14", 0),
            "atr_20": current.get("atr_20", 0),
            "recent_volatility": current.get("recent_volatility", 0),
            "historical_volatility": current.get("historical_volatility", 0),
            "volatility_ratio": current.get("volatility_ratio", 1),
            # Тренд
            "price_vs_ema9": (entry_price - current.get("ema_9", entry_price))
            / entry_price,
            "price_vs_ema21": (entry_price - current.get("ema_21", entry_price))
            / entry_price,
            "price_vs_ema50": (entry_price - current.get("ema_50", entry_price))
            / entry_price,
            # Осцилляторы
            "rsi_14": current.get("rsi_14", 50),
            "stoch_k": current.get("stoch_k", 50),
            "bb_position": current.get("bb_position", 0.5),
            "bb_width": current.get("bb_width", 0),
            # Объем
            "volume_ratio": current.get("volume_ratio", 1),
            "volume_imbalance": current.get("volume_imbalance", 0),
            "volume_price_correlation": current.get("volume_price_corr", 0),
            # MACD
            "macd_line": current.get("macd_line", 0),
            "macd_signal": current.get("macd_signal", 0),
            "macd_histogram": current.get("macd_histogram", 0),
            # Другие индикаторы
            "williams_r": current.get("williams_r", -50),
            "cci": current.get("cci", 0),
            # Моментум
            "momentum_5": current.get("momentum_5", 0),
            "momentum_10": current.get("momentum_10", 0),
            "momentum_20": current.get("momentum_20", 0),
            # Support/Resistance
            "support_level": current.get("support_level", 0),
            "resistance_level": current.get("resistance_level", 0),
            # Consecutive moves
            "consecutive_up": current.get("consecutive_up", 0),
            "consecutive_down": current.get("consecutive_down", 0),
            # Distance from extremes
            "distance_from_high": current.get("distance_from_high", 0),
            "distance_from_low": current.get("distance_from_low", 0),
            # Distribution
            "price_skewness": current.get("price_skewness", 0),
            "price_kurtosis": current.get("price_kurtosis", 0),
            # НОВЫЕ МЕТРИКИ (17-28 категории)
            # Advanced Oscillators
            "adx": current.get("adx", 25),
            "plus_di": current.get("plus_di", 25),
            "minus_di": current.get("minus_di", 25),
            "di_cross_up": current.get("di_cross_up", False),
            "di_cross_down": current.get("di_cross_down", False),
            "adx_slope": current.get("adx_slope", 0),
            "adx_accel": current.get("adx_accel", 0),
            # Ichimoku Cloud
            "tenkan_sen": current.get("tenkan_sen", entry_price),
            "kijun_sen": current.get("kijun_sen", entry_price),
            "senkou_span_a": current.get("senkou_span_a", entry_price),
            "senkou_span_b": current.get("senkou_span_b", entry_price),
            "chikou_span": current.get("chikou_span", entry_price),
            "price_above_cloud": current.get("price_above_cloud", False),
            "price_below_cloud": current.get("price_below_cloud", False),
            "cloud_thickness": current.get("cloud_thickness", 0),
            "tenkan_kijun_cross": current.get("tenkan_kijun_cross", False),
            # Advanced Volume Analysis
            "obv": current.get("obv", 0),
            "volume_roc": current.get("volume_roc", 0),
            "ad_line": current.get("ad_line", 0),
            "mfi": current.get("mfi", 50),
            "vwap": current.get("vwap", entry_price),
            "price_vs_vwap": current.get("price_vs_vwap", 0),
            # Market Microstructure
            "spread_proxy": current.get("spread_proxy", 0),
            "spread_ma_ratio": current.get("spread_ma_ratio", 1),
            "price_efficiency": current.get("price_efficiency", 0.5),
            "gap_up": current.get("gap_up", False),
            "gap_down": current.get("gap_down", False),
            "gap_size": current.get("gap_size", 0),
            # Advanced Trend Analysis
            "psar_approx": current.get("psar_approx", entry_price),
            "trend_5": current.get("trend_5", 0),
            "trend_10": current.get("trend_10", 0),
            "trend_20": current.get("trend_20", 0),
            "trend_consensus": current.get("trend_consensus", 0),
            "trend_acceleration": current.get("trend_acceleration", 0),
            # Volatility Regime Detection
            "volatility_cluster": current.get("volatility_cluster", False),
            "vol_breakout_up": current.get("vol_breakout_up", False),
            "vol_breakout_down": current.get("vol_breakout_down", False),
            "vol_compression": current.get("vol_compression", False),
            "vol_expansion": current.get("vol_expansion", False),
            # Market Regime Indicators
            "bull_market": current.get("bull_market", False),
            "bear_market": current.get("bear_market", False),
            "regime_strength": current.get("regime_strength", 0),
            "sideways_market": current.get("sideways_market", False),
            # Advanced Price Action
            "inside_bar": current.get("inside_bar", False),
            "outside_bar": current.get("outside_bar", False),
            "bullish_engulfing": current.get("bullish_engulfing", False),
            "bearish_engulfing": current.get("bearish_engulfing", False),
            "pin_bar_up": current.get("pin_bar_up", False),
            "pin_bar_down": current.get("pin_bar_down", False),
            # Time-based Features
            "hour": current.get("hour", 12),
            "day_of_week": current.get("day_of_week", 2),
            "is_weekend": current.get("is_weekend", False),
            "asian_session": current.get("asian_session", False),
            "london_session": current.get("london_session", False),
            "ny_session": current.get("ny_session", False),
            "overlap_session": current.get("overlap_session", False),
            "session_volatility": current.get("session_volatility", 0),
            # Advanced Statistical Features
            "trend_persistence": current.get("trend_persistence", 0.0),
            "price_complexity": current.get("price_complexity", 1.0),
            # Risk Metrics
            "var_95": current.get("var_95", 0),
            "var_99": current.get("var_99", 0),
            "expected_shortfall": current.get("expected_shortfall", 0),
            "drawdown": current.get("drawdown", 0),
            "max_drawdown": current.get("max_drawdown", 0),
        }

        # Вычисляем производные метрики
        support = current.get("support_level", 0)
        resistance = current.get("resistance_level", 0)

        if is_long:
            risk_distance = (entry_price - support) / entry_price if support > 0 else 0
            reward_distance = (
                (resistance - entry_price) / entry_price if resistance > 0 else 0
            )
        else:
            risk_distance = (
                (resistance - entry_price) / entry_price if resistance > 0 else 0
            )
            reward_distance = (
                (entry_price - support) / entry_price if support > 0 else 0
            )

        risk_reward_ratio = reward_distance / risk_distance if risk_distance > 0 else 0

        # ATR ratios
        atr_ratio_14 = current.get("atr_14", 0) / entry_price if entry_price > 0 else 0
        atr_ratio_20 = current.get("atr_20", 0) / entry_price if entry_price > 0 else 0

        # Trend direction and strength
        ema_9 = current.get("ema_9", entry_price)
        ema_21 = current.get("ema_21", entry_price)
        ema_50 = current.get("ema_50", entry_price)

        trend_direction = (
            1 if ema_9 > ema_21 > ema_50 else -1 if ema_9 < ema_21 < ema_50 else 0
        )
        trend_strength = abs(ema_9 - ema_50) / entry_price if entry_price > 0 else 0

        # Momentum acceleration
        momentum_acceleration = current.get("momentum_5", 0) - current.get(
            "momentum_10", 0
        )

        # Net direction
        net_direction = current.get("consecutive_up", 0) - current.get(
            "consecutive_down", 0
        )

        # Добавляем производные метрики
        metrics.update(metric_mapping)
        metrics.update(
            {
                "risk_distance": risk_distance,
                "reward_distance": reward_distance,
                "risk_reward_ratio": risk_reward_ratio,
                "atr_ratio_14": atr_ratio_14,
                "atr_ratio_20": atr_ratio_20,
                "trend_direction": trend_direction,
                "trend_strength": trend_strength,
                "momentum_acceleration": momentum_acceleration,
                "net_direction": net_direction,
            }
        )

        # Временные метрики
        entry_time = pd.to_datetime(trade["entry_time"])
        hour = entry_time.hour
        day_of_week = entry_time.weekday()

        metrics.update(
            {
                "hour_of_day": hour,
                "day_of_week": day_of_week,
                "is_london_session": 8 <= hour <= 16,
                "is_ny_session": 13 <= hour <= 21,
                "is_asian_session": 0 <= hour <= 8 or 22 <= hour <= 23,
                "is_overlap": 13 <= hour <= 16,
                "is_monday": day_of_week == 0,
                "is_friday": day_of_week == 4,
            }
        )

        # Свечные метрики
        body_size = abs(current["close"] - current["open"])
        total_range = current["high"] - current["low"]

        if total_range > 0:
            body_ratio = body_size / total_range
            upper_shadow_ratio = (
                current["high"] - max(current["open"], current["close"])
            ) / total_range
            lower_shadow_ratio = (
                min(current["open"], current["close"]) - current["low"]
            ) / total_range

            metrics.update(
                {
                    "body_ratio": body_ratio,
                    "upper_shadow_ratio": upper_shadow_ratio,
                    "lower_shadow_ratio": lower_shadow_ratio,
                    "is_doji": body_ratio < 0.1,
                    "is_hammer": lower_shadow_ratio > 0.6 and upper_shadow_ratio < 0.2,
                    "is_shooting_star": upper_shadow_ratio > 0.6
                    and lower_shadow_ratio < 0.2,
                    "is_engulfing": body_ratio > 0.7,
                }
            )
        else:
            metrics.update(
                {
                    "body_ratio": 0,
                    "upper_shadow_ratio": 0,
                    "lower_shadow_ratio": 0,
                    "is_doji": True,
                    "is_hammer": False,
                    "is_shooting_star": False,
                    "is_engulfing": False,
                }
            )

        return metrics

    def calculate_separation_metrics(
        self, metric_name: str, by_direction: bool = True
    ) -> Dict:
        """
        Вычисляет метрики разделения для конкретной метрики.

        Parameters:
        -----------
        metric_name : str
            Название метрики для анализа
        by_direction : bool
            Если True, анализирует отдельно для long и short позиций

        Returns:
        --------
        Dict
            Словарь с метриками разделения
        """
        if self.entry_metrics is None:
            self.extract_entry_metrics()

        if self.entry_metrics.empty or metric_name not in self.entry_metrics.columns:
            return {}

        results = {}

        if by_direction and "is_long" in self.entry_metrics.columns:
            # Анализируем отдельно для long и short позиций
            for direction, direction_name in [(True, "long"), (False, "short")]:
                direction_data = self.entry_metrics[
                    self.entry_metrics["is_long"] == direction
                ]

                # Разделяем на TP и SL для данного направления
                tp_data = direction_data[
                    direction_data["exit_reason"] == "take_profit"
                ][metric_name].dropna()
                sl_data = direction_data[direction_data["exit_reason"] == "stop_loss"][
                    metric_name
                ].dropna()

                # Анализируем даже если данных мало (минимум 1 TP и 1 SL)
                if len(tp_data) >= 1 and len(sl_data) >= 1:
                    # Вычисляем метрики разделения
                    direction_metrics = self._calculate_direction_metrics(
                        metric_name, tp_data, sl_data, direction_name
                    )
                    results.update(direction_metrics)
                else:
                    # Если данных недостаточно, создаем запись с нулевыми значениями
                    direction_metrics = self._create_empty_direction_metrics(
                        metric_name, direction_name, len(tp_data), len(sl_data)
                    )
                    results.update(direction_metrics)
        else:
            # Анализируем все позиции вместе
            tp_data = self.entry_metrics[
                self.entry_metrics["exit_reason"] == "take_profit"
            ][metric_name].dropna()
            sl_data = self.entry_metrics[
                self.entry_metrics["exit_reason"] == "stop_loss"
            ][metric_name].dropna()

            if len(tp_data) > 0 and len(sl_data) > 0:
                all_metrics = self._calculate_direction_metrics(
                    metric_name, tp_data, sl_data, "all"
                )
                results.update(all_metrics)

        return results

    def _create_empty_direction_metrics(
        self, metric_name: str, direction: str, tp_count: int, sl_count: int
    ) -> Dict:
        """Создает пустые метрики для направлений с недостаточными данными"""
        prefix = f"{direction}_" if direction != "all" else ""

        return {
            f"{prefix}metric_name": f"{metric_name}_{direction}"
            if direction != "all"
            else metric_name,
            f"{prefix}ks_statistic": 0.0,
            f"{prefix}ks_pvalue": 1.0,
            f"{prefix}js_divergence": 0.0,
            f"{prefix}wasserstein_distance": 0.0,
            f"{prefix}auc_score": 0.5,  # Случайный уровень
            f"{prefix}gini_coefficient": 0.0,
            f"{prefix}mutual_information": 0.0,
            f"{prefix}tp_count": tp_count,
            f"{prefix}sl_count": sl_count,
            f"{prefix}tp_mean": 0.0,
            f"{prefix}sl_mean": 0.0,
            f"{prefix}tp_std": 0.0,
            f"{prefix}sl_std": 0.0,
        }

    def _calculate_direction_metrics(
        self, metric_name: str, tp_data: pd.Series, sl_data: pd.Series, direction: str
    ) -> Dict:
        """Вычисляет метрики разделения для конкретного направления"""
        # 1. Kolmogorov-Smirnov Test
        ks_statistic, ks_pvalue = stats.ks_2samp(tp_data, sl_data)

        # 2. Jensen-Shannon Divergence
        js_divergence = self._calculate_js_divergence(tp_data, sl_data)

        # 3. Wasserstein Distance
        wasserstein_distance = stats.wasserstein_distance(tp_data, sl_data)

        # 4. AUC (Area Under ROC Curve)
        auc_score = self._calculate_auc(tp_data, sl_data)

        # 5. Gini Coefficient
        gini_coefficient = 2 * auc_score - 1

        # 6. Mutual Information
        mutual_info = self._calculate_mutual_information(tp_data, sl_data)

        prefix = f"{direction}_" if direction != "all" else ""

        return {
            f"{prefix}metric_name": f"{metric_name}_{direction}"
            if direction != "all"
            else metric_name,
            f"{prefix}ks_statistic": ks_statistic,
            f"{prefix}ks_pvalue": ks_pvalue,
            f"{prefix}js_divergence": js_divergence,
            f"{prefix}wasserstein_distance": wasserstein_distance,
            f"{prefix}auc_score": auc_score,
            f"{prefix}gini_coefficient": gini_coefficient,
            f"{prefix}mutual_information": mutual_info,
            f"{prefix}tp_count": len(tp_data),
            f"{prefix}sl_count": len(sl_data),
            f"{prefix}tp_mean": tp_data.mean(),
            f"{prefix}sl_mean": sl_data.mean(),
            f"{prefix}tp_std": tp_data.std(),
            f"{prefix}sl_std": sl_data.std(),
        }

    def _calculate_js_divergence(
        self, data1: pd.Series, data2: pd.Series, bins: int = 50
    ) -> float:
        """Вычисляет Jensen-Shannon divergence"""
        # Создаем гистограммы
        min_val = min(data1.min(), data2.min())
        max_val = max(data1.max(), data2.max())

        if min_val == max_val:
            return 0.0

        bin_edges = np.linspace(min_val, max_val, bins + 1)

        hist1, _ = np.histogram(data1, bins=bin_edges, density=True)
        hist2, _ = np.histogram(data2, bins=bin_edges, density=True)

        # Нормализуем
        hist1 = hist1 / (hist1.sum() + 1e-10)
        hist2 = hist2 / (hist2.sum() + 1e-10)

        # Среднее распределение
        m = (hist1 + hist2) / 2

        # JS divergence
        js_div = 0.5 * entropy(hist1, m) + 0.5 * entropy(hist2, m)

        return js_div

    def _calculate_auc(self, tp_data: pd.Series, sl_data: pd.Series) -> float:
        """Вычисляет AUC для разделения TP/SL"""
        # Создаем бинарные метки: 1 для TP, 0 для SL
        tp_labels = np.ones(len(tp_data))
        sl_labels = np.zeros(len(sl_data))

        y_true = np.concatenate([tp_labels, sl_labels])
        y_scores = (
            MinMaxScaler()
            .fit_transform(
                np.concatenate([tp_data.values, sl_data.values]).reshape(-1, 1)
            )
            .flatten()
        )

        try:
            auc = roc_auc_score(y_true, y_scores)
            return auc
        except ValueError:
            return 0.5  # Случайное разделение

    def _calculate_mutual_information(
        self, tp_data: pd.Series, sl_data: pd.Series, bins: int = 50
    ) -> float:
        """Вычисляет взаимную информацию"""
        # Создаем бинарные метки
        tp_labels = np.ones(len(tp_data))
        sl_labels = np.zeros(len(sl_data))

        y_true = np.concatenate([tp_labels, sl_labels])
        y_scores = np.concatenate([tp_data.values, sl_data.values])

        # Дискретизируем непрерывные значения
        min_val = min(tp_data.min(), sl_data.min())
        max_val = max(tp_data.max(), sl_data.max())

        if min_val == max_val:
            return 0.0

        bin_edges = np.linspace(min_val, max_val, bins + 1)
        y_scores_discrete = np.digitize(y_scores, bin_edges)

        # Вычисляем взаимную информацию
        mi = mutual_info_classif(
            y_scores_discrete.reshape(-1, 1), y_true, discrete_features=True
        )[0]

        return mi

    def find_best_predictors(self, top_n: int = 10) -> pd.DataFrame:
        """
        Находит лучшие предикторы исхода сделок.

        Parameters:
        -----------
        top_n : int
            Количество лучших предикторов для возврата

        Returns:
        --------
        pd.DataFrame
            DataFrame с лучшими предикторами, отсортированными по AUC
        """
        if self.entry_metrics is None:
            self._logger.info("📈 Entry metrics not found, extracting...")
            self.extract_entry_metrics()

        if self.entry_metrics.empty:
            self._logger.warning("No entry metrics available for analysis")
            return pd.DataFrame()

        self._logger.info(
            f"🔬 Starting separation analysis for {len(self.entry_metrics)} trades..."
        )

        # Исключаем служебные колонки
        exclude_cols = [
            "trade_id",
            "entry_time",
            "exit_reason",
            "pnl_abs",
            "is_long",
            "entry_price",
        ]
        metric_cols = [
            col for col in self.entry_metrics.columns if col not in exclude_cols
        ]

        self._logger.info(f"📊 Analyzing {len(metric_cols)} metrics...")

        results = []

        for i, metric in enumerate(metric_cols):
            if i % 20 == 0:  # Логируем каждые 20 метрик
                self._logger.info(
                    f"🧮 Processing metric {i + 1}/{len(metric_cols)}: {metric}"
                )

            separation_metrics = self.calculate_separation_metrics(
                metric, by_direction=True
            )
            if separation_metrics:
                # Обрабатываем результаты для каждого направления
                for key, value in separation_metrics.items():
                    if key.endswith("_auc_score"):
                        direction = key.replace("_auc_score", "")
                        metric_name = metric

                        # Создаем запись для данного направления
                        result_row = {
                            "metric_name": f"{metric_name}_{direction}",
                            "base_metric": metric_name,
                            "direction": direction,
                            "auc_score": value,
                            "ks_statistic": separation_metrics.get(
                                f"{direction}_ks_statistic", 0
                            ),
                            "js_divergence": separation_metrics.get(
                                f"{direction}_js_divergence", 0
                            ),
                            "mutual_information": separation_metrics.get(
                                f"{direction}_mutual_information", 0
                            ),
                            "tp_count": separation_metrics.get(
                                f"{direction}_tp_count", 0
                            ),
                            "sl_count": separation_metrics.get(
                                f"{direction}_sl_count", 0
                            ),
                            "tp_mean": separation_metrics.get(
                                f"{direction}_tp_mean", 0
                            ),
                            "sl_mean": separation_metrics.get(
                                f"{direction}_sl_mean", 0
                            ),
                            "tp_std": separation_metrics.get(f"{direction}_tp_std", 0),
                            "sl_std": separation_metrics.get(f"{direction}_sl_std", 0),
                        }
                        results.append(result_row)

        if not results:
            self._logger.warning("No separation results found")
            return pd.DataFrame()

        self._logger.info(f"📋 Found {len(results)} metric-direction combinations")

        results_df = pd.DataFrame(results)

        # Сортируем по AUC (лучшие предикторы имеют AUC дальше от 0.5)
        results_df["auc_distance_from_random"] = abs(results_df["auc_score"] - 0.5)
        results_df = results_df.sort_values("auc_distance_from_random", ascending=False)

        self.separation_results = results_df

        # Логируем топ результаты
        self._logger.info("🏆 Top 5 predictors found:")
        for i, (_, row) in enumerate(results_df.head(5).iterrows()):
            self._logger.info(
                f"  {i + 1}. {row['metric_name']}: AUC={row['auc_score']:.3f}, KS={row['ks_statistic']:.3f}"
            )

        return results_df.head(top_n)

    def save_entry_metrics(self, output_dir: str):
        """
        Сохраняет метрики входа в CSV файл.

        Parameters:
        -----------
        output_dir : str
            Директория для сохранения файла
        """
        if self.entry_metrics is None:
            self._logger.warning("No entry metrics to save")
            return

        import os

        os.makedirs(output_dir, exist_ok=True)
        file_path = os.path.join(output_dir, "entry_metrics.csv")
        self.entry_metrics.to_csv(file_path, index=False)
        self._logger.info(f"Entry metrics saved to: {file_path}")

    def plot_distributions(
        self,
        metric_name: str,
        save_path: Optional[str] = None,
        direction: Optional[str] = None,
    ):
        """
        Визуализирует распределения метрики для TP и SL.

        Parameters:
        -----------
        metric_name : str
            Название метрики для визуализации
        save_path : Optional[str]
            Путь для сохранения графика
        direction : Optional[str]
            Направление для фильтрации ('long' или 'short')
        """
        if self.entry_metrics is None:
            self.extract_entry_metrics()

        if self.entry_metrics.empty or metric_name not in self.entry_metrics.columns:
            self._logger.warning(f"Metric {metric_name} not found")
            return

        # Фильтруем данные по направлению если указано
        data_to_analyze = self.entry_metrics.copy()
        if direction and "is_long" in data_to_analyze.columns:
            if direction == "long":
                data_to_analyze = data_to_analyze[data_to_analyze["is_long"] == True]
            elif direction == "short":
                data_to_analyze = data_to_analyze[data_to_analyze["is_long"] == False]

        # Разделяем данные
        tp_data = data_to_analyze[data_to_analyze["exit_reason"] == "take_profit"][
            metric_name
        ].dropna()
        sl_data = data_to_analyze[data_to_analyze["exit_reason"] == "stop_loss"][
            metric_name
        ].dropna()

        if len(tp_data) == 0 or len(sl_data) == 0:
            self._logger.warning(
                f"Insufficient data for {metric_name} (direction: {direction})"
            )
            return

        # Создаем график
        direction_suffix = f" ({direction})" if direction else ""
        plt.figure(figsize=(12, 8))

        # Гистограммы
        plt.subplot(2, 2, 1)
        plt.hist(tp_data, alpha=0.7, label="Take Profit", bins=30, density=True)
        plt.hist(sl_data, alpha=0.7, label="Stop Loss", bins=30, density=True)
        plt.xlabel(metric_name)
        plt.ylabel("Density")
        plt.title(f"Distribution of {metric_name}{direction_suffix}")
        plt.legend()

        # Box plots
        plt.subplot(2, 2, 2)
        data_to_plot = [tp_data, sl_data]
        labels = ["Take Profit", "Stop Loss"]
        plt.boxplot(data_to_plot, labels=labels)
        plt.ylabel(metric_name)
        plt.title(f"Box Plot of {metric_name}")

        # Q-Q plot
        plt.subplot(2, 2, 3)
        stats.probplot(tp_data, dist="norm", plot=plt)
        plt.title("Q-Q Plot: Take Profit")

        plt.subplot(2, 2, 4)
        stats.probplot(sl_data, dist="norm", plot=plt)
        plt.title("Q-Q Plot: Stop Loss")

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches="tight")
        else:
            plt.show()

        plt.close()

    def generate_report(self) -> str:
        """
        Генерирует текстовый отчет с анализом условий сделок.

        Returns:
        --------
        str
            Текстовый отчет
        """
        if self.separation_results is None:
            self.find_best_predictors()

        if self.separation_results is None or self.separation_results.empty:
            return "No separation analysis results available."

        report = []
        report.append("=" * 60)
        report.append("📊 TRADE CONDITIONS ANALYSIS")
        report.append("=" * 60)

        # Общая статистика
        total_trades = len(self.entry_metrics) if self.entry_metrics is not None else 0
        tp_trades = (
            len(self.entry_metrics[self.entry_metrics["exit_reason"] == "take_profit"])
            if self.entry_metrics is not None
            else 0
        )
        sl_trades = (
            len(self.entry_metrics[self.entry_metrics["exit_reason"] == "stop_loss"])
            if self.entry_metrics is not None
            else 0
        )

        report.append(f"Total trades analyzed: {total_trades}")
        report.append(f"Take Profit trades: {tp_trades}")
        report.append(f"Stop Loss trades: {sl_trades}")
        report.append("")

        # Топ предикторы
        report.append("🏆 TOP PREDICTORS (by AUC distance from random):")
        report.append("-" * 60)
        report.append(
            f"{'Metric':<25} {'AUC':<8} {'KS':<8} {'JS':<8} {'TP':<6} {'SL':<6}"
        )
        report.append("-" * 60)

        for _, row in self.separation_results.head(10).iterrows():
            report.append(
                f"{row['metric_name']:<25} "
                f"{row['auc_score']:<8.3f} "
                f"{row['ks_statistic']:<8.3f} "
                f"{row['js_divergence']:<8.3f} "
                f"{row['tp_count']:<6} "
                f"{row['sl_count']:<6}"
            )

        return "\n".join(report)
