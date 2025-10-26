# src/agent_lab/agents/cathie.py
from .base import Decision, Action
from agent_lab.data_connectors.cache import get_fundamentals
import random

class CathieAgent:
    name = "cathie"

    def __init__(self):
        # Strong bias toward high-growth stocks
        self.min_rev_growth = 0.25
        self.weights = {
            "rev_high": 3.5,
            "rev_mod": 1.5,
            "neg_fcf_tolerance": 1,
            "pe": 0.5,
        }

    def decide(self, symbol: str, data=None):
        row = data or get_fundamentals(symbol)
        if row is None:
            return Decision(symbol, Action.HOLD, 0.2, 0, "no data")

        score = 0
        rationale = []

        # Revenue growth scoring
        rev = row.get("revenue_growth_cagr") or 0
        if rev > 0.35:
            score += self.weights["rev_high"]
            rationale.append(f"Explosive rev growth {rev:.2f}")
        elif rev > self.min_rev_growth:
            score += self.weights["rev_mod"]
            rationale.append(f"Healthy rev growth {rev:.2f}")

        # FCF handling
        fcf = row.get("free_cashflow")
        if fcf and fcf > 0:
            score += 1
            rationale.append("Positive FCF")
        elif rev > 0.35:
            score += self.weights["neg_fcf_tolerance"]
            rationale.append("Tolerates negative FCF for growth")

        # PE consideration
        pe = row.get("pe")
        if pe and pe > 80:
            score -= 0.5
            rationale.append(f"Very high PE {pe:.1f}")
        elif pe and pe < 20:
            score += 0.5
            rationale.append("Undervalued PE")

        # Slight randomization to prevent tie allocations
        confidence = min(0.75 + 0.05*random.random(), 0.9)

        # Decision mapping
        if score >= 3:
            return Decision(symbol, Action.BUY, confidence, score, " | ".join(rationale))
        elif score >= 1.5:
            return Decision(symbol, Action.HOLD, confidence*0.7, score, " | ".join(rationale))
        else:
            return Decision(symbol, Action.SELL, 0.25, score, " | ".join(rationale))
