# Deploying live execution to Railway

This Railway service runs `python -m crypt --execution-only` after a mandatory
data preflight. The preflight removes zero-byte parquet files, checks live OHLCV
coverage for H1/H4/D1, and runs the existing OKX backfill before the trading
process starts when data is missing, stale, or gapped.

The first deployment can take a long time. That is intentional: a bot that
starts on empty parquet files is more dangerous than a slow deployment.

## Railway service

1. Create a Railway project from the GitHub repository.
2. Attach one persistent volume to the service.
3. Set the volume mount path to `/app/data`.
4. Keep Serverless disabled so the process is not put to sleep.

`railway.toml` starts `scripts/railway_live_start.sh`. The script sets safe
container defaults:

- `DATA_DIR=/app/data`
- `EXECUTION_DATA_DIR=/app/data`
- `EXECUTION_STATE_PATH=/app/data/live_positions.json`
- `LOG_DIR=/app/data/logs`
- `PYTHONPATH=/app/src`
- `NUMBA_DISABLE_JIT=1`

Do not override the Railway dashboard start command unless you also preserve
the preflight step:

```bash
uv run --no-dev python -m crypt.runtime.deploy_preflight
uv run --no-dev python -u -m crypt --execution-only
```

## Required variables

Set these in **Service -> Variables**:

| Variable | Value |
| --- | --- |
| `TELEGRAM_BOT_TOKEN` | Telegram bot token |
| `TELEGRAM_CHAT_ID` | Telegram chat/channel ID |
| `OKX_API_KEY` | OKX API key |
| `OKX_API_SECRET` | OKX API secret |
| `OKX_API_PASSPHRASE` | OKX API passphrase |
| `EXECUTION_ENABLED` | `true` |
| `EXECUTION_DRY_RUN` | `false` for live money, `true` for paper validation |
| `EXECUTION_STRATEGY_CONFIG` | `strategies/archive/filtered_donor_portfolio_post_adr0058_tail_control_v6_drop_negative_v5.json` |
| `EXECUTION_SYMBOLS` | `SOL-USDT-SWAP` |
| `EXECUTION_REQUIRE_EXCHANGE_SYNC` | `true` |

Recommended explicit values:

| Variable | Value |
| --- | --- |
| `PYTHONUNBUFFERED` | `1` |
| `LOG_LEVEL` | `INFO` |
| `DATA_DIR` | `/app/data` |
| `EXECUTION_DATA_DIR` | `/app/data` |
| `EXECUTION_STATE_PATH` | `/app/data/live_positions.json` |
| `LOG_DIR` | `/app/data/logs` |

## Bootstrap variables

These control the startup preflight:

| Variable | Default | Meaning |
| --- | --- | --- |
| `EXECUTION_BOOTSTRAP_ENABLED` | `true` | Run preflight before live execution |
| `EXECUTION_BOOTSTRAP_FROM` | `2021-12-18` | Start date for idempotent OKX backfill |
| `EXECUTION_BOOTSTRAP_TO` | empty | Explicit exclusive end date, `YYYY-MM-DD` |
| `EXECUTION_BOOTSTRAP_TO_BUFFER_DAYS` | `1` | When `TO` is empty, backfill through tomorrow UTC plus this buffer |
| `EXECUTION_BOOTSTRAP_DATA_TYPES` | `ohlcv` | Comma-separated backfill types |
| `EXECUTION_BOOTSTRAP_PAGE_SIZE` | `100` | OKX page size, capped at 100 |
| `EXECUTION_BOOTSTRAP_MAX_RPS` | `5` | Max OKX requests per second |
| `EXECUTION_BOOTSTRAP_FORCE` | `false` | Force idempotent backfill on every start |

Live execution requires `ohlcv` because the strategy runner uses H1/H4/D1
closed candles. Add `execution_1m` only when the Railway volume should also
build minute replay data for later investigation. That can make the first
deploy much slower.

Examples:

```text
EXECUTION_BOOTSTRAP_DATA_TYPES=ohlcv
```

```text
EXECUTION_BOOTSTRAP_DATA_TYPES=ohlcv,execution_1m
EXECUTION_BOOTSTRAP_MAX_RPS=3
```

## Expected startup logs

On a fresh or damaged volume, expect:

```text
Railway live preflight requires backfill: SOL-USDT-SWAP 1h missing or empty parquet
Railway live preflight backfill starting: data_dir=/app/data ...
Backfill SOL-USDT-SWAP | 2021-12-18 -> ...
Backfill complete: SOL-USDT-SWAP
Railway live preflight backfill complete
Starting crypt [execution-only] ...
```

On a healthy volume, expect:

```text
Railway live preflight OK: data_dir=/app/data symbols=['SOL-USDT-SWAP'] data_types=['ohlcv'] no backfill needed
Starting crypt [execution-only] ...
```

## Monitoring and export

Railway dashboard logs are short-lived. Persistent logs are written to
`/app/data/logs/crypt.log` and rotated daily.

Useful commands after `railway link`:

```bash
railway logs
railway ssh -- sh -c 'ls -la /app/data && find /app/data -name "*.parquet" | wc -l'
railway ssh -- cat /app/data/logs/crypt.log > crypt_full.log
railway ssh -- sh -c 'find /app/data -name "*.parquet" | tar czf - -T -' > data_export.tar.gz
```

Use `railway ssh` for volume files. `railway run` executes locally with Railway
variables and does not see `/app/data`.

## Troubleshooting

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| Preflight keeps backfilling | Data is missing, stale, gapped, zero-byte, or `EXECUTION_BOOTSTRAP_FORCE=true` | Check `/app/data/SOL-USDT-SWAP/*.parquet` and remove `FORCE` after repair |
| `refusing to overwrite unreadable parquet file` | Existing parquet is corrupt but non-empty | Inspect/export the file first; if it is disposable deploy damage, remove it and redeploy |
| `data/` empty after restart | Volume is missing or mounted elsewhere | Attach volume at `/app/data` |
| `ModuleNotFoundError: crypt.models` | `PYTHONPATH` was overridden | Restore `/app/src` or use the repository start script |
| Logs are not persisted | `LOG_DIR` is not on the volume | Set `LOG_DIR=/app/data/logs` |
| Orders do not open | Exchange sync failed or `EXECUTION_DRY_RUN=true` | Check startup sync lines and Railway variables |
