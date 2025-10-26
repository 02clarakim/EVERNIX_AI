"""
Run backtests for one or more agents using the existing BacktestEngine.
Save equity curves to CSVs in the results/ folder.
"""

import os
import pandas as pd
from agent_lab.backtesting.engine import BacktestEngine
from agent_lab.agents.buffett import BuffettAgent
from agent_lab.agents.ackman import AckmanAgent
# from agent_lab.agents.soros import SorosAgent  # once you add Soros
from agent_lab.ensemble.oversight import OversightAgent
from agent_lab.data_connectors.cache import preload_fundamentals  # <-- add this

PRICES_FILE = "data/prices.csv"

# --- Load the prices ---
raw = pd.read_csv(PRICES_FILE, index_col=0, parse_dates=True)

# If you saved only adjusted prices in fetch_prices.py,
# the CSV will already be just one column per ticker:
if 'Adj Close' in raw.columns:
    prices = raw['Adj Close']
elif isinstance(raw.columns, pd.MultiIndex) and 'Adj Close' in raw.columns.get_level_values(0):
    prices = raw['Adj Close']
else:
    # already flat table of adjusted closes (one ticker per column)
    prices = raw


# your fixed tickers:
stockOptions = ["AAPL", "MSFT", "KO", "BAC", "JNJ", "PG",
                "AMZN", "UBER", "GOOG", "AXP", "NVR", "UNH"]

# preload all fundamentals once at startup:
fundamentals_map = preload_fundamentals(stockOptions)

# --- Initialize agents ---
buffett = BuffettAgent()
ackman = AckmanAgent()
oversight = OversightAgent([buffett, ackman])
# soros = SorosAgent()  # once implemented

agents = {
    "buffett": buffett,
    "ackman": ackman,
    "oversight": oversight,
    # "soros": soros,
}

# --- Backtest parameters ---
CASH = 1_000_000.0
COST_BPS = 5.0  # trading cost in basis points
RESULTS_DIR = "results"
os.makedirs(RESULTS_DIR, exist_ok=True)

# --- Backtest each agent ---
for name, agent in agents.items():
    print(f"Running backtest for {name}...")
    engine = BacktestEngine(prices, cost_bps=COST_BPS)

    # daily_decider now uses pre-fetched fundamentals:
    def daily_decider(dt):
        return {
            sym: agent.decide(sym, data=fundamentals_map.get(sym))
            for sym in prices.columns if sym in fundamentals_map
        }

    equity_curve = engine.run(daily_decider, cash=CASH)
    out_file = os.path.join(RESULTS_DIR, f"{name}_equity_curve.csv")
    equity_curve.to_csv(out_file)
    print(f"Saved equity curve to {out_file}")

print("✅ Backtests complete.")
