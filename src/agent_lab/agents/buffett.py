# src/agent_lab/agents/buffett.py
from __future__ import annotations
from typing import Dict
from .base import Agent, Decision, Action
from agent_lab.data_connectors.finnhub_data import fetch_finnhub_fundamentals_single

class BuffettAgent(Agent):
    name = "BuffettAgent"

    def __init__(self, criteria: Dict | None = None):
        self.criteria = criteria or {
            "pe_ratio_max": 20,
            "roe_min": 0.15,
            "debt_to_equity_max": 1.0,
            "target_sectors": [
                "Consumer Defensive","Financial Services",
                "Healthcare","Industrials","Energy"
            ],
        }

    def decide(self, symbol: str) -> Decision:
        row = fetch_finnhub_fundamentals_single(symbol)
        if row is None:
            return Decision(symbol=symbol, action=Action.HOLD, confidence=0.3,
                            score=0, rationale="No data", extras={"agent_name": self.name})

        score, rationale = 0, []

        pe = row.get("pe")
        if pe is not None and pe < self.criteria["pe_ratio_max"]:
            score += 2; rationale.append("P/E OK")
        else: rationale.append("P/E high or NA")

        roe = row.get("roe", 0)
        if roe > self.criteria["roe_min"]:
            score += 2; rationale.append("ROE strong")
        else: rationale.append("ROE weak")

        d2e = row.get("debt_to_equity", 0)
        if d2e < self.criteria["debt_to_equity_max"]:
            score += 1; rationale.append("Debt OK")
        else: rationale.append("Debt high")

        fcf = row.get("free_cashflow", 0)
        if fcf > 0:
            score += 2; rationale.append("FCF positive")
        else: rationale.append("No FCF")

        sector = row.get("sector", "Unknown")
        if sector in self.criteria["target_sectors"]:
            score += 1; rationale.append(f"Sector {sector}")
        else: rationale.append(f"Sector {sector} off-target")

        if score >= 7: action, confidence = Action.BUY, 0.95
        elif score >= 5: action, confidence = Action.BUY, 0.75
        elif score >= 3: action, confidence = Action.HOLD, 0.5
        else: action, confidence = Action.SELL, 0.2

        return Decision(symbol=symbol, action=action, confidence=confidence,
                        score=score, rationale=" | ".join(rationale),
                        extras={"sector": sector, "agent_name": self.name})
