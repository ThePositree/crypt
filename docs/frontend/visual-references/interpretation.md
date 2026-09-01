# Visual References Interpretation

Status: visual direction approved.
Revision: 1

Persist selected and rejected visual direction boards here after frontend
design onboarding or task-specific exploration.

Use this format:

```text
Board or Reference Name - PRIMARY / POSITIVE REFERENCE / NEGATIVE REFERENCE
SOURCE:
- path or URL

MODEL/TOOL AND DATE:
- value

LIKE:
- property

AVOID:
- property

DO NOT COPY:
- brand, composition, or product-specific element

LOCAL PRODUCT PRINCIPLE:
- principle supported by this reference

APPROVAL:
- pending / approved / rejected / mixed
```

Store positive visual assets in `docs/frontend/visual-references/positive/` and
negative visual assets in `docs/frontend/visual-references/negative/` when such
assets exist.

## Visual Direction Boards

Pastel Lab Map - CANDIDATE
SOURCE:
- `docs/frontend/visual-references/boards/board-01-pastel-lab-map.png`

MODEL/TOOL AND DATE:
- Built-in `image_gen` tool, 2026-09-01.

LIKE:
- Clear docs application frame with left navigation, global search, system
  map, mobile preview, guide step, glossary result, and visible component
  states.

AVOID:
- The central map is functional but less immersive than the atlas/town
  directions.

DO NOT COPY:
- Any generated pseudo-performance output or example command should be replaced
  with curated project-accurate copy during implementation.

LOCAL PRODUCT PRINCIPLE:
- Start from a useful docs app surface, then add mascot warmth and pastel
  technical diagrams.

APPROVAL:
- pending

Notebook Garden - CANDIDATE
SOURCE:
- `docs/frontend/visual-references/boards/board-02-notebook-garden.png`

MODEL/TOOL AND DATE:
- Built-in `image_gen` tool, 2026-09-01.

LIKE:
- Strong lo-fi notebook personality, abstract mascot helpers, soft hand-drawn
  islands, and a good balance between role journeys and technical docs.

AVOID:
- Generated version label `v1.4.0` is only an example; final implementation
  should use the approved semver labels.

DO NOT COPY:
- Do not copy exact generated labels or any invented community/help promises.

LOCAL PRODUCT PRINCIPLE:
- Make dense research concepts feel hand-curated and approachable without
  lowering the technical depth.

APPROVAL:
- pending

Block Kit Framework - CANDIDATE
SOURCE:
- `docs/frontend/visual-references/boards/board-03-block-kit-framework.png`

MODEL/TOOL AND DATE:
- Built-in `image_gen` tool, 2026-09-01.

LIKE:
- Best fit for a major framework-style docs portal: crisp navigation, table of
  contents, modular architecture nodes, source-linked proof, and clear
  component states.

AVOID:
- It is less whimsical than the strongest mascot/map options; final direction
  may need warmer mascots or illustrated page moments.

DO NOT COPY:
- Replace invented API endpoints and install commands with curated project
  truth.

LOCAL PRODUCT PRINCIPLE:
- Use familiar framework-docs structure as the usability base, then layer
  pastel and mascot identity onto it.

APPROVAL:
- pending

Strategy Atlas - CANDIDATE
SOURCE:
- `docs/frontend/visual-references/boards/board-04-strategy-atlas.png`

MODEL/TOOL AND DATE:
- Built-in `image_gen` tool, 2026-09-01.

LIKE:
- Strongest "home as map" interpretation with journey progress, related docs,
  guide cards, search states, version selector, and public risk footer.

AVOID:
- Explorer characters are less abstract than the owner requested; final mascot
  system should become more abstract if this direction is selected.

DO NOT COPY:
- Do not copy the exact atlas region names unless they are approved as public
  information architecture.

LOCAL PRODUCT PRINCIPLE:
- The first viewport should teach the whole system as a clickable landscape
  before sending readers into detailed pages.

APPROVAL:
- pending

Docs Town - CANDIDATE
SOURCE:
- `docs/frontend/visual-references/boards/board-05-docs-town.png`

MODEL/TOOL AND DATE:
- Built-in `image_gen` tool, 2026-09-01.

LIKE:
- Strongest "huge public docs platform" feeling: map, curated page tiles,
  backend search modal, versioning, guide pattern, mobile preview, components,
  and cute abstract helpers.

AVOID:
- The page headline and small tagline include slightly broad generated copy;
  final copy should stay precise and avoid implying trading advice.

DO NOT COPY:
- Do not copy example commands, output values, or any text that suggests
  confidence/trading action without source-backed context.

LOCAL PRODUCT PRINCIPLE:
- Treat `crypt` as a public knowledge town: every major subsystem has a visible
  place, route, and role in the research workflow.

APPROVAL:
- approved by owner on 2026-09-01 as the full visual basis: "берем все из 5"

## Approved Visual Direction

- Selected board: Docs Town.
- Source path:
  `docs/frontend/visual-references/boards/board-05-docs-town.png`.
- Owner approval: 2026-09-01, "берем все из 5".
- Implementation consequences: use Docs Town as the primary direction for the
  public docs portal: a cute lo-fi pastel docs-town map, abstract helper
  mascots, large interactive first-viewport map, left topic navigation, top
  backend search, semver selector, mobile-first compressed map, curated page
  tiles, guide pattern cards, component states, and a dedicated risk callout.
- Required translation: generated board text, commands, output, and values are
  visual placeholders only. Production copy must be curated from repository
  truth and avoid trading advice, private runtime data, and performance
  promises.

## Visual Board Inspection

- Desktop evidence: each board is a 1536x1024 raster UI showcase inspected
  locally on 2026-09-01.
- Mobile evidence: each board includes a mobile preview state inside the
  rendered artifact.
- Component/state coverage: boards collectively show navigation, search,
  map-node states, guide steps, version selector, glossary/reference cards,
  risk callouts, copy-button states, loading, empty, error, hover, selected,
  disabled, and responsive examples.
- Known limitations: generated text and commands are visual placeholders only;
  production implementation must replace them with curated repository-accurate
  public content. No board is approved until the owner selects, mixes, rejects,
  or requests iteration.
