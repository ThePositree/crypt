"""Strategy registry (single source of truth).

This module defines the canonical mapping from a **strategy registry key** to
the corresponding strategy class. CLI, GUI, docs and examples should import
from here to avoid drift.
"""

from typing import Final

from backtester.strategies.crypt_ensemble import CryptEnsembleStrategy
from backtester.strategies.dss_strategy import DSSStrategy
from backtester.strategies.dual_ma import DualMAStrategy
from backtester.strategies.forest import ForestStrategy
from backtester.strategies.fractal_rb import FractalRbStrategy
from backtester.strategies.fractal_rejection import FractalRejectionStrategy
from backtester.strategies.fvg_imbalance import FVGImbalanceStrategy
from backtester.strategies.liquidity_hunter import LiquidityHunter
from backtester.strategies.meta import MetaStrategy
from backtester.strategies.phase_routed import PhaseRoutedStrategy
from backtester.strategies.promoted_router import PromotedRouterStrategy
from backtester.strategies.rejection import RejectionStrategy
from backtester.strategies.som import SOMStrategy
from backtester.strategy import BaseStrategy

STRATEGIES: Final[dict[str, type[BaseStrategy]]] = {
    "dual_ma": DualMAStrategy,
    "meta": MetaStrategy,
    "liq_hunter": LiquidityHunter,
    "som": SOMStrategy,
    "forest": ForestStrategy,
    "fvg_imbalance": FVGImbalanceStrategy,
    "fractal_rejection": FractalRejectionStrategy,
    "rejection": RejectionStrategy,
    "fractal_rb": FractalRbStrategy,
    "phase_routed": PhaseRoutedStrategy,
    "promoted_router": PromotedRouterStrategy,
    "crypt_ensemble": CryptEnsembleStrategy,
    "dss_strategy": DSSStrategy,
}
