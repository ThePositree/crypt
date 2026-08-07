from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import optuna
import pandas as pd
from pandas.testing import assert_frame_equal

from backtester.data_contracts import StrategyData, StrategyInput
from backtester.router_runtime import ArchivedStrategySpec, build_archived_signal_frames
from backtester.strategy import BaseStrategy
from backtester.strategy_discovery.features import (
    DiscoveryDataset,
    build_discovery_dataset,
    build_donor_discovery_features,
)
from backtester.tp_policy import TpPolicyConfig

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class PortfolioFilterRule:
    feature: str
    op: str
    value: float | str | bool


class FilteredDonorPortfolioStrategy(BaseStrategy):
    """Release every donor signal that passes its entry-known filter."""

    _LIVE_TAIL_BARS = 512
    _LIVE_VALIDATION_BARS = 128

    def __init__(self, params: dict[str, Any]) -> None:
        super().__init__(params)
        raw_paths = params.get("strategy_paths", {})
        if not isinstance(raw_paths, dict) or not raw_paths:
            raise ValueError("strategy_paths must be a non-empty mapping")
        self._strategy_paths = {
            str(strategy_id): Path(str(path)) for strategy_id, path in raw_paths.items()
        }
        raw_filters = params.get("filters", {})
        if not isinstance(raw_filters, dict):
            raise ValueError("filters must be a mapping")
        self._filters = {
            str(strategy_id): self._parse_rules(raw_rules)
            for strategy_id, raw_rules in raw_filters.items()
        }
        raw_nested_backtest_args = params.get("nested_backtest_args", {})
        if not isinstance(raw_nested_backtest_args, dict):
            raise ValueError("nested_backtest_args must be a mapping when provided")
        self._nested_backtest_args = dict(raw_nested_backtest_args)
        raw_components = params.get("components", {})
        if not isinstance(raw_components, dict):
            raise ValueError("components must be a mapping when provided")
        unknown_components = set(raw_components) - {"distant_tp"}
        if unknown_components:
            raise ValueError(
                f"unsupported filtered donor portfolio components: {sorted(unknown_components)}"
            )
        # ``tp_policy`` remains a backward-compatible alias for early research
        # copies. The composable ``components.distant_tp`` mount is canonical.
        raw_tp_policy = raw_components.get("distant_tp", params.get("tp_policy", {}))
        if not isinstance(raw_tp_policy, dict):
            raise ValueError("components.distant_tp must be a mapping when provided")
        self._tp_policy = dict(raw_tp_policy)
        unknown = set(self._filters) - set(self._strategy_paths)
        if unknown:
            raise ValueError(f"filters reference unknown strategies: {sorted(unknown)}")
        self._progress = bool(params.get("progress", True))
        self._portfolio_id = str(params.get("portfolio_id", "filtered_donor_portfolio"))
        self._candle_timeframe = str(
            params.get("candle_timeframe") or self._infer_candle_timeframe()
        )
        self._progress_callback: Callable[[str, int, int], None] | None = None
        self._cached_specs: tuple[ArchivedStrategySpec, ...] | None = None
        self._live_cached_primary: pd.DataFrame | None = None
        self._live_cached_frames: dict[str, pd.DataFrame] | None = None

    def set_progress_callback(
        self,
        callback: Callable[[str, int, int], None] | None,
    ) -> None:
        self._progress_callback = callback

    def _infer_candle_timeframe(self) -> str:
        from backtester.cli_runner import load_strategy_config, strategy_config_candle_timeframe
        from backtester.data_contracts import timeframe_minutes

        fastest: str | None = None
        fastest_minutes: int | None = None
        for path in self._strategy_paths.values():
            cfg = load_strategy_config(str(path), logger)
            if cfg is None:
                continue
            timeframe = strategy_config_candle_timeframe(cfg)
            minutes = timeframe_minutes(timeframe)
            if fastest_minutes is None or minutes < fastest_minutes:
                fastest = timeframe
                fastest_minutes = minutes
        return fastest or "H1"

    def generate(self, data: StrategyInput) -> pd.DataFrame:
        primary = data.require_timeframe(self._candle_timeframe) if isinstance(data, StrategyData) else data
        total_events = len(primary)
        event_base = 3
        total_work = event_base + total_events
        self._report_progress("load donor specs", 0, total_work)
        specs = list(self._get_specs())
        logger.info("Filtered donor portfolio signal preparation starting")
        frames = self._controlled_frames(data=data, primary=primary, specs=specs)
        self._report_progress("donor signals", 1, total_work)
        frames = {
            strategy_id: _join_catalog_features(frame)
            for strategy_id, frame in frames.items()
        }
        self._report_progress("catalog features", 2, total_work)
        _validate_filter_features_available(frames, self._filters)

        output = primary.copy()
        output["signal"] = 0
        output["sl_price"] = 0.0
        output["signal_events"] = [[] for _ in range(len(output))]
        output["portfolio_id"] = self._portfolio_id

        self._report_progress("portfolio events", event_base, total_work)
        for offset, timestamp in enumerate(output.index, start=1):
            output.at[timestamp, "signal_events"] = self._events_at(
                timestamp=timestamp,
                specs=specs,
                frames=frames,
                primary=primary,
            )
            self._report_progress("portfolio events", event_base + offset, total_work)
        return output

    def _report_progress(self, label: str, done: int, total: int) -> None:
        if self._progress and self._progress_callback is not None:
            self._progress_callback(label, done, total)

    def generate_latest(self, data: StrategyInput) -> pd.DataFrame:
        """Build only the latest portfolio row with a validated donor-frame cache."""
        primary = data.require_timeframe(self._candle_timeframe) if isinstance(data, StrategyData) else data
        if primary.empty:
            return primary.copy()

        specs = list(self._get_specs())
        symbol = str(data.metadata.get("symbol", "")) if isinstance(data, StrategyData) else ""
        dataset = build_discovery_dataset(
            data=primary,
            window_label="filtered_donor_portfolio_live",
            symbol=symbol,
        )
        frames = self._updated_live_frames(
            data=data,
            primary=primary,
            dataset=dataset,
            specs=specs,
        )
        timestamp = primary.index[-1]
        frames = {
            strategy_id: _join_catalog_features(frame)
            for strategy_id, frame in frames.items()
        }
        _validate_filter_features_available(frames, self._filters)

        output = primary.loc[[timestamp]].copy()
        output["signal"] = 0
        output["sl_price"] = 0.0
        output["signal_events"] = pd.Series(
            [
                self._events_at(
                    timestamp=timestamp,
                    specs=specs,
                    frames=frames,
                    primary=primary,
                    allow_future_entry=True,
                )
            ],
            index=output.index,
            dtype="object",
        )
        output["portfolio_id"] = self._portfolio_id
        return output

    def _get_specs(self) -> tuple[ArchivedStrategySpec, ...]:
        from backtester.cli_runner import (
            build_backtest_args,
            load_strategy_config,
            strategy_config_candle_timeframe,
        )

        if self._cached_specs is not None:
            return self._cached_specs

        specs: list[ArchivedStrategySpec] = []
        for strategy_id in sorted(self._strategy_paths):
            cfg = load_strategy_config(str(self._strategy_paths[strategy_id]), logger)
            if cfg is None:
                path = self._strategy_paths[strategy_id]
                raise ValueError(f"Invalid nested strategy config: {path}")
            nested_defaults = {
                "capital": 10_000.0,
                "risk_percent": 1.0,
                "rrr": 2.0,
                "trail_activation_rrr": 0.0,
                "trail_distance_atr": 0.0,
                "maker_fee": 0.0002,
                "taker_fee": 0.0005,
                "ttl": 0,
                "max_positions": 0,
                "max_allowed_leverage": 25.0,
                "max_allowed_margin": 1.0,
                "risk_base_period": "monthly",
                "max_daily_profit": None,
                "max_daily_loss": None,
                "trading_begin": None,
                "trading_end": None,
                "exit_geometry": "sl_rrr",
                "tp_move_pct": None,
                "structural_sl_mode": "cap",
                "min_tp_move_pct": 0.004,
            }
            nested_defaults.update(self._nested_backtest_args)
            args = build_backtest_args(
                cfg,
                candle_timeframe=strategy_config_candle_timeframe(cfg),
                **nested_defaults,
            )
            specs.append(
                ArchivedStrategySpec(
                    strategy_id=strategy_id,
                    name=cfg.name,
                    params=dict(cfg.params),
                    execution=args,
                )
            )
        self._cached_specs = tuple(specs)
        return self._cached_specs

    def _controlled_frames(
        self,
        *,
        data: StrategyInput,
        primary: pd.DataFrame,
        specs: list[ArchivedStrategySpec],
        dataset: DiscoveryDataset | None = None,
    ) -> dict[str, pd.DataFrame]:
        frames = build_archived_signal_frames(
            data=data,
            specs=specs,
            ohlcv=primary,
            dataset=dataset,
        )
        return {
            spec.strategy_id: _apply_nested_replay_controls(
                frame=frames[spec.strategy_id],
                primary=primary,
                params=spec.params,
            )
            for spec in specs
        }

    def _updated_live_frames(
        self,
        *,
        data: StrategyInput,
        primary: pd.DataFrame,
        dataset: DiscoveryDataset,
        specs: list[ArchivedStrategySpec],
    ) -> dict[str, pd.DataFrame]:
        cached_primary = self._live_cached_primary
        cached_frames = self._live_cached_frames
        cache_valid = (
            cached_primary is not None
            and cached_frames is not None
            and len(primary) >= len(cached_primary)
            and primary.iloc[: len(cached_primary)].equals(cached_primary)
        )
        if not cache_valid:
            if cached_primary is not None:
                logger.warning("Live donor cache invalidated by revised or incompatible history")
            frames = self._controlled_frames(
                data=data,
                primary=primary,
                specs=specs,
                dataset=dataset,
            )
            self._store_live_cache(primary, frames)
            logger.info("Live donor cache cold-built through %s", primary.index[-1])
            return frames

        assert cached_primary is not None
        assert cached_frames is not None
        if len(primary) == len(cached_primary):
            logger.info("Live donor cache hit through %s", primary.index[-1])
            return cached_frames

        tail_start = max(0, len(cached_primary) - self._LIVE_TAIL_BARS)
        if tail_start == len(cached_primary):
            return self._cold_rebuild_live_cache(data, primary, dataset, specs)
        tail_index = primary.index[tail_start:]
        tail_data = _slice_strategy_input(data, tail_index)
        tail_dataset = DiscoveryDataset(
            window_label=dataset.window_label,
            symbol=dataset.symbol,
            ohlcv=dataset.ohlcv.loc[tail_index],
            features=dataset.features.loc[tail_index],
        )
        tail_frames = self._controlled_frames(
            data=tail_data,
            primary=primary.loc[tail_index],
            specs=specs,
            dataset=tail_dataset,
        )

        overlap_end = len(cached_primary)
        overlap_start = max(tail_start, overlap_end - self._LIVE_VALIDATION_BARS)
        overlap_index = primary.index[overlap_start:overlap_end]
        if overlap_index.empty:
            return self._cold_rebuild_live_cache(data, primary, dataset, specs)
        try:
            for spec in specs:
                assert_frame_equal(
                    cached_frames[spec.strategy_id].loc[overlap_index],
                    tail_frames[spec.strategy_id].loc[overlap_index],
                    check_exact=True,
                    check_dtype=True,
                    check_freq=False,
                )
        except AssertionError:
            logger.warning("Live donor cache overlap mismatch; rebuilding complete donor frames")
            return self._cold_rebuild_live_cache(data, primary, dataset, specs)

        cached_last = cached_primary.index[-1]
        frames = {
            spec.strategy_id: pd.concat(
                [
                    cached_frames[spec.strategy_id],
                    tail_frames[spec.strategy_id].loc[
                        tail_frames[spec.strategy_id].index > cached_last
                    ],
                ]
            )
            for spec in specs
        }
        self._store_live_cache(primary, frames)
        logger.info(
            "Live donor cache appended %d bar(s) through %s",
            len(primary) - len(cached_primary),
            primary.index[-1],
        )
        return frames

    def _cold_rebuild_live_cache(
        self,
        data: StrategyInput,
        primary: pd.DataFrame,
        dataset: DiscoveryDataset,
        specs: list[ArchivedStrategySpec],
    ) -> dict[str, pd.DataFrame]:
        frames = self._controlled_frames(
            data=data,
            primary=primary,
            specs=specs,
            dataset=dataset,
        )
        self._store_live_cache(primary, frames)
        return frames

    def _store_live_cache(
        self,
        primary: pd.DataFrame,
        frames: dict[str, pd.DataFrame],
    ) -> None:
        self._live_cached_primary = primary.copy()
        self._live_cached_frames = {
            strategy_id: frame.copy() for strategy_id, frame in frames.items()
        }

    def _events_at(
        self,
        *,
        timestamp: pd.Timestamp,
        specs: list[ArchivedStrategySpec],
        frames: dict[str, pd.DataFrame],
        primary: pd.DataFrame,
        allow_future_entry: bool = False,
    ) -> list[dict[str, Any]]:
        events: list[dict[str, Any]] = []
        for spec in specs:
            frame = frames[spec.strategy_id]
            donor_signal = _donor_signal_for_portfolio_emit(
                frame=frame,
                primary_index=primary.index,
                emit_timestamp=timestamp,
                allow_future_entry=allow_future_entry,
            )
            if donor_signal is None:
                continue
            donor_signal_time, row = donor_signal
            signal = int(row.get("signal", 0))
            if signal not in (1, -1):
                continue
            if not self._passes_filters(row, self._filters.get(spec.strategy_id, [])):
                continue
            policy = _tp_policy_for_strategy(self._tp_policy, spec.strategy_id)
            event = _event_from_signal_row(row, spec, tp_policy=policy)
            event.pop("entry_price", None)
            event["donor_signal_time"] = donor_signal_time.isoformat()
            event["tp_last_touch_bars"] = _last_tp_touch_bars(
                primary=primary,
                timestamp=timestamp,
                signal=signal,
                entry_price=_entry_reference_price(primary, timestamp),
                sl_price=float(row["sl_price"]),
                rrr=float(event["rrr"]),
            )
            events.append(event)
        return events

    @staticmethod
    def _parse_rules(raw_rules: Any) -> list[PortfolioFilterRule]:
        if raw_rules is None:
            return []
        if not isinstance(raw_rules, list):
            raise ValueError("each filter entry must be a list of rules")
        rules: list[PortfolioFilterRule] = []
        for raw in raw_rules:
            if not isinstance(raw, dict):
                raise ValueError("filter rules must be dictionaries")
            rules.append(
                PortfolioFilterRule(
                    feature=str(raw["feature"]),
                    op=str(raw["op"]),
                    value=raw["value"],
                )
            )
        return rules

    @staticmethod
    def _passes_filters(row: pd.Series, rules: list[PortfolioFilterRule]) -> bool:
        for rule in rules:
            if rule.feature not in row.index:
                return False
            value = row[rule.feature]
            if pd.isna(value):
                return False
            if not _compare_filter_value(value, rule.op, rule.value):
                return False
        return True

    def suggest_params(self, trial: optuna.Trial) -> dict[str, Any]:  # noqa: ARG002
        return {}


