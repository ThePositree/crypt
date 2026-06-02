# streamlit_app.py

import json
import tempfile
from datetime import datetime

import streamlit as st

from backtester.data_loader import DataLoader
from backtester.optimizer import ParameterOptimizer, TargetFunction
from backtester.registry import STRATEGIES
from backtester.tester import Backtester

# Заголовок
st.set_page_config(page_title="Strategy Lab", layout="wide")
st.title("📊 Strategy Lab: Backtester & Optimizer")

# --- 1. Загрузка данных ---
st.header("1. 📥 Загрузите OHLCV данные (CSV)")
uploaded_file = st.file_uploader("Выберите CSV файл", type="csv")

if uploaded_file is not None:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as tmp:
        tmp.write(uploaded_file.getvalue())
        temp_path = tmp.name

    loader = DataLoader()
    try:
        df = loader.from_csv(temp_path, timestamp_col="time")
        st.success(f"✅ Данные загружены: {len(df)} баров")
        st.write("Превью данных:")
        st.dataframe(df.head())
        st.session_state["data"] = df
        st.session_state["temp_path"] = temp_path
    except Exception as e:
        st.error(f"❌ Ошибка загрузки: {e}")

# --- 2. Выбор стратегии ---
if "data" in st.session_state:
    st.header("2. 🧠 Выберите стратегию")

    strategy_name = st.selectbox(
        "Стратегия",
        list(STRATEGIES.keys()),
        format_func=lambda x: x.replace("_", " ").title(),
    )

    strategy_class = STRATEGIES[strategy_name]
    st.session_state["strategy_class"] = strategy_class

# --- 3. Параметры бэктеста ---
if "data" in st.session_state:
    st.header("3. ⚙️ Настройте параметры")

    col1, col2 = st.columns(2)

    with col1:
        initial_capital = st.number_input(
            "Начальный капитал", min_value=1.0, value=1000.0
        )
        taker_fee = st.number_input(
            "Taker Fee", min_value=0.0, value=0.001, format="%.4f"
        )
        maker_fee = st.number_input(
            "Maker Fee", min_value=0.0, value=0.0002, format="%.4f"
        )

    with col2:
        max_positions = st.number_input(
            "Макс. одновременных позиций", min_value=0, value=5
        )
        position_ttl_bars = st.number_input(
            "TTL позиции (в барах)", min_value=0, value=20
        )
        min_net_exposure = st.number_input(
            "Min Net Exposure", min_value=0.0, value=0.01, format="%.4f"
        )

    st.session_state["backtest_params"] = {
        "initial_capital": initial_capital,
        "taker_fee": taker_fee,
        "maker_fee": maker_fee,
        "max_positions": max_positions,
        "position_ttl_bars": position_ttl_bars,
        "min_net_exposure": min_net_exposure,
    }

    st.subheader("Параметры стратегии (JSON)")
    strategy_params_raw = st.text_area(
        "Strategy params",
        value="{}",
        height=150,
        help="JSON-словарь, который будет передан в конструктор стратегии как `params`.",
    )
    try:
        st.session_state["strategy_params"] = (
            json.loads(strategy_params_raw) if strategy_params_raw else {}
        )
    except json.JSONDecodeError as e:
        st.error(f"❌ Некорректный JSON в параметрах стратегии: {e}")
        st.session_state["strategy_params"] = {}

# --- 4. Запуск бэктеста ---
if "backtest_params" in st.session_state and "strategy_class" in st.session_state:
    st.header("4. ▶️ Запустите бэктест")

    if st.button("Запустить бэктест"):
        with st.spinner("Запуск симуляции..."):
            try:
                df_bt = st.session_state["data"]

                def strategy(df):
                    strategy_params = st.session_state.get("strategy_params", {})
                    return st.session_state["strategy_class"](strategy_params).generate(
                        df
                    )

                bt = Backtester(df_bt, strategy)
                results = bt.run(
                    **st.session_state["backtest_params"], risk_percent=1.0, rrr=2.0
                )

                st.session_state["results"] = results
                st.success("✅ Бэктест завершён!")
            except Exception as e:
                st.error(f"❌ Ошибка: {e}")

# --- 5. Отображение результатов ---
if "results" in st.session_state:
    results = st.session_state["results"]
    metrics = results.metrics

    st.header("5. 📊 Результаты бэктеста")

    col1, col2 = st.columns(2)
    with col1:
        st.metric("Начальный капитал", f"${metrics['initial_capital']:,.2f}")
        st.metric("Финальный капитал", f"${metrics['final_capital']:,.2f}")
        st.metric("Общая доходность", f"{metrics['total_return_pct']:.2f}%")
        st.metric("Win Rate", f"{metrics['win_rate']:.2f}%")

    with col2:
        st.metric("Profit Factor", f"{metrics['profit_factor']}")
        st.metric("Max Drawdown", f"{metrics['max_drawdown']:.2f}%")
        st.metric("Средняя сделка", f"${metrics['avg_pnl_abs']:.2f}")
        st.metric("Avg Holding Bars", f"{metrics['avg_holding_bars']:.1f}")

    st.subheader("Распределение выходов")
    st.bar_chart(metrics["exit_distribution"])

    st.subheader("Кривая капитала")
    equity_curve = results.get_equity_curve()
    if equity_curve is not None:
        st.line_chart(equity_curve)

    st.subheader("История сделок")
    st.dataframe(results.get_trades())

    st.download_button(
        label="📥 Скачать результаты (CSV)",
        data=results.get_trades().to_csv(index=False).encode("utf-8"),
        file_name=f"backtest_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        mime="text/csv",
    )

# --- 6. Оптимизация ---
if (
    "data" in st.session_state
    and "backtest_params" in st.session_state
    and "strategy_class" in st.session_state
):
    st.header("6. 🔍 Оптимизация параметров")

    n_trials = st.number_input("Количество итераций", min_value=10, value=50)

    if st.button("Запустить оптимизацию"):
        with st.spinner("Оптимизация..."):
            try:
                # Целевая функция
                def target_fn(analyzer):
                    m = analyzer.metrics
                    win_rate = m.get("win_rate", 0) / 100
                    profit_factor = m.get("profit_factor", 1.0)
                    max_dd = abs(m.get("max_drawdown", 0) / 100)
                    return (
                        (win_rate * profit_factor) / (1 + max_dd) if max_dd < 1 else 0.0
                    )

                # Подготовка данных
                df_opt = st.session_state["data"]

                # Запуск оптимизатора
                optimizer = ParameterOptimizer(
                    df=df_opt,
                    strategy_class=st.session_state["strategy_class"],
                    target=TargetFunction(fn=target_fn, direction="maximize"),
                    **st.session_state["backtest_params"],
                )

                best_params, study = optimizer.optimize(n_trials=n_trials)

                st.success("✅ Оптимизация завершена!")
                st.json(best_params)
                st.metric("Лучшее значение", f"{study.best_value:.4f}")

                # Визуализация
                if st.checkbox("Показать историю оптимизации"):
                    import plotly.graph_objects as go

                    fig = go.Figure()
                    fig.add_trace(
                        go.Scatter(
                            x=list(range(len(study.trials))),
                            y=[t.value for t in study.trials],
                            mode="lines+markers",
                        )
                    )
                    fig.update_layout(
                        title="Optimization History",
                        xaxis_title="Trial",
                        yaxis_title="Target Value",
                    )
                    st.plotly_chart(fig)

            except Exception as e:
                st.error(f"❌ Ошибка оптимизации: {e}")

# --- Очистка ---
if st.sidebar.button("Очистить всё"):
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.experimental_rerun()
