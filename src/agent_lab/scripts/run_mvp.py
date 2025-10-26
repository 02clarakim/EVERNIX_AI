# src/agent_lab/scripts/run_mvp.py
import pandas as pd
from agent_lab.data_connectors.price_data import get_price_history
from agent_lab.data_connectors.cache import preload_fundamentals
from agent_lab.backtesting.engine import BacktestEngine
from agent_lab.agents.buffett import BuffettAgent
from agent_lab.agents.ackman import AckmanAgent
from agent_lab.agents.soros import SorosAgent
from agent_lab.agents.cathie import CathieAgent
import matplotlib.pyplot as plt
import os

RESULTS_DIR = "results"
os.makedirs(RESULTS_DIR, exist_ok=True)

# pick tickers for MVP
UNIVERSE = ["AAPL","MSFT","NVDA","TSLA","AMZN","KO"]
# Build price DataFrame (aligned)
price_map = {}
for s in UNIVERSE:
    try:
        price_map[s] = get_price_history(s)
    except Exception as e:
        print("Price fetch failed for", s, e)
prices = pd.concat(price_map.values(), axis=1)
prices.columns = list(price_map.keys())

# preload fundamentals
funds = preload_fundamentals(UNIVERSE)

agents = {
    "buffett": BuffettAgent(),
    "ackman": AckmanAgent(),
    "soros": SorosAgent(),
    "cathie": CathieAgent(),
}

for name, agent in agents.items():
    print("Running", name)
    engine = BacktestEngine(prices)
    def daily_decider(dt):
        # create decisions dict for all symbols
        out = {}
        for sym in prices.columns:
            # prefer passing preloaded fundamentals
            d = None
            try:
                d = agent.decide(sym, data=funds.get(sym))
            except TypeError:
                d = agent.decide(sym)  # fallback
            out[sym] = d
        return out

    result = engine.run(daily_decider, cash=100_000.0)
    # compute equity curve by date (equity repeated per symbol, take first)
    equity_by_date = result.groupby(result.index).first()["equity"]
    out_csv = os.path.join(RESULTS_DIR, f"{name}_equity.csv")
    equity_by_date.to_csv(out_csv)
    print("Saved", out_csv)
    # plot
    plt.plot(equity_by_date.index, equity_by_date.values, label=name)

plt.legend()
plt.title("MVP Agent Equity Curves")
plt.savefig(os.path.join(RESULTS_DIR, "agents_equity.png"))
print("Saved combined plot")
