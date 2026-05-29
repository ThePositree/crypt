"""Backtest harness — M2 milestone (docs/backtest.md)."""

from crypt.backtest.execution_sim import (
    ExecutionSim,
    ExitReason,
    FundingRateModel,
    ParquetFundingModel,
    ZeroFundingModel,
)
from crypt.backtest.fee_model import ExitContext, FeeModel, StaticPercentFeeModel
from crypt.backtest.labels import compute_labels
from crypt.backtest.metrics import generate_metrics
from crypt.backtest.optimizer import OptResult, aggregate_weights_across_folds, run_optimizer
from crypt.backtest.recorder import BacktestRecorder
from crypt.backtest.replay import ReplayContextBuilder, ReplayParquetStore
from crypt.backtest.risk_model import BasicRiskModel, EntryContext, RiskModel, RiskResult
from crypt.backtest.walkforward import FoldSpec, generate_folds

__all__ = [
    "BacktestRecorder",
    "BasicRiskModel",
    "EntryContext",
    "ExecutionSim",
    "ExitContext",
    "ExitReason",
    "FeeModel",
    "FoldSpec",
    "FundingRateModel",
    "OptResult",
    "ParquetFundingModel",
    "ReplayContextBuilder",
    "ReplayParquetStore",
    "RiskModel",
    "RiskResult",
    "StaticPercentFeeModel",
    "ZeroFundingModel",
    "aggregate_weights_across_folds",
    "compute_labels",
    "generate_folds",
    "generate_metrics",
    "run_optimizer",
]
