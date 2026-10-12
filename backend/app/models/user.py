from sqlalchemy import String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class User(TimestampMixin, Base):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255,collation="utf8mb4_0900_as_cs"), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)

    __table_args__ = (UniqueConstraint("email", name="uq_users_email"),)