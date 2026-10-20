from typing import Literal
from pydantic import BaseModel,ConfigDict,Field

Difficulty = Literal["easy", "medium", "hard"]
CardStatus = Literal["draft", "published"]

class TopicKeyPoint(BaseModel):
    id:str=Field(min_length=1,max_length=128)
    text:str=Field(min_length=1,max_length=1024)

class ProbeStep(BaseModel):
    id:str=Field(min_length=1,max_length=128)
    intent:str=Field(min_length=1,max_length=1024)

class TopicCard(BaseModel):
    key: str = Field(min_length=1, max_length=64)  # 全局唯一 slug
    name: str = Field(min_length=1, max_length=128)
    summary: str = Field(min_length=1, max_length=255)  # 给计划生成看，不进用户问题
    difficulty: Difficulty
    role_tags: list[str] = Field(min_length=1)
    skill_tags: list[str] = Field(min_length=1)
    key_points: list[TopicKeyPoint] = Field(min_length=2, max_length=6)
    probe_path: list[ProbeStep] = Field(min_length=2, max_length=5)
    pitfalls: list[str] = Field(min_length=1, max_length=6)
    status: CardStatus = "published"   