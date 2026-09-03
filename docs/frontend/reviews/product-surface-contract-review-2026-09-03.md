# Product Surface Model Contract Review: crypt docs (Revision 1)

- **Review Type**: Independent Product Surface Model Contract Review / Frontend Lead Contract Review (O22)
- **Artifact Reviewed**: `docs/frontend/product-surface-model.md` (Revision 1, 2026-09-03)
- **Reviewer Context**: Independent Frontend Lead Contract Reviewer (`task_da7dc5b490a7`, dispatch `ctx_9e5ccc970aaf`, terminal `term_668cc1a5-f3f0-4d62-8ef9-b5912e10075b`)
- **Author Context**: Product Surface Author (`task_fba2e2cb878b`, dispatch `ctx_e25333e8f4b0`, terminal `term_07a19ef4-dd73-45bb-a04b-3ceb3091d9d0`)
- **Independence Status**: Confirmed independent review context.
- **Owner Approvals / Waivers**: None recorded; full standard review applied without waivers.
- **Review Date**: 2026-09-03
- **Verdict**: **pass-with-fixes**
- **Blocking Findings Count**: 1
- **Non-Blocking Findings Count**: 3
- **Product Surface Approval Readiness**: Can be presented to the owner once the 1 blocking finding and 2 recommended contract fixes are addressed in Revision 2.

---

## 1. Executive Summary

`docs/frontend/product-surface-model.md` Revision 1 provides a thorough, disciplined, and faithful specification for the new `crypt docs` documentation portal. It establishes clear boundaries between the documentation site and the underlying Python quantitative workbench/live execution engine, strictly adhering to the findings in `docs/frontend/reviews/product-research-crypt-docs-2026-09-03.md`, `docs/state/current.yml`, and `AGENTS.md`.

All 10 required sections, the dual-route navigation model (Architecture Route vs Learning Route), the playful lo-fi pastel aesthetic with abstract mascots, full-text search (Cmd+K), and negative boundaries (no live account balances/metrics and no raw source code quotations) are comprehensively articulated.

A single blocking factual contradiction was identified: line 128 attributes `Polars` to the system's data processing stack, whereas the repository and research artifact confirm that only `pandas` and `pyarrow` are utilized. Additionally, three non-blocking contract improvements were identified: the omission of a dedicated 404 / Not Found screen in the page inventory, lack of explicit output suppression rules in the code snippet component state specification, and absence of an open decision regarding diagram implementation technology.

With these targeted fixes applied, the artifact will fully qualify for the Owner Product Surface Approval (O05 Gate).

---

## 2. Review Criteria Evaluation

### 2.1 Explicit Product Definition for Frontend Lead
- **Product Name & Framing**: Explicitly defined as `crypt docs` (lines 7, 47–50) with an official framework documentation aesthetic.
- **Target Audience & Persona**: Explicitly targeted at `developer-crypto-trader` (lines 53–61) balancing quant literacy and software engineering rigor.
- **Jobs to Be Done (JTBD)**: Comprehensive primary JTBD (lines 63–65) and 7 actionable secondary jobs (lines 66–73).
- **In-Scope & Out-of-Scope**: Clearly partitioned with strict prohibitions (lines 74–120).
- **Pages and Screens**: Exhaustive inventory of 34 distinct documentation pages across 10 sections plus modal search palette (lines 122–165). (Minor gap: 404 page missing; see Finding 2).
- **User Journeys**: 4 concrete, actionable, end-to-end user journeys defined (lines 168–210).
- **System & Component States**: Explicit definitions for visual themes, sidebar nav, on-page TOC scrollspy, search palette, interactive components, and callout tiers (lines 212–260).
- **Criterion Status**: **PASS (with minor enhancement)**

