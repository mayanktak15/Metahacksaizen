from __future__ import annotations

from devops_openenv.models import ActionType, IncidentTask, ServiceState


TASKS: dict[str, IncidentTask] = {
    "incident_easy": IncidentTask(
        name="incident_easy",
        difficulty="easy",
        description="Restore a degraded payment service after a memory spike.",
        expected_behavior="Inspect service, inspect logs, restart service, then resolve with correct root cause.",
        success_conditions=[
            "payment service returns to healthy",
            "root cause identifies memory leak",
            "remediation includes restart and memory fix plan",
        ],
        root_cause_hint="Recent release introduced a memory leak in payment worker.",
        required_actions=[
            ActionType.INSPECT_SERVICE,
            ActionType.INSPECT_LOGS,
            ActionType.RESTART_SERVICE,
            ActionType.RESOLVE_INCIDENT,
        ],
        services={
            "payment": ServiceState(status="degraded", version="stable", replicas=1),
            "api": ServiceState(status="healthy", version="stable", replicas=2),
        },
        alerts=["payment latency p95 above threshold", "payment memory usage critical"],
        logs={
            "payment": [
                "worker loop delayed by GC pressure",
                "out-of-memory warning raised in payment worker",
            ],
            "api": ["request volume nominal"],
        },
        config={"payment_memory_limit_mb": "512"},
        solution_root_cause="memory leak in payment worker",
        solution_remediation="restart payment service and patch memory leak",
        max_steps=8,
    ),
    "incident_medium": IncidentTask(
        name="incident_medium",
        difficulty="medium",
        description="Recover checkout failures caused by a bad deploy.",
        expected_behavior="Inspect service and logs, roll back checkout, then resolve incident.",
        success_conditions=[
            "checkout service returns healthy",
            "root cause identifies bad release",
            "remediation includes rollback",
        ],
        root_cause_hint="Checkout v2.8.1 has a regression in cart serialization.",
        required_actions=[
            ActionType.INSPECT_SERVICE,
            ActionType.INSPECT_LOGS,
            ActionType.ROLLBACK_SERVICE,
            ActionType.RESOLVE_INCIDENT,
        ],
        services={
            "checkout": ServiceState(status="down", version="v2.8.1", replicas=2),
            "api": ServiceState(status="healthy", version="stable", replicas=3),
        },
        alerts=["checkout 500 rate critical", "cart conversion dropped by 70%"],
        logs={
            "checkout": [
                "serialization exception in cart payload parser",
                "error introduced after deployment v2.8.1",
            ],
            "api": ["downstream checkout timeout"],
        },
        config={"checkout_canary_enabled": "true"},
        solution_root_cause="buggy checkout deployment v2.8.1",
        solution_remediation="rollback checkout service to previous stable version",
        max_steps=10,
    ),
    "incident_hard": IncidentTask(
        name="incident_hard",
        difficulty="hard",
        description="Mitigate cascading order failures caused by DB connection exhaustion.",
        expected_behavior="Inspect API and DB logs, update config, restart API, then resolve with complete diagnosis.",
        success_conditions=[
            "api service healthy after config update and restart",
            "root cause identifies db connection pool limit",
            "remediation includes config change and controlled restart",
        ],
        root_cause_hint="Max DB connections is too low after traffic growth.",
        required_actions=[
            ActionType.INSPECT_SERVICE,
            ActionType.INSPECT_LOGS,
            ActionType.UPDATE_CONFIG,
            ActionType.RESTART_SERVICE,
            ActionType.RESOLVE_INCIDENT,
        ],
        services={
            "api": ServiceState(status="degraded", version="stable", replicas=3),
            "db-proxy": ServiceState(status="degraded", version="stable", replicas=1),
        },
        alerts=["api timeout rate high", "db connection acquisition timeout"],
        logs={
            "api": [
                "failed to obtain DB connection from pool",
                "timeout while creating order transaction",
            ],
            "db-proxy": [
                "pool exhausted: max_connections=60",
                "active clients exceeded expected baseline",
            ],
        },
        config={"max_connections": "60", "api_retry_budget": "2"},
        solution_root_cause="database connection pool limit too low",
        solution_remediation="increase max_connections and restart api service",
        max_steps=12,
    ),
}
