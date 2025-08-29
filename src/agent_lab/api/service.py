from fastapi import FastAPI
from agent_lab.agents.buffett import BuffettAgent
from agent_lab.agents.momentum import MomentumAgent
from agent_lab.ensemble.oversight import OversightAgent

app = FastAPI(title="Agent Lab API")

buffett = BuffettAgent()
momentum = MomentumAgent()
oversight = OversightAgent([buffett, momentum])

@app.get("/")
async def root():
    return {"message": "Agent Lab API running"}

@app.get("/decide")
async def decide(symbol: str):
    return {
        "buffett": buffett.decide(symbol).dict(),
        "momentum": momentum.decide(symbol).dict(),
        "oversight": oversight.decide(symbol)
    }
