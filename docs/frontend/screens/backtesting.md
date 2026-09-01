# Backtesting

## Purpose

Explain exact backtests, simulation contracts, regression checkpoints, and
parity with live behavior.

## Primary Action

Learn how to validate or extend backtesting behavior.

## Information Hierarchy

1. Backtester role.
2. Execution simulation.
3. Warmup versus accounting windows.
4. Regression checkpoints.
5. Parity and failure modes.

## Messaging Contract

- Main idea: backtests are engineering evidence and must avoid look-ahead and
  accounting drift.
- Required proof: checkpoint and validation concepts, not result dashboards.
- Objections: no historical result display in the portal.

## Content And Capability Contract

Coverage includes runner, tester, execution simulation, fee/risk/margin/TP
policies, regression docs, and `--load-from` warmup concept.

## Interaction Inventory

Step diagrams, validation recipe accordions, contract list, glossary links.

## States

normal, checkpoint selected, validation error explanation, overflow code
concept block, dark theme.

## Acceptance Criteria

The page explains validation behavior without showing performance results.
