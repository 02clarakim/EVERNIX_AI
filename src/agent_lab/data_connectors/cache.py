# src/agent_lab/data_connectors/cache.py
import time
import os
import json
from typing import Optional
from agent_lab.data_connectors.finnhub_client import company_profile2, company_basic_financials, stock_insider_transactions

DISK_CACHE_DIR = "data/cache_fundamentals"
os.makedirs(DISK_CACHE_DIR, exist_ok=True)

_CACHE_TTL = 24 * 3600  # 1 day in seconds
_inmem = {}

def _disk_path(symbol: str):
    return os.path.join(DISK_CACHE_DIR, f"{symbol}.json")

def _write_disk(symbol: str, raw: dict):
    with open(_disk_path(symbol), "w") as f:
        json.dump({"fetched_at": time.time(), "raw": raw}, f)

def _read_disk(symbol: str) -> Optional[dict]:
    p = _disk_path(symbol)
    if not os.path.exists(p):
        return None
    with open(p, "r") as f:
        return json.load(f)

def fetch_fundamentals_from_finnhub(symbol: str) -> dict:
    """Fetch and normalize fundamentals for one symbol, persist raw JSON."""
    profile = company_profile2(symbol) or {}
    ratios = company_basic_financials(symbol, "all") or {}
    insider = {}
    try:
        insider_resp = stock_insider_transactions(symbol) or {}
        insider = insider_resp.get("data", [])
    except Exception:
        insider = []

    raw = {"profile": profile, "ratios": ratios, "insider": insider}
    _write_disk(symbol, raw)
    # transform raw into normalized row (simple)
    metric = ratios.get("metric", {}) if isinstance(ratios, dict) else {}
    def _to_float(x):
        try:
            return float(x) if x is not None else None
        except Exception:
            return None

    ev = metric.get("enterpriseValue")
    pe = metric.get("peTTM") or metric.get("forwardPE")
    row = {
        "symbol": symbol,
        "company": profile.get("name"),
        "sector": profile.get("finnhubIndustry"),
        "pe": _to_float(pe),
        "roe": _to_float(metric.get("roeTTM")),
        "roic": _to_float(metric.get("roiTTM") or metric.get("roicTTM")),
        "ev_ebitda": None,
        "debt_to_equity": _to_float(metric.get("totalDebt/totalEquityAnnual") or metric.get("longTermDebt/equityAnnual")),
        "free_cashflow": _to_float(metric.get("pfcfShareTTM") or metric.get("freeCashFlowTTM")),
        "revenue_growth_cagr": _to_float(metric.get("revenueGrowth5Y")),
        "revenue_stability": _to_float(metric.get("revenueGrowthQuarterlyYoy")),
        "recent_insider_buy": sum([t.get("shares",0) for t in insider if t.get("change",0) > 0]),
        "recent_insider_sell": sum([t.get("shares",0) for t in insider if t.get("change",0) < 0]),
    }
    # EV/EBITDA best-effort
    try:
        shares_out = metric.get("sharesOutstanding") or profile.get("shareOutstanding")
        ebitd_per_share = metric.get("ebitdPerShareTTM")
        if ev and ebitd_per_share and shares_out:
            row["ev_ebitda"] = _to_float(float(ev) / (float(ebitd_per_share) * float(shares_out)))
    except Exception:
        row["ev_ebitda"] = None
    return row

def get_fundamentals(symbol: str) -> Optional[dict]:
    """Use in-memory -> disk -> remote fetch flow with TTL."""
    now = time.time()
    # in-memory cache
    cached = _inmem.get(symbol)
    if cached and now - cached["time"] < _CACHE_TTL:
        return cached["data"]

    # disk cache
    disk = _read_disk(symbol)
    if disk and now - disk["fetched_at"] < _CACHE_TTL:
        # transform raw to normalized if needed
        row = fetch_fundamentals_from_finnhub(symbol) if False else None
        # attempt to use disk raw if we want to avoid transformation cost:
        # we'll just call fetch_fundamentals_from_finnhub to normalize using raw file
        # For simplicity, call remote normalization now only if needed:
        try:
            normalized = fetch_fundamentals_from_finnhub(symbol)
        except Exception:
            # fallback: create minimal structure
            normalized = {"symbol": symbol, "company": disk.get("raw", {}).get("profile", {}).get("name")}
        _inmem[symbol] = {"data": normalized, "time": now}
        return normalized

    # otherwise fetch
    row = fetch_fundamentals_from_finnhub(symbol)
    _inmem[symbol] = {"data": row, "time": now}
    return row

def preload_fundamentals(symbols):
    out = {}
    for s in symbols:
        out[s] = get_fundamentals(s)
    return out
