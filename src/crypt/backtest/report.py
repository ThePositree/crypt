"""
HTML report generator for the backtest harness — docs/backtest.md §12.

Produces a single static summary.html with embedded PNG charts.
No server required.
"""

from __future__ import annotations

import base64
import io
import json
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

# ---------------------------------------------------------------------------
# Chart helpers (matplotlib only imported here — optional dep)
# ---------------------------------------------------------------------------


def _fig_to_b64(fig: Any) -> str:
    """Encode a matplotlib Figure to a base64 PNG string."""
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=100, bbox_inches="tight")
    buf.seek(0)
    return base64.b64encode(buf.read()).decode("ascii")


def _equity_curve_chart(
    trades_df: pd.DataFrame,
    title: str,
) -> str | None:
    """Return base64 PNG of the equity curve, or None if matplotlib is unavailable."""
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return None

    if trades_df.empty:
        return None

    from crypt.backtest.metrics import build_equity_curve

    df = trades_df.copy()
    df["exit_time"] = pd.to_datetime(df["exit_time"], utc=True)
    df["entry_time"] = pd.to_datetime(df["entry_time"], utc=True)

    try:
        equity, initial, _final, _ = build_equity_curve(df)
    except Exception:
        return None

    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(equity.index, equity.values, linewidth=1.5)
    ax.axhline(initial, color="grey", linestyle="--", linewidth=0.8)
    ax.set_title(title)
    ax.set_xlabel("Date")
    ax.set_ylabel("Capital ($)")
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    b64 = _fig_to_b64(fig)
    plt.close(fig)
    return b64


def _per_symbol_equity_charts(
    trades_df: pd.DataFrame,
    fold_label: str,
) -> dict[str, str]:
    """Return {symbol: b64_png} for each symbol's equity curve."""
    charts: dict[str, str] = {}
    if trades_df.empty or "symbol" not in trades_df.columns:
        return charts
    for sym in trades_df["symbol"].unique():
        sub = trades_df[trades_df["symbol"] == sym]
        b64 = _equity_curve_chart(sub, f"{sym} — {fold_label}")
        if b64:
            charts[sym] = b64
    return charts


def _monthly_return_chart(monthly_returns: dict[str, dict[str, float]], title: str) -> str | None:
    """Bar chart of MoM returns."""
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return None

    if not monthly_returns:
        return None

    months = list(monthly_returns.keys())
    rets = [v["ret"] for v in monthly_returns.values()]
    colors = ["#2ecc71" if r >= 0 else "#e74c3c" for r in rets]

    fig, ax = plt.subplots(figsize=(12, 4))
    ax.bar(months, rets, color=colors, edgecolor="white", linewidth=0.5)
    ax.axhline(0, color="black", linewidth=0.8)
    ax.set_title(title)
    ax.set_xlabel("Month")
    ax.set_ylabel("Return (%)")
    plt.xticks(rotation=45, ha="right")
    ax.grid(True, alpha=0.3, axis="y")
    fig.tight_layout()
    b64 = _fig_to_b64(fig)
    plt.close(fig)
    return b64


# ---------------------------------------------------------------------------
# HTML building blocks
# ---------------------------------------------------------------------------


def _img_tag(b64: str | None, alt: str = "chart") -> str:
    if not b64:
        return "<p><em>Chart not available (matplotlib not installed)</em></p>"
    return f'<img src="data:image/png;base64,{b64}" alt="{alt}" style="max-width:100%;"/>'


def _badge(text: str, color: str = "#3498db") -> str:
    return f'<span style="background:{color};color:white;padding:2px 8px;border-radius:4px;font-size:0.85em;">{text}</span>'


def _metric_row(label: str, value: Any, warn: bool = False) -> str:
    color = "#c0392b" if warn else "inherit"
    return f"<tr><td><b>{label}</b></td><td style='color:{color}'>{value}</td></tr>"


