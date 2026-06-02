import os
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# Добавляем путь к модулю
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(project_root, "src"))


# Настройка страницы
st.set_page_config(
    page_title="Backtester Analysis Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# CSS для улучшения внешнего вида
st.markdown(
    """
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #1f77b4;
    }
    .success-metric {
        border-left-color: #28a745;
    }
    .warning-metric {
        border-left-color: #ffc107;
    }
    .danger-metric {
        border-left-color: #dc3545;
    }
</style>
""",
    unsafe_allow_html=True,
)


def find_latest_results():
    """Находит последнюю папку с результатами"""
    results_dir = Path("results")
    if not results_dir.exists():
        return None

    result_folders = [
        f
        for f in results_dir.iterdir()
        if f.is_dir() and f.name.startswith("backtesting_")
    ]

    if not result_folders:
        return None

    # Сортируем по времени создания (новые первыми)
    latest_folder = max(result_folders, key=lambda x: x.stat().st_mtime)
    return latest_folder


def load_results_data(results_folder):
    """Загружает данные из папки результатов"""
    data = {}

    # Загружаем CSV файлы
    csv_files = {
        "trades": "trades.csv",
        "metrics": "metrics.csv",
        "equity_curve": "equity_curve.csv",
        "trade_conditions": "trade_conditions_analysis.csv",
    }

    for key, filename in csv_files.items():
        file_path = results_folder / filename
        if file_path.exists():
            try:
                df = pd.read_csv(file_path)
                # Для metrics файла преобразуем в словарь для удобства
                if key == "metrics" and not df.empty:
                    # Если это CSV с одной строкой, преобразуем в словарь
                    if len(df) == 1:
                        metrics_dict = {}
                        for col in df.columns:
                            value = df.iloc[0][col]
                            # Обрабатываем специальные случаи
                            if col in [
                                "exit_distribution",
                                "monthly_returns_pct",
                                "long_metrics",
                                "short_metrics",
                            ]:
                                # Эти поля содержат сложные структуры, пропускаем их
                                continue
                            elif pd.isna(value):
                                metrics_dict[col] = 0
                            else:
                                metrics_dict[col] = value
                        data[key] = metrics_dict
                    else:
                        data[key] = df
                else:
                    data[key] = df
            except Exception as e:
                st.error(f"Ошибка загрузки файла {filename}: {e}")

    return data, results_folder


def create_metric_cards(metrics_data):
    """Создает карточки с ключевыми метриками"""
    if metrics_data is None:
        return

    # Проверяем, является ли это словарем или DataFrame
    if isinstance(metrics_data, dict):
        if not metrics_data:
            return
    elif hasattr(metrics_data, "empty") and metrics_data.empty:
        return

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        total_return = metrics_data.get("total_return_pct", 0)
        if isinstance(total_return, pd.Series):
            total_return = total_return.iloc[0] if len(total_return) > 0 else 0
        color_class = "success-metric" if total_return > 0 else "danger-metric"
        st.markdown(
            f"""
        <div class="metric-card {color_class}">
            <h3>Total Return</h3>
            <h2>{total_return:.2f}%</h2>
        </div>
        """,
            unsafe_allow_html=True,
        )

    with col2:
        win_rate = metrics_data.get("win_rate", 0)
        if isinstance(win_rate, pd.Series):
            win_rate = win_rate.iloc[0] if len(win_rate) > 0 else 0
        color_class = (
            "success-metric"
            if win_rate > 50
            else "warning-metric"
            if win_rate > 40
            else "danger-metric"
        )
        st.markdown(
            f"""
        <div class="metric-card {color_class}">
            <h3>Win Rate</h3>
            <h2>{win_rate:.1f}%</h2>
        </div>
        """,
            unsafe_allow_html=True,
        )

    with col3:
        profit_factor = metrics_data.get("profit_factor", 0)
        if isinstance(profit_factor, pd.Series):
            profit_factor = profit_factor.iloc[0] if len(profit_factor) > 0 else 0
        if profit_factor == "inf":
            profit_factor = float("inf")
        color_class = (
            "success-metric"
            if profit_factor > 1.5
            else "warning-metric"
            if profit_factor > 1.0
            else "danger-metric"
        )
        pf_display = "∞" if profit_factor == float("inf") else f"{profit_factor:.2f}"
        st.markdown(
            f"""
        <div class="metric-card {color_class}">
            <h3>Profit Factor</h3>
            <h2>{pf_display}</h2>
        </div>
        """,
            unsafe_allow_html=True,
        )

    with col4:
        max_dd = metrics_data.get("max_drawdown", 0)
        if isinstance(max_dd, pd.Series):
            max_dd = max_dd.iloc[0] if len(max_dd) > 0 else 0
        color_class = (
            "success-metric"
            if max_dd > -10
            else "warning-metric"
            if max_dd > -20
            else "danger-metric"
        )
        st.markdown(
            f"""
        <div class="metric-card {color_class}">
            <h3>Max Drawdown</h3>
            <h2>{max_dd:.2f}%</h2>
        </div>
        """,
            unsafe_allow_html=True,
        )


def plot_equity_curve(equity_data):
    """Строит график кривой капитала"""
    if equity_data is None or equity_data.empty:
        return

    fig = go.Figure()

    # Основная кривая капитала
    fig.add_trace(
        go.Scatter(
            x=equity_data.index,
            y=equity_data.iloc[:, 0],  # Предполагаем, что капитал в первом столбце
            mode="lines",
            name="Capital",
            line=dict(color="#1f77b4", width=2),
        )
    )

    fig.update_layout(
        title="Equity Curve",
        xaxis_title="Time",
        yaxis_title="Capital ($)",
        hovermode="x unified",
        height=400,
    )

    st.plotly_chart(fig, use_container_width=True)


def plot_trade_distribution(trades_data):
    """Строит график распределения сделок"""
    if trades_data is None or trades_data.empty:
        return

    col1, col2 = st.columns(2)

    with col1:
        # Распределение по исходу сделок
        exit_counts = trades_data["exit_reason"].value_counts()
        colors = [
            "#28a745" if reason == "take_profit" else "#dc3545"
            for reason in exit_counts.index
        ]

        fig = px.pie(
            values=exit_counts.values,
            names=exit_counts.index,
            title="Trade Outcome Distribution",
            color_discrete_sequence=colors,
        )
        st.plotly_chart(fig, width="stretch")

    with col2:
        # Распределение PnL
        fig = go.Figure()

        for reason in trades_data["exit_reason"].unique():
            data = trades_data[trades_data["exit_reason"] == reason]["pnl_abs"]
            color = "#28a745" if reason == "take_profit" else "#dc3545"

            fig.add_trace(
                go.Histogram(
                    x=data,
                    name=reason.replace("_", " ").title(),
                    opacity=0.7,
                    marker_color=color,
                )
            )

        fig.update_layout(
            title="PnL Distribution by Outcome",
            xaxis_title="PnL ($)",
            yaxis_title="Count",
            barmode="overlay",
            height=400,
        )

        st.plotly_chart(fig, width="stretch")


def plot_predictor_analysis(conditions_data):
    """Анализ предикторов"""
    if conditions_data is None or conditions_data.empty:
        return

    st.subheader("🏆 Top Predictors Analysis")

    # Топ 10 предикторов
    top_predictors = conditions_data.head(10)

    col1, col2 = st.columns(2)

    with col1:
        # AUC Score
        fig = px.bar(
            top_predictors,
            x="auc_score",
            y="metric_name",
            orientation="h",
            title="AUC Scores (Top 10)",
            color="auc_score",
            color_continuous_scale=["red", "yellow", "green"],
            range_color=[0, 1],
        )
        fig.add_vline(
            x=0.5, line_dash="dash", line_color="black", annotation_text="Random (0.5)"
        )
        fig.update_layout(height=500)
        st.plotly_chart(fig, width="stretch")

    with col2:
        # KS Statistic
        fig = px.bar(
            top_predictors,
            x="ks_statistic",
            y="metric_name",
            orientation="h",
            title="Kolmogorov-Smirnov Statistics",
            color="ks_statistic",
            color_continuous_scale="Blues",
        )
        fig.update_layout(height=500)
        st.plotly_chart(fig, width="stretch")

    # Детальная таблица
    st.subheader("📊 Detailed Predictor Metrics")

    # Форматируем таблицу для лучшего отображения
    display_data = top_predictors.copy()
    display_data["metric_name"] = (
        display_data["metric_name"].str.replace("_", " ").str.title()
    )

    # Округляем числовые значения
    numeric_cols = ["auc_score", "ks_statistic", "js_divergence", "gini_coefficient"]
    for col in numeric_cols:
        if col in display_data.columns:
            display_data[col] = display_data[col].round(3)

    st.dataframe(
        display_data[
            [
                "metric_name",
                "auc_score",
                "ks_statistic",
                "js_divergence",
                "tp_count",
                "sl_count",
            ]
        ],
        width="stretch",
        column_config={
            "metric_name": "Metric",
            "auc_score": st.column_config.NumberColumn("AUC", format="%.3f"),
            "ks_statistic": st.column_config.NumberColumn("KS", format="%.3f"),
            "js_divergence": st.column_config.NumberColumn("JS", format="%.3f"),
            "tp_count": "TP Count",
            "sl_count": "SL Count",
        },
    )


def plot_interactive_distributions(conditions_data, trades_data):
    """Интерактивный анализ распределений метрик"""
    if (
        conditions_data is None
        or conditions_data.empty
        or trades_data is None
        or trades_data.empty
    ):
        return

    st.subheader("🔍 Interactive Distribution Analysis")

    # Создаем селектор метрик
    metric_options = conditions_data["metric_name"].tolist()
    metric_display_names = [name.replace("_", " ").title() for name in metric_options]

    # Создаем словарь для маппинга
    metric_mapping = dict(zip(metric_display_names, metric_options))

    col1, col2 = st.columns([2, 1])

    with col1:
        selected_display_name = st.selectbox(
            "Выберите метрику для анализа:",
            options=metric_display_names,
            index=0,
            help="Выберите метрику для построения распределений TP vs SL",
        )

    with col2:
        show_stats = st.checkbox("Показать статистики", value=True)

    selected_metric = metric_mapping[selected_display_name]

    # Получаем данные для выбранной метрики
    metric_info = conditions_data[
        conditions_data["metric_name"] == selected_metric
    ].iloc[0]

    # Пытаемся загрузить реальные данные метрик
    entry_metrics_data = None
    try:
        # Ищем файл с метриками входа
        results_folder = find_latest_results()
        if results_folder:
            entry_metrics_file = results_folder / "entry_metrics.csv"
            if entry_metrics_file.exists():
                entry_metrics_data = pd.read_csv(entry_metrics_file)
    except Exception as e:
        st.warning(f"Не удалось загрузить данные метрик: {e}")

    # Инициализируем переменные
    tp_mean = metric_info.get("tp_mean", 0)
    sl_mean = metric_info.get("sl_mean", 0)

    # Если есть реальные данные, используем их
    if entry_metrics_data is not None and selected_metric in entry_metrics_data.columns:
        # Добавляем фильтр по направлению
        col_filter1, col_filter2 = st.columns(2)
        with col_filter1:
            direction_filter = st.selectbox(
                "Направление сделок:", ["Все", "Long", "Short"], key="direction_filter"
            )

        # Фильтруем данные по направлению
        filtered_data = entry_metrics_data.copy()
        if direction_filter == "Long" and "is_long" in filtered_data.columns:
            filtered_data = filtered_data[filtered_data["is_long"] == True]
        elif direction_filter == "Short" and "is_long" in filtered_data.columns:
            filtered_data = filtered_data[filtered_data["is_long"] == False]

        # Разделяем данные по исходу сделок
        tp_data = filtered_data[filtered_data["exit_reason"] == "take_profit"][
            selected_metric
        ].dropna()

        sl_data = filtered_data[filtered_data["exit_reason"] == "stop_loss"][
            selected_metric
        ].dropna()

        if len(tp_data) == 0 or len(sl_data) == 0:
            st.warning(
                f"Недостаточно данных для выбранной метрики ({direction_filter})"
            )
            return
    else:
        # Используем синтетические данные на основе статистик
        st.info("Используются синтетические данные на основе статистик")
        np.random.seed(42)  # Для воспроизводимости

        tp_std = metric_info.get("tp_std", 0.1)
        sl_std = metric_info.get("sl_std", 0.1)
        tp_count = int(metric_info.get("tp_count", 5))
        sl_count = int(metric_info.get("sl_count", 5))

        # Генерируем синтетические данные
        tp_data = pd.Series(np.random.normal(tp_mean, tp_std, tp_count))
        sl_data = pd.Series(np.random.normal(sl_mean, sl_std, sl_count))

    # Создаем графики
    col1, col2 = st.columns(2)

    with col1:
        # Гистограммы
        fig = go.Figure()

        fig.add_trace(
            go.Histogram(
                x=tp_data,
                name="Take Profit",
                opacity=0.7,
                marker_color="green",
                nbinsx=20,
            )
        )

        fig.add_trace(
            go.Histogram(
                x=sl_data, name="Stop Loss", opacity=0.7, marker_color="red", nbinsx=20
            )
        )

        direction_suffix = (
            f" ({direction_filter})" if "direction_filter" in locals() else ""
        )
        fig.update_layout(
            title=f"Distribution: {selected_display_name}{direction_suffix}",
            xaxis_title=selected_display_name,
            yaxis_title="Count",
            barmode="overlay",
            height=400,
        )

        st.plotly_chart(fig, width="stretch")

    with col2:
        # Box plots
        fig = go.Figure()

        fig.add_trace(
            go.Box(
                y=tp_data,
                name="Take Profit",
                marker_color="green",
                boxpoints="outliers",
            )
        )

        fig.add_trace(
            go.Box(
                y=sl_data, name="Stop Loss", marker_color="red", boxpoints="outliers"
            )
        )

        fig.update_layout(
            title=f"Box Plot: {selected_display_name}",
            yaxis_title=selected_display_name,
            height=400,
        )

        st.plotly_chart(fig, width="stretch")

    # Статистики
    if show_stats:
        st.subheader("📊 Statistics")

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric(
                "AUC Score",
                f"{metric_info.get('auc_score', 0):.3f}",
                help="Area Under Curve - качество разделения",
            )

        with col2:
            st.metric(
                "KS Statistic",
                f"{metric_info.get('ks_statistic', 0):.3f}",
                help="Kolmogorov-Smirnov - максимальная разность распределений",
            )

        with col3:
            st.metric(
                "TP Mean",
                f"{tp_mean:.4f}",
                help="Среднее значение для Take Profit сделок",
            )

        with col4:
            st.metric(
                "SL Mean",
                f"{sl_mean:.4f}",
                help="Среднее значение для Stop Loss сделок",
            )

        # Дополнительная информация
        st.info("""
        **Интерпретация результатов:**
        - **AUC > 0.7**: Отличный предиктор
        - **AUC > 0.6**: Хороший предиктор
        - **AUC < 0.5**: Плохой предиктор
        - **KS > 0.3**: Значительное различие между распределениями
        """)

    # Рекомендации по использованию
    auc_score = metric_info.get("auc_score", 0)
    if auc_score > 0.7:
        st.success(
            f"🎯 **{selected_display_name}** - отличный предиктор! Рекомендуется использовать в стратегии."
        )
    elif auc_score > 0.6:
        st.warning(
            f"⚠️ **{selected_display_name}** - хороший предиктор. Можно использовать с осторожностью."
        )
    else:
        st.error(
            f"❌ **{selected_display_name}** - слабый предиктор. Не рекомендуется для использования."
        )


def plot_correlation_heatmap(conditions_data):
    """Корреляционная матрица предикторов"""
    if conditions_data is None or conditions_data.empty:
        return

    st.subheader("🔥 Predictor Correlation Matrix")

    # Берем топ 8 предикторов для корреляционной матрицы
    top_8 = conditions_data.head(8)

    # Создаем матрицу корреляций между метриками
    # Проверяем какие колонки действительно есть в данных
    available_metrics = []
    potential_metrics = [
        "auc_score",
        "ks_statistic",
        "js_divergence",
        "gini_coefficient",
        "mutual_information",
    ]

    for metric in potential_metrics:
        if metric in top_8.columns:
            available_metrics.append(metric)

    if not available_metrics:
        st.warning("Нет доступных метрик для корреляционного анализа")
        return

    correlation_data = top_8[available_metrics].corr()

    fig = px.imshow(
        correlation_data,
        text_auto=True,
        aspect="auto",
        color_continuous_scale="RdBu",
        title="Correlation Between Separation Metrics",
    )

    st.plotly_chart(fig, use_container_width=True)


def plot_trade_timeline(trades_data):
    """Временная линия сделок с интерактивной фильтрацией"""
    if trades_data is None or trades_data.empty:
        return

    st.subheader("⏰ Trade Timeline")

    # Подготавливаем данные
    trades = trades_data.copy()
    trades["entry_time"] = pd.to_datetime(trades["entry_time"])
    trades["exit_time"] = pd.to_datetime(trades["exit_time"])
    trades["color"] = trades["exit_reason"].map(
        {"take_profit": "#28a745", "stop_loss": "#dc3545", "ttl_expired": "#ffc107"}
    )

    # Создаем интерактивный график с возможностью выделения диапазона
    fig = go.Figure()

    for _, trade in trades.iterrows():
        fig.add_trace(
            go.Scatter(
                x=[trade["entry_time"], trade["exit_time"]],
                y=[trade["pnl_abs"], trade["pnl_abs"]],
                mode="lines+markers",
                line=dict(color=trade["color"], width=3),
                marker=dict(size=8),
                name=trade["exit_reason"].replace("_", " ").title(),
                showlegend=False,
                hovertemplate=f"PnL: ${trade['pnl_abs']:.2f}<br>"
                + f"Entry: {trade['entry_time']}<br>"
                + f"Exit: {trade['exit_time']}<extra></extra>",
            )
        )

    # Добавляем линию нуля
    fig.add_hline(y=0, line_dash="dash", line_color="black", opacity=0.5)

    fig.update_layout(
        title="Individual Trades Timeline (Select range to filter)",
        xaxis_title="Time",
        yaxis_title="PnL ($)",
        height=400,
        hovermode="closest",
        # Включаем возможность выделения диапазона
        xaxis=dict(
            rangeselector=dict(
                buttons=list(
                    [
                        dict(count=7, label="7d", step="day", stepmode="backward"),
                        dict(count=30, label="30d", step="day", stepmode="backward"),
                        dict(count=90, label="90d", step="day", stepmode="backward"),
                        dict(step="all"),
                    ]
                )
            ),
            rangeslider=dict(visible=True),
            type="date",
        ),
    )

    # Отображаем график и получаем выбранный диапазон
    selected_data = st.plotly_chart(fig, use_container_width=True, key="timeline_chart")

    # Добавляем возможность ручного выбора диапазона
    st.markdown("**📅 Manual Date Range Selection:**")
    col1, col2 = st.columns(2)

    with col1:
        start_date = st.date_input(
            "Start Date",
            value=trades["entry_time"].min().date(),
            min_value=trades["entry_time"].min().date(),
            max_value=trades["exit_time"].max().date(),
            key="start_date_filter",
        )

    with col2:
        end_date = st.date_input(
            "End Date",
            value=trades["exit_time"].max().date(),
            min_value=trades["entry_time"].min().date(),
            max_value=trades["exit_time"].max().date(),
            key="end_date_filter",
        )

    # Фильтруем данные по выбранному диапазону
    start_datetime = pd.to_datetime(start_date)
    end_datetime = pd.to_datetime(end_date) + pd.Timedelta(days=1)  # Включаем весь день

    filtered_trades = trades[
        (trades["entry_time"] >= start_datetime) & (trades["exit_time"] <= end_datetime)
    ].copy()

    # Показываем статистику по отфильтрованным данным
    if not filtered_trades.empty:
        st.markdown(f"**📊 Filtered Data Statistics ({len(filtered_trades)} trades):**")

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            total_pnl = filtered_trades["pnl_abs"].sum()
            color = "normal" if total_pnl >= 0 else "inverse"
            st.metric("Total PnL", f"${total_pnl:.2f}", delta=None)

        with col2:
            win_rate = (
                (filtered_trades["exit_reason"] == "take_profit").sum()
                / len(filtered_trades)
                * 100
            )
            st.metric("Win Rate", f"{win_rate:.1f}%")

        with col3:
            avg_pnl = filtered_trades["pnl_abs"].mean()
            st.metric("Avg PnL", f"${avg_pnl:.2f}")

        with col4:
            max_pnl = filtered_trades["pnl_abs"].max()
            min_pnl = filtered_trades["pnl_abs"].min()
            st.metric("Best/Worst", f"${max_pnl:.2f} / ${min_pnl:.2f}")

        # Кумулятивная прибыль для отфильтрованных данных
        st.markdown("**📈 Filtered Cumulative PnL:**")
        filtered_sorted = filtered_trades.sort_values("exit_time")
        filtered_sorted["cumulative_pnl"] = filtered_sorted["pnl_abs"].cumsum()

        fig2 = go.Figure()
        fig2.add_trace(
            go.Scatter(
                x=filtered_sorted["exit_time"],
                y=filtered_sorted["cumulative_pnl"],
                mode="lines+markers",
                fill="tonexty",
                name="Cumulative PnL",
                line=dict(color="#1f77b4", width=3),
                marker=dict(size=6),
            )
        )

        fig2.add_hline(y=0, line_dash="dash", line_color="black", opacity=0.5)

        fig2.update_layout(
            title=f"Cumulative Profit/Loss ({start_date} to {end_date})",
            xaxis_title="Time",
            yaxis_title="Cumulative PnL ($)",
            height=400,
        )

        st.plotly_chart(fig2, use_container_width=True)

        # Детальная таблица отфильтрованных сделок
        st.markdown("**📋 Filtered Trades Details:**")

        # Форматируем данные для отображения
        display_trades = filtered_trades[
            ["entry_time", "exit_time", "pnl_abs", "exit_reason"]
        ].copy()
        display_trades["entry_time"] = display_trades["entry_time"].dt.strftime(
            "%Y-%m-%d %H:%M"
        )
        display_trades["exit_time"] = display_trades["exit_time"].dt.strftime(
            "%Y-%m-%d %H:%M"
        )
        display_trades["pnl_abs"] = display_trades["pnl_abs"].apply(
            lambda x: f"${x:.2f}"
        )
        display_trades["exit_reason"] = (
            display_trades["exit_reason"].str.replace("_", " ").str.title()
        )

        display_trades.columns = ["Entry Time", "Exit Time", "PnL", "Exit Reason"]

        st.dataframe(display_trades, use_container_width=True, hide_index=True)

        # Возвращаем отфильтрованные данные для использования в других функциях
        return filtered_trades

    else:
        st.warning("No trades found in the selected date range.")
        return trades_data  # Возвращаем исходные данные если фильтр пустой


def plot_market_conditions_analysis(trades_data, equity_data):
    """Анализ работы стратегии в разных рыночных условиях"""
    if trades_data is None or trades_data.empty:
        return

    st.subheader("📈 Market Conditions Analysis")

    # Подготавливаем данные
    trades = trades_data.copy()
    trades["entry_time"] = pd.to_datetime(trades["entry_time"])
    trades["exit_time"] = pd.to_datetime(trades["exit_time"])

    # Создаем дневные данные для анализа тренда
    if equity_data is not None and not equity_data.empty:
        # Используем equity curve для определения дневного тренда
        equity_df = equity_data.copy()
        equity_df.index = pd.to_datetime(equity_df.index)

        # Убеждаемся, что данные equity являются числовыми
        equity_column = equity_df.columns[0]
        equity_df[equity_column] = pd.to_numeric(
            equity_df[equity_column], errors="coerce"
        )

        # Удаляем строки с NaN значениями
        equity_df = equity_df.dropna()

        if equity_df.empty:
            st.warning("Недостаточно данных для анализа рыночных условий")
            return

        equity_df["date"] = equity_df.index.date

        # Группируем по дням и находим дневные изменения
        daily_equity = equity_df.groupby("date")[equity_column].agg(["first", "last"])
        daily_equity["daily_return"] = (
            daily_equity["last"] - daily_equity["first"]
        ) / daily_equity["first"]
        daily_equity["trend"] = daily_equity["daily_return"].apply(
            lambda x: "Bullish" if x > 0.01 else "Bearish" if x < -0.01 else "Sideways"
        )

        # Добавляем информацию о тренде к сделкам
        trades["entry_date"] = trades["entry_time"].dt.date
        trades["exit_date"] = trades["exit_time"].dt.date

        # Определяем тренд на момент входа
        trades = trades.merge(
            daily_equity[["trend"]].reset_index(),
            left_on="entry_date",
            right_on="date",
            how="left",
        )
        trades["market_trend"] = trades["trend"].fillna("Unknown")

        # Анализ по трендам
        trend_analysis = (
            trades.groupby("market_trend")
            .agg(
                {
                    "pnl_abs": ["count", "sum", "mean"],
                    "exit_reason": lambda x: (x == "take_profit").sum() / len(x) * 100,
                }
            )
            .round(2)
        )

        trend_analysis.columns = ["Total Trades", "Total PnL", "Avg PnL", "Win Rate %"]
        trend_analysis = trend_analysis.reset_index()

        # Визуализация
        col1, col2 = st.columns(2)

        with col1:
            # Распределение сделок по трендам
            trend_counts = trades["market_trend"].value_counts()
            colors = [
                "#28a745"
                if trend == "Bullish"
                else "#dc3545"
                if trend == "Bearish"
                else "#ffc107"
                for trend in trend_counts.index
            ]

            fig = px.pie(
                values=trend_counts.values,
                names=trend_counts.index,
                title="Trades Distribution by Market Trend",
                color_discrete_sequence=colors,
            )
            st.plotly_chart(fig, width="stretch")

        with col2:
            # Средний PnL по трендам
            fig = px.bar(
                trend_analysis,
                x="market_trend",
                y="Avg PnL",
                title="Average PnL by Market Trend",
                color="Avg PnL",
                color_continuous_scale=["red", "yellow", "green"],
            )
            fig.add_hline(y=0, line_dash="dash", line_color="black", opacity=0.5)
            st.plotly_chart(fig, width="stretch")

        # Детальная таблица
        st.subheader("📊 Performance by Market Trend")

        # Форматируем таблицу
        display_analysis = trend_analysis.copy()
        display_analysis["Total PnL"] = display_analysis["Total PnL"].apply(
            lambda x: f"${x:.2f}"
        )
        display_analysis["Avg PnL"] = display_analysis["Avg PnL"].apply(
            lambda x: f"${x:.2f}"
        )
        display_analysis["Win Rate %"] = display_analysis["Win Rate %"].apply(
            lambda x: f"{x:.1f}%"
        )

        st.dataframe(
            display_analysis,
            width="stretch",
            column_config={
                "market_trend": "Market Trend",
                "Total Trades": "Total Trades",
                "Total PnL": "Total PnL",
                "Avg PnL": "Avg PnL",
                "Win Rate %": "Win Rate %",
            },
        )

        # Временной график с трендами
        st.subheader("📅 Daily Trend Timeline")

        # Создаем временной ряд дневных трендов
        daily_trends = daily_equity.reset_index()
        daily_trends["date"] = pd.to_datetime(daily_trends["date"])

        fig = go.Figure()

        # Добавляем фон для разных трендов
        for i, row in daily_trends.iterrows():
            color = (
                "#d4edda"
                if row["trend"] == "Bullish"
                else "#f8d7da"
                if row["trend"] == "Bearish"
                else "#fff3cd"
            )
            fig.add_vrect(
                x0=row["date"],
                x1=row["date"] + pd.Timedelta(days=1),
                fillcolor=color,
                opacity=0.3,
                layer="below",
                line_width=0,
            )

        # Добавляем дневные изменения капитала
        fig.add_trace(
            go.Scatter(
                x=daily_trends["date"],
                y=daily_trends["daily_return"] * 100,
                mode="lines+markers",
                name="Daily Return %",
                line=dict(color="#1f77b4", width=2),
                marker=dict(size=6),
            )
        )

        # Добавляем сделки
        for _, trade in trades.iterrows():
            color = "#28a745" if trade["exit_reason"] == "take_profit" else "#dc3545"
            fig.add_vline(
                x=trade["entry_time"],
                line=dict(color=color, width=2, dash="dot"),
                annotation_text=f"${trade['pnl_abs']:.0f}",
                annotation_position="top",
            )

        fig.add_hline(y=0, line_dash="dash", line_color="black", opacity=0.5)

        fig.update_layout(
            title="Daily Market Trends and Trade Entries",
            xaxis_title="Date",
            yaxis_title="Daily Return (%)",
            height=500,
            hovermode="x unified",
        )

        st.plotly_chart(fig, width="stretch")

        # Рекомендации
        st.subheader("💡 Insights")

        best_trend = trend_analysis.loc[
            trend_analysis["Avg PnL"].idxmax(), "market_trend"
        ]
        worst_trend = trend_analysis.loc[
            trend_analysis["Avg PnL"].idxmin(), "market_trend"
        ]

        col1, col2 = st.columns(2)

        with col1:
            if (
                trend_analysis[trend_analysis["market_trend"] == best_trend][
                    "Avg PnL"
                ].iloc[0]
                > 0
            ):
                st.success(
                    f"🎯 **Лучше всего стратегия работает в {best_trend} рынке**"
                )
                st.write(
                    f"Средний PnL: ${trend_analysis[trend_analysis['market_trend'] == best_trend]['Avg PnL'].iloc[0]:.2f}"
                )

        with col2:
            if (
                trend_analysis[trend_analysis["market_trend"] == worst_trend][
                    "Avg PnL"
                ].iloc[0]
                < 0
            ):
                st.error(f"⚠️ **Хуже всего стратегия работает в {worst_trend} рынке**")
                st.write(
                    f"Средний PnL: ${trend_analysis[trend_analysis['market_trend'] == worst_trend]['Avg PnL'].iloc[0]:.2f}"
                )

        # Общие рекомендации
        bullish_trades = trend_analysis[trend_analysis["market_trend"] == "Bullish"]
        bearish_trades = trend_analysis[trend_analysis["market_trend"] == "Bearish"]

        if not bullish_trades.empty and not bearish_trades.empty:
            bullish_avg = bullish_trades["Avg PnL"].iloc[0]
            bearish_avg = bearish_trades["Avg PnL"].iloc[0]

            if (
                bearish_avg < bullish_avg * 0.5
            ):  # Если в медвежьем рынке результаты значительно хуже
                st.warning(
                    "🚨 **Стратегия показывает слабые результаты в медвежьем рынке!**"
                )
                st.write("Рекомендации:")
                st.write("- Рассмотрите добавление фильтров для медвежьего рынка")
                st.write("- Изучите возможность использования шортов")
                st.write("- Добавьте анализ волатильности как дополнительный фильтр")
            elif (
                bullish_avg > bearish_avg * 1.5
            ):  # Если в бычьем рынке результаты значительно лучше
                st.info("📈 **Стратегия оптимизирована для бычьего рынка**")
                st.write("Это нормально для трендовых стратегий")

    else:
        st.warning("Недостаточно данных для анализа рыночных условий")


def main():
    # Заголовок
    st.markdown(
        '<h1 class="main-header">📊 Backtester Analysis Dashboard</h1>',
        unsafe_allow_html=True,
    )

    # Боковая панель
    st.sidebar.title("🔧 Controls")

    # Поиск результатов
    results_folder = find_latest_results()

    if results_folder is None:
        st.error("❌ No results found. Please run a backtest first.")
        st.info(
            "💡 Use: `hatch env run -- python -m backtester run --csv val.csv --strategy strategies/dual_ma_v1.json --analyze-conditions --create-dashboard`"
        )
        return

    st.sidebar.success(f"✅ Found results: {results_folder.name}")

    # Загружаем данные
    data, folder = load_results_data(results_folder)

    if not data:
        st.error("❌ No data files found in results folder.")
        return

    # Инициализируем session state для отфильтрованных данных
    if "filtered_trades" not in st.session_state:
        st.session_state.filtered_trades = None

    # Информация о результатах
    st.sidebar.markdown("### 📁 Results Info")
    st.sidebar.write(f"**Folder:** {folder.name}")
    st.sidebar.write(
        f"**Created:** {datetime.fromtimestamp(folder.stat().st_mtime).strftime('%Y-%m-%d %H:%M:%S')}"
    )

    # Доступные данные
    available_data = list(data.keys())
    st.sidebar.write(f"**Available data:** {', '.join(available_data)}")

    # Основной контент
    if "metrics" in data:
        st.header("📈 Key Metrics")
        create_metric_cards(data["metrics"])
        st.markdown("---")

    if "equity_curve" in data:
        st.header("📊 Equity Curve")
        plot_equity_curve(data["equity_curve"])
        st.markdown("---")

    if "trades" in data:
        st.header("🎯 Trade Analysis")
        plot_trade_distribution(data["trades"])
        st.markdown("---")

        # Получаем отфильтрованные данные из timeline
        st.session_state.filtered_trades = plot_trade_timeline(data["trades"])
        st.markdown("---")

        # Анализ рыночных условий с отфильтрованными данными
        if "equity_curve" in data:
            trades_for_analysis = (
                st.session_state.filtered_trades
                if st.session_state.filtered_trades is not None
                else data["trades"]
            )
            plot_market_conditions_analysis(trades_for_analysis, data["equity_curve"])
            st.markdown("---")

    if "trade_conditions" in data:
        st.header("🔍 Trade Conditions Analysis")
        plot_predictor_analysis(data["trade_conditions"])
        st.markdown("---")

        # Интерактивный анализ распределений с отфильтрованными данными
        if "trades" in data:
            # Используем отфильтрованные данные если они доступны
            trades_for_analysis = (
                st.session_state.filtered_trades
                if st.session_state.filtered_trades is not None
                else data["trades"]
            )
            plot_interactive_distributions(
                data["trade_conditions"], trades_for_analysis
            )
            st.markdown("---")

        plot_correlation_heatmap(data["trade_conditions"])
        st.markdown("---")

    # Дополнительная информация
    st.sidebar.markdown("### 📊 Quick Stats")
    if "trades" in data:
        # Показываем статистику в зависимости от того, применен ли фильтр
        if st.session_state.filtered_trades is not None:
            trades_data = st.session_state.filtered_trades
            st.sidebar.info("🔍 **Filtered Data Active**")
        else:
            trades_data = data["trades"]
            st.sidebar.info("📊 **All Data**")

        total_trades = len(trades_data)
        tp_trades = len(trades_data[trades_data["exit_reason"] == "take_profit"])
        sl_trades = len(trades_data[trades_data["exit_reason"] == "stop_loss"])

        st.sidebar.metric("Total Trades", total_trades)
        st.sidebar.metric("Take Profit", tp_trades)
        st.sidebar.metric("Stop Loss", sl_trades)

        # Показываем общую статистику для сравнения
        if st.session_state.filtered_trades is not None:
            st.sidebar.markdown("---")
            st.sidebar.markdown("### 📈 All Data (for comparison)")
            all_total = len(data["trades"])
            all_tp = len(data["trades"][data["trades"]["exit_reason"] == "take_profit"])
            all_sl = len(data["trades"][data["trades"]["exit_reason"] == "stop_loss"])

            st.sidebar.metric("All Trades", all_total)
            st.sidebar.metric("All TP", all_tp)
            st.sidebar.metric("All SL", all_sl)

    if "trade_conditions" in data:
        best_predictor = data["trade_conditions"].iloc[0]["metric_name"]
        best_auc = data["trade_conditions"].iloc[0]["auc_score"]
        st.sidebar.metric("Best Predictor", best_predictor.replace("_", " ").title())
        st.sidebar.metric("Best AUC", f"{best_auc:.3f}")

    # Футер
    st.markdown("---")
    st.markdown(
        """
    <div style='text-align: center; color: #666;'>
        <p>📊 Backtester Analysis Dashboard | Built with Streamlit</p>
        <p>💡 Tip: Use the sidebar to explore different aspects of your backtest results</p>
    </div>
    """,
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
