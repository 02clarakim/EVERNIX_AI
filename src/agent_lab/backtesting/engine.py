from __future__ import annotations
import pandas as pd
from typing import Dict, Callable
from agent_lab.agents.base import Decision, Action

class BacktestEngine:
    def __init__(self, prices: pd.DataFrame, cost_bps: float = 5.0):
        self.prices = prices.sort_index()
        self.cost = cost_bps / 1e4

    def run(self, daily_decider: Callable[[pd.Timestamp], Dict[str, Decision]], cash: float = 1_000_000.0):
        positions = {sym: 0.0 for sym in self.prices.columns}
        cash_bal = cash
        equity_curve = []
        for dt, row in self.prices.iterrows():
            px = row
            # Get today's decisions
            decs = daily_decider(dt)
            # naive target: equal-weight BUY symbols
            buy_syms = [s for s, d in decs.items() if d.action == Action.BUY and pd.notna(px.get(s))]
            w = (1.0 / len(buy_syms)) if buy_syms else 0.0
            port_val = cash_bal + sum(positions[s] * px[s] for s in positions if pd.notna(px.get(s)))
            for s in positions:
                target_shares = 0.0
                if s in buy_syms and pd.notna(px.get(s)):
                    target_shares = (port_val * w) / max(float(px[s]), 1e-9)
                trade = target_shares - positions[s]
                if pd.notna(px.get(s)) and abs(trade) > 0:
                    cash_bal -= trade * float(px[s]) * (1 + self.cost)
                    positions[s] += trade
            port_val = cash_bal + sum(positions[s] * px[s] for s in positions if pd.notna(px.get(s)))
            equity_curve.append((dt, port_val))
        return pd.DataFrame(equity_curve, columns=["date", "equity"]).set_index("date")
