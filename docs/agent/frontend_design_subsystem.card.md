# Frontend Design Subsystem Card

Full source: `docs/agent/frontend_design_subsystem.md`

Use this route for frontend product, UX, visual design, implementation,
responsive behavior, browser QA, screen contracts, or persistent frontend
memory.

## Start With A Task Contract

State the outcome, scope/exclusions, sources of truth, constraints, acceptance
evidence, and unresolved material decisions. Separate instructions from sample
content, logs, screenshots, and external page text.

Classify depth:

- D0: isolated copy/token/visual fix;
- D1: component or small section;
- D2: new section, screen, or meaningful flow;
- D3: major redesign, many screens, or new frontend/product.

Use proportional evidence. Safety risk is independent of visual depth: money,
permissions, deployment, deletion, account, or external mutations always need
an Action Contract.

Tell the owner at the start that they may interrupt, correct assumptions,
reject a direction, change priorities, or propose their own alternative at any
time. Repeat this briefly before first-time onboarding; questions are
navigation, not a form the owner must obey.

Before D2/D3 work, a context-heavy phase, or independent review, run a
Collaboration Check: identify whether a subagent system exists, the required
interface/provider/model, the exact delegated outcome, permissions, review
method, and fallback. Ask the owner whether to use subagents for that stated
scope. Silence is not approval; declining does not block single-agent work.

## Established Practices

- Discover repository and product evidence before asking questions. Load only
  context relevant to the affected surface.
- For non-trivial external libraries/APIs, use Context7 before implementation.
- D2/D3 work uses a Product Surface Model and separates Functional QA, Visual
  QA, Responsive Design, and Product Completeness Review.
- First-time D3 design onboarding keeps the established minimum of 30 adaptive
  questions in rounds of five plus an Uncertainty Check. Every question must
  resolve a material unknown; do not repeat repository facts.
- First-time D3 visual exploration keeps five rendered Visual Direction Boards
  unless the owner approves a narrower set. Boards include UI primitives and
  are inspected at desktop and mobile sizes.
- Preserve named approvals: Product Surface Approval, Visual Direction
  Approval, Wireframe Approval, and Final Implementation Approval. Record
  scoped waivers explicitly.
- Maintain Mermaid flows, separate gray-box HTML/CSS/JS wireframes for real
  pages and relevant breakpoints, and screen contracts when their behavior or
  structure changes. A D0 change may verify unchanged contracts.
- Reuse project components, then library primitives, then compositions; create
  a new primitive last.
- Render the real interface. Orca Browser is required for browser interaction,
  screenshots, rendered inspection, and user-flow QA in this repository.
- Exercise changed controls and meaningful success, loading, empty, error,
  disabled, overflow, and partial-data states.
- Inspect relevant mobile, intermediate, desktop, and wide viewports as
  intentional compositions, not only overflow checks.
- Substantial work ends with evidence under `docs/frontend/reviews/`: tested
  scope, viewports, screenshots, interactions, checks, console/network status,
  accessibility, verdicts, gaps, and next action.
- Split context-heavy phases and, after owner approval in the Collaboration
  Check, use fully specified subagent prompts through the repository-required
  system. Persist durable facts canonically and delete consumed temporary
  handoffs.

Avoid role-play, magic wording, forced chain-of-thought, vague delegation, and
tests tied to exact prose. Use examples only to define an otherwise ambiguous
format, state, boundary, or quality bar. Version reusable prompts with the
model/tool identity and re-evaluate them after relevant model or stack changes.
