import json

from backtester.strategies.liquidity_hunter import LiquidityHunter

with open("strategies/liq_hunter_v1.json", "r") as f:
    params = json.load(f)["params"]

print(LiquidityHunter(params).generate_pine_script())
