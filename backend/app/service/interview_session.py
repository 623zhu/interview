from __future__ import annotations

import json
import random
from datetime import datetime, timezone
from typing import Any

from openai import AsyncOpenAI
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.interview_sessions import InterviewSession
from app.models.interview_turn import InterviewTurn   
from app.models.resumes import Resume
from app.models.topic_cards import TopicCard
from app.schemas.interviews import (
    CurrentTurn,
    Difficulty,
    InterviewPlan,
    InterviewProgress,
    InterviewReport,
    InterviewSessionCreateResponse,
    InterviewSessionGetResponse,
    InterviewSessionListItem,
    InterviewStage,
    InterviewTurnPublic,
    SessionStatus,
    TurnEvaluation,
)
from app.schemas.resumes import ResumeProfile
from app.service.interview_score import build_interview_report, gate_evaluation

MAX_CANDIDATE_CARDS = 12
PLAN_RETRY = 1
INTRO_QUESTION = "先做个一分钟自我介绍吧，可以结合你最近的项目。"
DIFFICULTY_RANK = {"easy": 0, "medium": 1, "hard": 2}
SCENARIO_SKILL_TAGS = {"mq", "http", "distributed"}

GENERATE_PLAN_PROMPT = """
你是模拟面试的出题策划。根据候选人简历快照和候选考点卡，为本场面试填写中间阶段。
只返回 JSON,不要 markdown。
只能使用提供的项目名、经历和卡片 key,不要编造简历里没有的经历,不要使用未提供的卡片。

JSON 形状：
{
  "project_probe": {
    "goal": "本阶段考察目标",
    "max_turns": 4,
    "resume_anchor": "项目名或公司名，没有可用锚点时为 null"
  },
  "fundamentals": [
    {"goal": "考察目标", "max_turns": 3, "topic_card_key": "候选卡 key"},
    {"goal": "考察目标", "max_turns": 2, "topic_card_key": "另一个候选卡 key"}
  ],
  "scenario": {
    "goal": "考察目标",
    "max_turns": 3,
    "topic_card_key": "候选卡 key",
    "resume_anchor": "能联系上的项目名，没有则为 null"
  }
}

约束：
- fundamentals 必须恰好 2 条,key 互不相同，且都在候选卡里。
- scenario 的 key 在候选卡里，且不能与 fundamentals 重复。
- project_probe.max_turns 取 3-5;fundamentals 取 2-3;scenario 取 3-4。
- resume_anchor 必须是 allowed_anchors 中的一项，或为 null。
"""


class ResumeNotFoundError(Exception):
    pass


class ResumeNotReadyError(Exception):
    pass


class PlanGenerationError(Exception):
    pass


class _PlanProjectProbe(BaseModel):
    goal: str = Field(min_length=1)
    max_turns: int = Field(ge=3, le=5)
    resume_anchor: str | None = None


class _PlanBankStage(BaseModel):
    goal: str = Field(min_length=1)
    max_turns: int
    topic_card_key: str = Field(min_length=1)
    resume_anchor: str | None = None


class _GeneratedMiddlePlan(BaseModel):
    project_probe: _PlanProjectProbe
    fundamentals: list[_PlanBankStage] = Field(min_length=2, max_length=2)
    scenario: _PlanBankStage

# 小写化以及去空格化
def _normalize_tag(value: str) -> str:
    return "".join(value.lower().split())


def role_tags_for(target_role: str) -> list[str]:
    text = _normalize_tag(target_role)
    tags: set[str] = set()
    if "java" in text:
        tags.add("java")
    if "backend" in text or "后端" in target_role:
        tags.add("backend")
    if not tags:
        tags.update({"backend", "java"})
    return sorted(tags)


# 把题库标签归一化，比如把 springboot 归一化为 spring,把 rabbitmq 归一化为 mq。
def normalize_skills(skills: list[str]) -> set[str]:
    aliases = {
        "springboot": "spring",
        "springframework": "spring",
        "rabbitmq": "mq",
        "kafka": "mq",
        "rocketmq": "mq",
        "activemq": "mq",
        "jvm": "jvm",
        "mysql": "mysql",
        "redis": "redis",
        "http": "http",
    }
    result: set[str] = set()
    for skill in skills:
        key = _normalize_tag(skill)
        if not key:
            continue
        result.add(aliases.get(key, key))
        if "spring" in key:
            result.add("spring")
        if "mysql" in key:
            result.add("mysql")
        if "redis" in key:
            result.add("redis")
        if "java" in key:
            result.add("java")
    return result

