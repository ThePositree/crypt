# Design System: crypt docs

Status: proposed (Revision 2)
Revision: 2
Derived from Design Identity revision: Revision 2 (2026-09-03)
Date: 2026-09-03
Target Stack: Next.js App Router (v14/v15) + Tailwind CSS (v3.4 / v4)
Canonical Product Surface: docs/frontend/product-surface-model.md (Revision 2, approved)
Review Reference: docs/frontend/reviews/messaging-design-contract-review-2026-09-03.md (Revision 1 Review, pass-with-fixes)
Downstream Mandatory Gates: O10 (Five raster Visual Direction Boards), O11 (Visual Direction Approval), O18–O20 (Page-level Wireframes, Persistent HTML Wireframe Artifacts, and Wireframe Approval), O21 (Screen Contracts for all 35+ portal routes), O25 (Final Implementation Approval), O33 (Independent Frontend QA Gate), O34 (Independent QA Brief)

This document establishes the technical design system for `crypt docs`—a comprehensive Russian framework documentation portal for quantitative developer-crypto-traders. It derives its visual principles from Design Identity Revision 2 and translates them into reusable design tokens, component rules, responsive behaviors, and practical Next.js + Tailwind CSS configuration guidance.

---

## Foundational Principles & Mandatory Gate

1. **Derivation from Design Identity Revision 2**:
   - The design system implements the approved visual tension: combining playful lo-fi pastel aesthetics and abstract geometric mascots with high-density, technically rigorous engineering documentation UX.
   - It strictly eliminates generic one-note crypto aesthetics (no pure purple-on-black neon palettes, no dark-slate terminal clones, no generic glowing orbs).
2. **Strict Negative Boundaries**:
   - **No Live Trading Metrics or Balances**: No real-time PnL widgets, active positions, or live equity charts.
   - **No Raw Source Code Quotations**: Explanations use structured prose, parameter tables, and architecture diagrams rather than quoted Python source lines.
   - **Command-Only Snippets**: CLI blocks display runnable commands only; captured stdout/stderr execution outputs are strictly excluded.
   - **No Cards-Inside-Cards**: Information density is maintained through clean divider hairlines, table grids, and subtle background shifts rather than nested box containers.
3. **Mandatory Downstream Gates Chain**:
   - **EXPLICIT GATING REQUIREMENT**: Exactly five rendered raster Visual Direction Boards remain required under `docs/agent/frontend_design_subsystem.md` (Gate O10) before Visual Direction Approval (Gate O11) and subsequent visual sign-off can occur. The complete downstream gate progression before any production code implementation includes:
     1. Gate O10: Five raster Visual Direction Boards
     2. Gate O11: Visual Direction Approval
     3. Gates O18–O20: Page-Level Wireframes (O18), Persistent HTML Wireframe Artifacts (O19), and Wireframe Approval (O20)
     4. Gate O21: Screen Contracts for all 35+ portal routes
     5. Gate O25: Final Implementation Approval
     6. Gate O33: Independent Frontend QA Gate (accompanied by Gate O34 Independent QA Brief)
   - Written tokens, HTML wireframes, and CSS classes establish technical rules and contracts but do not satisfy or bypass these mandatory downstream gates.

---

## 1. Typography

The typographic hierarchy prioritizes rapid scanning, effortless reading of dense technical prose, and unambiguous distinction between Russian conceptual text and English code identifiers.

### 1.1 Font Families
- **Primary Sans (Body & UI)**:
  - Font: `Inter`, `Geist Sans`, or system fallback:
    `-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif`
  - Purpose: Body copy, section leads, navigation links, table cells, tooltips.
  - Characteristics: Exceptional Cyrillic glyph clarity, neutral grotesque geometry, balanced vertical metrics.
- **Display Sans (Headings)**:
  - Font: Primary Sans with normal letter-spacing (`tracking-normal` / `0em`).
  - Purpose: Page titles (`h1`), section headers (`h2`), subsystem titles (`h3`).
- **Technical Monospace (Code & Data)**:
  - Font: `JetBrains Mono`, `Geist Mono`, or system monospace fallback:
    `ui-monospace, SFMono-Regular, "Roboto Mono", Menlo, Monaco, Consolas, monospace`
  - Purpose: CLI command snippets, parameter flags (`--strategy`), environment variables (`PYTHONPATH=src`), JSON keys, file paths (`src/backtester/`), tabular numeric values.
  - Characteristics: Distinct `0`/`O` and `1`/`l`/`I` glyphs, proportional Cyrillic support, built-in tabular figures.

### 1.2 Type Scale & Hierarchy

