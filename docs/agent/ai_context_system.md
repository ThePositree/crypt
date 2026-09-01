# AI Context System

The repository keeps agent accuracy by leaving hard rules and current state in
plain text, while reducing routine token load through deterministic routing and
route-specific full-document selection.

## Goals

- Agents load the routed subset of large markdown files needed for the current
  task.
- Hard rules must remain exact, searchable, and readable as text.
- Routing must be deterministic enough that future agents can reproduce why a
  doc was loaded.
- Retrieval systems may help discovery; canonical docs remain the source for
  rules, live money truth, and backtester checkpoints.

## Layers

1. `AGENTS.md`: short bootstrap plus non-negotiable hard rules.
2. `docs/state/current.yml`: compact current project, production, and
   checkpoint snapshot.
3. `docs/agent/context_routes.yml`: maps task keywords to full docs.
4. Full markdown docs: source truth for detailed behavior, commands, evidence,
   and runbooks.
5. Archives and experiments: old changelog, old ADRs, old reconciliation docs,
   optional vector indexes, and optional text-as-image packs.

The helper CLI is `scripts/agent_context.py`:

```bash
python scripts/agent_context.py validate
python scripts/agent_context.py route "phase-c backtester replay drift"
python scripts/agent_context.py budget --route backtester_regression
python scripts/agent_context.py benchmark
python scripts/agent_context.py image-pack \
  --source CHANGELOG_ARCHIVE.md \
  --output results/agent_context/image_pack/changelog_archive
```

## Accuracy Rules

- Keep hard rules in canonical markdown in addition to embeddings, images, or
  generated summaries.
- Treat full source docs, runtime config, OKX state, and exact command output as
  final authority when money, production, or regression verdicts depend on exact
  commands or numbers. Use route-selected full docs as entry points.
- Use YAML routing before semantic/vector retrieval.
- Use `rg` on canonical text when a task needs exact names, paths, commits, or
  dollar values.
- If docs and runtime config disagree, stop and ask the owner.

## Knowledge Base Expansion Rules

Use the smallest durable place that preserves accuracy:

- Hard rule: put the short mandatory rule in `AGENTS.md`; put detailed policy
  in `docs/agent/operating_rules.md` when needed.
- Current runtime/production/checkpoint fact: update `docs/state/current.yml`.
- Large runbook, spec, report, or audit: write the full markdown doc and add it
  to deterministic routing when it is likely to be routed into future sessions.
- New knowledge area: add or update a route in `docs/agent/context_routes.yml`
  with `match` and `full_docs`.
- Live-money or backtester-critical knowledge: add at least one question to
  `docs/agent/context_benchmark.yml` and keep the markdown benchmark aligned.
- Completed historical work: write `CHANGELOG.md`; archive older history in
  `CHANGELOG_ARCHIVE.md` or `docs/archive/`.
- Reference-only old material: vector/image retrieval may index it later, but
  the canonical source remains markdown.

Keep knowledge expansion complete and compact:

- Large docs that future agents need have a route.
- Routes point directly to canonical full docs.
- Active production truth lives in current canonical state and runtime sources.

After expanding the knowledge base, run:

```bash
UV_CACHE_DIR=/tmp/uv-cache uv run python scripts/agent_context.py validate
UV_CACHE_DIR=/tmp/uv-cache uv run python scripts/agent_context.py benchmark
```

## Vector Retrieval

Vector DB is a later-stage discovery tool for archive/reference material:

- old ADRs;
- old reconciliation reports;
- old changelog archive;
- candidate/router archive READMEs.

Vector results point back to canonical text paths. Rules and checkpoints live in
canonical markdown.

## Text-As-Image Experiment

Text-as-image experiments apply to archival/reference material where exact
instruction compliance is handled by canonical markdown:

- `CHANGELOG_ARCHIVE.md`;
- superseded ADRs;
- old reconciliation reports;
- old candidate/router archive notes.

Keep these sources as readable canonical text:

- `AGENTS.md`;
- `docs/state/current.yml`;
- `docs/agent/context_routes.yml`;
- `docs/backtester_regression.md`;
- live execution runbooks used for money decisions;
- active task files.

## Benchmark

Use `docs/agent/context_benchmark.md` and
`docs/agent/context_benchmark.yml` before adopting vector or image retrieval as
a default workflow. Compare:

- plain markdown with deterministic routing;
- routed markdown plus `rg`;
- vector retrieval pointing to markdown;
- image-pack retrieval for archives only.

Pass criteria:

- answers include the correct file path and source type;
- no hard rule is missed;
- no stale archive fact overrides current state;
- phase A/B/C checkpoints are reproduced exactly;
- live-money questions identify OKX/runtime config as source truth;
- token use is lower than loading the full doc set.

`python scripts/agent_context.py benchmark` is the deterministic baseline. A
future vector DB or image-pack retriever must beat or match this source-hit and
required-term score before becoming a default workflow. Current baseline
results live in `docs/agent/context_benchmark_results.md`.
