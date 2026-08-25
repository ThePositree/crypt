# Frontend Design Subsystem Card

Full source: `docs/agent/frontend_design_subsystem.md`

Use this card when a task touches frontend UX, visual design, UI components,
screen contracts, rendered inspection, design memory, or product-specific
interface identity.

Core lifecycle:

- Classify the frontend change by depth: visual bug, small UI modification, new
  component, new section, new screen, major redesign, or new frontend/product.
- For a new frontend/product or major redesign with no established Design
  Identity, stop after discovery and ask the owner for design onboarding input.
  Do not implement the site/app in the same turn unless the owner explicitly
  waives onboarding or prior frontend memory already proves the identity.
- Do not fill product Design Identity, Visual Direction Boards, positive or
  negative references, or final design-system choices from agent taste alone.
- Run design onboarding in small adaptive rounds. Ask only the next useful
  batch of questions, then let later questions depend on the owner's answers.
- For a new site/app or major frontend surface, explicitly ask whether the owner
  wants a lightweight static stack or a framework/UI-library stack before
  choosing implementation technology, unless the repo already makes that choice
  unambiguous.
- Use proportional design before implementation. Tiny fixes can go straight to
  implementation plus inspection; new screens and redesigns need UX modeling,
  contracts, and exploration first.
- For a new site/app, major redesign, or substantial new product surface,
  discover existing product knowledge before asking the owner to repeat it.
  Build a Product Surface Model before screen design.
- First inspect existing frontend choices and infer stable decisions. Ask only
  for unresolved choices that cannot reasonably be inferred.
- If product design identity is not established, run a deep one-time design
  onboarding before major UI work.
- Persist the resulting design identity, system, references, screen contracts,
  component registry, decisions, and reviews under `docs/frontend/`.
- Before creating components, prefer existing project components, then UI
  library primitives, then composed primitives; new primitives are last.
- Render the real interface after implementation and visually inspect it. Code
  compilation is not enough. Check desktop, mobile, intermediate, and large
  viewport breakpoints relevant to the layout.
- Run a Responsive Design Pass for meaningful responsive work. Responsive
  design is not layout survival: each important viewport must feel intentionally
  composed for that product and width.
- Exercise every added interactive element: buttons, links, tabs, menus, forms,
  toggles, keyboard/focus states, and post-interaction behavior.
- Run Functional QA, Visual QA, and Product Completeness Review as separate
  checks when the work is substantial. One does not replace the others.

Visual review rubric:

- hierarchy, spacing, alignment, typography, density, composition;
- component consistency, semantic color, state handling, accessibility;
- responsive behavior across relevant viewport sizes, including large screens
  when the layout could stretch;
- responsive transformations preserve hierarchy, density, priorities,
  interaction model, spacing rhythm, and Design Identity;
- interaction correctness for every added clickable or focusable control;
- consistency with Design Identity, Signature Traits, Anti-Identity, and visual
  references;
- no unexamined AI-default UI such as excessive cards, meaningless gradients,
  decorative glow, giant in-app headings, pill overload, or generic dashboard
  metric-card layouts.

Final check:

- Ask whether the UI merely looks clean or clearly belongs to this product.
- Ask whether removing CSS would still leave a complete useful product surface
  for the requested scope.
