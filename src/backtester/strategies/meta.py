from __future__ import annotations

import pandas as pd
from optuna.storages import JournalStorage
from optuna.storages.journal import JournalFileBackend

from backtester.strategies.dual_ma import DualMAStrategy
from backtester.strategies.fractal_rejection import FractalRejectionStrategy
from backtester.strategies.fvg_imbalance import FVGImbalanceStrategy
from backtester.strategies.liquidity_hunter import LiquidityHunter
from backtester.strategy import BaseStrategy


class MetaStrategy(BaseStrategy):
    strategies = {
        "dual_ma": DualMAStrategy,
        "liq_hunter": LiquidityHunter,
        "fvg_imbalance": FVGImbalanceStrategy,
        "fractal_rejection": FractalRejectionStrategy,
    }

    def __init__(self, params):
        super().__init__(params)
        self.strategy = MetaStrategy.strategies[params["strategy"]]

    def suggest_params(self, trial):
        raise NotImplementedError

    def generate(self, df: pd.DataFrame) -> pd.DataFrame:
        study_log = self.params["study_log"]
        study_name = self.params["study_name"]
        enough_max_min_per_month_return = self.params.get(
            "enough_max_min_per_month_return", -5
        )
        enough_min_total_return = self.params.get("enough_min_total_return", 10)
        storage = JournalStorage(JournalFileBackend(study_log))
        study_id = storage.get_study_id_from_name(study_name)

        from optuna.trial import FrozenTrial

        df["risk_percent"] = 0.0
        df["rrr"] = 0.0
        df["signal"] = 0
        df["sl_price"] = 0.0
        for t in sorted(
            filter(lambda t: t.values is not None, storage.get_all_trials(study_id)),
            key=lambda t: t.user_attrs.get("total_return_pct", -100),
        ):
            t: FrozenTrial
            if "min_monthly_return" not in t.user_attrs:
                continue

            if "total_return_pct" not in t.user_attrs:
                continue

            if t.user_attrs["min_monthly_return"] < enough_max_min_per_month_return:
                continue

            if t.user_attrs["total_return_pct"] < enough_min_total_return:
                continue

            st = self.strategy(t.params)
            df_cp = st.generate(df.copy())
            is_signal = df_cp["signal"] != 0
            df.loc[is_signal, "signal"] = df_cp["signal"][is_signal]
            df.loc[is_signal, "sl_price"] = df_cp["sl_price"][is_signal]
            df.loc[is_signal, "risk_percent"] = t.params["risk_percent"]
            df.loc[is_signal, "rrr"] = t.params["rrr"]

        return df
