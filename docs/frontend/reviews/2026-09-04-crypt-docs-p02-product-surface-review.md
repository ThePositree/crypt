# Crypt Docs Portal P02 Product Surface Contract Review

- Artifact path: `docs/frontend/reviews/2026-09-04-crypt-docs-p02-product-surface-review.md`
- Review type: Independent Contract Review (D3 Phase P02 Product Surface Model & Source Map)
- Revision: 1
- Date: 2026-09-04
- Reviewer context: Dispatched Orca independent reviewer (`task_9c7fffbeb164`, terminal `term_bfd0f0f6-37fe-4588-ae8b-6a7ea6bb1650`)
- Authoring context reviewed: D3 frontend phase main (`term_b095c115-2e3c-45ce-bc58-3ab5a82b338b`)
- Reviewed artifacts:
  - `docs/frontend/product-surface-model.md` (Revision 1)
  - `docs/frontend/decisions/2026-09-04-crypt-docs-source-map-p02.md` (Revision 1)
  - `docs/frontend/decisions/2026-09-04-crypt-docs-portal-p01.md` (Revision 1)
  - Context & rules: `AGENTS.md`, `docs/agent/context_routes.yml`, `docs/state/current.yml`, `docs/agent/frontend_design_subsystem.md`
- Independence confirmation: Read-only independent reviewer context; did not author or modify product-surface, source-map, handoff, task, changelog, or frontend implementation files.
- Controlling gate: Product Surface Approval (owner decision pending).

---

## 1. Executive Summary & Verdict

- **Verdict:** **PASS** (with 2 nonblocking advisory notes).
- **Blocking findings count:** 0
- **Nonblocking findings count:** 2
- **Approval readiness:** **READY FOR PRODUCT SURFACE APPROVAL**. The Product Surface Model (`docs/frontend/product-surface-model.md` Rev 1) and Factual Product Research artifact (`docs/frontend/decisions/2026-09-04-crypt-docs-source-map-p02.md` Rev 1) fully satisfy the D3 P02 contractual requirements, align 100% with the 30 owner onboarding answers, establish strict boundaries against live money state exposure, and demonstrate verified factual grounding across all 10 core sections and 38 mapped pages.

---

## 2. Review Methodology & Verification Performed

1. **Path Existence Audit:** Verified 65+ repository paths (source code in `src/crypt/` and `src/backtester/`, documentation under `docs/`, ADR records under `docs/decisions/`, strategy JSONs, configuration templates, and runtime scripts) using automated filesystem checks.
2. **Owner Answers Alignment:** Cross-checked all 30 owner onboarding answers from `docs/frontend/decisions/2026-09-04-crypt-docs-portal-p01.md` against every specification in the Product Surface Model and Source Map.
3. **Route & Page Model Audit:** Evaluated the 10-section, 38-page information architecture for completeness, logical flow, developer and quant-trader learning tracks, and absence of capability gaps.
4. **Safety & Invariant Inspection:** Checked the strict exclusion of live execution balances, positions, real-time trading triggers, CMS dependencies, and look-ahead bias violations.
5. **Factual Grounding & Parity Audit:** Inspected parity contracts, ADR references (ADR-0010 through ADR-0062), execution architecture components, and backtester regression checkpoints to ensure accurate representation of repository reality.

---

## 3. Detailed Criteria Evaluation

### 3.1 D3 P02 Compliance & Process Hygiene
- **Product Surface Model (`docs/frontend/product-surface-model.md`):** Updated to Revision 1; defines canonical product source links, frontend-specific delta, audience jobs, 10 core sections, 38 key pages, 4 user journeys, 11 interactive affordances/states, 4 risk callouts, 4 maturity statuses, and explicit approval records.
- **Factual Research Artifact (`docs/frontend/decisions/2026-09-04-crypt-docs-source-map-p02.md`):** Comprehensive factual mapping per section, detailing audience jobs, canonical source paths, key technical topics, risk markers, and maturity tiers.
- **Independence & Gate Sequence:** Authored by D3 phase main; independently audited here by read-only reviewer prior to owner Product Surface Approval. Satisfies D3 phase separation obligations.

