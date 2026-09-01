# Architecture

## Purpose

Describe boundaries between data, engines, aggregators, backtester, execution,
runtime, exchange, and sinks.

## Primary Action

Inspect module relationships and open a subsystem.

## Information Hierarchy

1. Architecture map.
2. Component responsibilities.
3. Contracts and invariants.
4. Extension seams.
5. Failure modes.

## Messaging Contract

- Starting user state: reader knows the project exists but not its boundaries.
- Intended leaving state: reader knows where each responsibility belongs.
- Main idea: decision logic should stay shared and pure where possible, while
  runtime/exchange effects stay isolated.
- Required proof: boundary map and extension rules.
- Objections: explain that runtime config beats prose for live execution.

## Content And Capability Contract

Coverage includes engines, decision filters, aggregators, backtester,
execution, runtime, exchange clients, sinks, data store, and config.

## Interaction Inventory

Architecture diagram node selection, overview/deep tabs, contract accordions,
related glossary links, recipe links.

## States

selected component, partial-data explanation, overflow diagram, dark theme.

## Acceptance Criteria

No page copy implies that docs override runtime config or exchange truth.
