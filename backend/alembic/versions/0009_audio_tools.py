"""Alembic migration: audio_tool_jobs table for Audio Tools Framework

Revision ID: 0009
Revises: 0008
Create Date: 2026-11-11
"""
from alembic import op
import sqlalchemy as sa

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = inspector.get_table_names()

    if "audio_tool_jobs" not in existing_tables:
        op.create_table(
            "audio_tool_jobs",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("tool_id", sa.String(100), nullable=False),
            sa.Column("status", sa.String(20), nullable=False, server_default="queued"),
            sa.Column("progress", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("input_path", sa.String(1000), nullable=False),
            sa.Column("input_filename", sa.String(255), nullable=False),
            sa.Column("input_duration", sa.Float(), nullable=True),
            sa.Column("params", sa.Text(), nullable=True),
            sa.Column("output_path", sa.String(1000), nullable=True),
            sa.Column("output_filename", sa.String(255), nullable=True),
            sa.Column("output_duration", sa.Float(), nullable=True),
            sa.Column("output_size_bytes", sa.Integer(), nullable=True),
            sa.Column("credit_used", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("error_message", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        )
        op.create_index("ix_audio_tool_jobs_user_id", "audio_tool_jobs", ["user_id"])
        op.create_index("ix_audio_tool_jobs_tool_id", "audio_tool_jobs", ["tool_id"])
        op.create_index("ix_audio_tool_jobs_status", "audio_tool_jobs", ["status"])
        op.create_index("ix_audio_tool_jobs_user_status", "audio_tool_jobs", ["user_id", "status"])
        op.create_index("ix_audio_tool_jobs_tool_status", "audio_tool_jobs", ["tool_id", "status"])


def downgrade() -> None:
    op.drop_table("audio_tool_jobs")
