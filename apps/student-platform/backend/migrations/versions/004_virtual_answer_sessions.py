"""virtual_student_study_session_info 추가, virtual_study_sessions → virtual_student_study_log 리네임

Revision ID: 004
Revises: 003
Create Date: 2026-06-03

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 세션 단위 mastery 변화 기록 테이블
    op.create_table(
        "virtual_student_study_session_info",
        sa.Column("session_id", sa.String(), nullable=False),
        sa.Column("student_id", sa.Integer(), nullable=False),
        sa.Column("node_id", sa.String(), nullable=False),
        sa.Column("subject_id", sa.String(), nullable=False),
        sa.Column("mastery_before", sa.Float(), nullable=True),
        sa.Column("mastery_after", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["student_id"], ["virtual_students.id"]),
        sa.PrimaryKeyConstraint("session_id"),
    )

    # virtual_study_sessions → virtual_student_study_log 리네임
    # (003에서 추가된 run_id 컬럼은 rename/batch 재생성 시 그대로 보존된다)
    op.rename_table("virtual_study_sessions", "virtual_student_study_log")

    # session_id 컬럼 추가 (SQLite batch mode)
    with op.batch_alter_table("virtual_student_study_log") as batch_op:
        batch_op.add_column(sa.Column("session_id", sa.String(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("virtual_student_study_log") as batch_op:
        batch_op.drop_column("session_id")
    op.rename_table("virtual_student_study_log", "virtual_study_sessions")
    op.drop_table("virtual_student_study_session_info")