| Token | Class (Tailwind) | Font Size | Line Height | Weight | Tracking | Primary Usage |
|---|---|---|---|---|---|---|
| `text-display` | `text-4xl` | 36px (2.25rem) | 44px (2.75rem) | 800 (extrabold) | `0em` (`tracking-normal`) | Portal root landing hero title |
| `text-h1` | `text-3xl` | 30px (1.875rem) | 36px (2.25rem) | 700 (bold) | `0em` (`tracking-normal`) | Page main titles (e.g. "Обзор платформы") |
| `text-h2` | `text-2xl` | 24px (1.5rem) | 32px (2.0rem) | 700 (bold) | `0em` (`tracking-normal`) | Major section headers (H2) |
| `text-h3` | `text-xl` | 20px (1.25rem) | 28px (1.75rem) | 600 (semibold) | `0em` (`tracking-normal`) | Subsystem headings, card titles (H3) |
| `text-h4` | `text-lg` | 18px (1.125rem) | 26px (1.625rem) | 600 (semibold) | `0em` (`tracking-normal`) | Callout headers, accordion titles (H4) |
| `text-body` | `text-base` | 16px (1.0rem) | 24px (1.5rem) | 400 (normal) | `0em` | Primary prose paragraphs, lead text |
| `text-body-sm` | `text-sm` | 14px (0.875rem) | 20px (1.25rem) | 400 / 500 | `0em` | Sidebar navigation, table body, code blocks |
| `text-caption` | `text-xs` | 12px (0.75rem) | 16px (1.0rem) | 500 (medium) | `+0.01em` | Maturity badges, breadcrumbs, TOC child items |
| `text-mono` | `font-mono text-sm` | 13px (0.8125rem)| 20px (1.25rem) | 400 / 500 | `0em` | Inline code, command snippets, file paths |

### 1.3 Typographic Rules
- **Line Length**: Main documentation prose columns are constrained to `max-w-3xl` (approx. 68–75 characters per line) to maintain optimal reading rhythm.
- **Russian Language Formatting**: All UI labels, explanations, guides, and tooltips are authored in Russian. Proper Russian typographic punctuation is enforced (em-dash `—` with spaces, chevron quotation marks `«` and `»` for titles).
- **Prohibition on Negative Letter-Spacing**: Negative tracking (`tracking-tight`, negative `letter-spacing`) is strictly prohibited across all headings, body copy, and UI text. In Cyrillic typography, negative tracking crushes wide glyphs (Ж, Ш, Щ, Ю, Ы, Ф, Д, Ц), degrades scannability in technical documentation, and causes font clipping across WebKit and Blink renderers when custom fonts or system fallbacks render with wider Cyrillic metrics. All headings and body copy use normal tracking (`0em` / `tracking-normal`). Positive tracking is reserved exclusively for small uppercase labels (`text-caption` with `+0.01em` and uppercase table headers with `tracking-wider` / `+0.05em`).
- **Technical Identifier Rule**: Code terms, CLI flags, environment variables, strategy names, and exchange parameters retain exact English casing (e.g. `filtered_donor_portfolio`, `move_order_stop`, `closed=True`) styled with inline monospace pills.

---

## 2. Spacing & Layout Geometry

The spatial system uses an 8-point base grid with a 4-point micro-grid for compact controls.

### 2.1 Spacing Scale

| Token | Pixels | Rem | Typical Usage |
|---|---|---|---|
| `space-1` | 4px | 0.25rem | Micro-gap between icon and text, compact badge padding (`py-0.5`) |
| `space-2` | 8px | 0.5rem | Gap between list items, badge horizontal padding (`px-2`), chip gap |
| `space-3` | 12px | 0.75rem | Compact button padding (`py-1.5 px-3`), breadcrumb gap |
| `space-4` | 16px | 1.0rem | Standard card padding (`p-4`), callout padding, table cell padding |
| `space-6` | 24px | 1.5rem | Section spacing inside cards, modal interior padding (`p-6`) |
| `space-8` | 32px | 2.0rem | Vertical margin between major documentation sections (`mb-8`) |
| `space-12` | 48px | 3.0rem | Vertical margin above `h2` headings, page bottom padding |
| `space-16` | 64px | 4.0rem | Top hero spacing, footer separation |

### 2.2 Layout Dimensions
- **Left Navigation Sidebar**: `w-64` (256px) on desktop; `w-72` (288px) on wide viewports. Sticky positioning (`sticky top-16 h-[calc(100vh-4rem)]`).
- **Main Documentation Content Column**: Centered with `max-w-4xl` (896px) total width, with prose blocks constrained to `max-w-3xl` (768px).
- **Right On-Page Table of Contents (TOC)**: `w-56` (224px) to `w-64` (256px). Sticky positioning with scrollspy highlighting.
- **Top Header Navbar**: Height `h-16` (64px). Sticky with backdrop blur (`backdrop-blur-md`).
- **Command Palette Modal (Cmd+K)**: Centered overlay, `max-w-2xl` (672px), `max-h-[80vh]`.

---

## 3. Colors & Semantic Color Usage

