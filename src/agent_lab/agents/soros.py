from __future__ import annotations
from typing import Dict, Callable, Optional, Tuple
from .base import Agent, Decision, Action

class SorosAgent(Agent):
    """
    Soros-style global macro agent focused on FX/rates with reflexivity logic.

    Data contract (row: dict[str, any]) — provide via `data` or `data_provider(symbol)`:
        # Regime & policy
        'regime': str in {'peg', 'band', 'managed', 'float'}            # exchange-rate regime
        'credibility': float in [0,1]                                    # CB/policy credibility proxy
        'policy_events_30d': int                                         # elections, key meetings count
        'cb_fx_intervention_30d': float                                  # USD bn or local equiv
        'reserves_months_imports': float                                 # adequacy proxy
        'st_debt_to_reserves': float                                     # short-term ext debt / reserves

        # External balance
        'ca_gdp': float                                                  # current account (% of GDP), negative = deficit
        'reserves_trend_3m': float                                       # % change last 3m

        # Rates & inflation
        'real_rate_diff_usd': float                                      # local real rate minus US real rate (pp)
        'inflation_yoy': float                                           # %
        'inflation_exp_1y': float                                        # %

        # Market validation / flows
        'fx_momentum_3m': float                                          # % move of BASE/QUOTE over 3m
        'carry_3m': float                                                # annualized % carry of BASE vs QUOTE over 3m
        'positioning_z': float                                           # speculative positioning z-score (BASE)

        # Reflexivity / breakpoint
        'pass_through': float in [0,1]                                   # FX->inflation pass-through sensitivity
        'break_level': Optional[float]                                   # known band edge/peg level for BASE/QUOTE
        'current_fx': Optional[float]                                    # current spot BASE/QUOTE

    Symbol format:
        Prefer standard FX pairs like 'GBPUSD', 'USDKRW', 'EURUSD', or 'GBP/USD'.
        This agent assumes USD is on one side. Non-USD crosses will be treated conservatively.

    Output semantics:
        If the agent detects pressure for the BASE currency to DEPRECIATE versus USD:
            - For pairs like 'GBPUSD' (BASE is non-USD), it will suggest Action.SELL (short BASE).
            - For pairs like 'USDKRW' (BASE is USD), it will suggest Action.BUY (long USD).
        Rationale includes explicit trade bias and key triggers.
    """

    name = "SorosAgent"

    def __init__(
        self,
        criteria: Dict | None = None,
        data_provider: Optional[Callable[[str], Optional[dict]]] = None,
    ):
        # Default thresholds calibrated for “peg stress / credibility wobble” detection.
        self.criteria = criteria or {
            # External balance & reserves
            "ca_deficit_thresh": -3.0,              # % of GDP
            "reserves_months_min": 3.0,             # months of imports
            "st_debt_reserves_max": 1.0,            # >1x is risky
            "reserves_trend_min": -5.0,             # -5% over 3m considered draining

            # Rates & inflation
            "real_rate_diff_min": -1.0,             # pp below US is problematic if persistent
            "inflation_gap_min": 0.5,               # exp > spot by 0.5pp signals worsening

            # Regime & credibility
            "low_cred_thresh": 0.5,                 # 0..1 scale
            "regime_fragility_weights": {           # regime fragility base weights
                "peg": 3, "band": 2, "managed": 2, "float": 0
            },

            # Market validation
            "momentum_confirm_min": -2.0,           # % over 3m (negative means BASE weakening)
            "carry_risky_min": 2.0,                 # positive carry supporting peg can backfire
            "positioning_extreme": 1.5,             # |z| > 1.5 considered one-sided

            # Reflexivity & breakpoint
            "pass_through_high": 0.6,               # high sensitivity
            "break_dist_pct_max": 2.0,              # within 2% of break/band edge is acute
            "policy_events_risky_min": 1,           # elections/meetings heighten constraints
            "intervention_heavy_min": 2.0,          # USD bn over 30d (scale per market)

            # Weights for composite score
            "weights": {
                "external_balance": 3,
                "rates": 2,
                "regime": 3,
                "momentum": 2,
                "positioning": 1,
                "reflexivity": 3,
                "breakpoint": 3,
                "policy_inflex": 2,
                "intervention_exhaust": 2,
            },
        }
        self.data_provider = data_provider

    # ---------- helpers ----------
    @staticmethod
    def _parse_pair(symbol: str) -> Tuple[str, str]:
        s = symbol.replace("/", "").upper()
        if len(s) >= 6:
            return s[:3], s[3:6]
        # Fallback: unknown -> treat as base/quote unknown
        return s[:3], s[3:] or "USD"

    def _get_row(self, symbol: str, data: Optional[dict]) -> Optional[dict]:
        if data is not None:
            return data
        if self.data_provider is not None:
            try:
                return self.data_provider(symbol)
            except Exception:
                return None
        return None

    def _add(self, rationale: list[str], msg: str) -> None:
        rationale.append(msg)

    def _pct_dist_to_break(self, current: Optional[float], level: Optional[float]) -> Optional[float]:
        try:
            if current is None or level is None or current == 0:
                return None
            return abs((level - current) / current) * 100.0
        except Exception:
            return None

    # ---------- main ----------
    def decide(self, symbol: str, data: Optional[dict] = None) -> Decision:
        row = self._get_row(symbol, data)
        if not row:
            return Decision(
                symbol=symbol,
                action=Action.HOLD,
                confidence=0.3,
                score=0,
                rationale="No data",
            )

        base, quote = self._parse_pair(symbol)
        usd_on_side = base == "USD" or quote == "USD"

        c = self.criteria
        w = c["weights"]
        score = 0
        rationale: list[str] = []

        # --- External balance & reserves ---
        eb_sub = 0
        ca_gdp = row.get("ca_gdp")
        if isinstance(ca_gdp, (int, float)) and ca_gdp <= c["ca_deficit_thresh"]:
            eb_sub += 1
            self._add(rationale, f"Current-account deficit large ({ca_gdp:.1f}% GDP)")

        rmonths = row.get("reserves_months_imports")
        if isinstance(rmonths, (int, float)) and rmonths < c["reserves_months_min"]:
            eb_sub += 1
            self._add(rationale, f"Reserves thin ({rmonths:.1f} months of imports)")

        sdr = row.get("st_debt_to_reserves")
        if isinstance(sdr, (int, float)) and sdr > c["st_debt_reserves_max"]:
            eb_sub += 1
            self._add(rationale, f"Short-term debt high vs reserves ({sdr:.2f}x)")

        rtrend = row.get("reserves_trend_3m")
        if isinstance(rtrend, (int, float)) and rtrend <= c["reserves_trend_min"]:
            eb_sub += 1
            self._add(rationale, f"Reserves draining ({rtrend:.1f}% over 3m)")

        if eb_sub > 0:
            score += w["external_balance"] * min(eb_sub, 2) / 2  # cap contribution
        # --- Rates & inflation ---
        rates_sub = 0
        rdiff = row.get("real_rate_diff_usd")
        if isinstance(rdiff, (int, float)) and rdiff <= c["real_rate_diff_min"]:
            rates_sub += 1
            self._add(rationale, f"Real rate below US ({rdiff:.2f} pp)")

        inf = row.get("inflation_yoy")
        infx = row.get("inflation_exp_1y")
        if isinstance(inf, (int, float)) and isinstance(infx, (int, float)):
            if infx - inf >= c["inflation_gap_min"]:
                rates_sub += 1
                self._add(rationale, f"Inflation expectations rising (gap {infx - inf:.2f} pp)")

        if rates_sub > 0:
            score += w["rates"] * rates_sub / 2

        # --- Regime & credibility ---
        regime = str(row.get("regime", "float")).lower()
        cred = row.get("credibility")
        reg_weight = c["regime_fragility_weights"].get(regime, 0)
        reg_sub = 0
        if reg_weight > 0:
            reg_sub += reg_weight
            self._add(rationale, f"Fragile regime '{regime}'")
        if isinstance(cred, (int, float)) and cred <= c["low_cred_thresh"]:
            reg_sub += 1
            self._add(rationale, f"Low policy credibility ({cred:.2f})")
        if reg_sub > 0:
            score += w["regime"] * min(reg_sub, 3) / 3

        # --- Market validation (trend alignment & carry mismatch) ---
        mom = row.get("fx_momentum_3m")
        carry = row.get("carry_3m")
        mom_ok = isinstance(mom, (int, float)) and mom <= c["momentum_confirm_min"]
        carry_risky = isinstance(carry, (int, float)) and carry >= c["carry_risky_min"]
        if mom_ok:
            score += w["momentum"] * 0.6
            self._add(rationale, f"BASE weakening on 3m momentum ({mom:.1f}%)")
        if carry_risky:
            score += w["momentum"] * 0.4
            self._add(rationale, f"Positive carry supports one-way risk ({carry:.1f}%)")

        # --- Positioning (one-sidedness) ---
        posz = row.get("positioning_z")
        if isinstance(posz, (int, float)) and abs(posz) >= c["positioning_extreme"]:
            score += w["positioning"]
            side = "long" if posz > 0 else "short"
            self._add(rationale, f"Positioning one-sided ({side}, z={posz:.1f})")

        # --- Reflexivity (FX -> inflation -> real rates loop) ---
        pth = row.get("pass_through")
        reflex_sub = 0
        if isinstance(pth, (int, float)) and pth >= c["pass_through_high"]:
            reflex_sub += 1
        if mom_ok and isinstance(infx, (int, float)) and isinstance(inf, (int, float)) and (infx > inf):
            reflex_sub += 1
        if reflex_sub > 0:
            score += w["reflexivity"] * reflex_sub / 2
            self._add(rationale, "Reflexive loop forming (FX weakness → inflation → weaker real rates)")

        # --- Breakpoint proximity (band edge / peg level) ---
        dist = self._pct_dist_to_break(row.get("current_fx"), row.get("break_level"))
        if isinstance(dist, (int, float)) and dist <= c["break_dist_pct_max"]:
            score += w["breakpoint"]
            self._add(rationale, f"Near policy break level ({dist:.2f}% away)")

        # --- Policy inflexibility (timing constraints) ---
        pevents = row.get("policy_events_30d")
        if isinstance(pevents, int) and pevents >= c["policy_events_risky_min"]:
            score += w["policy_inflex"] * 0.6
            self._add(rationale, f"Policy window constrained (events next 30d: {pevents})")

        inter = row.get("cb_fx_intervention_30d")
        if isinstance(inter, (int, float)) and inter >= c["intervention_heavy_min"]:
            score += w["intervention_exhaust"] * 0.8
            self._add(rationale, f"Heavy recent CB intervention ({inter:.1f} units)")

        # --- Direction mapping & action ---
        # Baseline: higher score => higher probability the NON-USD currency is under pressure.
        # If USD is not in the pair, stay conservative.
        trade_bias = "NEUTRAL"
        action = Action.HOLD

        # Heuristic bias: if score is high, expect BASE to weaken vs USD.
        # If pair includes USD, express that bias.
        high = score >= 9
        medium = 6 <= score < 9

        if usd_on_side:
            if base != "USD":
                # Pair like XXXUSD: short BASE when risk is high.
                if high:
                    action = Action.SELL
                    trade_bias = f"SHORT {base} vs USD"
                elif medium:
                    action = Action.SELL
                    trade_bias = f"LIGHT SHORT {base} vs USD"
                else:
                    action = Action.HOLD
                    trade_bias = "NEUTRAL / WAIT"
            else:
                # Pair like USDXXX: long USD when risk is high.
                quote_ccy = quote
                if high:
                    action = Action.BUY
                    trade_bias = f"LONG USD vs {quote_ccy}"
                elif medium:
                    action = Action.BUY
                    trade_bias = f"LIGHT LONG USD vs {quote_ccy}"
                else:
                    action = Action.HOLD
                    trade_bias = "NEUTRAL / WAIT"
        else:
            # Non-USD cross: insufficient reference; hold unless extreme.
            if score >= 11:
                action = Action.HOLD
                trade_bias = "Prefer USD cross for expression"
            else:
                action = Action.HOLD
                trade_bias = "NEUTRAL (non-USD cross)"

        # --- Confidence: dynamic sizing logic (validation -> higher confidence) ---
        # Base confidence from score, then boost for validation signals (momentum+reflexivity+breakpoint).
        base_conf = max(0.2, min(0.95, 0.2 + (score / 12.0) * 0.7))
        validation_boost = 0.0
        if mom_ok:
            validation_boost += 0.05
        if reflex_sub > 0:
            validation_boost += 0.05
        if isinstance(dist, (int, float)) and dist <= c["break_dist_pct_max"]:
            validation_boost += 0.05
        confidence = min(0.95, base_conf + validation_boost)

        # Kill-switch hint: if momentum flips violently against bias, external caller should cut.
        # We surface that as a rationale note rather than changing the interface.
        if isinstance(mom, (int, float)) and mom > 1.5 and action in (Action.SELL, Action.BUY):
            self._add(rationale, "Warning: short-term momentum opposes bias; size smaller / use options")

        # Final rationale
        rationale_str = f"{trade_bias} | " + " | ".join(rationale) if rationale else trade_bias

        return Decision(
            symbol=symbol,
            action=action,
            confidence=round(confidence, 3),
            score=int(round(score)),
            rationale=rationale_str,
        )
