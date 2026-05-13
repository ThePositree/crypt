# Engine: <name>

## Purpose

One paragraph: which "trader view" this engine models and why it deserves
to be in the ensemble.

## Inputs

What `EvaluationContext` fields it reads. Note required vs optional.

## Output (`Signal`)

- `engine`: `"<name>"`
- `direction`: bullish / bearish / neutral — when
- `strength`: how `[-1, +1]` is mapped from raw measurements
- `confidence`: how it is computed
- `rationale`: which bullets are always emitted

## Logic

Pseudo-code, indicator parameters, thresholds. Be specific — this is the
contract.

## Edge cases

What happens when data is missing or extreme.

## Tests

Synthetic-data scenarios the unit tests must cover.

## Known weaknesses

The honest list. This is *not* a hype document.
