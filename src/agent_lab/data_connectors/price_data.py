# src/agent_lab/data_connectors/price_data.py
import os
import pandas as pd
import yfinance as yf
import pickle
from datetime import datetime, timedelta

CACHE_DIR = "data/cache_prices"
os.makedirs(CACHE_DIR, exist_ok=True)

def _cache_path(symbol):
    return os.path.join(CACHE_DIR, f"{symbol}.pkl")

def get_price_history(symbol: str, start=None, end=None):
    """
    Returns a pandas Series of Adjusted Close indexed by date.
    Caches per-symbol to disk to avoid re-downloads.
    """
    if start is None:
        start = (datetime.now() - timedelta(days=365*3)).strftime("%Y-%m-%d")
    if end is None:
        end = datetime.now().strftime("%Y-%m-%d")

    pfile = _cache_path(symbol)
    # If cached and reasonably fresh (1 day), reuse
    if os.path.exists(pfile):
        mtime = datetime.fromtimestamp(os.path.getmtime(pfile))
        if (datetime.now() - mtime).days < 1:
            with open(pfile, "rb") as f:
                df = pickle.load(f)
            # ensure requested window available
            df = df.loc[(df.index >= start) & (df.index <= end)]
            return df["Adj Close"]

    # download
    ticker = yf.Ticker(symbol)
    df = ticker.history(start=start, end=end, auto_adjust=False)
    if df.empty:
        raise RuntimeError(f"No price data for {symbol}")
    # ensure 'Adj Close' exists
    if "Adj Close" not in df.columns and "Close" in df.columns:
        df["Adj Close"] = df["Close"]
    with open(pfile, "wb") as f:
        pickle.dump(df, f)
    return df["Adj Close"]
