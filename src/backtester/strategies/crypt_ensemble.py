from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Literal, cast

import numpy as np
import optuna
import pandas as pd
from tqdm import tqdm

from backtester.data_contracts import StrategyData, StrategyInput
from backtester.execution_context import (
    EXECUTION_CONTEXT_METADATA_KEY,
    StrategyExecutionContext,
    read_execution_context,
)
from backtester.strategy import BaseStrategy
from crypt.aggregator.ensemble import aggregate
from crypt.aggregator.weights import SCORING_ENGINES, WeightsConfig
from crypt.data.context import _df_to_ls_ratio, _df_to_oi, _df_to_taker_volume
from crypt.engines.derivatives import DerivativesEngine
from crypt.engines.meanrev import MeanRevEngine
from crypt.engines.regime import RegimeEngine
from crypt.engines.smc_liquidity import SMCLiquidityEngine
from crypt.engines.smc_order_blocks import SMCOrderBlocksEngine
from crypt.engines.smc_structure import SMCStructureEngine
from crypt.engines.trend import TrendEngine
from crypt.engines.volatility import VolatilityEngine
from crypt.models import (
    EvaluationContext,
    Regime,
    Signal,
    Timeframe,
    Verdict,
    VolRegime,
)
from crypt.structure.smc import (
    BEARISH,
    BULLISH,
    SMCOrderBlock,
    SMCPivot,
    SMCState,
    analyse_smc_cached,
)

_TIMEFRAME_CLOSE_DELTA = {
    Timeframe.M15: timedelta(minutes=15),
    Timeframe.H1: timedelta(hours=1),
    Timeframe.H4: timedelta(hours=4),
    Timeframe.D1: timedelta(days=1),
}
_CANDLE_LIMIT = 250
_OI_LIMIT = 200
_LS_LIMIT = 100
_TAKER_LIMIT = 100
_DEFAULT_SL_ATR_MULT = 2.0
_DEFAULT_SL_ATR_BUFFER_MULT = 0.10
_DEFAULT_ALLOW_ATR_SL_FALLBACK = False
_DEFAULT_MIN_CONFIDENCE: int | None = None
_DEFAULT_MAX_SL_DISTANCE_ATR = 8.0
_DEFAULT_OPTIMIZED_SETUP_SNAPSHOTS = True
_DEFAULT_MAX_TRIGGER_AGE_BARS = 3
_H4 = timedelta(hours=4)
_MAX_SWEEP_AGE_BARS = 3

_StopAnchorType = Literal["order_block", "liquidity_sweep", "pivot", "atr_fallback", "none"]
_STOP_ANCHOR_TYPES = frozenset({"order_block", "liquidity_sweep", "pivot", "atr_fallback", "none"})
_TriggerRule = Literal[
    "h1_sweep_reversal",
    "h1_structure_break",
    "h1_order_block_retest",
    "h1_candle_confirm",
    "h1_momentum_burst",
    "h1_nr7_breakout",
]
_H1_STRUCTURAL_TRIGGER_RULES: tuple[_TriggerRule, ...] = (
    "h1_sweep_reversal",
    "h1_structure_break",
    "h1_order_block_retest",
)
_TRIGGER_RULES = frozenset(
    (*_H1_STRUCTURAL_TRIGGER_RULES, "h1_candle_confirm", "h1_momentum_burst", "h1_nr7_breakout")
)
_DISCOVERY_CONTEXT_INCOMPLETE = frozenset({"missing", "neutral"})
_SETUP_SOURCES = frozenset({"mtf", "h1_raw"})


@dataclass(frozen=True)
class TimeframeRoleConfig:
    context: tuple[Timeframe, ...]
    setup: tuple[Timeframe, ...]
    trigger: Timeframe
    execution: Timeframe


@dataclass(frozen=True)
class _MTFDecision:
    verdict: Verdict
    signal_override: int | None
    trigger_type: str
    context_bias: str
    setup_direction: str
    rationale_suffix: str | None = None


@dataclass(frozen=True)
class _StopPlan:
    signal: int
    sl_price: float
    anchor_type: _StopAnchorType
    anchor_level: float | None
    anchor_known_at: datetime | None
    distance_atr: float | None
    rationale_suffix: str | None = None


@dataclass(frozen=True)
class _SignalFilterConfig:
    allowed_sides: frozenset[str] | None
    allowed_sl_anchor_types: frozenset[str] | None
    blocked_sl_anchor_types: frozenset[str]
    max_anchor_age_hours: float | None
    min_signal_sl_distance_atr: float | None
    max_signal_sl_distance_atr: float | None
    block_context_reversal: bool
    block_d1_h4_context_reversal: bool = False
    require_h4_context_aligned: bool = False
    min_trend_strength_atr: float | None = None
    min_volume_median_ratio: float | None = None
    max_bb_width_pct: float | None = None


@dataclass(frozen=True)
class _DiscoveryBarFeatures:
    trend_strength_atr: float | None
    volume: float | None
    volume_median20: float | None
    d1_context: str
    h4_context: str
    bb_width_pct: float | None = None


