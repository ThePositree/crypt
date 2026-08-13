# AI Context System Card

Full source: `docs/agent/ai_context_system.md`

Use this card when changing agent docs, context routing, changelog/archive
policy, vector retrieval, or text-as-image experiments.

Key rules:

- Keep hard rules and current state as plain text.
- Use `docs/agent/context_routes.yml` before broad doc reading.
- When adding durable knowledge, update routes/cards/current state/benchmark as
  applicable.
- Use `.card.md` files as entry points, not final authority for money or
  regression details.
- Vector DB is discovery-only until proven by a benchmark.
- Text-as-image is archive-only and must not hold mandatory instructions.
- Exact facts still come from canonical markdown, runtime config, OKX, or `rg`.

Implemented layers:

- `AGENTS.md`: compact bootstrap and hard rules.
- `docs/state/current.yml`: compact project/live/checkpoint state.
- `docs/agent/context_routes.yml`: deterministic routing manifest.
- `docs/agent/context_benchmark.yml`: machine-readable 20-question benchmark.
- `.card.md`: summaries for high-token docs.
- Full docs: canonical source truth.
- `scripts/agent_context.py`: validate, route, budget, benchmark, and
  archive-only image-pack helper.

Expansion rule:

- Hard rules -> `AGENTS.md` plus optional `docs/agent/operating_rules.md`.
- Current production facts -> `docs/state/current.yml`.
- Large docs -> full markdown plus `.card.md`.
- New areas -> `docs/agent/context_routes.yml`.
- Critical live/backtester knowledge -> benchmark question.

Benchmark requirement:

- Use `docs/agent/context_benchmark.md` and
  `docs/agent/context_benchmark.yml` before adopting vector or image retrieval
  as a default workflow.
- Compare against the current deterministic baseline in
  `docs/agent/context_benchmark_results.md`.
- Compare accuracy and token use across md routing, cards+rg, vector retrieval,
  and archive-only image packs.
- Deterministic routing must score 100% on source and required-term hits before
  a vector/image retriever can be compared against it.
