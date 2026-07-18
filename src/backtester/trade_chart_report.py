from __future__ import annotations

import json
from dataclasses import dataclass
from html import escape
from pathlib import Path
from typing import Any

import pandas as pd


@dataclass(frozen=True)
class TradeChartReportConfig:
    run_dir: Path
    output_path: Path | None = None
    ohlcv_path: Path | None = None
    ohlcv_df: pd.DataFrame | None = None
    timestamp_col: str = "timestamp"
    title: str | None = None


def build_trade_chart_report(config: TradeChartReportConfig) -> Path:
    """Build a TradingView Lightweight Charts HTML report from a backtester run."""
    run_dir = config.run_dir
    trades_path = run_dir / "trades.csv"
    if not trades_path.exists():
        raise FileNotFoundError(f"Missing trades.csv in run directory: {run_dir}")

    trades = _read_trades(trades_path)
    candles = _read_candles(config)
    metrics = _read_optional_csv(run_dir / "metrics.csv")
    signals = _read_optional_csv(run_dir / "signals.csv")
    signal_diagnostics = _read_optional_csv(run_dir / "signal_diagnostics.csv")
    trade_diagnostics = _read_optional_csv(run_dir / "trade_diagnostics.csv")

    title = config.title or f"Backtest chart: {run_dir.name}"
    output_path = config.output_path or (run_dir / "trade_chart.html")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        _render_html(
            title=title,
            run_dir=run_dir,
            candles=candles,
            trades=trades,
            signals=signals,
            metrics=metrics,
            trade_diagnostics=trade_diagnostics,
            signal_diagnostics=signal_diagnostics,
        ),
        encoding="utf-8",
    )
    return output_path


def _read_trades(path: Path) -> pd.DataFrame:
    trades = pd.read_csv(path)
    for col in ("entry_time", "exit_time", "signal_time"):
        if col in trades.columns:
            trades[col] = pd.to_datetime(trades[col], utc=True, errors="coerce")
    if trades.empty:
        return trades

    required = {"entry_time", "exit_time", "entry_price", "exit_price", "is_long"}
    missing = sorted(required - set(trades.columns))
    if missing:
        raise ValueError(f"trades.csv missing required columns: {', '.join(missing)}")
    return trades


def _read_candles(config: TradeChartReportConfig) -> pd.DataFrame:
    if config.ohlcv_df is not None:
        return _standardize_ohlcv(config.ohlcv_df, timestamp_col=config.timestamp_col)
    if config.ohlcv_path is not None:
        return _read_ohlcv_path(config.ohlcv_path, timestamp_col=config.timestamp_col)

    full_candles_path = config.run_dir / "ohlcv.csv"
    if full_candles_path.exists():
        return _read_ohlcv_path(full_candles_path, timestamp_col=config.timestamp_col)

    candles_dir = config.run_dir / "trade_candles"
    if not candles_dir.exists():
        raise FileNotFoundError(
            "Missing OHLCV input. Pass --ohlcv, or use a run directory with ohlcv.csv."
        )

    frames = [
        _read_ohlcv_path(path, timestamp_col=config.timestamp_col)
        for path in sorted(candles_dir.glob("trade_*.csv"))
    ]
    if not frames:
        raise FileNotFoundError(f"No candle files found in {candles_dir}")
    candles = pd.concat(frames).sort_index()
    candles = candles[~candles.index.duplicated(keep="last")]
    return _validate_ohlcv(candles)


def _read_ohlcv_path(path: Path, *, timestamp_col: str) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"OHLCV file does not exist: {path}")
    frame = pd.read_parquet(path) if path.suffix.lower() == ".parquet" else pd.read_csv(path)
    return _standardize_ohlcv(frame, timestamp_col=timestamp_col)


def _standardize_ohlcv(frame: pd.DataFrame, *, timestamp_col: str) -> pd.DataFrame:
    df = frame.copy()
    if isinstance(df.index, pd.DatetimeIndex):
        df.index = pd.to_datetime(df.index, utc=True)
    else:
        candidate = timestamp_col if timestamp_col in df.columns else None
        if candidate is None:
            for col in ("timestamp", "open_time", "time", "date"):
                if col in df.columns:
                    candidate = col
                    break
        if candidate is None:
            raise ValueError("OHLCV data must have a DatetimeIndex or timestamp column")
        df[candidate] = pd.to_datetime(df[candidate], utc=True, errors="coerce")
        df = df.dropna(subset=[candidate]).set_index(candidate)

    rename = {
        "Open": "open",
        "High": "high",
        "Low": "low",
        "Close": "close",
        "Volume": "volume",
    }
    df = df.rename(columns={k: v for k, v in rename.items() if k in df.columns})
    df = df.sort_index()
    df = df[~df.index.duplicated(keep="last")]
    return _validate_ohlcv(df)