class CryptEnsembleStrategy(BaseStrategy):
    """Donor adapter that runs the existing crypt ensemble as one strategy."""

    def __init__(self, params: dict[str, Any]):
        super().__init__(params)
        self.sl_atr_mult = float(params.get("sl_atr_mult", _DEFAULT_SL_ATR_MULT))
        self.sl_atr_buffer_mult = float(
            params.get("sl_atr_buffer_mult", _DEFAULT_SL_ATR_BUFFER_MULT)
        )
        self.allow_atr_sl_fallback = bool(
            params.get("allow_atr_sl_fallback", _DEFAULT_ALLOW_ATR_SL_FALLBACK)
        )
        self.min_confidence = _optional_int(params.get("min_confidence", _DEFAULT_MIN_CONFIDENCE))
        self.max_sl_distance_atr = float(
            params.get("max_sl_distance_atr", _DEFAULT_MAX_SL_DISTANCE_ATR)
        )
        self.timeframes = _timeframe_role_config(params.get("timeframes"))
        self.progress = bool(params.get("progress", True))
        self.optimized_windows = bool(params.get("optimized_windows", False))
        self.optimized_setup_snapshots = bool(
            params.get("optimized_setup_snapshots", _DEFAULT_OPTIMIZED_SETUP_SNAPSHOTS)
        )
        self.trigger_rules = _trigger_rules_config(params.get("trigger_rules"), self.timeframes)
        self.setup_source = _setup_source_config(params.get("setup_source"))
        self.max_trigger_age_bars = _positive_int(
            params.get("max_trigger_age_bars", _DEFAULT_MAX_TRIGGER_AGE_BARS),
            "max_trigger_age_bars",
        )
        self.signal_filters = _signal_filter_config(params)
        self.weights = WeightsConfig.load(_weights_path(params.get("weights_path")))
        self._trend = TrendEngine()
        self._meanrev = MeanRevEngine()
        self._derivatives = DerivativesEngine()
        self._smc_structure = SMCStructureEngine()
        self._smc_order_blocks = SMCOrderBlocksEngine()
        self._smc_liquidity = SMCLiquidityEngine()
        self._volatility = VolatilityEngine()
        self._regime = RegimeEngine()

    def generate(self, data: StrategyInput) -> pd.DataFrame:
        strategy_data = _coerce_strategy_data(data)
        execution_context = read_execution_context(data)
        primary = strategy_data.primary.sort_index().copy()
        out = primary.copy()
        tick_index = _tick_index_from_open_index(primary.index, self.timeframes.execution)
        out.index = tick_index
        out.index.name = "tick_time"

        crypt_candles = {
            tf: _to_crypt_candles(_candle_frame(strategy_data, tf))
            for tf in (Timeframe.H4, Timeframe.H1, Timeframe.D1, Timeframe.M15)
        }
        if self.timeframes.execution == Timeframe.H4 and crypt_candles[Timeframe.H4].empty:
            crypt_candles[Timeframe.H4] = _to_crypt_candles(primary)
        extras = strategy_data.extras
        symbol = str(strategy_data.metadata.get("symbol", "UNKNOWN"))
        atr = _atr14_from_donor_frame(primary).reindex(primary.index)
        discovery_features = (
            _donor_discovery_features(
                primary=primary,
                h4=_candle_frame(strategy_data, Timeframe.H4),
                d1=_candle_frame(strategy_data, Timeframe.D1),
            )
            if _uses_discovery_features(self.signal_filters)
            else None
        )
        window_cache = (
            _ContextWindowCache(candles=crypt_candles, extras=extras)
            if self.optimized_windows
            else None
        )

        rows: list[dict[str, object]] = []
        setup_snapshot_cache: dict[tuple[str, datetime, datetime | None], Verdict] = {}
        bars = zip(primary.index, tick_index, strict=True)
        for open_time, tick_time in tqdm(
            bars,
            total=len(primary),
            desc="crypt_ensemble",
            unit="bar",
            disable=not self.progress,
        ):
            try:
                tick_dt = tick_time.to_pydatetime()
                setup_snapshot_time: datetime | None = tick_dt
                if window_cache is None:
                    ctx = _build_context(
                        symbol=symbol,
                        tick_time=tick_dt,
                        candles=crypt_candles,
                        extras=extras,
                    )
                else:
                    ctx = window_cache.build_context(symbol=symbol, tick_time=tick_dt)
                if self._use_setup_snapshots():
                    setup_time = _latest_closed_time(
                        crypt_candles[Timeframe.H4],
                        timeframe=Timeframe.H4,
                        tick_time=tick_dt,
                    )
                    setup_snapshot_time = setup_time or tick_dt
                    setup_ctx = ctx
                    if setup_time is not None:
                        setup_ctx = (
                            _build_context(
                                symbol=symbol,
                                tick_time=setup_time,
                                candles=crypt_candles,
                                extras=extras,
                            )
                            if window_cache is None
                            else window_cache.build_context(symbol=symbol, tick_time=setup_time)
                        )
                    setup_key = (
                        symbol,
                        setup_time or tick_dt,
                        _latest_closed_time(
                            crypt_candles[Timeframe.D1],
                            timeframe=Timeframe.D1,
                            tick_time=setup_time or tick_dt,
                        ),
                    )
                    verdict = setup_snapshot_cache.get(setup_key)
                    if verdict is None:
                        verdict = self._evaluate_context(setup_ctx)
                        setup_snapshot_cache[setup_key] = verdict
                    mtf = self._mtf_decision_from_verdict(
                        verdict, ctx, setup_ctx, primary.loc[open_time]
                    )
                else:
                    mtf = self._mtf_decision(ctx, primary.loc[open_time])
                signal = _signal_from_verdict(
                    mtf.verdict,
                    signal_override=mtf.signal_override,
                    min_confidence=self.min_confidence,
                )
                entry = float(primary.loc[open_time, "close"])
                atr_value = float(atr.loc[open_time])
                if _skip_structural_entry_gate(execution_context) and signal != 0:
                    stop = _tp_pct_placeholder_stop(
                        signal=signal,
                        entry=entry,
                        atr=atr_value,
                    )
                    sl_source_tf = self.timeframes.execution
                else:
                    stop, sl_source_tf = _select_structural_stop(
                        ctx=ctx,
                        signal=signal,
                        price_row=primary.loc[open_time],
                        atr=atr.loc[open_time],
                        sl_atr_mult=self.sl_atr_mult,
                        sl_atr_buffer_mult=self.sl_atr_buffer_mult,
                        max_sl_distance_atr=self.max_sl_distance_atr,
                        allow_atr_sl_fallback=self.allow_atr_sl_fallback,
                        execution_tf=self.timeframes.execution,
                    )
                discovery_bar = (
                    _discovery_bar_features(
                        discovery_features,
                        open_time,
                        volume=float(primary.loc[open_time, "volume"]),
                    )
                    if discovery_features is not None
                    else None
                )
                filtered_stop, filter_reason = _apply_signal_filters(
                    stop=stop,
                    filters=self.signal_filters,
                    trigger_known_at=tick_dt,
                    context_bias=mtf.context_bias,
                    setup_direction=mtf.setup_direction,
                    discovery=discovery_bar,
                )
                rows.append(
                    _row_from_verdict(
                        mtf.verdict,
                        filtered_stop,
                        rationale_suffix=mtf.rationale_suffix,
                        context_tf=",".join(tf.value for tf in self.timeframes.context),
                        setup_tf=",".join(tf.value for tf in self.timeframes.setup),
                        trigger_tf=self.timeframes.trigger.value,
                        context_bias=mtf.context_bias,
                        setup_direction=mtf.setup_direction,
                        trigger_type=mtf.trigger_type,
                        trigger_known_at=tick_time.to_pydatetime(),
                        setup_snapshot_time=setup_snapshot_time,
                        sl_source_tf=sl_source_tf.value,
                        signal_filter_reason=filter_reason,
                    )
                )
            except Exception as exc:
                rows.append(_neutral_row(f"crypt_ensemble error: {exc}", primary.loc[open_time]))

        signal_df = pd.DataFrame(rows, index=tick_index)
        for col in signal_df.columns:
            out.loc[:, col] = signal_df[col].to_numpy()
        return out

    def _evaluate_context(self, ctx: EvaluationContext) -> Verdict:
        vol_signal: Signal = self._volatility.evaluate(ctx)
        vol_regime: VolRegime = str(vol_signal.meta.get("vol_regime", "normal"))  # type: ignore[assignment]
        ctx.vol_regime = vol_regime

        regime_signal: Signal = self._regime.evaluate(ctx)
        regime_str = str(regime_signal.meta.get("regime", Regime.RANGING.value))
        regime = Regime(regime_str)

        all_signals = [
            self._trend.evaluate(ctx),
            self._meanrev.evaluate(ctx),
            self._derivatives.evaluate(ctx),
            self._smc_structure.evaluate(ctx),
            self._smc_order_blocks.evaluate(ctx),
            self._smc_liquidity.evaluate(ctx),
            vol_signal,
            regime_signal,
        ]
        verdict = aggregate(
            signals=all_signals,
            regime=regime,
            weights_cfg=self.weights,
            symbol=ctx.symbol,
            vol_regime=vol_regime,
        )
        return verdict.model_copy(update={"produced_at": ctx.tick_time})

    def _use_setup_snapshots(self) -> bool:
        return (
            self.optimized_setup_snapshots
            and self.setup_source == "mtf"
            and self.timeframes.execution != Timeframe.H4
            and Timeframe.H4 in self.timeframes.setup
        )

    def _mtf_decision(self, ctx: EvaluationContext, price_row: pd.Series) -> _MTFDecision:
        verdict = self._evaluate_context(ctx)
        return self._mtf_decision_from_verdict(verdict, ctx, ctx, price_row)

    def _mtf_decision_from_verdict(
        self,
        verdict: Verdict,
        trigger_ctx: EvaluationContext,
        setup_ctx: EvaluationContext,
        price_row: pd.Series,
    ) -> _MTFDecision:
        setup_direction = verdict.decision
        context_bias = _context_bias(setup_ctx)
        if self.setup_source == "h1_raw":
            return _raw_h1_decision(
                verdict=verdict,
                ctx=trigger_ctx,
                price_row=price_row,
                rules=self.trigger_rules,
                max_age_bars=self.max_trigger_age_bars,
                context_bias=context_bias,
            )
        if self.timeframes.execution == Timeframe.H4:
            return _MTFDecision(
                verdict=verdict,
                signal_override=None,
                trigger_type="h4_close",
                context_bias=context_bias,
                setup_direction=setup_direction,
            )

        signal = {"BUY": 1, "SELL": -1, "HOLD": 0}.get(verdict.decision, 0)
        if signal == 0:
            return _MTFDecision(
                verdict=verdict,
                signal_override=0,
                trigger_type="setup_neutral",
                context_bias=context_bias,
                setup_direction=setup_direction,
                rationale_suffix="MTF neutralized: H4 setup is neutral",
            )
        if _context_opposes_signal(context_bias, signal):
            return _MTFDecision(
                verdict=verdict,
                signal_override=0,
                trigger_type="context_opposite",
                context_bias=context_bias,
                setup_direction=setup_direction,
                rationale_suffix="MTF neutralized: D1 context is opposite",
            )
        trigger_type = _select_h1_trigger_type(
            ctx=trigger_ctx,
            price_row=price_row,
            signal=signal,
            trigger_tf=self.timeframes.trigger,
            rules=self.trigger_rules,
            max_age_bars=self.max_trigger_age_bars,
        )
        if trigger_type is None:
            return _MTFDecision(
                verdict=verdict,
                signal_override=0,
                trigger_type="trigger_rejected",
                context_bias=context_bias,
                setup_direction=setup_direction,
                rationale_suffix="MTF neutralized: trigger candle did not confirm setup",
            )
        return _MTFDecision(
            verdict=verdict,
            signal_override=signal,
            trigger_type=trigger_type,
            context_bias=context_bias,
            setup_direction=setup_direction,
        )

    def suggest_params(self, trial: optuna.Trial) -> dict[str, Any]:
        return {
            "sl_atr_mult": trial.suggest_float("sl_atr_mult", 1.0, 3.5),
            "sl_atr_buffer_mult": trial.suggest_float("sl_atr_buffer_mult", 0.05, 0.30),
            "max_sl_distance_atr": trial.suggest_float("max_sl_distance_atr", 2.0, 8.0),
            "min_confidence": trial.suggest_int("min_confidence", 0, 75, step=5),
        }


