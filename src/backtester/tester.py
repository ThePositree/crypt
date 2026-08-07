import logging
import time
from collections.abc import Callable

import pandas as pd

from backtester.data_contracts import IntrabarExecutionData, StrategyData, StrategyInput
from backtester.execution_context import (
    attach_execution_context,
    execution_context_from_run_kwargs,
)
from backtester.execution_sim import ExecutionSim
from backtester.progress import HeartbeatLogger, ProgressLogger, format_duration
from backtester.results_analyzer import ResultsAnalyzer


def _utc_timestamp(value: str | pd.Timestamp | None) -> pd.Timestamp | None:
    if value is None:
        return None
    ts = pd.Timestamp(value)
    if ts.tzinfo is None:
        return ts.tz_localize("UTC")
    return ts.tz_convert("UTC")


def _slice_execution_window(
    frame: pd.DataFrame,
    *,
    start: pd.Timestamp | None,
    end: pd.Timestamp | None,
) -> pd.DataFrame:
    sliced = frame
    if start is not None:
        sliced = sliced.loc[sliced.index >= start]
    if end is not None:
        sliced = sliced.loc[sliced.index <= end]
    return sliced


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
        *,
        ohlcv: pd.DataFrame | None = None,
    ):
        """
        Backtester initialization.

        Parameters:
        ----------
        df : StrategyInput
            Plain OHLCV DataFrame, or a StrategyData bundle passed through to
            the strategy.
        ohlcv : pd.DataFrame, optional
            Explicit OHLCV frame used by the simulator when ``df`` is a
            StrategyData bundle.

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
        if isinstance(df, StrategyData):
            if ohlcv is None:
                raise ValueError("Backtester requires explicit ohlcv when input is StrategyData")
            self.df = ohlcv
        else:
            self.df = df if ohlcv is None else ohlcv
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
        position_ttl_minutes: int = 0,
        min_net_exposure: float = 0.01,
        max_allowed_leverage: float = 25.0,
        max_allowed_margin: float = 1.0,
        risk_base_period: str = "trade",
        max_daily_profit: float | None = None,
        max_daily_loss: float | None = None,
        trading_begin: int | None = None,
        trading_end: int | None = None,
        capital_sweep: str = "none",
        exit_geometry: str = "sl_rrr",
        tp_move_pct: float | None = None,
        structural_sl_mode: str = "cap",
        min_tp_move_pct: float = 0.004,
        maintenance_margin_rate: float = 0.004,
        liquidation_fee_rate: float = 0.0005,
        liquidation_buffer_pct: float = 0.005,
        maintenance_margin_tier_schedule: str | None = None,
        instrument_precision_policy: str | None = None,
        intrabar_execution_timeframe: str | None = None,
        risk_free_rate_annual: float = 0.02,
        execution_start: str | pd.Timestamp | None = None,
        execution_end: str | pd.Timestamp | None = None,
        progress: bool = False,
        log_summary: bool = True,
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

        max_allowed_margin : float, default 1.0
            Maximum allowed margin for the strategy.
            If margin > max_allowed_margin, position is not opened.
            Isolated-margin leverage consistency is always enforced (ADR-0029).

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
        - If there are no trades, analyzer is still created but metrics will
          reflect absence of trades.
        - **Supports both long (signal=1) and short (signal=-1) positions**
        Note:
        -----
        Capital is shared across all trades of the instrument.
        This models real-world portfolio management scenarios.
        """
        if log_summary:
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
                ("Position TTL Bars", position_ttl_bars),
                ("Position TTL Minutes", position_ttl_minutes),
                ("Min Net Exposure", min_net_exposure),
                ("Max Allowed Leverage", max_allowed_leverage),
                ("Max Allowed Margin", max_allowed_margin),
                ("Risk Base Period", risk_base_period),
                ("Capital Sweep", capital_sweep),
                ("Instrument Precision", instrument_precision_policy or "continuous"),
                ("Intrabar Execution", intrabar_execution_timeframe or "bar-close"),
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
            position_ttl_minutes=position_ttl_minutes,
            min_net_exposure=min_net_exposure,
            max_allowed_leverage=max_allowed_leverage,
            max_allowed_margin=max_allowed_margin,
            risk_base_period=risk_base_period,
            max_daily_profit=max_daily_profit,
            max_daily_loss=max_daily_loss,
            trading_begin=trading_begin,
            trading_end=trading_end,
            capital_sweep=capital_sweep,
            exit_geometry=exit_geometry,
            tp_move_pct=tp_move_pct,
            structural_sl_mode=structural_sl_mode,
            min_tp_move_pct=min_tp_move_pct,
            maintenance_margin_rate=maintenance_margin_rate,
            liquidation_fee_rate=liquidation_fee_rate,
            liquidation_buffer_pct=liquidation_buffer_pct,
            maintenance_margin_tier_schedule=maintenance_margin_tier_schedule,
            instrument_precision_policy=instrument_precision_policy,
            intrabar_execution_timeframe=intrabar_execution_timeframe,
        )

        execution_context = execution_context_from_run_kwargs(
            exit_geometry=exit_geometry,
            tp_move_pct=tp_move_pct,
            structural_sl_mode=structural_sl_mode,
            min_tp_move_pct=min_tp_move_pct,
        )
        signaled_df = pd.DataFrame()
        entry_rejections_df = pd.DataFrame()
        try:
            signal_started_at = time.monotonic()
            if progress:
                self._logger.info("Generating strategy signals...")
            strategy_input: StrategyInput
            if isinstance(self.data, StrategyData):
                strategy_input = attach_execution_context(self.data.copy(), execution_context)
            else:
                strategy_input = attach_execution_context(self.df.copy(), execution_context)
            strategy_progress_started_at = time.monotonic()
            strategy_progress_supported = False
            strategy_owner = getattr(self.strategy, "__self__", None)
            set_progress_callback = getattr(strategy_owner, "set_progress_callback", None)
            strategy_progress_last_log_at = strategy_progress_started_at
            strategy_progress_last_done = -1

            def _strategy_progress(label: str, done: int, total: int) -> None:
                nonlocal strategy_progress_last_done, strategy_progress_last_log_at
                total = max(int(total), 0)
                done = max(0, min(int(done), total)) if total else max(0, int(done))
                now = time.monotonic()
                unchanged = done != 0 and done < total and done == strategy_progress_last_done
                too_soon = done != 0 and done < total and now - strategy_progress_last_log_at < 10.0
                if unchanged or too_soon:
                    return
                elapsed = time.monotonic() - strategy_progress_started_at
                rate = done / elapsed if elapsed > 0 else 0.0
                eta = (total - done) / rate if rate > 0 and total >= done else None
                self._logger.info(
                    "Generating strategy signals: %d/%d items current=%s elapsed=%s eta=%s",
                    done,
                    total,
                    label,
                    format_duration(elapsed),
                    format_duration(eta),
                )
                strategy_progress_last_log_at = now
                strategy_progress_last_done = done

            if progress and callable(set_progress_callback):
                set_progress_callback(_strategy_progress)
                strategy_progress_supported = True
            try:
                if progress and not strategy_progress_supported:
                    with HeartbeatLogger(self._logger, "Generating strategy signals"):
                        signaled_df = self.strategy(strategy_input)
                else:
                    signaled_df = self.strategy(strategy_input)
            finally:
                if strategy_progress_supported and callable(set_progress_callback):
                    set_progress_callback(None)
            if progress:
                self._logger.info(
                    "Strategy signals generated: rows=%d elapsed=%s",
                    len(signaled_df),
                    format_duration(time.monotonic() - signal_started_at),
                )
            sim_df = self.df
            execution_start_ts = _utc_timestamp(execution_start)
            execution_end_ts = _utc_timestamp(execution_end)
            if execution_start_ts is not None or execution_end_ts is not None:
                sim_df = _slice_execution_window(
                    sim_df,
                    start=execution_start_ts,
                    end=execution_end_ts,
                )
                signaled_df = _slice_execution_window(
                    signaled_df,
                    start=execution_start_ts,
                    end=execution_end_ts,
                )
                if sim_df.empty:
                    raise ValueError("execution window has no OHLCV candles after warmup trim")

            has_signal_events = "signal_events" in signaled_df.columns
            if "signal" not in signaled_df.columns and not has_signal_events:
                self._logger.error("🚨 Strategy did not generate 'signal' column.")
                trades_df = pd.DataFrame()
            elif "sl_price" not in signaled_df.columns and not has_signal_events:
                self._logger.error("🚨 Strategy did not generate 'sl_price' column.")
                trades_df = pd.DataFrame()
            else:
                if len(signaled_df) != len(sim_df) or not signaled_df.index.equals(sim_df.index):
                    raise ValueError(
                        "strategy signal frame index must exactly match simulator OHLCV index"
                    )
                intrabar_data: IntrabarExecutionData | None = None
                if intrabar_execution_timeframe is not None:
                    if not isinstance(self.data, StrategyData):
                        raise ValueError(
                            "minute execution requires StrategyData from crypt-parquet"
                        )
                    intrabar_data = self.data.execution
                progress_logger = (
                    ProgressLogger(
                        self._logger,
                        "Simulating trades",
                        max(len(signaled_df) - 1, 0),
                        "bars",
                    )
                    if progress
                    else None
                )
                trades_df = sim.run(
                    signaled_df,
                    intrabar_data=intrabar_data,
                    progress_callback=(
                        (lambda done: progress_logger.update(done))
                        if progress_logger is not None
                        else None
                    ),
                )
                entry_rejections_df = pd.DataFrame(sim.entry_rejections)
                if progress_logger is not None:
                    progress_logger.finish(max(len(signaled_df) - 1, 0))
                if trades_df.empty and log_summary:
                    self._logger.warning("🚫 No trades generated for the asset.")
                elif log_summary:
                    self._logger.info("  📊 Trades: %d", len(trades_df))

        except ValueError:
            raise
        except Exception:
            self._logger.exception("🚨 Error during backtest execution")
            trades_df = pd.DataFrame()

        analyzer = ResultsAnalyzer(
            trades_df,
            signal_df=signaled_df,
            entry_rejections_df=entry_rejections_df,
        )
        analyzer.generate(risk_free_rate_annual=risk_free_rate_annual)

        return analyzer
