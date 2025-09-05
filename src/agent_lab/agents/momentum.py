# from __future__ import annotations
# from typing import List, Tuple
# import pandas as pd
# from .base import Agent, Decision, Action
# from agent_lab.data_connectors.finnhub_data import fetch_finnhub_price_data  # implement as needed

# class MomentumAgent(Agent):
#     name = "MomentumAgent"

#     def __init__(self, lookback_fast=50, lookback_slow=200):
#         self.fast = lookback_fast
#         self.slow = lookback_slow

#     def decide(self, symbol: str) -> Decision:
#         # fetch MA data from Finnhub
#         ma_data = fetch_finnhub_price_data(symbol, self.fast, self.slow)
#         ma_f, ma_s = ma_data.get("ma_fast"), ma_data.get("ma_slow")
#         score, rationale = 0, []

#         if ma_f is not None and ma_s is not None:
#             if ma_f > ma_s:
#                 score += 1; action, conf = Action.BUY, 0.65; rationale.append("MA fast>slow")
#             elif ma_f < ma_s:
#                 score -= 1; action, conf = Action.SELL, 0.65; rationale.append("MA fast<slow")
#             else:
#                 action, conf = Action.HOLD, 0.5; rationale.append("MA equal")
#         else:
#             action, conf = Action.HOLD, 0.5; rationale.append("MA NA")

#         return Decision(symbol=symbol, action=action, confidence=conf,
#                         score=score, rationale=" | ".join(rationale),
#                         extras={"agent_name": self.name})
