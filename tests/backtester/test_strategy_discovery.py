from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from backtester.data_contracts import StrategyData
from backtester.strategy_discovery.convert import (
    DiscoveryConversionError,
    convert_discovery_strategy,
)
from backtester.strategy_discovery.events import DiscoveryEvent
from backtester.strategy_discovery.features import (
    DiscoveryDataset,
    build_discovery_dataset,
    build_timeframe_discovery_dataset,
)
from backtester.strategy_discovery.filters import filter_catalog
from backtester.strategy_discovery.labeler import LabelConfig, label_events
from backtester.strategy_discovery.scoring import discovery_score
from backtester.strategy_discovery.search import (
    DiscoveryConfig,
    DiscoveryWindow,
    run_strategy_discovery,
)
from backtester.strategy_discovery.triggers import trigger_catalog


def test_candle_confirm_trigger_uses_current_closed_candle_only() -> None:
    dataset = _dataset_from_close_path([10, 11, 10, 12, 11, 13])

    events = trigger_catalog()["h1_candle_confirm"](dataset)

    assert [event.side for event in events] == ["long", "short", "long", "short", "long"]
    assert events[-1].event_time == dataset.ohlcv.index[-1]


def test_labeler_handles_win_loss_neutral_and_same_bar_loss() -> None:
    dataset = _dataset_from_ohlcv(
        [
            (10, 10.2, 9.8, 10),
            (10, 10.2, 9.8, 10),
            (10, 11.2, 9.8, 10.8),
            (10, 10.2, 9.8, 10),
            (10, 10.2, 9.8, 10),
        ],
        atr=1.0,
    )
    event = _event(dataset, index=1, side="long", entry=10)
    [labeled] = label_events(events=[event], dataset=dataset, config=LabelConfig())
    assert labeled.label == "win"

    loss_dataset = _dataset_from_ohlcv(
        [
            (10, 10.2, 9.8, 10),
            (10, 10.2, 9.8, 10),
            (10, 10.2, 8.8, 9.2),
        ],
        atr=1.0,
    )
    [loss] = label_events(
        events=[_event(loss_dataset, index=1, side="long", entry=10)],
        dataset=loss_dataset,
        config=LabelConfig(),
    )
    assert loss.label == "loss"

    neutral_dataset = _dataset_from_ohlcv(
        [
            (10, 10.2, 9.8, 10),
            (10, 10.2, 9.8, 10),
            (10, 10.5, 9.6, 10.1),
        ],
        atr=1.0,
    )
    [neutral] = label_events(
        events=[_event(neutral_dataset, index=1, side="long", entry=10)],
        dataset=neutral_dataset,
        config=LabelConfig(),
    )
    assert neutral.label == "neutral"

    same_bar_dataset = _dataset_from_ohlcv(
        [
            (10, 10.2, 9.8, 10),
            (10, 10.2, 9.8, 10),
            (10, 11.2, 8.8, 10),
        ],
        atr=1.0,
    )
    [same_bar] = label_events(
        events=[_event(same_bar_dataset, index=1, side="long", entry=10)],
        dataset=same_bar_dataset,
        config=LabelConfig(),
    )
    assert same_bar.label == "loss"
    assert same_bar.label_reason == "same_bar_both_barriers"


def test_filters_pass_and_reject_with_stable_reasons() -> None:
    dataset = _dataset_from_close_path([10, 11, 12])
    event = _event(dataset, index=1, side="short", entry=11)
    event.metadata.update(
        {
            "h4_context": "short",
            "d1_context": "long",
            "anchor_type": "liquidity_sweep",
            "anchor_age_hours": 48.0,
            "atr_distance": 1.5,
            "volatility_rank": 0.5,
            "trend_strength_atr": 0.7,
            "move_6_atr": 1.0,
            "volume": 100.0,
            "volume_median20": 120.0,
        }
    )
    filters = filter_catalog()

    assert filters["side_short_only"](event, dataset).passed
    assert filters["h4_context_aligned"](event, dataset).passed
    d1 = filters["d1_context_aligned"](event, dataset)
    assert not d1.passed
    assert d1.reason == "context_misaligned"
    assert filters["atr_distance_1_2"](event, dataset).passed
    anchor = filters["anchor_no_liquidity_sweep"](event, dataset)
    assert not anchor.passed
    assert anchor.reason == "liquidity_sweep_anchor"


