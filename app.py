from __future__ import annotations

from typing import Any, Dict

from fastapi import Body, FastAPI, HTTPException
from pydantic import BaseModel

from devops_openenv.environment import DevOpsIncidentEnv


app = FastAPI(title="DevOps Incident OpenEnv", version="1.0.0")
_env = DevOpsIncidentEnv(task_name="incident_easy")


class StepRequest(BaseModel):
    action: Dict[str, Any] | None = None


class ResetRequest(BaseModel):
    task_name: str | None = None


@app.get("/")
def health() -> dict[str, str]:
    return {"status": "ok", "benchmark": _env.benchmark_name}


@app.post("/reset")
def reset(req: ResetRequest | None = Body(default=None)) -> dict[str, Any]:
    """Reset environment for an optional task_name and return observation JSON."""
    try:
        task_name = req.task_name if req is not None else None
        obs = _env.reset(task_name=task_name)
        return obs.model_dump()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"reset failed: {exc}") from exc


@app.get("/state")
def state() -> dict[str, Any]:
    try:
        return _env.state().model_dump()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"state failed: {exc}") from exc


@app.post("/step")
def step(req: StepRequest | None = Body(default=None)) -> dict[str, Any]:
    if req is None or req.action is None:
        raise HTTPException(status_code=400, detail="missing required field: action")

    try:
        result = _env.step(req.action)
        payload = result.model_dump()
        return {
            "observation": payload["observation"],
            "reward": payload["reward"],
            "done": payload["done"],
            "info": payload["info"],
        }
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"invalid action: {exc}") from exc


@app.get("/tasks")
def tasks() -> dict[str, list[str]]:
    return {"tasks": _env.available_tasks()}
