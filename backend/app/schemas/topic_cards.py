import hashlib
import json
from typing import Literal

from pydantic import BaseModel, Field

Difficulty = Literal["easy", "medium", "hard"]
CardStatus = Literal["draft", "published"]


class TopicKeyPoint(BaseModel):
    id: str = Field(min_length=1, max_length=128)
    text: str = Field(min_length=1, max_length=1024)


class ProbeStep(BaseModel):
    id: str = Field(min_length=1, max_length=128)
    intent: str = Field(min_length=1, max_length=1024)


class TopicCard(BaseModel):
    key: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=128)
    summary: str = Field(min_length=1, max_length=255)
    difficulty: Difficulty
    role_tags: list[str] = Field(min_length=1)
    skill_tags: list[str] = Field(min_length=1)
    key_points: list[TopicKeyPoint] = Field(min_length=2, max_length=6)
    probe_path: list[ProbeStep] = Field(min_length=2, max_length=5)
    pitfalls: list[str] = Field(min_length=1, max_length=6)
    status: CardStatus = "published"

    def content_hash(self) -> str:
        payload = self.model_dump(
            include={
                "name",
                "summary",
                "difficulty",
                "role_tags",
                "skill_tags",
                "key_points",
                "probe_path",
                "pitfalls",
            }
        )
        canonical = json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
