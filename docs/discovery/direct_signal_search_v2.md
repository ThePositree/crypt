# Direct Signal Search v2

Status: historical note.

DSS v2 has been superseded by DSS v3. Do not use this document to build owner
commands or new implementation work. The current contract is
`docs/discovery/direct_signal_search_v3.md` and the compact command surface is
`docs/cli.md`.

The useful carry-over from v2 is quality-diverse directional candidate
discovery. The obsolete parts are old internal budget wording, old artifacts,
old sampler flags, and any command examples that required the owner or an
agent to choose internal evaluation phases.

Current DSS owner command:

```bash
UV_CACHE_DIR=/tmp/uv-cache PYTHONPATH=src uv run backtester search-signals-matrix \
  --output-root results/dss_v3_sol_all_endless
```