### 2.2 Reflection of Owner Requirements
- **Russian Language**: Exclusively Russian copy, navigation, labels, and explanations, while preserving English for technical identifiers and CLI syntax (lines 50–51, 75).
- **Next.js + Tailwind CSS**: Explicitly established in metadata and technical choices (lines 9, 298).
- **Full-Content Search**: Detailed Cmd+K command palette modal indexing headers, content paragraphs, and glossary terms (lines 95, 232–239, 302–306).
- **Dual Routes (Tutorial + Reference)**: Explicitly split into Learning Route (`/learning/*`) and Architecture/Reference Route (`/architecture/*`, `/backtester/*`, etc.) (lines 89–91, 129–135).
- **Required 10 Sections**: All 10 sections completely enumerated and described (lines 77–88).
- **Diagrams**: Interactive and static data/decision flow diagrams mandated across key architecture and execution pages (lines 96, 127, 181).
- **Snippets Without Output**: Noted in owner onboarding source summary (line 315). (Component spec enforcement needed; see Finding 3).
- **Dark Theme**: Explicit Light, Dark, and System preference theme states with defined token palettes (lines 51, 100, 214–219, 307–309).
- **Breadcrumbs, Side Nav, On-Page TOC, Read-Next Blocks**: Fully integrated across navigation states and page specs (lines 93–94, 221–228).
- **Playful Lo-Fi Mascot Style**: Defined pastel palette (`#E8E5F6`, `#E3F5E9`, `#FCECE9`, `#FAF9F5`, `#1E2024`) and abstract mascot illustrations for guides and empty states (lines 51, 238, 307–309).
- **Risk Callouts**: 4 tiered callout specifications (`Критический риск`, `Строгий инвариант`, `Важное примечание`, `Устаревший компонент`) (lines 99, 254–260).
- **Maturity Statuses**: Explicit badges (`stable`, `research`, `operational`, `archived`) assigned to every route (lines 98, 127–164).
- **No CMS**: 100% file-backed architecture using MDX/TypeScript in git, strictly banning external CMS and database layers (lines 52, 108–109).
- **Criterion Status**: **PASS**

### 2.3 Source-of-Truth and Risk Boundaries
- **Live Metrics / Balance Prohibition**: Explicitly bans displaying live exchange accounts, balances, positions, open orders, real-time PnL, or equity curves (lines 103–105, 280–282).
- **Mandatory Disclaimer Copy**: Mandates explicit Russian disclaimer on all live execution pages: *"Этот раздел описывает архитектурные гарантии и алгоритмы исполнения. Портал документации не отображает текущие позиции, балансы или результаты реального счета."* (lines 281–282).
- **Code Quotation Prohibition**: Strictly prohibits quoting raw Python repository source code, enforcing framework-level explanatory prose, diagrams, tables, and CLI snippets (lines 106–107).
- **No Look-Ahead Invariant**: Emphasizes strict closed-candle persistence and evaluation (`closed=True`), and defines the forming candle open strictly as the `next_open` reference price (lines 25, 283–286).
- **Operational Reality Disclosures**: Discloses that active production portfolio v6 failed Phase C benchmark targets (-13% vs +15%) and operates via owner override; documents fill drift (`Цена входа отличается от плана`) and WebSocket fallback mechanisms (lines 26, 82, 118–119, 288–290).
- **Criterion Status**: **PASS**

### 2.4 Alignment with Factual Research, current.yml, and AGENTS.md
- **Repository Framing**: Matches research workbench + live OKX execution (lines 4–5, 48–49).
- **Subsystem Separation**: Accurately reflects `src/backtester/` vs `src/crypt/` (lines 78–87).
- **Retired Subsystems**: Accurately documents retirement of `src/crypt/backtest/` (ADR-0023) and removal of Coinglass (ADR-0016) (lines 26, 38, 79, 84).
- **Unbuilt Capabilities**: Correctly identifies proposed Telegram commands (`/status`, `/trade`) and microsecond JSONL telemetry as unbuilt proposals (lines 27, 41–43, 114–116, 292–294).
- **Production Truth**: Matches active strategy `strategies/archive/filtered_donor_portfolio_post_adr0058_tail_control_v6_drop_negative_v5.json` on `SOL-USDT-SWAP` (lines 22–23, 81).
- **Technical Discrepancy**: Mentions `Polars` in line 128, which contradicts `pyproject.toml` and research lines 79–80 (Finding 1).
- **Criterion Status**: **PASS-WITH-FIXES** (conditioned on resolving Finding 1)

