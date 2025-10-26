from __future__ import annotations
import pandas as pd
from agent_lab.agents.base import Action

def evaluate_agent_accuracy(agent, historical_trades: pd.DataFrame, data_fetcher: callable):
    """
    Compare agent decisions to real historical trades (e.g., from 13F filings).

    Parameters:
    - agent: e.g., BuffettAgent, AckmanAgent, OversightAgent
    - historical_trades: DataFrame with columns ['date', 'symbol', 'real_action']
        real_action: 'BUY', 'SELL', 'HOLD'
    - data_fetcher: callable(symbol: str) -> dict, returns fundamentals for that symbol.

    Returns:
    - DataFrame of evaluation results.
    """
    records = []

    for _, row in historical_trades.iterrows():
        date = pd.to_datetime(row["date"])
        symbol = row["symbol"]
        real_action = row["real_action"].upper().strip()

        try:
            data = data_fetcher(symbol)
            dec = agent.decide(symbol, data=data)
            agent_action = dec.action.name
        except Exception as e:
            agent_action = "ERROR"
            dec = None

        correct = int(agent_action == real_action)

        records.append({
            "date": date,
            "symbol": symbol,
            "real_action": real_action,
            "agent_action": agent_action,
            "correct": correct,
            "score": getattr(dec, "score", None),
            "confidence": getattr(dec, "confidence", None),
        })

    df = pd.DataFrame(records)

    # Compute summary stats
    total = len(df)
    accuracy = df["correct"].mean()
    confusion = df.groupby(["real_action", "agent_action"]).size().unstack(fill_value=0)

    print(f"\n=== {agent.name} Accuracy Evaluation ===")
    print(f"Total records: {total}")
    print(f"Overall Accuracy: {accuracy:.2%}")
    print("\nConfusion Matrix (Real vs Agent):")
    print(confusion)

    return df
