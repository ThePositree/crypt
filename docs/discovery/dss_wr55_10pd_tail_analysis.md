# DSS WR55/10pd Tail Analysis

Status: historical note.

This old tail analysis belonged to the retired DSS v2 search contract. It is
kept only as evidence that strict all-window WR55 directional gating discarded
many near-miss families. It is not a current command reference and should not
drive new implementation work.

Current DSS v3 uses persistent multi-timeframe directional quality-diversity
search. Use:

```bash
UV_CACHE_DIR=/tmp/uv-cache PYTHONPATH=src uv run backtester search-signals-matrix \
  --output-root results/dss_v3_sol_all_endless
```

See `docs/discovery/direct_signal_search_v3.md` for the current DSS contract.
