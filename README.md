---
title: METAHACKSAIZEN
emoji: 🚀
colorFrom: blue
colorTo: purple
sdk: docker
app_file: app.py
pinned: false
---



# DevOps Incident OpenEnv (Round 1 Submission)

A complete OpenEnv-style real-world RL environment that simulates DevOps incident response workflows.

This project includes:
- step(), reset(), state() APIs
- 3 graded tasks (easy, medium, hard)
- Deterministic, dense, normalized reward scoring in [0.0, 1.0]
- OpenAI-client-based inference script with strict logging format
- FastAPI server for deployment
- Dockerfile for Hugging Face Spaces

## Step 1: Problem Selection

Three strong non-game environment ideas:
1. Customer Support Ticket Resolution Environment
2. File System Recovery Assistant Environment
3. DevOps Incident Troubleshooting Environment

Best choice: DevOps Incident Troubleshooting Environment

Why this was selected:
- Simplicity: finite, structured action space and deterministic transitions
- Evaluability: explicit operational goals (recover services, diagnose root cause)
- Scoring clarity: measurable progress from partial action coverage to full incident resolution

## Step 2: Environment Design

### State Space
State contains:
- Task metadata (name, difficulty)
- Current step and max steps
- Service states (status, version, replicas)
- Alerts and log snippets
- Last action and validation error
- Event log tail

### Action Space (typed model)
The EnvAction model supports these action types:
- inspect_service
- inspect_logs
- restart_service
- rollback_service
- scale_service
- update_config
- resolve_incident

Action payload fields:
- service
- key, value
- replicas
- root_cause, remediation

### Observation Format
Observation is a typed model returned by reset(), state(), and step() containing a normalized service snapshot and context for decision making.

### Transitions
- inspect actions add evidence to event log
- restart/rollback/scale/update actions mutate service/config state
- resolve_incident submits diagnosis/remediation text for grader evaluation
- episode ends on success or max step timeout

## Step 3: OpenEnv Implementation

Core environment class:
- devops_openenv/environment.py
- class DevOpsIncidentEnv
- methods: reset(), state(), step()

HTTP API wrapper:
- app.py
- endpoints: /reset, /step, /state, /tasks, /

## Step 4: Task Design (Mandatory)

### Easy Task: incident_easy
Description:
- Restore degraded payment service after memory spike.
Expected behavior:
- Inspect payment service/logs, restart payment, resolve incident.
Success conditions:
- payment healthy
- root cause identifies memory leak
- remediation includes restart + patch plan

### Medium Task: incident_medium
Description:
- Recover checkout failures from a bad deployment.
Expected behavior:
- Inspect checkout service/logs, rollback checkout, resolve incident.
Success conditions:
- checkout healthy and stable version
- root cause identifies bad release
- remediation includes rollback

### Hard Task: incident_hard
Description:
- Resolve cascading API failures caused by DB connection exhaustion.
Expected behavior:
- Inspect API/DB logs, increase max_connections, restart API, resolve incident.
Success conditions:
- db-proxy + api healthy
- root cause identifies connection pool limit
- remediation includes config update + restart

## Step 5: Graders

File:
- devops_openenv/graders.py

Properties:
- Deterministic
- Returns score in [0.0, 1.0]
- Supports partial rewards

Grading components:
- action_coverage (required action completion)
- diagnosis_quality (root cause text quality)
- remediation_quality (remediation text quality)
- service_recovery (operational recovery)

Weighted score:
- 0.40 * action_coverage
- 0.25 * diagnosis_quality
- 0.20 * remediation_quality
- 0.15 * service_recovery

## Step 6: Reward Function

Dense reward is the current graded score after each step:
- reward_t = grader_score(history_1_to_t)

This gives:
- incremental progress signals (not sparse)
- partial completion credit
- normalized score range [0, 1]

## Step 7: inference.py (Strict Format)

File:
- inference.py

Uses required environment variables:
- API_BASE_URL
- MODEL_NAME
- HF_TOKEN

Uses OpenAI client for LLM calls.

STDOUT lines are emitted in strict format:
- [START] task=... env=... model=...
- [STEP] step=... action=... reward=... done=... error=...
- [END] success=... steps=... score=... rewards=...

## Step 8: openenv.yaml

File:
- openenv.yaml

Includes:
- environment name/version/description
- class entrypoint
- API endpoint mapping
- task list with difficulty and grader
- runtime constraints

## Step 9: Dockerfile

File:
- Dockerfile

Characteristics:
- python:3.11-slim base image
- installs pinned dependencies from requirements.txt
- runs uvicorn on port 7860
- lightweight and compatible with 2 vCPU / 8GB RAM constraints

## Step 10: Hugging Face Deployment

### Required files
- app.py
- devops_openenv/ package
- inference.py
- openenv.yaml
- requirements.txt
- Dockerfile
- README.md

### Steps
1. Create a new Hugging Face Space with Docker SDK.
2. Push repository files to Space.
3. Set Space secrets/environment variables:
   - API_BASE_URL
   - MODEL_NAME
   - HF_TOKEN
4. Space will build from Dockerfile.
5. Verify health endpoint returns 200 at /.
6. Verify environment APIs:
   - POST /reset
   - POST /step
   - GET /state

### Exposing endpoints
- Base URL: https://<space-name>.hf.space
- OpenEnv endpoints are available directly on this host via the FastAPI routes above.

## Step 11: Setup and Usage

### Local setup
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Run API server
```bash
uvicorn app:app --host 0.0.0.0 --port 7860
```

### Run inference
```bash
export API_BASE_URL="https://router.huggingface.co/v1"
export MODEL_NAME="Qwen/Qwen2.5-72B-Instruct"
export HF_TOKEN="<your_token>"
python inference.py
```

### API examples
```bash
curl -s http://localhost:7860/
```

```bash
curl -s -X POST http://localhost:7860/reset -H "content-type: application/json" -d '{"task_name":"incident_easy"}'
```

```bash
curl -s -X POST http://localhost:7860/step -H "content-type: application/json" -d '{"action":{"action_type":"inspect_service","service":"payment"}}'
```

## Step 12: Validation Checklist

- step(), reset(), state() are implemented and reachable
- Three tasks exist with easy/medium/hard difficulty
- Graders are deterministic and bounded to [0, 1]
- Inference uses OpenAI client and required env vars
- Inference logs follow START/STEP/END format
- Dockerfile builds and runs the API server
- Runtime is lightweight for competition constraints
- Score outputs are reproducible with deterministic environment logic
