# Ideas

Owner-provided ideas to remember for later.

This file is intentionally separate from `BACKLOG.md`. Items here are not
approved work. Agents must not implement an idea from this file unless the
owner explicitly approves it in chat.

When an idea becomes relevant to the current work, remind the owner briefly,
explain why it may fit now or why it should wait, and ask for explicit approval
before moving it into `BACKLOG.md`, a spec, or code.

---

## 2026-06-03 — Cap outsized monthly backtest profits for calibration

**Status:** **approved** — moved to `docs/investment_mandate.md` §4 and
ADR-0025 (2026-06-05).

**Policy:** `capped_monthly_return_pct = min(raw, 20%)` for ranking; pass/fail
uses raw `≥ 15%`. Implementation tracked in `BACKLOG.md`.

---