def _metrics_table(metrics: dict[str, Any]) -> str:
    rows = []
    ci = metrics.get("expectancy_ci_95", (None, None))
    sig = metrics.get("expectancy_significant", False)
    ci_str = f"({ci[0]:.4f}, {ci[1]:.4f})" if ci and ci[0] is not None else "N/A"
    not_sig_badge = "" if sig else _badge("NOT SIGNIFICANT", "#e74c3c")

    rows.append(_metric_row("Total trades", metrics.get("total_trades", "N/A")))
    rows.append(_metric_row("Win rate", f"{metrics.get('win_rate', 0):.1f}%"))
    rows.append(_metric_row("Profit factor", metrics.get("profit_factor", "N/A")))
    rows.append(
        _metric_row(
            "Expectancy (rel)",
            f"{metrics.get('expectancy_rel_mean', 0):.4f} 95%CI {ci_str} {not_sig_badge}",
            warn=not sig,
        )
    )
    rows.append(_metric_row("Total return", f"{metrics.get('total_return_pct', 0):.2f}%"))
    rows.append(_metric_row("Max drawdown", f"{metrics.get('max_drawdown', 0):.2f}%"))
    rows.append(
        _metric_row(
            "Sharpe (annualised)",
            f"{metrics.get('sharpe_ratio', 0):.3f}"
            + (f" — {metrics['sharpe_warning']}" if metrics.get("sharpe_warning") else ""),
            warn=bool(metrics.get("sharpe_warning")),
        )
    )
    rows.append(_metric_row("Trade-level Sharpe", f"{metrics.get('trade_level_sharpe', 0):.3f}"))
    rows.append(_metric_row("Avg holding (bars)", metrics.get("avg_holding_bars", "N/A")))

    # Hit rates
    if "hit_rate_h24" in metrics:
        rows.append(_metric_row("Hit rate H4", f"{metrics.get('hit_rate_h4', 0):.1%}"))
        rows.append(_metric_row("Hit rate H24 (headline)", f"{metrics.get('hit_rate_h24', 0):.1%}"))
        rows.append(_metric_row("Hit rate H96", f"{metrics.get('hit_rate_h96', 0):.1%}"))

    return (
        "<table border='1' cellpadding='6' cellspacing='0' style='border-collapse:collapse;width:100%;'>"
        + "".join(rows)
        + "</table>"
    )


def _exit_dist_table(exit_dist: dict[str, int]) -> str:
    if not exit_dist:
        return "<p>No exit data.</p>"
    total = sum(exit_dist.values())
    rows = "".join(
        f"<tr><td>{reason}</td><td>{count}</td><td>{count / total:.1%}</td></tr>"
        for reason, count in sorted(exit_dist.items())
    )
    return (
        "<table border='1' cellpadding='6' cellspacing='0' style='border-collapse:collapse'>"
        "<tr><th>Exit reason</th><th>Count</th><th>%</th></tr>" + rows + "</table>"
    )


def _long_short_table(long_m: dict[str, Any], short_m: dict[str, Any]) -> str:
    def _row(name: str, lv: Any, sv: Any) -> str:
        return f"<tr><td><b>{name}</b></td><td>{lv}</td><td>{sv}</td></tr>"

    rows = [
        "<tr><th>Metric</th><th>Long</th><th>Short</th></tr>",
        _row("Count", long_m.get("count", 0), short_m.get("count", 0)),
        _row("Win rate", f"{long_m.get('win_rate', 0):.1f}%", f"{short_m.get('win_rate', 0):.1f}%"),
        _row("Total PnL", long_m.get("total_pnl", 0), short_m.get("total_pnl", 0)),
        _row("Avg PnL", long_m.get("avg_pnl", 0), short_m.get("avg_pnl", 0)),
        _row(
            "Profit factor", long_m.get("profit_factor", "inf"), short_m.get("profit_factor", "inf")
        ),
    ]
    return (
        "<table border='1' cellpadding='6' cellspacing='0' style='border-collapse:collapse;width:100%;'>"
        + "".join(rows)
        + "</table>"
    )


