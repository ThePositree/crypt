# Agent Operating Rules Card

Full source: `docs/agent/operating_rules.md`

Use this card when a task touches agent policy, long commands, dependencies,
task hygiene, specs, ADRs, or incident response.

Hard reminders:

- Owner production override is allowed; record risks once and continue.
- Benchmark is a reporting target, not a live-production veto.
- Use Context7 before non-trivial external library/API work.
- Set `UV_CACHE_DIR=/tmp/uv-cache` for agent-run `uv` commands.
- Stop silent long jobs; hand owner the command when ETA is above 3 minutes or
  progress is invisible.
- Keep `IN_PROGRESS.md` active-only and `BACKLOG.md` unfinished-only.
- Specs must move with new engines, sinks, execution components, or
  non-trivial modules.
- ADRs are append-only and needed for future-questioned trade-offs.
- Missing data must fail fast, block entries, or degrade explicitly.
