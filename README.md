---
title: METAHACKSAIZEN
emoji: 🚀
colorFrom: blue
colorTo: purple
sdk: docker
app_file: app.py
pinned: false
---

# DevOps Incident OpenEnv

Train agents on incidents that look like production outages, not toy games.

This project is an OpenEnv-compatible reinforcement learning environment for real-world DevOps incident response. Agents must investigate alerts, read logs, apply remediations, and resolve incidents with a correct diagnosis under runtime constraints.

## At a Glance

- Real-world benchmark: DevOps incident troubleshooting
- OpenEnv API: reset(), step(), state()
- 3 graded tasks: easy, medium, hard
- Typed actions and observations (Pydantic models)
- Dense deterministic reward in [0.0, 1.0]
- Inference script with strict [START]/[STEP]/[END] logging
- Docker-ready for Hugging Face Spaces deployment

## Why This Matters

Most RL benchmarks optimize for games. Real AI operations need reliability under ambiguous failure signals.

This environment measures whether an agent can:

- reason through operational symptoms
- take valid recovery actions in sequence
- produce useful root-cause and remediation summaries
- improve services, not just maximize abstract reward

In short: it bridges RL evaluation and practical SRE behavior.

## What Makes This Different

- Incident realism: noisy logs, degraded/down services, and config-driven failures
- Verifiable progress: each step yields meaningful partial reward, not only terminal success
- Judgable outputs: diagnosis and remediation quality are explicitly scored
- Deterministic grading: reproducible evaluation across runs
- Submission-ready architecture: OpenEnv spec + Docker + inference protocol

## Technical Design

### Environment Contract

- Core class: devops_openenv/environment.py
- Class: DevOpsIncidentEnv
- Methods: reset(), step(), state()

### HTTP API (FastAPI)

- GET /
- POST /reset
- POST /step
- GET /state
- GET /tasks

### Typed Models

Defined in devops_openenv/models.py:

- EnvAction
- Observation
- StepResult
- IncidentTask
- ServiceState

### Action Space

- inspect_service
- inspect_logs
- restart_service
- rollback_service
- scale_service
- update_config
- resolve_incident

### Observation Includes

- task metadata and difficulty
- step_count and max_steps
- alerts and service snapshot
- last_action and validation errors
- event log tail

## Tasks and Grading

Defined in devops_openenv/tasks.py and devops_openenv/graders.py.

### Tasks

- incident_easy: payment memory pressure recovery
- incident_medium: checkout rollback after bad deploy
- incident_hard: db connection exhaustion mitigation

### Grading Components

- action_coverage
- diagnosis_quality
- remediation_quality
- service_recovery

### Weighted Score

- 0.40 * action_coverage
- 0.25 * diagnosis_quality
- 0.20 * remediation_quality
- 0.15 * service_recovery

Score is clamped to [0.0, 1.0].

### Reward Function

Dense reward at each step:

- reward_t = grader_score(history_1_to_t)

This provides incremental signal, partial credit, and stable optimization behavior.

## OpenEnv Compliance

- openenv.yaml includes entrypoint, API mapping, tasks, graders, constraints
- step(), reset(), state() are implemented and reachable
- 3 tasks with easy/medium/hard difficulties
- deterministic graders with bounded normalized scores
- runtime aligned to 2 vCPU / 8 GB expectations

## Inference Protocol

File: inference.py

Uses environment variables:

- API_BASE_URL
- MODEL_NAME
- HF_TOKEN

Uses OpenAI client for LLM calls.

Strict stdout format:

- [START] task=... env=... model=...
- [STEP] step=... action=... reward=... done=... error=...
- [END] success=... steps=... score=... rewards=...

## Quick Start

### Local

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Run API server:

```bash
python app.py
```

Or with uv project script:

```bash
uv run server
```

Run inference:

```bash
export API_BASE_URL="https://router.huggingface.co/v1"
export MODEL_NAME="Qwen/Qwen2.5-72B-Instruct"
export HF_TOKEN="<your_token>"
python inference.py
```

API examples:

```bash
curl -s http://localhost:7860/
curl -s -X POST http://localhost:7860/reset -H "content-type: application/json" -d '{"task_name":"incident_easy"}'
curl -s -X POST http://localhost:7860/step -H "content-type: application/json" -d '{"action":{"action_type":"inspect_service","service":"payment"}}'
```

## Hugging Face Spaces Deployment (Docker)

- SDK: docker
- Container port: 7860
- Entry process: python app.py

Deployment flow:

1. Create a Docker Space.
2. Push repository files.
3. Configure secrets: API_BASE_URL, MODEL_NAME, HF_TOKEN.
4. Let Space build using Dockerfile.
5. Verify health and OpenEnv endpoints.

Base URL pattern:

- https://<space-name>.hf.space

## Final Validation Checklist

- OpenEnv YAML is valid and complete
- API endpoints respond correctly
- Tasks and graders are deterministic and bounded
- Inference logs follow required format
- Docker image builds and serves successfully
- Environment is reproducible and submission-ready
