"""Add cloned_voices, voice_consent_logs, and voice_abuse_reports tables

Revision ID: 0006
Revises: 0005
Create Date: 2026-11-09
"""
from alembic import op
import sqlalchemy as sa

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Bảng cloned_voices
    try:
        op.create_table(
            "cloned_voices",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("voice_id", sa.String(100), nullable=False, unique=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("name", sa.String(100), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("audio_sample_path", sa.String(500), nullable=False),
            sa.Column("sample_duration", sa.Float(), nullable=False),
            sa.Column("sample_size_bytes", sa.Integer(), nullable=False),
            sa.Column("quality_score", sa.Float(), nullable=True),
            sa.Column("gender", sa.String(20), nullable=False, server_default="unspecified"),
            sa.Column("language", sa.String(20), nullable=False, server_default="vi-VN"),
            sa.Column("provider", sa.String(50), nullable=False, server_default="mock"),
            sa.Column("provider_voice_id", sa.String(150), nullable=True),
            sa.Column("preview_audio_path", sa.String(500), nullable=True),
            sa.Column("preview_audio_url", sa.String(500), nullable=True),
            sa.Column("status", sa.String(30), nullable=False, server_default="ready"),
            sa.Column("error_message", sa.Text(), nullable=True),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default="1"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        )
        op.create_index("ix_cloned_voices_voice_id", "cloned_voices", ["voice_id"], unique=True)
        op.create_index("ix_cloned_voices_user_id", "cloned_voices", ["user_id"])
    except Exception:
        pass

    # 2. Bảng voice_consent_logs
    try:
        op.create_table(
            "voice_consent_logs",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("cloned_voice_id", sa.Integer(), sa.ForeignKey("cloned_voices.id", ondelete="CASCADE"), nullable=True),
            sa.Column("voice_name", sa.String(100), nullable=False),
            sa.Column("audio_sample_filename", sa.String(255), nullable=False),
            sa.Column("consent_text", sa.Text(), nullable=False),
            sa.Column("ip_address", sa.String(50), nullable=True),
            sa.Column("user_agent", sa.String(500), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )
        op.create_index("ix_voice_consent_logs_user_id", "voice_consent_logs", ["user_id"])
        op.create_index("ix_voice_consent_logs_cloned_voice_id", "voice_consent_logs", ["cloned_voice_id"])
    except Exception:
        pass

    # 3. Bảng voice_abuse_reports
    try:
        op.create_table(
            "voice_abuse_reports",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("cloned_voice_id", sa.Integer(), sa.ForeignKey("cloned_voices.id", ondelete="CASCADE"), nullable=False),
            sa.Column("reporter_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.Column("reporter_email", sa.String(255), nullable=True),
            sa.Column("reason", sa.String(50), nullable=False),
            sa.Column("description", sa.Text(), nullable=False),
            sa.Column("status", sa.String(30), nullable=False, server_default="pending"),
            sa.Column("ip_address", sa.String(50), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )
        op.create_index("ix_voice_abuse_reports_cloned_voice_id", "voice_abuse_reports", ["cloned_voice_id"])
    except Exception:
        pass


def downgrade() -> None:
    try:
        op.drop_table("voice_abuse_reports")
    except Exception:
        pass
    try:
        op.drop_table("voice_consent_logs")
    except Exception:
        pass
    try:
        op.drop_table("cloned_voices")
    except Exception:
        pass
