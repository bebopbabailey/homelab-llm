from __future__ import annotations

import uuid

import uvicorn
from fastapi import FastAPI, HTTPException

from .agent import TinyAgentRunner
from .models import RunRequest, RunResponse
from .settings import load_settings

app = FastAPI(title="tiny-agents", version="0.1.0")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/run", response_model=RunResponse)
async def run(req: RunRequest) -> RunResponse:
    settings = load_settings()
    if not req.run_id:
        req.run_id = f"run-{uuid.uuid4()}"

    try:
        runner = TinyAgentRunner(settings)
        return await runner.run(req)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def main() -> None:
    settings = load_settings()
    uvicorn.run(app, host=settings.service_host, port=settings.service_port)


if __name__ == "__main__":
    main()
