# src/agent_lab/data_connectors/finnhub_client.py
import os
import time
import json
import random
import finnhub
from typing import Any
from requests import HTTPError

API_KEY = "d2lhkrpr01qr27gjbi4gd2lhkrpr01qr27gjbi50"
if not API_KEY:
    raise RuntimeError("Set FINNHUB_API_KEY env var before running")

_client = finnhub.Client(api_key=API_KEY)

# Configure conservative limits for free plan:
CALLS_PER_MIN = 30  # set low to be safe on free plan
_INTERVAL = 60.0 / CALLS_PER_MIN
_last_call = 0.0

def _wait_rate_limit():
    global _last_call
    now = time.time()
    dt = now - _last_call
    if dt < _INTERVAL:
        time.sleep(_INTERVAL - dt + random.random()*0.1)
    _last_call = time.time()

def safe_call(fn, *args, max_attempts=6, **kwargs) -> Any:
    for attempt in range(max_attempts):
        try:
            _wait_rate_limit()
            res = fn(*args, **kwargs)
            return res
        except Exception as e:
            # finnhub client may raise generic exceptions on 429; back off
            backoff = min(2 ** attempt + random.random(), 60)
            time.sleep(backoff)
    raise RuntimeError(f"Failed after {max_attempts} attempts calling {fn.__name__}")

def company_profile2(symbol: str):
    return safe_call(_client.company_profile2, symbol=symbol)

def company_basic_financials(symbol: str, metric: str = "all"):
    return safe_call(_client.company_basic_financials, symbol, metric)

def stock_insider_transactions(symbol: str):
    return safe_call(_client.stock_insider_transactions, symbol)
