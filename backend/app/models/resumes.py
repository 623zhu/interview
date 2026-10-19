from sqlalchemy import String, Integer, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin
from app.models.user import User
from sqlalchemy.dialects.mysql import BIGINT,MEDIUMTEXT,JSON

class Resume(TimestampMixin, Base):
    __tablename__ = "resumes"

    user_id: Mapped[int] = mapped_column(
        BIGINT(unsigned=True),
        ForeignKey("users.id", name="fk_resumes_user_id_users"),
        nullable=False,
    )
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_path: Mapped[str] = mapped_column(String(255), nullable=False)
    media_type: Mapped[str] = mapped_column(String(127), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    raw_text: Mapped[str | None] = mapped_column(MEDIUMTEXT, nullable=True)
    profile: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error_detail: Mapped[str | None] = mapped_column(String(512), nullable=True)