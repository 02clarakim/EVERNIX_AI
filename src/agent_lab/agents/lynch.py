from __future__ import annotations
from typing import Dict, Callable, Optional, Tuple, Any
from .base import Agent, Decision, Action
from agent_lab.data_connectors.finnhub_data import fetch_finnhub_fundamentals_single


class LynchAgent(Agent):
    """
    Peter Lynch–style stock picker.

    Core ideas implemented:
      1) Classify the business (fast grower, stalwart, cyclical, slow grower, turnaround, asset play)
         using lightweight heuristics. Decisions/weights depend on the category.
      2) Prioritize growth at a reasonable price (PEG), balance sheet strength, clean working capital,
         positive cash generation, and underfollowed signals (low analyst coverage, moderate institutional ownership,
         insider buying/ownership).
      3) Produce a terse 'two-minute drill' rationale to enforce explainability.

    Notes:
      - All metrics are optional. Missing values never crash scoring; they simply reduce confidence.
      - If `data` is passed to `decide`, no API call is made (avoids per-symbol requests).
      - PEG is computed defensively: accepts growth as 0.20 (20%) or 20 (percent).
    """

    name = "LynchAgent"

    def __init__(self, criteria: Dict | None = None):
        # Sensible defaults aligned to Lynch heuristics; tune as needed.
        self.criteria: Dict[str, Any] = criteria or {
            # Category thresholds
            "fast_eps_cagr_min": 0.20,          # 20%+ EPS CAGR -> fast grower candidate
            "stalwart_eps_cagr_min": 0.05,      # 5%+ EPS CAGR and large cap -> stalwart candidate
            "stalwart_marketcap_min": 10e9,     # USD
            "cyclical_sectors": {"Energy", "Materials", "Autos", "Automobiles", "Metals & Mining"},
            # Valuation sanity
            "peg_fast_max": 1.2,
            "peg_stalwart_max": 1.5,
            "pb_cyclical_max": 1.5,             # cheap vs assets for cyclicals
            # Balance sheet & cash
            "debt_to_equity_max": 0.8,
            "interest_coverage_min": 5.0,
            "fcf_min": 0.0,                     # positive FCF preferred
            # Working capital cleanliness
            "days_inventory_max": 120.0,        # absolute guardrail if provided
            "dso_max": 75.0,
            # Ownership/coverage signals
            "insider_ownership_min": 0.02,      # 2%+
            "analyst_count_max": 10,
            "inst_ownership_max_smallcap": 0.85,
            "smallcap_max": 3e9,
            # Buyback signal
            "buyback_yield_min": 0.01,          # 1%+ net buyback yield
            # Scoring weights (baseline, adjusted per category)
            "weights": {
                "peg": 3,
                "eps_growth": 3,
                "balance_sheet": 2,
                "fcf": 2,
                "inventory": 1,
                "receivables": 1,
                "insider": 1,
                "analyst": 1,
                "inst_ownership": 1,
                "buybacks": 1,
                "dividend": 1,  # small nod for stalwarts/slow growers
                "asset_value": 2  # for asset plays / cyclicals
            },
        }

    # -------------------------
    # Helpers
    # -------------------------

    @staticmethod
    def _safe_float(v) -> Optional[float]:
        try:
            if v is None:
                return None
            return float(v)
        except Exception:
            return None

    @staticmethod
    def _compute_peg(pe: Optional[float], growth: Optional[float]) -> Optional[float]:
        """
        PEG = P/E divided by growth rate in PERCENT.
        Accepts growth as 0.20 (20%) or 20 (percent). Returns None if invalid.
        """
        if pe is None or growth is None:
            return None
        try:
            g = float(growth)
            # Interpret growth: if <= 1.0 assume decimal; else assume already percent.
            g_percent = g * 100.0 if g <= 1.0 else g
            if g_percent <= 0:
                return None
            return float(pe) / g_percent
        except Exception:
            return None

    def _score(
        self,
        score: int,
        rationale: list[str],
        name: str,
        val: Optional[float],
        weight: int,
        cond: Callable[[float], bool],
        ok_msg: str,
        bad_msg: str
    ) -> int:
        if val is None:
            rationale.append(f"{name}: missing")
            return score
        try:
            if cond(val):
                score += weight
                rationale.append(f"{ok_msg} ({val:.2f})")
            else:
                rationale.append(f"{bad_msg} ({val:.2f})")
        except Exception:
            rationale.append(f"{name}: invalid")
        return score

    def _categorize(self, row: dict) -> str:
        """
        Heuristic category assignment inspired by Lynch's six buckets.
        Uses EPS growth, market cap, sector hints, and cheap P/B for asset plays/cyclicals.
        """
        eps_cagr = self._safe_float(row.get("eps_cagr_3y"))
        mcap = self._safe_float(row.get("market_cap"))
        sector = (row.get("sector") or "").strip()
        pb = self._safe_float(row.get("price_to_book"))
        roe = self._safe_float(row.get("roe"))

        if eps_cagr is not None and eps_cagr >= self.criteria["fast_eps_cagr_min"] and (mcap is None or mcap <= self.criteria["stalwart_marketcap_min"]):
            return "fast_grower"

        if eps_cagr is not None and eps_cagr >= self.criteria["stalwart_eps_cagr_min"] and mcap is not None and mcap >= self.criteria["stalwart_marketcap_min"]:
            return "stalwart"

        if sector in self.criteria["cyclical_sectors"]:
            return "cyclical"

        # Asset play: cheap vs book or raw assets
        if pb is not None and pb <= 1.2:
            return "asset_play"

        # Slow grower: low EPS growth, possibly higher dividend and stable ROE
        if eps_cagr is not None and eps_cagr < 0.05:
            return "slow_grower"

        # Turnaround: negative recent EPS CAGR but current EPS positive
        eps_ttm = self._safe_float(row.get("eps_ttm"))
        if eps_cagr is not None and eps_cagr <= 0 and eps_ttm is not None and eps_ttm > 0:
            return "turnaround"

        return "unknown"

    def _category_adjusted_weights(self, category: str) -> Dict[str, int]:
        w = dict(self.criteria["weights"])  # copy
        if category == "fast_grower":
            w["peg"] = 4
            w["eps_growth"] = 4
            w["balance_sheet"] = 3
            w["dividend"] = 0
            w["asset_value"] = 0
        elif category == "stalwart":
            w["peg"] = 3
            w["eps_growth"] = 2
            w["dividend"] = 2
        elif category == "cyclical":
            w["peg"] = 2
            w["asset_value"] = 3
            w["balance_sheet"] = 3
        elif category == "asset_play":
            w["peg"] = 1
            w["asset_value"] = 4
            w["eps_growth"] = 1
        elif category == "turnaround":
            w["peg"] = 2
            w["balance_sheet"] = 4
            w["eps_growth"] = 1
        elif category == "slow_grower":
            w["peg"] = 2
            w["dividend"] = 3
            w["eps_growth"] = 1
        # unknown -> keep baseline
        return w

    # -------------------------
    # Decision
    # -------------------------

    def decide(self, symbol: str, data: Optional[dict] = None) -> Decision:
        """
        Accept `data` (pre-fetched fundamentals) to avoid per-symbol API calls.

        Expected (optional) keys in `data`/row:
          pe, eps_cagr_3y, roe, roic, price_to_book, market_cap,
          debt_to_equity, interest_coverage, free_cashflow, sector,
          days_inventory, days_sales_outstanding,
          analyst_count, institutional_ownership, insider_ownership, insider_buying_6m,
          buyback_yield, dividend_yield, eps_ttm
        Missing keys are tolerated.
        """
        row = data or fetch_finnhub_fundamentals_single(symbol)
        if not row:
            return Decision(symbol=symbol, action=Action.HOLD, confidence=0.3, score=0, rationale="No data")

        # Extract frequently used fields safely
        pe = self._safe_float(row.get("pe"))
        eps_cagr = self._safe_float(row.get("eps_cagr_3y"))
        peg = self._compute_peg(pe, eps_cagr)
        debt_to_equity = self._safe_float(row.get("debt_to_equity"))
        interest_cov = self._safe_float(row.get("interest_coverage"))
        fcf = self._safe_float(row.get("free_cashflow"))
        days_inv = self._safe_float(row.get("days_inventory"))
        dso = self._safe_float(row.get("days_sales_outstanding"))
        analyst_cnt = self._safe_float(row.get("analyst_count"))
        inst_own = self._safe_float(row.get("institutional_ownership"))
        insider_own = self._safe_float(row.get("insider_ownership"))
        insider_buy = self._safe_float(row.get("insider_buying_6m"))
        buyback_yield = self._safe_float(row.get("buyback_yield"))
        div_yield = self._safe_float(row.get("dividend_yield"))
        pb = self._safe_float(row.get("price_to_book"))
        mcap = self._safe_float(row.get("market_cap"))
        sector = row.get("sector") or "Unknown"

        category = self._categorize(row)
        w = self._category_adjusted_weights(category)

        score, rationale = 0, []
        notes = []

        # Valuation: PEG by category
        if category == "fast_grower":
            peg_max = self.criteria["peg_fast_max"]
        else:
            peg_max = self.criteria["peg_stalwart_max"]

        score = self._score(
            score, rationale, "PEG", peg, w["peg"],
            lambda v: v < peg_max, f"PEG fair (<{peg_max:.2f})", "PEG rich"
        )

        # EPS growth
        score = self._score(
            score, rationale, "EPS CAGR 3y", eps_cagr, w["eps_growth"],
            lambda v: v >= (self.criteria["fast_eps_cagr_min"] if category == "fast_grower" else self.criteria["stalwart_eps_cagr_min"]),
            "Growth solid", "Growth modest"
        )

        # Balance sheet
        # debt_to_equity and interest coverage both tested; pass if both ok, partial credit via pair of checks
        score = self._score(
            score, rationale, "Debt/Equity", debt_to_equity, w["balance_sheet"],
            lambda v: v <= self.criteria["debt_to_equity_max"],
            "Debt conservative", "Debt elevated"
        )
        score = self._score(
            score, rationale, "Interest coverage", interest_cov, w["balance_sheet"],
            lambda v: v >= self.criteria["interest_coverage_min"],
            "Interest covered", "Interest tight"
        )

        # Free Cash Flow
        score = self._score(
            score, rationale, "Free cash flow", fcf, w["fcf"],
            lambda v: v >= self.criteria["fcf_min"], "FCF positive", "FCF weak/negative"
        )

        # Working capital cleanliness
        score = self._score(
            score, rationale, "Days inventory", days_inv, w["inventory"],
            lambda v: v <= self.criteria["days_inventory_max"], "Inventory in-range", "Inventory heavy"
        )
        score = self._score(
            score, rationale, "DSO", dso, w["receivables"],
            lambda v: v <= self.criteria["dso_max"], "Receivables in-range", "Receivables stretched"
        )

        # Underfollowed/ownership signals
        score = self._score(
            score, rationale, "Analyst count", analyst_cnt, w["analyst"],
            lambda v: v <= self.criteria["analyst_count_max"], "Underfollowed", "Crowded by analysts"
        )

        # Institutional ownership check (prefer not extreme for small caps)
        if mcap is not None and mcap <= self.criteria["smallcap_max"]:
            score = self._score(
                score, rationale, "Institutional ownership", inst_own, w["inst_ownership"],
                lambda v: v is None or v <= self.criteria["inst_ownership_max_smallcap"],
                "Room for discovery", "Already heavily owned"
            )
        else:
            rationale.append("Institutional ownership: n/a (not small-cap)")

        # Insider ownership/buying
        score = self._score(
            score, rationale, "Insider ownership", insider_own, w["insider"],
            lambda v: v >= self.criteria["insider_ownership_min"], "Owner mindset", "Low insider stake"
        )
        if insider_buy is not None:
            if insider_buy > 0:
                score += 1
                rationale.append("Recent insider buying (+)")
            else:
                rationale.append("No recent insider buying")

        # Buybacks
        score = self._score(
            score, rationale, "Buyback yield", buyback_yield, w["buybacks"],
            lambda v: v >= self.criteria["buyback_yield_min"], "Buybacks present", "No buybacks"
        )

        # Dividends (minor nod for stalwarts/slow growers)
        if category in {"stalwart", "slow_grower"}:
            score = self._score(
                score, rationale, "Dividend yield", div_yield, w["dividend"],
                lambda v: v is not None and v >= 0.015, "Dividend reasonable", "Dividend light"
            )

        # Asset value tests for cyclicals/asset plays
        if category in {"cyclical", "asset_play"}:
            score = self._score(
                score, rationale, "Price/Book", pb, w["asset_value"],
                lambda v: v is not None and v <= self.criteria["pb_cyclical_max"], "Asset cheap-ish", "Asset pricey vs book"
            )

        # Two-minute drill notes
        # Valuation summary
        notes.append(f"Category: {category}")
        if peg is not None:
            notes.append(f"PEG={peg:.2f}")
        if pe is not None:
            notes.append(f"P/E={pe:.1f}")
        if eps_cagr is not None:
            notes.append(f"EPS_CAGR_3y={eps_cagr:.2%}" if eps_cagr <= 1 else f"EPS_CAGR_3y≈{eps_cagr:.0f}%")
        if debt_to_equity is not None:
            notes.append(f"D/E={debt_to_equity:.2f}")
        if interest_cov is not None:
            notes.append(f"ICov={interest_cov:.1f}x")
        if fcf is not None:
            notes.append(f"FCF={fcf:.0f}")
        if buyback_yield is not None:
            notes.append(f"BuybackYld={buyback_yield:.1%}")
        if div_yield is not None:
            notes.append(f"DivYld={div_yield:.1%}")
        notes.append(f"Sector={sector}")

        # Decision mapping: category-aware bar
        # Higher bar for BUY on fast growers (avoid paying up), slightly lower for stalwarts.
        if category == "fast_grower":
            buy_strong, buy_ok, hold_min = 14, 11, 7
        elif category == "stalwart":
            buy_strong, buy_ok, hold_min = 12, 9, 6
        elif category in {"cyclical", "asset_play", "turnaround"}:
            buy_strong, buy_ok, hold_min = 13, 10, 6
        else:
            buy_strong, buy_ok, hold_min = 13, 10, 6

        if score >= buy_strong:
            action, confidence = Action.BUY, 0.95
        elif score >= buy_ok:
            action, confidence = Action.BUY, 0.78
        elif score >= hold_min:
            action, confidence = Action.HOLD, 0.55
        else:
            action, confidence = Action.SELL, 0.25

        rationale_str = " | ".join(rationale + ["; ".join(notes)])
        return Decision(symbol=symbol, action=action, confidence=confidence, score=score, rationale=rationale_str)
