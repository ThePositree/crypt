import logging
import os
import warnings
from typing import Optional

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

warnings.filterwarnings("ignore")

# Настройка стиля графиков
plt.style.use("seaborn-v0_8")
sns.set_palette("husl")


class TradeConditionsVisualizer:
    """
    Класс для визуализации результатов анализа условий сделок.
    """

    def __init__(self, trade_analyzer, output_dir: str = "results"):
        """
        Инициализация визуализатора.

        Parameters:
        -----------
        trade_analyzer : TradeAnalyzer
            Объект анализатора условий сделок
        output_dir : str
            Директория для сохранения графиков
        """
        self.analyzer = trade_analyzer
        self.output_dir = output_dir
        self._logger = logging.getLogger(__name__)

        # Создаем директорию если не существует
        os.makedirs(output_dir, exist_ok=True)

    def plot_predictor_ranking(self, top_n: int = 15, save_path: Optional[str] = None):
        """
        График ранжирования предикторов по AUC.

        Parameters:
        -----------
        top_n : int
            Количество лучших предикторов для отображения
        save_path : Optional[str]
            Путь для сохранения графика
        """
        if self.analyzer.separation_results is None:
            self.analyzer.find_best_predictors()

        if self.analyzer.separation_results.empty:
            self._logger.warning("No separation results to visualize")
            return

        # Берем топ N предикторов
        top_predictors = self.analyzer.separation_results.head(top_n)

        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 8))

        # График 1: AUC vs Random (0.5)
        colors = [
            "red" if auc < 0.5 else "green" for auc in top_predictors["auc_score"]
        ]
        bars1 = ax1.barh(
            range(len(top_predictors)),
            top_predictors["auc_score"],
            color=colors,
            alpha=0.7,
        )
        ax1.axvline(
            x=0.5, color="black", linestyle="--", alpha=0.5, label="Random (0.5)"
        )
        ax1.set_yticks(range(len(top_predictors)))
        # Извлекаем базовые названия метрик для отображения
        display_names = []
        for name in top_predictors["metric_name"]:
            base_name = (
                name.replace("_long", "").replace("_short", "").replace("_all", "")
            )
            display_names.append(base_name.replace("_", " ").title())
        ax1.set_yticklabels(display_names)
        ax1.set_xlabel("AUC Score")
        ax1.set_title("Top Predictors by AUC Score")
        ax1.legend()
        ax1.grid(True, alpha=0.3)

        # Добавляем значения на столбцы
        for i, (bar, auc) in enumerate(zip(bars1, top_predictors["auc_score"])):
            ax1.text(
                bar.get_width() + 0.01,
                bar.get_y() + bar.get_height() / 2,
                f"{auc:.3f}",
                va="center",
                fontsize=9,
            )

        # График 2: KS Statistic
        bars2 = ax2.barh(
            range(len(top_predictors)),
            top_predictors["ks_statistic"],
            color="steelblue",
            alpha=0.7,
        )
        ax2.set_yticks(range(len(top_predictors)))
        ax2.set_yticklabels(display_names)
        ax2.set_xlabel("KS Statistic")
        ax2.set_title("Kolmogorov-Smirnov Statistic")
        ax2.grid(True, alpha=0.3)

        # Добавляем значения на столбцы
        for i, (bar, ks) in enumerate(zip(bars2, top_predictors["ks_statistic"])):
            ax2.text(
                bar.get_width() + 0.01,
                bar.get_y() + bar.get_height() / 2,
                f"{ks:.3f}",
                va="center",
                fontsize=9,
            )

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches="tight")
            self._logger.info(f"Predictor ranking plot saved to: {save_path}")
        else:
            plt.show()

        plt.close()

    def plot_distribution_comparison(
        self, metric_name: str, save_path: Optional[str] = None
    ):
        """
        Детальное сравнение распределений для конкретной метрики.

        Parameters:
        -----------
        metric_name : str
            Название метрики для анализа
        save_path : Optional[str]
            Путь для сохранения графика
        """
        if self.analyzer.entry_metrics is None:
            self.analyzer.extract_entry_metrics()

        if (
            self.analyzer.entry_metrics.empty
            or metric_name not in self.analyzer.entry_metrics.columns
        ):
            self._logger.warning(f"Metric {metric_name} not found")
            return

        # Разделяем данные
        tp_data = self.analyzer.entry_metrics[
            self.analyzer.entry_metrics["exit_reason"] == "take_profit"
        ][metric_name].dropna()

        sl_data = self.analyzer.entry_metrics[
            self.analyzer.entry_metrics["exit_reason"] == "stop_loss"
        ][metric_name].dropna()

        if len(tp_data) == 0 or len(sl_data) == 0:
            self._logger.warning(f"Insufficient data for {metric_name}")
            return

        # Получаем метрики разделения
        separation_metrics = self.analyzer.calculate_separation_metrics(metric_name)

        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 12))

        # График 1: Гистограммы
        ax1.hist(
            tp_data,
            alpha=0.7,
            label="Take Profit",
            bins=20,
            density=True,
            color="green",
        )
        ax1.hist(
            sl_data, alpha=0.7, label="Stop Loss", bins=20, density=True, color="red"
        )
        ax1.set_xlabel(metric_name.replace("_", " ").title())
        ax1.set_ylabel("Density")
        ax1.set_title(
            f"Distribution Comparison: {metric_name.replace('_', ' ').title()}"
        )
        ax1.legend()
        ax1.grid(True, alpha=0.3)

        # График 2: Box plots
        data_to_plot = [tp_data, sl_data]
        labels = ["Take Profit", "Stop Loss"]
        bp = ax2.boxplot(data_to_plot, labels=labels, patch_artist=True)
        bp["boxes"][0].set_facecolor("green")
        bp["boxes"][1].set_facecolor("red")
        ax2.set_ylabel(metric_name.replace("_", " ").title())
        ax2.set_title("Box Plot Comparison")
        ax2.grid(True, alpha=0.3)

        # График 3: Q-Q Plot для TP
        from scipy import stats

        stats.probplot(tp_data, dist="norm", plot=ax3)
        ax3.set_title("Q-Q Plot: Take Profit")
        ax3.grid(True, alpha=0.3)

        # График 4: Q-Q Plot для SL
        stats.probplot(sl_data, dist="norm", plot=ax4)
        ax4.set_title("Q-Q Plot: Stop Loss")
        ax4.grid(True, alpha=0.3)

        # Добавляем информацию о метриках
        metrics_text = f"""Separation Metrics:
AUC: {separation_metrics.get("auc_score", 0):.3f}
KS: {separation_metrics.get("ks_statistic", 0):.3f}
JS: {separation_metrics.get("js_divergence", 0):.3f}
TP Count: {separation_metrics.get("tp_count", 0)}
SL Count: {separation_metrics.get("sl_count", 0)}"""

        fig.text(
            0.02,
            0.02,
            metrics_text,
            fontsize=10,
            bbox=dict(boxstyle="round,pad=0.3", facecolor="lightgray", alpha=0.8),
        )

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches="tight")
            self._logger.info(f"Distribution comparison plot saved to: {save_path}")
        else:
            plt.show()

        plt.close()

    def plot_correlation_heatmap(
        self, top_n: int = 10, save_path: Optional[str] = None
    ):
        """
        Тепловая карта корреляций между лучшими предикторами.

        Parameters:
        -----------
        top_n : int
            Количество лучших предикторов для анализа
        save_path : Optional[str]
            Путь для сохранения графика
        """
        if self.analyzer.separation_results is None:
            self.analyzer.find_best_predictors()

        if self.analyzer.separation_results.empty:
            self._logger.warning("No separation results to visualize")
            return

        # Берем топ N предикторов
        top_predictors = self.analyzer.separation_results.head(top_n)

        # Извлекаем базовые названия метрик (убираем суффиксы направлений)
        if "base_metric" in top_predictors.columns:
            metric_names = top_predictors["base_metric"].unique().tolist()
        else:
            # Fallback: извлекаем базовые названия из metric_name
            metric_names = []
            for name in top_predictors["metric_name"].tolist():
                # Убираем суффиксы _long, _short, _all
                base_name = (
                    name.replace("_long", "").replace("_short", "").replace("_all", "")
                )
                if base_name not in metric_names:
                    metric_names.append(base_name)

        # Получаем данные для этих метрик
        if self.analyzer.entry_metrics is None:
            self.analyzer.extract_entry_metrics()

        # Фильтруем только существующие колонки
        available_metrics = [
            name for name in metric_names if name in self.analyzer.entry_metrics.columns
        ]

        if not available_metrics:
            self.logger.warning("No available metrics for correlation analysis")
            return

        correlation_data = self.analyzer.entry_metrics[available_metrics].corr()

        plt.figure(figsize=(12, 10))

        # Создаем маску для верхнего треугольника
        mask = np.triu(np.ones_like(correlation_data, dtype=bool))

        # Создаем тепловую карту
        sns.heatmap(
            correlation_data,
            mask=mask,
            annot=True,
            cmap="RdBu_r",
            center=0,
            square=True,
            fmt=".2f",
            cbar_kws={"shrink": 0.8},
        )

        plt.title(f"Correlation Matrix of Top {top_n} Predictors")
        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches="tight")
            self._logger.info(f"Correlation heatmap saved to: {save_path}")
        else:
            plt.show()

        plt.close()

    def plot_metric_importance_radar(
        self, top_n: int = 8, save_path: Optional[str] = None
    ):
        """
        Радарная диаграмма важности метрик.

        Parameters:
        -----------
        top_n : int
            Количество лучших предикторов для отображения
        save_path : Optional[str]
            Путь для сохранения графика
        """
        if self.analyzer.separation_results is None:
            self.analyzer.find_best_predictors()

        if self.analyzer.separation_results.empty:
            self._logger.warning("No separation results to visualize")
            return

        # Берем топ N предикторов
        top_predictors = self.analyzer.separation_results.head(top_n)

        # Нормализуем метрики для радарной диаграммы
        metrics = ["auc_score", "ks_statistic", "js_divergence"]
        normalized_data = {}

        for metric in metrics:
            values = top_predictors[metric].values
            # Нормализуем к 0-1
            normalized_data[metric] = (values - values.min()) / (
                values.max() - values.min() + 1e-8
            )

        # Создаем радарную диаграмму
        fig, ax = plt.subplots(figsize=(10, 10), subplot_kw=dict(projection="polar"))

        # Углы для каждой метрики
        angles = np.linspace(0, 2 * np.pi, len(metrics), endpoint=False).tolist()
        angles += angles[:1]  # Замыкаем круг

        colors = plt.cm.Set3(np.linspace(0, 1, len(top_predictors)))

        for i, (_, row) in enumerate(top_predictors.iterrows()):
            values = [normalized_data[metric][i] for metric in metrics]
            values += values[:1]  # Замыкаем круг

            ax.plot(
                angles,
                values,
                "o-",
                linewidth=2,
                label=row["metric_name"]
                .replace("_long", "")
                .replace("_short", "")
                .replace("_all", "")
                .replace("_", " ")
                .title(),
                color=colors[i],
            )
            ax.fill(angles, values, alpha=0.25, color=colors[i])

        # Настройка осей
        ax.set_xticks(angles[:-1])
        ax.set_xticklabels([metric.replace("_", " ").title() for metric in metrics])
        ax.set_ylim(0, 1)
        ax.set_title("Metric Importance Radar Chart", size=16, pad=20)
        ax.legend(loc="upper right", bbox_to_anchor=(1.3, 1.0))
        ax.grid(True)

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches="tight")
            self._logger.info(f"Radar chart saved to: {save_path}")
        else:
            plt.show()

        plt.close()

    def plot_trade_timeline(self, save_path: Optional[str] = None):
        """
        Временная линия сделок с цветовой кодировкой по исходу.

        Parameters:
        -----------
        save_path : Optional[str]
            Путь для сохранения графика
        """
        if self.analyzer.trades.empty:
            self._logger.warning("No trades to visualize")
            return

        trades = self.analyzer.trades.copy()
        trades["entry_time"] = pd.to_datetime(trades["entry_time"])
        trades["exit_time"] = pd.to_datetime(trades["exit_time"])

        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(15, 10))

        # График 1: Временная линия сделок
        colors = [
            "green" if reason == "take_profit" else "red"
            for reason in trades["exit_reason"]
        ]

        for i, (_, trade) in enumerate(trades.iterrows()):
            ax1.scatter(
                trade["entry_time"], trade["pnl_abs"], color=colors[i], alpha=0.7, s=50
            )
            ax1.plot(
                [trade["entry_time"], trade["exit_time"]],
                [trade["pnl_abs"], trade["pnl_abs"]],
                color=colors[i],
                alpha=0.3,
                linewidth=2,
            )

        ax1.axhline(y=0, color="black", linestyle="--", alpha=0.5)
        ax1.set_xlabel("Time")
        ax1.set_ylabel("PnL ($)")
        ax1.set_title("Trade Timeline")
        ax1.grid(True, alpha=0.3)

        # График 2: Кумулятивная прибыль
        trades_sorted = trades.sort_values("exit_time")
        trades_sorted["cumulative_pnl"] = trades_sorted["pnl_abs"].cumsum()

        ax2.plot(
            trades_sorted["exit_time"],
            trades_sorted["cumulative_pnl"],
            linewidth=2,
            color="blue",
        )
        ax2.fill_between(
            trades_sorted["exit_time"],
            trades_sorted["cumulative_pnl"],
            alpha=0.3,
            color="blue",
        )
        ax2.axhline(y=0, color="black", linestyle="--", alpha=0.5)
        ax2.set_xlabel("Time")
        ax2.set_ylabel("Cumulative PnL ($)")
        ax2.set_title("Cumulative Profit/Loss")
        ax2.grid(True, alpha=0.3)

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches="tight")
            self._logger.info(f"Trade timeline plot saved to: {save_path}")
        else:
            plt.show()

        plt.close()

    def generate_all_visualizations(self, output_prefix: str = "trade_analysis"):
        """
        Генерирует все доступные визуализации.

        Parameters:
        -----------
        output_prefix : str
            Префикс для имен файлов
        """
        self._logger.info("🎨 Generating all visualizations...")

        # 1. Ранжирование предикторов
        self.plot_predictor_ranking(
            top_n=15,
            save_path=os.path.join(
                self.output_dir, f"{output_prefix}_predictor_ranking.png"
            ),
        )

        # 2. Корреляционная матрица
        self.plot_correlation_heatmap(
            top_n=10,
            save_path=os.path.join(
                self.output_dir, f"{output_prefix}_correlation_heatmap.png"
            ),
        )

        # 3. Радарная диаграмма
        self.plot_metric_importance_radar(
            top_n=8,
            save_path=os.path.join(self.output_dir, f"{output_prefix}_radar_chart.png"),
        )

        # 4. Временная линия сделок
        self.plot_trade_timeline(
            save_path=os.path.join(self.output_dir, f"{output_prefix}_timeline.png")
        )

        # 5. Детальное сравнение для топ-3 предикторов
        if (
            self.analyzer.separation_results is not None
            and not self.analyzer.separation_results.empty
        ):
            # Извлекаем базовые названия метрик
            top_3_predictors = []
            for name in self.analyzer.separation_results.head(3)[
                "metric_name"
            ].tolist():
                base_name = (
                    name.replace("_long", "").replace("_short", "").replace("_all", "")
                )
                if base_name not in top_3_predictors:
                    top_3_predictors.append(base_name)

            for i, metric in enumerate(top_3_predictors):
                self.plot_distribution_comparison(
                    metric,
                    save_path=os.path.join(
                        self.output_dir, f"{output_prefix}_distribution_{metric}.png"
                    ),
                )

        self._logger.info(f"✅ All visualizations saved to: {self.output_dir}")

    def create_summary_dashboard(self, save_path: Optional[str] = None):
        """
        Создает сводную панель с ключевыми метриками.

        Parameters:
        -----------
        save_path : Optional[str]
            Путь для сохранения графика
        """
        if self.analyzer.separation_results is None:
            self.analyzer.find_best_predictors()

        if self.analyzer.separation_results.empty:
            self._logger.warning("No separation results to visualize")
            return

        fig = plt.figure(figsize=(20, 12))

        # Создаем сетку для размещения графиков
        gs = fig.add_gridspec(3, 4, hspace=0.3, wspace=0.3)

        # График 1: Топ предикторы (AUC)
        ax1 = fig.add_subplot(gs[0, :2])
        top_5 = self.analyzer.separation_results.head(5)
        colors = ["red" if auc < 0.5 else "green" for auc in top_5["auc_score"]]
        bars = ax1.barh(range(len(top_5)), top_5["auc_score"], color=colors, alpha=0.7)
        ax1.axvline(x=0.5, color="black", linestyle="--", alpha=0.5)
        ax1.set_yticks(range(len(top_5)))
        # Извлекаем базовые названия для отображения
        display_names_5 = []
        for name in top_5["metric_name"]:
            base_name = (
                name.replace("_long", "").replace("_short", "").replace("_all", "")
            )
            display_names_5.append(base_name.replace("_", " ").title())
        ax1.set_yticklabels(display_names_5)
        ax1.set_xlabel("AUC Score")
        ax1.set_title("Top 5 Predictors by AUC")
        ax1.grid(True, alpha=0.3)

        # График 2: Статистика сделок
        ax2 = fig.add_subplot(gs[0, 2:])
        if self.analyzer.entry_metrics is not None:
            exit_counts = self.analyzer.entry_metrics["exit_reason"].value_counts()
            colors_pie = [
                "green" if reason == "take_profit" else "red"
                for reason in exit_counts.index
            ]
            ax2.pie(
                exit_counts.values,
                labels=exit_counts.index,
                autopct="%1.1f%%",
                colors=colors_pie,
                startangle=90,
            )
            ax2.set_title("Trade Outcome Distribution")

        # График 3: Корреляционная матрица (топ 6)
        ax3 = fig.add_subplot(gs[1, :2])
        top_6 = self.analyzer.separation_results.head(6)
        if self.analyzer.entry_metrics is not None:
            # Извлекаем базовые названия метрик для корреляции
            correlation_metrics = []
            for name in top_6["metric_name"]:
                base_name = (
                    name.replace("_long", "").replace("_short", "").replace("_all", "")
                )
                if (
                    base_name not in correlation_metrics
                    and base_name in self.analyzer.entry_metrics.columns
                ):
                    correlation_metrics.append(base_name)

            if correlation_metrics:
                correlation_data = self.analyzer.entry_metrics[
                    correlation_metrics
                ].corr()
            else:
                return  # Нет доступных метрик для корреляции
            im = ax3.imshow(
                correlation_data, cmap="RdBu_r", aspect="auto", vmin=-1, vmax=1
            )
            ax3.set_xticks(range(len(top_6)))
            ax3.set_yticks(range(len(top_6)))
            # Используем базовые названия для отображения
            display_names_6 = []
            for name in top_6["metric_name"]:
                base_name = (
                    name.replace("_long", "").replace("_short", "").replace("_all", "")
                )
                display_names_6.append(base_name.replace("_", " ").title())

            ax3.set_xticklabels(display_names_6, rotation=45, ha="right")
            ax3.set_yticklabels(display_names_6)
            ax3.set_title("Correlation Matrix (Top 6)")
            plt.colorbar(im, ax=ax3, shrink=0.8)

        # График 4: Радарная диаграмма (топ 5)
        ax4 = fig.add_subplot(gs[1, 2:], projection="polar")
        top_5_radar = self.analyzer.separation_results.head(5)
        metrics = ["auc_score", "ks_statistic", "js_divergence"]
        angles = np.linspace(0, 2 * np.pi, len(metrics), endpoint=False).tolist()
        angles += angles[:1]

        colors_radar = plt.cm.Set3(np.linspace(0, 1, len(top_5_radar)))
        for i, (_, row) in enumerate(top_5_radar.iterrows()):
            values = [row[metric] for metric in metrics]
            values += values[:1]
            ax4.plot(
                angles,
                values,
                "o-",
                linewidth=2,
                label=row["metric_name"]
                .replace("_long", "")
                .replace("_short", "")
                .replace("_all", "")
                .replace("_", " ")
                .title(),
                color=colors_radar[i],
            )
            ax4.fill(angles, values, alpha=0.25, color=colors_radar[i])

        ax4.set_xticks(angles[:-1])
        ax4.set_xticklabels([metric.replace("_", " ").title() for metric in metrics])
        ax4.set_title("Metric Importance Radar")
        ax4.legend(loc="upper right", bbox_to_anchor=(1.3, 1.0))

        # График 5: Временная линия (если есть сделки)
        ax5 = fig.add_subplot(gs[2, :])
        if not self.analyzer.trades.empty:
            trades = self.analyzer.trades.copy()
            trades["entry_time"] = pd.to_datetime(trades["entry_time"])
            trades_sorted = trades.sort_values("exit_time")
            trades_sorted["cumulative_pnl"] = trades_sorted["pnl_abs"].cumsum()

            ax5.plot(
                trades_sorted["exit_time"],
                trades_sorted["cumulative_pnl"],
                linewidth=2,
                color="blue",
            )
            ax5.fill_between(
                trades_sorted["exit_time"],
                trades_sorted["cumulative_pnl"],
                alpha=0.3,
                color="blue",
            )
            ax5.axhline(y=0, color="black", linestyle="--", alpha=0.5)
            ax5.set_xlabel("Time")
            ax5.set_ylabel("Cumulative PnL ($)")
            ax5.set_title("Cumulative Profit/Loss Over Time")
            ax5.grid(True, alpha=0.3)

        plt.suptitle("Trade Conditions Analysis Dashboard", fontsize=16, y=0.98)

        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches="tight")
            self._logger.info(f"Summary dashboard saved to: {save_path}")
        else:
            plt.show()

        plt.close()
