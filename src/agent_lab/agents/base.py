from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from typing import Dict, Any, Protocol, List
import pandas as pd
from datetime import date

class Action(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"

@dataclass
class Decision:
    symbol: str
    action: Action
    confidence: float          # 0..1
    score: float               # agent-internal score
    rationale: str             # short, human-readable rationale
    extras: Dict[str, Any]     # extra debug/metrics

class Agent(Protocol):
    name: str
    def decide(
        self, asof: date, universe: List[str], features: pd.DataFrame
    ) -> tuple[list[Decision], pd.DataFrame]:
        ...
