# Visual Direction Artifacts

This role contract covers P04 Visual Direction Boards and P05 Selected Visual
Direction Translation. The P04 author receives approved onboarding,
product-surface, content, and factual inputs and first creates Preliminary
Identity before generating boards. Its reviewer receives that finished identity
revision with the five immutable boards. P05 authors and reviewers receive the
approved Preliminary Identity and selected raster inputs. Every role receives
only its factual constraints, deliverable paths, and this file; it does not need
the full frontend subsystem.

## P04 Boards

Generate exactly five meaningfully different raster boards. HTML, CSS,
JavaScript, SVG, locally coded screenshots, and prose are not fallback board
artifacts. Each board includes identifiable desktop and mobile product frames,
representative production-relevant components, applicable states, hierarchy,
density, typography, geometry, surfaces, color, and imagery/illustration logic.
Do not invent product facts, commands, integrations, or capabilities.

Use immutable paths and record revision, hash, dimensions, generation time,
desktop/mobile frame bounds, author context, and product hypothesis. If the
owner selects several boards, generate one merged raster as the only downstream
selected reference.

An independent image-capable reviewer opens every actual raster and checks
blank output, clipping, overlap, legibility, composition, component/state
coverage, desktop/mobile evidence, factual grounding, and visible Preliminary
Identity. Metadata or notes alone cannot pass. The review records immutable
input identity, report path/hash, verdict, and stable blockers.

## P05 Translation

The write-scoped Visual-System Author opens the selected raster and records its
immutable identity and frame bounds, a finite Signature Traits Matrix, required
production rules, mood-only properties, forbidden literal copying, component
families, responsive behavior, and asset needs. Incidental generated details
do not become owner requirements.

When faithful reproduction needs custom raster, typography, icon, illustration,
texture, diagram, or character material, create the minimal UI Fidelity Asset
Seed defined in `docs/frontend/assets/README.md`. Otherwise require an explicit
independent non-applicability verdict.

A separate image-capable reviewer opens the raster and translation, compares
them holistically before checking the matrix, rejects missing signature traits
or invented constraints, and verifies the seed or its non-applicability. The
phase main consumes only compact manifests, verdicts, and cited blockers.