The color system avoids one-note purple or dark-slate monotony. It introduces a balanced, multi-hue pastel palette paired symmetrically between Light and Dark modes.

### 3.1 Neutral Canvas & Surface Tokens

| Role | Light Mode (HEX / CSS) | Dark Mode (HEX / CSS) | Purpose & Usage |
|---|---|---|---|
| `canvas-base` | `#FAF9F5` (`ivory-50`) | `#131418` (`graphite-950`) | Base viewport background |
| `canvas-subtle` | `#F3F2EC` (`ivory-100`) | `#1B1D23` (`graphite-900`) | Sidebar, navbar, table headers |
| `surface-card` | `#FFFFFF` (`white`) | `#22242C` (`graphite-850`) | Standard cards, code containers, callout boxes |
| `surface-overlay` | `#FFFFFF` (`white`) | `#2A2D36` (`graphite-800`) | Command palette modal, dropdowns, tooltips |
| `border-subtle` | `#E6E5DE` (`stone-200`) | `#2E323D` (`graphite-700`) | Default 1px card and divider borders |
| `border-medium` | `#D3D1C7` (`stone-300`) | `#404554` (`graphite-600`) | Hovered card borders, active input borders |
| `text-primary` | `#1A1C1E` (`stone-900`) | `#F3F4F6` (`gray-100`) | Main headings and prose text |
| `text-secondary` | `#595E68` (`stone-600`) | `#9CA3AF` (`gray-400`) | Subheadings, sidebar links, table captions |
| `text-muted` | `#8A909D` (`stone-400`) | `#6B7280` (`gray-500`) | Breadcrumbs, metadata, inactive icons |

### 3.2 Multi-Hue Semantic Pastel Families

Each functional domain is assigned a deliberate pastel hue pair (tint background + saturated accent border/text).

```
┌────────────────────────────────────────────────────────────────────────┐
│                     Semantic Pastel Color Matrix                       │
├───────────────────┬──────────────────┬──────────────────┬──────────────┤
│ Domain / Category │ Light (Bg / Text)│ Dark (Bg / Text) │ Accent Border│
├───────────────────┼──────────────────┼──────────────────┼──────────────┤
│ 1. Invariants     │ #F3EFFF / #5B3FB8│ #231C3D / #C7B5FF│ #7C5CE6      │
│    (Lavender)     │ (pure math, DSS) │ (closed-candle)  │              │
├───────────────────┼──────────────────┼──────────────────┼──────────────┤
│ 2. Parity/Stable  │ #EBF8F1 / #1B7243│ #162B20 / #88E3AE│ #2DB872      │
│    (Mint / Sage)  │ (exchange sync)  │ (regression pass)│              │
├───────────────────┼──────────────────┼──────────────────┼──────────────┤
│ 3. Research/Warn  │ #FEF5E7 / #9A5A07│ #322513 / #FAD089│ #F59E0B      │
│    (Warm Peach)   │ (optuna, caveats)│ (uncalibrated)   │              │
├───────────────────┼──────────────────┼──────────────────┼──────────────┤
│ 4. Risk / Money   │ #FDEEEE / #B32626│ #35191C / #FFA4A4│ #EF4444      │
│    (Soft Coral)   │ (liquidation, SL)│ (live execution) │              │
├───────────────────┼──────────────────┼──────────────────┼──────────────┤
│ 5. Operational    │ #EDF5FF / #1E56A0│ #15263F / #93C5FD│ #3B82F6      │
│    (Sky Blue)     │ (Railway, CLI)   │ (deploy, logs)   │              │
├───────────────────┼──────────────────┼──────────────────┼──────────────┤
│ 6. Retired/Arch   │ #F4F4F6 / #4B5563│ #1E2026 / #9CA3AF│ #6B7280      │
│    (Muted Ash)    │ (crypt.backtest) │ (coinglass)      │              │
└───────────────────┴──────────────────┴──────────────────┴──────────────┘
```

### 3.3 Accessibility & Contrast Compliance
- All text combinations satisfy **WCAG AA** minimum contrast ratios:
  - Body text against canvas/surface: `> 7:1` (exceeds the 4.5:1 requirement).
  - Secondary text against canvas: `> 4.6:1`.
  - Semantic alert text against alert background: `> 4.5:1` in both Light and Dark themes.
  - Interactive focus indicators (`ring-2 ring-pastel-lavender-accent` or `ring-2 ring-accent-ring`): `> 3:1` against adjacent surfaces.

---

## 4. Surfaces & Layering

Surfaces follow a clean, low-depth architectural layering model without nested card clutter.

- **Level 0 (Canvas)**: Viewport background (`bg-canvas-base`).
- **Level 1 (Structural Surfaces)**: Left navigation sidebar, top navbar, footer (`bg-canvas-subtle border-border-subtle`).
- **Level 2 (Content Containers)**: Code snippet blocks, callout panels, tabbed panels, table containers (`bg-surface-card border border-border-subtle rounded-lg`).
- **Level 3 (Interactive Overlays)**: Cmd+K search palette, mobile drawer, dropdowns, tooltips (`bg-surface-overlay border border-border-medium shadow-xl`).

