# Deploying crypt to Railway — 14-day run guide

## Pre-requisites

| Item | Notes |
|------|-------|
| Railway account | Sign up at [railway.app](https://railway.app). Hobby plan ($5/month) is enough. |
| GitHub repo | This repository must be pushed to GitHub (public or private — both work). |
| Railway CLI | `npm install -g @railway/cli` or see [CLI install docs](https://docs.railway.com/guides/cli). Log in with `railway login`. |

---

## Step 1 — Create a new Railway project

1. Open [railway.app/new](https://railway.app/new).
2. Choose **Deploy from GitHub repo** → select the `crypt` repository.
3. Railway will ask which branch to deploy. Choose **`master`**.
   - If `master` is not listed, set the branch later: **Service Settings → Source → Branch = master**.
4. Railway creates a service and triggers the first build automatically.

---

## Step 2 — Set environment variables

Go to **Service → Variables** and add the following. All are plain text, no quotes needed.

### Required

| Variable | Value | Notes |
|----------|-------|-------|
| `TELEGRAM_BOT_TOKEN` | `123456:ABC-...` | From @BotFather |
| `TELEGRAM_CHAT_ID` | `-100...` or `12345...` | Your Telegram chat/channel ID |

### Recommended for the 14-day run

| Variable | Value | Notes |
|----------|-------|-------|
| `SYMBOLS` | `SOL-USDT-SWAP,TON-USDT-SWAP,XPL-USDT-SWAP` | Default 3 symbols |
| `LOG_LEVEL` | `INFO` | |
| `LOG_DIR` | `data/logs` | **Important:** puts log files on the persistent volume so they survive 14 days |
| `ALERT_CONFIDENCE_THRESHOLD` | `75` | |

### Optional (not used in MVP)

| Variable | Value |
|----------|-------|
| `OKX_API_KEY` | *(leave empty)* |
| `OKX_API_SECRET` | *(leave empty)* |
| `OKX_API_PASSPHRASE` | *(leave empty)* |

---

## Step 3 — Attach a persistent volume

This step is critical. Without a volume, parquet data and logs are lost on every redeploy.

1. In the Railway project canvas, open the **Command Palette** (`⌘K` / `Ctrl+K`) and search
   **"New Volume"**, or right-click the canvas → **Add Volume**.
2. When prompted to select a service, choose your `crypt` service.
3. Set **mount path** = `/app/data`.
4. Click **Create Volume**.

After the volume is attached, Railway redeploys the service. The `data/` directory (parquet
files) and `data/logs/` (log files, if `LOG_DIR=data/logs` is set) are now persistent.

> **Note:** Railway allows only one volume per service. Both parquet files and logs share
> the same `/app/data` volume via subdirectories — this is intentional (see ADR-0010).

---

## Step 4 — Disable "Serverless" (app-sleeping)

1. Go to **Service Settings → Networking**.
2. Find **Serverless** and make sure it is **disabled** (toggled off).

The crypt process makes OKX API calls every 4 h and sends heartbeats every 30 min, so it
would likely stay awake regardless — but disabling serverless eliminates any risk.

---

## Step 5 — Confirm the first deploy succeeded

After Railway finishes building, open **Deployments → latest deploy → Logs**. Look for:

```
Bootstrap: fetching initial history for ['SOL-USDT-SWAP', 'TON-USDT-SWAP', 'XPL-USDT-SWAP']
Bootstrap complete
Tick started
...
Tick complete: 3/3 symbols OK, 0 partial (missing data), 0 failed
```

If `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` are set correctly, a Telegram message
arrives within a few minutes of the first tick completing (confidence must be ≥ threshold).

---

## Step 6 — Monitor during the 14-day run

### Railway dashboard

- **Observability → Log Explorer**: live logs, searchable, filterable.
  > ⚠️ Hobby plan retains logs for **7 days** in the cloud viewer. Logs older than 7 days
  > are only available from the `data/logs/crypt.log` file on the persistent volume.

### Railway CLI

```bash
# Tail live logs
railway logs

# Fetch last 200 lines
railway logs --lines 200

# Logs from the last hour
railway logs --since 1h

# Filter errors only
railway logs --filter "@level:error"
```

### Heartbeat confirmation

The process logs `Heartbeat: alive at <timestamp>` every 30 minutes. If you stop seeing
heartbeats, the process has stalled — check logs and redeploy if needed.

---

## Step 7 — Extract data and logs at the end of the run

> **Important:** there is no file browser in Railway. Files are accessed through the service
> shell via `railway run`.

### Method A — Railway CLI shell (recommended)

```bash
# Link your local terminal to the project/service first (if not already linked)
railway link

# Copy parquet files to your local machine
railway run -- sh -c "find /app/data -name '*.parquet' | tar czf - -T -" > data_export.tar.gz

# Copy the full log file
railway run -- cat /app/data/logs/crypt.log > crypt_full.log

# Or copy all rotated log files (including compressed .gz archives)
railway run -- sh -c "tar czf - /app/data/logs/" > logs_export.tar.gz
```

### Method B — Volume dump template

Railway has a community "Volume Dump" template that can SSH into the container and produce
a downloadable archive. Search for it in the [Railway Template Gallery](https://railway.app/templates).

> ⚠️ The Volume Dump template requires temporarily detaching the volume from your service,
> which causes brief downtime. Prefer Method A for a live running service.

---

## Step 8 — Stop the service after 14 days

1. In the Railway dashboard, go to **Service Settings → Danger Zone → Remove Service**.
2. Or, to pause billing without deleting data: click **Service Settings → Pause Service**.
   The volume and its contents remain until you delete them.

To delete the volume (and free storage billing): **Volume settings → Delete Volume**.
Railway will email you a restoration link; the volume is permanently deleted after 48 hours.

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| Build fails with `uv: command not found` | Railpack did not detect uv | Ensure `uv.lock` is committed and pushed |
| `ModuleNotFoundError: crypt` | `uv sync --all-extras` didn't install the local package | Check `pyproject.toml` `[build-system]` section |
| Telegram alerts not arriving | Bot token or chat ID wrong, or `ALERT_CONFIDENCE_THRESHOLD` too high | Check Variables; lower threshold to 0 for a test run with `--once` |
| Service sleeping unexpectedly | Serverless feature still enabled | Go to Service Settings → Networking → disable Serverless |
| `data/` directory empty after restart | Volume not attached or mounted at wrong path | Verify volume mount path = `/app/data` |
| Log file missing from volume | `LOG_DIR` env var not set | Set `LOG_DIR=data/logs` in Variables, redeploy |
