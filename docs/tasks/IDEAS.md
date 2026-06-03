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

**Status:** idea only; not approved for implementation.

**Owner signal:** idea for later, not now.

**Idea:**

In backtest and calibration reports, if a strategy earns more than some
configured monthly profit cap (`N%`) in a month, the main calibration/evaluation
metric should treat that month as if it earned a normal capped profit instead
of the full oversized profit.

The raw oversized profit must still be preserved and shown somewhere in the
report, but the strategy should not be judged as robust only because one month
had unusually large profit.

**Motivation:**

- Avoid relying on one exceptional month as if it were repeatable.
- Make candidate comparison more conservative.
- Preserve the raw upside information separately so it can still be inspected.

**Possible future shape:**

- Add a report-only or calibration-only metric such as
  `capped_monthly_return_pct`.
- Keep raw `monthly_returns_pct` unchanged.
- Add report fields for:
  - raw monthly return;
  - capped monthly return;
  - cap threshold;
  - excess return excluded from capped evaluation.
- Use the capped metric for candidate ranking only after the owner approves
  the policy and threshold.

**Open questions before implementation:**

- What should the monthly cap `N%` be?
- Should the cap apply per symbol, per portfolio, or both?
- Should negative outlier months also be clipped, or only positive outliers?
- Should this affect only reports, Optuna targets, or both?