### Anti-Pattern: No Cards-Inside-Cards
Nested containers are strictly prohibited. When a card contains multiple sub-items, separation must use:
1. Subtle hairline borders (`divide-y divide-border-subtle`).
2. Alternating row fills (`even:bg-canvas-subtle/50`).
3. Generous vertical spacing (`space-y-4`) rather than nested bordered boxes.

---

## 5. Borders, Radii, and Elevation

### 5.1 Borders
- **Standard Border**: `1px solid var(--border-subtle)`. Clean hairline frame separating content regions.
- **Accent Left Border**: `3px solid var(--accent)` or `4px solid` on callout warning boxes (mapped via `--accent: var(--pastel-lavender-accent)`).
- **Interactive Ring**: `2px solid var(--accent-ring)` with `offset-2` for accessible keyboard focus (mapped via `--accent-ring: var(--pastel-lavender-accent)`).

### 5.2 Radii (Corner Rounding)
- `rounded-sm` (4px): Inline code badges, keyboard shortcuts (`<kbd>⌘K</kbd>`).
- `rounded-md` (6px): Interactive buttons, search inputs, status badges.
- `rounded-lg` (8px): Code snippet containers, callout boxes, table frames, tab containers.
- `rounded-xl` (12px): Cmd+K command palette modal, dialog boxes.
- `rounded-full` (9999px): Route indicator dots, status chips, avatar badges.

### 5.3 Elevation & Shadows
- Flat and diffuse shadows preserve the calm lo-fi aesthetic:
  - `shadow-none`: Default for standard inline content cards, tables, and callouts.
  - `shadow-sm`: Subtle lift on sticky navbar during scroll, interactive buttons.
  - `shadow-md`: Contextual dropdown menus, tooltips.
  - `shadow-xl`: Cmd+K command palette modal paired with `backdrop-blur-sm`.
- **Prohibition**: Heavy, opaque black drop shadows and multi-color neon outer glows are banned.

---

## 6. Density & Information Architecture

- **High Technical Density**: Developer-crypto-traders need efficient information throughput. Tables, parameter lists, and CLI snippets use tight vertical padding (`py-2 px-3` for table cells, `py-1.5` for list rows).
- **Prose Breathing Room**: Reading blocks preserve comfortable readability with `leading-relaxed` (1.5 line height) and `max-w-3xl` column constraint.
- **Hierarchical Scannability**: Every page provides:
  1. Breadcrumb navigation path at top.
  2. Section maturity status badge (`stable`, `research`, `operational`, `archived`).
  3. Interactive on-page TOC on the right with active scrollspy tracking.
  4. Contextual "Что читать дальше" (What to Read Next) footer cards at the bottom.

---

## 7. Iconography & Abstract Mascots

### 7.1 Technical Iconography
- **Icon Family**: Clean, consistent outline icons with 1.5px to 2px stroke width (e.g. `Lucide React`).
- **Sizing Standards**:
  - `14px` (`w-3.5 h-3.5`): Inline maturity badges, copy button status, micro indicators.
  - `16px` (`w-4 h-4`): Table column headers, breadcrumb chevrons, button icons.
  - `20px` (`w-5 h-5`): Navigation sidebar items, callout headers, search inputs.
  - `24px` (`w-6 h-6`): Modal headers, section overview cards.

### 7.2 Abstract Geometric Mascots
- **Aesthetic**: Minimalist lo-fi geometric vector entities composed of clean lines, pastel fills, and rounded vertices. They embody system concepts rather than cartoon characters:
  - *The Candle Keeper*: Geometric block holding an hourglass (symbolizing closed-candle invariant).
  - *The Risk Sentry*: Shield-like geometric figure with safety latch (symbolizing isolated margin & circuit breakers).
  - *The Signal Scout*: Multi-faceted crystalline polyhedron (symbolizing DSS v3 discovery).
  - *The Lost Automaton*: Puzzled geometric robot with an unplugged cable (featured on the `/not-found` 404 page).
- **Usage**: Mascots appear strictly in section milestone cards, empty search states (`Ничего не найдено`), callout banners, and the 404 page. They never obscure or clutter dense technical text.
- **Dimensional Stability & Aspect Ratio Constraints**:
  To eliminate Cumulative Layout Shift (CLS) during client-side hydration, all mascot containers enforce rigid width, height, and aspect-ratio constraints:
  - *Inline Callouts & Milestone Badges*: `w-16 h-16` (64×64px), `aspect-square`, `shrink-0`.
  - *Section Overview Cards*: `w-24 h-24` (96×96px), `aspect-square`, container with reserved min-height `min-h-[96px]`.
  - *Empty Search State & 404 Error Screen*: `w-32 h-32` (128×128px), `aspect-square`, centered container with reserved min-height `min-h-[160px]`.
  - All SVG mascot illustrations declare explicit `viewBox="0 0 128 128"` and `preserveAspectRatio="xMidYMid meet"`.