### 3.2 Alignment with Owner Onboarding Answers
All 30 onboarding answers from `docs/frontend/decisions/2026-09-04-crypt-docs-portal-p01.md` are strictly observed:
- **Questions 1–3 (Product & Framing):** Portal documents the repository as a crypto-trading framework for developer-crypto-traders; first screen explains concepts without displaying runtime execution results. (Aligned)
- **Question 4 (Stack):** Next.js + Tailwind CSS. (Aligned)
- **Question 5 (Coordination):** Independent Orca subagent coordination used for review and QA phases. (Aligned)
- **Question 6 (Language):** Russian UI and documentation copy with standard technical English identifiers. (Aligned)
- **Questions 7–9 (Audience & Navigation):** Developer-crypto-traders; dual navigation (architecture-first left sidebar + guided learning tracks); framework-style reference docs without raw Python source dumping. (Aligned)
- **Questions 10, 14, 24 (Search):** Full-content search engine with header search input and `Cmd/Ctrl+K` command palette. (Aligned)
- **Questions 11, 16 (Content & Landing):** Tutorial and reference tracks; landing combines framework topology and guided start. (Aligned)
- **Question 12 (Required Sections):** All 10 required sections present: Overview, Architecture, Backtester, Strategies, Live Execution, Data Pipeline, CLI, Configuration, Operations, Glossary. (Aligned)
- **Questions 13, 17, 18 (Interactivity & CLI):** Expandable diagrams, tabs, filters, copyable CLI snippets with feedback. (Aligned)
- **Question 19 (Live Execution):** Architectural and operational guarantees only; strict non-goal excludes live balances and open positions. (Aligned)
- **Questions 20, 21 (Theme & Name):** `crypt docs`; dark theme default with light theme toggle. (Aligned)
- **Questions 22, 23, 28 (Page Chrome):** Breadcrumbs, left sidebar, sticky desktop on-page TOC, and "What to read next" blocks on every page. (Aligned)
- **Questions 25, 26 (Mascots):** Playful lo-fi visual language with abstract geometric mascots (decision logic, risk shield, candle observer). (Aligned)
- **Question 27 (Risk Markers):** Prominent risk badges for Live Money, OKX Execution, Configuration Safety, and No Look-Ahead Bias. (Aligned)
- **Question 29 (Maturity Statuses):** `stable`, `research`, `operational`, `archived`. (Aligned)
- **Question 30 (Content Depth):** First release delivers a fully curated 38-page portal, not a skeleton. (Aligned)

### 3.3 Route & Page Model Completeness
The 10 sections encompass 38 distinct routes with no orphaned pages or architectural blind spots:
1. `/docs/overview/`: `manifesto`, `quickstart`, `learning-routes`, `boundaries` (4 pages).
2. `/docs/architecture/`: `system-overview`, `decision-pipeline`, `module-map`, `adrs` (4 pages).
3. `/docs/backtester/`: `engine`, `regression`, `optimization`, `metrics` (4 pages).
4. `/docs/strategies/`: `anatomy`, `dss-v3`, `portfolios`, `regimes`, `lifecycle` (5 pages).
5. `/docs/execution/`: `architecture`, `okx-client`, `reconciliation`, `risk-base`, `notifications` (5 pages).
6. `/docs/data-pipeline/`: `ingestion`, `models`, `storage`, `timeframes` (4 pages).
7. `/docs/cli/`: `overview`, `backtester`, `discovery`, `live-and-backfill` (4 pages).
8. `/docs/configuration/`: `env-vars`, `strategy-json`, `risk-params`, `safety-guards` (4 pages).
9. `/docs/operations/`: `railway`, `monitoring`, `runbook`, `reconciliation-audits` (4 pages).
10. `/docs/glossary/`: `trading`, `architecture`, `strategies` (3 pages).
- Plus root landing page `/docs` (or `/docs/overview/manifesto`).

