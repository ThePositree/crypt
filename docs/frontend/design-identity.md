# Design Identity: crypt docs

Status: proposed (Revision 2)
Revision: 2
Date: 2026-09-03
Approval source: pending independent design contract re-review (O22) and downstream gate progression
Downstream Mandatory Gates: O10 (Five raster Visual Direction Boards), O11 (Visual Direction Approval), O18–O20 (Page-level Wireframes, Persistent HTML Wireframe Artifacts, and Wireframe Approval), O21 (Screen Contracts for all 35+ portal routes), O25 (Final Implementation Approval), O33 (Independent Frontend QA Gate), O34 (Independent QA Brief)
Canonical Product Surface: docs/frontend/product-surface-model.md (Revision 2, approved)
Review Reference: docs/frontend/reviews/messaging-design-contract-review-2026-09-03.md (Revision 1 Review, pass-with-fixes)

This document establishes the foundational design identity for `crypt docs`—a comprehensive Russian-language framework documentation portal for quantitative developer-crypto-traders. It guides downstream design system tokens, wireframes, flows, and component contracts.

---

## Core Feeling

- **Decision**:
  The portal evokes the calm, intellectual clarity and disarming warmth of an artisan engineering workshop combined with the uncompromising precision of a high-reliability aerospace manual. When a developer-crypto-trader arrives, they feel an immediate sense of relief from crypto industry cynicism: there are no garish neon tickers, no dark-mode gambling aesthetics, and no inflated promises. Instead, the environment feels thoughtfully curated, transparent, and quietly confident. Exploring intricate stochastic algorithms (DSS v3, CatCMA-QD) and discrete execution mechanics feels approachable, orderly, and intellectually invigorating rather than exhausting.

- **Evidence**:
  - The approved Product Surface Model (`docs/frontend/product-surface-model.md`, lines 48–61) mandates a framework-style documentation portal (comparable to PyTorch, Next.js, or Django documentation) in Russian, combining a playful lo-fi pastel aesthetic with abstract mascots and technically serious, dense docs UX.
  - The target persona (`developer-crypto-trader`, lines 54–61) possesses software engineering discipline and quantitative trading expertise. They value architectural truthfulness, statistical honesty, and clear mental models over marketing hype, while suffering fatigue from generic dark-slate crypto terminals.

---

## Personality

- **Decision**:
  The portal's visual personality balances four distinct attributes:
  1. *Rigorous & Truthful*: Unflinchingly honest about mathematical limits, execution risks, and operational trade-offs. It prominently displays the benchmark failure of production portfolio v6 (-13% return vs +15% target) and owner override status rather than sweeping anomalies under the rug.
  2. *Playful & Unpretentious*: Employs minimalist, geometric lo-fi mascots and soft pastel accents to humanize complex state machines without trivializing the underlying financial mathematics.
  3. *Dense & Structured*: Respects the cognitive workflow of engineers. Navigation, table of contents, parameter matrices, and breadcrumbs provide immediate orientation without wasteful decorative margins or bloated marketing heroes.
  4. *Pragmatic & Focused*: Strictly delivers executable syntax, copyable command snippets without terminal noise, and definitive parameter specifications that solve immediate operator problems.

- **Evidence**:
  - Persona requirements and Jobs-to-be-Done (`docs/frontend/product-surface-model.md`, lines 62–72): guided onboarding, architectural clarity, parity verification, and fast keyboard discovery.
  - Negative documentation boundaries (`docs/frontend/reviews/product-research-crypt-docs-2026-09-03.md`, lines 495–525): strict prohibition of simulated terminal logs, raw Python code quoting, and exaggerated capability claims.

---

## Desired Perception

- **Decision**:
  The user leaves every interaction with three definitive perceptions:
  1. *"This is an authentic, production-grade engineering artifact, not a commercial SaaS sales pitch or Web3 token project."*
  2. *"The architects behind this system deeply understand execution parity down to the millisecond WebSocket clock, discrete order states, isolated margin mechanics, and exchange accounting nuances."*
  3. *"The playful lo-fi visual language makes complex quantitative concepts enjoyable and intuitive to explore, while the documentation itself gives me exact operational mechanics without forcing me to reverse-engineer Python source files."*

