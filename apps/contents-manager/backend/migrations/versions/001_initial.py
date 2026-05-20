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
        "users",
        sa.Column("id", sa.Text(), nullable=False),
        sa.Column("email", sa.Text(), nullable=False),
        sa.Column("hashed_pw", sa.Text(), nullable=False),
        sa.Column("role", sa.Text(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(), server_default=sa.text("now()"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.create_table(
        "subjects",
        sa.Column("id", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("owner_id", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.TIMESTAMP(), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "subject_nodes",
        sa.Column("subject_id", sa.Text(), nullable=False),
        sa.Column("node_id", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["subject_id"], ["subjects.id"]),
        sa.PrimaryKeyConstraint("subject_id", "node_id"),
    )
    op.create_table(
        "subject_edges",
        sa.Column("subject_id", sa.Text(), nullable=False),
        sa.Column("edge_id", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["subject_id"], ["subjects.id"]),
        sa.PrimaryKeyConstraint("subject_id", "edge_id"),
    )
    op.create_table(
        "blueprints",
        sa.Column("id", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("matrix", sa.Text(), nullable=True),
        sa.Column("owner_id", sa.Text(), nullable=False),
        sa.Column("weight", sa.Float(), nullable=True),
        sa.Column("required", sa.Boolean(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.TIMESTAMP(), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "blueprint_integration_items",
        sa.Column("id", sa.Text(), nullable=False),
        sa.Column("blueprint_id", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("required_combinations", sa.Text(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["blueprint_id"], ["blueprints.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "question_items",
        sa.Column("id", sa.Text(), nullable=False),
        sa.Column("entity_id", sa.Text(), nullable=False),
        sa.Column("blueprint_id", sa.Text(), nullable=True),
        sa.Column("question_text", sa.Text(), nullable=False),
        sa.Column("options", sa.Text(), nullable=False),
        sa.Column("correct_answer", sa.Text(), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=True),
        sa.Column("node_snapshot", sa.Text(), nullable=True),
        sa.Column("question_type", sa.Text(), nullable=True),
        sa.Column("difficulty", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.TIMESTAMP(), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["blueprint_id"], ["blueprints.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "question_entity_links",
        sa.Column("question_id", sa.Text(), nullable=False),
        sa.Column("entity_id", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["question_id"], ["question_items.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("question_id", "entity_id"),
    )
    op.create_table(
        "question_matrix_links",
        sa.Column("question_id", sa.Text(), nullable=False),
        sa.Column("blueprint_id", sa.Text(), nullable=False),
        sa.Column("layer", sa.Text(), nullable=False),
        sa.Column("stage", sa.Text(), nullable=False),
        sa.Column("integration_item_id", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["blueprint_id"], ["blueprints.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["integration_item_id"], ["blueprint_integration_items.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["question_id"], ["question_items.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("question_id", "blueprint_id", "layer", "stage"),
    )
    op.create_table(
        "generation_jobs",
        sa.Column("id", sa.Text(), nullable=False),
        sa.Column("entity_id", sa.Text(), nullable=False),
        sa.Column("blueprint_id", sa.Text(), nullable=True),
        sa.Column("integration_item_id", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=True),
        sa.Column("result", sa.Text(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.TIMESTAMP(), server_default=sa.text("now()"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("generation_jobs")
    op.drop_table("question_matrix_links")
    op.drop_table("question_entity_links")
    op.drop_table("question_items")
    op.drop_table("blueprint_integration_items")
    op.drop_table("blueprints")
    op.drop_table("subject_edges")
    op.drop_table("subject_nodes")
    op.drop_table("subjects")
    op.drop_table("users")
