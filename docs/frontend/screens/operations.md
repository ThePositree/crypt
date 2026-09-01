# Operations

## Purpose

Teach operator scenarios: dry-run, preflight, Railway deployment concepts,
Telegram notifications, observability, and incident response.

## Primary Action

Choose an operational scenario and understand expected boundaries.

## Information Hierarchy

1. Scenario chooser.
2. Preconditions.
3. What the code path does.
4. Failure/recovery behavior.
5. Related live execution and glossary links.

## Messaging Contract

- Main idea: operations pages explain workflows and failure handling without
  exposing private runtime state.
- Required proof: scenario cards and recovery paths.
- Objections: deployment is not performed by this portal.

## Content And Capability Contract

Coverage includes dry-run, live preflight, Telegram notifications, Railway
runbook concepts, observability, and incident response.

## Interaction Inventory

Scenario filters, accordions, related links, glossary terms, copyable command
concept disabled until implementation contract decides behavior.

## States

normal, scenario selected, warning state, recovery path expanded, dark theme.

## Acceptance Criteria

The page explains operator behavior but does not mutate external systems.
