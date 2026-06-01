"""add ingestion review tables

Revision ID: 003
Revises: 002
Create Date: 2026-06-01

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ingestion_sources",
        sa.Column("id", sa.Text(), nullable=False),
        sa.Column("source_type", sa.Text(), nullable=False),
        sa.Column("source_summary", sa.Text(), nullable=True),
        sa.Column("raw_text", sa.Text(), nullable=True),
        sa.Column("subject_id", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), server_default="saved", nullable=True),
        sa.Column("extracted_node_count", sa.Integer(), server_default="0", nullable=True),
        sa.Column("extracted_edge_count", sa.Integer(), server_default="0", nullable=True),
        sa.Column("extraction_notes", sa.Text(), nullable=True),
        sa.Column("created_by", sa.Text(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(), nullable=True),
        sa.ForeignKeyConstraint(["subject_id"], ["subjects.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "ingestion_pending_nodes",
        sa.Column("id", sa.Text(), nullable=False),
        sa.Column("session_id", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("type", sa.Text(), nullable=False),
        sa.Column("depth", sa.Integer(), server_default="1", nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("source_excerpt", sa.Text(), nullable=True),
        sa.Column("db_exists", sa.Boolean(), server_default="false", nullable=True),
        sa.Column("matched_node_id", sa.Text(), nullable=True),
        sa.Column("decision", sa.Text(), server_default="add", nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(), nullable=True),
        sa.ForeignKeyConstraint(["session_id"], ["ingestion_sources.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ingestion_pending_nodes_session_id", "ingestion_pending_nodes", ["session_id"])

    op.create_table(
        "ingestion_pending_edges",
        sa.Column("id", sa.Text(), nullable=False),
        sa.Column("session_id", sa.Text(), nullable=False),
        sa.Column("source_name", sa.Text(), nullable=False),
        sa.Column("target_name", sa.Text(), nullable=False),
        sa.Column("relation", sa.Text(), nullable=False),
        sa.Column("basis", sa.Text(), nullable=True),
        sa.Column("source_excerpt", sa.Text(), nullable=True),
        sa.Column("db_exists", sa.Boolean(), server_default="false", nullable=True),
        sa.Column("decision", sa.Text(), server_default="add", nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(), nullable=True),
        sa.ForeignKeyConstraint(["session_id"], ["ingestion_sources.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ingestion_pending_edges_session_id", "ingestion_pending_edges", ["session_id"])


def downgrade() -> None:
    op.drop_index("ix_ingestion_pending_edges_session_id", table_name="ingestion_pending_edges")
    op.drop_table("ingestion_pending_edges")
    op.drop_index("ix_ingestion_pending_nodes_session_id", table_name="ingestion_pending_nodes")
    op.drop_table("ingestion_pending_nodes")
    op.drop_table("ingestion_sources")