### 2.5 Implementation-Relevant Decisions & Assumptions
- **Open Decisions Explicitly Formulated**:
  - Decision 1: Next.js Content Structure (App Router with `@next/mdx` vs Content Collections / Velite) (lines 298–301).
  - Decision 2: Client-side Full-Text Search Engine (Minisearch/FlexSearch manifests vs Pagefind) (lines 302–306).
  - Decision 3: Playful Lo-Fi Pastel Visual Design Tokens and Mascot Illustrations (lines 307–309).
- **Gaps Identified**:
  - Diagram implementation technology is unspecified (Finding 4).
- **Criterion Status**: **PASS**

---

## 3. Findings Ordered by Severity

### Finding 1: Factual Discrepancy in Technology Stack Specification (`Polars`)
- **Severity**: **High (Blocking Fix)**
- **File & Line**: `docs/frontend/product-surface-model.md:128`
- **Reproduction / Evidence**:
  Line 128 states:
  ```markdown
  | `/overview` | `Обзор платформы` | Overview | Quantitative workbench + OKX execution framing, historical MVP context (retired H4 ensemble), design principles, tech stack (`uv`, Python 3.12, OKX, Polars/Pandas, Optuna). | `stable` |
  ```
  Inspection of `pyproject.toml` (lines 16–20) and `docs/frontend/reviews/product-research-crypt-docs-2026-09-03.md` (lines 79–80) confirms:
  ```markdown
  - Data Processing: `pandas` (v2.2+), `pyarrow` (v17+), `pydantic` (v2.7+), `pydantic-settings` (pyproject.toml, lines 16–20).
  ```
  `polars` is not an installed dependency or part of the `crypt` runtime/backtest architecture.
- **Impact**: Frontend content authors writing the `/overview` page will document Polars as part of the framework's core data engine, introducing false technical claims into the public documentation.
- **Required Fix**: Update line 128 to replace `Polars/Pandas` with `Pandas, PyArrow`.

---

### Finding 2: Missing 404 / Not Found Error Page in Screen Inventory
- **Severity**: **Medium (Non-blocking Contract Gap)**
- **File & Line**: `docs/frontend/product-surface-model.md:122–165` (Required Pages and Screens Table)
- **Reproduction / Evidence**:
  The page inventory exhaustively lists 34 documentation routes across 10 sections and a global search modal, but omits a `404` or `/not-found` route.
- **Impact**: A documentation portal of 34+ pages with deep anchors, cross-links, and search results inevitably encounters broken links or mistyped URLs. Without a defined 404 contract, developers may implement an unstyled default Next.js error page that lacks the playful lo-fi mascot, theme support, or search redirection.
- **Required Fix**: Add a row to the screen inventory table:
  ```markdown
  | `/not-found` | `404: Страница не найдена` | Global Error | Friendly 404 screen with lo-fi lost-mascot illustration, explanation in Russian, quick links to Home and Overview, and search trigger. | `stable` |
  ```

---

### Finding 3: Omission of Output Suppression Rule in Snippet Component Specification
- **Severity**: **Medium (Non-blocking Contract Gap)**
- **File & Line**: `docs/frontend/product-surface-model.md:250–252` and lines `106–107`
- **Reproduction / Evidence**:
  The owner onboarding answers specify "snippets without output" (line 315). However, in Section 4 "Interactive Component States" (lines 250–252) under `Code Snippet Blocks`, the states specify monospace font, syntax highlighting, hover copy button, and copied feedback, but do not explicitly formalize the negative rule that command snippets must exclude execution output streams.