def _monthly_table(monthly: dict[str, dict[str, float]]) -> str:
    if not monthly:
        return "<p>No monthly data.</p>"
    rows = ["<tr><th>Month</th><th>MoM (%)</th><th>Cumulative (%)</th></tr>"]
    for month, vals in sorted(monthly.items()):
        ret = vals.get("ret", 0)
        ret_abs = vals.get("ret_abs", 0)
        color = "#2ecc71" if ret >= 0 else "#e74c3c"
        sign = "+" if ret >= 0 else ""
        rows.append(
            f"<tr><td>{month}</td><td style='color:{color}'>{sign}{ret:.2f}%</td><td>{ret_abs:.2f}%</td></tr>"
        )
    return (
        "<table border='1' cellpadding='6' cellspacing='0' style='border-collapse:collapse'>"
        + "".join(rows)
        + "</table>"
    )


def _baseline_table(baselines: dict[str, Any]) -> str:
    rows = [
        "<tr><th>Baseline</th><th>Total return (%)</th><th>Max drawdown (%)</th><th>Note</th></tr>"
    ]
    for name, vals in baselines.items():
        rows.append(
            f"<tr><td>{name}</td>"
            f"<td>{vals.get('total_return_pct', 'N/A')}</td>"
            f"<td>{vals.get('max_drawdown', 'N/A')}</td>"
            f"<td>{vals.get('note', '')}</td>"
            f"</tr>"
        )
    return (
        "<table border='1' cellpadding='6' cellspacing='0' style='border-collapse:collapse;width:100%;'>"
        + "".join(rows)
        + "</table>"
    )


# ---------------------------------------------------------------------------
# Top-level report builder
# ---------------------------------------------------------------------------


def build_report(
    *,
    meta: dict[str, Any],
    fold_results: list[dict[str, Any]],
    aggregate_metrics: dict[str, Any],
    baselines: dict[str, Any],
    recommended_weights: dict[str, Any],
    guard_violations: list[str],
) -> str:
    """
    Build and return the full HTML report as a string.

    Parameters
    ----------
    meta : dict
        Run metadata (git_sha, weights_sha, dataset window, etc.).
    fold_results : list[dict]
        Per-fold results; each dict has keys: fold_index, trades_df,
        metrics, labelled_verdicts, equity_charts.
    aggregate_metrics : dict
        Aggregated metrics across all test slices.
    baselines : dict
        Baseline comparison results (buy-and-hold, always-hold, random).
    recommended_weights : dict
        Median-across-folds weights (§13).
    guard_violations : list[str]
        Non-empty if optimizer sanity guard fired.
    """
    now_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

    # Aggregate metrics section
    agg_table = _metrics_table(aggregate_metrics)

    # Per-fold sections
    fold_sections = []
    for fr in fold_results:
        fi = fr.get("fold_index", "?")
        metrics = fr.get("metrics", {})
        m_table = _metrics_table(metrics)
        exit_table = _exit_dist_table(metrics.get("exit_distribution", {}))
        ls_table = _long_short_table(
            metrics.get("long_metrics", {}), metrics.get("short_metrics", {})
        )
        monthly_table = _monthly_table(metrics.get("monthly_returns_pct", {}))
        monthly_chart = _monthly_return_chart(
            metrics.get("monthly_returns_pct", {}),
            f"Fold {fi} — Monthly Returns",
        )
        eq_charts = fr.get("equity_charts", {})

        equity_html = ""
        for sym, b64 in eq_charts.items():
            equity_html += f"<h4>{sym}</h4>" + _img_tag(b64, f"Equity {sym}")

        fold_sections.append(
            f"""
<details open>
<summary><b>Fold {fi}</b> &nbsp;
  train: {fr.get("train_from", "?")} → {fr.get("train_to", "?")} &nbsp;
  test: {fr.get("test_from", "?")} → {fr.get("test_to", "?")}
</summary>
<h4>Metrics (test slice)</h4>{m_table}
<h4>Exit distribution</h4>{exit_table}
<h4>Long / Short breakdown</h4>{ls_table}
<h4>Equity curves</h4>{equity_html}
<h4>Monthly returns</h4>
{_img_tag(monthly_chart, f"Monthly {fi}")}{monthly_table}
</details>
"""
        )

    # Guard warning banner
    guard_html = ""
    if guard_violations:
        items = "".join(f"<li>{v}</li>" for v in guard_violations)
        guard_html = f"""
<div style="background:#f9ebea;border:2px solid #e74c3c;padding:12px;margin:12px 0;border-radius:4px;">
  <b>⚠ Sanity guard fired — see weights.candidate.yaml instead of weights.optimal.yaml</b>
  <ul>{items}</ul>
</div>"""

    # Recommended weights block
    weights_yaml_str = json.dumps(recommended_weights, indent=2)

    # Baseline section
    baseline_html = _baseline_table(baselines)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>Backtest Report — crypt</title>
