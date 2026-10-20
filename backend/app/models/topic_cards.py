from app.models.base import Base,TimestampMixin
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, JSON
from sqlalchemy.schema import UniqueConstraint

class TopicCard(TimestampMixin,Base):
    __tablename__ = "topic_cards"

    key :Mapped[str] = mapped_column(String(64), nullable=False)
    name :Mapped[str] = mapped_column(String(128), nullable=False)
    summary :Mapped[str] = mapped_column(String(255), nullable=False)
    difficulty :Mapped[str] = mapped_column(String(32), nullable=False)
    role_tags :Mapped[list[str]] = mapped_column(JSON, nullable=False)
    skill_tags:Mapped[list[str]] = mapped_column(JSON, nullable=False)
    key_points:Mapped[list[dict]] = mapped_column(JSON, nullable=False)
    probe_path:Mapped[list[dict]] = mapped_column(JSON, nullable=False)
    pitfalls:Mapped[list[str]] = mapped_column(JSON, nullable=False)
    status:Mapped[str] = mapped_column(String(32), nullable=False)
    content_hash:Mapped[str] = mapped_column(String(64), nullable=False)
    
    __table_args__= (UniqueConstraint(key, name="uq_topic_cards_key"),)