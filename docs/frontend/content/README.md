# Frontend Content Package

Store source-grounded production copy here when the repository does not already
have a stronger canonical content source. The package avoids a single
monolithic copy inventory and prevents the same long copy from being repeated
in an inventory, a screen contract, implementation code, and QA evidence.

## Package Shape

Use only the parts that apply:

```text
docs/frontend/content/
|-- index.md                 # compact root coverage index
|-- shared-ui-copy.md        # exact shared chrome, action, and state copy
|-- manifests/               # optional section-level coverage indexes
`-- pages/                   # final page- or screen-local copy
```

An existing canonical content directory, documentation corpus, CMS export,
localization catalog, or production content module may replace `pages/`. In
that case, `index.md` links to the real source rather than copying it here. A
mutable URL, branch name, CMS view, or module path alone is not a pinned
contract: record an immutable export, revision, commit, version, or content
hash that reviewers and implementation can resolve again.

## Coverage Identity And Closure

The approved Product Surface defines stable Content Coverage Keys for every
content-bearing route or screen, meaningful state, global region, and repeated
copy family. A key represents one promised content requirement, not merely a
file or route count. Every expected key must resolve through the package
manifests to exactly one reviewed canonical leaf. A canonical leaf may serve
several consumers only when each consumer has its own explicit mapping to that
same leaf.

Use a transitive manifest chain:

```text
root index -> optional section manifest -> canonical page/content leaf
           -> shared UI copy registry
```

Every parent-to-child edge records the child path or immutable external
identifier, revision, content hash, expected coverage keys, review status, and
review manifest. Every leaf records the Product Surface IDs and Content
Coverage Keys it satisfies. The root publishes aggregate `expected`,
`covered`, `missing`, `duplicate`, `orphan`, and `unreviewed` key counts.
Approval requires zero missing, duplicate, orphan, and unreviewed keys. Counts
prove closure only; they never replace semantic copy review.

## Root Index

Keep `index.md` compact. One row per page, screen, meaningful state group, or
content shard records:

- entry type: section manifest / canonical leaf / shared-copy registry;
- stable content ID;
- Product Surface IDs and Content Coverage Keys;
- route, screen, or state scope;
- exact canonical copy path and heading, key, or anchor;
- page purpose and Messaging Contract reference;
- required sections and minimum depth promised by the approved Product Surface;
- factual source paths;
- shared UI copy IDs and state-copy families used;
- child revision and content hash;
- review manifest path and hash;
- approval status, author context, reviewer context, and verdict.

Large products may split coverage into `manifests/` by product area. The root
index then contains one row per shard and its pinned aggregate counts. Every
section manifest repeats the same edge fields for its canonical leaves and
publishes its own closure counts. Root counts must equal the sum and set union
of child manifests; a reviewer blocks mismatched totals or keys. Do not use
line numbers as durable identity; use stable IDs, paths, headings, keys,
revisions, and content hashes.

## Page-Local Copy

Each page-local file contains the final production wording once, together with
compact metadata:

```md
# Page Or Screen Name

- Content ID:
- Product Surface IDs and Content Coverage Keys:
- Route or state:
- Audience and starting state:
- Intended leaving state:
- Messaging Contract:
- Product and factual sources:
- Required sections and depth:
- Revision and status:
- Parent manifest:

## Route Messaging Contract

- Why this route or state exists:
- Audience:
- Starting user state:
- Intended leaving state:
- Main idea:
- First and later messages:
- Objections to answer:
- Required proof:
- Natural action:
- Generic-copy risks:

## Production Copy

<finished wording in final hierarchy>
```

Finished copy means every required heading, paragraph, example, proof point,
action, and state message is present. An outline, synopsis, ellipsis, placeholder,
sample-only subset, or a heading plus one short paragraph cannot be approved as
finished copy unless that is the literal approved production content.

When the production architecture can render or import Markdown or structured
content directly and wholesale, use these canonical files as inputs and pin the
leaf content hash in the parent manifest. Otherwise give every independently
placed heading, block, example, proof item, action, and state message a stable
block ID or structured key, and map every block ID to one production source
location. Implementation must not rewrite, shorten, expand, or omit approved
copy silently.

## Shared UI Copy

Use `shared-ui-copy.md` only for exact repeated strings or parameterized patterns:
navigation, actions, form labels, validation, loading, empty, error, success,
disabled, overflow, tooltips, badges, dialogs, and accessibility text. Record:

- stable copy ID;
- exact text or bounded pattern;
- variables and grammar rules;
- semantic job and state;
- source or claim boundary;
- consumers;
- revision and review verdict.

Do not place long page prose in the shared registry.

## Copy Approval Gate

P03 produces one compact Copy Approval manifest with:

- Content Package root path, revision, and content hash;
- approved Product Surface revision/hash and route-catalog revision/hash;
- expected, covered, missing, duplicate, orphan, and unreviewed coverage-key
  counts;
- placeholder and unresolved-fact counts;
- shared-copy expected and covered family counts;
- required-depth result for every section manifest;
- author and semantic-review manifest paths, revisions, hashes, and contexts;
- semantic reviewer verdict, stable blockers, and unresolved owner decisions;
- owner decision: pending / approved / rejected / waived / superseded;
- owner decision path/date and exact next phase unlocked.

The owner gate is blocked unless manifest closure passes, every required shard
has a semantic verdict, placeholders are zero, and unresolved facts are either
resolved or explicitly bounded in the presented copy. A count-only, sampled,
or path-only review cannot unlock Copy Approval.

## Authoring And Review

For a large corpus, assign disjoint content shards to independent authors and
reviewers. Authors write the canonical files directly and return compact
manifests. Reviewers read the final copy and its factual sources, then check
completeness, depth, specificity, claim support, voice, actions, and state copy.
They must not reduce review to row counts, line indexes, or placeholder
presence.

A package-level reviewer verifies the transitive root-to-leaf graph and
aggregate closure after shard reviews pass. It checks every expected Content
Coverage Key against the approved Product Surface, rejects missing, duplicate,
orphan, stale-hash, or unreviewed leaves, and signs the Copy Approval manifest.

The phase main reads the compact root index, verdicts, and cited blockers only.
It does not load the full corpus, compose final copy, or repeat the authors' and
reviewers' work.
