# from __future__ import annotations
# import pandas as pd
# from typing import Dict, Callable
# from agent_lab.agents.base import Decision, Action

# class BacktestEngine:
#     def __init__(self, prices: pd.DataFrame, cost_bps: float = 5.0):
#         self.prices = prices.sort_index()
#         self.cost = cost_bps / 1e4

#     def run(self, daily_decider: Callable[[pd.Timestamp], Dict[str, Decision]], cash: float = 1_000_000.0):
#         positions = {sym: 0.0 for sym in self.prices.columns}
#         cash_bal = float(cash)
#         equity_curve = []

#         for dt, row in self.prices.iterrows():
#             px = row
#             decs = daily_decider(dt)  # dict: {symbol: Decision}
            
#             # --- record per-symbol agent info ---
#             daily_records = []
#             buy_syms = []
#             for s, d in decs.items():
#                 daily_records.append({
#                     "date": dt,
#                     "symbol": s,
#                     "action": d.action.name,
#                     "score": d.score,
#                     "confidence": d.confidence
#                 })
#                 if d.action == Action.BUY and pd.notna(px.get(s)):
#                     buy_syms.append(s)
            
#             # --- compute portfolio weights ---
#             w = (1.0 / len(buy_syms)) if buy_syms else 0.0

#             # --- compute portfolio value before trades ---
#             port_val = cash_bal + sum(float(positions[s]) * float(px[s]) for s in positions if pd.notna(px.get(s)))

#             # --- execute trades ---
#             for s in positions:
#                 target_shares = 0.0
#                 if s in buy_syms and pd.notna(px.get(s)):
#                     target_shares = (port_val * w) / max(float(px[s]), 1e-9)
#                 trade = float(target_shares) - float(positions[s])
#                 if pd.notna(px.get(s)) and abs(trade) > 0:
#                     cash_bal -= float(trade) * float(px[s]) * (1 + self.cost)
#                     positions[s] = float(positions[s]) + float(trade)

#             # --- compute portfolio value after trades ---
#             port_val = cash_bal + sum(float(positions[s]) * float(px[s]) for s in positions if pd.notna(px.get(s)))

#             # --- append equity + decisions ---
#             for rec in daily_records:
#                 rec["equity"] = port_val
#                 equity_curve.append(rec)

#         return pd.DataFrame(equity_curve).set_index("date")

# src/agent_lab/backtesting/engine.py
import pandas as pd
from typing import Callable, Dict
from agent_lab.agents.base import Decision, Action

class BacktestEngine:
    def __init__(self, prices: pd.DataFrame, cost_bps: float = 5.0, slippage_pct: float = 0.001):
        self.prices = prices.sort_index()
        self.cost = cost_bps / 1e4
        self.slippage = slippage_pct

    def run(self, daily_decider: Callable[[pd.Timestamp], Dict[str, Decision]], cash: float = 100_000.0):
        """
        daily_decider(dt) -> dict of {symbol: Decision}
        """
        positions: Dict[str, float] = {sym: 0.0 for sym in self.prices.columns}
        cash_bal = float(cash)
        equity_curve = []

        for dt, px in self.prices.iterrows():
            decs = daily_decider(dt)
            
            # Compute portfolio value before trades
            port_val = cash_bal + sum(positions[s] * px[s] for s in positions if pd.notna(px.get(s)))

            # Determine buy weights by confidence * score
            buy_syms = [s for s, d in decs.items() if d.action == Action.BUY and pd.notna(px.get(s))]
            weights = {}
            if buy_syms:
                scores = [max(0.0, decs[s].confidence * decs[s].score) for s in buy_syms]
                total = sum(scores) or len(scores)
                for s, sc in zip(buy_syms, scores):
                    weights[s] = sc / total

            # Execute trades
            for s, d in decs.items():
                if pd.isna(px.get(s)) or px[s] <= 0:
                    continue

                target_shares = 0.0
                if s in weights:
                    # Target position in $ based on weight
                    target_value = weights[s] * port_val
                    # limit max allocation to 10% of portfolio
                    max_alloc = 0.1 * port_val
                    target_value = min(target_value, max_alloc)
                    target_shares = target_value / px[s]

                # Compute trade delta
                trade = target_shares - positions[s]
                if abs(trade) < 1e-6:
                    continue

                # Buy or sell
                trade_value = trade * px[s]
                if trade > 0:  # buying
                    trade_cost = trade_value * (1 + self.cost + self.slippage)
                    if trade_cost > cash_bal:
                        # scale down if not enough cash
                        trade = cash_bal / ((1 + self.cost + self.slippage) * px[s])
                        trade_value = trade * px[s]
                        trade_cost = trade_value * (1 + self.cost + self.slippage)
                    cash_bal -= trade_cost
                else:  # selling
                    trade_cost = abs(trade_value) * (self.cost + self.slippage)
                    cash_bal += abs(trade_value) - trade_cost

                positions[s] += trade

            # Update portfolio value after trades
            port_val = cash_bal + sum(positions[s] * px[s] for s in positions if pd.notna(px.get(s)))

            # Record equity for each symbol/decision
            for s, d in decs.items():
                equity_curve.append({
                    "date": dt,
                    "symbol": s,
                    "action": d.action.name,
                    "score": d.score,
                    "confidence": d.confidence,
                    "equity": port_val
                })

        df = pd.DataFrame(equity_curve)
        df.set_index("date", inplace=True)
        return df

