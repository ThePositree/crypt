# Data

## Purpose

Explain how market data is loaded, stored, normalized, and passed into
strategies and backtests.

## Primary Action

Follow the data flow into strategy and backtester pages.

## Information Hierarchy

1. Data sources and candle boundaries.
2. Store and loader responsibilities.
3. Closed-candle/no-look-ahead rules.
4. Missing-data behavior.
5. Extension recipes.

## Messaging Contract

- Main idea: data availability and candle boundaries control signal quality.
- Required proof: data-flow diagram and no-look-ahead invariant.
- Objections: missing data must not be silently assumed.

## Content And Capability Contract

Coverage includes ingestion, storage, context, data loader, candle timeframe,
closed-candle use, and neutral/blocked behavior for missing data.

## Interaction Inventory

Data-flow steps, invariant accordions, recipe expansion, glossary links.

## States

normal, missing data example, partial data, error explanation, dark theme.

## Acceptance Criteria

The page clearly states that indicators and features use closed candles only.
