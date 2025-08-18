from __future__ import annotations
from typing import Dict, List, Tuple
import pandas as pd
from datetime import date
from .base import Agent, Decision, Action

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

    def decide(self, asof: date, universe: List[str], features: pd.DataFrame) -> Tuple[List[Decision], pd.DataFrame]:
        decisions: List[Decision] = []
        table_rows = []

        for sym in universe:
            if sym not in features.index:
                continue
            row = features.loc[sym]
            score, why = 0, []

            pe = row.get("pe")
            if pd.notna(pe) and pe < self.criteria["pe_ratio_max"]:
                score += 2; why.append("P/E OK")
            else: why.append("P/E high/NA")

            roe = row.get("roe", 0) or 0
            if roe > self.criteria["roe_min"]:
                score += 2; why.append("ROE strong")
            else: why.append("ROE weak")

            d2e = row.get("debt_to_equity", 0) or 0
            if d2e < self.criteria["debt_to_equity_max"]:
                score += 1; why.append("Debt manageable")
            else: why.append("Debt high")

            fcf = row.get("free_cashflow", 0) or 0
            if fcf > 0:
                score += 2; why.append("FreeCF positive")
            else: why.append("No FreeCF")

            sector = row.get("sector", "Unknown")
            if sector in self.criteria["target_sectors"]:
                score += 1; why.append(f"Sector {sector}")
            else: why.append(f"Sector {sector} off")

            if score >= 7: action, conf = Action.BUY, 0.95
            elif score >= 5: action, conf = Action.BUY, 0.75
            elif score >= 3: action, conf = Action.HOLD, 0.50
            else:            action, conf = Action.SELL, 0.20

            decisions.append(Decision(
                symbol=sym,
                action=action,
                confidence=conf,
                score=score,
                rationale=" | ".join(why),
                extras={"sector": sector, "asof": str(asof), "agent_name": self.name}
            ))

            table_rows.append({
                "symbol": sym,
                "score": score,
                "decision": action.name,
                "confidence": conf,
                "justification": " | ".join(why),
                "sector": sector
            })

        table = pd.DataFrame(table_rows).set_index("symbol")
        return decisions, table
