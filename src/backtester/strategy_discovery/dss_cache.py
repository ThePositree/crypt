"""DSS signal cache — LRU cache for generated signal DataFrames.

Keyed by (signal_cache_key, window_label). Per-process; not shared between
parallel Optuna workers.
"""

from __future__ import annotations

import logging
from collections import OrderedDict
from collections.abc import Callable

import pandas as pd

from backtester.strategy_discovery.dss_config import TrialConfig

logger = logging.getLogger(__name__)

_DEFAULT_MAX_ENTRIES = 2_000


class DSSSignalCache:
    """LRU cache for signal DataFrames.

    Parameters
    ----------
    max_entries:
        Maximum number of (signal_key, window_label) entries before eviction.
    """

    def __init__(self, max_entries: int = _DEFAULT_MAX_ENTRIES) -> None:
        self._max_entries = max_entries
        self._cache: OrderedDict[tuple[str, str], pd.DataFrame] = OrderedDict()
        self._hits = 0
        self._misses = 0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_or_compute(
        self,
        config: TrialConfig,
        window_label: str,
        compute_fn: Callable[[], pd.DataFrame],
    ) -> pd.DataFrame:
        """Return cached DataFrame or compute and cache it.

        Parameters
        ----------
        config:
            Trial config; only the signal part (trigger + filters + atr_sl_mult)
            determines the cache key.
        window_label:
            Identifies which window's data was used.
        compute_fn:
            Called when cache misses; must return the signal DataFrame.
        """
        key = (config.signal_cache_key, window_label)
        if key in self._cache:
            self._hits += 1
            self._cache.move_to_end(key)
            return self._cache[key]

        self._misses += 1
        result = compute_fn()

        if len(self._cache) >= self._max_entries:
            oldest_key, _ = self._cache.popitem(last=False)
            logger.debug("Cache evicted %s", oldest_key)

        self._cache[key] = result
        return result

    def invalidate(self, config: TrialConfig, window_label: str) -> None:
        """Remove a specific entry from the cache."""
        key = (config.signal_cache_key, window_label)
        self._cache.pop(key, None)

    def clear(self) -> None:
        """Remove all cached entries."""
        self._cache.clear()
        self._hits = 0
        self._misses = 0

    @property
    def size(self) -> int:
        return len(self._cache)

    @property
    def hits(self) -> int:
        return self._hits

    @property
    def misses(self) -> int:
        return self._misses

    @property
    def hit_rate(self) -> float:
        total = self._hits + self._misses
        return self._hits / total if total > 0 else 0.0
