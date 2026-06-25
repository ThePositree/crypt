"""Promoted routers exposed through the normal strategy contract."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import optuna
import pandas as pd

from backtester.data_contracts import StrategyData, StrategyInput
from backtester.regime_labels import build_rolling_label_dataset_from_trades
from backtester.regime_router import (
    RouterCandidate,
    RouterSearchConfig,
    evaluate_frozen_router_candidate,
)
from backtester.strategy import BaseStrategy

logger = logging.getLogger(__name__)


class PromotedRouterStrategy(BaseStrategy):
    """Select one nested strategy using a frozen catalog router."""

    def __init__(self, params: dict[str, Any]) -> None:
        super().__init__(params)
        self._router_id = str(params["router_id"])
        self._fallback_strategy = str(params["fallback_strategy"])
        raw_paths = params.get("strategy_paths", {})
        if not isinstance(raw_paths, dict) or not raw_paths:
            raise ValueError("strategy_paths must be a non-empty mapping")
        self._strategy_paths = {
            str(strategy_id): Path(str(path))
            for strategy_id, path in raw_paths.items()
        }
        if self._fallback_strategy not in self._strategy_paths:
            raise ValueError("fallback_strategy must exist in strategy_paths")
        router = params.get("router", {})
        self._candidate = RouterCandidate(
            router_id=self._router_id,
            scoring_method=str(router["scoring_method"]),
            lookback_days=int(router["lookback_days"]),
            feature_set=str(router.get("feature_set", "pinescript")),
            knn_k=int(router.get("knn_k", 0)),
            state_subset=str(router.get("state_subset", "none")),
            state_match_mode=str(router.get("state_match_mode", "none")),
            state_similarity_threshold=float(
                router.get("state_similarity_threshold", 1.0)
            ),
            state_weight_profile=str(router.get("state_weight_profile", "equal")),
            ewm_halflife_days=int(router.get("ewm_halflife_days", 0)),
            min_samples=int(router.get("min_samples", 10)),
            min_hold_days=int(router.get("min_hold_days", 0)),
            switch_margin_threshold=float(
                router.get("switch_margin_threshold", 0.0)
            ),
        )
        self._horizon_days = int(params.get("horizon_days", 30))
        self._min_history_days = int(params.get("min_history_days", 90))
        self._min_available_strategies = int(
            params.get("min_available_strategies", len(self._strategy_paths))
        )

    def generate(self, data: StrategyInput) -> pd.DataFrame:
        """Generate signals from the currently selected nested strategy."""

        from backtester.cli_runner import (
            build_backtest_args,
            build_strategy_instance,
            load_strategy_config,
            run_backtest,
        )

        primary = data.primary if isinstance(data, StrategyData) else data
        donor_trades: dict[str, pd.DataFrame] = {}
        signal_frames: dict[str, pd.DataFrame] = {}
        execution: dict[str, Any] = {}

        for strategy_id, path in self._strategy_paths.items():
            logger.info("Promoted router donor starting: %s", strategy_id)
            cfg = load_strategy_config(str(path), logger)
            if cfg is None:
                raise ValueError(f"Invalid nested strategy config: {path}")
            strategy = build_strategy_instance(cfg.name, cfg.params, logger=logger)
            if strategy is None:
                raise ValueError(f"Could not build nested strategy: {path}")
            args = build_backtest_args(
                cfg,
                capital=10_000.0,
                risk_percent=1.0,
                rrr=2.0,
                trail_activation_rrr=0.0,
                trail_distance_atr=0.0,
                maker_fee=0.0002,
                taker_fee=0.0005,
                ttl=0,
                max_positions=0,
                max_allowed_leverage=25.0,
                max_allowed_margin=1.0,
                risk_base_period="monthly",
                max_daily_profit=None,
                max_daily_loss=None,
                trading_begin=None,
                trading_end=None,
                exit_geometry="sl_rrr",
                tp_move_pct=None,
                structural_sl_mode="cap",
                min_tp_move_pct=0.004,
            )
            donor = run_backtest(df=data, strategy=strategy, args=args)
            donor_trades[strategy_id] = donor.trades
            signal_frames[strategy_id] = donor.signals.reindex(primary.index)
            execution[strategy_id] = args
            logger.info(
                "Promoted router donor complete: %s trades=%d",
                strategy_id,
                len(donor.trades),
            )

        labels = build_rolling_label_dataset_from_trades(
            trades_by_strategy=donor_trades,
            ohlcv=primary,
            step="day",
            horizon_days=self._horizon_days,
            min_history_days=self._min_history_days,
        )
        selected = self._selection_series(labels, primary.index)
        output = primary.copy()
        output["signal"] = 0
        output["sl_price"] = 0.0
        output["risk_percent"] = 1.0
        output["rrr"] = 2.0
        output["position_ttl_bars"] = 0
        output["trail_activation_rrr"] = 0.0
        output["trail_distance_atr"] = 0.0
        output["exit_geometry"] = "sl_rrr"
        output["tp_move_pct"] = float("nan")
        output["structural_sl_mode"] = "cap"
        output["min_tp_move_pct"] = 0.004
        output["position_group"] = selected
        output["drain_on_group_change"] = True
        output["router_id"] = self._router_id
        output["selected_strategy"] = selected

        for strategy_id, frame in signal_frames.items():
            mask = selected == strategy_id
            if not mask.any():
                continue
            args = execution[strategy_id]
            for column in ("signal", "sl_price", "entry_price"):
                if column in frame.columns:
                    output.loc[mask, column] = frame.loc[mask, column]
            output.loc[mask, "risk_percent"] = args.risk_percent
            output.loc[mask, "rrr"] = args.rrr
            output.loc[mask, "position_ttl_bars"] = args.ttl
            output.loc[mask, "trail_activation_rrr"] = args.trail_activation_rrr
            output.loc[mask, "trail_distance_atr"] = args.trail_distance_atr
            output.loc[mask, "exit_geometry"] = args.exit_geometry
            output.loc[mask, "tp_move_pct"] = (
                args.tp_move_pct if args.tp_move_pct is not None else float("nan")
            )
            output.loc[mask, "structural_sl_mode"] = args.structural_sl_mode
            output.loc[mask, "min_tp_move_pct"] = args.min_tp_move_pct
        return output

    def _selection_series(
        self,
        labels: pd.DataFrame,
        index: pd.DatetimeIndex,
    ) -> pd.Series:
        if labels.empty:
            return pd.Series(self._fallback_strategy, index=index, dtype="object")
        first_asof = pd.to_datetime(labels["asof"], utc=True).min()
        predictions = evaluate_frozen_router_candidate(
            labels,
            candidate=self._candidate,
            config=RouterSearchConfig(
                validation_start=first_asof.isoformat(),
                min_available_strategies=self._min_available_strategies,
                catalog_version="v2",
                max_configs=1,
            ),
        )
        if predictions.empty:
            return pd.Series(self._fallback_strategy, index=index, dtype="object")
        choices = predictions[["asof", "selected_strategy"]].copy()
        choices["asof"] = pd.to_datetime(choices["asof"], utc=True)
        target = pd.DataFrame({"timestamp": pd.to_datetime(index, utc=True)})
        merged = pd.merge_asof(
            target.sort_values("timestamp"),
            choices.sort_values("asof"),
            left_on="timestamp",
            right_on="asof",
            direction="backward",
        )
        values = merged["selected_strategy"].fillna(self._fallback_strategy).to_numpy()
        return pd.Series(values, index=index, dtype="object")

    def suggest_params(self, trial: optuna.Trial) -> dict[str, Any]:  # noqa: ARG002
        """Promoted router parameters are frozen."""

        return {}
