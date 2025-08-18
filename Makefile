.PHONY: fmt lint api

fmt:
    ruff fix . || true
    black src tests notebooks || true

lint:
    ruff check .

api:
    uvicorn agent_lab.api.service:app --reload --port 8000