def test_context_features_are_available_only_after_context_candle_close() -> None:
    h1 = _trend_frame(120)
    h4_index = pd.date_range("2025-01-01", periods=30, freq="4h", tz="UTC")
    h4_close = pd.Series([100.0 + index for index in range(30)], index=h4_index)
    h4 = pd.DataFrame(
        {
            "open": h4_close - 0.5,
            "high": h4_close + 1.0,
            "low": h4_close - 1.0,
            "close": h4_close,
            "volume": 100.0,
        },
        index=h4_index,
    )

    dataset = build_timeframe_discovery_dataset(
        data=StrategyData(
            candles_by_timeframe={"H1": h1, "H4": h4, "D1": pd.DataFrame()},
            extras={},
            metadata={},
        ),
        timeframe="H1",
        window_label="sample",
        symbol="SOL-USDT-SWAP",
    )
    context_open = h4_index[20]

    assert dataset.features.loc[context_open, "h4_context"] != "long"
    assert dataset.features.loc[context_open + pd.Timedelta(hours=4), "h4_context"] == "long"


def test_score_penalizes_tiny_samples() -> None:
    tiny = discovery_score(
        wins=1,
        losses=0,
        neutral=0,
        passed_events=1,
        windows_passing_min_trades=1,
        window_count=1,
    )
    larger = discovery_score(
        wins=10,
        losses=0,
        neutral=0,
        passed_events=10,
        windows_passing_min_trades=1,
        window_count=1,
    )

    assert larger > tiny


def test_strategy_discovery_exports_ranked_artifacts(tmp_path: Path) -> None:
    progress_steps: list[int] = []
    output = run_strategy_discovery(
        windows=[
            DiscoveryWindow(
                label="sample",
                symbol="SOL-USDT-SWAP",
                start="2025-01-01",
                end="2025-01-04",
                data=_trend_frame(80),
            )
        ],
        config=DiscoveryConfig(
            output=tmp_path,
            candle_timeframe="1h",
            min_trades_total=1,
            min_trades_per_window=1,
            beam_width=3,
            max_filter_depth=2,
        ),
        progress_callback=progress_steps.append,
    )

    candidates = pd.read_csv(output / "candidates.csv")
    assert not candidates.empty
    assert candidates["candidate_id"].is_unique
    assert "min_window_win_rate" in candidates.columns
    candidate_windows = pd.read_csv(output / "candidate_windows.csv")
    assert not candidate_windows.empty
    assert {
        "candidate_id",
        "window_label",
        "events",
        "wins",
        "losses",
        "neutral",
        "win_rate",
    }.issubset(candidate_windows.columns)
    assert (output / "search_trace.csv").exists()
    assert (output / "rejected.csv").exists()
    best_files = sorted((output / "best_candidates").glob("rank_*_strategy.json"))
    assert best_files
    payload = json.loads(best_files[0].read_text())
    assert payload["name"] == "strategy_discovery_candidate"
    assert (output / "top_win_rate_min_50.csv").exists()
    assert (output / "robust_min_window_win_rate_50.csv").exists()
    assert (output / "best_candidates" / "top_score" / "rank_001_strategy.json").exists()
    assert sum(progress_steps) > 0


def _trend_frame(length: int) -> pd.DataFrame:
    index = pd.date_range("2025-01-01", periods=length, freq="h", tz="UTC")
    close = pd.Series([100.0 + index_ * 0.2 for index_ in range(length)], index=index)
    return pd.DataFrame(
        {
            "open": close - 0.1,
            "high": close + 0.6,
            "low": close - 0.4,
            "close": close,
            "volume": 100.0,
        },
        index=index,
    )


def _dataset_from_close_path(closes: list[float]) -> DiscoveryDataset:
    rows = []
    for index, close in enumerate(closes):
        previous = closes[index - 1] if index > 0 else close
        rows.append((previous, max(previous, close), min(previous, close), close))
    return _dataset_from_ohlcv(rows, atr=1.0)


def _dataset_from_ohlcv(
    rows: list[tuple[float, float, float, float]],
    *,
    atr: float,
) -> DiscoveryDataset:
    index = pd.date_range("2025-01-01", periods=len(rows), freq="h", tz="UTC")
    frame = pd.DataFrame(rows, columns=["open", "high", "low", "close"], index=index)
    frame["volume"] = 100.0
    features = pd.DataFrame(
        {
            "atr": atr,
            "h4_context": "long",
            "d1_context": "long",
            "trend_strength_atr": 1.0,
            "volatility_rank": 0.5,
            "move_6_atr": 1.0,
            "volume_median20": 100.0,
        },
        index=index,
    )
    return DiscoveryDataset(
        window_label="sample",
        symbol="SOL-USDT-SWAP",
        ohlcv=frame,
        features=features,
    )