<style>
  body {{font-family:sans-serif;max-width:1200px;margin:auto;padding:16px;}}
  h1,h2,h3,h4 {{color:#2c3e50;}}
  table {{font-size:0.9em;}}
  details summary {{cursor:pointer;font-size:1.1em;margin:8px 0;}}
  pre {{background:#f4f4f4;padding:12px;border-radius:4px;overflow:auto;}}
  .meta-grid {{display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:8px;}}
  .meta-card {{background:#ecf0f1;padding:8px;border-radius:4px;}}
</style>
</head>
<body>

<h1>📊 Backtest Report</h1>
<p style="color:grey;">Generated: {now_str}</p>

{guard_html}

<h2>1. Run metadata</h2>
<div class="meta-grid">
{"".join(f'<div class="meta-card"><b>{k}</b><br/>{v}</div>' for k, v in meta.items())}
</div>

<h2>2. Headline metrics (all test slices combined)</h2>
{agg_table}

<h2>3. Baselines</h2>
{baseline_html}

<h2>4. Per-fold results</h2>
{"".join(fold_sections)}

<h2>5. Recommended weights</h2>
<pre>{weights_yaml_str}</pre>

<h2>9. Known limitations</h2>
<ul>
  <li>H4 forward labels look 96h ahead — only ~2200 non-overlapping samples per symbol per year. Statistical power is modest.</li>
  <li>OKX OI snapshot timing is opaque; large OI deltas may be exchange bookkeeping. Robust z-score normalisation absorbs some of this.</li>
  <li>XPL may have &lt; 1 year of history — its results will have wide CIs.</li>
  <li>Walk-forward with 5 folds means each test slice is ~10 weeks. Regime transitions that span only one fold can produce misleading per-regime expectancy.</li>
  <li>Fee schedule and slippage are assumptions, not measurements.</li>
  <li>Drawdown computation uses closed-trade equity curve only; intra-position unrealised losses are not reflected (see §18.4 of backtest.md).</li>
</ul>

</body>
</html>"""
    return html  # noqa: RET504


def write_report(
    report_dir: Path,
    report_html: str,
    meta: dict[str, Any],
    trades_df: pd.DataFrame,
    verdicts_df: pd.DataFrame,
    optimal_weights: dict[str, Any],
    recommended_weights: dict[str, Any],
    guard_fired: bool,
) -> None:
    """
    Write all report artefacts to report_dir.

    Files produced (§12):
        summary.html
        meta.json
        verdicts.parquet
        weights.optimal.yaml  (or weights.candidate.yaml if guard fired)
        weights.recommended.yaml
    """
    report_dir.mkdir(parents=True, exist_ok=True)

    (report_dir / "summary.html").write_text(report_html, encoding="utf-8")
    (report_dir / "meta.json").write_text(json.dumps(meta, indent=2, default=str), encoding="utf-8")

    if not verdicts_df.empty:
        verdicts_df.to_parquet(report_dir / "verdicts.parquet", index=False)
    if not trades_df.empty:
        trades_df.to_parquet(report_dir / "trades.parquet", index=False)

    from crypt.backtest.optimizer import weights_to_yaml

    if optimal_weights:
        fname = "weights.candidate.yaml" if guard_fired else "weights.optimal.yaml"
        weights_to_yaml(optimal_weights, str(report_dir / fname))
    if recommended_weights:
        weights_to_yaml(recommended_weights, str(report_dir / "weights.recommended.yaml"))
