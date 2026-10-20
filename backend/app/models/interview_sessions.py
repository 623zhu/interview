from sqlalchemy import String, ForeignKey
from app.models.base import Base,TimestampMixin
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.mysql import BIGINT,JSON

class InterviewSession(TimestampMixin,Base):
    __tablename__ = "interview_sessions"

    user_id:Mapped[int] = mapped_column(
        BIGINT(unsigned=True), 
    ForeignKey("users.id",name="fk_interview_sessions_user_id"), 
    nullable=False)

    resume_id:Mapped[int] = mapped_column(
        BIGINT(unsigned=True),
        ForeignKey("resumes.id",name="fk_interview_sessions_resume_id"), 
        nullable=False)

    target_role:Mapped[str] = mapped_column(String(128), nullable=False)
    difficulty:Mapped[str] = mapped_column(String(32), nullable=False)
    status:Mapped[str] = mapped_column(String(32), nullable=False)
    resume_snapshot:Mapped[dict] = mapped_column(JSON, nullable=False)
    plan:Mapped[dict] = mapped_column(JSON, nullable=False)
    progress:Mapped[dict] = mapped_column(JSON, nullable=False)