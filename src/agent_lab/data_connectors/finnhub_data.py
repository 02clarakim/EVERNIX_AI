import finnhub
import pandas as pd

# --- Initialize Finnhub client ---
API_KEY = "d2lhkrpr01qr27gjbi4gd2lhkrpr01qr27gjbi50"
finnhub_client = finnhub.Client(api_key=API_KEY)

def fetch_finnhub_fundamentals(symbols):
    rows = []
    for s in symbols:
        try:
            profile = finnhub_client.company_profile2(symbol=s) or {}
            metrics = finnhub_client.company_basic_financials(s, "all").get("metric", {}) or {}
            insider_resp = finnhub_client.stock_insider_transactions(s) or {}
            insider_data = insider_resp.get("data", [])

            recent_buy = sum([t.get("shares", 0) for t in insider_data if t.get("change", 0) > 0])
            recent_sell = sum([t.get("shares", 0) for t in insider_data if t.get("change", 0) < 0])

            # --- Fallback for debt and FCF ---
            debt_to_equity = metrics.get("debtEquityRatioAnnual")
            if debt_to_equity is None:
                debt_to_equity = metrics.get("debtEquityRatioQuarterly", 0)

            free_cashflow = metrics.get("fcfAnnual")
            if free_cashflow is None:
                free_cashflow = metrics.get("fcfQuarterly", 0)

            rows.append({
                "symbol": s,
                "Company": profile.get("name", s),
                "sector": profile.get("finnhubIndustry", "Unknown"),
                "pe": metrics.get("peBasicExclExtraTTM"),
                "roe": metrics.get("roeTTM") or 0,
                "debt_to_equity": debt_to_equity,
                "free_cashflow": free_cashflow,
                "recent_insider_buy": recent_buy,
                "recent_insider_sell": recent_sell
            })
        except Exception as e:
            print(f"Error fetching {s}: {e}")
            rows.append({
                "symbol": s,
                "Company": None,
                "sector": None,
                "pe": None,
                "roe": None,
                "debt_to_equity": None,
                "free_cashflow": None,
                "recent_insider_buy": None,
                "recent_insider_sell": None
            })

    return pd.DataFrame(rows).set_index("symbol")

# --- Fetch fundamentals for a single symbol ---
def fetch_finnhub_fundamentals_single(symbol):
    df = fetch_finnhub_fundamentals([symbol])
    if df.empty:
        return None
    return df.loc[symbol].to_dict()
