# Frontend Design Subsystem Card

Full source: `docs/agent/frontend_design_subsystem.md`

Use this card when a task touches frontend UX, visual design, UI components, screen contracts, rendered inspection, design memory, or product identity.

Core lifecycle:
- Classify depth: visual bug, small UI modification, new component, new section, new screen, major redesign, or new frontend/product.
- If frontend memory is not established, stop substantial frontend work after
  discovery and run full onboarding before implementation; this applies to the
  first serious frontend task, not only a new site/app.
- Interview completed is not onboarding completed, design approved, or ready for
  implementation. Owner Decision Gates must pass before implementation.
- An owner's first answer to onboarding questions is not enough to establish
  frontend memory. Continue interview, Product Surface Model, visual exploration
  and feedback, final identity, and design system unless waived.
- Do not fill product Design Identity, Visual Direction Boards, positive or
  negative references, or final design-system choices from agent taste alone.
- First-time frontend onboarding is deep, not short: 30 questions total,
  delivered as 6 adaptive rounds of 5 questions. Do not ask all 30 at once.
- The agent chooses each round's 5 questions dynamically from product context
  and prior answers; there is no fixed questionnaire.
- Do not promise implementation immediately after the owner's next answer while
  frontend memory is still not established. Promise the next onboarding step,
  synthesis, visual exploration, or persistence step instead.
- For a new site/app or major frontend surface, ask whether the owner wants a
  lightweight static stack or a framework/UI-library stack unless the repo
  already decides; this is the Stack Gate.
- Product Surface, Visual Direction, Scope/Completeness, and Final Pre-Implementation Gates require owner confirmation for substantial work.
- Large frontend tasks must be split into phases when onboarding, product
  modeling, design, implementation, and QA would overload active context; use
  Phase Handoff Strategy for production-ready sites/apps, many screens, major
  redesigns, or any case where context stops being manageable.
- End each phase with a durable handoff artifact when another phase/session or
  subagent must continue. Handoff is temporary and must not be the only source
  of truth: persist durable facts, then delete consumed handoff files.
- Continue by priority: canonical phase output, isolated subagent if supported
  and reliable, fresh user session handoff, or current session only if context
  remains manageable. The agent must not pretend it can remove previous
  conversation history from context.
- Use proportional design before implementation. Tiny fixes can go straight to
  implementation plus inspection; new screens/redesigns need UX modeling first.
- For a new site/app, major redesign, or substantial new product surface,
  discover existing product knowledge and Build a Product Surface Model before
  screen design.
- First inspect existing frontend choices and infer stable decisions. Ask only
  for unresolved choices.
- If product design identity is not established, run a deep one-time design
  onboarding before major UI work.
- Visual exploration boards are direction studies; Visual Direction Boards require owner feedback and are not production assets. Do not replace the default five boards with one hero image.
- Do not finalize Design Identity before owner feedback or implement before required owner gates pass.
- Persist design identity, system, references, screen contracts, component
  registry, decisions, and reviews under `docs/frontend/`.
- Before creating components, prefer existing project components, then UI
  library primitives, then composed primitives; new primitives are last.
- Render the real interface after implementation; code compilation is not
  enough. Check desktop, mobile, intermediate, and large viewport breakpoints.
- Run a Responsive Design Pass for meaningful responsive work. Responsive design
  is not layout survival: each important viewport must feel intentionally
  composed for that product and width.
- Exercise every added interactive element: buttons, links, tabs, menus, forms,
  toggles, keyboard/focus states, and post-interaction behavior.
- Run Functional QA, Visual QA, and Product Completeness Review as separate
  checks for substantial work.

Visual review rubric:
- hierarchy, spacing, alignment, typography, density, composition;
- component consistency, semantic color, state handling, accessibility;
- responsive behavior across relevant viewport sizes, including large screens;
- responsive transformations preserve hierarchy, density, priorities, interaction
  model, spacing rhythm, and Design Identity;
- interaction correctness for every added clickable or focusable control;
- consistency with Design Identity, Signature Traits, Anti-Identity, and references;
- no unexamined AI-default UI such as excessive cards, meaningless gradients,
  decorative glow, giant in-app headings, pill overload, or generic dashboards.

Final check:
- Ask whether the UI merely looks clean or clearly belongs to this product.
- Ask whether removing CSS would still leave a complete useful product surface.
