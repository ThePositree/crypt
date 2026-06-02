import pandas as pd

from backtester.execution_sim import ExecutionSim


def _simple_df(index_name: str | None) -> pd.DataFrame:
    idx = pd.date_range("2026-01-01", periods=3, freq="D")
    idx = idx.rename(index_name)
    df = pd.DataFrame(
        {
            "open": [100.0, 101.0, 102.0],
            # Use large highs so TP is reached and a trade is closed
            "high": [101.0, 200.0, 200.0],
            "low": [99.0, 100.0, 101.0],
            "close": [100.5, 150.0, 150.0],
            "signal": [1, 0, 0],
            "sl_price": [99.0, 100.0, 101.0],
        },
        index=idx,
    )
    return df
def test_run_works_with_unnamed_datetimeindex():
    sim = ExecutionSim(initial_capital=1000.0)
    df = _simple_df(index_name=None)

    trades = sim.run(df)
    assert not trades.empty
    # First trade should open on bar 0 and use timestamp of bar 1 as entry_time
    assert trades.iloc[0]["entry_time"] == df.index[1]
def test_run_works_with_named_datetimeindex():
    sim = ExecutionSim(initial_capital=1000.0)
    df = _simple_df(index_name="ts")

    trades = sim.run(df)
    assert not trades.empty
    # Behaviour should be identical regardless of index.name
    assert trades.iloc[0]["entry_time"] == df.index[1]

