# src/agent_lab/data_connectors/finnhub_data.py
import finnhub
import pandas as pd

# --- Initialize Finnhub client ---
API_KEY = "d2lhkrpr01qr27gjbi4gd2lhkrpr01qr27gjbi50"
finnhub_client = finnhub.Client(api_key=API_KEY)

# src/agent_lab/data_connectors/finnhub_data.py

def fetch_finnhub_fundamentals_batch(symbols: list[str]) -> dict[str, dict]:
    """
    Return a dict mapping symbol -> fundamentals dict.
    Avoids multiple API calls per symbol.
    """
    df = fetch_finnhub_fundamentals(symbols)
    data = {}
    for sym in symbols:
        try:
            data[sym] = df.loc[sym].to_dict()
        except KeyError:
            data[sym] = None
    return data

def fetch_finnhub_fundamentals(symbols):
    rows = []

    for s in symbols:
        try:
            profile = finnhub_client.company_profile2(symbol=s) or {}
            ratios = finnhub_client.company_basic_financials(s, "all") or {}
            metric = ratios.get("metric", {})

            # --- Compute EV/EBITDA if possible ---
            enterprise_value = metric.get("enterpriseValue")
            ebitd_per_share = metric.get("ebitdPerShareTTM")
            shares_outstanding = metric.get("sharesOutstanding") or profile.get("shareOutstanding")

            ev_ebitda = None
            if enterprise_value and ebitd_per_share and shares_outstanding:
                try:
                    ev_ebitda = float(enterprise_value) / (float(ebitd_per_share) * float(shares_outstanding))
                except (TypeError, ValueError):
                    ev_ebitda = None

            # --- P/E fallback ---
            pe = metric.get("peTTM") or metric.get("forwardPE") or metric.get("peExclExtraTTM")
            try:
                pe = float(pe)
            except (TypeError, ValueError):
                pe = None

            # --- Debt/Equity ---
            debt_to_equity = metric.get("totalDebt/totalEquityAnnual") or metric.get("longTermDebt/equityAnnual") or 0
            try:
                debt_to_equity = float(debt_to_equity)
            except (TypeError, ValueError):
                debt_to_equity = 0

            # --- Free Cash Flow ---
            free_cashflow = metric.get("pfcfShareTTM") or metric.get("currentEv/freeCashFlowTTM") or 0
            try:
                free_cashflow = float(free_cashflow)
            except (TypeError, ValueError):
                free_cashflow = 0

            # --- ROIC ---
            roic = metric.get("roiTTM") or metric.get("roiAnnual")
            try:
                roic = float(roic) if roic is not None else None
            except (TypeError, ValueError):
                roic = None

            # --- Revenue Growth ---
            revenue_cagr = metric.get("revenueGrowth5Y") or metric.get("revenueGrowth3Y") or 0
            try:
                revenue_cagr = float(revenue_cagr)
            except (TypeError, ValueError):
                revenue_cagr = 0

            # --- Revenue Stability ---
            revenue_stability = metric.get("revenueGrowthQuarterlyYoy") or 0
            try:
                revenue_stability = float(revenue_stability)
            except (TypeError, ValueError):
                revenue_stability = 0

            # --- Insider Activity ---
            insider_resp = finnhub_client.stock_insider_transactions(s) or {}
            insider_data = insider_resp.get("data", [])
            recent_buy = sum([t.get("shares", 0) for t in insider_data if t.get("change", 0) > 0])
            recent_sell = sum([t.get("shares", 0) for t in insider_data if t.get("change", 0) < 0])

            row = {
                "symbol": s,
                "Company": profile.get("name"),
                "sector": profile.get("finnhubIndustry"),
                "pe": pe,
                "roe": metric.get("roeTTM"),
                "roic": roic,
                "ev_ebitda": ev_ebitda,
                "debt_to_equity": debt_to_equity,
                "free_cashflow": free_cashflow,
                "revenue_growth_cagr": revenue_cagr,
                "revenue_stability": revenue_stability,
                "recent_insider_buy": recent_buy,
                "recent_insider_sell": recent_sell
            }

            rows.append(row)

        except Exception as e:
            print(f"[ERROR] Failed to fetch {s}: {e}")
            rows.append({
                "symbol": s,
                "Company": None,
                "sector": None,
                "pe": None,
                "roe": None,
                "roic": None,
                "ev_ebitda": None,
                "debt_to_equity": None,
                "free_cashflow": None,
                "revenue_growth_cagr": None,
                "revenue_stability": None,
                "recent_insider_buy": None,
                "recent_insider_sell": None,
            })

    return pd.DataFrame(rows).set_index("symbol")


# --- Fetch fundamentals for a single symbol ---
def fetch_finnhub_fundamentals_single(symbol):
    df = fetch_finnhub_fundamentals([symbol])
    if df.empty:
        return None
    return df.loc[symbol].to_dict()