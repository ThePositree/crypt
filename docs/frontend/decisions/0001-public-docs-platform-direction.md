# Public Docs Platform Direction

- Date: 2026-09-01
- Status: approved
- Affected artifact revisions: Product Surface Model revision 1, Messaging
  revision 1, Design Identity revision 1, Design System revision 1

## Context

The repository has no active frontend application. The owner requested a
production-ready public docs platform under `site/` that explains how the
Python code works for developers and crypto-native readers. The site should be
curated, not a direct rendering of existing Markdown files.

## Decision

Build a large versioned Next.js and Tailwind CSS docs portal with an
interactive system-map home page, dual topic and journey navigation, backend
search over curated public content, guide pages with command/output/explanation
steps, a glossary, and a dedicated Risk & Limits section.

The visual direction is a cute lo-fi pastel research desk with abstract mascot
helpers. Public live-execution content explains neutral architecture and
trust boundaries, not private live-money details.

## Consequences

The first implementation requires D3 frontend artifacts before production code:
approved product surface, visual direction boards, flows, rendered wireframes,
screen contracts, and final implementation approval or scoped waiver.

Search needs an API route and a curated index. Versioning must be part of the
information architecture from the first release.

## Validation Or Revisit Trigger

Revisit if the owner changes the target audience, makes the site private,
removes backend search, chooses a different stack, or approves publishing
specific live-money/runtime details.

## Approval

Approved by owner on 2026-09-01 with "делай" after the Product Surface Model
revision 1 and proposed direction were presented.
