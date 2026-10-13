from datetime import datetime,timezone

from sqlalchemy.dialects.mysql import BIGINT,DATETIME
from sqlalchemy.orm import Mapped,mapped_column,DeclarativeBase

def utcnow()->datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    id: Mapped[int] = mapped_column(
        BIGINT(unsigned=True),
        primary_key=True,
        autoincrement=True,
        sort_order=-1,
    )
    created_at: Mapped[datetime] = mapped_column(
        DATETIME(fsp=6),
        nullable=False,
        default=utcnow,
        sort_order=100,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DATETIME(fsp=6),
        nullable=False,
        default=utcnow,
        onupdate=utcnow,
        sort_order=101,
    )