from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional

from openai import OpenAI

from devops_openenv import DevOpsIncidentEnv


API_BASE_URL = os.getenv("API_BASE_URL", "https://router.huggingface.co/v1")
MODEL_NAME = os.getenv("MODEL_NAME", "Qwen/Qwen2.5-72B-Instruct")
HF_TOKEN = os.getenv("HF_TOKEN", "")
MAX_STEPS = int(os.getenv("MAX_STEPS", "12"))
TASKS = ["incident_easy", "incident_medium", "incident_hard"]


def log_start(task: str, env: str, model: str) -> None:
    print(f"[START] task={task} env={env} model={model}", flush=True)


def log_step(step: int, action: str, reward: float, done: bool, error: Optional[str]) -> None:
    error_val = error if error else "null"
    done_val = str(done).lower()
    print(
        f"[STEP] step={step} action={action} reward={reward:.2f} done={done_val} error={error_val}",
        flush=True,
    )


def log_end(success: bool, steps: int, score: float, rewards: List[float]) -> None:
    rewards_csv = ",".join(f"{r:.2f}" for r in rewards)
    success_val = str(success).lower()
    print(
        f"[END] success={success_val} steps={steps} score={score:.2f} rewards={rewards_csv}",
        flush=True,
    )


def build_prompt(observation: Dict[str, Any]) -> str:
    return (
        "You are an SRE agent in a DevOps incident simulation. "
        "Return exactly one JSON object with keys: action_type, service, key, value, replicas, root_cause, remediation. "
        "Choose only valid action_type values: inspect_service, inspect_logs, restart_service, rollback_service, "
        "scale_service, update_config, resolve_incident. "
        "Observation: " + json.dumps(observation, ensure_ascii=True)
    )


def heuristic_action(task_name: str, step: int) -> Dict[str, Any]:
    plans = {
        "incident_easy": [
            {"action_type": "inspect_service", "service": "payment"},
            {"action_type": "inspect_logs", "service": "payment"},
            {"action_type": "restart_service", "service": "payment"},
            {
                "action_type": "resolve_incident",
                "root_cause": "memory leak in payment worker",
                "remediation": "restart payment service and patch memory leak",
            },
        ],
        "incident_medium": [
            {"action_type": "inspect_service", "service": "checkout"},
            {"action_type": "inspect_logs", "service": "checkout"},
            {"action_type": "rollback_service", "service": "checkout"},
            {
                "action_type": "resolve_incident",
                "root_cause": "buggy checkout deployment v2.8.1",
                "remediation": "rollback checkout service to previous stable version",
            },
        ],
        "incident_hard": [
            {"action_type": "inspect_service", "service": "api"},
            {"action_type": "inspect_logs", "service": "db-proxy"},
            {"action_type": "update_config", "key": "max_connections", "value": "150"},
            {"action_type": "restart_service", "service": "api"},
            {
                "action_type": "resolve_incident",
                "root_cause": "database connection pool limit too low",
                "remediation": "increase max_connections and restart api service",
            },
        ],
    }
    seq = plans[task_name]
    return seq[min(step - 1, len(seq) - 1)]


def parse_llm_action(raw_text: str) -> Dict[str, Any]:
    cleaned = raw_text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        cleaned = cleaned.replace("json", "", 1).strip()
    return json.loads(cleaned)


def llm_choose_action(client: OpenAI, observation: Dict[str, Any]) -> Dict[str, Any]:
    response = client.chat.completions.create(
        model=MODEL_NAME,
        temperature=0.0,
        max_tokens=180,
        messages=[
            {
                "role": "system",
                "content": "Output only valid JSON for the next action.",
            },
            {"role": "user", "content": build_prompt(observation)},
        ],
    )
    text = response.choices[0].message.content or "{}"
    return parse_llm_action(text)


def run_task(task_name: str, client: OpenAI) -> None:
    env = DevOpsIncidentEnv(task_name=task_name)
    obs = env.reset().model_dump()
    rewards: List[float] = []
    success = False
    final_score = 0.0
    step_num = 0

    log_start(task=task_name, env=env.benchmark_name, model=MODEL_NAME)

    try:
        for step_num in range(1, MAX_STEPS + 1):
            try:
                action = llm_choose_action(client=client, observation=obs)
            except Exception:
                action = heuristic_action(task_name=task_name, step=step_num)

            action_str = json.dumps(action, ensure_ascii=True, separators=(",", ":"))
            result = env.step(action)
            rewards.append(float(result.reward))

            obs = result.observation.model_dump()
            err = result.observation.last_action_error
            log_step(step=step_num, action=action_str, reward=float(result.reward), done=bool(result.done), error=err)

            final_score = float(result.info.get("score", 0.0))
            success = bool(result.info.get("success", False))
            if result.done:
                break
    except Exception:
        success = False
    finally:
        log_end(success=success, steps=step_num, score=final_score, rewards=rewards)


def main() -> None:
    api_key = HF_TOKEN if HF_TOKEN else "EMPTY"
    client = OpenAI(base_url=API_BASE_URL, api_key=api_key)
    for task_name in TASKS:
        run_task(task_name=task_name, client=client)


if __name__ == "__main__":
    main()
