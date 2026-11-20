"""Alembic migration: dubbing_jobs table for Subtitle Dubbing (Issue #21)

Revision ID: 0011
Revises: 0010
Create Date: 2026-11-20
"""
from alembic import op
import sqlalchemy as sa

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = inspector.get_table_names()

    if "dubbing_jobs" not in existing_tables:
        op.create_table(
            "dubbing_jobs",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("title", sa.String(255), nullable=False, server_default="Lồng tiếng phụ đề"),
            sa.Column("subtitle_format", sa.String(10), nullable=False, server_default="srt"),
            sa.Column("target_format", sa.String(10), nullable=False, server_default="mp3"),
            sa.Column("default_voice", sa.String(100), nullable=False, server_default="vi-VN-HoaiMyNeural"),
            sa.Column("status", sa.String(20), nullable=False, server_default="queued"),
            sa.Column("progress", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("total_cues", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("char_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("credit_used", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("cues_data", sa.Text(), nullable=True),
            sa.Column("output_audio_path", sa.String(1000), nullable=True),
            sa.Column("output_zip_path", sa.String(1000), nullable=True),
            sa.Column("background_audio_path", sa.String(1000), nullable=True),
            sa.Column("ducking_volume", sa.Float(), nullable=False, server_default="0.2"),
            sa.Column("error_message", sa.Text(), nullable=True),
            sa.Column("duration", sa.Float(), nullable=False, server_default="0.0"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        )
        op.create_index("ix_dubbing_jobs_user_id", "dubbing_jobs", ["user_id"])
        op.create_index("ix_dubbing_jobs_status", "dubbing_jobs", ["status"])
        op.create_index("ix_dubbing_jobs_user_status", "dubbing_jobs", ["user_id", "status"])


def downgrade() -> None:
    op.drop_table("dubbing_jobs")
