# Live Execution

## Purpose

Explain live OKX execution architecture and safety boundaries without secrets
or runtime values.

## Primary Action

Understand the live execution path and trust boundaries.

## Information Hierarchy

1. Live execution role.
2. Runtime config truth.
3. Exchange sync and order client boundaries.
4. Risk base and position state.
5. Notifications and reconciliation.

## Messaging Contract

- Main idea: live behavior is governed by loaded runtime config and exchange
  state, while the portal explains architecture only.
- Required proof: trust-boundary diagram and scenario cards.
- Objections: no live account values, secrets, or runtime result display.

## Content And Capability Contract

Coverage includes execution runner, executor, OKX order client, exchange sync,
position state, risk calculator, fill classifier, notifications, and runtime
preflight concepts.

## Interaction Inventory

Trust-boundary tabs, scenario accordions, signal journey links, glossary links.

## States

normal, dry-run scenario, blocked-entry explanation, exchange-error recovery,
dark theme.

## Acceptance Criteria

The page never implies that public docs are the source of live money truth.
