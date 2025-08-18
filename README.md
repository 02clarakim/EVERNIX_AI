# EVERNIX

EVERNIX AI PROJECT

The purpose of EVERNIX LLC is to research, design, develop, deploy, and commercialize artificial intelligence systems, including but not limited to modular multi-agent AI architectures, intelligent decision-making frameworks, and confidence-based voting systems. The company will provide software products, APIs, platforms, data services, and consulting that enable enterprises to integrate explainable and autonomous decision agents into their workflows.

EVERNIX may also engage in technology licensing, academic and industrial research collaborations, cloud-based solution deployment, and the creation of intellectual property including patents, trademarks, and proprietary software systems.

In addition to its primary AI and software-focused activities, EVERNIX LLC shall have the power to conduct any lawful business or activities permitted under the laws of the State of California and the United States of America

## Quickstart

```bash
# 1) Create venv and install
python -m venv .venv && source .venv/bin/activate  # on Windows: .venv\Scripts\activate
pip install -U pip
pip install -e .

# 2) Run the API
uvicorn agent_lab.api.service:app --reload --port 8000

# 3) Try the notebook
jupyter notebook notebooks/01_quickstart.ipynb
```

> Note: Uses free data connectors (yfinance) for MVP. Swap in paid vendors later
by replacing adapters in `data_connectors/`.

## Layout

```
src/agent_lab/
  agents/         # base interface, sample agents
  ensemble/       # oversight / ensemble logic
  data_connectors # yfinance + stubs for alt data
  backtesting/    # tiny backtest engine + metrics
  api/            # FastAPI service
notebooks/        # exploration
```

## Disclaimer

This project is for research/education. It is **not** financial advice.
