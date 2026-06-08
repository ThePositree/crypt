import logging
from collections.abc import Callable

import pandas as pd

from backtester.data_contracts import StrategyData, StrategyInput
from backtester.execution_context import (
    attach_execution_context,
    execution_context_from_run_kwargs,
)
from backtester.execution_sim import ExecutionSim
from backtester.results_analyzer import ResultsAnalyzer


class Backtester:
    """
    Unified interface for backtesting trading strategies with risk-based position sizing.

    Combines:
    - Single-asset OHLCV data
    - Signal generation strategy
    - Trade simulation with TP/SL/TTL
    - Results analysis and export

    Features:
    ---------
    - Support for multiple assets (BTC, ETH, etc.)
    - Realistic execution: fees, position size based on risk_percent and SL distance
    - Exit via Take Profit (maker), Stop Loss (taker) or TTL
    - Limit on simultaneous positions
    - Protection against trading with insufficient capital
    - Full analysis: Win Rate, PnL, Drawdown, periodic returns
    - CSV export

    Usage example:
    --------------
    >>> def strategy(df):
    ...     df = df.copy()
    ...     df["signal"] = 0
    ...     df.loc[df["close"] > df["close"].shift(1), "signal"] = 1  # long
    ...     df.loc[df["close"] < df["close"].shift(1), "signal"] = -1  # short
    ...     df["sl_price"] = 0.0
    ...     df.loc[df["signal"] == 1, "sl_price"] = (
    ...         df.loc[df["signal"] == 1, "close"] * 0.98
    ...     )
    ...     df.loc[df["signal"] == -1, "sl_price"] = (
    ...         df.loc[df["signal"] == -1, "close"] * 1.02
    ...     )
    ...     return df
    >>>
    >>> bt = Backtester(btc_df, strategy)
    >>> results = bt.run(
    ...     initial_capital=10000,
    ...     risk_percent=1.0,
    ...     rrr=2.0,
    ...     max_positions=3,
    ...     position_ttl_bars=15,
    ...     taker_fee=0.001,
    ...     maker_fee=0.0002,
    ...     max_allowed_leverage=25.0,
    ... )
    >>> results.print_report()
    >>> results.export_results("results/long_short_strategy_v1")
    """

    def __init__(
        self,
        df: StrategyInput,
        strategy: Callable[[StrategyInput], pd.DataFrame],
    ):
        """
        Backtester initialization.

        Parameters:
        ----------
        df : pd.DataFrame
            OHLCV DataFrame with DatetimeIndex for a single asset.
            Required columns: ['open', 'high', 'low', 'close', 'volume']

        strategy : Callable[[pd.DataFrame] -> pd.DataFrame]
            Function that takes a DataFrame and returns it with
            added 'signal' column:
                - 1 = long entry
                - -1 = short entry
                - 0 = no signal
            And 'sl_price' column with stop loss price.
            Example:
                def my_strategy(df):
                    df = df.copy()
                    df['signal'] = 0
                    df['sl_price'] = 0.0
                    # Long: price up
                    long_cond = df['close'] > df['close'].shift(1)
                    df.loc[long_cond, 'signal'] = 1
                    df.loc[long_cond, 'sl_price'] = df.loc[long_cond, 'close'] * 0.98
                    # Short: price down
                    short_cond = df['close'] < df['close'].shift(1)
                    df.loc[short_cond, 'signal'] = -1
                    df.loc[short_cond, 'sl_price'] = df.loc[short_cond, 'close'] * 1.02
                    return df

        Notes:
        ------
        - Strategy is applied to a single asset DataFrame.
        - DataFrame must have DatetimeIndex.
        - No look-ahead bias checks are performed - this is your responsibility.
        """
        self.data = df
        self.df = df.primary if isinstance(df, StrategyData) else df
        self.strategy = strategy
        self._logger = logging.getLogger(__name__)

    def run(
        self,
        initial_capital: float = 1000.0,
        taker_fee: float = 0.001,
        maker_fee: float = 0.0002,
        risk_percent: float = 1.0,
        rrr: float = 2.0,
        trail_activation_rrr: float = 0.0,
        trail_distance_atr: float = 0.0,
        max_positions: int = 5,
        position_ttl_bars: int = 20,
        min_net_exposure: float = 0.01,
        max_allowed_leverage: float = 25.0,
        is_isolated_futures: bool = False,
        max_allowed_margin: float = 1.0,
        risk_base_period: str = "trade",
        max_daily_profit: float | None = None,
        max_daily_loss: float | None = None,
        trading_begin: int | None = None,
        trading_end: int | None = None,
        exit_geometry: str = "sl_rrr",
        tp_move_pct: float | None = None,
        structural_sl_mode: str = "cap",
        min_tp_move_pct: float = 0.004,
        risk_free_rate_annual: float = 0.02,
    ) -> ResultsAnalyzer:
        """
        Runs backtest for a single trading instrument using risk-based position sizing.

        Parameters:
        ----------
        initial_capital : float, default 1000.0
            Starting capital amount.

        taker_fee : float, default 0.001 (0.1%)
            Fee for market orders (entry and exit via SL/TTL).

        maker_fee : float, default 0.0002 (0.02%)
            Fee for limit orders (exit via TP).

        risk_percent : float, default 1.0 (1%)
            Percentage of current capital you are willing to lose on a single trade.
            Example: 1.0 → 1% of current capital is at risk.
            Used to calculate position size: size = risk_usd / (entry_price - sl_price)

        rrr : float, default 2.0
            Reward to Risk ratio. Defines how many times further TP is than SL.
            Example: 2.0 → TP is 2x the distance from entry as SL.
            TP price = entry_price + (entry_price - sl_price) * rrr
        trail_activation_rrr : float, default 0.0
            Profit threshold in stop-distance multiples that activates trailing.
            ``0`` disables trailing and keeps fixed TP behaviour.
        trail_distance_atr : float, default 0.0
            Trailing distance in ATR units after activation.
        max_positions : int, default 5
            Maximum number of simultaneous positions.

        position_ttl_bars : int, default 20
            Maximum position duration in bars. If TP/SL not triggered, position closes at TTL.

        min_net_exposure : float, default 0.01 (1%)
            Minimum net exposure after fees. If net_exposure < min_net_exposure * capital,
            position is not opened.

        max_allowed_leverage : float, default 25.0
            Maximum allowed leverage for the strategy.
            If leverage > max_allowed_leverage, position is not opened.

        is_isolated_futures : bool, default False
            Enable isolated futures mode. In this mode:
            - All positions must have the same leverage
            - Each position is isolated from others

        max_allowed_margin : float, default 1.0
            Maximum allowed margin for the strategy.
            If margin > max_allowed_margin, position is not opened.

        max_daily_profit : float | None, optional
            Daily profit limit in RRR; new positions disabled when daily_rrr >= this.
        max_daily_loss : float | None, optional
            Daily loss limit in RRR; new positions disabled when daily_rrr <= -this.
        trading_begin : int | None, optional
            Start hour (0-23) of trading window; entries only when hour >= this.
        trading_end : int | None, optional
            End hour (0-24) of trading window; entries only when hour < this.
        risk_free_rate_annual : float, default 0.02 (2%)
            Annual risk-free rate in decimal for Sharpe ratio in results metrics.

        Returns:
        -----------
        ResultsAnalyzer
            Ready-to-use analyzer with metrics, report, and export capabilities.

        Execution Logic:
        --------------
        1. Strategy is applied → signal generation
        2. ExecutionSim is triggered → trade simulation
        3. ResultsAnalyzer is executed → analysis + report generation

        Special Cases:
        --------------
        - If strategy does not generate required columns, backtest returns empty results.
        - If there are no trades, analyzer is still created but metrics will reflect absence of trades.
        - **Supports both long (signal=1) and short (signal=-1) positions**
        Note:
        -----
        Capital is shared across all trades of the instrument.
        This models real-world portfolio management scenarios.
        """
        self._logger.info("Starting backtest for a single asset...")
        self._logger.info("Parameters:")
        for param, value in [
            ("Initial Capital", initial_capital),
            ("Risk Percent", risk_percent),
            ("RRR", rrr),
            ("Trail Activation RRR", trail_activation_rrr),
            ("Trail Distance ATR", trail_distance_atr),
            ("Taker Fee", taker_fee),
            ("Maker Fee", maker_fee),
            ("Max Positions", max_positions),
            ("Position TTL", position_ttl_bars),
            ("Min Net Exposure", min_net_exposure),
            ("Max Allowed Leverage", max_allowed_leverage),
            ("Isolated Futures", is_isolated_futures),
            ("Max Allowed Margin", max_allowed_margin),
            ("Risk Base Period", risk_base_period),
        ]:
            self._logger.info("  %s: %s", param, value)
        if max_daily_profit is not None:
            self._logger.info("  Max Daily Profit (RRR): %s", max_daily_profit)
        if max_daily_loss is not None:
            self._logger.info("  Max Daily Loss (RRR): %s", max_daily_loss)
        if trading_begin is not None:
            self._logger.info("  Trading Begin (hour): %s", trading_begin)
        if trading_end is not None:
            self._logger.info("  Trading End (hour): %s", trading_end)

        sim = ExecutionSim(
            initial_capital=initial_capital,
            taker_fee=taker_fee,
            maker_fee=maker_fee,
            risk_percent=risk_percent,
            rrr=rrr,
            trail_activation_rrr=trail_activation_rrr,
            trail_distance_atr=trail_distance_atr,
            max_positions=max_positions,
            position_ttl_bars=position_ttl_bars,
            min_net_exposure=min_net_exposure,
            max_allowed_leverage=max_allowed_leverage,
            is_isolated_futures=is_isolated_futures,
            max_allowed_margin=max_allowed_margin,
            risk_base_period=risk_base_period,
            max_daily_profit=max_daily_profit,
            max_daily_loss=max_daily_loss,
            trading_begin=trading_begin,
            trading_end=trading_end,
            exit_geometry=exit_geometry,
            tp_move_pct=tp_move_pct,
            structural_sl_mode=structural_sl_mode,
            min_tp_move_pct=min_tp_move_pct,
        )

        execution_context = execution_context_from_run_kwargs(
            exit_geometry=exit_geometry,
            tp_move_pct=tp_move_pct,
            structural_sl_mode=structural_sl_mode,
            min_tp_move_pct=min_tp_move_pct,
        )
        signaled_df = pd.DataFrame()
        try:
            strategy_input: StrategyInput
            if isinstance(self.data, StrategyData):
                strategy_input = attach_execution_context(self.data.copy(), execution_context)
            else:
                strategy_input = attach_execution_context(self.df.copy(), execution_context)
            signaled_df = self.strategy(strategy_input)

            if "signal" not in signaled_df.columns:
                self._logger.error("🚨 Strategy did not generate 'signal' column.")
                trades_df = pd.DataFrame()
            elif "sl_price" not in signaled_df.columns:
                self._logger.error("🚨 Strategy did not generate 'sl_price' column.")
                trades_df = pd.DataFrame()
            else:
                trades_df = sim.run(signaled_df)
                if trades_df.empty:
                    self._logger.warning("🚫 No trades generated for the asset.")
                else:
                    self._logger.info("  📊 Trades: %d", len(trades_df))

        except Exception:
            self._logger.exception("🚨 Error during backtest execution")
            trades_df = pd.DataFrame()

        analyzer = ResultsAnalyzer(trades_df, signal_df=signaled_df)
        analyzer.generate(risk_free_rate_annual=risk_free_rate_annual)

        return analyzer