---

## 8. Motion & Transitions

All animations are functional, subtle, and respect user accessibility preferences.

- **Standard Duration & Easing**:
  - Micro-interactions (hover, focus, tab active indicator): `150ms ease-out`.
  - Component disclosures (accordion expand/collapse, dropdowns): `200ms ease-out`.
  - Modal overlay (Cmd+K open/fade): `200ms ease-out`.
- **Accessibility Rule**:
  - All transitions must include `motion-reduce:transition-none` and `motion-reduce:transform-none` to honor system `prefers-reduced-motion` settings.
- **Prohibitions**:
  - No continuous background particle animations, no 3D card flips, no infinite pulsing neon elements, and no scroll-jacking parallax effects.

---

## 9. Forms & Interactive Controls

### 9.1 Search & Command Palette (Cmd+K)
- **Header Search Bar**:
  - Pill input with search icon, placeholder `"Поиск по документации..."`, and right-aligned `<kbd>⌘K</kbd>` / `<kbd>Ctrl+K</kbd>` badge.
  - Focus state triggers subtle `ring-2 ring-pastel-lavender-accent` / `ring-accent-ring`.
- **Command Palette Modal**:
  - Backdrop: `bg-stone-900/40 dark:bg-black/60 backdrop-blur-sm`.
  - Input field: Borderless `text-lg` with real-time in-memory query evaluation.
  - Results list: Grouped by documentation section with breadcrumbs, title, match snippet, and maturity badge.
  - Active result: Highlighted with pastel-lavender surface and arrow indicator.
  - Empty State: Friendly lo-fi mascot illustration with "Ничего не найдено" and query suggestions.

### 9.2 Filter Inputs & Toggles
- **Table / Glossary Filter**: Clean text input with search icon and an instant clear button (`✕`).
- **Theme Toggle**: Accessible icon button in header (Sun / Moon) with smooth SVG path transition. Stored in `localStorage`.

---

## 10. Tables & Matrices

Tables are central to presenting CLI parameters, configuration variables, and glossary definitions.

- **Structure**:
  - Container: `border border-border-subtle rounded-lg overflow-hidden`.
  - Header: `bg-canvas-subtle text-text-secondary text-xs uppercase tracking-wider font-semibold border-b border-border-subtle px-4 py-2.5 text-left`.
  - Rows: `divide-y divide-border-subtle text-sm`.
  - Hover: `hover:bg-canvas-subtle/50 transition-colors`.
  - Monospace Cells: Arguments (`--strategy`), environment variables (`PYTHONPATH`), and file paths receive `font-mono text-xs bg-canvas-subtle/80 px-1.5 py-0.5 rounded`.
  - Responsiveness: Wrapped in `overflow-x-auto` with sticky left column for narrow viewports.

---

## 11. Code Snippets & Command Blocks

- **Strict Command-Only Constraint**: Snippets display runnable syntax, arguments, and environment flags only. Captured terminal outputs, mock results, and execution stdout/stderr logs are strictly prohibited.
- **Structure**:
  - Frame: `bg-surface-card border border-border-subtle rounded-lg p-4 font-mono text-sm relative group`.
  - Header Pill: Displays environment context (e.g. `bash` or `env`).
  - Copy Action: Top-right button visible on hover/focus, with fixed width (`min-w-[140px]`) and fixed height (`h-8`) to eliminate layout jump when transitioning between `"Копировать команду"` and `"Скопировано!"`.
  - Copied State: Replaces copy icon with green checkmark and shows `"Скопировано!"` text (persists for 2000ms within identical dimensions) or renders feedback via tooltip.

---

## 12. Diagrams & System Visualizations

- **Implementation Approach**: Bespoke React SVG components styled via Tailwind utility classes and CSS variables (per approved Decision 4 in Product Surface Model).
- **Theme Parity**: SVG strokes, fills, and text labels use semantic CSS variables (`var(--border-subtle)`, `var(--pastel-lavender-bg)`, `var(--pastel-lavender-accent)`, `var(--text-primary)`), automatically updating with light/dark theme switches without re-rendering.
- **Dimensional Stability & Aspect Ratio Rules**:
  - All React SVG diagrams declare static `viewBox` definitions (e.g. `viewBox="0 0 800 400"` for two-domain overview, `viewBox="0 0 600 240"` for state machines) and `preserveAspectRatio="xMidYMid meet"`.
  - Diagram wrapper containers enforce responsive aspect-ratio classes (`aspect-[2/1]` or `aspect-[5/2]`) with minimum heights (`min-h-[240px]` or `min-h-[300px]`) to reserve layout space and eliminate Cumulative Layout Shift (CLS) during initial hydration and dynamic theme switching.