def _weights_path(value: object) -> Path:
    if value is not None:
        return Path(str(value))
    repo_root = Path(__file__).resolve().parents[4]
    return repo_root / "config" / "weights.yaml"


def _setup_source_config(value: object) -> str:
    if value is None:
        return "mtf"
    setup_source = str(value)
    if setup_source not in _SETUP_SOURCES:
        joined = ", ".join(sorted(_SETUP_SOURCES))
        raise ValueError(f"setup_source must be one of: {joined}")
    return setup_source


def _optional_int(value: object) -> int | None:
    if value is None:
        return None
    if not isinstance(value, int | float | str | bytes | bytearray):
        raise TypeError(f"min_confidence must be int-compatible, got {type(value).__name__}")
    return int(value)


def _signal_filter_config(params: dict[str, Any]) -> _SignalFilterConfig:
    return _SignalFilterConfig(
        allowed_sides=_optional_side_set(params.get("allowed_sides")),
        allowed_sl_anchor_types=_optional_anchor_type_set(params.get("allowed_sl_anchor_types")),
        blocked_sl_anchor_types=frozenset(
            str(anchor_type) for anchor_type in (params.get("blocked_sl_anchor_types") or ())
        ),
        max_anchor_age_hours=_optional_positive_float(
            params.get("max_anchor_age_hours"), "max_anchor_age_hours"
        ),
        min_signal_sl_distance_atr=_optional_positive_float(
            params.get("min_signal_sl_distance_atr"), "min_signal_sl_distance_atr"
        ),
        max_signal_sl_distance_atr=_optional_positive_float(
            params.get("max_signal_sl_distance_atr"), "max_signal_sl_distance_atr"
        ),
        block_context_reversal=bool(params.get("block_context_reversal", False)),
        block_d1_h4_context_reversal=bool(params.get("block_d1_h4_context_reversal", False)),
        require_h4_context_aligned=bool(params.get("require_h4_context_aligned", False)),
        min_trend_strength_atr=_optional_non_negative_float(
            params.get("min_trend_strength_atr"), "min_trend_strength_atr"
        ),
        min_volume_median_ratio=_optional_non_negative_float(
            params.get("min_volume_median_ratio"), "min_volume_median_ratio"
        ),
        max_bb_width_pct=_optional_non_negative_float(
            params.get("max_bb_width_pct"), "max_bb_width_pct"
        ),
    )


def _optional_side_set(value: object) -> frozenset[str] | None:
    if value is None:
        return None
    if not isinstance(value, list | tuple | set | frozenset):
        raise TypeError("allowed_sides must be a list of 'long'/'short' values")
    sides = frozenset(str(item).lower() for item in value)
    invalid = sides.difference({"long", "short"})
    if invalid:
        joined = ", ".join(sorted(invalid))
        raise ValueError(f"allowed_sides contains invalid values: {joined}")
    return sides


def _optional_anchor_type_set(value: object) -> frozenset[str] | None:
    if value is None:
        return None
    if not isinstance(value, list | tuple | set | frozenset):
        raise TypeError("allowed_sl_anchor_types must be a list of anchor type values")
    anchors = frozenset(str(item) for item in value)
    invalid = anchors.difference(_STOP_ANCHOR_TYPES)
    if invalid:
        joined = ", ".join(sorted(invalid))
        raise ValueError(f"allowed_sl_anchor_types contains invalid values: {joined}")
    return anchors


def _optional_positive_float(value: object, name: str) -> float | None:
    if value is None:
        return None
    if not isinstance(value, int | float | str | bytes | bytearray):
        raise ValueError(f"{name} must be a positive number")
    result = float(value)
    if result <= 0:
        raise ValueError(f"{name} must be positive")
    return result


def _optional_non_negative_float(value: object, name: str) -> float | None:
    if value is None:
        return None
    if not isinstance(value, int | float | str | bytes | bytearray):
        raise ValueError(f"{name} must be a non-negative number")
    result = float(value)
    if result < 0:
        raise ValueError(f"{name} must be non-negative")
    return result


def _donor_discovery_features(
    *,
    primary: pd.DataFrame,
    h4: pd.DataFrame,
    d1: pd.DataFrame,
) -> pd.DataFrame:
    from backtester.strategy_discovery.features import build_donor_discovery_features

    return build_donor_discovery_features(
        primary=primary,
        h4=h4 if not h4.empty else None,
        d1=d1 if not d1.empty else None,
    )


def _uses_discovery_features(filters: _SignalFilterConfig) -> bool:
    return (
        filters.block_d1_h4_context_reversal
        or filters.require_h4_context_aligned
        or filters.min_trend_strength_atr is not None
        or filters.min_volume_median_ratio is not None
        or filters.max_bb_width_pct is not None
    )


def _discovery_bar_features(
    features: pd.DataFrame,
    open_time: pd.Timestamp,
    *,
    volume: float,
) -> _DiscoveryBarFeatures:
    row = features.loc[open_time]
    return _DiscoveryBarFeatures(
        trend_strength_atr=_finite_float_or_none(row.get("trend_strength_atr")),
        volume=volume,
        volume_median20=_finite_float_or_none(row.get("volume_median20")),
        d1_context=str(row.get("d1_context", "missing")),
        h4_context=str(row.get("h4_context", "missing")),
        bb_width_pct=_finite_float_or_none(row.get("bb_width_pct")),
    )


def _finite_float_or_none(value: object) -> float | None:
    if value is None or pd.isna(value):
        return None
    result = float(value)
    if not np.isfinite(result):
        return None
    return result


def _positive_int(value: object, name: str) -> int:
    if not isinstance(value, int | float | str | bytes | bytearray):
        raise ValueError(f"{name} must be a positive integer")
    result = int(value)
    if result <= 0:
        raise ValueError(f"{name} must be positive")
    return result


