from __future__ import annotations

import json
from typing import Any

from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, StateGraph
from openai import AsyncOpenAI
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.graphs.state import TurnState
from app.models.interview_sessions import InterviewSession
from app.models.interview_turn import InterviewTurn
from app.models.topic_cards import TopicCard
from app.schemas.interview_sessions import (
    InterviewPlan,
    InterviewProgress,
    InterviewReport,
    InterviewStage,
    TurnEvaluation,
)
from app.schemas.resumes import ProjectItem, ResumeProfile
from app.service.interview_decide import decide_next_action

EVALUATE_RETRY = 1
ASK_RETRY = 1

EVALUATE_PROMPT = """
你是模拟面试的评估员。只评估这一轮回答，不要出题，不要给标准答案。
只返回 JSON:
{
  "covered": ["要点id"],
  "missing": ["要点id"],
  "depth": "shallow | adequate | deep",
  "vague_quotes": ["从回答里摘的含糊原话"],
  "said_dont_know": false,
  "off_topic": false
}
covered/missing 只能使用提供的要点 id。depth 只能是 shallow/adequate/deep。
"""

ASK_PROMPT = """
你是模拟面试官。根据指定动作生成下一问，只返回 JSON:{"question": "..."}
约束：
- 只做简短承接，不评价对错，不说出答案。
- 不编造简历里没有的经历。
- 不要把考点卡原文当题面念出来。
- 一到两句话，口语化。
"""


class SessionNotFoundError(Exception):
    pass


class SessionConflictError(Exception):
    pass


class TurnPipelineError(Exception):
    pass


class _AskOutput(BaseModel):
    question: str = Field(min_length=1, max_length=2048)


def _cfg(config: RunnableConfig) -> dict[str, Any]:
    configurable = config.get("configurable") or {}
    return configurable


def _dump_card(card: TopicCard | None) -> dict[str, Any] | None:
    if card is None:
        return None
    return {
        "key": card.key,
        "name": card.name,
        "summary": card.summary,
        "key_points": card.key_points,
        "probe_path": card.probe_path,
        "pitfalls": card.pitfalls,
    }


def _find_project(profile: ResumeProfile, anchor: str | None) -> ProjectItem | None:
    if not anchor:
        return None
    for item in profile.projects:
        if item.name == anchor:
            return item
    return None


def _rubric(
    stage: InterviewStage,
    profile: ResumeProfile,
    card: dict[str, Any] | None,
) -> list[dict[str, str]]:
    if card and card.get("key_points"):
        return [
            {"id": point["id"], "text": point["text"]}
            for point in card["key_points"]
        ]
    if stage.kind == "project_probe":
        project = _find_project(profile, stage.resume_anchor)
        highlights = project.highlights if project else []
        return [{"id": f"h{index}", "text": text} for index, text in enumerate(highlights)]
    if stage.kind == "intro":
        return [{"id": "intro", "text": "自我介绍是否结合最近项目或经历"}]
    if stage.kind == "closing":
        return [{"id": "closing", "text": "是否正常收尾或提出问题"}]
    return [{"id": "g1", "text": stage.goal}]


def _stub_evaluation(stage: InterviewStage) -> TurnEvaluation:
    point_id = "intro" if stage.kind == "intro" else "closing"
    return TurnEvaluation(
        covered=[point_id],
        missing=[],
        depth="adequate",
        vague_quotes=[],
        said_dont_know=False,
        off_topic=False,
    )


def _probe_step(card: dict[str, Any] | None, turn_in_stage: int) -> dict[str, str] | None:
    path = (card or {}).get("probe_path") or []
    if not path:
        return None
    index = min(max(turn_in_stage - 1, 0), len(path) - 1)
    return path[index]


async def _load_card(db: AsyncSession, key: str | None) -> TopicCard | None:
    if not key:
        return None
    result = await db.execute(select(TopicCard).where(TopicCard.key == key))
    return result.scalar_one_or_none()