# 根据难度等级，返回允许的难度等级集合
def _allowed_difficulties(difficulty: Difficulty) -> set[str]:
    cap = DIFFICULTY_RANK[difficulty]
    return {name for name, rank in DIFFICULTY_RANK.items() if rank <= cap}

# 判断是否是场景题
def _is_scenario_card(card: TopicCard) -> bool:
    return bool(set(card.skill_tags or []) & SCENARIO_SKILL_TAGS)

# 判断卡片是否匹配
def _card_matches(
    card: TopicCard,
    role_tags: list[str],
    resume_skills: set[str],
    allowed_difficulties: set[str],
) -> bool:
    if card.difficulty not in allowed_difficulties:
        return False
    if not set(card.role_tags or []) & set(role_tags):
        return False
    if _is_scenario_card(card):
        return True
    return bool(set(card.skill_tags or []) & resume_skills)

# 获取简历中的项目名和公司名
def _anchors(profile: ResumeProfile) -> list[str]:
    projects = [item.name.strip() for item in profile.projects if item.name and item.name.strip()]
    if projects:
        return projects
    companies = [
        item.company.strip()
        for item in profile.experience
        if item.company and item.company.strip()
    ]
    if companies:
        return companies
    return [skill.strip() for skill in profile.skills if skill.strip()][:3]

# 将卡片信息转换为 JSON 格式
def _candidate_payload(cards: list[TopicCard]) -> list[dict[str, Any]]:
    return [
        {
            "key": card.key,
            "name": card.name,
            "summary": card.summary,
            "difficulty": card.difficulty,
            "skill_tags": card.skill_tags,
        }
        for card in cards
    ]

# 加载简历
async def load_resume(
    db: AsyncSession,
    user_id: int,
    resume_id: int,
) -> tuple[Resume, ResumeProfile]:
    result = await db.execute(
        select(Resume).where(Resume.id == resume_id, Resume.user_id == user_id)
    )
    resume = result.scalar_one_or_none()
    if resume is None:
        raise ResumeNotFoundError()
    if resume.status != "ready" or not resume.profile:
        raise ResumeNotReadyError()
    return resume, ResumeProfile.model_validate(resume.profile)

# 从题库中选择卡片
async def pick_cards(
    db: AsyncSession,
    role_tags: list[str],
    resume_skills: set[str],
    difficulty: Difficulty,
) -> list[TopicCard]:
    result = await db.execute(select(TopicCard).where(TopicCard.status == "published"))
    published = list(result.scalars().all())
    allowed = _allowed_difficulties(difficulty)
    matched = [
        card
        for card in published
        if _card_matches(card, role_tags, resume_skills, allowed)
    ]
    random.shuffle(matched)
    return matched[:MAX_CANDIDATE_CARDS]

# 构建面试计划
def _build_plan(
    middle: _GeneratedMiddlePlan,
    candidate_keys: set[str],
    allowed_anchors: list[str],
) -> InterviewPlan:
    fund_keys = [item.topic_card_key for item in middle.fundamentals]
    if len(set(fund_keys)) != 2:
        raise PlanGenerationError("fundamentals keys must be unique")
    if middle.scenario.topic_card_key in fund_keys:
        raise PlanGenerationError("scenario key overlaps fundamentals")

    used_keys = set(fund_keys) | {middle.scenario.topic_card_key}
    if not used_keys <= candidate_keys:
        raise PlanGenerationError("plan referenced unknown topic_card_key")

    if middle.fundamentals[0].max_turns not in (2, 3) or middle.fundamentals[1].max_turns not in (2, 3):
        raise PlanGenerationError("fundamentals max_turns must be 2 or 3")
    if middle.scenario.max_turns not in (3, 4):
        raise PlanGenerationError("scenario max_turns must be 3 or 4")

    for stage in (middle.project_probe, middle.scenario):
        if stage.resume_anchor and stage.resume_anchor not in allowed_anchors:
            raise PlanGenerationError("resume_anchor is not in the resume")

    return InterviewPlan(
        stages=[
            InterviewStage(
                id="s1",
                kind="intro",
                goal="一分钟自我介绍，接到最近项目或经历",
                max_turns=1,
                source="resume",
            ),
            InterviewStage(
                id="s2",
                kind="project_probe",
                goal=middle.project_probe.goal,
                max_turns=middle.project_probe.max_turns,
                source="resume",
                resume_anchor=middle.project_probe.resume_anchor,
            ),
            InterviewStage(
                id="s3",
                kind="fundamentals",
                goal=middle.fundamentals[0].goal,
                max_turns=middle.fundamentals[0].max_turns,
                source="bank",
                topic_card_key=middle.fundamentals[0].topic_card_key,
            ),
            InterviewStage(
                id="s4",
                kind="fundamentals",
                goal=middle.fundamentals[1].goal,
                max_turns=middle.fundamentals[1].max_turns,
                source="bank",
                topic_card_key=middle.fundamentals[1].topic_card_key,
            ),
            InterviewStage(
                id="s5",
                kind="scenario",
                goal=middle.scenario.goal,
                max_turns=middle.scenario.max_turns,
                source="bank",
                resume_anchor=middle.scenario.resume_anchor,
                topic_card_key=middle.scenario.topic_card_key,
            ),
            InterviewStage(
                id="s6",
                kind="closing",
                goal="收尾，请候选人提问",
                max_turns=1,
                source="resume",
            ),
        ]
    )