def _timeframe_role_config(value: object) -> TimeframeRoleConfig:
    if value is None:
        return TimeframeRoleConfig(
            context=(Timeframe.D1,),
            setup=(Timeframe.H4,),
            trigger=Timeframe.H4,
            execution=Timeframe.H4,
        )
    if not isinstance(value, dict):
        raise TypeError("timeframes must be an object")
    context_raw = value.get("context", [Timeframe.D1.value])
    setup_raw = value.get("setup", [Timeframe.H4.value])
    return TimeframeRoleConfig(
        context=tuple(_parse_timeframe(item) for item in _as_list(context_raw)),
        setup=tuple(_parse_timeframe(item) for item in _as_list(setup_raw)),
        trigger=_parse_timeframe(value.get("trigger", Timeframe.H4.value)),
        execution=_parse_timeframe(
            value.get("execution", value.get("trigger", Timeframe.H4.value))
        ),
    )


def _trigger_rules_config(
    value: object, timeframes: TimeframeRoleConfig
) -> tuple[_TriggerRule, ...]:
    if timeframes.execution == Timeframe.H4:
        return ("h1_candle_confirm",)
    if value is None:
        return _H1_STRUCTURAL_TRIGGER_RULES
    if not isinstance(value, list | tuple | set | frozenset):
        raise TypeError("trigger_rules must be a list of trigger rule names")
    rules = tuple(str(item) for item in value)
    invalid = sorted(set(rules).difference(_TRIGGER_RULES))
    if invalid:
        joined = ", ".join(invalid)
        raise ValueError(f"trigger_rules contains invalid values: {joined}")
    if not rules:
        raise ValueError("trigger_rules must not be empty")
    return cast(tuple[_TriggerRule, ...], rules)


def _as_list(value: object) -> list[object]:
    if isinstance(value, list | tuple):
        return list(value)
    return [value]


def _parse_timeframe(value: object) -> Timeframe:
    text = str(value).strip().lower()
    aliases = {
        "m15": Timeframe.M15,
        "15m": Timeframe.M15,
        "h1": Timeframe.H1,
        "1h": Timeframe.H1,
        "h4": Timeframe.H4,
        "4h": Timeframe.H4,
        "d1": Timeframe.D1,
        "1d": Timeframe.D1,
    }
    if text not in aliases:
        raise ValueError(f"unsupported timeframe: {value!r}")
    return aliases[text]


def _coerce_strategy_data(data: StrategyInput) -> StrategyData:
    if isinstance(data, StrategyData):
        return data
    metadata: dict[str, object] = {"symbol": "UNKNOWN", "exchange": "unknown"}
    execution_context = read_execution_context(data)
    if execution_context is not None:
        metadata[EXECUTION_CONTEXT_METADATA_KEY] = execution_context
    return StrategyData(
        primary=data,
        candles={Timeframe.H4.name: data},
        extras={},
        metadata=metadata,
    )


def _skip_structural_entry_gate(context: StrategyExecutionContext | None) -> bool:
    return context is not None and context.skips_structural_entry_gate


def _tp_pct_placeholder_stop(*, signal: int, entry: float, atr: float) -> _StopPlan:
    if signal not in (1, -1) or not np.isfinite(entry) or entry <= 0:
        return _StopPlan(0, entry, "none", None, None, None)
    if not np.isfinite(atr) or atr <= 0:
        sl_price = entry * (0.999 if signal == 1 else 1.001)
    else:
        sl_price = entry - atr if signal == 1 else entry + atr
    return _StopPlan(
        signal,
        sl_price,
        "none",
        None,
        None,
        None,
        "execution_context tp_pct: structural entry gate skipped",
    )


def _candle_frame(data: StrategyData, timeframe: Timeframe) -> pd.DataFrame:
    return data.candles.get(timeframe.name, data.candles.get(timeframe.value, pd.DataFrame()))


def _tick_index_from_open_index(index: pd.Index, timeframe: Timeframe) -> pd.DatetimeIndex:
    dt_index = pd.to_datetime(index, utc=True)
    return pd.DatetimeIndex(dt_index + _TIMEFRAME_CLOSE_DELTA[timeframe])


def _to_crypt_candles(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["open_time", "o", "h", "l", "c", "volume"])
    frame = df.copy()
    if "open_time" not in frame.columns:
        frame.loc[:, "open_time"] = pd.to_datetime(frame.index, utc=True)
    else:
        frame.loc[:, "open_time"] = pd.to_datetime(frame["open_time"], utc=True)

    rename = {
        "open": "o",
        "high": "h",
        "low": "l",
        "close": "c",
    }
    frame = frame.rename(columns=rename)
    required = ["open_time", "o", "h", "l", "c", "volume"]
    missing = [col for col in required if col not in frame.columns]
    if missing:
        return pd.DataFrame(columns=required)
    result = frame.loc[:, required].copy()
    result.index.name = None
    for col in ("o", "h", "l", "c", "volume"):
        result.loc[:, col] = result[col].astype(float)
    return result.sort_values("open_time").reset_index(drop=True)


def _closed_candles(df: pd.DataFrame, timeframe: Timeframe, tick_time: datetime) -> pd.DataFrame:
    if df.empty:
        return df
    open_time = pd.to_datetime(df["open_time"], utc=True)
    tick = pd.Timestamp(tick_time)
    if tick.tzinfo is None:
        tick = tick.tz_localize("UTC")
    close_time = open_time + _TIMEFRAME_CLOSE_DELTA[timeframe]
    return df.loc[close_time <= tick].tail(_CANDLE_LIMIT).reset_index(drop=True)


def _latest_closed_time(
    df: pd.DataFrame, *, timeframe: Timeframe, tick_time: datetime
) -> datetime | None:
    if df.empty:
        return None
    open_time = pd.to_datetime(df["open_time"], utc=True)
    tick = _utc_timestamp(tick_time)
    close_time = pd.DatetimeIndex(open_time + _TIMEFRAME_CLOSE_DELTA[timeframe])
    end = int(close_time.searchsorted(tick, side="right"))
    if end <= 0:
        return None
    return cast(datetime, close_time[end - 1].to_pydatetime())


def _filter_ts(df: pd.DataFrame, tick_time: datetime, limit: int) -> pd.DataFrame:
    if df.empty or "ts" not in df.columns:
        return pd.DataFrame()
    tick = pd.Timestamp(tick_time)
    if tick.tzinfo is None:
        tick = tick.tz_localize("UTC")
    frame = df.copy()
    frame.loc[:, "ts"] = pd.to_datetime(frame["ts"], utc=True)
    return frame.loc[frame["ts"] < tick].tail(limit).reset_index(drop=True)


