from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd
from click.testing import CliRunner
from pytest import MonkeyPatch

from backtester.__main__ import cli
from backtester.data_contracts import StrategyData
from backtester.strategy_discovery.events import DiscoveryEvent
from backtester.strategy_discovery.features import DiscoveryDataset, build_discovery_dataset
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
    assert events[-1].event_time == dataset.primary.index[-1]


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

    dataset = build_discovery_dataset(
        data=StrategyData(
            primary=h1,
            candles={"H4": h4, "D1": pd.DataFrame()},
            extras={},
            metadata={},
        ),
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
            primary_timeframe="1h",
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


def test_discover_strategies_cli_writes_artifacts(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    class FakeLoader:
        pass

    def fake_build_cli_data_loader(*_args: Any, **_kwargs: Any) -> FakeLoader:
        return FakeLoader()

    def fake_load_ohlcv_via_loader(*_args: Any, **_kwargs: Any) -> pd.DataFrame:
        return _trend_frame(80)

    monkeypatch.setattr(
        "backtester.__main__.build_cli_data_loader",
        fake_build_cli_data_loader,
    )
    monkeypatch.setattr(
        "backtester.__main__.load_ohlcv_via_loader",
        fake_load_ohlcv_via_loader,
    )

    result = CliRunner().invoke(
        cli,
        [
            "discover-strategies",
            "--data-dir",
            str(tmp_path / "data"),
            "--symbol",
            "SOL-USDT-SWAP",
            "--from",
            "2025-01-01",
            "--to",
            "2025-01-04",
            "--output",
            str(tmp_path / "discovery"),
            "--min-trades-total",
            "1",
            "--min-trades-per-window",
            "1",
            "--beam-width",
            "2",
            "--max-filter-depth",
            "1",
        ],
    )

    assert result.exit_code == 0, result.output
    [output_dir] = (tmp_path / "discovery").iterdir()
    assert (output_dir / "candidates.csv").exists()
    assert (output_dir / "best_candidates").exists()


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
        primary=frame,
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
        event_time=dataset.primary.index[index],
        side=side,  # type: ignore[arg-type]
        trigger_name="test_trigger",
        entry_reference_price=entry,
        window_label=dataset.window_label,
        symbol=dataset.symbol,
        metadata={},
    )
