# Visual Direction Boards

Status: ready for owner comparison; Visual Direction Approval pending.
Product Surface source: revision 1, approved 2026-08-30.
Preliminary Design Identity source: revision 1.

These five self-contained HTML boards explore materially different visual
interpretations of the same approved public documentation portal. They are
design evidence, not production pages or reusable application code.

## Shared Product Contract

- English, public, self-contained documentation portal explaining how the
  `crypt` code works in plain language.
- Cartoon lo-fi laboratory identity with immediate crypto cues and a recurring
  named human researcher mascot.
- Moderate information density, equal mobile and desktop quality, light and
  dark theme evidence, global search, styled but exact charts, pseudocode,
  architecture diagrams, safe research/backtest CLI examples, and optional
  playful interactions.
- No dashboard, authentication, trading controls, exchange/account mutation,
  strategy editor, deploy control, live-money command, profit promise, or
  GitHub dependency.
- Motion may support comprehension but must have a useful static presentation
  under `prefers-reduced-motion`.

## Required Evidence In Every Board

- A distinct direction name and short rationale.
- Desktop composition that demonstrates the Overview page.
- A visible mobile composition or responsive transformation.
- Navigation, search, theme control, buttons, form/input, cards, list or table,
  styled chart, system diagram, semantic states, code/CLI block, tooltip or
  overlay, glossary treatment, and mascot usage.
- Representative loading, empty, error, disabled, overflow, or partial-data
  states where they clarify the direction.
- Exact chart labels and values sufficient to judge legibility; invented
  numbers must be visibly labelled as illustrative.
- Notes stating what the direction intentionally does not propose.

## Assigned Directions

1. `01-daybreak-sketch-lab.html` — airy editorial sketchbook laboratory.
2. `02-night-shift-observatory.html` — dark celestial crypto observatory.
3. `03-pocket-field-lab.html` — tactile field notebook and specimen archive.
4. `04-kinetic-systems-workshop.html` — animated modular machine workshop.
5. `05-soft-data-greenhouse.html` — organic pastel greenhouse for data flows.

## Inspection Targets

- Desktop: 1440 x 1000.
- Mobile: 390 x 844.
- Wide desktop spot check: 1728 x 1117.

Visual Direction Approval is required after rendering, inspection, independent
review, and owner comparison. No board is approved by its creation alone.

## QA Summary

- All five boards parse as standalone HTML and use no external assets.
- Browser QA covered the 390 x 844 mobile composition for every board, with
  global horizontal overflow removed while chart/table strips remain locally
  scrollable. Desktop and wide layouts were spot-checked during comparison.
- Theme, search, navigation, and reduced-motion evidence were source-reviewed;
  the mobile blockers found in directions 02 and 05 were corrected.
- Browser console and network logs were clean during the comparison session.
- Independent Cursor Grok review ranked identity fit as 01, 03, 04, 05, 02.
  This is review input, not an approval decision.

See `../reviews/2026-08-30-visual-direction-boards.md` for the recorded verdict.
