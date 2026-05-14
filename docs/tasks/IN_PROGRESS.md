# In progress

Nothing is currently in progress. Session 2 finished cleanly.

## Next agent: where to start

M1 code layer is complete. The next session should focus on **validation and
MVP wiring**:

1. **Verify `XPL-USDT-SWAP` on OKX** — run `uv run python -m crypt --once
   --symbols XPL-USDT-SWAP` (requires network). If the symbol does not exist,
   ask the owner for a replacement and update `SYMBOLS` in `.env.example` and
   `README.md`.
2. **Smoke test against OKX** — run `uv run python -m crypt --once` with a
   real `.env` and verify that candle data is fetched and a verdict is printed
   to the console. Check for any OKX response-shape surprises in `okx.py`
   (especially the `rubik/stat` endpoints — column names may differ from what
   was assumed).
3. **Bootstrap script** (BACKLOG P1) — first-run helper that fetches ≥ 200
   H4 candles before the scheduler starts. Currently `bootstrap()` in
   `Orchestrator` calls `ingest_all()` which should already do this; verify.
4. **Logging configuration** (BACKLOG P1) — loguru file sink with JSON mode.
5. **mypy** — run `uv run mypy src/` and fix type errors that surface.
6. **Health-check helper** — verify OKX + Telegram connectivity on startup.
7. Update `README.md` Quick start section (no longer a placeholder).