- **Architectural Schematics**:
  - Two-Domain Split: Clear visual boundary separating research workbench (`src/backtester/`, lavender-tinted frame) from production runtime (`src/crypt/`, sky-tinted frame).
  - State Machines: Sequential pill nodes (`entry_intent -> entry_submitted -> entry_filled -> protected`) connected by directional SVG arrows with status badges.
- **Prohibitions**:
  - No live trading charts, no simulated market tickers, and no real-time PnL graphs.

---

## 13. Responsive Principles & Canonical Viewport Classes

Per `docs/agent/frontend_design_subsystem.md` (Gate O31), the responsive architecture strictly defines layout behavior across **six canonical viewport classes**:

| # | Viewport Class | Width Range | Layout Behavior & Structural Adaptations |
|---|---|---|---|
| **1** | **Narrow mobile** | `< 640px` | Single-column layout. Sticky top bar with hamburger button opening a full-screen slide-over drawer with dual-route switch (Architecture vs Learning) and section accordion. On-page TOC hidden. Tables horizontally scrollable with sticky first column. Floating search icon button triggers full-screen Cmd+K modal. Mascot illustrations scale to `w-16 h-16`. |
| **2** | **Mobile-wide / Small tablet** | `640px – 767px` | Single-column layout with expanded horizontal margins (`px-6`). Search bar expands inline in top header (`max-w-xs`). Table controls display horizontal chips. Sidebar remains in slide-over drawer with larger touch targets. Preflight/code snippet containers scroll horizontally without clipping. |
| **3** | **Tablet** | `768px – 1023px` | Two-column collapsible layout. Left sidebar collapsible into a compact icon rail or toggled overlay drawer. Central documentation column expands to full width (`max-w-2xl`). On-page TOC accessible via a collapsible top accordion banner (`На этой странице`). |
| **4** | **Desktop** | `1024px – 1279px` | Two-column persistent layout. Left navigation sidebar permanently visible (`w-64`, sticky `h-[calc(100vh-4rem)]`). Central documentation column constrained to `max-w-3xl` for optimal reading line length. On-page TOC accessible as a floating slide-over sheet or inline header drop. |
| **5** | **Large desktop** | `1280px – 1535px` | Three-column persistent layout. Fixed left navigation sidebar (`w-64`). Central documentation column (`max-w-4xl`, prose constrained to `max-w-3xl`). Sticky right on-page TOC (`w-56`) with live scrollspy active heading highlighting. Full top header search pill (`Cmd+K`). |
| **6** | **Wide desktop** | `≥ 1536px` | Three-column expansive layout. Fixed left navigation sidebar (`w-72`). Central documentation column (`max-w-4xl`). Sticky right on-page TOC (`w-64`). Maximum canvas centered with generous outer margins to prevent awkward line elongation. |

---

## 14. Semantic States

All interactive components specify explicit visual feedback across all states:

1. **Default / Resting**: Clear typography, subtle borders, accessible contrast.
2. **Hover**: Surface tint shifts (`hover:bg-canvas-subtle/80`), borders darken (`hover:border-border-medium`), cursor becomes pointer.
3. **Active / Pressed**: Subtle scale down (`active:scale-[0.98]`), surface darkens slightly.
4. **Focus-Visible**: Keyboard focus displays high-visibility ring (`focus-visible:ring-2 focus-visible:ring-pastel-lavender-accent focus-visible:outline-none`).
5. **Disabled**: Opacity reduced (`opacity-50`), cursor changed (`cursor-not-allowed`), pointer events blocked.
6. **Loading / Skeleton**: Smooth pastel-tinted pulse shimmer (`animate-pulse bg-canvas-subtle rounded`).
7. **Empty**: Centered lo-fi mascot illustration, friendly Russian heading (`Ничего не найдено`), and actionable search suggestions or filter reset buttons.
8. **Error**: Soft coral banner (`bg-pastel-coral-bg text-pastel-coral-text border border-pastel-coral-accent`), clear error explanation, and retry action.

---

## 15. Practical Next.js + Tailwind Token Guidance

This section provides concrete, production-ready configuration code for implementing the design system in a Next.js App Router application with Tailwind CSS.

### 15.1 CSS Variables Definition (`app/globals.css`)

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