- **Impact**: Frontend authors or component implementers might include mocked terminal stdout/stderr blocks (e.g. simulated backtest run summaries or backfill logs) inside snippet containers, which can become stale, violate parity, or simulate live execution metrics.
- **Required Fix**: Add an explicit constraint under `Code Snippet Blocks` (lines 250–252) and in Section `Out of Scope`:
  "Terminal & CLI snippets must contain only runnable command syntax, flags, and arguments; displaying mocked or captured stdout/stderr terminal output is strictly prohibited to prevent stale or ungrounded claims."

---

### Finding 4: Unaddressed Diagram Implementation Technology in Open Decisions
- **Severity**: **Low (Non-blocking Architecture Refinement)**
- **File & Line**: `docs/frontend/product-surface-model.md:296–309` (Open Owner Decisions)
- **Reproduction / Evidence**:
  The product model mandates data and decision flow diagrams on multiple pages (Home, Architecture, Backtester, Execution), but leaves the technical implementation mechanism unspecified.
- **Impact**: Without explicit guidance, implementers may reach for heavy client-side diagram rendering libraries (such as Mermaid.js or Cytoscape) that increase initial bundle size and introduce layout shift during hydration, instead of lightweight theme-reactive React/SVG components or build-time SVG assets.
- **Required Fix**: Append `Decision 4: Diagram Rendering Approach` to Open Owner Decisions:
  - *Option A (Recommended)*: Bespoke React SVG diagram components styled with Tailwind CSS utility classes and design tokens, ensuring zero external client runtime, instant render, and seamless light/dark theme switching.
  - *Option B*: Build-time or client-rendered Mermaid.js diagrams embedded via MDX plugins.

---

## 4. Verification Checklists

| Requirement / Gate Check | Status | Evidence Reference |
|---|---|---|
| Product Name & Persona explicit | PASS | Lines 47–61 |
| 10 Required Sections complete | PASS | Lines 77–88, 122–165 |
| Dual-route navigation model (Learning vs Architecture) | PASS | Lines 89–91, 129–135, 168–189 |
| Russian language for interface and content | PASS | Lines 50–51, 75 |
| Next.js + Tailwind CSS stack | PASS | Lines 9, 298 |
| Full-text Cmd+K search | PASS | Lines 95, 232–239 |
| Light & Dark themes with lo-fi pastel tokens | PASS | Lines 51, 214–219, 307–309 |
| Breadcrumbs, Sidebar, TOC, Read-Next blocks | PASS | Lines 93–94, 221–228 |
| Section maturity statuses (`stable`, `research`, etc.) | PASS | Lines 98, 127–164 |
| No external CMS or database dependency | PASS | Lines 52, 108–109 |
| Absolute ban on live accounts, balances, and positions | PASS | Lines 103–105, 280–282 |
| Prohibition on raw Python source quotations | PASS | Lines 106–107 |
| Strict closed-candle invariant (`closed=True`) | PASS | Lines 25, 283–286 |
| Disclosure of Phase C benchmark fail & owner override | PASS | Lines 26, 82, 118–119, 288–290 |
| Proposed features marked absent/unbuilt | PASS | Lines 27, 41–43, 114–116, 292–294 |
| Factual alignment with codebase dependencies | FAIL (Fixed via Finding 1) | Line 128 (`Polars` contradiction) |

---

## 5. Verdict and Next Action

- **Verdict**: **pass-with-fixes**
- **Re-review Target**: `docs/frontend/product-surface-model.md` Revision 2.
- **Next Action**:
  1. Product Surface Author updates `docs/frontend/product-surface-model.md` to resolve Finding 1 (replace `Polars` with `Pandas, PyArrow`), Finding 2 (add 404 route), and Finding 3 (codify snippet output prohibition).
  2. Contract Reviewer performs brief verification of Revision 2.
  3. Control Context presents Product Surface Approval (O05 Gate) to the repository owner.