### 3.4 Live State Isolation & Secrets Safety
- The Product Surface Model enforces strict non-goals forbidding live balance queries, position displays, or trading action triggers.
- The Secrets Boundary mandates placeholder credentials (`your_okx_key_here`, `your_telegram_bot_token`) in all examples.
- Content is statically source-authored and built via SSG; no backend runtime or live exchange proxying is introduced.

### 3.5 Source-to-Section Accuracy & Factual Grounding
- **Pure Decision Parity:** Accurately reflects shared decision logic between `src/backtester` and `src/crypt/execution`.
- **Closed Candle Invariant:** Correctly emphasizes `candle.is_closed == True` across ingestion, feature generation, and signal execution.
- **Live Reconciliation & Parity:** Faithfully represents Phase A/B/C regression checkpoints from `docs/backtester_regression.md` and the 2026-07 reconciliation audit in `docs/execution/live_backtest_reconciliation_2026-07-28.md`.
- **Active Strategy Truth:** References current production v6 SOL portfolio (`strategies/archive/filtered_donor_portfolio_post_adr0058_tail_control_v6_drop_negative_v5.json`) and monthly risk base continuity (ADR-0059).

---

## 4. Path Verification Audit

Every canonical source path cited in the Product Surface Model and Source Map was checked against the workspace:

| Path Category | Referenced Path | Verification Result |
|---|---|---|
| **Root & Setup** | `README.md`, `AGENTS.md`, `pyproject.toml`, `.env.example`, `railway.toml`, `scripts/railway_live_start.sh`, `deploy/crypt.service` | Verified (All exist) |
| **Canonical Docs** | `docs/state/current.yml`, `docs/agent/context_routes.yml`, `docs/agent/operating_rules.md`, `docs/agent/frontend_design_subsystem.md`, `docs/architecture.md`, `docs/strategy_benchmark.md`, `docs/backtester_regression.md`, `docs/cli.md`, `docs/operator.md`, `docs/backfill.md`, `docs/regime_detection.md`, `docs/operations/observability.md`, `docs/deploy/railway.md`, `docs/discovery/direct_signal_search_v3.md`, `docs/execution/live_execution.md`, `docs/execution/live_backtest_reconciliation_2026-07-28.md`, `docs/execution/telegram_notifications.md`, `docs/execution/h1_websocket_trigger.md`, `docs/backtester/candidate_archive.md`, `docs/archive/candidates/README.md` | Verified (All exist) |
| **ADR Records** | `docs/decisions/0010-railway-deployment.md`, `docs/decisions/0031-mandate-aware-optuna-target.md`, `docs/decisions/0033-m4-live-execution-architecture.md`, `docs/decisions/0057-distinguish-below-start-and-peak-drawdown.md`, `docs/decisions/0058-okx-aggregate-average-entry-accounting.md`, `docs/decisions/0059-durable-monthly-risk-base-checkpoints.md`, `docs/decisions/0062-dss-v3-persistent-multi-timeframe-search.md` | Verified (All exist) |
| **Runtime Source (`src/crypt/`)** | `src/crypt/__init__.py`, `src/crypt/__main__.py`, `src/crypt/config.py`, `src/crypt/models.py`, `src/crypt/data/context.py`, `src/crypt/data/store.py`, `src/crypt/data/ingestor.py`, `src/crypt/backfill/__main__.py`, `src/crypt/runtime/health.py`, `src/crypt/runtime/logging.py`, `src/crypt/runtime/h1_websocket.py`, `src/crypt/execution/executor.py`, `src/crypt/execution/okx_order_client.py`, `src/crypt/execution/exchange_sync.py`, `src/crypt/execution/risk_base_continuity.py`, `src/crypt/execution/position_state.py`, `src/crypt/execution/risk_calculator.py`, `src/crypt/execution/trade_replay.py`, `src/crypt/execution/settings.py`, `src/crypt/execution/notifications.py`, `src/crypt/sinks/telegram.py`, `src/crypt/structure/smc.py` | Verified (All exist) |
| **Backtester Source (`src/backtester/`)** | `src/backtester/cli_runner.py`, `src/backtester/execution_sim.py`, `src/backtester/optimizer.py`, `src/backtester/fee_model.py`, `src/backtester/exit_geometry.py`, `src/backtester/mandate_report.py`, `src/backtester/margin_policy.py`, `src/backtester/data_contracts.py`, `src/backtester/data_loader.py`, `src/backtester/strategy.py`, `src/backtester/registry.py`, `src/backtester/regime_router.py`, `src/backtester/indicators/market_phase.py`, `src/backtester/strategies/filtered_donor_portfolio.py`, `src/backtester/strategy_discovery/search.py`, `src/backtester/strategy_discovery/dss_config.py` | Verified (All exist) |
| **Strategy & Data Artifacts** | `strategies/archive/filtered_donor_portfolio_post_adr0058_tail_control_v6_drop_negative_v5.json`, `data/live_positions.json`, `data/SOL-USDT-SWAP/*.parquet`, `results/` | Verified (All exist) |