# 生成面试计划
async def generate_plan(
    llm_client: AsyncOpenAI,
    profile: ResumeProfile,
    target_role: str,
    difficulty: Difficulty,
    candidate_cards: list[TopicCard],
) -> InterviewPlan:
    if len(candidate_cards) < 3:
        raise PlanGenerationError("not enough topic cards")

    allowed_anchors = _anchors(profile)
    candidate_keys = {card.key for card in candidate_cards}
    user_payload = {
        "target_role": target_role,
        "difficulty": difficulty,
        "profile": profile.model_dump(),
        "allowed_anchors": allowed_anchors,
        "candidate_cards": _candidate_payload(candidate_cards),
    }
    last_error: Exception | None = None
    for _ in range(PLAN_RETRY + 1):
        try:
            completion = await llm_client.chat.completions.create(
                model=settings.llm_model_heavy,
                messages=[
                    {"role": "system", "content": GENERATE_PLAN_PROMPT},
                    {
                        "role": "user",
                        "content": json.dumps(user_payload, ensure_ascii=False),
                    },
                ],
                response_format={"type": "json_object"},
            )
            raw = completion.choices[0].message.content
            if not raw:
                raise PlanGenerationError("empty plan")
            middle = _GeneratedMiddlePlan.model_validate_json(raw)
            return _build_plan(middle, candidate_keys, allowed_anchors)
        except Exception as exc:
            last_error = exc
    raise PlanGenerationError(str(last_error) if last_error else "plan generation failed")

# 生成第一个问题
def ask_first_question() -> str:
    return INTRO_QUESTION

# 持久化面试会话
async def persist_session(
    db: AsyncSession,
    user_id: int,
    resume: Resume,
    profile: ResumeProfile,
    target_role: str,
    difficulty: Difficulty,
    plan: InterviewPlan,
    question: str,
) -> InterviewSessionCreateResponse:
    progress = InterviewProgress(
        stage_index=0,
        turn_in_stage=1,
        consecutive_misses=0,
        used_card_keys=[
            stage.topic_card_key for stage in plan.stages if stage.topic_card_key
        ],
    )
    session_row = InterviewSession(
        user_id=user_id,
        resume_id=resume.id,
        target_role=target_role,
        difficulty=difficulty,
        status="in_progress",
        resume_snapshot=profile.model_dump(),
        plan=plan.model_dump(),
        progress=progress.model_dump(),
    )
    db.add(session_row)
    await db.flush()

    db.add(
        InterviewTurn(
            session_id=session_row.id,
            seq=1,
            stage_index=0,
            action="first",
            question=question,
            answer="",
            evaluation=None,
        )
    )

    response = InterviewSessionCreateResponse(
        id=session_row.id,
        resume_id=session_row.resume_id,
        target_role=session_row.target_role,
        difficulty=difficulty,
        status=session_row.status,
        created_at=session_row.created_at,
        current_turn=CurrentTurn(seq=1, action="first", question=question),
    )
    await db.commit()
    return response

class SessionNotFoundError(Exception):
    pass

