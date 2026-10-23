"""add interview_sessions.report

Revision ID: c4f8a21b9d07
Revises: 1ce649d360ab
Create Date: 2026-10-23 16:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

revision: str = "c4f8a21b9d07"
down_revision: Union[str, Sequence[str], None] = "1ce649d360ab"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "interview_sessions",
        sa.Column("report", mysql.JSON(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("interview_sessions", "report")