@layer base {
  :root {
    /* Neutral Foundations - Light */
    --canvas-base: #FAF9F5;
    --canvas-subtle: #F3F2EC;
    --surface-card: #FFFFFF;
    --surface-overlay: #FFFFFF;
    --border-subtle: #E6E5DE;
    --border-medium: #D3D1C7;
    --text-primary: #1A1C1E;
    --text-secondary: #595E68;
    --text-muted: #8A909D;

    /* Accent & Interactive Ring Tokens - Light */
    --accent: var(--pastel-lavender-accent);
    --accent-ring: var(--pastel-lavender-accent);

    /* Semantic Pastel Families - Light */
    --pastel-lavender-bg: #F3EFFF;
    --pastel-lavender-text: #5B3FB8;
    --pastel-lavender-accent: #7C5CE6;

    --pastel-mint-bg: #EBF8F1;
    --pastel-mint-text: #1B7243;
    --pastel-mint-accent: #2DB872;

    --pastel-peach-bg: #FEF5E7;
    --pastel-peach-text: #9A5A07;
    --pastel-peach-accent: #F59E0B;

    --pastel-coral-bg: #FDEEEE;
    --pastel-coral-text: #B32626;
    --pastel-coral-accent: #EF4444;

    --pastel-sky-bg: #EDF5FF;
    --pastel-sky-text: #1E56A0;
    --pastel-sky-accent: #3B82F6;

    --pastel-ash-bg: #F4F4F6;
    --pastel-ash-text: #4B5563;
    --pastel-ash-accent: #6B7280;
  }

  .dark {
    /* Neutral Foundations - Dark */
    --canvas-base: #131418;
    --canvas-subtle: #1B1D23;
    --surface-card: #22242C;
    --surface-overlay: #2A2D36;
    --border-subtle: #2E323D;
    --border-medium: #404554;
    --text-primary: #F3F4F6;
    --text-secondary: #9CA3AF;
    --text-muted: #6B7280;

    /* Accent & Interactive Ring Tokens - Dark */
    --accent: var(--pastel-lavender-accent);
    --accent-ring: var(--pastel-lavender-accent);

    /* Semantic Pastel Families - Dark */
    --pastel-lavender-bg: #231C3D;
    --pastel-lavender-text: #C7B5FF;
    --pastel-lavender-accent: #9A80F2;

    --pastel-mint-bg: #162B20;
    --pastel-mint-text: #88E3AE;
    --pastel-mint-accent: #3DD68C;

    --pastel-peach-bg: #322513;
    --pastel-peach-text: #FAD089;
    --pastel-peach-accent: #FBBF24;

    --pastel-coral-bg: #35191C;
    --pastel-coral-text: #FFA4A4;
    --pastel-coral-accent: #F87171;

    --pastel-sky-bg: #15263F;
    --pastel-sky-text: #93C5FD;
    --pastel-sky-accent: #60A5FA;

    --pastel-ash-bg: #1E2026;
    --pastel-ash-text: #9CA3AF;
    --pastel-ash-accent: #9CA3AF;
  }
}
```

### 15.2 Tailwind Configuration (`tailwind.config.ts`)

```typescript
import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: "class",
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./content/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        canvas: {
          base: "var(--canvas-base)",
          subtle: "var(--canvas-subtle)",
        },
        surface: {
          card: "var(--surface-card)",
          overlay: "var(--surface-overlay)",
        },
        border: {
          subtle: "var(--border-subtle)",
          medium: "var(--border-medium)",
        },
        accent: {
          DEFAULT: "var(--accent)",
          ring: "var(--accent-ring)",
        },
        text: {
          primary: "var(--text-primary)",
          secondary: "var(--text-secondary)",
          muted: "var(--text-muted)",
        },
        pastel: {
          lavender: {
            bg: "var(--pastel-lavender-bg)",
            text: "var(--pastel-lavender-text)",
            accent: "var(--pastel-lavender-accent)",
          },
          mint: {
            bg: "var(--pastel-mint-bg)",
            text: "var(--pastel-mint-text)",
            accent: "var(--pastel-mint-accent)",
          },
          peach: {
            bg: "var(--pastel-peach-bg)",
            text: "var(--pastel-peach-text)",
            accent: "var(--pastel-peach-accent)",
          },
          coral: {
            bg: "var(--pastel-coral-bg)",
            text: "var(--pastel-coral-text)",
            accent: "var(--pastel-coral-accent)",
          },
          sky: {
            bg: "var(--pastel-sky-bg)",
            text: "var(--pastel-sky-text)",
            accent: "var(--pastel-sky-accent)",
          },
          ash: {
            bg: "var(--pastel-ash-bg)",
            text: "var(--pastel-ash-text)",
            accent: "var(--pastel-ash-accent)",
          },
        },
      },
      fontFamily: {
        sans: [
          "Inter",
          "Geist Sans",
          "-apple-system",
          "BlinkMacSystemFont",
          "Segoe UI",
          "Roboto",
          "sans-serif",
        ],
        mono: [
          "JetBrains Mono",
          "Geist Mono",
          "ui-monospace",
          "SFMono-Regular",
          "Menlo",
          "Monaco",
          "monospace",
        ],
      },
      borderRadius: {
        sm: "4px",
        md: "6px",
        lg: "8px",
        xl: "12px",
      },
    },
  },
  plugins: [],
};

