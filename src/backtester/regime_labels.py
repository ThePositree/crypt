"""Offline regime-label dataset utilities."""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any

import pandas as pd


def build_oracle_label_dataset(
    *,
    return_matrix: pd.DataFrame,
    ohlcv: pd.DataFrame,
    bucket: str,
) -> pd.DataFrame:
    """Build a detector-safe monthly strategy-oracle dataset.

    Labels come from same-bucket strategy returns. OHLCV features are computed
    using only candles strictly before the bucket start.
    """

    if return_matrix.empty:
        return pd.DataFrame()
    if "bucket" not in return_matrix.columns:
        raise ValueError("return_matrix must contain a bucket column")

    freq = _bucket_freq(bucket)
    matrix = return_matrix.copy()
    strategy_cols = [col for col in matrix.columns if col != "bucket"]
    if not strategy_cols:
        raise ValueError("return_matrix must contain at least one strategy column")

    candles = _standardize_ohlcv(ohlcv)
    rows: list[dict[str, Any]] = []
    for _, row in matrix.iterrows():
        bucket_id = str(row["bucket"])
        bucket_start = pd.Period(bucket_id, freq=freq).start_time.tz_localize("UTC")
        returns = pd.to_numeric(row[strategy_cols], errors="coerce").fillna(0.0)
        ranked = returns.sort_values(ascending=False)
        best_strategy = str(ranked.index[0])
        second_strategy = str(ranked.index[1]) if len(ranked) > 1 else ""
        best_return = float(ranked.iloc[0])
        second_return = float(ranked.iloc[1]) if len(ranked) > 1 else math.nan

        output: dict[str, Any] = {
            "bucket": bucket_id,
            "bucket_start": bucket_start.isoformat(),
            "best_strategy": best_strategy,
            "best_return_pct": best_return,
            "second_strategy": second_strategy,
            "second_return_pct": second_return,
            "margin_to_second_pct": (
                best_return - second_return if not math.isnan(second_return) else math.nan
            ),
            "positive_strategy_count": int((returns > 0).sum()),
            "negative_strategy_count": int((returns < 0).sum()),
            "return_dispersion_pct": float(returns.std(ddof=0)),
        }
        output.update({f"return_{col}": float(returns[col]) for col in strategy_cols})
        output.update(_ohlcv_features_asof(candles, bucket_start))
        rows.append(output)

    return pd.DataFrame(rows)


def write_oracle_label_outputs(
    *,
    output: Path,
    dataset: pd.DataFrame,
) -> None:
    """Write oracle label dataset artifacts."""

    output.mkdir(parents=True, exist_ok=True)
    dataset.to_csv(output / "oracle_labels.csv", index=False)
    _write_summary(output / "summary.md", dataset)


