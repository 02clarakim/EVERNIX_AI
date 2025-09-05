# src/agent_lab/agents/buffett.py
from __future__ import annotations
from typing import Dict, Callable, Optional
from .base import Agent, Decision, Action
from agent_lab.data_connectors.finnhub_data import fetch_finnhub_fundamentals_single

class BuffettAgent(Agent):
    name = "BuffettAgent"

    def __init__(self, criteria: Dict | None = None):
        self.criteria = criteria or {
            "pe_ratio_max": 20,
            "roe_min": 0.15,
            "roic_min": 0.12,
            "ev_ebitda_max": 15,
            "debt_to_equity_max": 1.0,
            "stable_revenue_std": 0.2,
            "fcf_min": 0,
            "target_sectors": [
                "Consumer Defensive", "Financial Services",
                "Healthcare", "Industrials", "Energy"
            ],
            "weights": {
                "pe": 2, "roe": 2, "roic": 3, "ev_ebitda": 2,
                "debt": 1, "fcf": 2, "sector": 1, "revenue_stability": 2,
            },
        }

    def _score_metric(
        self,
        score: int,
        rationale: list[str],
        metric_name: str,
        value,
        weight: int,
        condition: Callable[[float], bool],
        msg_ok: str,
        msg_bad: str,
    ) -> int:
        if value is None:
            rationale.append(f"{metric_name} missing")
            return score
        try:
            if condition(value):
                score += weight
                rationale.append(f"{msg_ok} ({value:.2f})")
            else:
                rationale.append(f"{msg_bad} ({value:.2f})")
        except Exception:
            rationale.append(f"{metric_name} invalid")
        return score

    def decide(self, symbol: str, data: Optional[dict] = None) -> Decision:
        """
        Accept `data` (pre-fetched fundamentals) to avoid individual API calls.
        If `data` is None, fallback to single-symbol fetch.
        """
        row = data or fetch_finnhub_fundamentals_single(symbol)
        if row is None:
            return Decision(
                symbol=symbol,
                action=Action.HOLD,
                confidence=0.3,
                score=0,
                rationale="No data",
            )

        score, rationale = 0, []
        w = self.criteria["weights"]

        # --- Valuation ---
        score = self._score_metric(score, rationale, "P/E", row.get("pe"), w["pe"],
                                   lambda v: v < self.criteria["pe_ratio_max"],
                                   "P/E OK", "P/E high")

        score = self._score_metric(score, rationale, "EV/EBITDA", row.get("ev_ebitda"), w["ev_ebitda"],
                                   lambda v: v and v < self.criteria["ev_ebitda_max"],
                                   "EV/EBITDA fair", "EV/EBITDA high")

        # --- Profitability ---
        score = self._score_metric(score, rationale, "ROE", row.get("roe"), w["roe"],
                                   lambda v: v > self.criteria["roe_min"], "ROE strong", "ROE weak")

        score = self._score_metric(score, rationale, "ROIC", row.get("roic"), w["roic"],
                                   lambda v: v > self.criteria["roic_min"], "ROIC strong", "ROIC weak")

        # --- Leverage ---
        score = self._score_metric(score, rationale, "Debt/Equity", row.get("debt_to_equity"), w["debt"],
                                   lambda v: v < self.criteria["debt_to_equity_max"], "Debt OK", "Debt high")

        # --- Free Cash Flow ---
        score = self._score_metric(score, rationale, "Free Cash Flow", row.get("free_cashflow"), w["fcf"],
                                   lambda v: v > self.criteria["fcf_min"], "FCF positive", "No FCF")

        # --- Sector Preference ---
        sector = row.get("sector")
        if sector in self.criteria["target_sectors"]:
            score += w["sector"]
            rationale.append(f"Sector {sector} target")
        else:
            rationale.append(f"Sector {sector} off-target")

        # --- Revenue Stability ---
        score = self._score_metric(score, rationale, "Revenue Stability", row.get("revenue_stability"), w["revenue_stability"],
                                   lambda v: v and v < self.criteria["stable_revenue_std"],
                                   "Stable revenue", "Volatile revenue")

        # --- Decision mapping ---
        if score >= 10:
            action, confidence = Action.BUY, 0.95
        elif score >= 7:
            action, confidence = Action.BUY, 0.75
        elif score >= 4:
            action, confidence = Action.HOLD, 0.5
        else:
            action, confidence = Action.SELL, 0.2

        return Decision(
            symbol=symbol,
            action=action,
            confidence=confidence,
            score=score,
            rationale=" | ".join(rationale),
        )
