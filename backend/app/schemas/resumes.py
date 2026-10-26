from pydantic import BaseModel, ConfigDict, Field

from app.schemas.utc import UtcDateTime


class ResumeUploadResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    original_filename: str
    media_type: str
    status: str
    raw_text: str | None = None
    profile: dict | None = None
    error_detail: str | None = None
    created_at: UtcDateTime

class ResumeGetResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    original_filename: str
    media_type: str
    status: str
    created_at: UtcDateTime

class EducationItem(BaseModel):
    school: str
    degree: str | None = None
    major: str | None = None
    start: str | None = None
    end: str | None = None

class ExperienceItem(BaseModel):
    company: str
    title: str | None = None
    start: str | None = None
    end: str | None = None
    highlights: list[str] = Field(default_factory=list)

class ProjectItem(BaseModel):
    name: str
    role: str | None = None
    highlights: list[str] = Field(default_factory=list)

class ResumeProfile(BaseModel):
    name: str | None = None
    education: list[EducationItem] = Field(default_factory=list)
    experience: list[ExperienceItem] = Field(default_factory=list)
    projects: list[ProjectItem] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)