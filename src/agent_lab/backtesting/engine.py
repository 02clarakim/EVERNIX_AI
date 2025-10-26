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
        Run backtest. Returns a DataFrame with one row per date: total portfolio equity.
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
                    target_value = weights[s] * port_val
                    max_alloc = 0.1 * port_val  # max 10% per position
                    target_value = min(target_value, max_alloc)
                    target_shares = target_value / px[s]

                trade = target_shares - positions[s]
                if abs(trade) < 1e-6:
                    continue

                trade_value = trade * px[s]
                if trade > 0:  # buying
                    trade_cost = trade_value * (1 + self.cost + self.slippage)
                    if trade_cost > cash_bal:
                        trade = cash_bal / ((1 + self.cost + self.slippage) * px[s])
                        trade_value = trade * px[s]
                        trade_cost = trade_value * (1 + self.cost + self.slippage)
                    cash_bal -= trade_cost
                else:  # selling
                    trade_cost = abs(trade_value) * (self.cost + self.slippage)
                    cash_bal += abs(trade_value) - trade_cost

                positions[s] += trade

            # --- Record daily equity (ONE ROW per day) ---
            port_val = cash_bal + sum(positions[s] * px[s] for s in positions if pd.notna(px.get(s)))
            equity_curve.append({"date": dt, "equity": port_val})

        df = pd.DataFrame(equity_curve).set_index("date")
        return df
