from typing import Literal
from pydantic import BaseModel,ConfigDict,Field
from datetime import datetime


Difficulty = Literal["easy", "medium", "hard"]
StageKind = Literal["intro","project_probe","fundamentals","scenario","closing"]
TurnAction = Literal["first", "follow_up", "deepen", "hint", "next_stage", "end"]
SessionStatus = Literal["planned", "in_progress", "completed", "abandoned"]

class InterviewSessionCreateRequest(BaseModel):
    resume_id:int = Field(...,description="The ID of the resume to create the interview session for")
    target_role:str = Field(...,min_length=1,max_length=128,description="The role the candidate is applying for")
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
    created_at:datetime
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
    consecutive_misses: int = Field(ge=0, default=0)
    used_card_keys: list[str] = Field(default_factory=list)