async def load_session(state: TurnState, config: RunnableConfig) -> dict[str, Any]:
    cfg = _cfg(config)
    db: AsyncSession = cfg["db"]
    user_id: int = cfg["user_id"]
    session_id = state["session_id"]

    result = await db.execute(
        select(InterviewSession).where(
            InterviewSession.id == session_id,
            InterviewSession.user_id == user_id,
        )
    )
    session_row = result.scalar_one_or_none()
    if session_row is None:
        raise SessionNotFoundError()
    if session_row.status != "in_progress":
        raise SessionConflictError()

    turns_result = await db.execute(
        select(InterviewTurn)
        .where(InterviewTurn.session_id == session_id)
        .order_by(InterviewTurn.seq.asc())
    )
    turns = list(turns_result.scalars().all())
    pending = next((turn for turn in turns if turn.answer == ""), None)
    if pending is None:
        raise SessionConflictError()

    progress = InterviewProgress.model_validate(session_row.progress)
    plan = InterviewPlan.model_validate(session_row.plan)
    stage = plan.stages[progress.stage_index]
    card = await _load_card(db, stage.topic_card_key)

    return {
        "resume_snapshot": session_row.resume_snapshot,
        "plan": session_row.plan,
        "progress": session_row.progress,
        "current_card": _dump_card(card),
        "pending_seq": pending.seq,
        "pending_question": pending.question,
        "recent_turns": [
            {
                "seq": turn.seq,
                "stage_index": turn.stage_index,
                "action": turn.action,
                "question": turn.question,
                "answer": turn.answer,
                "evaluation": turn.evaluation,
            }
            for turn in turns
        ],
    }


