# Promoted router: PineScript median-DD trend-structure 180d

**Router id:** `pinescript_median_dd_trend_structure_180d_exact_hold60_margin0p5`  
**Search row:** `router_v2_2687609`  
**Archived:** 2026-06-24  
**Reason:** owner_promoted  
**Strategy:** `strategies/archive/router_v2_2687609.json`

## Logic

The router compares all six archived strategies using completed prior rolling
labels:

- 180-day lookback;
- exact PineScript trend + SMC structure state;
- median return minus drawdown score;
- at least 10 matching samples;
- minimum 60-day hold;
- switch margin 0.5 points.

It always selects one strategy and never selects cash.

## Evidence

Rolling-label search:

- median offset return: +293.09%;
- minimum offset return: +211.29%;
- worst offset DD: -9.62%.

Continuous archived-trade replay for 2025:

- final capital: $22,504.42 from $10,000;
- return: +125.04%;
- four months at or above +15%;
- no losing months;
- no monthly DD breach;
- worst monthly DD: -9.66%;
- 359 trades;
- peak locked margin: 14.01%.

The mandate verdict is still `discard` because eight months remain below the
15% floor. The owner explicitly promoted it into a normal composite strategy
for full-period validation.

## Implementation

`promoted_router` generates all six nested strategy signal streams, reconstructs
completed rolling labels, selects one nested strategy, and emits its signal
through the standard `ExecutionSim`.

No special router backtest command is used.
