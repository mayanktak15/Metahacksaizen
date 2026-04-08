from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict

from devops_openenv.graders import grade_task
from devops_openenv.models import ActionType, EnvAction, IncidentTask, Observation, StepResult
from devops_openenv.tasks import TASKS


class DevOpsIncidentEnv:
    """OpenEnv-style real-world environment for DevOps incident response."""

    benchmark_name = "devops_incident_ops"

    def __init__(self, task_name: str = "incident_easy"):
        if task_name not in TASKS:
            raise ValueError(f"Unknown task_name: {task_name}")
        self.task_name = task_name
        self.task: IncidentTask = TASKS[task_name]
        self._reset_internal()

    def _reset_internal(self) -> None:
        self.services = deepcopy(self.task.services)
        self.logs = deepcopy(self.task.logs)
        self.alerts = list(self.task.alerts)
        self.config = dict(self.task.config)
        self.step_count = 0
        self.done = False
        self.last_action_error: str | None = None
        self.last_action: str | None = None
        self.event_log: list[str] = [f"task_loaded:{self.task.name}"]
        self.actions_taken: list[EnvAction] = []

    def reset(self, task_name: str | None = None) -> Observation:
        if task_name is not None:
            if task_name not in TASKS:
                raise ValueError(f"Unknown task_name: {task_name}")
            self.task_name = task_name
            self.task = TASKS[task_name]
        self._reset_internal()
        return self.state()

    def state(self) -> Observation:
        snapshot = {
            svc: {
                "status": s.status,
                "version": s.version,
                "replicas": s.replicas,
            }
            for svc, s in self.services.items()
        }
        return Observation(
            task_name=self.task.name,
            difficulty=self.task.difficulty,
            step_count=self.step_count,
            max_steps=self.task.max_steps,
            alerts=self.alerts,
            service_snapshot=snapshot,
            last_action=self.last_action,
            last_action_error=self.last_action_error,
            event_log_tail=self.event_log[-5:],
        )

    def available_tasks(self) -> list[str]:
        return sorted(TASKS.keys())

    def _apply_action(self, action: EnvAction) -> None:
        self.last_action_error = None
        self.last_action = action.model_dump_json()
        self.actions_taken.append(action)

        if action.action_type in {
            ActionType.INSPECT_SERVICE,
            ActionType.RESTART_SERVICE,
            ActionType.ROLLBACK_SERVICE,
            ActionType.SCALE_SERVICE,
            ActionType.INSPECT_LOGS,
        } and (not action.service or action.service not in self.services and action.service not in self.logs):
            self.last_action_error = "invalid_or_missing_service"
            self.event_log.append("error:invalid_service")
            return

        if action.action_type == ActionType.INSPECT_SERVICE:
            svc = self.services[action.service]
            self.event_log.append(f"inspect_service:{action.service}:{svc.status}")

        elif action.action_type == ActionType.INSPECT_LOGS:
            lines = self.logs.get(action.service, [])
            self.event_log.append(f"inspect_logs:{action.service}:{'|'.join(lines[:1])}")

        elif action.action_type == ActionType.RESTART_SERVICE:
            svc = self.services[action.service]
            svc.status = "healthy"
            self.event_log.append(f"restart_service:{action.service}")

        elif action.action_type == ActionType.ROLLBACK_SERVICE:
            svc = self.services[action.service]
            svc.version = "stable"
            svc.status = "healthy"
            self.event_log.append(f"rollback_service:{action.service}")

        elif action.action_type == ActionType.SCALE_SERVICE:
            if action.replicas is None or action.replicas < 1:
                self.last_action_error = "invalid_replicas"
                self.event_log.append("error:invalid_replicas")
                return
            svc = self.services[action.service]
            svc.replicas = action.replicas
            if svc.status == "degraded" and action.replicas >= 2:
                svc.status = "healthy"
            self.event_log.append(f"scale_service:{action.service}:{action.replicas}")

        elif action.action_type == ActionType.UPDATE_CONFIG:
            if not action.key or action.value is None:
                self.last_action_error = "invalid_config_update"
                self.event_log.append("error:invalid_config_update")
                return
            self.config[action.key] = action.value
            self.event_log.append(f"update_config:{action.key}:{action.value}")

            if self.task.name == "incident_hard" and action.key == "max_connections":
                try:
                    if int(action.value) >= 120:
                        self.services["db-proxy"].status = "healthy"
                except ValueError:
                    self.last_action_error = "max_connections_not_int"
                    self.event_log.append("error:max_connections_not_int")

        elif action.action_type == ActionType.RESOLVE_INCIDENT:
            self.event_log.append("resolve_incident:submitted")

    def _is_recovered(self) -> bool:
        if self.task.name == "incident_easy":
            return self.services["payment"].status == "healthy"
        if self.task.name == "incident_medium":
            return self.services["checkout"].status == "healthy" and self.services["checkout"].version == "stable"
        if self.task.name == "incident_hard":
            return (
                self.services["db-proxy"].status == "healthy"
                and self.services["api"].status == "healthy"
                and int(self.config.get("max_connections", "0")) >= 120
            )
        return False

    def step(self, action: Dict[str, Any] | EnvAction) -> StepResult:
        if self.done:
            return StepResult(
                observation=self.state(),
                reward=0.0,
                done=True,
                info={"error": "episode_already_done", "score": 0.0},
            )

        parsed = action if isinstance(action, EnvAction) else EnvAction(**action)
        self.step_count += 1

        self._apply_action(parsed)

        if self.task.name == "incident_hard":
            if self.config.get("max_connections") and self.services["db-proxy"].status == "healthy":
                has_api_restart = any(a.action_type == ActionType.RESTART_SERVICE and a.service == "api" for a in self.actions_taken)
                if has_api_restart:
                    self.services["api"].status = "healthy"

        recovered = self._is_recovered()
        breakdown = grade_task(task=self.task, actions=self.actions_taken, recovered=recovered)

        done_by_success = recovered and any(a.action_type == ActionType.RESOLVE_INCIDENT for a in self.actions_taken)
        done_by_timeout = self.step_count >= self.task.max_steps
        self.done = done_by_success or done_by_timeout

        reward = breakdown["score"]

        return StepResult(
            observation=self.state(),
            reward=reward,
            done=self.done,
            info={
                "score": breakdown["score"],
                "action_coverage": breakdown["action_coverage"],
                "diagnosis_quality": breakdown["diagnosis_quality"],
                "remediation_quality": breakdown["remediation_quality"],
                "service_recovery": breakdown["service_recovery"],
                "success": done_by_success,
            },
        )
