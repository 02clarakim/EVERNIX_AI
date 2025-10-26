import pandas as pd
import matplotlib.pyplot as plt
import os

def plot_agent_equity_curve(csv_file: str, agent_name: str = "Agent"):
    """
    Loads the backtest CSV, plots the equity curve, and visualizes BUY/HOLD/SELL actions.
    Computes basic stats to audit agent behavior.
    """
    df = pd.read_csv(csv_file, parse_dates=['date'])

    # --- Equity curve plot ---
    plt.figure(figsize=(14,6))
    plt.plot(df['date'], df['equity'], label=f'{agent_name} Equity', color='blue')

    # --- Mark actions ---
    buy = df[df['action'] == 'BUY']
    hold = df[df['action'] == 'HOLD']
    sell = df[df['action'] == 'SELL']

    plt.scatter(buy['date'], buy['equity'], marker='^', color='green', label='BUY', alpha=0.7)
    plt.scatter(hold['date'], hold['equity'], marker='o', color='gray', label='HOLD', alpha=0.5)
    plt.scatter(sell['date'], sell['equity'], marker='v', color='red', label='SELL', alpha=0.7)

    plt.title(f"{agent_name} Equity Curve & Actions")
    plt.xlabel("Date")
    plt.ylabel("Equity")
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.show()

    # --- Compute simple audit stats ---
    total = len(df)
    buy_pct = len(buy) / total * 100
    hold_pct = len(hold) / total * 100
    sell_pct = len(sell) / total * 100
    avg_confidence = df['confidence'].mean()
    avg_score = df['score'].mean()

    print(f"=== {agent_name} Summary ===")
    print(f"Total trades: {total}")
    print(f"BUY: {len(buy)} ({buy_pct:.1f}%) | HOLD: {len(hold)} ({hold_pct:.1f}%) | SELL: {len(sell)} ({sell_pct:.1f}%)")
    print(f"Average confidence: {avg_confidence:.2f}")
    print(f"Average score: {avg_score:.2f}")
    print()

if __name__ == "__main__":
    # Example: add CSVs for all your agents here
    agent_csvs = {
        "Ackman": "../../results/ackman_equity_curve.csv",
        "Buffett": "../../results/buffett_equity_curve.csv",
        "Oversight": "../../results/oversight_equity_curve.csv",
    }

    for agent, csv_file in agent_csvs.items():
        if os.path.exists(csv_file):
            plot_agent_equity_curve(csv_file, agent_name=agent)
        else:
            print(f"CSV file not found: {csv_file}")
