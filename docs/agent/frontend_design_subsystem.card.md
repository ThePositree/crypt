# Frontend Design Subsystem Card

Full source: `docs/agent/frontend_design_subsystem.md`

Use this card when a task touches frontend UX, visual design, UI components, screen contracts, rendered inspection, design memory, or product identity.

Core lifecycle:
- Classify depth: visual bug, small UI modification, new component, new section, new screen, major redesign, or new frontend/product.
- Frontend work is phase-based product work. The owner values correctness, product fit, visual quality, and durable frontend memory more than immediate implementation.
- Every frontend task, from a small CSS adjustment to a new site, follows the same phase order: context discovery, product or screen intent, UI contract, implementation at the appropriate phase, rendered inspection, responsive consideration, and durable memory or handoff when needed.
- A frontend session can be successful progress when it completes discovery, onboarding, product modeling, visual direction, wireframes, review, or handoff without starting production UI code.
- If frontend memory is not established, substantial frontend work starts with discovery and full onboarding; this applies to the first serious frontend task.
- Established frontend memory means complete product surface, identity, visual references, design-system rules, screen contracts, and onboarding completion evidence exist for the relevant product surface.
- Interview completed is not onboarding completed, design approved, or ready for implementation. Owner Decision Gates must pass before implementation.
- An owner's first answer to onboarding questions is not enough to establish frontend memory. Continue interview, Product Surface Model, visual exploration and feedback, final identity, and design system unless waived.
- Design Identity, Visual Direction Boards, references, and final design-system choices are grounded in owner answers, product evidence, or owner approval.
- First-time frontend onboarding is deep: at least 30 questions in adaptive rounds of 5, followed by an Uncertainty Check and more rounds when needed.
- The agent chooses each round's 5 questions dynamically from product context and prior answers; there is no fixed questionnaire.
- While frontend memory is still not established, name the next onboarding, synthesis, visual exploration, or persistence step.
- For a new site/app or major frontend surface, ask whether the owner wants a lightweight static stack or a framework/UI-library stack unless the repo already decides; this is the Stack Gate.
- Product Surface, Visual Direction, Scope/Completeness, and Final Pre-Implementation Gates require owner confirmation for substantial work.
- Approvals are named and scoped: Product Surface Approval, Visual Direction Approval, Wireframe Approval, and Final Implementation Approval. Implementation starts after Final Implementation Approval for the stated scope.
- After 30 onboarding questions, write an Uncertainty Check covering product scope, stack, data/API, auth, content, visual direction, interactions/states, accessibility/responsive behavior, and success criteria.
- Mutating money, infrastructure, auth, account, deployment, external-service, or destructive actions start from an Action Contract covering actor, permissions, confirmation, exact mutation, runtime truth, audit log, results, recovery, tests, and operator feedback states.
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
- Use proportional design before implementation. Small fixes keep the same phase order with focused artifacts and focused rendered inspection; new screens/redesigns need UX modeling first.
- For a new site/app, major redesign, or substantial new product surface, discover existing product knowledge and Build a Product Surface Model before screen design.
- First inspect existing frontend choices and infer stable decisions. Ask only for unresolved choices.
- If product design identity is not established, run a deep one-time design onboarding before major UI work.
- Visual Direction Boards are picture artifacts plus notes. Use image-generation
  or visual tools for images; HTML fallback output is five separate rendered HTML
  board pages. Each board shows composition, typography, density, surfaces,
  color, component primitives, UI fragments, states, and signature ideas. Owner
  feedback selects, mixes, rejects, or iterates them.
- Before Visual Direction Approval or Wireframe Approval, render and inspect artifacts at desktop and mobile sizes, then present approval-ready artifacts with checked sizes recorded.
- Final responses label delivered scope precisely when mocks, fallback data, disabled controls, placeholder content, or future integration seams are present.
- Final Design Identity, Design System, and implementation follow the required owner gates.
- Persist design identity, system, references, Mermaid flows, wireframes, screen contracts, registry, decisions, and reviews under `docs/frontend/`.
- Substantial implementation ends with a durable review under `docs/frontend/reviews/` covering viewport sizes, screenshots/artifacts, interactions, console status, API/data states, accessibility notes, gaps, and product completeness verdict.
- Before creating components, prefer existing project components, then UI library primitives, then composed primitives; new primitives are last.
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