export default config;
```

### 15.3 Composite Utility Patterns

- **Callout Invariant (Строгий инвариант)**:
  `bg-pastel-lavender-bg text-pastel-lavender-text border-l-4 border-pastel-lavender-accent p-4 rounded-r-lg`
- **Callout Risk (Критический риск)**:
  `bg-pastel-coral-bg text-pastel-coral-text border-l-4 border-pastel-coral-accent p-4 rounded-r-lg`
- **Callout Notice (Важное примечание)**:
  `bg-pastel-sky-bg text-pastel-sky-text border-l-4 border-pastel-sky-accent p-4 rounded-r-lg`
- **Error Banner (Ошибка / Сбой)**:
  `bg-pastel-coral-bg text-pastel-coral-text border border-pastel-coral-accent p-4 rounded-lg`
- **Maturity Badge (Стабильный / `stable`)**:
  `inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-pastel-mint-bg text-pastel-mint-text border border-pastel-mint-accent/30`
- **Maturity Badge (Исследования / `research`)**:
  `inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-pastel-peach-bg text-pastel-peach-text border border-pastel-peach-accent/30`
- **Code Block Container**:
  `bg-surface-card border border-border-subtle rounded-lg p-4 font-mono text-sm overflow-x-auto`
- **Copy Command Button (Fixed Dimensions)**:
  `inline-flex items-center justify-center min-w-[140px] h-8 px-3 py-1.5 rounded-md text-xs font-medium bg-canvas-subtle hover:bg-canvas-subtle/80 text-text-primary border border-border-subtle focus-visible:ring-2 focus-visible:ring-pastel-lavender-accent transition-colors`

---

## 16. Validation & Governance

- **Six Canonical Viewports Targeted for Verification (Gate O31)**:
  1. Narrow mobile: `375px` (iPhone SE/13 mini), `390px` (iPhone 14/15) (< 640px)
  2. Mobile-wide or small tablet: `640px` (landscape phone), `720px` (small tablet) (640px – 767px)
  3. Tablet: `768px` (iPad mini portrait), `820px` (iPad Air) (768px – 1023px)
  4. Desktop: `1024px` (Small laptop / 13" MacBook) (1024px – 1279px)
  5. Large desktop: `1280px` (MacBook default), `1440px` (1280px – 1535px)
  6. Wide desktop: `1536px` / `1920px` (Wide monitor / 1080p+ display) (≥ 1536px)

- **Components Sampled**:
  - Global Header with theme toggle and search trigger
  - Left navigation sidebar with dual-route switch and maturity badges
  - On-page table of contents with scrollspy active indicator
  - Semantic risk and invariant callout panels
  - Filterable CLI parameter tables
  - Copy-only monospace command snippet blocks with stable geometry (`min-w-[140px]`)
  - Cmd+K Command Palette overlay with search empty states and lo-fi mascots
  - 404 / Not Found screen with lo-fi mascot illustration and fixed aspect container
  - React SVG flow diagrams with static `viewBox` and responsive aspect-ratio containers

- **Accessibility Checks**:
  - Full keyboard navigation flow (Tab, Arrow keys, Enter, Escape).
  - WCAG AA contrast verified across all Light and Dark text tokens (> 4.5:1 text, > 3:1 focus rings).
  - Reduced-motion toggle tested (`motion-reduce:transition-none`).
  - Screen reader friendly heading hierarchy (`h1` -> `h2` -> `h3`).
  - Strictly normal letter-spacing (`tracking-normal` / `0em`) on all headings and body text (no Cyrillic clipping or glyph collisions).

- **Mandatory Downstream Gating Pipeline**:
  Under `docs/agent/frontend_design_subsystem.md`, production frontend Next.js code must not be implemented until each of the following sequential gates is satisfied:
  1. **Gate O10 (Five raster Visual Direction Boards)**: Rendering of exactly five raster visual direction boards exploring the playful lo-fi pastel aesthetic with abstract mascots.
  2. **Gate O11 (Visual Direction Approval)**: Explicit owner sign-off selecting one of the five visual direction boards.
  3. **Gates O18–O20 (Page-Level Wireframes, HTML Prototypes & Wireframe Approval)**: Page-level wireframes for every real screen (O18), persistent interactive HTML wireframes (O19), and formal wireframe approval sign-off (O20).
  4. **Gate O21 (Screen Contracts)**: Comprehensive screen-by-screen contracts across all 35+ portal routes.
  5. **Gate O25 (Final Implementation Approval)**: Explicit owner approval of the complete design and wireframe package before starting production frontend code in a separate session.
  6. **Gate O33 (Independent Frontend QA Gate) & Gate O34 (Independent QA Brief)**: Independent multi-viewport inspection across all six canonical viewport classes, validating accessibility, typography, and functional link coverage.
