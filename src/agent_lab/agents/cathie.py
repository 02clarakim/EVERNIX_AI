# src/agent_lab/agents/cathie.py
from .base import Decision, Action
from agent_lab.data_connectors.cache import get_fundamentals

class CathieAgent:
    name = "cathie"
    def __init__(self):
        # Growth-oriented investor
        self.min_rev_growth = 0.25
        self.weights = {
            "rev_high": 2,
            "rev_mod": 1,
            "fcf": 1,
            "pe": 0.5
        }

    def decide(self, symbol: str, data=None):
        row = data or get_fundamentals(symbol)
        if row is None:
            return Decision(symbol, Action.HOLD, 0.2, 0, "no data")

        score = 0
        rationale = []

        # Revenue growth scoring
        rev = row.get("revenue_growth_cagr") or 0
        if rev > self.min_rev_growth:
            score += self.weights["rev_high"]; rationale.append(f"High rev growth {rev:.2f}")
        elif rev > 0.1:
            score += self.weights["rev_mod"]; rationale.append(f"Moderate rev growth {rev:.2f}")

        # Free cash flow
        fcf = row.get("free_cashflow")
        if fcf and fcf > 0:
            score += self.weights["fcf"]; rationale.append("Positive FCF")

        # Optional: slight penalty if PE extremely high
        pe = row.get("pe")
        if pe and pe > 50:
            score -= self.weights["pe"]; rationale.append(f"High PE {pe:.1f}")

        # Decision
        if score >= 2:
            return Decision(symbol, Action.BUY, 0.75, score, " | ".join(rationale))
        elif score == 1:
            return Decision(symbol, Action.HOLD, 0.45, score, " | ".join(rationale))
        else:
            return Decision(symbol, Action.SELL, 0.2, score, " | ".join(rationale))