def _catalog_features(primary: pd.DataFrame) -> pd.DataFrame:
    features = build_donor_discovery_features(primary=primary, h4=None, d1=None)
    return _catalog_features_from_primary_features(features)


def _join_catalog_features(frame: pd.DataFrame) -> pd.DataFrame:
    if not {"open", "high", "low", "close", "volume"}.issubset(frame.columns):
        return frame
    return frame.join(_catalog_features(frame), how="left")


def _catalog_features_from_primary_features(features: pd.DataFrame) -> pd.DataFrame:
    closed_features = features.shift(1)
    catalog = pd.DataFrame(index=features.index)
    catalog["entry_hour"] = catalog.index.hour
    catalog["entry_dayofweek"] = catalog.index.dayofweek
    catalog["catalog_atr_pct"] = closed_features["atr_pct"]
    catalog["catalog_volatility_rank"] = closed_features["volatility_rank"]
    catalog["catalog_trend_strength_atr"] = closed_features["trend_strength_atr"]
    catalog["catalog_rsi14"] = closed_features["rsi14"]
    catalog["catalog_bb_width_pct"] = closed_features["bb_width_pct"]
    catalog["catalog_body_to_range"] = closed_features["body_to_range"]
    catalog["catalog_bar_range_atr"] = closed_features["bar_range_atr"]
    catalog["catalog_roc10"] = closed_features["roc10"]
    catalog["catalog_volume_ratio_20"] = closed_features["volume_ratio_20"]
    catalog["catalog_ema_stack_long"] = closed_features["ema_stack_long"].astype("boolean")
    catalog["catalog_ema_stack_short"] = closed_features["ema_stack_short"].astype("boolean")
    catalog["catalog_bb_squeeze"] = (closed_features["bb_width_rank_20"] <= 0.25).astype("boolean")
    catalog["catalog_bb_wide"] = (closed_features["bb_width_rank_20"] >= 0.75).astype("boolean")
    catalog["catalog_volume_above_median"] = (closed_features["volume_ratio_20"] >= 1.0).astype(
        "boolean"
    )
    catalog["catalog_session_london"] = closed_features["hour_utc"].between(7, 16).astype("boolean")
    catalog["catalog_session_ny"] = closed_features["hour_utc"].between(13, 21).astype("boolean")
    return catalog


