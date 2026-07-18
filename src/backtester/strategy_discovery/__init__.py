from __future__ import annotations

from backtester.strategy_discovery.catcma_qd import run_catcma_qd_search
from backtester.strategy_discovery.convert import (
    DiscoveryConversionError,
    convert_discovery_strategy,
    load_and_convert_discovery_strategy,
)
from backtester.strategy_discovery.dss_cache import DSSSignalCache
from backtester.strategy_discovery.dss_config import (
    DSSBehavior,
    DSSCandidate,
    DSSConfig,
    DSSSearchSpace,
    DSSWindowSpec,
    TrialConfig,
)
from backtester.strategy_discovery.dss_objective import DSSObjective
from backtester.strategy_discovery.dss_report import write_dss_report
from backtester.strategy_discovery.dss_v2 import run_dss_v2_search
from backtester.strategy_discovery.hyperband_qd import run_hyperband_qd_search
from backtester.strategy_discovery.island_qd import run_island_qd_search
from backtester.strategy_discovery.parameterized_filters import parameterized_filter_catalog
from backtester.strategy_discovery.parameterized_triggers import (
    parameterized_trigger_catalog,
    parameterized_trigger_param_space,
)
from backtester.strategy_discovery.pinescript_catalog import (
    pinescript_filter_catalog,
    pinescript_filter_param_space,
    pinescript_trigger_catalog,
    pinescript_trigger_param_space,
)
from backtester.strategy_discovery.search import (
    DiscoveryConfig,
    DiscoveryWindow,
    run_strategy_discovery,
)
from backtester.strategy_discovery.signal_composer import SignalComposer
from backtester.strategy_discovery.smac_qd import run_smac_qd_search

__all__ = [
    "DSSBehavior",
    "DSSCandidate",
    "DSSConfig",
    "DSSObjective",
    "DSSSearchSpace",
    "DSSSignalCache",
    "DSSWindowSpec",
    "DiscoveryConfig",
    "DiscoveryConversionError",
    "DiscoveryWindow",
    "SignalComposer",
    "TrialConfig",
    "convert_discovery_strategy",
    "load_and_convert_discovery_strategy",
    "parameterized_filter_catalog",
    "parameterized_trigger_catalog",
    "parameterized_trigger_param_space",
    "pinescript_filter_catalog",
    "pinescript_filter_param_space",
    "pinescript_trigger_catalog",
    "pinescript_trigger_param_space",
    "run_catcma_qd_search",
    "run_dss_v2_search",
    "run_hyperband_qd_search",
    "run_island_qd_search",
    "run_smac_qd_search",
    "run_strategy_discovery",
    "write_dss_report",
]
