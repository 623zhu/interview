from typing import Literal
from pydantic import BaseModel,ConfigDict,Field

from app.schemas.utc import UtcDateTime


Difficulty = Literal["easy", "medium", "hard"]
TargetRole = Literal["Java 后端", "Python 后端", "AI Agent"]
StageKind = Literal["intro","project_probe","fundamentals","scenario","closing"]
TurnAction = Literal["first", "follow_up", "deepen", "hint", "next_stage", "end"]
SessionStatus = Literal["planned", "in_progress", "completed", "abandoned"]


class InterviewSessionCreateRequest(BaseModel):
    resume_id:int = Field(...,description="The ID of the resume to create the interview session for")
    target_role:TargetRole = Field(...,description="The role the candidate is applying for")
    difficulty:Difficulty = Field(...,description="The difficulty of the interview session")


class CurrentTurn(BaseModel):
    seq:int
    action:TurnAction
    question:str

class InterviewSessionCreateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:int
    resume_id:int
    target_role:str
    difficulty:Difficulty
    status:str
    created_at:UtcDateTime
    current_turn:CurrentTurn

# 计划的一个阶段
class InterviewStage(BaseModel):
    id:str
    kind:StageKind
    goal:str
    max_turns:int = Field(ge=1,le=8)
    source:Literal["resume","bank"]="resume"
    resume_anchor:str | None = None
    topic_card_key:str | None = None


class InterviewPlan(BaseModel):
    stages:list[InterviewStage]= Field(min_length=1)


class InterviewProgress(BaseModel):
    stage_index: int = Field(ge=0)
    turn_in_stage: int = Field(ge=1)
    consecutive_misses: int = Field(ge=0, default=0) # 用户回答不好的次数
    used_card_keys: list[str] = Field(default_factory=list) # 用户已经使用过的卡片 key



class TurnEvaluation(BaseModel):
    covered: list[str]
    missing: list[str]
    depth: Literal["shallow", "adequate", "deep"]
    vague_quotes: list[str]         # 用户回答中的含糊原话
    said_dont_know: bool
    off_topic: bool                     # 用户回答是否偏离主题
    score: int | None = Field(default=None, ge=0, le=100)
    comment: str | None = Field(default=None, max_length=512)


class StageScore(BaseModel):
    kind: StageKind
    score: int = Field(ge=0, le=100)


class InterviewTurnSubmitRequest(BaseModel):
    answer: str = Field(min_length=0, max_length=8000)


# 汇总
class InterviewReport(BaseModel):
    score: int = Field(ge=0, le=100)
    stages: list[StageScore] = Field(default_factory=list)
    covered: list[str]
    missing: list[str]
    said_dont_know_count: int = 0


class InterviewTurnSubmitResponse(BaseModel):
    id: int
    status: SessionStatus
    current_turn: CurrentTurn | None
    report: InterviewReport | None = None


class InterviewTurnPublic(BaseModel):
    seq:int
    question:str
    answer:str
    score: int | None = None
    comment: str | None = None

class InterviewSessionGetResponse(BaseModel):
    id:int
    resume_id:int
    target_role:str
    difficulty: str
    status: str
    created_at: UtcDateTime
    turns: list[InterviewTurnPublic]
    current_question: str | None
    report: InterviewReport | None = None


class InterviewSessionListItem(BaseModel):
    id: int
    resume_id: int
    target_role: str
    difficulty: str
    status: str
    created_at: UtcDateTime
    score: int | None = None
    stages: list[StageScore] = Field(default_factory=list)
    current_question: str | None = None


class InterviewSessionPatchRequest(BaseModel):
    status: Literal["abandoned"]