def build_rolling_label_dataset(
    *,
    trades_dir: Path,
    ohlcv: pd.DataFrame,
    step: str,
    horizon_days: int,
    min_history_days: int,
    start: str | None = None,
    end: str | None = None,
) -> pd.DataFrame:
    """Build rolling forward strategy labels from raw strategy trades."""

    if horizon_days <= 0:
        raise ValueError("horizon_days must be positive")
    if min_history_days < 0:
        raise ValueError("min_history_days must be >= 0")

    candles = _standardize_ohlcv(ohlcv)
    if candles.empty:
        return pd.DataFrame()
    trades_by_strategy = _load_strategy_trades(trades_dir)
    if not trades_by_strategy:
        raise ValueError(f"No strategy trade CSVs found in {trades_dir}")
    coverage_by_strategy = _load_strategy_coverage(trades_dir)

    timestamps = _rolling_timestamps(
        candles,
        step=step,
        start=start,
        end=end,
        min_history_days=min_history_days,
        horizon_days=horizon_days,
    )
    horizon = pd.Timedelta(days=horizon_days)
    rows: list[dict[str, Any]] = []
    for asof in timestamps:
        label_end = asof + horizon
        returns = {
            strategy_id: (
                _forward_trade_return_pct(trades, start=asof, end=label_end)
                if _strategy_covers_window(
                    coverage_by_strategy.get(strategy_id), start=asof, end=label_end
                )
                else math.nan
            )
            for strategy_id, trades in trades_by_strategy.items()
        }
        return_series = pd.Series(returns, dtype=float).dropna()
        if return_series.empty:
            continue
        ranked = return_series.sort_values(ascending=False)
        best_strategy = str(ranked.index[0])
        second_strategy = str(ranked.index[1]) if len(ranked) > 1 else ""
        best_return = float(ranked.iloc[0])
        second_return = float(ranked.iloc[1]) if len(ranked) > 1 else math.nan

        row: dict[str, Any] = {
            "asof": asof.isoformat(),
            "label_start": asof.isoformat(),
            "label_end": label_end.isoformat(),
            "horizon_days": horizon_days,
            "best_strategy": best_strategy,
            "best_return_pct": best_return,
            "second_strategy": second_strategy,
            "second_return_pct": second_return,
            "margin_to_second_pct": (
                best_return - second_return if not math.isnan(second_return) else math.nan
            ),
            "available_strategy_count": len(return_series),
            "positive_strategy_count": int((return_series > 0).sum()),
            "negative_strategy_count": int((return_series < 0).sum()),
            "return_dispersion_pct": float(return_series.std(ddof=0)),
        }
        row.update({f"return_{key}": float(value) for key, value in returns.items()})
        row.update(_ohlcv_features_asof(candles, asof))
        rows.append(row)

    return pd.DataFrame(rows)


def write_rolling_label_outputs(
    *,
    output: Path,
    dataset: pd.DataFrame,
    step: str,
    horizon_days: int,
) -> None:
    """Write rolling label dataset artifacts."""

    output.mkdir(parents=True, exist_ok=True)
    dataset.to_csv(output / "rolling_labels.csv", index=False)
    _write_rolling_summary(
        output / "summary.md",
        dataset=dataset,
        step=step,
        horizon_days=horizon_days,
    )


