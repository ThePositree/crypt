# Deploying live execution to Railway

This Railway service runs `python -m crypt --execution-only` after a mandatory
data preflight. The preflight removes zero-byte parquet files, checks live OHLCV
coverage for H1/H4/D1, and runs the existing OKX backfill before the trading
process starts when data is missing, stale, or gapped.

The first deployment can take a long time. That is intentional: a bot that
starts on empty parquet files is more dangerous than a slow deployment.

Railway runtime configuration is the source of truth for the active live
strategy. If `EXECUTION_STRATEGY_CONFIG` in Railway/env disagrees with prose
docs, stop and ask the owner before changing live behavior.

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
- `EXECUTION_RISK_BASE_CHECKPOINT_DIR=/app/data/risk_base_checkpoints`
- `LOG_DIR=/app/data/logs`
- `EXECUTION_STRATEGY_CONFIG=strategies/archive/filtered_donor_portfolio_post_adr0058_tail_control_v6_drop_negative_v5.json`
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
| `EXECUTION_RISK_BASE_CHECKPOINT_DIR` | `/app/data/risk_base_checkpoints` |
| `LOG_DIR` | `/app/data/logs` |
| `EXECUTION_STRATEGY_CONFIG` | Override only when deploying a different archived strategy JSON |

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

Startup is intentionally non-interactive. Railway must not wait for a human
confirmation when candles are missing: with bootstrap enabled it attempts the
configured backfill, and with bootstrap disabled any missing required data is
an operator configuration error to fix before live order logic starts.

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

The live executor must also log the resolved state path, checkpoint directory,
loaded state generation, and verified monthly risk window/base. A warning that
new entries are blocked for risk-base continuity is a safety stop: existing
positions still synchronize and close normally.

## Monthly risk-base migration and recovery

The first deployment containing ADR-0059 must not change July's historical
base mid-month. Schedule this deploy outside an H1 boundary (avoid roughly
`HH:58` through `HH:05` UTC), preserve the current Telegram/log evidence, and
confirm that the startup H1 callback reports its normal no-catch-up behaviour.
For the current reconciled state, set all three Railway variables for one
deploy only:

```text
EXECUTION_RISK_BASE_ADOPT_EXISTING_STATE=true
EXECUTION_RISK_BASE_ADOPT_EXPECTED_MONTH=2026-07
EXECUTION_RISK_BASE_ADOPT_EXPECTED_BASE=102.3381502678064
```

After startup reports a clean sync and an adopted checkpoint, verify the
durable pair before removing the variables and restarting once. The expected
July checkpoint pair is:

```text
/app/data/risk_base_checkpoints/2026-07.json
/app/data/risk_base_checkpoints/2026-07.backup.json
```

It must retain the exact current persisted value `102.3381502678064`; do not
replace historical July positions with a guessed `$104.77` number. Confirm the
pair exists, has matching hashes, and that each file exposes the expected base
and `/app/data/live_positions.json` path:

```bash
railway ssh --service crypt --environment production -- \
  sha256sum /app/data/risk_base_checkpoints/2026-07.json \
  /app/data/risk_base_checkpoints/2026-07.backup.json
railway ssh --service crypt --environment production -- \
  grep -E 'monthly_risk_base|state_path|checkpoint_checksum' \
  /app/data/risk_base_checkpoints/2026-07.json \
  /app/data/risk_base_checkpoints/2026-07.backup.json
railway ssh --service crypt --environment production -- \
  ls -l /app/data/live_positions.json /app/data/live_positions.previous.json
```

The two hashes must match; both files must show the exact base and state path.
Only then remove all three adoption variables and restart. The August anchor is
created at the first post-sync actionable H1 batch that reaches risk sizing,
not at midnight and not during a blocked or startup callback.

If Railway reports a missing/conflicting checkpoint, do not add a guessed
balance through the dashboard. Leave new entries paused, export the state,
checkpoint directory, and persistent log, then restore the confirmed checkpoint
or investigate the state path/volume:

```bash
railway ssh -- sh -c 'ls -la /app/data/risk_base_checkpoints /app/data/live_positions*'
railway ssh -- cat /app/data/live_positions.json > live_positions_export.json
railway ssh -- sh -c 'tar -C /app/data -czf - risk_base_checkpoints logs' > execution_recovery_export.tgz
```

`Цена входа отличается от плана` is an alert-only fill-drift notification: the
trade was opened. `Сигнал пропущен из-за защиты` means a safety block prevented
an otherwise actionable entry and should be preserved for later reconciliation.

## Monitoring and export

Railway dashboard logs are short-lived. Persistent logs are written to
`/app/data/logs/crypt.log` and rotated daily.

Runtime logging is shared by the preflight, backfill, and live process:
`DEBUG` is suppressed when `LOG_LEVEL=INFO`, normal `INFO` backfill progress
goes to stdout, and only `WARNING`/`ERROR` lines go to stderr. Railway should
therefore tag normal preflight/backfill output as informational logs, not
errors.

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
