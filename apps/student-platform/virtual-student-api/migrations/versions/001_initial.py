"""initial schema

Revision ID: 001
Revises:
Create Date: 2026-05-20

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "virtual_student_feature_definitions",
        sa.Column("key", sa.String(), nullable=False),
        sa.Column("display_name", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("value_type", sa.String(), nullable=False),
        sa.Column("value_options", sa.JSON(), nullable=True),
        sa.Column("value_range", sa.JSON(), nullable=True),
        sa.Column("default_value", sa.String(), nullable=True),
        sa.Column("category", sa.String(), nullable=False),
        sa.Column("is_builtin", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("key"),
    )

    op.create_table(
        "virtual_students",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("subject_id", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "virtual_student_feature_values",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("virtual_student_id", sa.String(), nullable=False),
        sa.Column("feature_key", sa.String(), nullable=False),
        sa.Column("value", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["feature_key"], ["virtual_student_feature_definitions.key"]),
        sa.ForeignKeyConstraint(["virtual_student_id"], ["virtual_students.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "simulation_runs",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("subject_id", sa.String(), nullable=False),
        sa.Column("mode", sa.String(), nullable=False),
        sa.Column("question_source", sa.String(), nullable=False),
        sa.Column("questions", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "simulation_results",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("run_id", sa.String(), nullable=False),
        sa.Column("virtual_student_id", sa.String(), nullable=False),
        sa.Column("answers", sa.JSON(), nullable=False),
        sa.Column("diagnosis", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["run_id"], ["simulation_runs.id"]),
        sa.ForeignKeyConstraint(["virtual_student_id"], ["virtual_students.id"]),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("simulation_results")
    op.drop_table("simulation_runs")
    op.drop_table("virtual_student_feature_values")
    op.drop_table("virtual_students")
    op.drop_table("virtual_student_feature_definitions")
