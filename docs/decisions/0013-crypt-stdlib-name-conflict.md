# ADR-0013: `crypt` package name conflicts with deprecated Python stdlib module

- **Status**: accepted
- **Date**: 2026-05-29
- **Owner**: agent

## Context

The project's top-level package is named `crypt`. Python 3.12 ships a deprecated
standard-library module with the same name (`crypt.py`, used for Unix password
hashing). The stdlib module is a plain `.py` file, not a package directory, so it
cannot have sub-modules like `crypt.models`.

The conflict surfaces whenever a Python process resolves `import crypt` before the
`src/` directory is on `sys.path`:

```
ModuleNotFoundError: No module named 'crypt.models'; 'crypt' is not a package
```

This happens silently in three contexts:

1. **`python -m crypt`** — if `src/` is not prepended to `PYTHONPATH`, the stdlib
   `crypt` module is found first and Python executes it (it does nothing, exits 0).
2. **`pytest`** — without `pythonpath = ["src"]` in `pyproject.toml`, conftest
   imports fail immediately.
3. **`mypy` / any tool** that walks `sys.path` without a `PYTHONPATH=src` prefix.

The issue was partially known before the 14-day run (Railway `PYTHONPATH=/app/src`
workaround existed in `railway.toml`), but was not systematically fixed for local
development and CI, causing agent sessions to spend time debugging it from scratch.

## Decision

Apply the minimum set of fixes so that every invocation path — local `pytest`,
`mypy`, CI GitHub Actions, Railway, pre-commit — works without a manual
`PYTHONPATH` export.

### Fix 1 — `pyproject.toml`: pytest `pythonpath`

```toml
[tool.pytest.ini_options]
pythonpath = ["src"]
```

`pytest` respects `pythonpath` since pytest ≥ 7.0 (we pin ≥ 8.0). This prepends
`src/` to `sys.path` before any collection, making `import crypt.models` resolve to
the project package.

### Fix 2 — `railway.toml`: PYTHONPATH in start command (already in place)

```toml
startCommand = "PYTHONPATH=/app/src uv run --no-dev python -u -m crypt"
```

This was already present from the Railway deployment work. No change needed.

### Fix 3 — `.env.example`: document local PYTHONPATH (recommended, not enforced)

Add `PYTHONPATH=src` to `.env.example` as a reminder. `pydantic-settings` reads
`.env`; `python-dotenv` (not a dependency) would need it too. Agents who run
`python -m crypt` directly rather than through `uv run` should export it manually.

### What we deliberately do NOT do

- **Rename the package** (`crypt` → `signal_engine` or `trad` etc.): would
  require updating every import in ~36 source files, every test, the README, and
  every doc reference. The rename would also break Railway's auto-detected start
  command. High cost, zero functional benefit — the fixes above solve the problem
  at the entry points instead.
- **Add `sys.path.insert(0, "src")` in `conftest.py`**: fragile, non-standard,
  and redundant given the `pythonpath` option.
- **Add a `conftest.py` at the repo root**: pytest already discovers `tests/`,
  adding a root conftest only for path manipulation would be confusing.

## Consequences

### Positive

- `uv run pytest` works out of the box with no environment variables.
- `uv run mypy --strict src` works (mypy reads `sys.path` after pytest adjusts
  it, and mypy's own invocation already starts with `src/crypt/` since we pass
  `src` as the argument).
- CI `.github/workflows/ci.yml` does not need a special env var export step.
- Future agents see one source of truth (`pyproject.toml`) rather than scattered
  `PYTHONPATH` exports.

### Negative

- The `pythonpath` fix only helps tools that respect pytest config (pytest itself).
  If an agent runs `python -m crypt` without `PYTHONPATH=src` they will still hit
  the stdlib module. The `.env.example` note mitigates this.

### Agent instructions going forward

**Do not** run `python -m crypt` directly. Always use one of:

```bash
# Correct — uv sets PYTHONPATH via railway.toml / the src layout detection:
PYTHONPATH=src uv run python -m crypt

# Or from .env (if PYTHONPATH=src is set there):
uv run python -m crypt

# Tests always work:
uv run pytest
```

If you see `ModuleNotFoundError: No module named 'crypt.models'`, the fix is:

```bash
export PYTHONPATH=src
```

## References

- `railway.toml` (existing `PYTHONPATH=/app/src` start command)
- `docs/deploy/railway.md` troubleshooting table (row: "No log output...")
- `pyproject.toml` `[tool.pytest.ini_options]` (Fix 1 applied here)
