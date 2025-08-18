from __future__ import annotations
from typing import List, Tuple
import pandas as pd
from datetime import date
from .base import Agent, Decision, Action

class CongressAgent(Agent):
    name = "CongressAgent"

    def __init__(self, buy_thresh_usd: float = 10000, sell_thresh_usd: float = 10000, decay_half_life_days: float = 30):
        self.buy_thresh = buy_thresh_usd
        self.sell_thresh = sell_thresh_usd
        self.half_life = decay_half_life_days

    def _decay(self, days: float) -> float:
        import math
        return 0.5 ** (days / max(self.half_life, 1e-9))

    def decide(self, asof: date, universe: List[str], features: pd.DataFrame) -> Tuple[List[Decision], pd.DataFrame]:
        """
        Expects features with columns: ['recent_congress_buy_usd', 'recent_congress_sell_usd', 'days_since_disclosure']
        """
        decisions: List[Decision] = []
        table_rows = []

        for sym in universe:
            if sym not in features.index:
                continue
            row = features.loc[sym]
            buy_amt = float(row.get("recent_congress_buy_usd", 0) or 0)
            sell_amt = float(row.get("recent_congress_sell_usd", 0) or 0)
            days = float(row.get("days_since_disclosure", 90) or 90)
            conf = self._decay(days)
            rationale = []
            
            if buy_amt >= self.buy_thresh and buy_amt > sell_amt:
                act = Action.BUY; score = +1; rationale.append(f"Congress BUY ${buy_amt:,.0f}")
            elif sell_amt >= self.sell_thresh and sell_amt > buy_amt:
                act = Action.SELL; score = -1; rationale.append(f"Congress SELL ${sell_amt:,.0f}")
            else:
                act = Action.HOLD; score = 0; rationale.append("No strong disclosure")
                conf *= 0.5

            decisions.append(Decision(
                symbol=sym, action=act, confidence=min(1.0, conf), score=score,
                rationale=" | ".join(rationale),
                extras={"asof": str(asof), "agent_name": self.name}
            ))

            table_rows.append({
                "symbol": sym,
                "score": score,
                "decision": act.name,
                "confidence": min(1.0, conf),
                "justification": " | ".join(rationale),
                "buy_amount": buy_amt,
                "sell_amount": sell_amt,
                "days_since": days
            })

        table = pd.DataFrame(table_rows).set_index("symbol")
        return decisions, table