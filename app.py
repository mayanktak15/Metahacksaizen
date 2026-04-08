from __future__ import annotations

from typing import Any, Dict

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from devops_openenv.environment import DevOpsIncidentEnv


app = FastAPI(title="DevOps Incident OpenEnv", version="1.0.0")
_env = DevOpsIncidentEnv(task_name="incident_easy")


class StepRequest(BaseModel):
    action: Dict[str, Any]


class ResetRequest(BaseModel):
    task_name: str | None = None


@app.get("/")
def health() -> dict[str, str]:
    return {"status": "ok", "benchmark": _env.benchmark_name}


@app.post("/reset")
def reset(req: ResetRequest) -> dict[str, Any]:
    try:
        obs = _env.reset(task_name=req.task_name)
        return {"observation": obs.model_dump(), "task": _env.task_name}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/state")
def state() -> dict[str, Any]:
    return {"observation": _env.state().model_dump(), "task": _env.task_name}


@app.post("/step")
def step(req: StepRequest) -> dict[str, Any]:
    try:
        result = _env.step(req.action)
        return result.model_dump()
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"invalid action: {exc}") from exc


@app.get("/tasks")
def tasks() -> dict[str, list[str]]:
    return {"tasks": _env.available_tasks()}
