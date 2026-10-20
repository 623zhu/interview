from typing import Literal
from pydantic import BaseModel,ConfigDict,Field
from datetime import datetime


Difficulty = Literal["easy", "medium", "hard"]
StageKind = Literal["intro","project_probe","fundamentals","scenario","closing"]

class InterviewSessionCreateRequest(BaseModel):
    resume_id:int = Field(...,description="The ID of the resume to create the interview session for")
    target_role:str = Field(...,description="The role the candidate is applying for")
    difficulty:Difficulty = Field(...,description="The difficulty of the interview session")


class InterviewSessionCreateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:int
    resume_id:int
    target_role:str
    difficulty:Difficulty
    status:str
    create_at:datetime

# 计划的一个阶段
class InterviewStage(BaseModel):
    id:str
    kind:StageKind
    goal:str
    max_turns:int = Field(ge=1,le=8)
    source:Literal["resume"]="resume"
    resume_anchor:str | None = None


class InterviewPlan(BaseModel):
    stages:list[InterviewStage]= Field(min_length=1)