class _ContextWindowCache:
    """Pre-index closed candle and extras windows without changing semantics."""

    def __init__(
        self,
        *,
        candles: dict[Timeframe, pd.DataFrame],
        extras: dict[str, pd.DataFrame],
    ) -> None:
        self._candles: dict[Timeframe, pd.DataFrame] = {}
        self._candle_close_times: dict[Timeframe, pd.DatetimeIndex] = {}
        for timeframe, frame in candles.items():
            self._candles[timeframe] = frame
            if frame.empty or "open_time" not in frame.columns:
                self._candle_close_times[timeframe] = pd.DatetimeIndex([], tz="UTC")
                continue
            open_time = pd.to_datetime(frame["open_time"], utc=True)
            close_time = pd.DatetimeIndex(open_time + _TIMEFRAME_CLOSE_DELTA[timeframe])
            self._candle_close_times[timeframe] = close_time

        self._extras: dict[str, pd.DataFrame] = {}
        self._extra_times: dict[str, pd.DatetimeIndex] = {}
        for name, frame in extras.items():
            if frame.empty or "ts" not in frame.columns:
                self._extras[name] = pd.DataFrame()
                self._extra_times[name] = pd.DatetimeIndex([], tz="UTC")
                continue
            converted = frame.copy()
            converted.loc[:, "ts"] = pd.to_datetime(converted["ts"], utc=True)
            self._extras[name] = converted
            self._extra_times[name] = pd.DatetimeIndex(converted["ts"])

    def build_context(self, *, symbol: str, tick_time: datetime) -> EvaluationContext:
        closed = {
            timeframe: frame
            for timeframe in self._candles
            if not (frame := self.closed_candles(timeframe=timeframe, tick_time=tick_time)).empty
        }
        oi_df = self.filter_extra(name="oi", tick_time=tick_time, limit=_OI_LIMIT)
        ls_df = self.filter_extra(name="ls_ratio", tick_time=tick_time, limit=_LS_LIMIT)
        taker_df = self.filter_extra(name="taker_volume", tick_time=tick_time, limit=_TAKER_LIMIT)
        return EvaluationContext(
            symbol=symbol,
            tick_time=tick_time,
            candles=closed,
            oi=_df_to_oi(oi_df, symbol),
            ls_ratio=_df_to_ls_ratio(ls_df, symbol),
            taker_volume=_df_to_taker_volume(taker_df, symbol),
        )

    def closed_candles(self, *, timeframe: Timeframe, tick_time: datetime) -> pd.DataFrame:
        frame = self._candles.get(timeframe, pd.DataFrame())
        if frame.empty:
            return frame
        close_times = self._candle_close_times[timeframe]
        tick = _utc_timestamp(tick_time)
        end = int(close_times.searchsorted(tick, side="right"))
        start = max(0, end - _CANDLE_LIMIT)
        return frame.iloc[start:end].reset_index(drop=True)

    def filter_extra(self, *, name: str, tick_time: datetime, limit: int) -> pd.DataFrame:
        frame = self._extras.get(name, pd.DataFrame())
        if frame.empty or name not in self._extra_times:
            return pd.DataFrame()
        times = self._extra_times[name]
        tick = _utc_timestamp(tick_time)
        end = int(times.searchsorted(tick, side="left"))
        start = max(0, end - limit)
        return frame.iloc[start:end].reset_index(drop=True)


def _utc_timestamp(value: datetime) -> pd.Timestamp:
    timestamp = pd.Timestamp(value)
    if timestamp.tzinfo is None:
        return timestamp.tz_localize("UTC")
    return timestamp.tz_convert("UTC")


def _build_context(
    *,
    symbol: str,
    tick_time: datetime,
    candles: dict[Timeframe, pd.DataFrame],
    extras: dict[str, pd.DataFrame],
) -> EvaluationContext:
    closed = {
        tf: frame
        for tf, df in candles.items()
        if not (frame := _closed_candles(df, tf, tick_time)).empty
    }
    oi_df = _filter_ts(extras.get("oi", pd.DataFrame()), tick_time, _OI_LIMIT)
    ls_df = _filter_ts(extras.get("ls_ratio", pd.DataFrame()), tick_time, _LS_LIMIT)
    taker_df = _filter_ts(extras.get("taker_volume", pd.DataFrame()), tick_time, _TAKER_LIMIT)
    return EvaluationContext(
        symbol=symbol,
        tick_time=tick_time,
        candles=closed,
        oi=_df_to_oi(oi_df, symbol),
        ls_ratio=_df_to_ls_ratio(ls_df, symbol),
        taker_volume=_df_to_taker_volume(taker_df, symbol),
    )


def _context_bias(ctx: EvaluationContext) -> str:
    d1 = ctx.candles.get(Timeframe.D1)
    if d1 is None or d1.empty:
        return "neutral"
    state = analyse_smc_cached(d1, tick_time=ctx.tick_time)
    if BEARISH in (state.swing_bias, state.internal_bias):
        return "bearish"
    if BULLISH in (state.swing_bias, state.internal_bias):
        return "bullish"
    last = d1.iloc[-1]
    close = float(last["c"])
    open_price = float(last["o"])
    if close > open_price:
        return "bullish"
    if close < open_price:
        return "bearish"
    return "neutral"


def _context_opposes_signal(context_bias: str, signal: int) -> bool:
    return (signal == 1 and context_bias == "bearish") or (
        signal == -1 and context_bias == "bullish"
    )


def _raw_h1_decision(
    *,
    verdict: Verdict,
    ctx: EvaluationContext,
    price_row: pd.Series,
    rules: tuple[_TriggerRule, ...],
    max_age_bars: int,
    context_bias: str,
) -> _MTFDecision:
    selected = _select_raw_h1_trigger(
        ctx=ctx,
        price_row=price_row,
        rules=rules,
        max_age_bars=max_age_bars,
    )
    if selected is None:
        return _MTFDecision(
            verdict=verdict,
            signal_override=0,
            trigger_type="raw_h1_trigger_rejected",
            context_bias=context_bias,
            setup_direction="RAW",
            rationale_suffix="MTF neutralized: raw H1 trigger did not fire",
        )
    signal, trigger_type = selected
    setup_direction = "BUY" if signal == 1 else "SELL"
    return _MTFDecision(
        verdict=verdict,
        signal_override=signal,
        trigger_type=trigger_type,
        context_bias=context_bias,
        setup_direction=setup_direction,
        rationale_suffix=f"raw H1 diagnostic trigger: {trigger_type}",
    )


def _select_raw_h1_trigger(
    *,
    ctx: EvaluationContext,
    price_row: pd.Series,
    rules: tuple[_TriggerRule, ...],
    max_age_bars: int,
) -> tuple[int, str] | None:
    state = _structural_stop_state_for_timeframe(ctx, Timeframe.H1)
    for rule in rules:
        if rule == "h1_candle_confirm":
            candle_signal = _candle_direction_signal(price_row)
            if candle_signal != 0:
                return candle_signal, "raw_1h_candle_confirm"
        if rule == "h1_sweep_reversal":
            sweep_signal = _raw_h1_sweep_reversal_signal(
                state=state,
                price_row=price_row,
                tick_time=ctx.tick_time,
                max_age_bars=max_age_bars,
            )
            if sweep_signal != 0:
                return sweep_signal, "raw_h1_sweep_reversal"
        if rule == "h1_structure_break":
            structure_signal = _raw_h1_structure_break_signal(
                state=state,
                tick_time=ctx.tick_time,
                max_age_bars=max_age_bars,
            )
            if structure_signal != 0:
                return structure_signal, "raw_h1_structure_break"
        if rule == "h1_order_block_retest":
            order_block_signal = _raw_h1_order_block_retest_signal(
                state=state,
                price_row=price_row,
                tick_time=ctx.tick_time,
            )
            if order_block_signal != 0:
                return order_block_signal, "raw_h1_order_block_retest"
        if rule == "h1_momentum_burst":
            momentum_signal = _raw_h1_momentum_burst_signal(
                ctx=ctx,
                price_row=price_row,
            )
            if momentum_signal != 0:
                return momentum_signal, "raw_h1_momentum_burst"
        if rule == "h1_nr7_breakout":
            nr7_signal = _raw_h1_nr7_breakout_signal(
                ctx=ctx,
                price_row=price_row,
            )
            if nr7_signal != 0:
                return nr7_signal, "raw_h1_nr7_breakout"
    return None


def _candle_direction_signal(price_row: pd.Series) -> int:
    close = float(price_row["close"])
    open_price = float(price_row["open"])
    if close > open_price:
        return 1
    if close < open_price:
        return -1
    return 0


def _raw_h1_sweep_reversal_signal(
    *,
    state: SMCState,
    price_row: pd.Series,
    tick_time: datetime,
    max_age_bars: int,
) -> int:
    candle_signal = _candle_direction_signal(price_row)
    if candle_signal == 0:
        return 0
    swept_side = "low" if candle_signal == 1 else "high"
    candidates = [
        sweep
        for sweep in state.liquidity_sweeps
        if sweep.side == swept_side
        and sweep.known_at <= tick_time
        and _event_age_bars(sweep.known_at, tick_time, Timeframe.H1) <= max_age_bars
    ]
    return candle_signal if candidates else 0


