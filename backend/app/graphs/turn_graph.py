from __future__ import annotations

import asyncio
import contextvars
import json
from typing import Any

from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, StateGraph
from openai import AsyncOpenAI
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import get_logger
from app.graphs.state import TurnState
from app.models.interview_sessions import InterviewSession
from app.models.interview_turn import InterviewTurn
from app.models.topic_cards import TopicCard
from app.schemas.interviews import (
    InterviewPlan,
    InterviewProgress,
    InterviewStage,
    TurnEvaluation,
)
from app.schemas.resumes import ProjectItem, ResumeProfile
from app.service.interview_decide import decide_next_action
from app.service.interview_score import build_interview_report, gate_evaluation

logger = get_logger()
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
  "off_topic": false,
  "score": 0,
  "comment": "本轮 0 分。一到两句扣分或得分理由。"
}
covered/missing 只能使用提供的要点 id。depth 只能是 shallow/adequate/deep。
score 是 0-100 的整数，必须和 depth、覆盖情况同向：
- shallow：0-50
- adequate：40-85
- deep：70-100
- said_dont_know 为 true 时不超过 30
- off_topic 为 true 时不超过 40
comment 必须以「本轮 {score} 分。」开头，接着写一两句理由，只解释本轮，不泄露标准答案。
comment 里的分数必须等于 score。
"""

ASK_PROMPT = """
你是模拟面试官。根据指定动作生成下一问。
只输出问题原文，不要 JSON，不要 markdown，不要前后引号或书名号。
约束：
- 不要客套，不要「好」「先到这儿」「那咱们换个方向聊聊」「接下来考一下」这类垫话。
- follow_up、hint：回答有错漏、跑题或含糊时，用半句点出问题所在，然后立刻追问。点问题要具体，对照 missing、vague_quotes、off_topic。不要把正确答案讲出来，不要报分数。
- next_stage、deepen、first：直接提问，不要点评上一题。
- 不编造简历里没有的经历。
- 不要把考点卡原文当题面念出来。
- 不要复述或粘贴候选人的自我介绍、上一轮长段原话。
- 一两句口语。
"""

ASK_STYLE = {
    "follow_up": "回答有错漏或含糊时，先用半句点出问题，再追问。不要给标准答案，不要报分数，不要客套。",
    "hint": "点出卡在哪里，给思考方向，不要把答案讲出来，不要报分数，不要客套。",
    "deepen": "直接往深处问。不要夸奖，不要客套。",
    "next_stage": "不要点评上一题，不要客套过渡，第一句就是新问题。",
    "first": "直接提问，不要客套。",
}

sse_token_queue: contextvars.ContextVar[asyncio.Queue[tuple[str, dict[str, Any]] | None] | None] = (
    contextvars.ContextVar("sse_token_queue", default=None)
)

CLOSING_QUESTION = "今天的面试先到这里，你有想问我的吗？"
TEMPLATE_CHUNK_INTERVAL = 0.024


class SessionNotFoundError(Exception):
    pass


class SessionConflictError(Exception):
    pass


class TurnPipelineError(Exception):
    pass


# 从langGraph 配置中取出数据库会话，用户编号和模型客户端
def _cfg(config: RunnableConfig) -> dict[str, Any]:
    configurable = config.get("configurable") or {}
    return configurable

# 靠点卡->字典
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

# 简历项目匹配
def _find_project(profile: ResumeProfile, anchor: str | None) -> ProjectItem | None:
    if not anchor:
        return None
    for item in profile.projects:
        if item.name == anchor:
            return item
    return None

# 根据阶段、简历、点卡生成评估标准
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

# 开场和收尾的评估
def _stub_evaluation(stage: InterviewStage) -> TurnEvaluation:
    point_id = "intro" if stage.kind == "intro" else "closing"
    comment = (
        "完成了开场自我介绍。"
        if stage.kind == "intro"
        else "完成了收尾。"
    )
    return gate_evaluation(
        TurnEvaluation(
            covered=[point_id],
            missing=[],
            depth="adequate",
            vague_quotes=[],
            said_dont_know=False,
            off_topic=False,
            score=75,
            comment=comment,
        )
    )


def _probe_step(card: dict[str, Any] | None, turn_in_stage: int) -> dict[str, str] | None:
    path = (card or {}).get("probe_path") or []
    if not path:
        return None
    index = min(max(turn_in_stage - 1, 0), len(path) - 1)
    return path[index]

# 按照考点卡查找已发布卡片
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
    session_id = state["session_id"]
    for attempt in range(EVALUATE_RETRY + 1):
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
            evaluation = gate_evaluation(TurnEvaluation.model_validate_json(raw))
            return {"evaluation": evaluation.model_dump()}
        except Exception as exc:
            last_error = exc
            logger.warning(
                "evaluate retry session_id=%s attempt=%s error=%s",
                session_id,
                attempt + 1,
                exc,
            )
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

# 综合各轮评估为报告。
def report(state: TurnState) -> dict[str, Any]:
    plan = InterviewPlan.model_validate(state["plan"])
    progress = InterviewProgress.model_validate(state["progress"])
    items: list[tuple[int, TurnEvaluation]] = []
    for item in state.get("recent_turns") or []:
        raw = item.get("evaluation")
        if not raw:
            continue
        items.append((int(item["stage_index"]), TurnEvaluation.model_validate(raw)))
    if state.get("evaluation"):
        items.append((progress.stage_index, TurnEvaluation.model_validate(state["evaluation"])))
    built = build_interview_report(plan=plan, items=items)
    return {"report": built.model_dump(), "question": None}


def _token_queue(config: RunnableConfig) -> asyncio.Queue[tuple[str, dict[str, Any]] | None] | None:
    return sse_token_queue.get() or _cfg(config).get("token_queue")


async def _emit_sse(config: RunnableConfig, event: str, data: dict[str, Any]) -> None:
    queue = _token_queue(config)
    if queue is None:
        return
    await queue.put((event, data))


def _normalize_question(raw: str) -> str:
    text = raw.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    if len(text) >= 2 and (
        (text[0] == text[-1] and text[0] in {'"', "'"})
        or (text.startswith("「") and text.endswith("」"))
    ):
        text = text[1:-1].strip()
    if text.startswith("{"):
        try:
            parsed = json.loads(text)
            if isinstance(parsed, dict) and parsed.get("question"):
                text = str(parsed["question"]).strip()
        except json.JSONDecodeError:
            pass
    return text[:2048]


def _ask_evaluation(raw: dict[str, Any] | None) -> dict[str, Any] | None:
    if not raw:
        return None
    return {
        "covered": raw.get("covered"),
        "missing": raw.get("missing"),
        "depth": raw.get("depth"),
        "vague_quotes": raw.get("vague_quotes"),
        "said_dont_know": raw.get("said_dont_know"),
        "off_topic": raw.get("off_topic"),
    }


def _clip_text(value: str | None, limit: int) -> str:
    text = (value or "").strip()
    if len(text) <= limit:
        return text
    return text[:limit] + "…"


async def _emit_question_chunks(config: RunnableConfig, question: str) -> None:
    if _token_queue(config) is None:
        return
    await _emit_sse(config, "status", {"phase": "asking"})
    for index in range(0, len(question)):
        await _emit_sse(config, "delta", {"text": question[index : index + 1]})
        await asyncio.sleep(TEMPLATE_CHUNK_INTERVAL)


async def _stream_llm_question(
    llm_client: AsyncOpenAI,
    payload: dict[str, Any],
    config: RunnableConfig,
    session_id: int,
) -> str:
    last_error: Exception | None = None
    for attempt in range(ASK_RETRY + 1):
        sent_any = False
        collected: list[str] = []
        try:
            await _emit_sse(config, "status", {"phase": "asking"})
            stream = await llm_client.chat.completions.create(
                model=settings.llm_model_light,
                messages=[
                    {"role": "system", "content": ASK_PROMPT},
                    {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
                ],
                stream=True,
            )
            async for event in stream:
                if not event.choices:
                    continue
                piece = event.choices[0].delta.content
                if not piece:
                    continue
                collected.append(piece)
                sent_any = True
                await _emit_sse(config, "delta", {"text": piece})
            question = _normalize_question("".join(collected))
            if not question:
                raise TurnPipelineError("empty question")
            return question
        except Exception as exc:
            last_error = exc
            logger.warning(
                "ask retry session_id=%s attempt=%s error=%s",
                session_id,
                attempt + 1,
                exc,
            )
            if sent_any:
                break
    raise TurnPipelineError(str(last_error) if last_error else "ask failed")


async def ask(state: TurnState, config: RunnableConfig) -> dict[str, Any]:
    cfg = _cfg(config)
    db: AsyncSession = cfg["db"]
    llm_client: AsyncOpenAI = cfg["llm_client"]
    plan = InterviewPlan.model_validate(state["plan"])
    next_progress = InterviewProgress.model_validate(state["next_progress"])
    stage = plan.stages[next_progress.stage_index]
    profile = ResumeProfile.model_validate(state["resume_snapshot"])

    card = state.get("current_card")
    if state.get("action") == "next_stage":
        loaded = await _load_card(db, stage.topic_card_key)
        card = _dump_card(loaded)

    if stage.kind == "closing":
        await _emit_question_chunks(config, CLOSING_QUESTION)
        return {"question": CLOSING_QUESTION, "current_card": card}

    recent: list[dict[str, Any]] = []
    for item in state.get("recent_turns") or []:
        if not item.get("answer"):
            continue
        seq = item.get("seq")
        limit = 400 if seq == state["pending_seq"] else 60
        recent.append(
            {
                "seq": seq,
                "question": item.get("question"),
                "answer": _clip_text(str(item.get("answer") or ""), limit),
                "action": item.get("action"),
            }
        )
    recent.append(
        {
            "seq": state["pending_seq"],
            "question": state["pending_question"],
            "answer": _clip_text(state["answer"], 400),
            "action": "current",
        }
    )
    recent = recent[-3:]
    project = _find_project(profile, stage.resume_anchor)
    payload = {
        "action": state["action"],
        "style": ASK_STYLE.get(str(state.get("action") or ""), "不要客套，直接提问。"),
        "stage": {
            "kind": stage.kind,
            "goal": stage.goal,
            "resume_anchor": stage.resume_anchor,
        },
        "evaluation": _ask_evaluation(state.get("evaluation")),
        "recent_turns": recent,
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
    question = await _stream_llm_question(
        llm_client, payload, config, state["session_id"]
    )
    return {"question": question, "current_card": card}

# 本轮回答和评估写回数据库
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
        session_row.report = state.get("report")
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