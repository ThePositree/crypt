# Visual References Interpretation

Status: no visual references selected yet.
Revision: 0

Persist selected and rejected visual direction boards here after frontend
design onboarding or task-specific exploration.

Visual Direction Boards are generated raster images only. HTML/CSS/JavaScript
pages, SVGs, and screenshots of coded pages are not board artifacts and cannot
be used as a fallback. When raster generation is unavailable, Visual Direction
Approval remains blocked.

Use this format:

```text
Board or Reference Name - PRIMARY / POSITIVE REFERENCE / NEGATIVE REFERENCE
SOURCE:
- path or URL

MODEL/TOOL AND DATE:
- value

IMMUTABLE INPUT:
- revision, content hash, dimensions, and capture/generation time
- desktop and mobile product-frame bounds

LIKE:
- property

AVOID:
- property

DO NOT COPY:
- brand, composition, or product-specific element

LOCAL PRODUCT PRINCIPLE:
- principle supported by this reference

AUTHORITY:
- explicit owner decision / observed image property / reviewed inference

SIGNATURE TRAIT MATRIX:
- image region or crop / production rule / forbidden counterexample / observable
  pass condition

VISIBLE PRELIMINARY IDENTITY EVIDENCE:
- composition, metaphor, signature trait, density, imagery/illustration, and
  component styling visibly demonstrated in the raster itself

APPROVAL:
- pending / approved / rejected / mixed
```

The translation author and independent image-capable reviewer must open the
actual raster. Notes, metadata, or prior descriptions alone are not visual
evidence. Do not turn incidental generated details into owner requirements.
When multiple boards are mixed, create one final combined raster with its own
revision and hash; downstream work receives that single selected reference.

Store positive visual assets in `docs/frontend/visual-references/positive/` and
negative visual assets in `docs/frontend/visual-references/negative/` when such
assets exist.
