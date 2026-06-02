"""
Streamlit dashboard to view backtest trades on candlestick charts.

Loads a results folder (trades.csv + trade_candles/), lets you pick a trade
and shows OHLC with entry/exit markers and TP/SL levels.
"""

import os
import sys
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root / "src"))

st.set_page_config(
    page_title="Trade candles viewer",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
<style>
    .main-header { font-size: 2rem; font-weight: bold; color: #1f77b4; margin-bottom: 1rem; }
    .no-candles-msg { padding: 1rem; background: #fff3cd; border-radius: 8px; margin: 1rem 0; }
</style>
""",
    unsafe_allow_html=True,
)


def find_results_folders():
    """Return list of result folders under results/, newest first."""
    results_dir = Path("results")
    if not results_dir.exists():
        return []
    folders = [f for f in results_dir.iterdir() if f.is_dir()]
    return sorted(folders, key=lambda x: x.stat().st_mtime, reverse=True)


def load_trades(results_folder: Path) -> pd.DataFrame | None:
    """Load trades.csv from results folder."""
    path = results_folder / "trades.csv"
    if not path.exists():
        return None
    df = pd.read_csv(path)
    df["entry_time"] = pd.to_datetime(df["entry_time"])
    df["exit_time"] = pd.to_datetime(df["exit_time"])
    return df


def load_trade_candles(results_folder: Path, trade_idx: int) -> pd.DataFrame | None:
    """Load OHLCV slice for one trade (trade_000.csv, ...)."""
    path = results_folder / "trade_candles" / f"trade_{trade_idx:03d}.csv"
    if not path.exists():
        return None
    df = pd.read_csv(path)
    # Index was saved as first column (name "timestamp" or "Unnamed: 0")
    time_col = None
    if "timestamp" in df.columns:
        time_col = "timestamp"
    elif len(df.columns) > 0 and df.columns[0] in ("Unnamed: 0", "timestamp"):
        time_col = df.columns[0]
    if time_col is not None:
        df[time_col] = pd.to_datetime(df[time_col])
        df = df.set_index(time_col)
    return df


def has_trade_candles(results_folder: Path) -> bool:
    """Check if trade_candles subfolder exists and has at least one file."""
    candles_dir = results_folder / "trade_candles"
    if not candles_dir.exists() or not candles_dir.is_dir():
        return False
    return any(candles_dir.glob("trade_*.csv"))


def build_candlestick_figure(
    candles: pd.DataFrame,
    trade_row: pd.Series,
) -> go.Figure:
    """Build Plotly figure: candlestick + entry/exit markers + TP/SL lines."""
    required = ["open", "high", "low", "close"]
    if not all(c in candles.columns for c in required):
        return go.Figure().add_annotation(
            text="Missing OHLC columns in candle data",
            xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False,
        )

    fig = go.Figure(
        data=[
            go.Candlestick(
                x=candles.index,
                open=candles["open"],
                high=candles["high"],
                low=candles["low"],
                close=candles["close"],
                name="OHLC",
            )
        ]
    )

    entry_time = pd.Timestamp(trade_row["entry_time"])
    exit_time = pd.Timestamp(trade_row["exit_time"])
    entry_price = float(trade_row["entry_price"])
    exit_price = float(trade_row["exit_price"])
    tp_price = float(trade_row["tp_price"])
    sl_price = float(trade_row["sl_price"])
    is_long = bool(trade_row["is_long"])

    # Entry marker: triangle up (long) or down (short)
    fig.add_trace(
        go.Scatter(
            x=[entry_time],
            y=[entry_price],
            mode="markers",
            marker=dict(
                size=14,
                symbol="triangle-up" if is_long else "triangle-down",
                color="green" if is_long else "red",
                line=dict(width=2, color="white"),
            ),
            name="Entry",
        )
    )
    # Exit marker: circle
    fig.add_trace(
        go.Scatter(
            x=[exit_time],
            y=[exit_price],
            mode="markers",
            marker=dict(size=12, symbol="circle", color="blue", line=dict(width=2, color="white")),
            name="Exit",
        )
    )

    # TP / SL horizontal lines (span full x range of candles)
    x_min = candles.index.min()
    x_max = candles.index.max()
    fig.add_hline(
        y=tp_price,
        line_dash="dash",
        line_color="green",
        annotation_text="TP",
    )
    fig.add_hline(
        y=sl_price,
        line_dash="dash",
        line_color="red",
        annotation_text="SL",
    )

    fig.update_layout(
        title=f"Trade: {'Long' if is_long else 'Short'} | PnL: {trade_row.get('pnl_abs', 0):.2f}",
        xaxis_title="Time",
        yaxis_title="Price",
        template="plotly_white",
        xaxis_rangeslider_visible=False,
        height=500,
    )
    return fig


def main():
    st.title("📊 Trade candles viewer")
    st.markdown("Просмотр сделок на графике свечей с отметками входа/выхода и уровней TP/SL.")

    folders = find_results_folders()
    if not folders:
        st.error("Папка results/ не найдена или пуста. Запустите бэктест и экспорт результатов.")
        return

    with st.sidebar:
        st.subheader("Результаты")
        folder_names = [f.name for f in folders]
        selected_name = st.selectbox(
            "Выберите папку с результатами",
            folder_names,
            index=0,
        )
        selected_folder = next(f for f in folders if f.name == selected_name)
        st.caption(str(selected_folder))

    trades_df = load_trades(selected_folder)
    if trades_df is None or trades_df.empty:
        st.warning("В выбранной папке нет trades.csv или он пуст.")
        return

    if not has_trade_candles(selected_folder):
        st.markdown(
            '<div class="no-candles-msg">'
            "⚠️ В этой папке нет срезов свечей (trade_candles/). "
            "Чтобы визуализировать сделки на графике, перезапустите бэктест и экспорт результатов "
            "(текущая версия CLI при экспорте сохраняет срезы свечей автоматически)."
            "</div>",
            unsafe_allow_html=True,
        )
        st.subheader("Список сделок")
        display_cols = ["entry_time", "exit_time", "pnl_abs", "exit_reason", "is_long"]
        display_cols = [c for c in display_cols if c in trades_df.columns]
        st.dataframe(trades_df[display_cols] if display_cols else trades_df, use_container_width=True)
        return

    st.sidebar.success(f"✅ Сделок: {len(trades_df)}")

    # Trade selector: index (persist in session for prev/next buttons)
    n_trades = len(trades_df)
    if "trade_idx" not in st.session_state:
        st.session_state["trade_idx"] = 0
    st.session_state["trade_idx"] = max(0, min(st.session_state["trade_idx"], n_trades - 1))

    trade_indices = list(range(n_trades))
    # Key depends on trade_idx so that after prev/next rerun the selectbox is a "new" widget and shows the updated index
    selected_idx = st.sidebar.selectbox(
        "Выберите сделку (по номеру)",
        trade_indices,
        index=st.session_state["trade_idx"],
        format_func=lambda i: f"#{i} {trades_df.iloc[i]['entry_time']} → PnL {trades_df.iloc[i].get('pnl_abs', 0):.2f}",
        key=f"trade_sel_{st.session_state['trade_idx']}",
    )
    st.session_state["trade_idx"] = selected_idx

    # Prev / Next buttons in sidebar
    col_prev, col_next = st.sidebar.columns(2)
    with col_prev:
        if st.button("◀ Предыдущая", disabled=(selected_idx <= 0), use_container_width=True):
            st.session_state["trade_idx"] = selected_idx - 1
            st.rerun()
    with col_next:
        if st.button("Следующая ▶", disabled=(selected_idx >= n_trades - 1), use_container_width=True):
            st.session_state["trade_idx"] = selected_idx + 1
            st.rerun()

    trade_row = trades_df.iloc[selected_idx]
    candles = load_trade_candles(selected_folder, selected_idx)
    if candles is None or candles.empty:
        st.warning(f"Нет данных свечей для сделки #{selected_idx} (trade_{selected_idx:03d}.csv).")
        return

    fig = build_candlestick_figure(candles, trade_row)
    st.plotly_chart(fig, use_container_width=True)

    with st.expander("Данные выбранной сделки"):
        st.dataframe(trade_row.to_frame().T, use_container_width=True)


if __name__ == "__main__":
    main()