---

## 5. Findings Ordered by Severity

### 5.1 Blocking Findings (0)
*None.* No nonexistent canonical source path remains, and no owner-answer mismatch was identified.

### 5.2 Nonblocking Notes & Advisory Recommendations (2)

#### Finding NB-01: Wildcard ADR path pattern in Section 4 source citations
- **Location:** `docs/frontend/decisions/2026-09-04-crypt-docs-source-map-p02.md`, line 125.
- **Reference:** `docs/decisions/0058-*.md`
- **Observation:** The source list uses a wildcard pattern `0058-*.md` rather than the exact filename `docs/decisions/0058-okx-aggregate-average-entry-accounting.md`. While this glob pattern uniquely resolves to that single ADR in `docs/decisions/`, contract documents should specify literal, exact file paths to ensure automated linters and link checkers resolve cleanly without globbing logic.
- **Required Action / Recommendation:** During P03 content authoring, replace `docs/decisions/0058-*.md` with the explicit canonical path `docs/decisions/0058-okx-aggregate-average-entry-accounting.md`.

#### Finding NB-02: Runtime-generated checkpoint directory disambiguation
- **Location:** `docs/frontend/product-surface-model.md`, line 192; `docs/frontend/decisions/2026-09-04-crypt-docs-source-map-p02.md`, lines 163 and 261.
- **Reference:** `data/risk_base_checkpoints/`
- **Observation:** In the Source-of-Truth mapping table, `data/risk_base_checkpoints/` is listed under "Конфигурация / Артефакты". While `data/live_positions.json` exists in the local workspace, the directory `data/risk_base_checkpoints/` is created on demand by the live executor runtime in production (Railway volume mount) and in unit tests; it does not exist as an initialized directory in the git repository.
- **Required Action / Recommendation:** In the documentation portal copy (specifically `/docs/execution/risk-base` and `/docs/operations/railway`), clearly explain that `data/risk_base_checkpoints/` is a runtime-generated directory managed by `MonthlyRiskBaseContinuity` (ADR-0059) and configured via `EXECUTION_RISK_BASE_CHECKPOINT_DIR`, rather than a static repository directory.

---

## 6. Approval Readiness & Next Phase Recommendation

The P02 deliverables meet all quality, structural, and factual criteria required by the frontend design subsystem (`docs/agent/frontend_design_subsystem.md`).

- **Gate Status:** Ready for owner decision on **Product Surface Approval**.
- **Recommended Action:** Present `docs/frontend/product-surface-model.md` (Revision 1) to the owner for formal approval.
- **Next Phase Unlocked:** P03 (Messaging Identity, Source-Grounded Content Authoring, Text Inventory, Independent Copy Review).