def _slice_strategy_input(
    data: StrategyInput,
    index: pd.Index,
) -> StrategyInput:
    if not isinstance(data, StrategyData):
        return data.loc[index]
    candles = {
        key: (frame.loc[frame.index.intersection(index)] if key == "H1" else frame)
        for key, frame in data.candles_by_timeframe.items()
    }
    return StrategyData(
        candles_by_timeframe=candles,
        extras=data.extras,
        metadata=data.metadata,
        execution=data.execution,
    )


def _apply_nested_replay_controls(
    *,
    frame: pd.DataFrame,
    primary: pd.DataFrame,
    params: dict[str, Any],
) -> pd.DataFrame:
    output = frame.copy()
    allowed_signal = params.get("allowed_signal")
    if allowed_signal is not None:
        allowed = int(allowed_signal)
        if allowed not in (-1, 1):
            raise ValueError("allowed_signal must be -1, 1, or omitted")
        rejected = output["signal"] != allowed
        output.loc[rejected, "signal"] = 0
        output.loc[rejected, "sl_price"] = 0.0

    entry_skip_rules = params.get("entry_skip_rules") or []
    if entry_skip_rules:
        _apply_nested_entry_skip_rules(output=output, primary=primary, rules=entry_skip_rules)
    return output


def _apply_nested_entry_skip_rules(
    *,
    output: pd.DataFrame,
    primary: pd.DataFrame,
    rules: list[dict[str, Any]],
) -> None:
    entry_open = primary["open"].shift(-1)
    entry_times = pd.Series(primary.index, index=primary.index).shift(-1)
    feature_values = {
        "entry_dayofweek": entry_times.dt.dayofweek.astype("float64"),
        "stop_distance_pct": (entry_open - output["sl_price"]).abs() / entry_open,
    }

    skip_mask = pd.Series(False, index=output.index)
    for rule in rules:
        conditions = rule.get("conditions")
        if not isinstance(conditions, list) or not conditions:
            raise ValueError("entry_skip_rules items must contain a non-empty conditions list")
        rule_mask = output["signal"] != 0
        for condition in conditions:
            feature = str(condition.get("feature"))
            op = str(condition.get("op"))
            if feature not in feature_values:
                raise ValueError(f"unsupported entry skip feature: {feature}")
            if "value" not in condition:
                raise ValueError("entry skip condition must contain value")
            rule_mask &= _compare_entry_skip_value(
                feature_values[feature],
                op,
                float(condition["value"]),
            )
        skip_mask |= rule_mask.fillna(False)

    output.loc[skip_mask, "signal"] = 0
    output.loc[skip_mask, "sl_price"] = 0.0


