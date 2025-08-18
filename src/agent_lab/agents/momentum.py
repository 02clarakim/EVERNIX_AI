from __future__ import annotations
from typing import List, Tuple
import pandas as pd
from datetime import date
from .base import Agent, Decision, Action

class MomentumAgent(Agent):
    name = "MomentumAgent"

    def __init__(self, lookback_fast: int = 50, lookback_slow: int = 200):
        self.fast = lookback_fast
        self.slow = lookback_slow

    def decide(self, asof: date, universe: List[str], features: pd.DataFrame) -> Tuple[List[Decision], pd.DataFrame]:
        """
        Expects features containing rolling averages:
        columns: [ma_fast, ma_slow], index: symbols
        """
        decisions: List[Decision] = []
        table_rows = []

        for sym in universe:
            if sym not in features.index:
                continue
            row = features.loc[sym]
            ma_f = row.get("ma_fast")
            ma_s = row.get("ma_slow")
            score, why = 0, []
            
            if pd.notna(ma_f) and pd.notna(ma_s):
                if ma_f > ma_s:
                    score += 1; action, conf = Action.BUY, 0.65; why.append("MA fast>slow")
                elif ma_f < ma_s:
                    score -= 1; action, conf = Action.SELL, 0.65; why.append("MA fast<slow")
                else:
                    action, conf = Action.HOLD, 0.5; why.append("MA equal")
            else:
                action, conf = Action.HOLD, 0.5; why.append("MA NA")

            decisions.append(Decision(
                symbol=sym, action=action, confidence=conf, score=score,
                rationale=" | ".join(why),
                extras={"asof": str(asof), "agent_name": self.name}
            ))

            table_rows.append({
                "symbol": sym,
                "score": score,
                "decision": action.name,
                "confidence": conf,
                "justification": " | ".join(why)
            })

        table = pd.DataFrame(table_rows).set_index("symbol")
        return decisions, table