def _standardize_ohlcv(ohlcv: pd.DataFrame) -> pd.DataFrame:
    rename = {
        "open_time": "timestamp",
        "o": "open",
        "h": "high",
        "l": "low",
        "c": "close",
        "v": "volume",
    }
    df = ohlcv.rename(columns=rename).copy()
    if "timestamp" not in df.columns and isinstance(df.index, pd.DatetimeIndex):
        df = df.reset_index().rename(columns={df.index.name or "index": "timestamp"})
    required = {"timestamp", "open", "high", "low", "close", "volume"}
    missing = sorted(required.difference(df.columns))
    if missing:
        raise ValueError(f"OHLCV data missing columns: {missing}")
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
    df = df.dropna(subset=["timestamp"]).sort_values("timestamp").reset_index(drop=True)
    for col in ["open", "high", "low", "close", "volume"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    if "closed" in df.columns:
        df = df[df["closed"].fillna(False).astype(bool)]
    return df.dropna(subset=["open", "high", "low", "close"])


def _load_strategy_trades(trades_dir: Path) -> dict[str, pd.DataFrame]:
    trades_by_strategy: dict[str, pd.DataFrame] = {}
    for path in sorted(trades_dir.glob("*.csv")):
        strategy_id = path.stem
        trades = pd.read_csv(path)
        if "exit_time" in trades.columns:
            trades["exit_time"] = pd.to_datetime(trades["exit_time"], utc=True, errors="coerce")
        else:
            trades["exit_time"] = pd.NaT
        if "pnl_abs" in trades.columns:
            trades["pnl_abs"] = pd.to_numeric(trades["pnl_abs"], errors="coerce").fillna(0.0)
        else:
            trades["pnl_abs"] = 0.0
        if "capital_before" in trades.columns:
            trades["capital_before"] = pd.to_numeric(
                trades["capital_before"], errors="coerce"
            )
        else:
            trades["capital_before"] = pd.NA
        trades_by_strategy[strategy_id] = trades
    return trades_by_strategy


def _load_strategy_coverage(
    trades_dir: Path,
) -> dict[str, tuple[pd.Timestamp, pd.Timestamp]]:
    """Load optional strategy coverage windows for partial trade datasets."""

    candidates = [
        trades_dir.parent / "strategy_coverage.csv",
        trades_dir.parent / "source_trades_manifest.csv",
    ]
    path = next((candidate for candidate in candidates if candidate.exists()), None)
    if path is None:
        return {}

    raw = pd.read_csv(path)
    required = {"strategy_id", "coverage_start", "coverage_end"}
    if not required.issubset(raw.columns):
        return {}

    coverage: dict[str, tuple[pd.Timestamp, pd.Timestamp]] = {}
    for _, row in raw.iterrows():
        strategy_id = str(row["strategy_id"])
        start = pd.to_datetime(row["coverage_start"], utc=True, errors="coerce")
        end = pd.to_datetime(row["coverage_end"], utc=True, errors="coerce")
        if pd.isna(start) or pd.isna(end) or end <= start:
            continue
        coverage[strategy_id] = (start, end)
    return coverage


def _strategy_covers_window(
    coverage: tuple[pd.Timestamp, pd.Timestamp] | None,
    *,
    start: pd.Timestamp,
    end: pd.Timestamp,
) -> bool:
    if coverage is None:
        return True
    coverage_start, coverage_end = coverage
    return start >= coverage_start and end <= coverage_end


def _rolling_timestamps(
    candles: pd.DataFrame,
    *,
    step: str,
    start: str | None,
    end: str | None,
    min_history_days: int,
    horizon_days: int,
) -> list[pd.Timestamp]:
    first = candles["timestamp"].min() + pd.Timedelta(days=min_history_days)
    last = candles["timestamp"].max() - pd.Timedelta(days=horizon_days)
    if start is not None:
        first = max(first, pd.Timestamp(start, tz="UTC"))
    if end is not None:
        last = min(last, pd.Timestamp(end, tz="UTC"))
    if last < first:
        return []

    normalized = step.lower()
    if normalized == "day":
        start_ts = first.ceil("D")
        return pd.date_range(start=start_ts, end=last, freq="D", tz="UTC").to_list()
    if normalized == "hour":
        start_ts = first.ceil("h")
        return pd.date_range(start=start_ts, end=last, freq="h", tz="UTC").to_list()
    raise ValueError(f"Unsupported step: {step}")


def _forward_trade_return_pct(
    trades: pd.DataFrame, *, start: pd.Timestamp, end: pd.Timestamp
) -> float:
    if trades.empty or "exit_time" not in trades.columns:
        return 0.0
    window = trades[(trades["exit_time"] >= start) & (trades["exit_time"] < end)]
    if window.empty:
        return 0.0
    pnl = float(pd.to_numeric(window["pnl_abs"], errors="coerce").fillna(0.0).sum())
    capital = _forward_start_capital(trades, start=start)
    return pnl / capital * 100.0 if capital > 0 else 0.0


def _forward_start_capital(trades: pd.DataFrame, *, start: pd.Timestamp) -> float:
    if "capital_before" not in trades.columns or "exit_time" not in trades.columns:
        return 10_000.0
    before = trades[trades["exit_time"] >= start].sort_values("exit_time")
    capital = pd.to_numeric(before["capital_before"], errors="coerce").dropna()
    if capital.empty:
        all_capital = pd.to_numeric(trades["capital_before"], errors="coerce").dropna()
        return float(all_capital.iloc[-1]) if not all_capital.empty else 10_000.0
    return float(capital.iloc[0])


def _ohlcv_features_asof(candles: pd.DataFrame, asof: pd.Timestamp) -> dict[str, float | int]:
    hist = candles[candles["timestamp"] < asof].copy()
    if hist.empty:
        return _empty_features(0)

    close = hist["close"]
    high = hist["high"]
    low = hist["low"]
    volume = hist["volume"].fillna(0.0)
    returns = close.pct_change()
    atr_pct = _atr_pct(hist)
    current_close = float(close.iloc[-1])

    features: dict[str, float | int] = {
        "feature_bar_count": len(hist),
        "feature_close": current_close,
        "ret_7d_pct": _trailing_return_pct(close, 24 * 7),
        "ret_30d_pct": _trailing_return_pct(close, 24 * 30),
        "ret_90d_pct": _trailing_return_pct(close, 24 * 90),
        "realized_vol_30d_pct": _realized_vol_pct(returns, 24 * 30),
        "realized_vol_90d_pct": _realized_vol_pct(returns, 24 * 90),
        "atr14_pct": _last_valid_float(atr_pct),
        "atr14_pct_rank_180d": _last_percentile_rank(atr_pct, 24 * 180),
        "bb_width20_pct": _bb_width_pct(close, 20),
        "volume_ratio_30d": _last_vs_mean(volume, 24 * 30),
        "volume_percentile_90d": _last_percentile_rank(volume, 24 * 90),
        "close_vs_sma50_pct": _close_vs_sma_pct(close, 50),
        "close_vs_sma200_pct": _close_vs_sma_pct(close, 200),
        "sma50_slope_30d_pct": _sma_slope_pct(close, 50, 24 * 30),
        "donchian_position_90d": _donchian_position(close, high, low, 24 * 90),
        "trend_efficiency_30d": _trend_efficiency(close, 24 * 30),
        "choppiness_30d": _choppiness(hist, 24 * 30),
    }
    return features


def _empty_features(bar_count: int) -> dict[str, float | int]:
    keys = [
        "feature_close",
        "ret_7d_pct",
        "ret_30d_pct",
        "ret_90d_pct",
        "realized_vol_30d_pct",
        "realized_vol_90d_pct",
        "atr14_pct",
        "atr14_pct_rank_180d",
        "bb_width20_pct",
        "volume_ratio_30d",
        "volume_percentile_90d",
        "close_vs_sma50_pct",
        "close_vs_sma200_pct",
        "sma50_slope_30d_pct",
        "donchian_position_90d",
        "trend_efficiency_30d",
        "choppiness_30d",
    ]
    values: dict[str, float | int] = {"feature_bar_count": bar_count}
    values.update(dict.fromkeys(keys, math.nan))
    return values


def _atr_pct(df: pd.DataFrame, period: int = 14) -> pd.Series:
    high = df["high"]
    low = df["low"]
    close = df["close"]
    prev_close = close.shift(1)
    tr = pd.concat(
        [
            high - low,
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    atr = tr.rolling(period, min_periods=period).mean()
    return atr / close * 100.0


def _trailing_return_pct(close: pd.Series, bars: int) -> float:
    if len(close) <= bars:
        return math.nan
    previous = float(close.iloc[-bars - 1])
    current = float(close.iloc[-1])
    if previous == 0:
        return math.nan
    return (current / previous - 1.0) * 100.0


def _realized_vol_pct(returns: pd.Series, bars: int) -> float:
    window = returns.dropna().tail(bars)
    if len(window) < 2:
        return math.nan
    return float(window.std(ddof=0) * math.sqrt(24 * 30) * 100.0)


def _bb_width_pct(close: pd.Series, period: int) -> float:
    if len(close) < period:
        return math.nan
    window = close.tail(period)
    mean = float(window.mean())
    if mean == 0:
        return math.nan
    std = float(window.std(ddof=0))
    return (4.0 * std / mean) * 100.0


def _last_vs_mean(series: pd.Series, bars: int) -> float:
    window = series.dropna().tail(bars)
    if len(window) < 2:
        return math.nan
    mean = float(window.iloc[:-1].mean())
    if mean == 0:
        return math.nan
    return float(window.iloc[-1]) / mean


def _last_percentile_rank(series: pd.Series, bars: int) -> float:
    window = series.dropna().tail(bars)
    if window.empty:
        return math.nan
    current = float(window.iloc[-1])
    return float((window <= current).mean())


def _last_valid_float(series: pd.Series) -> float:
    valid = series.dropna()
    if valid.empty:
        return math.nan
    return float(valid.iloc[-1])


def _close_vs_sma_pct(close: pd.Series, period: int) -> float:
    if len(close) < period:
        return math.nan
    sma = float(close.tail(period).mean())
    if sma == 0:
        return math.nan
    return (float(close.iloc[-1]) / sma - 1.0) * 100.0


def _sma_slope_pct(close: pd.Series, period: int, bars: int) -> float:
    sma = close.rolling(period, min_periods=period).mean().dropna()
    if len(sma) <= bars:
        return math.nan
    previous = float(sma.iloc[-bars - 1])
    current = float(sma.iloc[-1])
    if previous == 0:
        return math.nan
    return (current / previous - 1.0) * 100.0


def _donchian_position(
    close: pd.Series, high: pd.Series, low: pd.Series, bars: int
) -> float:
    if len(close) < bars:
        return math.nan
    highest = float(high.tail(bars).max())
    lowest = float(low.tail(bars).min())
    width = highest - lowest
    if width == 0:
        return math.nan
    return (float(close.iloc[-1]) - lowest) / width


def _trend_efficiency(close: pd.Series, bars: int) -> float:
    if len(close) <= bars:
        return math.nan
    window = close.tail(bars + 1)
    net = abs(float(window.iloc[-1]) - float(window.iloc[0]))
    path = float(window.diff().abs().sum())
    if path == 0:
        return math.nan
    return net / path


def _choppiness(df: pd.DataFrame, bars: int) -> float:
    if len(df) < bars + 1:
        return math.nan
    window = df.tail(bars + 1)
    tr = pd.concat(
        [
            window["high"] - window["low"],
            (window["high"] - window["close"].shift(1)).abs(),
            (window["low"] - window["close"].shift(1)).abs(),
        ],
        axis=1,
    ).max(axis=1)
    tr_sum = float(tr.tail(bars).sum())
    high_max = float(window["high"].tail(bars).max())
    low_min = float(window["low"].tail(bars).min())
    denominator = high_max - low_min
    if denominator <= 0 or tr_sum <= 0:
        return math.nan
    return 100.0 * math.log10(tr_sum / denominator) / math.log10(bars)


def _bucket_freq(bucket: str) -> str:
    normalized = bucket.lower()
    if normalized == "day":
        return "D"
    if normalized == "week":
        return "W"
    if normalized == "month":
        return "M"
    raise ValueError(f"Unsupported bucket: {bucket}")


def _write_summary(path: Path, dataset: pd.DataFrame) -> None:
    if dataset.empty:
        path.write_text("# Oracle Regime Labels\n\nNo rows.\n", encoding="utf-8")
        return

    counts = dataset["best_strategy"].value_counts()
    losing = int((dataset["best_return_pct"] < 0).sum())
    avg_margin = float(dataset["margin_to_second_pct"].mean())
    lines = [
        "# Oracle Regime Labels",
        "",
        f"Buckets: **{len(dataset)}**",
        f"Strategies selected: **{len(counts)}**",
        f"Losing oracle buckets: **{losing}**",
        f"Average margin to second: **{avg_margin:.4f}%**",
        "",
        "## Selection Counts",
        "",
        "| strategy | buckets |",
        "| --- | ---: |",
    ]
    lines.extend(f"| `{strategy}` | {count} |" for strategy, count in counts.items())
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def _write_rolling_summary(
    path: Path,
    *,
    dataset: pd.DataFrame,
    step: str,
    horizon_days: int,
) -> None:
    if dataset.empty:
        path.write_text("# Rolling Regime Labels\n\nNo rows.\n", encoding="utf-8")
        return

    counts = dataset["best_strategy"].value_counts()
    losing = int((dataset["best_return_pct"] < 0).sum())
    avg_margin = float(dataset["margin_to_second_pct"].mean())
    lines = [
        "# Rolling Regime Labels",
        "",
        f"Rows: **{len(dataset)}**",
        f"Step: **{step}**",
        f"Horizon: **{horizon_days}d**",
        f"Strategies selected: **{len(counts)}**",
        f"Losing oracle rows: **{losing}**",
        f"Average margin to second: **{avg_margin:.4f}%**",
        "",
        "## Selection Counts",
        "",
        "| strategy | rows |",
        "| --- | ---: |",
    ]
    lines.extend(f"| `{strategy}` | {count} |" for strategy, count in counts.items())
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")
