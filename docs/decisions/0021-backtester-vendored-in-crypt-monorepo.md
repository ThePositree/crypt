# ADR-0021: Vend `backtester/` into the `crypt` monorepo

- **Status**: accepted
- **Date**: 2026-06-02
- **Owner**: owner (direction in chat); agent documented
- **Supersedes**: the repository-layout assumption in ADR-0018 and docs that
  described `backtester/` as a separate nested git repository. ADR-0018 itself
  (donor package as canonical M2 architecture) remains in force.

## Context

`backtester/` began as an external package at
`https://github.com/AuriumX/backtester`, cloned into the workspace with its
own `.git` directory. That layout caused several problems:

- `git add backtester/` from the `crypt` root staged only a gitlink (embedded
  repo pointer), not the source files.
- Clones of `crypt` did not receive backtester contents unless a submodule was
  configured manually.
- Donor changes (`crypt_ensemble`, MTF loaders, structural SL) lived only in
  the nested repo's working tree and were easy to commit in the wrong place.

ADR-0018 already treats `backtester/` as the canonical M2 execution package
inside this workspace. The owner decided to fold it into the `crypt` monorepo
so strategy and ensemble work share one history and one push target.

## Decision

Track `backtester/` as ordinary source in the `crypt` repository:

1. Remove the nested `backtester/.git` directory (one-time migration).
2. Do **not** register `backtester/` as a git submodule.
3. Keep `backtester/` as a separate **Python package** with its own
   `pyproject.toml`, `uv.lock`, and tests — only the git boundary moves.
4. Preserve provenance in ported files via existing header comments pointing at
   `backtester/src/backtester/<file>.py` and, where applicable,
   `https://github.com/AuriumX/backtester` as the upstream origin.
5. Continue ADR-0018 donor safety rules: prefer additive donor edits, minimal
   surface changes, and focused tests.

## One-time operator steps

After removing the nested repository metadata:

```bash
rm -rf backtester/.git
cd /path/to/crypt
git add backtester/
git status   # must list files under backtester/, not a single gitlink
git commit -m "Vend backtester into crypt monorepo (ADR-0021)"
```

If `backtester` was previously staged as a gitlink:

```bash
git rm --cached backtester
rm -rf backtester/.git
git add backtester/
```

## Alternatives considered

- **Git submodule** — rejected. Adds clone friction (`git submodule update`)
  and splits review across two repos while `crypt_ensemble` already depends on
  tight coupling with `src/crypt/`.
- **Keep nested repo** — rejected by owner. Commits and CI visibility stay
  fragmented; embedded-repo warnings persist.
- **Delete `backtester/` and copy only needed modules into `src/crypt/`** —
  rejected for now. Would break the donor CLI/optimizer workflow and duplicate
  migration effort already spent on in-tree `backtester/`.

## Consequences

### Positive

- One commit, one PR, and one clone deliver ensemble + donor backtester code.
- Agents and operators no longer need to discover which repository to commit.
- Aligns documentation with how the project is actually developed.

### Negative

- Upstream `AuriumX/backtester` is no longer the automatic sync target; cherry-
  picks from that repo are manual if still needed.
- Root CI (`.github/workflows/ci.yml`) still runs only `crypt` tests; donor
  pytest remains a separate command under `backtester/` until a follow-up wires
  it into CI.
- `backtester/uv.lock` is now versioned in `crypt`; lock drift must be managed
  like any other dependency file.

## Follow-up

- Owner completes the one-time `rm -rf backtester/.git` + root `git add`.
- Optional P2: add donor `pytest`/`ruff` to root CI (see `docs/tasks/BACKLOG.md`).

## References

- ADR-0018: Donor backtester becomes the canonical M2 backtest architecture
- `docs/backtester_migration.md`
- `docs/backtest.md` §18
- `https://github.com/AuriumX/backtester` (historical upstream)
