from __future__ import annotations
from typing import Dict
import pandas as pd
from .base import Agent, Decision, Action
from agent_lab.api import finnhub_data  # <-- fetch fundamentals

class AckmanAgent(Agent):
    name = "AckmanAgent"

    def __init__(self, criteria: Dict | None = None):
        self.criteria = criteria or {
            "pe_ratio_max": 30,
            "roe_min": 0.20,
            "debt_to_equity_max": 1.5,
            "free_cashflow_positive": True,
            "target_sectors": [
                "Consumer Cyclical", "Technology", "Healthcare", "Industrials"
            ],
        }

    def decide(self, symbol: str) -> Decision:
        """Decide BUY/HOLD/SELL for a single symbol using Finnhub data"""
        row = finnhub_data.fetch_finnhub_fundamentals_single(symbol)
        if row is None:
            return Decision(
                symbol=symbol,
                action=Action.HOLD,
                confidence=0.3,
                score=0,
                rationale="No data available",
                extras={"agent_name": self.name}
            )

        score, rationale = 0, []

        pe = row.get("pe")
        if pd.notna(pe) and pe < self.criteria["pe_ratio_max"]:
            score += 2; rationale.append("P/E OK")
        else: rationale.append("P/E high/NA")

        roe = row.get("roe", 0)
        if roe > self.criteria["roe_min"]:
            score += 2; rationale.append("ROE strong")
        else: rationale.append("ROE weak")

        d2e = row.get("debt_to_equity", 0)
        if d2e < self.criteria["debt_to_equity_max"]:
            score += 1; rationale.append("Debt manageable")
        else: rationale.append("Debt high")

        fcf = row.get("free_cashflow", 0)
        if fcf > 0:
            score += 2; rationale.append("FreeCF positive")
        else: rationale.append("No FreeCF")

        sector = row.get("sector", "Unknown")
        if sector in self.criteria["target_sectors"]:
            score += 1; rationale.append(f"Sector: {sector}")
        else: rationale.append(f"Sector: {sector} off-target")

        if score >= 7:
            action, confidence = Action.BUY, 0.95
        elif score >= 5:
            action, confidence = Action.BUY, 0.75
        elif score >= 3:
            action, confidence = Action.HOLD, 0.50
        else:
            action, confidence = Action.SELL, 0.20

        return Decision(
            symbol=symbol,
            action=action,
            confidence=confidence,
            score=score,
            rationale=" | ".join(rationale),
            extras={"sector": sector, "agent_name": self.name}
        )
