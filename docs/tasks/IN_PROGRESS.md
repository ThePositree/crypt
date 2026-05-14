# In progress

## Next agent: Railway deployment for 14-day run

**Owner request (do not paraphrase, execute):**
Deploy the `crypt` project to [Railway](https://railway.app) for a 14-day continuous run.
Before touching any files, conduct the research described below. Then implement everything.
At the end, write a clear human-readable deployment checklist for the owner.

---

## Phase 1 — Research (mandatory, do before writing any code or config)

Use Context7 MCP + web search to answer the following questions.
Record findings as an ADR at `docs/decisions/0010-railway-deployment.md` (status: accepted)
before moving to Phase 2.

### 1.1 — Python / uv project on Railway

- How does Railway detect and build a Python project that uses `uv` as the package manager?
- Does Railway support `uv` natively, or do we need a custom `Dockerfile` / `nixpacks.toml`?
- What is the recommended `railway.toml` / `Dockerfile` approach for a project with
  `pyproject.toml` + `uv.lock`?
- What Python version does Railway default to, and how do we pin `3.12`?
- How do we pass the start command (`uv run python -m crypt`) to Railway?

### 1.2 — Auto-deploy on push to `master`

- How does Railway auto-deploy work when connected to a GitHub repo?
- Is auto-deploy triggered on any push, or only tagged releases?
- How to configure the branch (must be `master`, not `main`)?
- Are there any gotchas with Railway re-deploying mid-run (the process is long-lived, 4h cycle)?

### 1.3 — Log visibility

- Where and how can logs be viewed in the Railway dashboard?
- The project uses `loguru` writing to `logs/crypt.log` (with daily rotation) AND to stdout.
  Will Railway capture both? Is there any config needed?
- How long does Railway retain log history?
- Can logs be streamed or downloaded from the Railway CLI/API?

### 1.4 — Persistent files: `data/` and `logs/` extraction

- Railway containers are ephemeral by default. Does Railway offer persistent volumes?
- If yes: how do we mount a persistent volume to `/app/data` and `/app/logs`?
- If no: what is the recommended workaround for a 14-day run?
  (options: Railway Volume, writing to S3/R2, periodic Telegram dump, etc.)
- **Key question for owner:** after the 14-day run completes, can the owner pull the
  `data/*.parquet` and `logs/crypt.log` files out of Railway?
  Document the exact method (Railway CLI `railway run`, dashboard download, volume mount, etc.).
- Are there any free-tier limitations on volume size or file count?

### 1.5 — Free-tier / billing

- Railway Hobby plan: does it cover a long-lived Python process running 24/7 for 14 days?
- Is there a sleep/timeout for inactive services?
- Estimated cost for 14 days at low CPU / ~100 MB RAM.

---

## Phase 2 — Implementation

Based on research findings, create or modify the following.
**Do not create files that are not needed; skip items the research shows are unnecessary.**

### 2.1 — Build & run config

Decide (and justify in the ADR) between:
- `Dockerfile` (full control, no surprises)
- `nixpacks.toml` (lighter, Railway-native)
- `railway.toml` alone (if Railway uv support is sufficient)

Whatever you choose, the build must:
1. Install dependencies via `uv sync --all-extras --no-dev` (production install, no dev deps).
2. Start with `uv run python -m crypt`.
3. Pin Python 3.12.
4. Not copy `.env` into the image (secrets come from Railway environment variables).

### 2.2 — Environment variables

List every env var from `.env.example` that must be set in Railway dashboard.
**Required at minimum:**
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`
- `SYMBOLS` (default: `SOL-USDT-SWAP,TON-USDT-SWAP,XPL-USDT-SWAP`)
- `LOG_LEVEL` (default: `INFO`)
- `ALERT_CONFIDENCE_THRESHOLD` (default: `75`)

Optional (OKX keys — not used in MVP, but add as empty vars for future):
- `OKX_API_KEY`, `OKX_API_SECRET`, `OKX_API_PASSPHRASE`

### 2.3 — Persistent storage (if Railway Volumes are viable)

If Railway Volumes are available and work within free tier:
- Configure volume mount for `/app/data` and `/app/logs`.
- Document the `railway volume` CLI command to download files after the run.

If not viable on free tier:
- Decide on the best fallback and implement it (e.g. periodic Telegram file push, or note
  that the owner must use Railway CLI `railway run` to copy files before the container dies).

### 2.4 — `.gitignore` and secrets hygiene

Ensure `.env` is in `.gitignore` (it should already be, but verify).
Ensure no secrets will end up in the Railway build context.

### 2.5 — `railway.toml`

Create `railway.toml` at the repo root with at minimum:
- `[build]` section pointing to the build method chosen in 2.1.
- `[deploy]` section with `startCommand` and `restartPolicyType = "ON_FAILURE"`.
- Health-check config if Railway supports it (the project has a `HealthMonitor` class).

---

## Phase 3 — Owner instructions

Create `docs/deploy/railway.md` with a step-by-step guide for the owner:

1. Pre-requisites (Railway account, GitHub repo connected, Railway CLI installed).
2. Creating the project and linking the GitHub repo (with branch = `master`).
3. Setting environment variables in the Railway dashboard (full list with descriptions).
4. How to confirm the first deploy succeeded (logs to look for).
5. How to monitor the run during 14 days (dashboard, Railway CLI tail).
6. **How to extract `data/` and `logs/` files at the end of the run** — this is critical,
   give exact commands or steps.
7. How to stop the service after 14 days.

---

## Phase 4 — End-of-session housekeeping (standard)

1. Move this block from `IN_PROGRESS.md` to `DONE.md` (top, with date).
2. Update `BACKLOG.md` with anything discovered but not yet done.
3. Append an entry to `CHANGELOG.md`.
4. Update `README.md` if the run command or setup steps changed.