# 创建面试会话
async def create_interview_session_service(
    user_id: int,
    resume_id: int,
    target_role: str,
    difficulty: Difficulty,
    db: AsyncSession,
    llm_client: AsyncOpenAI,
) -> InterviewSessionCreateResponse:
    resume, profile = await load_resume(db, user_id, resume_id)
    candidate_cards = await pick_cards(
        db,
        role_tags_for(target_role),
        normalize_skills(profile.skills),
        difficulty,
    )
    plan = await generate_plan(
        llm_client,
        profile,
        target_role,
        difficulty,
        candidate_cards,
    )
    question = ask_first_question()
    return await persist_session(
        db,
        user_id,
        resume,
        profile,
        target_role,
        difficulty,
        plan,
        question,
    )


# 汇总各轮评估为报告
def _session_report(plan: InterviewPlan, turns: list[InterviewTurn]) -> InterviewReport:
    items: list[tuple[int, TurnEvaluation]] = []
    for turn in turns:
        if not turn.evaluation:
            continue
        items.append((turn.stage_index, TurnEvaluation.model_validate(turn.evaluation)))
    return build_interview_report(plan=plan, items=items)


def _public_turn(turn: InterviewTurn, *, completed: bool) -> InterviewTurnPublic:
    score = None
    comment = None
    if completed and turn.evaluation:
        evaluation = gate_evaluation(TurnEvaluation.model_validate(turn.evaluation))
        score = evaluation.score
        comment = evaluation.comment
    return InterviewTurnPublic(
        seq=turn.seq,
        question=turn.question,
        answer=turn.answer,
        score=score,
        comment=comment,
    )


async def get_interview_session_service(
    *,
    user_id: int,
    session_id: int,
    db: AsyncSession,
) -> InterviewSessionGetResponse:
    result = await db.execute(
        select(InterviewSession).where(
            InterviewSession.id == session_id,
            InterviewSession.user_id == user_id,
        )
    )
    session_row = result.scalar_one_or_none()
    if session_row is None:
        raise SessionNotFoundError()

    turns_result = await db.execute(
        select(InterviewTurn)
        .where(InterviewTurn.session_id == session_id)
        .order_by(InterviewTurn.seq.asc())
    )
    turns = list(turns_result.scalars().all())

    pending = next((turn for turn in turns if turn.answer == ""), None)
    completed = session_row.status == "completed"
    answered = [
        _public_turn(turn, completed=completed)
        for turn in turns
        if turn.answer != ""
    ]
    plan = InterviewPlan.model_validate(session_row.plan)
    return InterviewSessionGetResponse(
        id=session_row.id,
        resume_id=session_row.resume_id,
        target_role=session_row.target_role,
        difficulty=session_row.difficulty,
        status=session_row.status,
        created_at=session_row.created_at,
        turns=answered,
        current_question=None if completed else (pending.question if pending else None),
        report=_session_report(plan, turns) if completed else None,
    )


def _naive_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value
    return value.astimezone(timezone.utc).replace(tzinfo=None)


def _score_from_report(raw: dict | None) -> int | None:
    if not raw:
        return None
    try:
        return InterviewReport.model_validate(raw).score
    except Exception:
        return None


async def list_interview_sessions_service(
    *,
    user_id: int,
    db: AsyncSession,
    status: SessionStatus | None = None,
    created_after: datetime | None = None,
    limit: int = 50,
) -> list[InterviewSessionListItem]:
    stmt = select(InterviewSession).where(InterviewSession.user_id == user_id)
    if status is not None:
        stmt = stmt.where(InterviewSession.status == status)
    if created_after is not None:
        stmt = stmt.where(InterviewSession.created_at >= _naive_utc(created_after))
    stmt = stmt.order_by(
        InterviewSession.created_at.desc(),
        InterviewSession.id.desc(),
    ).limit(limit)
    rows = list((await db.execute(stmt)).scalars().all())

    pending_by_session: dict[int, str] = {}
    in_progress_ids = [row.id for row in rows if row.status == "in_progress"]
    if in_progress_ids:
        pending_result = await db.execute(
            select(InterviewTurn.session_id, InterviewTurn.question).where(
                InterviewTurn.session_id.in_(in_progress_ids),
                InterviewTurn.answer == "",
            )
        )
        pending_by_session = {
            session_id: question for session_id, question in pending_result.all()
        }

    return [
        InterviewSessionListItem(
            id=row.id,
            resume_id=row.resume_id,
            target_role=row.target_role,
            difficulty=row.difficulty,
            status=row.status,
            created_at=row.created_at,
            score=_score_from_report(row.report),
            current_question=(
                pending_by_session.get(row.id) if row.status == "in_progress" else None
            ),
        )
        for row in rows
    ]