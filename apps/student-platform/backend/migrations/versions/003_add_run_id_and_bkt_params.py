"""add run_id to virtual_study_sessions and bkt_node_params table

Revision ID: 003
Revises: 002
Create Date: 2026-06-02

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "virtual_study_sessions",
        sa.Column("run_id", sa.String(), nullable=True),
    )

    op.create_table(
        "bkt_node_params",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("subject_id", sa.String(), nullable=False),
        sa.Column("node_id", sa.String(), nullable=False),
        sa.Column("p_l0", sa.Float(), nullable=False),
        sa.Column("p_t", sa.Float(), nullable=False),
        sa.Column("p_g", sa.Float(), nullable=False),
        sa.Column("p_s", sa.Float(), nullable=False),
        sa.Column("n_students", sa.Integer(), nullable=True),
        sa.Column("n_responses", sa.Integer(), nullable=True),
        sa.Column("trained_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("subject_id", "node_id", name="uq_bkt_node"),
    )


def downgrade() -> None:
    op.drop_table("bkt_node_params")
    op.drop_column("virtual_study_sessions", "run_id")