def _compare_entry_skip_value(values: pd.Series, op: str, threshold: float) -> pd.Series:
    if op == "<":
        return values < threshold
    if op == "<=":
        return values <= threshold
    if op == ">":
        return values > threshold
    if op == ">=":
        return values >= threshold
    if op == "==":
        return values == threshold
    if op == "!=":
        return values != threshold
    raise ValueError(f"unsupported entry skip op: {op}")


def _validate_filter_features_available(
    frames: dict[str, pd.DataFrame],
    filters: dict[str, list[PortfolioFilterRule]],
) -> None:
    missing: dict[str, list[str]] = {}
    for strategy_id, rules in filters.items():
        frame = frames.get(strategy_id)
        if frame is None:
            missing[strategy_id] = [rule.feature for rule in rules]
            continue
        absent = sorted({rule.feature for rule in rules if rule.feature not in frame.columns})
        if absent:
            missing[strategy_id] = absent
    if missing:
        details = "; ".join(
            f"{strategy_id}: {', '.join(features)}"
            for strategy_id, features in sorted(missing.items())
        )
        raise ValueError(
            f"Filtered donor portfolio config references unavailable filter features: {details}"
        )


def _donor_signal_for_portfolio_emit(
    *,
    frame: pd.DataFrame,
    primary_index: pd.Index,
    emit_timestamp: pd.Timestamp,
    allow_future_entry: bool = False,
) -> tuple[pd.Timestamp, pd.Series] | None:
    """Return the donor signal row whose standalone next-bar entry matches this emit bar."""

    try:
        emit_pos = primary_index.get_loc(emit_timestamp)
    except KeyError:
        return None
    if isinstance(emit_pos, slice):
        return None
    if emit_pos + 1 < len(primary_index):
        intended_entry_time = pd.Timestamp(primary_index[emit_pos + 1])
    elif allow_future_entry:
        primary_step = _infer_index_step(primary_index)
        if primary_step is None:
            return None
        intended_entry_time = pd.Timestamp(emit_timestamp) + primary_step
    else:
        return None
    try:
        donor_entry_pos = frame.index.get_loc(intended_entry_time)
    except KeyError:
        if not allow_future_entry:
            return None
        donor_step = _infer_index_step(frame.index)
        if donor_step is None:
            return None
        donor_signal_pos = int(frame.index.searchsorted(intended_entry_time, side="left")) - 1
        if donor_signal_pos < 0:
            return None
        donor_signal_time = pd.Timestamp(frame.index[donor_signal_pos])
        if donor_signal_time + donor_step != intended_entry_time:
            return None
        return donor_signal_time, frame.iloc[donor_signal_pos]
    if isinstance(donor_entry_pos, slice) or donor_entry_pos <= 0:
        return None
    donor_signal_pos = int(donor_entry_pos) - 1
    donor_signal_time = pd.Timestamp(frame.index[donor_signal_pos])
    return donor_signal_time, frame.iloc[donor_signal_pos]


