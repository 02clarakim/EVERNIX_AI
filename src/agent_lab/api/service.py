# src/agent_lab/api/service.py

from fastapi import FastAPI, Query
from agent_lab.agents.buffett import BuffettAgent
from agent_lab.agents.momentum import MomentumAgent
from agent_lab.ensemble.oversight import OversightAgent

app = FastAPI(title="Agent Lab API")

# --- init agents ---
buffett = BuffettAgent()
momentum = MomentumAgent()
oversight = OversightAgent([buffett, momentum])

@app.get("/")
async def root():
    return {"message": "Agent Lab API running"}

@app.get("/decide")
async def decide(symbol: str = Query(..., description="Stock ticker symbol")):
    """
    Example: /decide?symbol=AAPL
    Runs Buffet + Momentum agents, then oversight agent.
    """
    results = {
        "buffett": buffett.decide(symbol),
        "momentum": momentum.decide(symbol),
    }
    results["oversight"] = oversight.decide(symbol)
    return results
