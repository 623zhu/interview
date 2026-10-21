from sqlalchemy import Integer
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.mysql import BIGINT,JSON
from sqlalchemy.schema import UniqueConstraint
from sqlalchemy.sql.schema import ForeignKey
from sqlalchemy.sql.sqltypes import String
from app.models.base import TimestampMixin,Base


class InterviewTurn(TimestampMixin,Base):
    __tablename__ = 'interview_turns'

    session_id:Mapped[int] = mapped_column(
        BIGINT(unsigned=True),
        ForeignKey(
            'interview_sessions.id',
            name = "fk_interview_turn_session_id_interview_sessions",
            ondelete = "CASCADE",
        ),
        nullable = False,
    )

    seq:Mapped[int] = mapped_column(Integer,nullable=False)
    stage_index:Mapped[int] = mapped_column(Integer,nullable=False)
    action:Mapped[str] = mapped_column(String(255),nullable=False)
    question:Mapped[str] = mapped_column(String(2048),nullable=False)
    answer:Mapped[str] = mapped_column(String(8000),nullable=False)
    evaluation:Mapped[dict|None] = mapped_column(JSON,nullable=True)

    __table_args__=(
        UniqueConstraint(
            'session_id','seq',
            name = "uq_interview_turn_session_id_seq",
        ),
    )