def _raw_h1_structure_break_signal(
    *,
    state: SMCState,
    tick_time: datetime,
    max_age_bars: int,
) -> int:
    candidates = [
        event
        for event in state.structure_events
        if event.known_at <= tick_time
        and _event_age_bars(event.known_at, tick_time, Timeframe.H1) <= max_age_bars
        and event.direction in {BULLISH, BEARISH}
    ]
    if not candidates:
        return 0
    newest = max(candidates, key=lambda event: event.known_at)
    return 1 if newest.direction == BULLISH else -1


def _raw_h1_order_block_retest_signal(
    *,
    state: SMCState,
    price_row: pd.Series,
    tick_time: datetime,
) -> int:
    candidates = [
        block
        for block in state.order_blocks
        if block.active
        and block.known_at <= tick_time
        and _trigger_candle_touches_order_block(price_row, block)
        and block.direction in {BULLISH, BEARISH}
    ]
    if not candidates:
        return 0
    candle_signal = _candle_direction_signal(price_row)
    if candle_signal == 0:
        return 0
    matching = [
        block
        for block in candidates
        if (block.direction == BULLISH and candle_signal == 1)
        or (block.direction == BEARISH and candle_signal == -1)
    ]
    if not matching:
        return 0
    newest = max(matching, key=lambda block: block.known_at)
    return 1 if newest.direction == BULLISH else -1


def _raw_h1_momentum_burst_signal(
    *,
    ctx: EvaluationContext,
    price_row: pd.Series,
) -> int:
    del price_row
    candles = ctx.candles.get(Timeframe.H1)
    if candles is None or candles.empty:
        return 0
    closed = _closed_candles(candles, Timeframe.H1, ctx.tick_time)
    if len(closed) < 21:
        return 0
    close = closed["c"].astype(float)
    open_ = closed["o"].astype(float)
    returns = close.pct_change()
    std = returns.rolling(20, min_periods=20).std().shift(1)
    current_return = returns.iloc[-1]
    current_std = std.iloc[-1]
    if pd.isna(current_return) or pd.isna(current_std) or float(current_std) <= 0:
        return 0
    current_close = float(close.iloc[-1])
    current_open = float(open_.iloc[-1])
    threshold = float(current_std) * 1.5
    if current_return > threshold and current_close > current_open:
        return 1
    if current_return < -threshold and current_close < current_open:
        return -1
    return 0


def _raw_h1_nr7_breakout_signal(
    *,
    ctx: EvaluationContext,
    price_row: pd.Series,
) -> int:
    del price_row
    candles = ctx.candles.get(Timeframe.H1)
    if candles is None or candles.empty:
        return 0
    closed = _closed_candles(candles, Timeframe.H1, ctx.tick_time)
    if len(closed) < 7:
        return 0
    high = closed["h"].astype(float)
    low = closed["l"].astype(float)
    open_ = closed["o"].astype(float)
    close = closed["c"].astype(float)
    bar_range = high - low
    rolling_min = bar_range.rolling(7, min_periods=7).min()
    current_min = rolling_min.iloc[-1]
    current_range = bar_range.iloc[-1]
    if pd.isna(current_min) or pd.isna(current_range) or current_range > current_min:
        return 0
    current_close = float(close.iloc[-1])
    current_open = float(open_.iloc[-1])
    if current_close > current_open:
        return 1
    if current_close < current_open:
        return -1
    return 0


def _trigger_candle_confirms(price_row: pd.Series, signal: int) -> bool:
    close = float(price_row["close"])
    open_price = float(price_row["open"])
    if signal == 1:
        return close > open_price
    if signal == -1:
        return close < open_price
    return False


def _select_h1_trigger_type(
    *,
    ctx: EvaluationContext,
    price_row: pd.Series,
    signal: int,
    trigger_tf: Timeframe,
    rules: tuple[_TriggerRule, ...],
    max_age_bars: int,
) -> str | None:
    if trigger_tf != Timeframe.H1:
        return (
            f"{trigger_tf.value}_candle_confirm"
            if _trigger_candle_confirms(price_row, signal)
            else None
        )

    state = _structural_stop_state_for_timeframe(ctx, Timeframe.H1)
    for rule in rules:
        if rule == "h1_sweep_reversal" and _h1_sweep_reversal_confirms(
            state=state,
            price_row=price_row,
            signal=signal,
            tick_time=ctx.tick_time,
            max_age_bars=max_age_bars,
        ):
            return rule
        if rule == "h1_structure_break" and _h1_structure_break_confirms(
            state=state,
            signal=signal,
            tick_time=ctx.tick_time,
            max_age_bars=max_age_bars,
        ):
            return rule
        if rule == "h1_order_block_retest" and _h1_order_block_retest_confirms(
            state=state,
            price_row=price_row,
            signal=signal,
            tick_time=ctx.tick_time,
        ):
            return rule
        if rule == "h1_candle_confirm" and _trigger_candle_confirms(price_row, signal):
            return "1h_candle_confirm"
    return None


def _h1_sweep_reversal_confirms(
    *,
    state: SMCState,
    price_row: pd.Series,
    signal: int,
    tick_time: datetime,
    max_age_bars: int,
) -> bool:
    swept_side = "low" if signal == 1 else "high"
    candidates = [
        sweep
        for sweep in state.liquidity_sweeps
        if sweep.side == swept_side
        and sweep.known_at <= tick_time
        and _event_age_bars(sweep.known_at, tick_time, Timeframe.H1) <= max_age_bars
    ]
    if not candidates:
        return False
    return _trigger_candle_confirms(price_row, signal)


def _h1_structure_break_confirms(
    *,
    state: SMCState,
    signal: int,
    tick_time: datetime,
    max_age_bars: int,
) -> bool:
    direction = BULLISH if signal == 1 else BEARISH
    candidates = [
        event
        for event in state.structure_events
        if event.direction == direction
        and event.known_at <= tick_time
        and _event_age_bars(event.known_at, tick_time, Timeframe.H1) <= max_age_bars
    ]
    return bool(candidates)


def _h1_order_block_retest_confirms(
    *,
    state: SMCState,
    price_row: pd.Series,
    signal: int,
    tick_time: datetime,
) -> bool:
    direction = BULLISH if signal == 1 else BEARISH
    candidates = [
        block
        for block in state.order_blocks
        if block.active
        and block.direction == direction
        and block.known_at <= tick_time
        and _trigger_candle_touches_order_block(price_row, block)
    ]
    if not candidates:
        return False
    return _trigger_candle_confirms(price_row, signal)


def _trigger_candle_touches_order_block(price_row: pd.Series, block: SMCOrderBlock) -> bool:
    high = float(price_row["high"])
    low = float(price_row["low"])
    close = float(price_row["close"])
    if block.direction == BULLISH:
        return low <= block.high and close >= block.low
    return high >= block.low and close <= block.high


def _event_age_bars(known_at: datetime, tick_time: datetime, timeframe: Timeframe) -> float:
    delta = _TIMEFRAME_CLOSE_DELTA[timeframe]
    return max(0.0, (tick_time - known_at) / delta)


def _atr14_from_donor_frame(df: pd.DataFrame) -> pd.Series:
    high = df["high"].astype(float)
    low = df["low"].astype(float)
    close = df["close"].astype(float)
    prev_close = close.shift(1)
    tr = pd.concat([high - low, (high - prev_close).abs(), (low - prev_close).abs()], axis=1).max(
        axis=1
    )
    return tr.rolling(14, min_periods=1).mean()


def _structural_stop_state(ctx: EvaluationContext) -> SMCState:
    return _structural_stop_state_for_timeframe(ctx, Timeframe.H4)


