from __future__ import annotations

from dataclasses import dataclass
from typing import List

from devops_openenv.models import ActionType, EnvAction, IncidentTask


@dataclass
class GradeBreakdown:
    score: float
    action_coverage: float
    diagnosis_quality: float
    remediation_quality: float
    service_recovery: float


class IncidentGrader:
    """Deterministic grader with dense, normalized rewards in [0, 1]."""

    def __init__(self, task: IncidentTask):
        self.task = task

    def score_progress(self, actions: List[EnvAction], recovered: bool) -> GradeBreakdown:
        required = self.task.required_actions
        completed = set(a.action_type for a in actions)
        coverage = sum(1 for a in required if a in completed) / float(len(required))

        diagnosis_quality = 0.0
        remediation_quality = 0.0

        resolve_actions = [a for a in actions if a.action_type == ActionType.RESOLVE_INCIDENT]
        if resolve_actions:
            resolve = resolve_actions[-1]
            root = (resolve.root_cause or "").lower()
            rem = (resolve.remediation or "").lower()

            expected_root = self.task.solution_root_cause.lower()
            expected_rem = self.task.solution_remediation.lower()

            diagnosis_quality = 1.0 if expected_root in root else 0.5 if any(
                token in root for token in expected_root.split()
            ) else 0.0

            remediation_quality = 1.0 if expected_rem in rem else 0.5 if any(
                token in rem for token in expected_rem.split()
            ) else 0.0

        service_recovery = 1.0 if recovered else 0.0

        raw = (
            0.40 * coverage
            + 0.25 * diagnosis_quality
            + 0.20 * remediation_quality
            + 0.15 * service_recovery
        )

        return GradeBreakdown(
            score=max(0.0, min(1.0, raw)),
            action_coverage=coverage,
            diagnosis_quality=diagnosis_quality,
            remediation_quality=remediation_quality,
            service_recovery=service_recovery,
        )


def grade_task(task: IncidentTask, actions: List[EnvAction], recovered: bool) -> dict[str, float]:
    breakdown = IncidentGrader(task).score_progress(actions=actions, recovered=recovered)
    return {
        "score": round(breakdown.score, 4),
        "action_coverage": round(breakdown.action_coverage, 4),
        "diagnosis_quality": round(breakdown.diagnosis_quality, 4),
        "remediation_quality": round(breakdown.remediation_quality, 4),
        "service_recovery": round(breakdown.service_recovery, 4),
    }
