import os
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

# Добавляем путь к модулю
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(project_root, "src"))

# Настройка страницы
st.set_page_config(
    page_title="🚀 Advanced Trading Strategy Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Кастомный CSS для улучшения внешнего вида
st.markdown(
    """
<style>
    .main-header {
        font-size: 3rem;
        font-weight: bold;
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        margin-bottom: 2rem;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.1);
    }
    
    .metric-card {
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
        padding: 1.5rem;
        border-radius: 15px;
        border-left: 5px solid #667eea;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        margin-bottom: 1rem;
        transition: transform 0.3s ease;
    }
    
    .metric-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 12px rgba(0, 0, 0, 0.15);
    }
    
    .success-metric {
        border-left-color: #28a745;
        background: linear-gradient(135deg, #d4edda 0%, #c3e6cb 100%);
    }
    
    .warning-metric {
        border-left-color: #ffc107;
        background: linear-gradient(135deg, #fff3cd 0%, #ffeaa7 100%);
    }
    
    .danger-metric {
        border-left-color: #dc3545;
        background: linear-gradient(135deg, #f8d7da 0%, #f5c6cb 100%);
    }
    
    .info-metric {
        border-left-color: #17a2b8;
        background: linear-gradient(135deg, #d1ecf1 0%, #bee5eb 100%);
    }
    
    .section-header {
        font-size: 1.8rem;
        font-weight: bold;
        color: #2c3e50;
        margin: 2rem 0 1rem 0;
        padding: 0.5rem 0;
        border-bottom: 3px solid #3498db;
    }
    
    .insight-box {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 10px;
        margin: 1rem 0;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    
    .predictor-card {
        background: white;
        border: 1px solid #e0e0e0;
        border-radius: 10px;
        padding: 1rem;
        margin: 0.5rem 0;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
        transition: all 0.3s ease;
    }
    
    .predictor-card:hover {
        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.15);
        transform: translateY(-1px);
    }
    
    .stTabs [data-baseweb="tab-list"] {
        gap: 2px;
    }
    
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        background-color: #f0f2f6;
        border-radius: 4px 4px 0px 0px;
        gap: 1px;
        padding-left: 20px;
        padding-right: 20px;
    }
    
    .stTabs [aria-selected="true"] {
        background-color: #667eea;
        color: white;
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
        if f.is_dir()
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
        "entry_metrics": "entry_metrics.csv",
    }

    for key, filename in csv_files.items():
        file_path = results_folder / filename
        if file_path.exists():
            try:
                df = pd.read_csv(file_path)
                # Для metrics файла преобразуем в словарь для удобства
                if key == "metrics" and not df.empty:
                    if len(df) == 1:
                        metrics_dict = {}
                        for col in df.columns:
                            value = df.iloc[0][col]
                            if col in [
                                "exit_distribution",
                                "monthly_returns_pct",
                                "long_metrics",
                                "short_metrics",
                            ]:
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
                    if key == "equity_curve":
                        print(f"✅ Загружен {filename}: {df.shape}")
                        print(f"   Колонки equity_curve: {list(df.columns)}")
                        print("   Первые строки equity_curve:")
                        print(df.head())
            except Exception as e:
                st.error(f"Ошибка загрузки файла {filename}: {e}")

    return data, results_folder


def create_enhanced_metric_cards(metrics_data, data=None):
    """Создает улучшенные карточки с ключевыми метриками"""
    if metrics_data is None:
        return

    if isinstance(metrics_data, dict):
        if not metrics_data:
            return
    elif hasattr(metrics_data, "empty") and metrics_data.empty:
        return

    # Основные метрики в 2 ряда
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        total_return = metrics_data.get("total_return_pct", 0)
        if isinstance(total_return, pd.Series):
            total_return = total_return.iloc[0] if len(total_return) > 0 else 0

        # Определяем цветовую схему на основе результата
        if total_return > 20:
            color_class = "success-metric"
            icon = "🚀"
        elif total_return > 0:
            color_class = "info-metric"
            icon = "📈"
        elif total_return > -10:
            color_class = "warning-metric"
            icon = "⚠️"
        else:
            color_class = "danger-metric"
            icon = "📉"

        st.markdown(
            f"""
        <div class="metric-card {color_class}">
            <h3>{icon} Total Return</h3>
            <h2>{total_return:.2f}%</h2>
            <p>Общая доходность стратегии</p>
        </div>
        """,
            unsafe_allow_html=True,
        )

    with col2:
        win_rate = metrics_data.get("win_rate", 0)
        if isinstance(win_rate, pd.Series):
            win_rate = win_rate.iloc[0] if len(win_rate) > 0 else 0

        if win_rate > 60:
            color_class = "success-metric"
            icon = "🎯"
        elif win_rate > 50:
            color_class = "info-metric"
            icon = "✅"
        elif win_rate > 40:
            color_class = "warning-metric"
            icon = "⚖️"
        else:
            color_class = "danger-metric"
            icon = "❌"

        st.markdown(
            f"""
        <div class="metric-card {color_class}">
            <h3>{icon} Win Rate</h3>
            <h2>{win_rate:.1f}%</h2>
            <p>Процент прибыльных сделок</p>
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

        if profit_factor > 2.0:
            color_class = "success-metric"
            icon = "💰"
        elif profit_factor > 1.5:
            color_class = "info-metric"
            icon = "💵"
        elif profit_factor > 1.0:
            color_class = "warning-metric"
            icon = "💸"
        else:
            color_class = "danger-metric"
            icon = "💸"

        pf_display = "∞" if profit_factor == float("inf") else f"{profit_factor:.2f}"
        st.markdown(
            f"""
        <div class="metric-card {color_class}">
            <h3>{icon} Profit Factor</h3>
            <h2>{pf_display}</h2>
            <p>Соотношение прибыли к убыткам</p>
        </div>
        """,
            unsafe_allow_html=True,
        )

    with col4:
        max_dd = metrics_data.get("max_drawdown", 0)
        if isinstance(max_dd, pd.Series):
            max_dd = max_dd.iloc[0] if len(max_dd) > 0 else 0

        if max_dd > -5:
            color_class = "success-metric"
            icon = "🛡️"
        elif max_dd > -10:
            color_class = "info-metric"
            icon = "⚡"
        elif max_dd > -20:
            color_class = "warning-metric"
            icon = "⚠️"
        else:
            color_class = "danger-metric"
            icon = "🚨"

        st.markdown(
            f"""
        <div class="metric-card {color_class}">
            <h3>{icon} Max Drawdown</h3>
            <h2>{max_dd:.2f}%</h2>
            <p>Максимальная просадка</p>
        </div>
        """,
            unsafe_allow_html=True,
        )

    # Дополнительные метрики во втором ряду
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        total_trades = metrics_data.get("total_trades", 0)
        if isinstance(total_trades, pd.Series):
            total_trades = total_trades.iloc[0] if len(total_trades) > 0 else 0

        st.markdown(
            f"""
        <div class="metric-card info-metric">
            <h3>📊 Total Trades</h3>
            <h2>{total_trades}</h2>
            <p>Общее количество сделок</p>
        </div>
        """,
            unsafe_allow_html=True,
        )

    with col2:
        avg_trade = metrics_data.get("avg_trade", 0)
        if isinstance(avg_trade, pd.Series):
            avg_trade = avg_trade.iloc[0] if len(avg_trade) > 0 else 0

        # Если avg_trade равен 0, пытаемся вычислить из данных сделок
        if avg_trade == 0 and "trades" in data and not data["trades"].empty:
            if "pnl_abs" in data["trades"].columns:
                avg_trade = data["trades"]["pnl_abs"].mean()

        color_class = "success-metric" if avg_trade > 0 else "danger-metric"
        icon = "💎" if avg_trade > 0 else "📉"

        st.markdown(
            f"""
        <div class="metric-card {color_class}">
            <h3>{icon} Avg Trade</h3>
            <h2>${avg_trade:.2f}</h2>
            <p>Средняя прибыль на сделку</p>
        </div>
        """,
            unsafe_allow_html=True,
        )

    with col3:
        sharpe_ratio = metrics_data.get("sharpe_ratio", 0)
        if isinstance(sharpe_ratio, pd.Series):
            sharpe_ratio = sharpe_ratio.iloc[0] if len(sharpe_ratio) > 0 else 0

        # Если sharpe_ratio равен 0, пытаемся вычислить из данных сделок
        if sharpe_ratio == 0 and "trades" in data and not data["trades"].empty:
            if "pnl_abs" in data["trades"].columns:
                returns = data["trades"]["pnl_abs"]
                if len(returns) > 1 and returns.std() > 0:
                    sharpe_ratio = (
                        returns.mean() / returns.std() * np.sqrt(252)
                    )  # Годовая нормализация

        if sharpe_ratio > 2:
            color_class = "success-metric"
            icon = "⭐"
        elif sharpe_ratio > 1:
            color_class = "info-metric"
            icon = "🌟"
        elif sharpe_ratio > 0:
            color_class = "warning-metric"
            icon = "✨"
        else:
            color_class = "danger-metric"
            icon = "💫"

        st.markdown(
            f"""
        <div class="metric-card {color_class}">
            <h3>{icon} Sharpe Ratio</h3>
            <h2>{sharpe_ratio:.2f}</h2>
            <p>Коэффициент Шарпа</p>
            <small>Отношение доходности к риску (годовая нормализация)</small>
        </div>
        """,
            unsafe_allow_html=True,
        )

    with col4:
        avg_duration = metrics_data.get("avg_duration", 0)
        if isinstance(avg_duration, pd.Series):
            avg_duration = avg_duration.iloc[0] if len(avg_duration) > 0 else 0

        # Если avg_duration равен 0, пытаемся вычислить из данных сделок
        if avg_duration == 0 and "trades" in data and not data["trades"].empty:
            if "duration" in data["trades"].columns:
                avg_duration = data["trades"]["duration"].mean()

        st.markdown(
            f"""
        <div class="metric-card info-metric">
            <h3>⏱️ Avg Duration</h3>
            <h2>{avg_duration:.1f}</h2>
            <p>Средняя длительность сделки (бары)</p>
        </div>
        """,
            unsafe_allow_html=True,
        )


def create_equity_curve_analysis(equity_data, trades_data):
    """Создает детальный анализ кривой капитала"""
    if equity_data is None or equity_data.empty:
        st.warning("⚠️ Данные кривой капитала не загружены или пусты")
        return

    st.markdown(
        '<h2 class="section-header">📈 Анализ Кривой Капитала</h2>',
        unsafe_allow_html=True,
    )

    # Добавляем прогресс-бар
    progress_bar = st.progress(0)
    status_text = st.empty()

    try:
        status_text.text("🔄 Подготовка данных...")
        progress_bar.progress(10)

        # Подготавливаем данные
        equity_df = equity_data.copy()

        status_text.text("🔄 Обработка временных меток...")
        progress_bar.progress(20)

        # Если данные имеют колонку exit_time, используем её как индекс
        if "exit_time" in equity_df.columns:
            equity_df["exit_time"] = pd.to_datetime(equity_df["exit_time"])
            equity_df = equity_df.set_index("exit_time")
            equity_column = (
                "capital_after"
                if "capital_after" in equity_df.columns
                else equity_df.columns[0]
            )
        else:
            # Если нет колонки времени, используем индекс
            equity_df.index = pd.to_datetime(equity_df.index)
            equity_column = equity_df.columns[0]

        status_text.text("🔄 Конвертация числовых данных...")
        progress_bar.progress(40)

        equity_df[equity_column] = pd.to_numeric(
            equity_df[equity_column], errors="coerce"
        )
        equity_df = equity_df.dropna()

        status_text.text("🔄 Проверка данных...")
        progress_bar.progress(60)

        # Проверяем, что данные не пустые
        if equity_df.empty:
            st.warning(
                "⚠️ Данные кривой капитала пусты или содержат только NaN значения"
            )
            st.write("Отладочная информация:")
            st.write(f"Исходные данные: {equity_data.shape}")
            st.write(f"Колонки: {list(equity_data.columns)}")
            st.write("Первые строки:")
            st.write(equity_data.head())
            return

        # Проверяем, что есть минимум 2 точки для расчета
        if len(equity_df) < 2:
            st.warning(
                "⚠️ Недостаточно данных для анализа кривой капитала (нужно минимум 2 точки)"
            )
            return

        status_text.text("🔄 Создание графиков...")
        progress_bar.progress(80)

        # Ограничиваем количество точек для производительности
        max_points = 1000
        if len(equity_df) > max_points:
            # Берем каждую N-ю точку для равномерного распределения
            step = len(equity_df) // max_points
            equity_df = equity_df.iloc[::step]
            status_text.text(f"🔄 Ограничение данных до {len(equity_df)} точек...")

        # Создаем подграфики
        fig = make_subplots(
            rows=3,
            cols=1,
            subplot_titles=("Кривая капитала", "Дневные доходности", "Просадки"),
            vertical_spacing=0.08,
            row_heights=[0.5, 0.25, 0.25],
        )

        status_text.text("🔄 Добавление кривой капитала...")
        progress_bar.progress(85)

        # Основная кривая капитала
        fig.add_trace(
            go.Scatter(
                x=equity_df.index,
                y=equity_df[equity_column],
                mode="lines",
                name="Capital",
                line=dict(color="#667eea", width=2),
                fill="tonexty",
            ),
            row=1,
            col=1,
        )

        status_text.text("🔄 Расчет доходностей...")
        progress_bar.progress(90)

        # Дневные доходности (упрощенная версия)
        daily_returns = equity_df[equity_column].pct_change().dropna()
        # Ограничиваем количество баров для производительности
        if len(daily_returns) > 500:
            daily_returns = daily_returns.iloc[:: len(daily_returns) // 500]

        fig.add_trace(
            go.Bar(
                x=daily_returns.index,
                y=daily_returns * 100,
                name="Daily Returns %",
                marker_color=["green" if x > 0 else "red" for x in daily_returns],
                opacity=0.7,
            ),
            row=2,
            col=1,
        )

        status_text.text("🔄 Расчет просадок...")
        progress_bar.progress(95)

        # Просадки
        rolling_max = equity_df[equity_column].expanding().max()
        drawdown = (equity_df[equity_column] - rolling_max) / rolling_max * 100

        fig.add_trace(
            go.Scatter(
                x=drawdown.index,
                y=drawdown,
                mode="lines",
                name="Drawdown %",
                line=dict(color="red", width=2),
                fill="tonexty",
            ),
            row=3,
            col=1,
        )

        status_text.text("🔄 Добавление сделок...")

        # Добавляем сделки если есть данные (ограничиваем количество для производительности)
        if trades_data is not None and not trades_data.empty:
            trades = trades_data.copy()
            trades["entry_time"] = pd.to_datetime(trades["entry_time"])
            trades["exit_time"] = pd.to_datetime(trades["exit_time"])

            # Ограничиваем количество сделок для отображения (максимум 50)
            if len(trades) > 50:
                trades = trades.sample(50)

            # Добавляем маркеры входов (упрощенная версия)
            for _, trade in trades.iterrows():
                color = "green" if trade["pnl_abs"] > 0 else "red"
                fig.add_vline(
                    x=trade["entry_time"],
                    line=dict(color=color, width=1, dash="dot"),
                    row=1,
                    col=1,
                )

        status_text.text("🔄 Финальная настройка графика...")

        fig.update_layout(
            height=600,  # Уменьшили высоту для производительности
            showlegend=False,
            title_text="Детальный анализ кривой капитала",
            title_x=0.5,
        )

        fig.update_xaxes(title_text="Время", row=3, col=1)
        fig.update_yaxes(title_text="Капитал ($)", row=1, col=1)
        fig.update_yaxes(title_text="Доходность (%)", row=2, col=1)
        fig.update_yaxes(title_text="Просадка (%)", row=3, col=1)

        status_text.text("🔄 Отображение графика...")
        st.plotly_chart(
            fig,
            config={"displayModeBar": True, "displaylogo": False, "width": "stretch"},
        )

        # Статистика по кривой капитала
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            if len(equity_df) >= 2:
                total_return = (
                    (
                        equity_df[equity_column].iloc[-1]
                        - equity_df[equity_column].iloc[0]
                    )
                    / equity_df[equity_column].iloc[0]
                    * 100
                )
                st.metric("Общая доходность", f"{total_return:.2f}%")
            else:
                st.metric("Общая доходность", "N/A")

        with col2:
            if len(drawdown) > 0:
                max_dd = drawdown.min()
                st.metric("Максимальная просадка", f"{max_dd:.2f}%")
            else:
                st.metric("Максимальная просадка", "N/A")

        with col3:
            if len(daily_returns) > 0 and daily_returns.std() > 0:
                volatility = (
                    daily_returns.std() * np.sqrt(252) * 100
                )  # Годовая волатильность
                st.metric("Годовая волатильность", f"{volatility:.2f}%")
            else:
                st.metric("Годовая волатильность", "N/A")

        with col4:
            if len(daily_returns) > 0 and daily_returns.std() > 0:
                sharpe = daily_returns.mean() / daily_returns.std() * np.sqrt(252)
                st.metric("Коэффициент Шарпа", f"{sharpe:.2f}")
            else:
                st.metric("Коэффициент Шарпа", "N/A")

        # Завершаем прогресс-бар
        progress_bar.progress(100)
        status_text.text("✅ Анализ кривой капитала завершен!")

    except Exception as e:
        st.error(f"❌ Ошибка при создании анализа кривой капитала: {str(e)}")

        # Показываем простой график как fallback
        st.warning("🔄 Показываем упрощенную версию графика...")
        try:
            # Простой график кривой капитала
            if "exit_time" in equity_data.columns:
                equity_simple = equity_data[["exit_time", "capital_after"]].copy()
                equity_simple["exit_time"] = pd.to_datetime(equity_simple["exit_time"])
                equity_simple = equity_simple.set_index("exit_time")
            else:
                equity_simple = equity_data.copy()
                equity_simple.index = pd.to_datetime(equity_simple.index)

            # Ограничиваем до 100 точек
            if len(equity_simple) > 100:
                equity_simple = equity_simple.iloc[:: len(equity_simple) // 100]

            fig_simple = go.Figure()
            fig_simple.add_trace(
                go.Scatter(
                    x=equity_simple.index,
                    y=equity_simple.iloc[:, 0],
                    mode="lines",
                    name="Capital",
                    line=dict(color="#667eea", width=2),
                )
            )

            fig_simple.update_layout(
                title="Кривая капитала (упрощенная версия)",
                xaxis_title="Время",
                yaxis_title="Капитал ($)",
                height=400,
            )

            st.plotly_chart(
                fig_simple,
                config={
                    "displayModeBar": True,
                    "displaylogo": False,
                    "width": "stretch",
                },
            )

        except Exception as e2:
            st.error(f"❌ Не удалось создать даже упрощенный график: {str(e2)}")

        st.write("Отладочная информация:")
        st.write(f"Тип данных equity_data: {type(equity_data)}")
        if hasattr(equity_data, "shape"):
            st.write(f"Размер данных: {equity_data.shape}")
        if hasattr(equity_data, "columns"):
            st.write(f"Колонки: {list(equity_data.columns)}")
        st.write("Первые строки:")
        st.write(
            equity_data.head() if hasattr(equity_data, "head") else str(equity_data)
        )
    finally:
        # Очищаем прогресс-бар
        progress_bar.empty()
        status_text.empty()


def create_trade_analysis(trades_data):
    """Создает детальный анализ сделок"""
    if trades_data is None or trades_data.empty:
        return

    st.markdown(
        '<h2 class="section-header">🎯 Анализ Сделок</h2>', unsafe_allow_html=True
    )

    trades = trades_data.copy()
    trades["entry_time"] = pd.to_datetime(trades["entry_time"])
    trades["exit_time"] = pd.to_datetime(trades["exit_time"])
    trades["duration"] = (
        trades["exit_time"] - trades["entry_time"]
    ).dt.total_seconds() / 3600  # в часах

    # Создаем табы для разных видов анализа
    tab1, tab2, tab3, tab4 = st.tabs(
        [
            "📊 Общая статистика",
            "⏰ Временной анализ",
            "📈 Распределение PnL",
            "🔄 Паттерны сделок",
        ]
    )

    with tab1:
        col1, col2 = st.columns(2)

        with col1:
            # Распределение по исходу сделок
            exit_counts = trades["exit_reason"].value_counts()
            colors = [
                "#28a745"
                if reason == "take_profit"
                else "#dc3545"
                if reason == "stop_loss"
                else "#ffc107"
                for reason in exit_counts.index
            ]

            fig = px.pie(
                values=exit_counts.values,
                names=exit_counts.index,
                title="Распределение исходов сделок",
                color_discrete_sequence=colors,
            )
            fig.update_traces(textposition="inside", textinfo="percent+label")
            st.plotly_chart(
                fig,
                config={
                    "displayModeBar": True,
                    "displaylogo": False,
                    "width": "stretch",
                },
            )

        with col2:
            # Статистика по направлениям
            if "is_long" in trades.columns:
                direction_stats = (
                    trades.groupby("is_long")
                    .agg(
                        {
                            "pnl_abs": ["count", "sum", "mean"],
                            "exit_reason": lambda x: (x == "take_profit").sum()
                            / len(x)
                            * 100,
                        }
                    )
                    .round(2)
                )

                direction_stats.columns = [
                    "Количество",
                    "Общий PnL",
                    "Средний PnL",
                    "Win Rate %",
                ]
                direction_stats.index = ["Short", "Long"]

                st.subheader("Статистика по направлениям")
                st.dataframe(direction_stats, width="stretch")
            else:
                st.info("Колонка 'is_long' не найдена в данных сделок")

    with tab2:
        col1, col2 = st.columns(2)

        with col1:
            # Анализ по часам дня
            if "entry_time" in trades.columns:
                trades["hour"] = trades["entry_time"].dt.hour
                hourly_stats = (
                    trades.groupby("hour")
                    .agg(
                        {
                            "pnl_abs": ["count", "sum", "mean"],
                            "exit_reason": lambda x: (x == "take_profit").sum()
                            / len(x)
                            * 100,
                        }
                    )
                    .round(2)
                )

                hourly_stats.columns = [
                    "Сделок",
                    "Общий PnL",
                    "Средний PnL",
                    "Win Rate %",
                ]

                if not hourly_stats.empty:
                    fig = px.bar(
                        hourly_stats.reset_index(),
                        x="hour",
                        y="Win Rate %",
                        title="Win Rate по часам дня",
                        color="Win Rate %",
                        color_continuous_scale="RdYlGn",
                    )
                    st.plotly_chart(
                        fig,
                        config={
                            "displayModeBar": True,
                            "displaylogo": False,
                            "width": "stretch",
                        },
                    )
                else:
                    st.info("Недостаточно данных для анализа по часам")
            else:
                st.info("Колонка 'entry_time' не найдена в данных сделок")

        with col2:
            # Анализ по дням недели
            if "entry_time" in trades.columns:
                trades["day_of_week"] = trades["entry_time"].dt.day_name()
                daily_stats = (
                    trades.groupby("day_of_week")
                    .agg(
                        {
                            "pnl_abs": ["count", "sum", "mean"],
                            "exit_reason": lambda x: (x == "take_profit").sum()
                            / len(x)
                            * 100,
                        }
                    )
                    .round(2)
                )

                daily_stats.columns = [
                    "Сделок",
                    "Общий PnL",
                    "Средний PnL",
                    "Win Rate %",
                ]

                if not daily_stats.empty:
                    fig = px.bar(
                        daily_stats.reset_index(),
                        x="day_of_week",
                        y="Средний PnL",
                        title="Средний PnL по дням недели",
                        color="Средний PnL",
                        color_continuous_scale="RdYlGn",
                    )
                    st.plotly_chart(
                        fig,
                        config={
                            "displayModeBar": True,
                            "displaylogo": False,
                            "width": "stretch",
                        },
                    )
                else:
                    st.info("Недостаточно данных для анализа по дням недели")
            else:
                st.info("Колонка 'entry_time' не найдена в данных сделок")

    with tab3:
        col1, col2 = st.columns(2)

        with col1:
            # Гистограмма PnL
            fig = go.Figure()

            for reason in trades["exit_reason"].unique():
                data = trades[trades["exit_reason"] == reason]["pnl_abs"]
                color = "#28a745" if reason == "take_profit" else "#dc3545"

                fig.add_trace(
                    go.Histogram(
                        x=data,
                        name=reason.replace("_", " ").title(),
                        opacity=0.7,
                        marker_color=color,
                        nbinsx=20,
                    )
                )

            fig.update_layout(
                title="Распределение PnL по исходам",
                xaxis_title="PnL ($)",
                yaxis_title="Количество",
                barmode="overlay",
            )
            st.plotly_chart(
                fig,
                config={
                    "displayModeBar": True,
                    "displaylogo": False,
                    "width": "stretch",
                },
            )

        with col2:
            # Box plot PnL
            fig = go.Figure()

            for reason in trades["exit_reason"].unique():
                data = trades[trades["exit_reason"] == reason]["pnl_abs"]
                color = "#28a745" if reason == "take_profit" else "#dc3545"

                fig.add_trace(
                    go.Box(
                        y=data,
                        name=reason.replace("_", " ").title(),
                        marker_color=color,
                        boxpoints="outliers",
                    )
                )

            fig.update_layout(title="Box Plot PnL по исходам", yaxis_title="PnL ($)")
            st.plotly_chart(
                fig,
                config={
                    "displayModeBar": True,
                    "displaylogo": False,
                    "width": "stretch",
                },
            )

    with tab4:
        # Анализ последовательных сделок
        col1, col2 = st.columns(2)

        with col1:
            # Анализ серий
            if "entry_time" in trades.columns and "pnl_abs" in trades.columns:
                trades_sorted = trades.sort_values("entry_time")
                trades_sorted["win"] = trades_sorted["pnl_abs"] > 0
                trades_sorted["series"] = (
                    trades_sorted["win"] != trades_sorted["win"].shift()
                ).cumsum()

                series_stats = trades_sorted.groupby("series").agg(
                    {"win": ["count", "sum"], "pnl_abs": "sum"}
                )
                series_stats.columns = ["Длина серии", "Побед в серии", "PnL серии"]

                if not series_stats.empty:
                    # Топ-5 лучших и худших серий
                    best_series = series_stats.nlargest(5, "PnL серии")
                    worst_series = series_stats.nsmallest(5, "PnL серии")

                    st.subheader("🏆 Топ-5 лучших серий")
                    st.dataframe(best_series, width="stretch")

                    st.subheader("💥 Топ-5 худших серий")
                    st.dataframe(worst_series, width="stretch")
                else:
                    st.info("Недостаточно данных для анализа серий")
            else:
                st.info("Необходимые колонки 'entry_time' или 'pnl_abs' не найдены")

        with col2:
            # Анализ длительности сделок
            if "duration" in trades.columns and "exit_reason" in trades.columns:
                fig = px.histogram(
                    trades,
                    x="duration",
                    title="Распределение длительности сделок",
                    nbins=20,
                    color="exit_reason",
                    color_discrete_map={
                        "take_profit": "#28a745",
                        "stop_loss": "#dc3545",
                        "ttl_expired": "#ffc107",
                    },
                )
                fig.update_xaxes(title_text="Длительность (часы)")
                fig.update_yaxes(title_text="Количество")
                st.plotly_chart(
                    fig,
                    config={
                        "displayModeBar": True,
                        "displaylogo": False,
                        "width": "stretch",
                    },
                )
            else:
                st.info(
                    "Колонки 'duration' или 'exit_reason' не найдены в данных сделок"
                )


def create_predictor_analysis(conditions_data, entry_metrics_data):
    """Создает детальный анализ предикторов"""
    if conditions_data is None or conditions_data.empty:
        st.warning("⚠️ Данные условий торговли недоступны")
        return

    st.markdown(
        '<h2 class="section-header">🔍 Анализ Предикторов</h2>', unsafe_allow_html=True
    )

    # Топ предикторы
    top_predictors = conditions_data.head(10)

    # Создаем табы для разных видов анализа
    tab1, tab2, tab3, tab4 = st.tabs(
        [
            "🏆 Топ предикторы",
            "📊 Корреляции",
            "🎯 Интерактивный анализ",
            "💡 Рекомендации",
        ]
    )

    with tab1:
        # Создаем отдельные графики для Long и Short
        col1, col2 = st.columns(2)

        with col1:
            # Фильтруем данные для Long позиций
            long_predictors = conditions_data[
                conditions_data["metric_name"].str.contains("_long$", na=False)
            ].head(10)
            if not long_predictors.empty:
                fig = px.bar(
                    long_predictors,
                    x="auc_score",
                    y="metric_name",
                    orientation="h",
                    title="AUC Scores - Long позиции (Топ 10)",
                    color="auc_score",
                    color_continuous_scale=["red", "yellow", "green"],
                    range_color=[0, 1],
                )
                fig.add_vline(
                    x=0.5,
                    line_dash="dash",
                    line_color="black",
                    annotation_text="Случайный (0.5)",
                )
                fig.update_layout(height=500)
                st.plotly_chart(
                    fig,
                    config={
                        "displayModeBar": True,
                        "displaylogo": False,
                        "width": "stretch",
                    },
                )
            else:
                st.info("Нет данных для Long позиций")

        with col2:
            # Фильтруем данные для Short позиций
            short_predictors = conditions_data[
                conditions_data["metric_name"].str.contains("_short$", na=False)
            ].head(10)
            if not short_predictors.empty:
                fig = px.bar(
                    short_predictors,
                    x="auc_score",
                    y="metric_name",
                    orientation="h",
                    title="AUC Scores - Short позиции (Топ 10)",
                    color="auc_score",
                    color_continuous_scale=["red", "yellow", "green"],
                    range_color=[0, 1],
                )
                fig.add_vline(
                    x=0.5,
                    line_dash="dash",
                    line_color="black",
                    annotation_text="Случайный (0.5)",
                )
                fig.update_layout(height=500)
                st.plotly_chart(
                    fig,
                    config={
                        "displayModeBar": True,
                        "displaylogo": False,
                        "width": "stretch",
                    },
                )
            else:
                st.info("Нет данных для Short позиций")

        # Общий график для сравнения
        st.subheader("📊 Сравнение Long vs Short")
        col1, col2 = st.columns(2)

        with col1:
            # KS Statistic для Long
            if not long_predictors.empty:
                fig = px.bar(
                    long_predictors,
                    x="ks_statistic",
                    y="metric_name",
                    orientation="h",
                    title="KS Statistics - Long позиции",
                    color="ks_statistic",
                    color_continuous_scale="Blues",
                )
                fig.update_layout(height=400)
                st.plotly_chart(
                    fig,
                    config={
                        "displayModeBar": True,
                        "displaylogo": False,
                        "width": "stretch",
                    },
                )

        with col2:
            # KS Statistic для Short
            if not short_predictors.empty:
                fig = px.bar(
                    short_predictors,
                    x="ks_statistic",
                    y="metric_name",
                    orientation="h",
                    title="KS Statistics - Short позиции",
                    color="ks_statistic",
                    color_continuous_scale="Blues",
                )
                fig.update_layout(height=400)
                st.plotly_chart(
                    fig,
                    config={
                        "displayModeBar": True,
                        "displaylogo": False,
                        "width": "stretch",
                    },
                )

        # Детальные таблицы для Long и Short
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("📊 Long позиции - Топ предикторы")
            if not long_predictors.empty:
                long_display = long_predictors.copy()
                long_display["metric_name"] = (
                    long_display["metric_name"]
                    .str.replace("_long$", "", regex=True)
                    .str.replace("_", " ")
                    .str.title()
                )

                # Округляем числовые значения
                numeric_cols = [
                    "auc_score",
                    "ks_statistic",
                    "js_divergence",
                    "gini_coefficient",
                ]
                for col in numeric_cols:
                    if col in long_display.columns:
                        long_display[col] = long_display[col].round(3)

                st.dataframe(
                    long_display[
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
                        "metric_name": "Метрика",
                        "auc_score": st.column_config.NumberColumn(
                            "AUC", format="%.3f"
                        ),
                        "ks_statistic": st.column_config.NumberColumn(
                            "KS", format="%.3f"
                        ),
                        "js_divergence": st.column_config.NumberColumn(
                            "JS", format="%.3f"
                        ),
                        "tp_count": "TP Count",
                        "sl_count": "SL Count",
                    },
                )
            else:
                st.info("Нет данных для Long позиций")

        with col2:
            st.subheader("📊 Short позиции - Топ предикторы")
            if not short_predictors.empty:
                short_display = short_predictors.copy()
                short_display["metric_name"] = (
                    short_display["metric_name"]
                    .str.replace("_short$", "", regex=True)
                    .str.replace("_", " ")
                    .str.title()
                )

                # Округляем числовые значения
                numeric_cols = [
                    "auc_score",
                    "ks_statistic",
                    "js_divergence",
                    "gini_coefficient",
                ]
                for col in numeric_cols:
                    if col in short_display.columns:
                        short_display[col] = short_display[col].round(3)

                st.dataframe(
                    short_display[
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
                        "metric_name": "Метрика",
                        "auc_score": st.column_config.NumberColumn(
                            "AUC", format="%.3f"
                        ),
                        "ks_statistic": st.column_config.NumberColumn(
                            "KS", format="%.3f"
                        ),
                        "js_divergence": st.column_config.NumberColumn(
                            "JS", format="%.3f"
                        ),
                        "tp_count": "TP Count",
                        "sl_count": "SL Count",
                    },
                )
            else:
                st.info("Нет данных для Short позиций")

    with tab2:
        # Корреляционная матрица
        if len(top_predictors) > 1:
            available_metrics = []
            potential_metrics = [
                "auc_score",
                "ks_statistic",
                "js_divergence",
                "gini_coefficient",
                "mutual_information",
            ]

            for metric in potential_metrics:
                if metric in top_predictors.columns:
                    available_metrics.append(metric)

            if available_metrics:
                correlation_data = top_predictors[available_metrics].corr()

                fig = px.imshow(
                    correlation_data,
                    text_auto=True,
                    aspect="auto",
                    color_continuous_scale="RdBu",
                    title="Корреляция между метриками разделения",
                )
                st.plotly_chart(
                    fig,
                    config={
                        "displayModeBar": True,
                        "displaylogo": False,
                        "width": "stretch",
                    },
                )

    with tab3:
        # Интерактивный анализ распределений
        if entry_metrics_data is not None and not entry_metrics_data.empty:
            st.subheader("🎯 Интерактивный анализ распределений")

            # Создаем селектор метрик из entry_metrics_data
            exclude_cols = [
                "trade_id",
                "symbol",
                "entry_time",
                "exit_reason",
                "pnl_abs",
                "is_long",
                "entry_price",
            ]
            metric_options = [
                col for col in entry_metrics_data.columns if col not in exclude_cols
            ]
            metric_display_names = [
                name.replace("_", " ").title() for name in metric_options
            ]

            metric_mapping = dict(zip(metric_display_names, metric_options))

            # Показываем информацию о количестве метрик
            st.info(f"📈 Доступно {len(metric_options)} метрик для анализа")

            col1, col2, col3 = st.columns([2, 1, 1])

            with col1:
                st.markdown("**Выберите метрику для анализа:**")

                # Создаем прокручиваемый контейнер
                with st.container():
                    # Добавляем CSS для прокрутки
                    st.markdown(
                        """
                    <style>
                    .stRadio > div {
                        max-height: 300px;
                        overflow-y: auto;
                        border: 1px solid #ddd;
                        border-radius: 5px;
                        padding: 10px;
                        background-color: #f8f9fa;
                    }
                    </style>
                    """,
                        unsafe_allow_html=True,
                    )

                    selected_display_name = st.radio(
                        "",
                        options=metric_display_names,
                        index=0,
                        help="Выберите метрику для построения распределений TP vs SL",
                    )

            with col2:
                show_stats = st.checkbox("Показать статистики", value=True)

            with col3:
                show_direction = st.selectbox(
                    "Направление:",
                    options=["Все", "Long", "Short"],
                    index=0,
                    help="Фильтр по направлению позиций",
                )

            selected_metric = metric_mapping[selected_display_name]

            # Получаем данные для выбранной метрики
            if selected_metric in entry_metrics_data.columns:
                # Применяем фильтр по направлению
                filtered_data = entry_metrics_data.copy()
                if show_direction == "Long":
                    filtered_data = filtered_data[filtered_data["is_long"] == True]
                elif show_direction == "Short":
                    filtered_data = filtered_data[filtered_data["is_long"] == False]

                # Разделяем данные по исходу сделок
                tp_data = filtered_data[filtered_data["exit_reason"] == "take_profit"][
                    selected_metric
                ].dropna()

                sl_data = filtered_data[filtered_data["exit_reason"] == "stop_loss"][
                    selected_metric
                ].dropna()

                # Всегда показываем распределение
                metric_data = filtered_data[selected_metric].dropna()
                if len(metric_data) > 0:
                    col1, col2 = st.columns(2)

                    with col1:
                        # Гистограммы
                        fig = go.Figure()

                        # Вычисляем общие границы для обеих гистограмм
                        all_data = (
                            pd.concat([tp_data, sl_data])
                            if len(tp_data) > 0 and len(sl_data) > 0
                            else (tp_data if len(tp_data) > 0 else sl_data)
                        )

                        if len(all_data) > 0:
                            data_min = all_data.min()
                            data_max = all_data.max()
                            bin_size = (data_max - data_min) / 60  # 60 бинов

                            # Добавляем TP данные если есть
                            if len(tp_data) > 0:
                                fig.add_trace(
                                    go.Histogram(
                                        x=tp_data,
                                        name="Take Profit",
                                        opacity=0.7,
                                        marker_color="green",
                                        xbins=dict(
                                            start=data_min, end=data_max, size=bin_size
                                        ),
                                    )
                                )

                            # Добавляем SL данные если есть
                            if len(sl_data) > 0:
                                fig.add_trace(
                                    go.Histogram(
                                        x=sl_data,
                                        name="Stop Loss",
                                        opacity=0.7,
                                        marker_color="red",
                                        xbins=dict(
                                            start=data_min, end=data_max, size=bin_size
                                        ),
                                    )
                                )

                        # Если нет данных TP/SL, показываем общее распределение
                        if len(tp_data) == 0 and len(sl_data) == 0:
                            fig.add_trace(
                                go.Histogram(
                                    x=metric_data,
                                    name="Все данные",
                                    opacity=0.7,
                                    marker_color="lightblue",
                                    nbinsx=60,
                                )
                            )

                        direction_suffix = (
                            f" ({show_direction})" if show_direction != "Все" else ""
                        )
                        fig.update_layout(
                            title=f"Распределение: {selected_display_name}{direction_suffix}",
                            xaxis_title=selected_display_name,
                            yaxis_title="Количество",
                            barmode="overlay",
                        )

                        st.plotly_chart(
                            fig,
                            config={
                                "displayModeBar": True,
                                "displaylogo": False,
                                "width": "stretch",
                            },
                        )

                    with col2:
                        # Box plots
                        fig = go.Figure()

                        # Добавляем TP данные если есть
                        if len(tp_data) > 0:
                            fig.add_trace(
                                go.Box(
                                    y=tp_data,
                                    name="Take Profit",
                                    marker_color="green",
                                    boxpoints="outliers",
                                )
                            )

                        # Добавляем SL данные если есть
                        if len(sl_data) > 0:
                            fig.add_trace(
                                go.Box(
                                    y=sl_data,
                                    name="Stop Loss",
                                    marker_color="red",
                                    boxpoints="outliers",
                                )
                            )

                        # Если нет данных TP/SL, показываем общее распределение
                        if len(tp_data) == 0 and len(sl_data) == 0:
                            fig.add_trace(
                                go.Box(
                                    y=metric_data,
                                    name="Все данные",
                                    marker_color="lightblue",
                                    boxpoints="outliers",
                                )
                            )

                        fig.update_layout(
                            title=f"Box Plot: {selected_display_name}{direction_suffix}",
                            yaxis_title=selected_display_name,
                        )

                        st.plotly_chart(
                            fig,
                            config={
                                "displayModeBar": True,
                                "displaylogo": False,
                                "width": "stretch",
                            },
                        )

                    # Статистики
                    if show_stats:
                        col1, col2, col3, col4 = st.columns(4)

                        with col1:
                            st.metric(
                                "Среднее",
                                f"{metric_data.mean():.4f}",
                                help="Среднее значение метрики",
                            )

                        with col2:
                            st.metric(
                                "Медиана",
                                f"{metric_data.median():.4f}",
                                help="Медианное значение метрики",
                            )

                        with col3:
                            st.metric(
                                "Стд. отклонение",
                                f"{metric_data.std():.4f}",
                                help="Стандартное отклонение",
                            )

                        with col4:
                            st.metric(
                                "Количество",
                                f"{len(metric_data)}",
                                help="Количество значений",
                            )
                else:
                    st.warning(
                        f"Недостаточно данных для метрики {selected_display_name}"
                    )
            else:
                st.warning(f"Метрика {selected_metric} не найдена в данных")

    with tab4:
        # Рекомендации по использованию предикторов
        st.subheader("💡 Рекомендации по использованию предикторов")

        col1, col2 = st.columns(2)

        with col1:
            st.subheader("📈 Long позиции")
            if not long_predictors.empty:
                # Анализируем Long предикторы
                excellent_long = long_predictors[long_predictors["auc_score"] > 0.7]
                good_long = long_predictors[
                    (long_predictors["auc_score"] > 0.6)
                    & (long_predictors["auc_score"] <= 0.7)
                ]
                weak_long = long_predictors[long_predictors["auc_score"] <= 0.6]

                if not excellent_long.empty:
                    st.success("🎯 **Отличные Long предикторы (AUC > 0.7):**")
                    for _, pred in excellent_long.iterrows():
                        metric_name = (
                            pred["metric_name"]
                            .replace("_long", "")
                            .replace("_", " ")
                            .title()
                        )
                        st.write(f"• **{metric_name}** - AUC: {pred['auc_score']:.3f}")
                    st.write(
                        "Рекомендация: Используйте эти метрики как основные фильтры для Long позиций."
                    )

                if not good_long.empty:
                    st.warning("⚠️ **Хорошие Long предикторы (AUC 0.6-0.7):**")
                    for _, pred in good_long.iterrows():
                        metric_name = (
                            pred["metric_name"]
                            .replace("_long", "")
                            .replace("_", " ")
                            .title()
                        )
                        st.write(f"• **{metric_name}** - AUC: {pred['auc_score']:.3f}")
                    st.write(
                        "Рекомендация: Используйте как дополнительные фильтры для Long позиций."
                    )

                if not weak_long.empty:
                    st.error("❌ **Слабые Long предикторы (AUC ≤ 0.6):**")
                    for _, pred in weak_long.iterrows():
                        metric_name = (
                            pred["metric_name"]
                            .replace("_long", "")
                            .replace("_", " ")
                            .title()
                        )
                        st.write(f"• **{metric_name}** - AUC: {pred['auc_score']:.3f}")
                    st.write(
                        "Рекомендация: Избегайте использования этих метрик для Long позиций."
                    )
            else:
                st.info("Нет данных для Long позиций")

        with col2:
            st.subheader("📉 Short позиции")
            if not short_predictors.empty:
                # Анализируем Short предикторы
                excellent_short = short_predictors[short_predictors["auc_score"] > 0.7]
                good_short = short_predictors[
                    (short_predictors["auc_score"] > 0.6)
                    & (short_predictors["auc_score"] <= 0.7)
                ]
                weak_short = short_predictors[short_predictors["auc_score"] <= 0.6]

                if not excellent_short.empty:
                    st.success("🎯 **Отличные Short предикторы (AUC > 0.7):**")
                    for _, pred in excellent_short.iterrows():
                        metric_name = (
                            pred["metric_name"]
                            .replace("_short", "")
                            .replace("_", " ")
                            .title()
                        )
                        st.write(f"• **{metric_name}** - AUC: {pred['auc_score']:.3f}")
                    st.write(
                        "Рекомендация: Используйте эти метрики как основные фильтры для Short позиций."
                    )

                if not good_short.empty:
                    st.warning("⚠️ **Хорошие Short предикторы (AUC 0.6-0.7):**")
                    for _, pred in good_short.iterrows():
                        metric_name = (
                            pred["metric_name"]
                            .replace("_short", "")
                            .replace("_", " ")
                            .title()
                        )
                        st.write(f"• **{metric_name}** - AUC: {pred['auc_score']:.3f}")
                    st.write(
                        "Рекомендация: Используйте как дополнительные фильтры для Short позиций."
                    )

                if not weak_short.empty:
                    st.error("❌ **Слабые Short предикторы (AUC ≤ 0.6):**")
                    for _, pred in weak_short.iterrows():
                        metric_name = (
                            pred["metric_name"]
                            .replace("_short", "")
                            .replace("_", " ")
                            .title()
                        )
                        st.write(f"• **{metric_name}** - AUC: {pred['auc_score']:.3f}")
                    st.write(
                        "Рекомендация: Избегайте использования этих метрик для Short позиций."
                    )
            else:
                st.info("Нет данных для Short позиций")

        # Общие рекомендации
        st.markdown(
            """
        <div class="insight-box">
            <h4>🔬 Общие рекомендации:</h4>
            <ul>
                <li><strong>Комбинируйте метрики:</strong> Используйте несколько сильных предикторов для повышения точности</li>
                <li><strong>Проверяйте стабильность:</strong> Убедитесь, что метрики работают на разных периодах</li>
                <li><strong>Учитывайте корреляции:</strong> Избегайте использования сильно коррелированных метрик</li>
                <li><strong>Тестируйте на out-of-sample:</strong> Проверяйте эффективность на новых данных</li>
            </ul>
        </div>
        """,
            unsafe_allow_html=True,
        )


def create_market_regime_analysis(trades_data, entry_metrics_data):
    """Создает анализ рыночных режимов"""
    if trades_data is None or trades_data.empty:
        return

    st.markdown(
        '<h2 class="section-header">🌊 Анализ Рыночных Режимов</h2>',
        unsafe_allow_html=True,
    )

    trades = trades_data.copy()
    trades["entry_time"] = pd.to_datetime(trades["entry_time"])

    # Создаем график сделок с цветовой кодировкой по рыночным режимам
    if entry_metrics_data is not None and not entry_metrics_data.empty:
        st.subheader("📈 Сделки по рыночным режимам")

        try:
            # Объединяем данные сделок с режимами
            trades_with_regimes = trades.merge(
                entry_metrics_data[
                    ["trade_id", "bull_market", "bear_market", "sideways_market"]
                ],
                left_index=True,
                right_on="trade_id",
                how="left",
            )

            # Определяем режим для каждой сделки
            def get_regime(row):
                if row.get("bull_market", False):
                    return "Бычий рынок"
                elif row.get("bear_market", False):
                    return "Медвежий рынок"
                elif row.get("sideways_market", False):
                    return "Боковой рынок"
                else:
                    return "Неопределен"

            trades_with_regimes["regime"] = trades_with_regimes.apply(
                get_regime, axis=1
            )

            # Создаем график
            fig = go.Figure()

            # Цвета для режимов
            regime_colors = {
                "Бычий рынок": "green",
                "Медвежий рынок": "red",
                "Боковой рынок": "orange",
                "Неопределен": "gray",
            }

            # Добавляем сделки по режимам
            for regime, color in regime_colors.items():
                regime_trades = trades_with_regimes[
                    trades_with_regimes["regime"] == regime
                ]

                if not regime_trades.empty:
                    # Определяем форму маркера в зависимости от исхода сделки
                    marker_symbols = []
                    for _, trade in regime_trades.iterrows():
                        if trade.get("exit_reason") == "take_profit":
                            marker_symbols.append(
                                "arrow-up"
                            )  # Take profit - стрелка вверх
                        else:
                            marker_symbols.append(
                                "x"
                            )  # Stop loss или другой исход - крестик

                    fig.add_trace(
                        go.Scatter(
                            x=regime_trades["entry_time"],
                            y=regime_trades["entry_price"],
                            mode="markers",
                            name=regime,
                            marker=dict(
                                color=color,
                                size=8,
                                symbol=marker_symbols,
                                line=dict(width=1, color="white"),
                            ),
                            text=[
                                f"PnL: ${trade.get('pnl_abs', 0):.2f}<br>Direction: {'Long' if trade.get('is_long', True) else 'Short'}<br>Exit: {trade.get('exit_reason', 'Unknown')}"
                                for _, trade in regime_trades.iterrows()
                            ],
                            hovertemplate="<b>%{text}</b><br>Время: %{x}<br>Цена: %{y}<extra></extra>",
                        )
                    )

            # Настройка графика
            fig.update_layout(
                title="Сделки по рыночным режимам",
                xaxis_title="Время входа",
                yaxis_title="Цена входа",
                height=500,
                showlegend=True,
                hovermode="closest",
            )

            # Настройка осей
            fig.update_xaxes(
                title_text="Время",
                showgrid=True,
                gridwidth=1,
                gridcolor="rgba(128,128,128,0.2)",
            )

            fig.update_yaxes(
                title_text="Цена",
                showgrid=True,
                gridwidth=1,
                gridcolor="rgba(128,128,128,0.2)",
            )

            st.plotly_chart(
                fig,
                config={
                    "displayModeBar": True,
                    "displaylogo": False,
                    "width": "stretch",
                },
            )

            # Легенда
            st.markdown(
                """
            <div style="background-color: #f0f2f6; padding: 10px; border-radius: 5px; margin: 10px 0;">
                <h4>🎨 Легенда:</h4>
                <p><span style="color: green;">🟢 Бычий рынок</span> - растущий тренд</p>
                <p><span style="color: red;">🔴 Медвежий рынок</span> - падающий тренд</p>
                <p><span style="color: orange;">🟠 Боковой рынок</span> - флэт/консолидация</p>
                <p><span style="color: gray;">⚪ Неопределен</span> - режим не определен</p>
                <p><strong>Форма маркера:</strong> ↑ Take Profit, ✗ Stop Loss</p>
            </div>
            """,
                unsafe_allow_html=True,
            )

            # Статистика по режимам
            regime_stats = (
                trades_with_regimes.groupby("regime")
                .agg(
                    {
                        "pnl_abs": ["count", "sum", "mean"],
                        "exit_reason": lambda x: (x == "take_profit").sum()
                        / len(x)
                        * 100,
                    }
                )
                .round(2)
            )

            regime_stats.columns = [
                "Количество сделок",
                "Общий PnL",
                "Средний PnL",
                "Win Rate %",
            ]

            st.subheader("📊 Статистика по режимам")
            st.dataframe(regime_stats, width="stretch")

        except Exception as e:
            st.warning(f"⚠️ Не удалось создать график режимов: {str(e)}")
            st.write("Отладочная информация:")
            if entry_metrics_data is not None:
                st.write(
                    f"Колонки entry_metrics_data: {list(entry_metrics_data.columns)}"
                )

    # Дополнительный анализ по режимам (если нужен)
    if entry_metrics_data is not None and not entry_metrics_data.empty:
        # Объединяем данные для дополнительного анализа
        trades_with_regimes = trades.merge(
            entry_metrics_data[
                [
                    "trade_id",
                    "bull_market",
                    "bear_market",
                    "sideways_market",
                    "regime_strength",
                ]
            ],
            left_index=True,
            right_on="trade_id",
            how="left",
        )

        # Анализ по рыночным режимам
        regime_analysis = []

        for regime in ["bull_market", "bear_market", "sideways_market"]:
            regime_trades = trades_with_regimes[trades_with_regimes[regime] == True]
            if not regime_trades.empty:
                regime_name = regime.replace("_market", "").title()
                win_rate = (
                    (regime_trades["exit_reason"] == "take_profit").sum()
                    / len(regime_trades)
                    * 100
                )
                avg_pnl = regime_trades["pnl_abs"].mean()
                total_pnl = regime_trades["pnl_abs"].sum()

                regime_analysis.append(
                    {
                        "Режим": regime_name,
                        "Сделок": len(regime_trades),
                        "Win Rate %": win_rate,
                        "Средний PnL": avg_pnl,
                        "Общий PnL": total_pnl,
                    }
                )

        if regime_analysis:
            regime_df = pd.DataFrame(regime_analysis)

            col1, col2 = st.columns(2)

            with col1:
                # График среднего PnL по режимам
                fig = px.bar(
                    regime_df,
                    x="Режим",
                    y="Средний PnL",
                    title="Средний PnL по рыночным режимам",
                    color="Средний PnL",
                    color_continuous_scale="RdYlGn",
                )
                fig.add_hline(y=0, line_dash="dash", line_color="black", opacity=0.5)
                st.plotly_chart(
                    fig,
                    config={
                        "displayModeBar": True,
                        "displaylogo": False,
                        "width": "stretch",
                    },
                )

            with col2:
                # График Win Rate по режимам
                fig = px.bar(
                    regime_df,
                    x="Режим",
                    y="Win Rate %",
                    title="Win Rate по рыночным режимам",
                    color="Win Rate %",
                    color_continuous_scale="RdYlGn",
                )
                fig.add_hline(y=50, line_dash="dash", line_color="black", opacity=0.5)
                st.plotly_chart(
                    fig,
                    config={
                        "displayModeBar": True,
                        "displaylogo": False,
                        "width": "stretch",
                    },
                )

            # Рекомендации по режимам
            if not regime_df.empty:
                best_regime = regime_df.loc[regime_df["Средний PnL"].idxmax()]
                worst_regime = regime_df.loc[regime_df["Средний PnL"].idxmin()]

                st.markdown(
                    f"""
                <div class="insight-box">
                    <h4>💡 Анализ рыночных режимов:</h4>
                    <p><strong>Лучший режим:</strong> {best_regime["Режим"]} (средний PnL: ${best_regime["Средний PnL"]:.2f})</p>
                    <p><strong>Худший режим:</strong> {worst_regime["Режим"]} (средний PnL: ${worst_regime["Средний PnL"]:.2f})</p>
                    <p><strong>Рекомендация:</strong> Рассмотрите возможность добавления фильтров рыночных режимов в стратегию.</p>
                </div>
                """,
                    unsafe_allow_html=True,
                )


def create_risk_analysis(trades_data, entry_metrics_data):
    """Создает анализ рисков"""
    if trades_data is None or trades_data.empty:
        return

    st.markdown(
        '<h2 class="section-header">⚠️ Анализ Рисков</h2>', unsafe_allow_html=True
    )

    # Добавляем прогресс-бар
    progress_bar = st.progress(0)
    status_text = st.empty()

    try:
        status_text.text("🔄 Подготовка данных для анализа рисков...")
        progress_bar.progress(10)

        trades = trades_data.copy()

        # Данных немного, не ограничиваем
        status_text.text(f"🔄 Обработка {len(trades)} сделок...")
        progress_bar.progress(20)

        # Создаем табы для разных видов анализа рисков
        tab1, tab2, tab3 = st.tabs(
            ["📊 VaR анализ", "📉 Анализ просадок", "🎯 Концентрация рисков"]
        )

        with tab1:
            status_text.text("🔄 VaR анализ...")
            progress_bar.progress(30)

            # Value at Risk анализ
            col1, col2 = st.columns(2)

            with col1:
                # VaR на разных уровнях
                if "pnl_abs" in trades.columns and not trades["pnl_abs"].empty:
                    pnl_returns = trades["pnl_abs"]
                    var_95 = np.percentile(pnl_returns, 5)
                    var_99 = np.percentile(pnl_returns, 1)
                    expected_shortfall_95 = pnl_returns[pnl_returns <= var_95].mean()

                    st.subheader("📊 Value at Risk")
                    st.metric("VaR 95%", f"${var_95:.2f}")
                    st.metric("VaR 99%", f"${var_99:.2f}")
                    st.metric("Expected Shortfall 95%", f"${expected_shortfall_95:.2f}")
                else:
                    st.info("Данные PnL недоступны для VaR анализа")

            with col2:
                # Распределение PnL с VaR линиями
                if "pnl_abs" in trades.columns and not trades["pnl_abs"].empty:
                    pnl_returns = trades["pnl_abs"]
                    var_95 = np.percentile(pnl_returns, 5)
                    var_99 = np.percentile(pnl_returns, 1)

                    fig = go.Figure()

                    fig.add_trace(
                        go.Histogram(
                            x=pnl_returns,
                            nbinsx=15,  # Еще меньше бинов
                            name="PnL Distribution",
                            opacity=0.7,
                        )
                    )

                    # Добавляем VaR линии (упрощенные)
                    fig.add_vline(x=var_95, line_dash="dash", line_color="orange")
                    fig.add_vline(x=var_99, line_dash="dash", line_color="red")

                    fig.update_layout(
                        title="Распределение PnL с VaR линиями",
                        xaxis_title="PnL ($)",
                        yaxis_title="Частота",
                        height=350,  # Еще меньше высота
                    )

                    st.plotly_chart(
                        fig,
                        config={
                            "displayModeBar": True,
                            "displaylogo": False,
                            "width": "stretch",
                        },
                    )
                else:
                    st.info("Данные PnL недоступны для построения графика")

        with tab2:
            status_text.text("🔄 Анализ просадок...")
            progress_bar.progress(50)

            # Анализ просадок
            col1, col2 = st.columns(2)

            with col1:
                # Кумулятивные просадки
                if "exit_time" in trades.columns and "pnl_abs" in trades.columns:
                    trades_sorted = trades.sort_values("exit_time")

                    # Простые вычисления
                    trades_sorted["cumulative_pnl"] = trades_sorted["pnl_abs"].cumsum()
                    trades_sorted["running_max"] = (
                        trades_sorted["cumulative_pnl"].expanding().max()
                    )
                    trades_sorted["drawdown"] = (
                        trades_sorted["cumulative_pnl"] - trades_sorted["running_max"]
                    )

                    fig = go.Figure()

                    # Только основная кривая
                    fig.add_trace(
                        go.Scatter(
                            x=trades_sorted["exit_time"],
                            y=trades_sorted["cumulative_pnl"],
                            mode="lines",
                            name="Cumulative PnL",
                            line=dict(color="blue", width=2),
                        )
                    )

                    fig.update_layout(
                        title="Кумулятивные просадки",
                        xaxis_title="Время",
                        yaxis_title="PnL ($)",
                        height=350,
                    )

                    st.plotly_chart(
                        fig,
                        config={
                            "displayModeBar": True,
                            "displaylogo": False,
                            "width": "stretch",
                        },
                    )
                else:
                    st.info("Необходимые колонки 'exit_time' или 'pnl_abs' не найдены")

        with col2:
            # Простая статистика просадок
            if "pnl_abs" in trades.columns:
                pnl_data = trades["pnl_abs"]
                max_loss = pnl_data.min()
                avg_loss = pnl_data[pnl_data < 0].mean() if (pnl_data < 0).any() else 0
                loss_count = (pnl_data < 0).sum()

                st.subheader("📉 Статистика убытков")
                st.metric("Максимальный убыток", f"${max_loss:.2f}")
                st.metric("Средний убыток", f"${avg_loss:.2f}")
                st.metric("Количество убытков", f"{loss_count}")
            else:
                st.info("Колонка 'pnl_abs' не найдена")

        with tab3:
            status_text.text("🔄 Концентрация рисков...")
            progress_bar.progress(70)

            # Концентрация рисков
            col1, col2 = st.columns(2)

            with col1:
                # Простая статистика по времени
                if "pnl_abs" in trades.columns:
                    pnl_data = trades["pnl_abs"]
                    best_trades = pnl_data.nlargest(5)
                    worst_trades = pnl_data.nsmallest(5)

                    st.subheader("🏆 Топ-5 лучших сделок")
                    for i, pnl in enumerate(best_trades, 1):
                        st.write(f"{i}. ${pnl:.2f}")

                    st.subheader("💥 Топ-5 худших сделок")
                    for i, pnl in enumerate(worst_trades, 1):
                        st.write(f"{i}. ${pnl:.2f}")
                else:
                    st.info("Колонка 'pnl_abs' не найдена")

            with col2:
                status_text.text("🔄 Анализ позиций...")
                progress_bar.progress(85)

                # Простая статистика по направлению
                if "is_long" in trades.columns and "pnl_abs" in trades.columns:
                    long_trades = trades[trades["is_long"] == True]["pnl_abs"]
                    short_trades = trades[trades["is_long"] == False]["pnl_abs"]

                    st.subheader("📊 Статистика по направлению")
                    st.metric("Long сделок", len(long_trades))
                    st.metric("Short сделок", len(short_trades))
                    st.metric("Средний PnL Long", f"${long_trades.mean():.2f}")
                    st.metric("Средний PnL Short", f"${short_trades.mean():.2f}")
                else:
                    st.info("Данные о направлении позиций недоступны")

        # Завершаем прогресс-бар
        progress_bar.progress(100)
        status_text.text("✅ Анализ рисков завершен!")

    except Exception as e:
        st.error(f"❌ Ошибка при создании анализа рисков: {str(e)}")
        st.write("Отладочная информация:")
        st.write(f"Тип данных trades_data: {type(trades_data)}")
        if hasattr(trades_data, "shape"):
            st.write(f"Размер данных: {trades_data.shape}")
        if hasattr(trades_data, "columns"):
            st.write(f"Колонки: {list(trades_data.columns)}")
    finally:
        # Очищаем прогресс-бар
        progress_bar.empty()
        status_text.empty()


def main():
    # Заголовок
    st.markdown(
        '<h1 class="main-header">🚀 Advanced Trading Strategy Dashboard</h1>',
        unsafe_allow_html=True,
    )

    # Боковая панель
    st.sidebar.title("🔧 Управление")

    # Поиск результатов
    results_folder = find_latest_results()

    if results_folder is None:
        st.error("❌ Результаты не найдены. Запустите бэктест сначала.")
        st.info(
            "💡 Используйте: `python -m backtester run --csv data.csv --strategy strategies/strategy.json --analyze-conditions --create-dashboard`"
        )
        return

    st.sidebar.success(f"✅ Найдены результаты: {results_folder.name}")

    # Загружаем данные
    data, folder = load_results_data(results_folder)

    if not data:
        st.error("❌ Файлы данных не найдены в папке результатов.")
        return

    # Информация о результатах
    st.sidebar.markdown("### 📁 Информация о результатах")
    st.sidebar.write(f"**Папка:** {folder.name}")
    st.sidebar.write(
        f"**Создано:** {datetime.fromtimestamp(folder.stat().st_mtime).strftime('%Y-%m-%d %H:%M:%S')}"
    )

    # Доступные данные
    available_data = list(data.keys())
    st.sidebar.write(f"**Доступные данные:** {', '.join(available_data)}")

    # Выбор разделов для отображения
    st.sidebar.markdown("### 📊 Выберите разделы для отображения")

    # Создаем чекбоксы для каждого раздела
    show_metrics = st.sidebar.checkbox("📈 Базовые показатели", value=True)
    show_equity = st.sidebar.checkbox("📊 Анализ кривой капитала", value=True)
    show_trades = st.sidebar.checkbox("📋 Анализ сделок", value=False)
    show_predictors = st.sidebar.checkbox("🔍 Анализ предикторов", value=False)
    show_regimes = st.sidebar.checkbox("🌊 Анализ рыночных режимов", value=False)
    show_risks = st.sidebar.checkbox("⚠️ Анализ рисков", value=False)

    # Основной контент (отображаем только выбранные разделы)
    if show_metrics and "metrics" in data:
        create_enhanced_metric_cards(data["metrics"], data)
        st.markdown("---")

    if show_equity and "equity_curve" in data:
        create_equity_curve_analysis(data["equity_curve"], data.get("trades"))
        st.markdown("---")

    if show_trades and "trades" in data:
        create_trade_analysis(data["trades"])
        st.markdown("---")

    if show_predictors and "trade_conditions" in data:
        create_predictor_analysis(data["trade_conditions"], data.get("entry_metrics"))
        st.markdown("---")

    if show_regimes and "trades" in data:
        create_market_regime_analysis(data["trades"], data.get("entry_metrics"))
        st.markdown("---")

    if show_risks and "trades" in data:
        create_risk_analysis(data["trades"], data.get("entry_metrics"))
        st.markdown("---")

    # Дополнительная информация в боковой панели
    st.sidebar.markdown("### 📊 Быстрая статистика")
    if "trades" in data:
        trades = data["trades"]
        if not trades.empty and "pnl_abs" in trades.columns:
            total_trades = len(trades)
            winning_trades = len(trades[trades["pnl_abs"] > 0])
            win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
            total_pnl = trades["pnl_abs"].sum()

            st.sidebar.metric("Всего сделок", total_trades)
            st.sidebar.metric("Винрейт", f"{win_rate:.1f}%")
            st.sidebar.metric("Общий PnL", f"${total_pnl:.2f}")

    # Информация о производительности
    st.sidebar.markdown("### ⚡ Производительность")
    st.sidebar.info("💡 **Совет:** Отключите ненужные разделы для ускорения загрузки")

    # Показываем, сколько разделов активно
    active_sections = sum(
        [
            show_metrics and "metrics" in data,
            show_equity and "equity_curve" in data,
            show_trades and "trades" in data,
            show_predictors and "trade_conditions" in data,
            show_regimes and "trades" in data,
            show_risks and "trades" in data,
        ]
    )

    st.sidebar.metric("Активных разделов", active_sections)

    # Футер
    st.sidebar.markdown("---")
    st.sidebar.markdown("**🚀 Advanced Trading Strategy Dashboard**")
    st.sidebar.markdown("*Создано с помощью Streamlit*")


if __name__ == "__main__":
    main()