def _structural_stop_state_for_timeframe(ctx: EvaluationContext, timeframe: Timeframe) -> SMCState:
    candles = ctx.candles.get(timeframe)
    if candles is None or candles.empty:
        return SMCState()
    return analyse_smc_cached(candles, tick_time=ctx.tick_time)


def _signal_from_verdict(
    verdict: Verdict,
    *,
    signal_override: int | None,
    min_confidence: int | None,
) -> int:
    signal = {"BUY": 1, "SELL": -1, "HOLD": 0}.get(verdict.decision, 0)
    if signal_override is not None:
        signal = signal_override
    if min_confidence is not None and verdict.confidence < min_confidence:
        return 0
    return signal


def _apply_signal_filters(
    *,
    stop: _StopPlan,
    filters: _SignalFilterConfig,
    trigger_known_at: datetime,
    context_bias: str,
    setup_direction: str,
    discovery: _DiscoveryBarFeatures | None = None,
) -> tuple[_StopPlan, str | None]:
    if stop.signal == 0:
        return stop, None
    side = "long" if stop.signal == 1 else "short"
    if filters.allowed_sides is not None and side not in filters.allowed_sides:
        return _neutralized_filtered_stop(stop, f"side_not_allowed:{side}")
    if filters.allowed_sl_anchor_types is not None and stop.anchor_type not in (
        filters.allowed_sl_anchor_types
    ):
        return _neutralized_filtered_stop(stop, f"sl_anchor_type_not_allowed:{stop.anchor_type}")
    if stop.anchor_type in filters.blocked_sl_anchor_types:
        return _neutralized_filtered_stop(stop, f"sl_anchor_type_blocked:{stop.anchor_type}")
    if (
        filters.min_signal_sl_distance_atr is not None
        and stop.distance_atr is not None
        and stop.distance_atr < filters.min_signal_sl_distance_atr
    ):
        return _neutralized_filtered_stop(stop, f"sl_distance_too_tight:{stop.distance_atr:.4f}")
    if (
        filters.max_signal_sl_distance_atr is not None
        and stop.distance_atr is not None
        and stop.distance_atr > filters.max_signal_sl_distance_atr
    ):
        return _neutralized_filtered_stop(stop, f"sl_distance_too_wide:{stop.distance_atr:.4f}")
    if filters.max_anchor_age_hours is not None and stop.anchor_known_at is not None:
        age_hours = (trigger_known_at - stop.anchor_known_at).total_seconds() / 3600
        if age_hours > filters.max_anchor_age_hours:
            return _neutralized_filtered_stop(stop, f"anchor_too_old:{age_hours:.2f}h")
    if filters.block_context_reversal and _context_opposes_signal(context_bias, stop.signal):
        return _neutralized_filtered_stop(
            stop, f"context_reversal:{context_bias}:{setup_direction}"
        )
    if filters.min_trend_strength_atr is not None:
        strength = None if discovery is None else discovery.trend_strength_atr
        if strength is None:
            return _neutralized_filtered_stop(stop, "missing_trend_strength")
        if strength < filters.min_trend_strength_atr:
            return _neutralized_filtered_stop(stop, f"trend_strength_low:{strength:.4f}")
    if filters.min_volume_median_ratio is not None:
        if discovery is None or discovery.volume is None or discovery.volume_median20 is None:
            return _neutralized_filtered_stop(stop, "missing_volume")
        threshold = discovery.volume_median20 * filters.min_volume_median_ratio
        if discovery.volume < threshold:
            return _neutralized_filtered_stop(stop, "low_volume")
    if filters.block_d1_h4_context_reversal and discovery is not None:
        d1 = discovery.d1_context
        h4 = discovery.h4_context
        if (
            d1 not in _DISCOVERY_CONTEXT_INCOMPLETE
            and h4 not in _DISCOVERY_CONTEXT_INCOMPLETE
            and d1 != h4
        ):
            return _neutralized_filtered_stop(stop, f"d1_h4_context_reversal:{d1}:{h4}")
    if filters.require_h4_context_aligned:
        if discovery is None or discovery.h4_context in _DISCOVERY_CONTEXT_INCOMPLETE:
            return _neutralized_filtered_stop(stop, "missing_h4_context")
        expected = "long" if side == "long" else "short"
        if discovery.h4_context != expected:
            return _neutralized_filtered_stop(
                stop, f"h4_context_misaligned:{discovery.h4_context}"
            )
    if filters.max_bb_width_pct is not None:
        width = None if discovery is None else discovery.bb_width_pct
        if width is None:
            return _neutralized_filtered_stop(stop, "missing_bb_width_pct")
        if width > filters.max_bb_width_pct:
            return _neutralized_filtered_stop(stop, f"bb_not_squeezed:{width:.4f}")
    return stop, None


def _neutralized_filtered_stop(stop: _StopPlan, reason: str) -> tuple[_StopPlan, str]:
    return (
        _StopPlan(
            0,
            stop.sl_price,
            stop.anchor_type,
            stop.anchor_level,
            stop.anchor_known_at,
            stop.distance_atr,
            f"signal filter neutralized: {reason}",
        ),
        reason,
    )


def _select_structural_stop(
    *,
    ctx: EvaluationContext,
    signal: int,
    price_row: pd.Series,
    atr: float,
    sl_atr_mult: float,
    sl_atr_buffer_mult: float,
    max_sl_distance_atr: float,
    allow_atr_sl_fallback: bool,
    execution_tf: Timeframe,
) -> tuple[_StopPlan, Timeframe]:
    entry = float(price_row["close"])
    atr_value = float(atr) if np.isfinite(atr) else 0.0
    h4_stop = _plan_structural_stop(
        signal=signal,
        entry=entry,
        atr=atr_value,
        sl_atr_mult=sl_atr_mult,
        sl_atr_buffer_mult=sl_atr_buffer_mult,
        max_sl_distance_atr=max_sl_distance_atr,
        allow_atr_sl_fallback=allow_atr_sl_fallback,
        state=_structural_stop_state(ctx),
        tick_time=ctx.tick_time,
    )
    if execution_tf != Timeframe.H1:
        return h4_stop, Timeframe.H4

    h1_stop = _plan_structural_stop(
        signal=signal,
        entry=entry,
        atr=atr_value,
        sl_atr_mult=sl_atr_mult,
        sl_atr_buffer_mult=sl_atr_buffer_mult,
        max_sl_distance_atr=max_sl_distance_atr,
        allow_atr_sl_fallback=False,
        state=_structural_stop_state_for_timeframe(ctx, Timeframe.H1),
        tick_time=ctx.tick_time,
    )
    if _prefer_candidate_stop(h1_stop, h4_stop):
        return h1_stop, Timeframe.H1
    return h4_stop, Timeframe.H4


def _prefer_candidate_stop(candidate: _StopPlan, fallback: _StopPlan) -> bool:
    if candidate.signal == 0:
        return False
    if fallback.signal == 0:
        return True
    if candidate.signal != fallback.signal:
        return False
    if candidate.distance_atr is None:
        return False
    if fallback.distance_atr is None:
        return True
    return candidate.distance_atr < fallback.distance_atr