def _event(
    dataset: DiscoveryDataset,
    *,
    index: int,
    side: str,
    entry: float,
) -> DiscoveryEvent:
    return DiscoveryEvent(
        event_time=dataset.ohlcv.index[index],
        side=side,  # type: ignore[arg-type]
        trigger_name="test_trigger",
        entry_reference_price=entry,
        window_label=dataset.window_label,
        symbol=dataset.symbol,
        metadata={},
    )


def test_v2_triggers_emit_events_on_synthetic_patterns() -> None:
    triggers = trigger_catalog()
    assert len(triggers) == 44

    engulfing = _dataset_from_ohlcv(
        [
            (10.0, 10.2, 9.8, 9.9),
            (9.85, 10.3, 9.8, 10.2),
        ],
        atr=1.0,
    )
    events = triggers["h1_engulfing"](engulfing)
    assert len(events) == 1
    assert events[0].side == "long"

    ema_dataset = build_discovery_dataset(
        data=_trend_frame(80),
        window_label="sample",
        symbol="SOL-USDT-SWAP",
    )
    ema_events = triggers["h1_ema_cross"](ema_dataset)
    assert ema_events


def test_v2_filters_use_extended_metadata() -> None:
    dataset = _dataset_from_close_path([10, 11, 12])
    event = _event(dataset, index=1, side="long", entry=11)
    event.metadata.update(
        {
            "close": 11.0,
            "sma20": 10.5,
            "rsi14": 45.0,
            "volatility_rank": 0.15,
            "bb_width_pct": 0.03,
            "body_to_range": 0.6,
            "bar_range_atr": 0.5,
            "hour_utc": 10,
            "trend_strength_atr": 1.0,
            "volume": 150.0,
            "volume_median20": 100.0,
            "roc10": 0.02,
            "ema_stack_long": True,
            "ema_stack_short": False,
        }
    )
    filters = filter_catalog()
    assert len(filters) == 100

    assert filters["trend_ema_stack_aligned"](event, dataset).passed
    assert filters["sma20_side_aligned"](event, dataset).passed
    assert filters["rsi_side_aligned"](event, dataset).passed
    assert filters["volatility_low_only"](event, dataset).passed
    assert filters["bb_squeeze"](event, dataset).passed
    assert filters["session_london"](event, dataset).passed
    assert filters["volume_above_median"](event, dataset).passed
    assert filters["roc_side_aligned"](event, dataset).passed

    short_event = _event(dataset, index=1, side="short", entry=11)
    short_event.metadata.update(event.metadata)
    short_event.metadata["ema_stack_long"] = False
    short_event.metadata["ema_stack_short"] = True
    short_event.metadata["roc10"] = -0.02
    short_event.metadata["rsi14"] = 55.0
    assert filters["trend_ema_stack_aligned"](short_event, dataset).passed
    assert filters["roc_side_aligned"](short_event, dataset).passed


def test_v3_catalog_triggers_emit_on_synthetic_data() -> None:
    triggers = trigger_catalog()
    hammer_dataset = _dataset_from_ohlcv(
        [
            (10.0, 10.1, 9.9, 10.0),
            (10.0, 10.1, 8.5, 10.2),
        ],
        atr=0.5,
    )
    assert triggers["h1_hammer"](hammer_dataset)
    trend_dataset = build_discovery_dataset(
        data=_trend_frame(80),
        window_label="sample",
        symbol="SOL-USDT-SWAP",
    )
    assert triggers["h1_higher_high_higher_close"](trend_dataset)


def test_v3_filters_accept_expansion_metadata() -> None:
    dataset = _dataset_from_close_path([10, 11, 12, 13])
    event = _event(dataset, index=2, side="long", entry=12)
    event.metadata.update(
        {
            "session_vwap_dist_pct": 0.004,
            "volume_ratio_20": 2.0,
            "bb_at_20bar_low": True,
            "bb_expanding": True,
            "consecutive_bull": 3,
            "hour_utc": 3,
            "session_open_hour": 0,
        }
    )
    filters = filter_catalog()
    assert filters["vwap_side_aligned"](event, dataset).passed
    assert filters["volume_spike_2x"](event, dataset).passed
    assert filters["consecutive_bull_3"](event, dataset).passed
    assert filters["session_asia"](event, dataset).passed


def test_build_discovery_features_includes_v2_columns() -> None:
    dataset = build_discovery_dataset(
        data=_trend_frame(120),
        window_label="sample",
        symbol="SOL-USDT-SWAP",
    )
    row = dataset.features.iloc[-1]
    for column in (
        "ema9",
        "ema21",
        "bb_upper",
        "bb_lower",
        "bb_width_pct",
        "body_to_range",
        "bar_range_atr",
        "roc10",
        "hour_utc",
    ):
        assert column in dataset.features.columns
        assert pd.notna(row[column])
    assert "rsi14" in dataset.features.columns
    assert dataset.features["rsi14"].iloc[-1] == pytest.approx(100.0)


