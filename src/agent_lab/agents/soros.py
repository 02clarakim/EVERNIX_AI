# src/agent_lab/agents/soros.py
from .base import Decision, Action
from agent_lab.data_connectors.price_data import get_price_history
import numpy as np

class SorosAgent:
    name = "soros"

    def __init__(self):
        self.lookbacks = {"short": 15, "medium": 50, "long": 150}
        self.vol_window = 30
        self.breakout_threshold = 0.03  # 3% move
        self.reversal_vol_mult = 1.5

    def decide(self, symbol: str, data=None):
        try:
            prices = get_price_history(symbol)
        except Exception:
            return Decision(symbol, Action.HOLD, 0.2, 0, "no price data")

        if len(prices) < self.lookbacks["long"]:
            return Decision(symbol, Action.HOLD, 0.3, 0, "insufficient history")

        last = prices.iloc[-1]
        ma_short = prices.rolling(self.lookbacks["short"]).mean().iloc[-1]
        ma_long = prices.rolling(self.lookbacks["long"]).mean().iloc[-1]

        returns = prices.pct_change().dropna()
        vol = returns[-self.vol_window:].std()
        avg_vol = returns.std()

        breakout = (last - ma_long)/ma_long
        diff = (ma_short - ma_long)/ma_long
        rationale = []

        # Trend-following & volatility logic
        if breakout > self.breakout_threshold:
            rationale.append(f"Breakout above long MA ({breakout:.3f})")
            confidence = min(0.6 + breakout*5 + vol*2, 0.9)
            return Decision(symbol, Action.BUY, confidence, diff, " | ".join(rationale))

        if breakout < -self.breakout_threshold:
            if vol > self.reversal_vol_mult*avg_vol:
                rationale.append(f"Vol spike reversal ({vol:.3f})")
                confidence = min(0.6 + vol*2, 0.85)
                return Decision(symbol, Action.BUY, confidence, diff, " | ".join(rationale))
            else:
                rationale.append(f"Downtrend below long MA ({breakout:.3f})")
                confidence = min(0.6 + abs(breakout)*5, 0.85)
                return Decision(symbol, Action.SELL, confidence, diff, " | ".join(rationale))

        return Decision(symbol, Action.HOLD, 0.4, diff, "neutral trend")
