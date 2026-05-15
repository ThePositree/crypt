# Continuous integration

Status: **proposed, post-M1 run** (BACKLOG P0 — without this the next
"fix" session will inevitably break something silently).

The project today relies on a future agent remembering to run `ruff`,
`mypy --strict`, and `pytest` before committing. This is unreliable.
Per the AI-first workflow, agents come and go session by session;
muscle memory does not persist.

This document specifies the CI we want.

---

## 1. Goals

- Every push to any branch triggers a green/red build.
- Every PR to `master` is gated on the same checks the agent currently
  runs locally.
- The check set is exhaustive enough that a passing build is a
  high-confidence "safe to merge".
- Configuration lives in one file (`.github/workflows/ci.yml`) — no
  scattered shell scripts.

Non-goals:
- Self-hosted runners. We use GitHub-hosted ones (free for public and
  private repos at the volumes we will hit).
- Deployment from CI. Railway already auto-deploys on push to `master`.
- Notifications to Slack / email. The GitHub UI is sufficient at this
  scale.

---

## 2. Required checks

1. **Ruff lint**: `ruff check src tests`. Fails on any rule we have
   selected in `pyproject.toml`.
2. **Ruff format**: `ruff format --check src tests`. Fails if anything
   would be re-formatted.
3. **Mypy strict**: `mypy --strict src`. Must remain at 0 errors.
4. **Pytest**: `pytest -q`. Currently 42 tests; growing.
5. **uv lock integrity**: `uv lock --check` (or equivalent) to ensure
   `uv.lock` matches `pyproject.toml`. Prevents the "I added a dep but
   forgot to lock" regression.
6. **No accidentally-committed secrets**: a minimal `gitleaks` step.
   Free, fast, catches API tokens.

Every check is a required status check on the `master` branch in branch
protection rules.

---

## 3. Workflow file

`.github/workflows/ci.yml` outline:

```yaml
name: ci

on:
  push:
    branches: ["**"]
  pull_request:
    branches: [master]

jobs:
  lint-type-test:
    runs-on: ubuntu-latest
    timeout-minutes: 10
    steps:
      - uses: actions/checkout@v4

      - name: Install uv
        uses: astral-sh/setup-uv@v3
        with:
          version: "latest"

      - name: Set up Python
        run: uv python install 3.12

      - name: Sync deps
        run: uv sync --all-extras --frozen

      - name: ruff lint
        run: uv run ruff check src tests

      - name: ruff format check
        run: uv run ruff format --check src tests

      - name: mypy strict
        run: uv run mypy --strict src

      - name: pytest
        run: uv run pytest -q

      - name: uv lock check
        run: uv lock --check

  secret-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - uses: gitleaks/gitleaks-action@v2
        env:
          GITLEAKS_LICENSE: ""
```

Notes:
- `uv sync --frozen` ensures CI matches the lockfile exactly.
- `--all-extras` so the `ta` extra (pandas-ta) is installed; tests use
  it.
- `NUMBA_DISABLE_JIT=1` is **not** needed in CI — the GitHub runner
  has plenty of CPU; numba init is fine. We only disable JIT in
  Railway's constrained containers.

Confirm the latest pinned actions (`actions/checkout`, `astral-sh/setup-uv`,
`gitleaks/gitleaks-action`) via Context7 or upstream README at
implementation time; pin to current major.

---

## 4. Branch protection (manual setup)

After the workflow is merged, the owner (or an agent with repo admin)
sets in GitHub repo settings:

- Branch protection rule for `master`:
  - Require pull request before merging.
  - Require status checks to pass: `lint-type-test`, `secret-scan`.
  - Require branches to be up to date before merging.
  - Disallow force-pushes.

This last point is the safeguard during the 14-day run: a force-push
could redeploy unintended commits.

---

## 5. Pre-commit hooks (developer ergonomics)

Local pre-commit configuration mirrors CI so an agent catches issues
before the push.

`.pre-commit-config.yaml`:

```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.6.9                    # pin; bump via Context7-vetted update
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format

  - repo: local
    hooks:
      - id: mypy
        name: mypy
        entry: uv run mypy --strict src
        language: system
        types: [python]
        pass_filenames: false
```

README gets a `Developer setup` section telling future agents to run:

```bash
uv tool install pre-commit
pre-commit install
```

---

## 6. CI behaviour during the 14-day Railway run

Important: CI runs on every push, but **we are not pushing during the
14-day run** because Railway redeploys cause downtime (ADR-0010). So in
practice, the first CI run will be on the post-run merge that brings in
all the doc and code work agents do during these two weeks.

Recommended path:
1. Write CI workflow on a `chore/ci` branch.
2. Verify it passes on a few cosmetic commits before opening the PR.
3. Open the PR; do not merge until the 14-day run is over.
4. Then enable branch protection.

---

## 7. Tests for the CI itself

Not in the traditional sense, but:
- A handwritten `cheatsheet.md` (one paragraph in this file is enough)
  lists the exact commands CI runs. A future agent can replicate
  locally to debug a CI failure without reading the YAML.

Cheatsheet:
```bash
uv sync --all-extras --frozen
uv run ruff check src tests
uv run ruff format --check src tests
uv run mypy --strict src
uv run pytest -q
uv lock --check
```

---

## 8. Coverage and quality gates (deferred)

We deliberately do NOT add a coverage gate yet. Two reasons:

- Coverage targets without judgment lead to test-shaped code.
- The existing 42 tests cover engines and aggregator end-to-end; the
  remaining gaps (sinks, runtime) are integration-flavoured and need
  real fixtures, not coverage-driven micro-tests.

After M3, revisit with a target like "engines + aggregator ≥ 90%
line coverage; runtime + sinks: must have integration tests for the
critical paths".

---

## 9. Known weaknesses

- Pin churn: pinning action versions and ruff/mypy versions means
  someone has to re-pin them. Agents should bump pinned versions when
  the upstream releases a relevant fix, via Context7-vetted changelogs.
- Mypy strict on a growing codebase is occasionally painful — false
  positives in third-party stub gaps. The `[[tool.mypy.overrides]]`
  block in `pyproject.toml` is the escape hatch; keep it small and
  reviewed.
- Gitleaks free tier has rate limits on private repos. If we hit them,
  switch to `trufflehog` which is fully self-contained.
- GitHub-hosted Ubuntu runners have a minute quota on private repos
  (~2000 min/month free). At ~3 min/build * 30 builds/month we use
  ~90 min — well within the budget.
