"""Alembic migration: Voice library unified model and VoiceFavorites

Revision ID: 0008
Revises: 0007
Create Date: 2026-11-11
"""
from alembic import op
import sqlalchemy as sa

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = inspector.get_table_names()

    # 1. Bảng voices (Thư viện giọng tập trung)
    if "voices" not in existing_tables:
        op.create_table(
            "voices",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("owner_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=True),
            sa.Column("name", sa.String(150), nullable=False),
            sa.Column("display_name", sa.String(200), nullable=True),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("provider", sa.String(50), nullable=False),
            sa.Column("provider_voice_id", sa.String(255), nullable=True),
            sa.Column("voice_type", sa.String(20), nullable=False, server_default="system"),
            sa.Column("language", sa.String(20), nullable=False, server_default="vi-VN"),
            sa.Column("gender", sa.String(20), nullable=False, server_default="Unknown"),
            sa.Column("tags", sa.String(500), nullable=True),
            sa.Column("preview_url", sa.String(1000), nullable=True),
            sa.Column("sample_duration", sa.Float(), nullable=True),
            sa.Column("visibility", sa.String(20), nullable=False, server_default="private"),
            sa.Column("status", sa.String(20), nullable=False, server_default="ready"),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default="1"),
            sa.Column("consent_id", sa.Integer(), nullable=True),
            sa.Column("license_note", sa.String(500), nullable=True),
            sa.Column("tier", sa.String(20), nullable=False, server_default="free"),
            sa.Column("credit_multiplier", sa.Float(), nullable=False, server_default="1.0"),
            sa.Column("cloned_voice_ref", sa.String(100), nullable=True),
            sa.Column("total_uses", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        )
        op.create_index("ix_voices_owner_id", "voices", ["owner_id"])
        op.create_index("ix_voices_provider", "voices", ["provider"])
        op.create_index("ix_voices_voice_type", "voices", ["voice_type"])
        op.create_index("ix_voices_language", "voices", ["language"])
        op.create_index("ix_voices_is_active", "voices", ["is_active"])
        op.create_index("ix_voices_status", "voices", ["status"])
        op.create_index("ix_voices_provider_active", "voices", ["provider", "is_active"])
        op.create_index("ix_voices_type_lang", "voices", ["voice_type", "language"])

    # 2. Bảng voice_favorites
    if "voice_favorites" not in existing_tables:
        op.create_table(
            "voice_favorites",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("voice_id", sa.Integer(), sa.ForeignKey("voices.id", ondelete="CASCADE"), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.UniqueConstraint("user_id", "voice_id", name="uq_voice_favorites_user_voice"),
        )
        op.create_index("ix_voice_favorites_user_id", "voice_favorites", ["user_id"])
        op.create_index("ix_voice_favorites_voice_id", "voice_favorites", ["voice_id"])


def downgrade() -> None:
    op.drop_table("voice_favorites")
    op.drop_table("voices")
