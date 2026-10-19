from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ResumeUploadResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    original_filename: str
    media_type: str
    status: str
    raw_text: str | None = None
    profile: dict | None = None
    error_detail: str | None = None
    created_at: datetime

class ResumeGetResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    original_filename: str
    media_type: str
    status: str
    created_at: datetime
