# In progress

Nothing is currently in progress. The previous session finished cleanly.

## Next agent: where to start

The scaffold (M0) is complete. The next session should begin **M1** by
picking the first cluster of P0 items from `BACKLOG.md`:

1. `pyproject.toml` with `uv` and pinned dependencies.
2. `src/crypt/config.py` (pydantic-settings).
3. `src/crypt/models.py` (typed data contracts).
4. `src/crypt/exchange/{base.py,okx.py}` (ccxt-backed OKX client, with
   smoke test against the public OHLCV endpoint for `BTC-USDT-SWAP`).
5. **Verify `XPL-USDT-SWAP` exists on OKX** — if not, ask the owner for a
   replacement before continuing.

Use Context7 (`/ccxt/ccxt` and `/websites/okx_docs-v5_en`) for any API
detail. Write the spec for any module that does not yet have one in
`docs/engines/` before writing its implementation. Update this file as work
starts and ends.
