# Agent Context Benchmark

Use this benchmark before replacing deterministic markdown routing with vector
retrieval or text-as-image packs. The benchmark compares accuracy and token use
across four modes:

- routed markdown: `AGENTS.md`, `docs/state/current.yml`, route cards, then
  exact full docs only as needed;
- cards plus `rg`: route cards first, exact `rg` for names/paths/numbers;
- vector retrieval: semantic discovery that points back to canonical markdown;
- image-pack retrieval: archive-only screenshots or rendered text images.

Machine-readable expected sources and required terms live in
`docs/agent/context_benchmark.yml`.

Run the deterministic baseline:

```bash
python scripts/agent_context.py benchmark
```

Any future vector or image-pack retrieval workflow must match or beat the
deterministic baseline on source hits and required-term hits before becoming a
default agent workflow.

Pass criteria:

- The answer identifies the correct canonical source path.
- Current state beats archive history when they disagree.
- Runtime config and OKX are treated as live-money truth.
- Phase checkpoints are reproduced exactly.
- No hard rule exists only in vector/image form.
- Token use is lower than loading all root/docs markdown eagerly.

## Questions

1. Which file should an agent read first after `AGENTS.md` to route context?
2. What is the current source of truth for the live strategy config?
3. Which exchange source is authoritative for live fills, fees, and account
   equity?
4. What benchmark doc defines the `$10,000` strategy comparison target?
5. Is the benchmark a hard gate that blocks owner-promoted production
   strategies?
6. Which runbook should be used when the owner asks whether the backtester is
   broken?
7. What are the phase-C `--load-from`, `--from`, and `--to` timestamps?
8. What phase-C starting capital should a replay use?
9. Which deployed commit starts the phase-C live behavior boundary?
10. Is commit `2704c83` deployed to Railway production, and does it affect the
    money path?
11. What exact symptom makes phase C fail around the `2026-08-03T17:00:00Z`
    signal?
12. Where should completed historical work go instead of
    `docs/tasks/IN_PROGRESS.md`?
13. What must an active/backlog task entry include?
14. When should an agent write a new ADR?
15. What should happen when required candle data is missing before expensive
    backtest or live order work?
16. What environment variable should agent-run `uv` commands use for cache
    writes?
17. What should an agent do with a long command whose ETA is above three
    minutes?
18. Which docs are allowed candidates for a text-as-image experiment?
19. Which docs must never be available only as vector/image retrieval?
20. What should the agent do if a card disagrees with its full source doc?