- **Evidence**:
  - Subsystem ground truth in `docs/frontend/reviews/product-research-crypt-docs-2026-09-03.md` (lines 10–269), establishing the dual-domain split (`src/backtester/` research vs `src/crypt/` runtime), H1 WebSocket triggers (`HH:59:30 UTC`), native OKX trailing stops (`move_order_stop`), and durable monthly risk-base checkpoints.
  - Persona profile (`docs/frontend/product-surface-model.md`, lines 54–61): an audience that demands operational transparency and respects deep systems craft.

---

## Visual Tension

- **Decision**:
  The design intentionally orchestrates three complementary visual tensions:
  1. *Playful Lo-Fi Whimsy vs Mathematical Rigor*:
     - Soft pastel foundations (lavender, mint, peach, coral, ivory) and whimsical geometric mascots coexist with dense monospace parameter tables, strict state machine flowcharts, and high-visibility risk warning panels.
     - The playfulness lowers cognitive barriers; the structural density provides engineering depth.
  2. *Light Warmth vs Dark Depth (Thematic Parity)*:
     - Light Mode is not sterile corporate white; it is a warm, tactile ivory/cream canvas (`#FAF9F5`) with crisp charcoal typography and soft pastel card surfaces.
     - Dark Mode is not a generic high-contrast pitch-black crypto terminal; it is a deep, velvety charcoal/graphite surface (`#131418`) accented by luminous, desaturated pastel indicators.
     - Both themes maintain identical semantic clarity and visual weight without collapsing into one-note palettes.
  3. *Dense Information Architecture vs Generous Micro-Whitespace*:
     - Maximizes high-density tabular and diagrammatic data while preserving clear typography line-heights, distinct component separation, and focused line lengths (65–75 characters) to eliminate visual clutter.

- **Evidence**:
  - Approved theme constraints (`docs/frontend/product-surface-model.md`, lines 51, 98–101, 220–225): dual light/dark themes, lo-fi pastel tokens, and avoidance of one-note purple, beige, or dark-slate styling.
  - Open Owner Decisions (`docs/frontend/product-surface-model.md`, lines 313–315): explicit selection of balanced pastel tones over stark primary palettes.

---

## Signature Traits

- **Trait 1: Abstract Lo-Fi Mascots as Navigational Guides**
  - *Product Purpose*: Friendly, geometric vector mascots (such as the "Candle Keeper" for closed-candle invariants, the "Risk Sentry" for live execution, and the "Lost Scout" on the 404 page) guide users through technical topics, add distinctive visual identity, and soften dry algorithmic content without distracting from technical accuracy.
  - *UI Expression*: Stylized minimal line-and-pastel geometric figures appearing in page headers, empty search states, callout boxes, and the 404 error screen.

- **Trait 2: Monospace Command Panels with Copy-Only Snippets**
  - *Product Purpose*: Provides clean, copyable terminal snippets for daily research and operations while eliminating distracting, out-of-date terminal output.
  - *UI Expression*: Crisp, single-line or multi-line monospace code blocks featuring subtle pastel borders, language/environment tags, and one-click copy buttons, strictly excluding captured stdout/stderr results.

- **Trait 3: Multi-Hue Pastel Semantic Callout Architecture**
  - *Product Purpose*: Instantly signals the functional risk and domain context of callout blocks without relying on generic warning banners.
  - *UI Expression*: Four distinct pastel hue pairs:
    - *Lavender / Violet*: Mathematical and algorithmic invariants (closed candles, DSS v3, no look-ahead).
    - *Mint / Sage*: Stable maturity, verified parity, and exchange synchronization.
    - *Warm Peach / Amber*: Research caveats, Optuna parameter spaces, and uncalibrated legacy parameters.
    - *Soft Coral / Rose*: High-stakes live money risk, liquidation buffers, and order execution alerts.

- **Trait 4: Dual-Route Breadcrumbs & Progress Anchor**
  - *Product Purpose*: Clarifies user context between the structural *Architecture Route* and the sequential *Learning Route*.
  - *UI Expression*: Header pills and breadcrumb indicators (`[Архитектура]` vs `[Обучение: Шаг 3 из 5]`) with interactive step indicators that guide readers through multi-step tutorials.

