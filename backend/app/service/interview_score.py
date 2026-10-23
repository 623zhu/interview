from __future__ import annotations

import re
from collections import defaultdict

from app.schemas.interviews import (
    InterviewPlan,
    InterviewReport,
    StageKind,
    StageScore,
    TurnEvaluation,
)

DEPTH_SCORE_RANGE: dict[str, tuple[int, int]] = {
    "shallow": (0, 50),
    "adequate": (40, 85),
    "deep": (70, 100),
}
DONT_KNOW_MAX = 30
OFF_TOPIC_MAX = 40
SCORED_KIND_WEIGHTS: dict[StageKind, float] = {
    "project_probe": 0.35,
    "fundamentals": 0.30,
    "scenario": 0.35,
}
STAGE_SCORE_ORDER: tuple[StageKind, ...] = (
    "project_probe",
    "fundamentals",
    "scenario",
)
_LEADING_SCORE = re.compile(r"^(?:本轮\s*)?\d{1,3}\s*分[。.\s:：]*")


def _fallback_score(evaluation: TurnEvaluation) -> int:
    denom = len(evaluation.covered) + len(evaluation.missing)
    coverage = (len(evaluation.covered) / denom) if denom else 0.5
    depth_mid = {"shallow": 25, "adequate": 62, "deep": 85}[evaluation.depth]
    return round(100 * (0.6 * coverage + 0.4 * (depth_mid / 100)))


def clamp_turn_score(evaluation: TurnEvaluation) -> int:
    score = evaluation.score if evaluation.score is not None else _fallback_score(evaluation)
    lo, hi = DEPTH_SCORE_RANGE[evaluation.depth]
    score = min(max(score, lo), hi)
    if evaluation.said_dont_know:
        score = min(score, DONT_KNOW_MAX)
    if evaluation.off_topic:
        score = min(score, OFF_TOPIC_MAX)
    return int(score)


def align_comment(comment: str | None, score: int) -> str:
    rest = _LEADING_SCORE.sub("", (comment or "").strip())
    if not rest:
        rest = "已记录本轮表现。"
    return f"本轮 {score} 分。{rest}"[:512]


def gate_evaluation(evaluation: TurnEvaluation) -> TurnEvaluation:
    score = clamp_turn_score(evaluation)
    return evaluation.model_copy(update={"score": score, "comment": align_comment(evaluation.comment, score)})


def build_interview_report(
    *,
    plan: InterviewPlan,
    items: list[tuple[int, TurnEvaluation]],
) -> InterviewReport:
    covered: list[str] = []
    missing: list[str] = []
    dont_know = 0
    scores_by_index: dict[int, list[int]] = defaultdict(list)

    gated: list[tuple[int, TurnEvaluation]] = [
        (stage_index, gate_evaluation(evaluation)) for stage_index, evaluation in items
    ]
    for stage_index, evaluation in gated:
        covered.extend(evaluation.covered)
        missing.extend(evaluation.missing)
        if evaluation.said_dont_know:
            dont_know += 1
        if evaluation.score is not None:
            scores_by_index[stage_index].append(evaluation.score)

    kind_avgs: dict[str, list[float]] = defaultdict(list)
    for stage_index, scores in scores_by_index.items():
        if stage_index >= len(plan.stages):
            continue
        kind = plan.stages[stage_index].kind
        kind_avgs[kind].append(sum(scores) / len(scores))

    collapsed = {kind: sum(values) / len(values) for kind, values in kind_avgs.items()}
    stages = [
        StageScore(kind=kind, score=int(round(collapsed[kind])))
        for kind in STAGE_SCORE_ORDER
        if kind in collapsed
    ]
    weight_sum = sum(SCORED_KIND_WEIGHTS[item.kind] for item in stages)
    total = (
        0
        if weight_sum <= 0
        else round(sum(item.score * SCORED_KIND_WEIGHTS[item.kind] for item in stages) / weight_sum)
    )
    return InterviewReport(
        score=max(0, min(100, total)),
        stages=stages,
        covered=sorted(set(covered)),
        missing=sorted(set(missing)),
        said_dont_know_count=dont_know,
    )
