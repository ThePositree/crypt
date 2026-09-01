# Live Execution Safety Learning Flow

- Actor and starting state: reader has completed dry-run and wants to understand
  detailed production execution without controlling it from the portal.
- Message transition: `dry-run worked` -> `I understand every additional live
  prerequisite, mutation, truth source, and recovery path`.

```text
Quick Start dry-run completion
  -> Live Execution overview
  -> Compare monitoring, dry-run, and live modes
  -> Inspect H1 scheduling and strategy decision path
  -> Inspect credentials and execution settings
  -> Inspect OKX sync and entry-block conditions
  -> Inspect order/fill/state/risk-base lifecycle
  -> Inspect Railway deployment and persistent storage
  -> Inspect monitoring, recovery, and export
  -> optional external action: follow repository command outside the portal
```

- Trust boundaries: runtime env/config governs active strategy; OKX governs
  fills, orders, fees, positions, and account equity; the portal is explanatory.
- Error/recovery: every unsafe or unavailable condition is paired with blocked
  behavior, operator evidence, safe recovery, and verification.
- Endpoint: the reader can describe what changes between dry-run and live and
  where to verify exchange truth before acting externally.