- **Trait 5: Theme-Adaptive Bespoke SVG Flow Schematics**
  - *Product Purpose*: Illustrates state machines and data flows (e.g. `entry_intent` -> `protected`, two-domain data boundaries) without heavy external image assets or unstyled text blocks.
  - *UI Expression*: Responsive SVG vector diagrams utilizing Tailwind semantic tokens that render crisply and switch palettes synchronously with light/dark themes.

---

## Anti-Identity

- **Avoid**: One-Note Purple-on-Black or Dark-Slate Crypto Terminal Aesthetics
  - *Reason*: Evokes generic crypto DEXes, pump-and-dump tokens, or gambling dashboards, undermining the serious quantitative framework positioning.

- **Avoid**: Generic Glowing Orbs, Blurred Neon Bokeh, and Floating 3D Coin Renders
  - *Reason*: Cliched visual noise that signals marketing hype over substantive technical documentation.

- **Avoid**: Oversized Marketing Hero Sections and Empty Promotional Slogans
  - *Reason*: Developer-crypto-traders need instant access to documentation indexes, search palettes, and architecture maps; marketing fluff frustrates technical operators.

- **Avoid**: Cards-Inside-Cards Nesting and Heavy Multi-Layer Borders
  - *Reason*: Degrades vertical reading rhythm, increases visual noise, and hampers content scanning.

- **Avoid**: Raw Python Source Code Quotations
  - *Reason*: Strictly prohibited by the Product Surface Model (`docs/frontend/product-surface-model.md`, lines 107–109); documentation must explain principles, state machines, and architectures using clear prose, diagrams, and parameter tables rather than quoting fragile, mutable source lines.

- **Avoid**: Live Metrics, Real-Time PnL Tickers, and Active Account Balances
  - *Reason*: Strictly prohibited negative boundary (`docs/frontend/product-surface-model.md`, lines 104–106); the documentation portal is a static reference manual and educational workbench guide, never a live trading terminal.

- **Avoid**: Mocked or Simulated Terminal Execution Outputs / stdout Logs
  - *Reason*: Strictly prohibited (`docs/frontend/product-surface-model.md`, lines 121–123); code snippets must present only runnable syntax, arguments, and environment flags to prevent misleading or out-of-date runtime claims.

---

## Implementation-Dependent Exploration Record

- **Execution Context and Methods Used**:
  Analytical derivation and synthesis based on the approved Product Surface Model (`docs/frontend/product-surface-model.md`, Revision 2), Product Research ground truth (`docs/frontend/reviews/product-research-crypt-docs-2026-09-03.md`), and visual reference framework (`docs/frontend/visual-references/interpretation.md`).

- **Date**: 2026-09-03

- **Approved Visual Direction Revision**:
  `none` (blocked pending raster Visual Direction Boards).

- **Known Limitations & Mandatory Downstream Gates Requirement**:
  **EXPLICIT GATING REQUIREMENT**: Design Identity Revision 2 provides conceptual and visual direction principles, but does not authorize production frontend code implementation. The complete sequence of unresolved mandatory downstream gates required prior to production deployment includes:
  1. **Gate O10 (Five raster Visual Direction Boards)**: Exactly five rendered raster visual direction boards exploring diverse executions of the playful lo-fi pastel aesthetic with abstract mascots.
  2. **Gate O11 (Visual Direction Approval)**: Formal owner evaluation and approval of the selected visual direction board.
  3. **Gates O18–O20 (Page-Level Wireframes, HTML Wireframe Artifacts & Wireframe Approval)**: Production of structural page wireframes across all portal views (O18), creation of persistent HTML wireframe prototypes (O19), and formal wireframe approval sign-off (O20).
  4. **Gate O21 (Screen Contracts)**: Comprehensive screen-level contracts for all 35+ portal routes covering layout models, data requirements, error/empty states, and interaction inventory.
  5. **Gate O25 (Final Implementation Approval)**: Explicit owner sign-off on the complete design and wireframe package before initiating production frontend code in a separate implementation session.
  6. **Gate O33 (Independent Frontend QA Gate) & Gate O34 (Independent QA Brief)**: Strict post-implementation quality assurance audit verifying six canonical viewport classes, accessibility, typography, and functional links.

  Text-only descriptions, HTML wireframes, and design system token definitions do not satisfy or bypass these mandatory downstream gates.