def test_convert_discovery_strategy_maps_selected_candidate() -> None:
    payload = {
        "name": "strategy_discovery_candidate",
        "params": {
            "discovery_schema_version": 1,
            "trigger": "h1_momentum_burst",
            "filters": [
                "avoid_low_volume",
                "block_context_reversal",
                "side_short_only",
                "trend_strength_min",
            ],
        },
        "metrics": {"win_rate": 0.5573, "passed_events": 325},
    }

    converted = convert_discovery_strategy(payload)

    assert converted["name"] == "crypt_ensemble"
    assert converted["params"]["setup_source"] == "h1_raw"
    assert converted["params"]["trigger_rules"] == ["h1_momentum_burst"]
    assert converted["params"]["allowed_sides"] == ["short"]
    assert converted["params"]["block_d1_h4_context_reversal"] is True
    assert converted["params"]["min_trend_strength_atr"] == 0.5
    assert converted["params"]["min_volume_median_ratio"] == 0.5
    assert converted["params"]["allow_atr_sl_fallback"] is True
    assert converted["discovery_source"]["candidate_id"].startswith("h1_momentum_burst")


def test_convert_discovery_strategy_maps_nr7_candidate() -> None:
    payload = {
        "name": "strategy_discovery_candidate",
        "params": {
            "discovery_schema_version": 1,
            "trigger": "h1_nr7_breakout",
            "filters": ["bb_squeeze", "h4_context_aligned"],
        },
        "metrics": {"win_rate": 0.5856, "passed_events": 222},
    }

    converted = convert_discovery_strategy(payload)

    assert converted["params"]["trigger_rules"] == ["h1_nr7_breakout"]
    assert converted["params"]["require_h4_context_aligned"] is True
    assert converted["params"]["max_bb_width_pct"] == 0.04
    assert converted["params"]["allow_atr_sl_fallback"] is True


def test_convert_discovery_strategy_maps_v3_vwap_reclaim_candidate() -> None:
    payload = {
        "name": "strategy_discovery_candidate",
        "params": {
            "discovery_schema_version": 1,
            "trigger": "h1_vwap_reclaim",
            "filters": [
                "avoid_low_volume",
                "bb_width_rank_min_low",
                "session_off_hours",
            ],
        },
        "metrics": {"win_rate": 0.5714, "passed_events": 238},
    }

    converted = convert_discovery_strategy(payload)

    assert converted["params"]["trigger_rules"] == ["h1_vwap_reclaim"]
    assert converted["params"]["min_volume_median_ratio"] == 0.5
    assert converted["params"]["min_bb_width_rank_20"] == 0.2
    assert converted["params"]["require_session_off_hours"] is True


def test_convert_discovery_strategy_maps_v3_nr4_candidate() -> None:
    payload = {
        "name": "strategy_discovery_candidate",
        "params": {
            "discovery_schema_version": 1,
            "trigger": "h1_nr4_breakout",
            "filters": [
                "avoid_doji",
                "vwap_dist_max_1pct",
                "vwap_dist_min_0_2pct",
            ],
        },
        "metrics": {"win_rate": 0.5718, "passed_events": 404},
    }

    converted = convert_discovery_strategy(payload)

    assert converted["params"]["trigger_rules"] == ["h1_nr4_breakout"]
    assert converted["params"]["min_body_to_range"] == 0.15
    assert converted["params"]["max_session_vwap_dist_pct"] == 0.01
    assert converted["params"]["min_session_vwap_dist_pct"] == 0.002


def test_convert_discovery_strategy_rejects_unsupported_filter() -> None:
    payload = {
        "name": "strategy_discovery_candidate",
        "params": {
            "discovery_schema_version": 1,
            "trigger": "h1_momentum_burst",
            "filters": ["d1_context_aligned"],
        },
    }

    with pytest.raises(DiscoveryConversionError, match="not yet supported"):
        convert_discovery_strategy(payload)


def test_convert_discovery_strategy_rejects_unsupported_trigger() -> None:
    payload = {
        "name": "strategy_discovery_candidate",
        "params": {
            "discovery_schema_version": 1,
            "trigger": "h1_range_breakout",
            "filters": [],
        },
    }

    with pytest.raises(DiscoveryConversionError, match="not yet supported"):
        convert_discovery_strategy(payload)
