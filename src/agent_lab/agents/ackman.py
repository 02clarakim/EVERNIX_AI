from __future__ import annotations
from typing import Dict, Callable, Optional
from .base import Agent, Decision, Action
from agent_lab.data_connectors.cache import get_fundamentals

# class AckmanAgent(Agent):
#     name = "AckmanAgent"

#     def __init__(self, criteria: Dict | None = None):
#         self.criteria = criteria or {
#             "pe_ratio_max": 30,          
#             "roe_min": 0.20,             
#             "roic_min": 0.15,            
#             "ev_ebitda_max": 18,         
#             "debt_to_equity_max": 1.5,   
#             "fcf_min": 0,                
#             "target_sectors": [
#                 "Consumer Cyclical", "Technology", "Healthcare", "Industrials"
#             ],
#             "weights": {
#                 "pe": 2, "roe": 3, "roic": 2, "ev_ebitda": 2,
#                 "debt": 1, "fcf": 2, "sector": 1,
#             },
#         }

#     def _score_metric(
#         self,
#         score: int,
#         rationale: list[str],
#         metric_name: str,
#         value,
#         weight: int,
#         condition: Callable[[float], bool],
#         msg_ok: str,
#         msg_bad: str
#     ) -> int:
#         if value is None:
#             rationale.append(f"{metric_name} missing")
#             return score
#         try:
#             if condition(value):
#                 score += weight
#                 rationale.append(f"{msg_ok} ({value:.2f})")
#             else:
#                 rationale.append(f"{msg_bad} ({value:.2f})")
#         except Exception:
#             rationale.append(f"{metric_name} invalid")
#         return score

#     def decide(self, symbol: str, data: Optional[dict] = None) -> Decision:
#         """
#         Accept `data` (pre-fetched fundamentals) to avoid per-symbol API calls.
#         """
#         row = data or get_fundamentals(symbol)
#         if row is None:
#             return Decision(
#                 symbol=symbol,
#                 action=Action.HOLD,
#                 confidence=0.3,
#                 score=0,
#                 rationale="No data",
#             )

#         score, rationale = 0, []
#         w = self.criteria["weights"]

#         # --- Valuation ---
#         score = self._score_metric(score, rationale, "P/E", row.get("pe"), w["pe"],
#                                    lambda v: v < self.criteria["pe_ratio_max"],
#                                    "P/E OK", "P/E high")

#         score = self._score_metric(score, rationale, "EV/EBITDA", row.get("ev_ebitda"), w["ev_ebitda"],
#                                    lambda v: v and v < self.criteria["ev_ebitda_max"],
#                                    "EV/EBITDA fair", "EV/EBITDA high")

#         # --- Profitability ---
#         score = self._score_metric(score, rationale, "ROE", row.get("roe"), w["roe"],
#                                    lambda v: v > self.criteria["roe_min"], "ROE strong", "ROE weak")

#         score = self._score_metric(score, rationale, "ROIC", row.get("roic"), w["roic"],
#                                    lambda v: v > self.criteria["roic_min"], "ROIC strong", "ROIC weak")

#         # --- Leverage ---
#         score = self._score_metric(score, rationale, "Debt/Equity", row.get("debt_to_equity"), w["debt"],
#                                    lambda v: v < self.criteria["debt_to_equity_max"], "Debt OK", "Debt high")

#         # --- Free Cash Flow ---
#         score = self._score_metric(score, rationale, "Free Cash Flow", row.get("free_cashflow"), w["fcf"],
#                                    lambda v: v > self.criteria["fcf_min"], "FCF positive", "No FCF")

#         # --- Sector Preference ---
#         sector = row.get("sector", "Unknown")
#         if sector in self.criteria["target_sectors"]:
#             score += w["sector"]
#             rationale.append(f"Sector {sector} target")
#         else:
#             rationale.append(f"Sector {sector} off-target")

#         # --- Decision mapping ---
#         if score >= 11:
#             action, confidence = Action.BUY, 0.95
#         elif score >= 8:
#             action, confidence = Action.BUY, 0.75
#         elif score >= 5:
#             action, confidence = Action.HOLD, 0.5
#         else:
#             action, confidence = Action.SELL, 0.2

#         return Decision(
#             symbol=symbol,
#             action=action,
#             confidence=confidence,
#             score=score,
#             rationale=" | ".join(rationale),
#         )

class AckmanAgent:
    name = "ackman"
    def __init__(self):
        self.min_score_to_buy = 2
        self.max_holding_days = 30

    def decide(self, symbol, data=None):
        row = data or get_fundamentals(symbol)
        if row is None:
            return Decision(symbol, Action.HOLD, 0.2, 0, "no data")

        score = 0
        rationale = []

        if row.get("roe", 0) > 0.15:
            score += 1; rationale.append("High ROE")
        if row.get("roic", 0) > 0.12:
            score += 1; rationale.append("High ROIC")
        if row.get("debt_to_equity", 1) < 0.5:
            score += 1; rationale.append("Low leverage")
        if row.get("recent_insider_buy", 0) > 0:
            score += 1; rationale.append("Insider buying")

        # Confidence scales with score
        confidence = min(0.3 + 0.15 * score, 0.9)

        if score >= self.min_score_to_buy:
            return Decision(symbol, Action.BUY, confidence, score, " | ".join(rationale))
        elif score >= 1:
            return Decision(symbol, Action.HOLD, 0.4, score, " | ".join(rationale))
        else:
            return Decision(symbol, Action.SELL, 0.25, score, " | ".join(rationale))
