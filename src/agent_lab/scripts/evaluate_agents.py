import pandas as pd
from agent_lab.agents.ackman import AckmanAgent
from agent_lab.agents.buffett import BuffettAgent
from agent_lab.data_connectors.cache import get_fundamentals
from agent_lab.evaluation.accuracy_eval import evaluate_agent_accuracy

# Example: read preprocessed 13F CSV
# You’ll later replace these with real ones you build from 13F data
buffett_trades = pd.read_csv("data/buffett_13f.csv")
ackman_trades = pd.read_csv("data/ackman_13f.csv")

# Define a small helper for fundamentals
def fetch_data(symbol: str):
    return get_fundamentals(symbol)

# Run evaluations
buffett_agent = BuffettAgent()
ackman_agent = AckmanAgent()

buffett_results = evaluate_agent_accuracy(buffett_agent, buffett_trades, fetch_data)
ackman_results = evaluate_agent_accuracy(ackman_agent, ackman_trades, fetch_data)

# Save detailed accuracy logs
buffett_results.to_csv("results/buffett_accuracy.csv", index=False)
ackman_results.to_csv("results/ackman_accuracy.csv", index=False)

print("\n✅ Accuracy results saved in results/")
