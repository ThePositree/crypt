import numpy as np
import optuna
import pandas as pd

from backtester.indicators.market_phase import compute_supertrend_adx_phase
from backtester.strategy import BaseStrategy
from backtester.strategies.fractal_rb import FractalRbStrategy


class PhaseRoutedStrategy(BaseStrategy):
    """Route signals to phase-specific Fractal RB models.

    The strategy detects market phase with Supertrend + ADX and delegates
    signal generation to one of three nested ``FractalRbStrategy`` models
    (bull, flat, bear).
    """

    def suggest_params(self, trial: optuna.Trial) -> dict:
        """Suggest optimization parameters for phase-routed execution.

        Parameters
        ----------
        trial : optuna.Trial
            Current Optuna trial object.

        Returns
        -------
        dict
            Strategy parameters with nested configs for bull/flat/bear models
            and trend detector settings.
        """

        def fractal_rb_params(trial: optuna.Trial, phase: int) -> dict:
            return {
                "fractal_bars": trial.suggest_categorical(f"fractal_bars_{phase}", [3, 5]),
                "min_wick_pips": trial.suggest_float(
                    f"min_wick_pips_{phase}", 50.0, 1000.0, step=25.0
                ),
                "pips_scale": trial.suggest_int(f"pips_scale_{phase}", 1000, 20000, step=1000),
            }

        return {
            "model_bull": fractal_rb_params(trial, 1),
            "model_flat": fractal_rb_params(trial, 0),
            "model_bear": fractal_rb_params(trial, -1),
            "timeframe": trial.suggest_categorical("timeframe", [3, 15, 30]),
            "trend": {
                "atr_period": trial.suggest_int("atr_period", 5, 20, step=5),
                "multiplier": trial.suggest_float("multiplier", 1.0, 3.0, step=0.1),
                "adx_period": trial.suggest_int("adx_period", 5, 20, step=5),
                "adx_thresh": trial.suggest_float("adx_thresh", 10.0, 30.0, step=1.0),
                "use_adx_filter": trial.suggest_categorical("use_adx_filter", [True, False]),
            }
        }

    def generate(self, df: pd.DataFrame) -> pd.DataFrame:
        """Generate trade signals using phase-dependent sub-strategies.

        Parameters
        ----------
        df : pandas.DataFrame
            Input OHLCV data indexed by timestamp.

        Returns
        -------
        pandas.DataFrame
            Resampled OHLCV frame with ``signal``, ``sl_price`` and
            ``entry_price`` columns populated from the selected model.
        """

        model_bull = FractalRbStrategy(self.params["model_bull"])
        model_flat = FractalRbStrategy(self.params["model_flat"])
        model_bear = FractalRbStrategy(self.params["model_bear"])

        df = df.copy()

        df = (
            df
            .resample(f'{self.params["timeframe"]}min')
            .agg({
                'open': 'first',
                'high': 'max',
                'low': 'min',
                'close': 'last',
                'volume': 'sum',
            })
            .dropna()
        )

        phase = compute_supertrend_adx_phase(df, **self.params["trend"])

        df["signal"] = 0
        df["sl_price"] = np.nan
        df["entry_price"] = np.nan

        bull_df = model_bull.generate(df)
        flat_df = model_flat.generate(df)
        bear_df = model_bear.generate(df)

        bull_mask = phase == 1
        flat_mask = phase == 0
        bear_mask = phase == -1

        df.loc[bull_mask, ["signal", "sl_price", "entry_price"]] = (
            bull_df.loc[bull_mask, ["signal", "sl_price", "entry_price"]]
        )
        df.loc[flat_mask, ["signal", "sl_price", "entry_price"]] = (
            flat_df.loc[flat_mask, ["signal", "sl_price", "entry_price"]]
        )
        df.loc[bear_mask, ["signal", "sl_price", "entry_price"]] = (
            bear_df.loc[bear_mask, ["signal", "sl_price", "entry_price"]]
        )

        return df
