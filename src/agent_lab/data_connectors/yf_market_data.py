from __future__ import annotations
from typing import List, Dict
import pandas as pd
import yfinance as yf

def fetch_prices(symbols: List[str], period: str = "2y", interval: str = "1d") -> pd.DataFrame:
    df = yf.download(symbols, period=period, interval=interval, auto_adjust=True, progress=False)["Close"]
    if isinstance(df, pd.Series):
        df = df.to_frame()
    return df.dropna(how="all")

def fetch_fundamentals(symbols: List[str]) -> pd.DataFrame:
    rows = []
    for s in symbols:
        try:
            info = yf.Ticker(s).info
            rows.append({
                "symbol": s,
                "Company": info.get("longName") or info.get("shortName") or s,
                "pe": info.get("trailingPE"),
                "roe": info.get("returnOnEquity") or 0,
                "debt_to_equity": info.get("debtToEquity") or 0,
                "free_cashflow": info.get("freeCashflow") or 0,
                "sector": info.get("sector", "Unknown"),
            })
        except Exception as e:
            rows.append({"symbol": s})
    df = pd.DataFrame(rows).set_index("symbol")
    return df

def build_momentum_features(prices: pd.DataFrame, lookback_fast: int = 50, lookback_slow: int = 200) -> pd.DataFrame:
    feats = {}
    for s in prices.columns:
        px = prices[s].dropna()
        feats[s] = {
            "ma_fast": px.rolling(lookback_fast).mean().iloc[-1] if len(px) >= lookback_fast else None,
            "ma_slow": px.rolling(lookback_slow).mean().iloc[-1] if len(px) >= lookback_slow else None,
        }
    return pd.DataFrame.from_dict(feats, orient="index")
