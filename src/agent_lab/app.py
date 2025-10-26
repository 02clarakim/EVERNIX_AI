# src/agent_lab/app_mvp.py
import sys
import os
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

# --- Fix Python import path dynamically ---
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from agent_lab.scripts.run_mvp import UNIVERSE, agents, prices, preload_fundamentals
from agent_lab.backtesting.engine import BacktestEngine
from agent_lab.agents.base import Action

st.set_page_config(page_title="Agent Lab MVP", layout="wide")
st.title("Agent Lab - Portfolio Recommendations")

# --- User Inputs ---
portfolio_size = st.number_input("Portfolio Size ($)", min_value=1000.0, value=100_000.0, step=1000.0)
selected_universe = st.multiselect("Select Universe (tickers)", UNIVERSE, default=UNIVERSE[:4])
selected_agents = st.multiselect("Select Agents", list(agents.keys()), default=list(agents.keys()))
run_backtest = st.checkbox("Show Historical Backtest", value=True)

if st.button("Generate Recommendations"):

    # --- Load fundamentals for selected universe ---
    funds = preload_fundamentals(selected_universe)
    price_subset = prices[selected_universe]

    # --- Prepare recommendations per agent ---
    recs = {}
    for name in selected_agents:
        agent = agents[name]
        agent_recs = []
        for sym in selected_universe:
            d = agent.decide(sym, data=funds.get(sym))
            agent_recs.append({
                "symbol": sym,
                "action": d.action.name,
                "confidence": d.confidence,
                "score": d.score,
                "rationale": d.rationale
            })
        recs[name] = pd.DataFrame(agent_recs).set_index("symbol")

    # --- Display Recommendations ---
    st.subheader("Agent Recommendations")
    for name, df_rec in recs.items():
        st.markdown(f"### {name.capitalize()} Agent")
        st.dataframe(df_rec)

    # --- Suggest Allocation based on confidence * score ---
    st.subheader("Suggested Portfolio Allocation")
    allocation = pd.DataFrame(index=selected_universe)
    for name, df_rec in recs.items():
        weights = []
        for idx, row in df_rec.iterrows():
            w = max(0, row["confidence"] * row["score"])
            weights.append(w)
        total = sum(weights) or 1.0
        allocation[name] = [w / total for w in weights]

    # Multiply by portfolio size
    allocation_cash = allocation * portfolio_size
    st.dataframe(allocation_cash.style.format("${:,.2f}"))

    # --- Optional: Backtest Historical Equity ---
    if run_backtest:
        st.subheader("Historical Backtest Equity")
        fig, ax = plt.subplots()
        for name in selected_agents:
            agent = agents[name]
            engine = BacktestEngine(price_subset)

            def daily_decider(dt):
                out = {}
                for sym in price_subset.columns:
                    out[sym] = agent.decide(sym, data=funds.get(sym))
                return out

            df_bt = engine.run(daily_decider, cash=portfolio_size)
            equity = df_bt.groupby(df_bt.index).first()["equity"]
            ax.plot(equity.index, equity.values, label=name)

        ax.set_ylabel("Equity ($)")
        ax.set_xlabel("Date")
        ax.legend()
        st.pyplot(fig)

        for name in selected_agents:
            final_eq = df_bt.groupby(df_bt.index).first()["equity"].iloc[-1]
            st.write(f"{name.capitalize()} final equity: ${final_eq:,.2f}")
