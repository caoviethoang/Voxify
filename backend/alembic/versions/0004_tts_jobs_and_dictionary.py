"""Add TTS background jobs columns and pronunciation dictionary table

Revision ID: 0004
Revises: 0003
Create Date: 2026-11-05
"""
from alembic import op
import sqlalchemy as sa

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Thêm cột mới vào generations
    with op.batch_alter_table("generations", schema=None) as batch_op:
        try:
            batch_op.add_column(sa.Column("status", sa.String(20), nullable=False, server_default="done"))
            batch_op.create_index("ix_generations_status", ["status"])
        except Exception:
            pass
        try:
            batch_op.add_column(sa.Column("progress", sa.Integer(), nullable=False, server_default="100"))
        except Exception:
            pass
        try:
            batch_op.add_column(sa.Column("duration", sa.Float(), nullable=False, server_default="0.0"))
        except Exception:
            pass
        try:
            batch_op.add_column(sa.Column("format", sa.String(10), nullable=False, server_default="mp3"))
        except Exception:
            pass
        try:
            batch_op.add_column(sa.Column("credit_used", sa.Integer(), nullable=False, server_default="0"))
        except Exception:
            pass
        try:
            batch_op.add_column(sa.Column("error_message", sa.Text(), nullable=True))
        except Exception:
            pass
        try:
            batch_op.add_column(sa.Column("srt_path", sa.String(500), nullable=True))
            batch_op.add_column(sa.Column("vtt_path", sa.String(500), nullable=True))
        except Exception:
            pass
        try:
            batch_op.add_column(sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True))
        except Exception:
            pass

    # 2. Tạo bảng pronunciation_dictionaries
    try:
        op.create_table(
            "pronunciation_dictionaries",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("word", sa.String(150), nullable=False),
            sa.Column("replacement", sa.String(255), nullable=False),
            sa.Column("category", sa.String(50), nullable=False, server_default="custom"),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default="1"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        )
        op.create_index("ix_pronunciation_dictionaries_user_id", "pronunciation_dictionaries", ["user_id"])
        op.create_index("ix_pronunciation_dictionaries_word", "pronunciation_dictionaries", ["word"])
    except Exception:
        pass


def downgrade() -> None:
    try:
        op.drop_table("pronunciation_dictionaries")
    except Exception:
        pass

    with op.batch_alter_table("generations", schema=None) as batch_op:
        for col in ["updated_at", "vtt_path", "srt_path", "error_message", "credit_used", "format", "duration", "progress", "status"]:
            try:
                batch_op.drop_column(col)
            except Exception:
                pass