async def evaluate(state: TurnState, config: RunnableConfig) -> dict[str, Any]:
    cfg = _cfg(config)
    llm_client: AsyncOpenAI = cfg["llm_client"]
    plan = InterviewPlan.model_validate(state["plan"])
    progress = InterviewProgress.model_validate(state["progress"])
    stage = plan.stages[progress.stage_index]
    profile = ResumeProfile.model_validate(state["resume_snapshot"])

    if stage.kind in ("intro", "closing"):
        return {"evaluation": _stub_evaluation(stage).model_dump()}

    payload = {
        "stage": {
            "kind": stage.kind,
            "goal": stage.goal,
            "resume_anchor": stage.resume_anchor,
        },
        "question": state["pending_question"],
        "answer": state["answer"],
        "key_points": _rubric(stage, profile, state.get("current_card")),
    }
    last_error: Exception | None = None
    for _ in range(EVALUATE_RETRY + 1):
        try:
            completion = await llm_client.chat.completions.create(
                model=settings.llm_model_light,
                messages=[
                    {"role": "system", "content": EVALUATE_PROMPT},
                    {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
                ],
                response_format={"type": "json_object"},
            )
            raw = completion.choices[0].message.content
            if not raw:
                raise TurnPipelineError("empty evaluation")
            evaluation = TurnEvaluation.model_validate_json(raw)
            return {"evaluation": evaluation.model_dump()}
        except Exception as exc:
            last_error = exc
    raise TurnPipelineError(str(last_error) if last_error else "evaluation failed")


def decide(state: TurnState) -> dict[str, Any]:
    plan = InterviewPlan.model_validate(state["plan"])
    progress = InterviewProgress.model_validate(state["progress"])
    stage = plan.stages[progress.stage_index]
    evaluation = TurnEvaluation.model_validate(state["evaluation"])
    card = state.get("current_card")
    probe_path_len = len((card or {}).get("probe_path") or [])
    already_hinted = any(
        item.get("stage_index") == progress.stage_index and item.get("action") == "hint"
        for item in state.get("recent_turns") or []
    )
    action, next_progress = decide_next_action(
        stage=stage,
        stages_count=len(plan.stages),
        progress=progress,
        evaluation=evaluation,
        already_hinted=already_hinted,
        probe_path_len=probe_path_len,
    )
    return {"action": action, "next_progress": next_progress.model_dump()}


def route_after_decide(state: TurnState) -> str:
    return "report" if state.get("action") == "end" else "ask"


def report(state: TurnState) -> dict[str, Any]:
    covered: list[str] = []
    missing: list[str] = []
    dont_know = 0
    evaluations = [
        item.get("evaluation")
        for item in state.get("recent_turns") or []
        if item.get("evaluation")
    ]
    if state.get("evaluation"):
        evaluations.append(state["evaluation"])
    for raw in evaluations:
        item = TurnEvaluation.model_validate(raw)
        covered.extend(item.covered)
        missing.extend(item.missing)
        if item.said_dont_know:
            dont_know += 1
    built = InterviewReport(
        covered=sorted(set(covered)),
        missing=sorted(set(missing)),
        said_dont_know_count=dont_know,
    )
    return {"report": built.model_dump(), "question": None}


async def ask(state: TurnState, config: RunnableConfig) -> dict[str, Any]:
    cfg = _cfg(config)
    db: AsyncSession = cfg["db"]
    llm_client: AsyncOpenAI = cfg["llm_client"]
    plan = InterviewPlan.model_validate(state["plan"])
    next_progress = InterviewProgress.model_validate(state["next_progress"])
    stage = plan.stages[next_progress.stage_index]
    profile = ResumeProfile.model_validate(state["resume_snapshot"])

    if stage.kind == "closing":
        return {"question": "今天的面试先到这里，你有想问我的吗？"}

    card = state.get("current_card")
    if state.get("action") == "next_stage":
        loaded = await _load_card(db, stage.topic_card_key)
        card = _dump_card(loaded)

    recent = [
        {
            "seq": item.get("seq"),
            "question": item.get("question"),
            "answer": item.get("answer"),
            "action": item.get("action"),
        }
        for item in state.get("recent_turns") or []
        if item.get("answer")
    ]
    recent.append(
        {
            "seq": state["pending_seq"],
            "question": state["pending_question"],
            "answer": state["answer"],
            "action": "current",
        }
    )
    project = _find_project(profile, stage.resume_anchor)
    payload = {
        "action": state["action"],
        "stage": {
            "kind": stage.kind,
            "goal": stage.goal,
            "resume_anchor": stage.resume_anchor,
        },
        "evaluation": state.get("evaluation"),
        "recent_turns": recent[-3:],
        "resume_skills": profile.skills,
        "project": project.model_dump() if project is not None else None,
        "card": (
            {
                "key": card.get("key"),
                "name": card.get("name"),
                "probe_step": _probe_step(card, next_progress.turn_in_stage),
                "pitfalls": card.get("pitfalls"),
            }
            if card
            else None
        ),
    }
    last_error: Exception | None = None
    for _ in range(ASK_RETRY + 1):
        try:
            completion = await llm_client.chat.completions.create(
                model=settings.llm_model_light,
                messages=[
                    {"role": "system", "content": ASK_PROMPT},
                    {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
                ],
                response_format={"type": "json_object"},
            )
            raw = completion.choices[0].message.content
            if not raw:
                raise TurnPipelineError("empty question")
            question = _AskOutput.model_validate_json(raw).question
            return {"question": question, "current_card": card}
        except Exception as exc:
            last_error = exc
    raise TurnPipelineError(str(last_error) if last_error else "ask failed")


async def persist(state: TurnState, config: RunnableConfig) -> dict[str, Any]:
    cfg = _cfg(config)
    db: AsyncSession = cfg["db"]
    session_id = state["session_id"]

    session_row = (
        await db.execute(select(InterviewSession).where(InterviewSession.id == session_id))
    ).scalar_one()
    current = (
        await db.execute(
            select(InterviewTurn).where(
                InterviewTurn.session_id == session_id,
                InterviewTurn.seq == state["pending_seq"],
            )
        )
    ).scalar_one()

    current.answer = state["answer"]
    current.evaluation = state.get("evaluation")
    session_row.progress = state["next_progress"]

    if state.get("action") == "end":
        session_row.status = "completed"
        await db.commit()
        return {}

    db.add(
        InterviewTurn(
            session_id=session_id,
            seq=state["pending_seq"] + 1,
            stage_index=state["next_progress"]["stage_index"],
            action=state["action"],
            question=state["question"] or "",
            answer="",
            evaluation=None,
        )
    )
    await db.commit()
    return {}


def build_turn_graph():
    graph = StateGraph(TurnState)
    graph.add_node("load_session", load_session)
    graph.add_node("evaluate", evaluate)
    graph.add_node("decide", decide)
    graph.add_node("ask", ask)
    graph.add_node("report", report)
    graph.add_node("persist", persist)

    graph.add_edge(START, "load_session")
    graph.add_edge("load_session", "evaluate")
    graph.add_edge("evaluate", "decide")
    graph.add_conditional_edges(
        "decide",
        route_after_decide,
        {"ask": "ask", "report": "report"},
    )
    graph.add_edge("ask", "persist")
    graph.add_edge("report", "persist")
    graph.add_edge("persist", END)
    return graph.compile()