def _infer_index_step(index: pd.Index) -> pd.Timedelta | None:
    if len(index) < 2:
        return None
    return pd.Timestamp(index[-1]) - pd.Timestamp(index[-2])


def _event_from_signal_row(
    row: pd.Series,
    spec: ArchivedStrategySpec,
    *,
    tp_policy: TpPolicyConfig | None = None,
) -> dict[str, Any]:
    event: dict[str, Any] = {
        "signal": int(row["signal"]),
        "sl_price": float(row["sl_price"]),
        "selected_strategy": spec.strategy_id,
        "position_group": spec.strategy_id,
        "drain_on_group_change": False,
        "risk_percent": float(getattr(spec.execution, "risk_percent", 1.0)),
        "rrr": float(getattr(spec.execution, "rrr", 2.0)),
        "position_ttl_bars": int(getattr(spec.execution, "ttl", 0)),
        "position_ttl_minutes": int(getattr(spec.execution, "ttl_minutes", 0)),
        "trail_activation_rrr": float(getattr(spec.execution, "trail_activation_rrr", 0.0)),
        "trail_distance_atr": float(getattr(spec.execution, "trail_distance_atr", 0.0)),
        "exit_geometry": str(getattr(spec.execution, "exit_geometry", "sl_rrr")),
        "tp_move_pct": getattr(spec.execution, "tp_move_pct", None),
        "structural_sl_mode": str(getattr(spec.execution, "structural_sl_mode", "cap")),
        "min_tp_move_pct": float(getattr(spec.execution, "min_tp_move_pct", 0.004)),
    }
    if tp_policy is not None:
        event.update(tp_policy.as_event_fields())
    if "entry_price" in row.index and not pd.isna(row["entry_price"]):
        event["entry_price"] = float(row["entry_price"])
    for key, value in row.items():
        if key in event or key in {"signal", "sl_price", "signal_events"}:
            continue
        if pd.isna(value):
            continue
        event[key] = value.item() if hasattr(value, "item") else value
    return event


