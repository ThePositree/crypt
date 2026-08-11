"""Promoted routers exposed through the normal strategy contract."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import optuna
import pandas as pd

from backtester.data_contracts import StrategyData, StrategyInput
from backtester.regime_router import (
    RouterCandidate,
    RouterSearchConfig,
    evaluate_frozen_router_candidate,
)
from backtester.router_runtime import (
    ArchivedStrategySpec,
    build_archived_signal_frames,
    replay_selected_signals,
)
from backtester.strategy import BaseStrategy

logger = logging.getLogger(__name__)


class PromotedRouterStrategy(BaseStrategy):
    """Select one nested strategy using a frozen catalog router."""

    def __init__(self, params: dict[str, Any]) -> None:
        super().__init__(params)
        self._router_id = str(params["router_id"])
        self._fallback_strategy = str(params["fallback_strategy"])
        raw_labels_path = params.get("labels_path")
        if not raw_labels_path:
            raise ValueError("labels_path is required")
        self._labels_path = Path(str(raw_labels_path))
        raw_paths = params.get("strategy_paths", {})
        if not isinstance(raw_paths, dict) or not raw_paths:
            raise ValueError("strategy_paths must be a non-empty mapping")
        self._strategy_paths = {
            str(strategy_id): Path(str(path)) for strategy_id, path in raw_paths.items()
        }
        if self._fallback_strategy not in self._strategy_paths:
            raise ValueError("fallback_strategy must exist in strategy_paths")
        router = params.get("router", {})
        raw_validation_start = router.get("validation_start")
        if not raw_validation_start:
            raise ValueError("router.validation_start is required")
        self._validation_start = pd.Timestamp(str(raw_validation_start), tz="UTC")
        self._candidate = RouterCandidate(
            router_id=self._router_id,
            scoring_method=str(router["scoring_method"]),
            lookback_days=int(router["lookback_days"]),
            feature_set=str(router.get("feature_set", "pinescript")),
            knn_k=int(router.get("knn_k", 0)),
            state_subset=str(router.get("state_subset", "none")),
            state_match_mode=str(router.get("state_match_mode", "none")),
            state_similarity_threshold=float(router.get("state_similarity_threshold", 1.0)),
            state_weight_profile=str(router.get("state_weight_profile", "equal")),
            ewm_halflife_days=int(router.get("ewm_halflife_days", 0)),
            min_samples=int(router.get("min_samples", 10)),
            min_hold_days=int(router.get("min_hold_days", 0)),
            switch_margin_threshold=float(router.get("switch_margin_threshold", 0.0)),
        )
        self._min_available_strategies = int(
            params.get("min_available_strategies", len(self._strategy_paths))
        )
        self._candle_timeframe = str(params.get("candle_timeframe", "H1"))
        self._progress = bool(params.get("progress", True))

    def generate(self, data: StrategyInput) -> pd.DataFrame:
        """Generate signals from the currently selected nested strategy."""

        from backtester.cli_runner import (
            build_backtest_args,
            load_strategy_config,
        )

        primary = data.require_timeframe(self._candle_timeframe) if isinstance(data, StrategyData) else data
        labels = self._load_labels()
        selected = self._selection_series(labels, primary.index)
        selected_ids = set(selected.astype(str))
        unknown = selected_ids - self._strategy_paths.keys()
        if unknown:
            names = ", ".join(sorted(unknown))
            raise ValueError(f"Router selected unknown nested strategies: {names}")

        specs: list[ArchivedStrategySpec] = []
        for strategy_id in sorted(self._strategy_paths):
            path = self._strategy_paths[strategy_id]
            cfg = load_strategy_config(str(path), logger)
            if cfg is None:
                raise ValueError(f"Invalid nested strategy config: {path}")
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
            specs.append(
                ArchivedStrategySpec(
                    strategy_id=strategy_id,
                    name=cfg.name,
                    params=dict(cfg.params),
                    execution=args,
                )
            )

        logger.info("Promoted router shared feature/signal preparation starting")
        signal_frames = build_archived_signal_frames(data=data, specs=specs, ohlcv=primary)
        logger.info("Promoted router chronological replay starting")
        return replay_selected_signals(
            primary=primary,
            selected=selected,
            frames=signal_frames,
            specs={spec.strategy_id: spec for spec in specs},
            router_id=self._router_id,
            progress=self._progress,
        )

    def _load_labels(self) -> pd.DataFrame:
        if not self._labels_path.is_file():
            raise FileNotFoundError(
                "Promoted router rolling-label state is missing: "
                f"{self._labels_path}. Restore the persisted artifact; nested "
                "backtests are forbidden inside the strategy."
            )
        labels = pd.read_csv(self._labels_path)
        if labels.empty:
            raise ValueError(f"Promoted router rolling-label state is empty: {self._labels_path}")
        return labels

    def _selection_series(
        self,
        labels: pd.DataFrame,
        index: pd.DatetimeIndex,
    ) -> pd.Series:
        if labels.empty:
            return pd.Series(self._fallback_strategy, index=index, dtype="object")
        predictions = evaluate_frozen_router_candidate(
            labels,
            candidate=self._candidate,
            config=RouterSearchConfig(
                validation_start=self._validation_start.isoformat(),
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
