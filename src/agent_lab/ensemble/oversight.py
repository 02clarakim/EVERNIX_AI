from __future__ import annotations
from typing import Dict, List
from agent_lab.agents.base import Decision, Action

class OversightAgent:
    def __init__(self, agent_weights: Dict[str, float] | None = None, buy_thresh: float = 0.2, sell_thresh: float = -0.2):
        self.weights = agent_weights or {}
        self.buy_thresh = buy_thresh
        self.sell_thresh = sell_thresh

    def combine(self, all_decisions: Dict[str, List[Decision]]) -> Dict[str, Decision]:
        """
        all_decisions: {symbol: [Decision, ...]}
        Returns final Decision per symbol using weighted voting by agent confidence.
        """
        final: Dict[str, Decision] = {}
        for sym, decs in all_decisions.items():
            agg = 0.0
            notes = []
            for d in decs:
                agent_name = (d.extras or {}).get("agent_name", "Unknown")
                w = float(self.weights.get(agent_name, 1.0))
                vote = 1.0 if d.action == Action.BUY else (-1.0 if d.action == Action.SELL else 0.0)
                agg += w * vote * float(d.confidence)
                notes.append(f"{agent_name}:{d.action}({d.confidence:.2f})")
            if   agg > self.buy_thresh:  action = Action.BUY
            elif agg < self.sell_thresh: action = Action.SELL
            else:                        action = Action.HOLD
            final[sym] = Decision(
                symbol=sym, action=action, confidence=min(1.0, abs(agg)), score=agg,
                rationale="; ".join(notes), extras={"agent_votes": len(decs)}
            )
        return final