def _tp_policy_for_strategy(raw: dict[str, Any], strategy_id: str) -> TpPolicyConfig:
    """Resolve a portfolio default and an optional donor-specific override."""

    default = {key: value for key, value in raw.items() if key != "strategies"}
    overrides = raw.get("strategies", {})
    if isinstance(overrides, dict) and isinstance(overrides.get(strategy_id), dict):
        default.update(overrides[strategy_id])
    return TpPolicyConfig.from_mapping(default)


def _entry_reference_price(primary: pd.DataFrame, timestamp: pd.Timestamp) -> float:
    """Use next H1 open in replay, signal close for the live tail."""

    try:
        position = primary.index.get_loc(timestamp)
        if not isinstance(position, slice) and position + 1 < len(primary):
            return float(primary.iloc[position + 1]["open"])
    except (KeyError, TypeError, ValueError):
        pass
    return float(primary.loc[timestamp, "close"])


def _last_tp_touch_bars(
    *,
    primary: pd.DataFrame,
    timestamp: pd.Timestamp,
    signal: int,
    entry_price: float,
    sl_price: float,
    rrr: float,
) -> int | None:
    """Return H1 bars since the last direction-aware touch before entry."""

    if entry_price <= 0 or sl_price <= 0 or rrr <= 0:
        return None
    target = entry_price + signal * abs(entry_price - sl_price) * rrr
    history = primary.loc[:timestamp]
    if history.empty:
        return None
    touched = history["high"] >= target if signal == 1 else history["low"] <= target
    if not touched.any():
        return None
    last_touch = history.index[touched][-1]
    touch_pos = int(history.index.get_loc(last_touch))
    return max(len(history) - 1 - touch_pos, 0)


def _compare_filter_value(value: Any, op: str, expected: float | str | bool) -> bool:
    if op in {"<=", ">="}:
        numeric = float(value)
        threshold = float(expected)
        return numeric <= threshold if op == "<=" else numeric >= threshold
    left = str(value)
    right = str(expected)
    if op == "==":
        return left == right
    if op == "!=":
        return left != right
    raise ValueError(f"Unsupported filter op: {op}")
