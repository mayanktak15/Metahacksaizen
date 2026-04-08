from __future__ import annotations

from enum import Enum
from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class ActionType(str, Enum):
    INSPECT_SERVICE = "inspect_service"
    INSPECT_LOGS = "inspect_logs"
    RESTART_SERVICE = "restart_service"
    ROLLBACK_SERVICE = "rollback_service"
    SCALE_SERVICE = "scale_service"
    UPDATE_CONFIG = "update_config"
    RESOLVE_INCIDENT = "resolve_incident"


class EnvAction(BaseModel):
    action_type: ActionType
    service: Optional[str] = None
    key: Optional[str] = None
    value: Optional[str] = None
    replicas: Optional[int] = None
    root_cause: Optional[str] = None
    remediation: Optional[str] = None


class ServiceState(BaseModel):
    status: Literal["healthy", "degraded", "down"] = "healthy"
    version: str = "stable"
    replicas: int = 2


class IncidentTask(BaseModel):
    name: str
    difficulty: Literal["easy", "medium", "hard"]
    description: str
    expected_behavior: str
    success_conditions: List[str]
    root_cause_hint: str
    required_actions: List[ActionType]
    services: Dict[str, ServiceState]
    alerts: List[str]
    logs: Dict[str, List[str]]
    config: Dict[str, str]
    solution_root_cause: str
    solution_remediation: str
    max_steps: int = 10


class Observation(BaseModel):
    task_name: str
    difficulty: str
    step_count: int
    max_steps: int
    alerts: List[str]
    service_snapshot: Dict[str, Dict[str, str | int]]
    last_action: Optional[str] = None
    last_action_error: Optional[str] = None
    event_log_tail: List[str] = Field(default_factory=list)


class StepResult(BaseModel):
    observation: Observation
    reward: float
    done: bool
    info: Dict[str, str | float | bool]
