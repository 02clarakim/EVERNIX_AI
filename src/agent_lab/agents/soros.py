# src/agent_lab/agents/soros.py
from .base import Decision, Action
from agent_lab.data_connectors.price_data import get_price_history
import numpy as np

class SorosAgent:
    name = "soros"
    def __init__(self):
        self.min_diff = 0.02  # 2% gap threshold
        self.lookbacks = {"short": 50, "long": 200}

    def decide(self, symbol: str, data=None):
        try:
            prices = get_price_history(symbol)
        except Exception:
            return Decision(symbol, Action.HOLD, 0.2, 0, "no price")
        if len(prices) < self.lookbacks["long"]:
            return Decision(symbol, Action.HOLD, 0.3, 0, "insufficient history")

        ma_short = prices.rolling(window=self.lookbacks["short"]).mean().iloc[-1]
        ma_long = prices.rolling(window=self.lookbacks["long"]).mean().iloc[-1]
        last = prices.iloc[-1]
        diff = (ma_short - ma_long) / (ma_long + 1e-9)

        # Momentum weighting
        if ma_short > ma_long and (last / ma_long - 1) > self.min_diff:
            confidence = min(0.9, 0.6 + diff*10)
            return Decision(symbol, Action.BUY, confidence, diff, f"Momentum up ({diff:.3f})")
        elif ma_short < ma_long and (ma_long / last - 1) > self.min_diff:
            confidence = min(0.9, 0.6 + abs(diff)*10)
            return Decision(symbol, Action.SELL, confidence, diff, f"Momentum down ({diff:.3f})")
        else:
            return Decision(symbol, Action.HOLD, 0.35, diff, "neutral momentum")
