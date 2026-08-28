# Frontend Design Subsystem Card

Full source: `docs/agent/frontend_design_subsystem.md`

Use this card when a task touches frontend UX, visual design, UI components, screen contracts, rendered inspection, design memory, or product identity.

Core lifecycle:
- Classify depth: visual bug, small UI modification, new component, new section, new screen, major redesign, or new frontend/product.
- If frontend memory is not established, substantial frontend work starts with discovery and full onboarding; this applies to the first serious frontend task.
- Established frontend memory means complete product surface, identity, visual
  references, design-system rules, screen contracts, and onboarding completion
  evidence exist for the relevant product surface.
- Interview completed is not onboarding completed, design approved, or ready for
  implementation. Owner Decision Gates must pass before implementation.
- An owner's first answer to onboarding questions is not enough to establish frontend memory. Continue interview, Product Surface Model, visual exploration and feedback, final identity, and design system unless waived.
- Design Identity, Visual Direction Boards, references, and final design-system
  choices are grounded in owner answers, product evidence, or owner approval.
- First-time frontend onboarding is deep: at least 30 questions in adaptive
  rounds of 5, followed by an Uncertainty Check and more rounds when needed.
- The agent chooses each round's 5 questions dynamically from product context and prior answers; there is no fixed questionnaire.
- While frontend memory is still not established, name the next onboarding, synthesis, visual exploration, or persistence step.
- For a new site/app or major frontend surface, ask whether the owner wants a
  lightweight static stack or a framework/UI-library stack unless the repo
  already decides; this is the Stack Gate.
- Product Surface, Visual Direction, Scope/Completeness, and Final Pre-Implementation Gates require owner confirmation for substantial work.
- UI Contract Gate: every UI edit starts from current Mermaid user flow,
  navigation, or state diagrams plus separate gray-block HTML/CSS/JS wireframes
  for each real page and relevant breakpoint; render wireframes and get owner
  approval before production UI code changes.
- Large frontend tasks must be split into phases when onboarding, product
  modeling, design, implementation, and QA would overload active context; use
  Phase Handoff Strategy for production-ready sites/apps, many screens, major
  redesigns, or any case where context stops being manageable.
- End each phase with a durable handoff artifact when another phase/session or
  subagent must continue. Handoff is temporary: canonical files are source of
  truth, durable facts are persisted, and consumed handoff files are deleted.
- Before every substantial frontend phase, run a Subagent Availability Check:
  name the phase, check isolated subagent availability, use the subagent path
  for the next substantial phase or independent review when available, and record
  the selected path in chat plus the review or handoff artifact.
- Continue by priority: canonical phase output, isolated subagent whenever the
  agent knows how to operate subagents, fresh user session handoff, or current
  session only if context remains manageable. Loaded conversation remains until
  compaction/replacement.
- Use proportional design before implementation. Tiny fixes can go straight to
  implementation plus inspection; new screens/redesigns need UX modeling first.
- For a new site/app, major redesign, or substantial new product surface,
  discover existing product knowledge and Build a Product Surface Model before
  screen design.
- First inspect existing frontend choices and infer stable decisions. Ask only
  for unresolved choices.
- If product design identity is not established, run a deep one-time design
  onboarding before major UI work.
- Visual Direction Boards are picture artifacts plus notes. Use image-generation
  or visual tools for images; HTML fallback output is five separate rendered HTML
  board pages. Each board shows composition, typography, density, surfaces,
  color, UI fragments, and signature ideas. Owner feedback selects, mixes,
  rejects, or iterates them.
- Final Design Identity, Design System, and implementation follow the required
  owner gates.
- Persist design identity, system, references, Mermaid flows, wireframes, screen
  contracts, registry, decisions, and reviews under `docs/frontend/`.
- Before creating components, prefer existing project components, then UI
  library primitives, then composed primitives; new primitives are last.
- Render the real interface after implementation; code compilation is not
  enough. Complete Functional QA, Visual QA, Visual Review Protocol rubric
  review, Responsive Design Pass, and Product Completeness Review. Check desktop,
  mobile, intermediate, and large viewport breakpoints.
- Run a Responsive Design Pass for meaningful responsive work. Responsive design
  goes beyond layout survival: each viewport feels intentionally composed.
- Exercise every added interactive element: buttons, links, tabs, menus, forms,
  toggles, keyboard/focus states, and post-interaction behavior.
- Run Functional QA, Visual QA, and Product Completeness Review as separate
  checks for substantial work.
Visual review rubric: hierarchy, spacing, alignment, typography, density,
composition, component consistency, semantic color, states, accessibility,
responsive behavior, responsive transformations preserve hierarchy, interaction
correctness, Design Identity, Signature Traits, Anti-Identity, references, and
product reasons for AI-default UI patterns. Ask whether the UI clearly belongs
to this product and removing CSS leaves a useful product surface.
