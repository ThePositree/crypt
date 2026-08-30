# Next.js And Tailwind Portal Baseline

- Date: 2026-08-30
- Status: proposed

## Decision

Use Next.js with TypeScript, App Router, and Tailwind CSS v4. Prefer Server
Components and static generation for documentation content; introduce Client
Components only for search, theme, mobile navigation, and focused playful
interactions. Keep the output compatible with static export unless a later
approved requirement needs a server runtime.

## Rationale

The owner explicitly selected Next.js and Tailwind CSS. App Router provides
durable page/layout structure, while Tailwind supports a custom token-driven
Pocket Field Lab system without adding a component-library identity. Static
generation preserves the original portability and read-only safety goals.

## Consequences

- Next.js, React, Tailwind CSS, PostCSS, TypeScript, and ESLint are the expected
  build dependencies. No remote font, analytics, or content API is required.
- Search uses a generated local index.
- Hosting remains portable when static export is retained.
- The setup follows the current official Next.js App Router and Tailwind CSS
  v4 PostCSS guidance verified on 2026-08-30.
