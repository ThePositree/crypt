# ADR-0010: Railway deployment for M1 14-day continuous run

- **Status**: accepted
- **Date**: 2026-05-14
- **Owner**: agent

## Context

M1 is complete and must run continuously for ≥ 14 days to satisfy the milestone exit criteria.
The owner does not have a dedicated VPS. Railway is a managed PaaS that accepts a GitHub repo,
builds and deploys automatically, supports persistent volumes, and has a Hobby plan at $5/month.

Key requirements:
- Python 3.12 + uv as package manager.
- Process must run 24/7 for 14 days without manual intervention.
- Parquet files in `data/` must survive container restarts.
- Logs must be accessible for the full 14-day window.
- Owner must be able to extract `data/*.parquet` and logs after the run.

## Decision

Deploy to **Railway** using **Railpack** (Railway's current default build system) with a
`railway.toml` configuration file and a Railway persistent **Volume** mounted at `/app/data`.

No Dockerfile is needed: Railpack automatically detects uv from `pyproject.toml` + `uv.lock`
and installs the correct toolchain.

Logs are redirected to `data/logs/` (same volume) via the `LOG_DIR` environment variable,
keeping both parquet files and log files on the single persistent volume.

## Alternatives considered

### Dockerfile + Railpack-free approach
- Pros: full control, no Railway-specific build behaviour.
- Cons: more boilerplate; Railpack handles uv natively so a Dockerfile adds zero value here.
  **Rejected.**

### Nixpacks
- Railway's legacy build system, now in maintenance mode. Superseded by Railpack.
  **Rejected.**

### Railway-managed `nixpacks.toml`
- Was the recommended path before Railpack. Now obsolete.
  **Rejected.**

### S3 / Cloudflare R2 for parquet persistence
- Adds an external dependency and cost for a 14-day MVP run. Overkill.
  **Rejected.** Railway Volume is sufficient.

### Single volume at `/app` (whole app directory)
- Would shadow the app code because Railway places code in `/app` before starting.
  Volumes are NOT overlays; mounting at `/app` would hide the application files.
  **Rejected.** Mount at `/app/data` only.

## Consequences

### Positive
- Zero-config build: Railpack detects uv automatically.
- Parquet files and logs are both persistent (single volume, two subdirs).
- Auto-deploy on push to `master`; restart on failure via `restartPolicyType = "ON_FAILURE"`.
- Estimated cost for 14 days (100 MB RAM, negligible CPU): well within Hobby $5 included
  usage credit. Realistic bill ≈ $5 (subscription fee only).

### Negative / Watch-outs
- **Log retention on Hobby plan is 7 days.** Railway's cloud log viewer will only show the
  last 7 days. Since logs are also written to `/app/data/logs/crypt.log` (on the Volume),
  the full 14-day log file is still accessible via `railway ssh` (not `railway run`,
  which executes locally).
- **Re-deploy causes brief downtime** when a Volume is attached (Railway prevents two
  simultaneous mounts for data integrity). Avoid pushing to `master` during the 14-day run.
- **Single volume per service** — `data/` and `logs/` share the same 5 GB volume. Not an
  issue at this scale (parquet files < 100 MB, logs < 10 MB for 14 days).
- **Serverless (app-sleeping) must be disabled** in Service Settings. The app makes OKX
  calls every 4 h and sends heartbeats every 30 min, so it would likely stay awake anyway,
  but explicit disabling is safer.

### To revisit later
- If the run grows beyond 14 days, consider upgrading to Pro (30-day log retention, 50 GB volume).
- M2 backtest will need a larger volume; resize is supported live on Hobby.

## References

- Railpack Python docs: https://railpack.com/languages/python.md
- Railway Volumes: https://docs.railway.com/volumes
- Railway config-as-code: https://docs.railway.com/reference/config-as-code
- Railway pricing: https://docs.railway.com/reference/pricing/plans
- Railway logs: https://docs.railway.com/observability/logs