def _validate_ohlcv(df: pd.DataFrame) -> pd.DataFrame:
    required = ["open", "high", "low", "close"]
    missing = [col for col in required if col not in df.columns]
    if missing:
        raise ValueError(f"OHLCV data missing required columns: {', '.join(missing)}")
    result = df[required + (["volume"] if "volume" in df.columns else [])].copy()
    for col in required:
        result[col] = pd.to_numeric(result[col], errors="coerce")
    result = result.dropna(subset=required)
    if result.empty:
        raise ValueError("OHLCV data has no valid candle rows")
    return result


def _read_optional_csv(path: Path) -> pd.DataFrame:
    if not path.exists() or path.stat().st_size == 0:
        return pd.DataFrame()
    return pd.read_csv(path)


def _render_html(
    *,
    title: str,
    run_dir: Path,
    candles: pd.DataFrame,
    trades: pd.DataFrame,
    signals: pd.DataFrame,
    metrics: pd.DataFrame,
    trade_diagnostics: pd.DataFrame,
    signal_diagnostics: pd.DataFrame,
) -> str:
    payload = {
        "candles": _candles_payload(candles),
        "markers": _markers_payload(trades, signals),
        "levels": _levels_payload(trades),
    }
    payload_json = json.dumps(payload, ensure_ascii=False, allow_nan=False)
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escape(title)}</title>
  <script src="https://unpkg.com/lightweight-charts@5.2.0/dist/lightweight-charts.standalone.production.js"></script>
  <style>
    :root {{
      color-scheme: light;
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      color: #101828;
      background: #f8fafc;
    }}
    body {{ margin: 0; }}
    header {{
      display: flex;
      justify-content: space-between;
      gap: 16px;
      align-items: flex-start;
      padding: 14px 18px;
      border-bottom: 1px solid #d0d5dd;
      background: #ffffff;
    }}
    h1 {{ font-size: 18px; line-height: 1.25; margin: 0 0 4px; }}
    .muted {{ color: #667085; font-size: 12px; margin: 0; word-break: break-all; }}
    .summary {{ display: flex; gap: 10px; flex-wrap: wrap; justify-content: flex-end; }}
    .pill {{
      border: 1px solid #d0d5dd;
      border-radius: 999px;
      padding: 4px 9px;
      background: #ffffff;
      font-size: 12px;
      white-space: nowrap;
    }}
    #chart-wrap {{ height: min(72vh, 860px); min-height: 520px; background: #ffffff; }}
    #chart {{ width: 100%; height: 100%; }}
    main {{ padding: 12px 18px 24px; }}
    .legend {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px 14px;
      font-size: 12px;
      color: #344054;
      margin-bottom: 10px;
    }}
    .swatch {{ display: inline-block; width: 18px; height: 3px; vertical-align: middle; margin-right: 5px; }}
    details {{
      border: 1px solid #d0d5dd;
      border-radius: 6px;
      padding: 10px 12px;
      margin: 10px 0;
      background: #ffffff;
    }}
    summary {{ cursor: pointer; font-weight: 650; }}
    table {{ border-collapse: collapse; width: 100%; font-size: 12px; margin-top: 10px; }}
    th, td {{ border: 1px solid #eaecf0; padding: 5px 7px; text-align: left; vertical-align: top; }}
    th {{ background: #f9fafb; position: sticky; top: 0; }}
    .table-scroll {{ max-height: 360px; overflow: auto; }}
    @media (max-width: 760px) {{
      header {{ display: block; }}
      .summary {{ justify-content: flex-start; margin-top: 10px; }}
      #chart-wrap {{ height: 72vh; min-height: 420px; }}
    }}
  </style>
</head>
<body>
  <header>
    <div>
      <h1>{escape(title)}</h1>
      <p class="muted">{escape(str(run_dir))}</p>
    </div>
    <div class="summary">{_metric_pills(metrics, trades)}</div>
  </header>
  <div id="chart-wrap"><div id="chart"></div></div>
  <main>
    <div class="legend">
      <span><span class="swatch" style="background:#2962ff"></span>Entry level</span>
      <span><span class="swatch" style="background:#039855"></span>Take profit</span>
      <span><span class="swatch" style="background:#d92d20"></span>Stop loss</span>
      <span><span class="swatch" style="background:#f79009"></span>Trailing stop</span>
    </div>
    {_details_table("Metrics", metrics)}
    {_details_table("Trade Diagnostics", trade_diagnostics)}
    {_details_table("Signal Diagnostics", signal_diagnostics)}
    {_details_table("Trades", trades)}
  </main>
  <script>
    const report = {payload_json};
    const container = document.getElementById('chart');
    const chart = LightweightCharts.createChart(container, {{
      autoSize: true,
      layout: {{ background: {{ color: '#ffffff' }}, textColor: '#344054' }},
      grid: {{ vertLines: {{ color: '#eef2f6' }}, horzLines: {{ color: '#eef2f6' }} }},
      crosshair: {{ mode: LightweightCharts.CrosshairMode.Normal }},
      rightPriceScale: {{ borderColor: '#d0d5dd', scaleMargins: {{ top: 0.08, bottom: 0.12 }} }},
      timeScale: {{
        borderColor: '#d0d5dd',
        timeVisible: true,
        secondsVisible: false,
        rightOffset: 8,
        barSpacing: 8
      }},
    }});
    const candleSeries = chart.addSeries(LightweightCharts.CandlestickSeries, {{
      upColor: '#16a34a',
      downColor: '#dc2626',
      wickUpColor: '#16a34a',
      wickDownColor: '#dc2626',
      borderVisible: false,
    }});
    candleSeries.setData(report.candles);
    LightweightCharts.createSeriesMarkers(candleSeries, report.markers);

    const lineOptions = {{
      entry: {{ color: '#2962ff', lineWidth: 1, lineStyle: LightweightCharts.LineStyle.Solid }},
      tp: {{ color: '#039855', lineWidth: 1, lineStyle: LightweightCharts.LineStyle.Dotted }},
      sl: {{ color: '#d92d20', lineWidth: 1, lineStyle: LightweightCharts.LineStyle.Dashed }},
      trail: {{ color: '#f79009', lineWidth: 1, lineStyle: LightweightCharts.LineStyle.LargeDashed }},
    }};
    for (const level of report.levels) {{
      const series = chart.addSeries(LightweightCharts.LineSeries, {{
        ...lineOptions[level.kind],
        priceLineVisible: false,
        lastValueVisible: false,
        crosshairMarkerVisible: false,
      }});
      series.setData(level.data);
    }}
    chart.timeScale().fitContent();
  </script>
</body>
</html>
"""


def _candles_payload(candles: pd.DataFrame) -> list[dict[str, int | float]]:
    return [
        {
            "time": _to_unix_seconds(index),
            "open": float(row["open"]),
            "high": float(row["high"]),
            "low": float(row["low"]),
            "close": float(row["close"]),
        }
        for index, row in candles.iterrows()
    ]


def _markers_payload(trades: pd.DataFrame, signals: pd.DataFrame) -> list[dict[str, Any]]:
    markers: list[dict[str, Any]] = []
    if not signals.empty:
        markers.extend(_signal_markers(signals))
    if not trades.empty:
        markers.extend(_trade_markers(trades))
    return sorted(markers, key=lambda item: int(item["time"]))


def _signal_markers(signals: pd.DataFrame) -> list[dict[str, Any]]:
    df = signals.copy()
    time_col = _time_column(df)
    if time_col is None or "signal" not in df.columns:
        return []
    df[time_col] = pd.to_datetime(df[time_col], utc=True, errors="coerce")
    df["signal"] = pd.to_numeric(df["signal"], errors="coerce")
    tradeable = df[df["signal"].isin([1, -1])].dropna(subset=[time_col])
    markers = []
    for _, row in tradeable.iterrows():
        is_long = int(row["signal"]) == 1
        markers.append(
            {
                "time": _to_unix_seconds(row[time_col]),
                "position": "belowBar" if is_long else "aboveBar",
                "color": "#7c3aed",
                "shape": "circle",
                "text": f"S {'L' if is_long else 'S'} {_fmt(row.get('confidence'))}",
            }
        )
    return markers


def _trade_markers(trades: pd.DataFrame) -> list[dict[str, Any]]:
    markers: list[dict[str, Any]] = []
    for _, row in trades.iterrows():
        is_long = _truthy(row.get("is_long"))
        entry_time = row.get("entry_time")
        exit_time = row.get("exit_time")
        if pd.notna(entry_time):
            markers.append(
                {
                    "time": _to_unix_seconds(entry_time),
                    "position": "belowBar" if is_long else "aboveBar",
                    "color": "#2962ff",
                    "shape": "arrowUp" if is_long else "arrowDown",
                    "text": f"E {_fmt(row.get('entry_price'))}",
                }
            )
        if pd.notna(exit_time):
            markers.append(
                {
                    "time": _to_unix_seconds(exit_time),
                    "position": "aboveBar" if is_long else "belowBar",
                    "color": _exit_color(row.get("exit_reason")),
                    "shape": "square",
                    "text": f"X {_fmt(row.get('exit_price'))} {row.get('exit_reason', '')}",
                }
            )
    return markers


def _levels_payload(trades: pd.DataFrame) -> list[dict[str, Any]]:
    if trades.empty:
        return []
    levels: list[dict[str, Any]] = []
    for _, row in trades.iterrows():
        entry_time = row.get("entry_time")
        exit_time = row.get("exit_time")
        if pd.isna(entry_time) or pd.isna(exit_time):
            continue
        levels.extend(
            _level_segment(
                kind=kind, entry_time=entry_time, exit_time=exit_time, value=row.get(col)
            )
            for kind, col in (
                ("entry", "entry_price"),
                ("tp", "tp_price"),
                ("sl", "sl_price"),
                ("trail", "trail_stop_price"),
            )
        )
    return [level for level in levels if level]


def _level_segment(*, kind: str, entry_time: Any, exit_time: Any, value: Any) -> dict[str, Any]:
    price = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
    if pd.isna(price):
        return {}
    return {
        "kind": kind,
        "data": [
            {"time": _to_unix_seconds(entry_time), "value": float(price)},
            {"time": _to_unix_seconds(exit_time), "value": float(price)},
        ],
    }


def _time_column(df: pd.DataFrame) -> str | None:
    for col in ("timestamp", "time", "tick_time", "open_time", "Unnamed: 0"):
        if col in df.columns:
            return col
    return None


def _to_unix_seconds(value: Any) -> int:
    ts = pd.Timestamp(value)
    ts = ts.tz_localize("UTC") if ts.tzinfo is None else ts.tz_convert("UTC")
    return int(ts.timestamp())


def _exit_color(reason: Any) -> str:
    if reason == "take_profit":
        return "#039855"
    if reason == "stop_loss":
        return "#d92d20"
    if reason == "trailing_stop":
        return "#f79009"
    return "#475467"


def _fmt(value: Any) -> str:
    numeric = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
    if pd.isna(numeric):
        return ""
    return f"{float(numeric):.4g}"


def _metric_pills(metrics: pd.DataFrame, trades: pd.DataFrame) -> str:
    row = metrics.iloc[0].to_dict() if not metrics.empty else {}
    values = [
        ("Trades", len(trades)),
        ("Return", row.get("total_return_pct", "n/a")),
        ("PF", row.get("profit_factor", "n/a")),
        ("Max DD", row.get("max_drawdown", "n/a")),
    ]
    return "".join(
        f'<span class="pill">{escape(label)}: {escape(str(value))}</span>'
        for label, value in values
    )


def _details_table(title: str, df: pd.DataFrame) -> str:
    if df.empty:
        return f"<details><summary>{escape(title)}</summary><p>No data.</p></details>"
    table = df.head(500).to_html(index=False, escape=True)
    return (
        f"<details><summary>{escape(title)} ({len(df)} rows)</summary>"
        f'<div class="table-scroll">{table}</div>'
        "</details>"
    )


def _truthy(value: Any) -> bool:
    if isinstance(value, str):
        return value.strip().lower() in {"true", "1", "long"}
    return bool(value)