def _row_from_verdict(
    verdict: Verdict,
    stop: _StopPlan,
    *,
    rationale_suffix: str | None = None,
    context_tf: str = "1d",
    setup_tf: str = "4h",
    trigger_tf: str = "4h",
    context_bias: str = "neutral",
    setup_direction: str = "HOLD",
    trigger_type: str = "h4_close",
    trigger_known_at: datetime | None = None,
    setup_snapshot_time: datetime | None = None,
    sl_source_tf: str = "4h",
    signal_filter_reason: str | None = None,
) -> dict[str, object]:
    row: dict[str, object] = {
        "signal": stop.signal,
        "sl_price": float(stop.sl_price),
        "entry_price": np.nan,
        "confidence": verdict.confidence,
        "score": verdict.score,
        "regime": verdict.regime.value,
        "decision": verdict.decision,
        "rationale": _append_rationale(
            _append_rationale(verdict.rationale, rationale_suffix),
            stop.rationale_suffix,
        ),
        "sl_anchor_type": stop.anchor_type,
        "sl_anchor_level": stop.anchor_level,
        "sl_anchor_known_at": (
            stop.anchor_known_at.isoformat() if stop.anchor_known_at is not None else None
        ),
        "sl_distance_atr": stop.distance_atr,
        "context_tf": context_tf,
        "setup_tf": setup_tf,
        "trigger_tf": trigger_tf,
        "context_bias": context_bias,
        "setup_direction": setup_direction,
        "trigger_type": trigger_type,
        "trigger_known_at": (
            trigger_known_at.isoformat() if trigger_known_at is not None else None
        ),
        "setup_snapshot_time": (
            setup_snapshot_time.isoformat() if setup_snapshot_time is not None else None
        ),
        "sl_source_tf": sl_source_tf,
        "signal_filter_reason": signal_filter_reason,
    }
    strengths = {
        signal_obj.engine: signal_obj.strength
        for signal_obj in verdict.breakdown
        if signal_obj.engine in SCORING_ENGINES
    }
    for engine in sorted(SCORING_ENGINES):
        row[f"strength_{engine}"] = strengths.get(engine)
    return row


def _plan_structural_stop(
    *,
    signal: int,
    entry: float,
    atr: float,
    sl_atr_mult: float,
    sl_atr_buffer_mult: float,
    max_sl_distance_atr: float,
    allow_atr_sl_fallback: bool,
    state: SMCState,
    tick_time: datetime,
) -> _StopPlan:
    if signal == 0:
        return _StopPlan(0, entry, "none", None, None, None)
    if not np.isfinite(entry) or entry <= 0:
        return _neutral_stop(entry, "invalid entry price")
    if not np.isfinite(atr) or atr <= 0:
        return _neutral_stop(entry, "ATR unavailable for structural stop validation")

    anchor = (
        _order_block_anchor(state, signal, entry, tick_time)
        or _liquidity_sweep_anchor(state, signal, entry, tick_time)
        or _pivot_anchor(state, signal, entry, tick_time)
    )
    if anchor is None:
        if allow_atr_sl_fallback:
            sl_price = entry - sl_atr_mult * atr if signal == 1 else entry + sl_atr_mult * atr
            return _validated_stop(
                signal=signal,
                entry=entry,
                sl_price=sl_price,
                atr=atr,
                anchor_type="atr_fallback",
                anchor_level=None,
                anchor_known_at=None,
                max_sl_distance_atr=max_sl_distance_atr,
            )
        return _neutral_stop(entry, "no structural stop anchor")

    anchor_type, level, known_at = anchor
    buffer = max(0.0, sl_atr_buffer_mult) * atr
    sl_price = level - buffer if signal == 1 else level + buffer
    return _validated_stop(
        signal=signal,
        entry=entry,
        sl_price=sl_price,
        atr=atr,
        anchor_type=anchor_type,
        anchor_level=level,
        anchor_known_at=known_at,
        max_sl_distance_atr=max_sl_distance_atr,
    )


def _order_block_anchor(
    state: SMCState, signal: int, entry: float, tick_time: datetime
) -> tuple[_StopAnchorType, float, datetime] | None:
    direction = BULLISH if signal == 1 else BEARISH
    candidates = [
        block
        for block in state.order_blocks
        if block.active
        and block.direction == direction
        and block.known_at <= tick_time
        and ((signal == 1 and block.low < entry) or (signal == -1 and block.high > entry))
    ]
    if not candidates:
        return None

    def key(block: SMCOrderBlock) -> tuple[int, int, datetime]:
        bias_aligned = direction in (state.swing_bias, state.internal_bias)
        swing_kind = block.kind == "swing"
        return (1 if bias_aligned else 0, 1 if swing_kind else 0, block.known_at)

    block = max(candidates, key=key)
    return ("order_block", block.low if signal == 1 else block.high, block.known_at)


def _liquidity_sweep_anchor(
    state: SMCState, signal: int, entry: float, tick_time: datetime
) -> tuple[_StopAnchorType, float, datetime] | None:
    protective_side = "low" if signal == 1 else "high"
    candidates = [
        sweep
        for sweep in state.liquidity_sweeps
        if sweep.side == protective_side
        and sweep.known_at <= tick_time
        and max(0.0, (tick_time - sweep.known_at) / _H4) <= _MAX_SWEEP_AGE_BARS
        and ((signal == 1 and sweep.level < entry) or (signal == -1 and sweep.level > entry))
    ]
    if not candidates:
        return None
    sweep = max(candidates, key=lambda item: (item.known_at, item.level_type == "swing"))
    return ("liquidity_sweep", sweep.level, sweep.known_at)


def _pivot_anchor(
    state: SMCState, signal: int, entry: float, tick_time: datetime
) -> tuple[_StopAnchorType, float, datetime] | None:
    protective_side = "low" if signal == 1 else "high"
    candidates = [
        pivot
        for pivot in state.pivots
        if pivot.side == protective_side
        and pivot.known_at <= tick_time
        and ((signal == 1 and pivot.level < entry) or (signal == -1 and pivot.level > entry))
    ]
    if not candidates:
        return None

    def key(pivot: SMCPivot) -> tuple[int, datetime, float]:
        return (
            1 if pivot.kind == "swing" else 0,
            pivot.known_at,
            -abs(entry - pivot.level),
        )

    pivot = max(candidates, key=key)
    return ("pivot", pivot.level, pivot.known_at)


def _validated_stop(
    *,
    signal: int,
    entry: float,
    sl_price: float,
    atr: float,
    anchor_type: _StopAnchorType,
    anchor_level: float | None,
    anchor_known_at: datetime | None,
    max_sl_distance_atr: float,
) -> _StopPlan:
    if not np.isfinite(sl_price):
        return _neutral_stop(entry, "invalid structural stop")
    if signal == 1 and sl_price >= entry:
        return _neutral_stop(entry, "structural stop is not below long entry")
    if signal == -1 and sl_price <= entry:
        return _neutral_stop(entry, "structural stop is not above short entry")

    distance_atr = abs(entry - sl_price) / atr
    if distance_atr <= 0 or distance_atr > max_sl_distance_atr:
        return _neutral_stop(entry, "structural stop distance outside ATR guard")
    return _StopPlan(
        signal,
        sl_price,
        anchor_type,
        anchor_level,
        anchor_known_at,
        round(distance_atr, 4),
    )


def _neutral_stop(entry: float, reason: str) -> _StopPlan:
    return _StopPlan(0, entry, "none", None, None, None, f"SL neutralized: {reason}")


def _append_rationale(rationale: str, suffix: str | None) -> str:
    if suffix is None:
        return rationale
    return f"{rationale}; {suffix}"


def _neutral_row(reason: str, price_row: pd.Series) -> dict[str, object]:
    close = float(price_row["close"])
    row: dict[str, object] = {
        "signal": 0,
        "sl_price": close,
        "entry_price": close,
        "confidence": 0,
        "score": 0.0,
        "regime": Regime.RANGING.value,
        "decision": "HOLD",
        "rationale": reason,
        "sl_anchor_type": "none",
        "sl_anchor_level": None,
        "sl_anchor_known_at": None,
        "sl_distance_atr": None,
        "context_tf": "1d",
        "setup_tf": "4h",
        "trigger_tf": "4h",
        "context_bias": "neutral",
        "setup_direction": "HOLD",
        "trigger_type": "error",
        "trigger_known_at": None,
        "setup_snapshot_time": None,
        "sl_source_tf": "4h",
        "signal_filter_reason": None,
    }
    for engine in sorted(SCORING_ENGINES):
        row[f"strength_{engine}"] = None
    return row
