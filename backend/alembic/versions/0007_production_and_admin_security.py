"""Add admin, api_keys, security, and user 2FA tables/columns

Revision ID: 0007
Revises: 0006
Create Date: 2026-11-10
"""
from alembic import op
import sqlalchemy as sa

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Bổ sung các cột bảo mật và 2FA vào bảng users
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_user_cols = [c["name"] for c in inspector.get_columns("users")]

    with op.batch_alter_table("users") as batch_op:
        if "two_factor_secret" not in existing_user_cols:
            batch_op.add_column(sa.Column("two_factor_secret", sa.String(64), nullable=True))
        if "two_factor_enabled" not in existing_user_cols:
            batch_op.add_column(sa.Column("two_factor_enabled", sa.Boolean(), nullable=False, server_default="0"))
        if "violation_count" not in existing_user_cols:
            batch_op.add_column(sa.Column("violation_count", sa.Integer(), nullable=False, server_default="0"))
        if "is_banned" not in existing_user_cols:
            batch_op.add_column(sa.Column("is_banned", sa.Boolean(), nullable=False, server_default="0"))
        if "ban_reason" not in existing_user_cols:
            batch_op.add_column(sa.Column("ban_reason", sa.String(500), nullable=True))

    existing_tables = inspector.get_table_names()

    # 2. Bảng api_keys
    if "api_keys" not in existing_tables:
        op.create_table(
            "api_keys",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("name", sa.String(100), nullable=False),
            sa.Column("key_prefix", sa.String(16), nullable=False),
            sa.Column("hashed_key", sa.String(255), nullable=False, unique=True),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default="1"),
            sa.Column("rate_limit_rpm", sa.Integer(), nullable=False, server_default="60"),
            sa.Column("total_requests", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        )
        op.create_index("ix_api_keys_user_id", "api_keys", ["user_id"])
        op.create_index("ix_api_keys_hashed_key", "api_keys", ["hashed_key"], unique=True)

    # 3. Bảng api_usage_logs
    if "api_usage_logs" not in existing_tables:
        op.create_table(
            "api_usage_logs",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("api_key_id", sa.Integer(), sa.ForeignKey("api_keys.id", ondelete="SET NULL"), nullable=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("endpoint", sa.String(255), nullable=False),
            sa.Column("method", sa.String(10), nullable=False, server_default="POST"),
            sa.Column("status_code", sa.Integer(), nullable=False),
            sa.Column("response_time_ms", sa.Float(), nullable=False, server_default="0.0"),
            sa.Column("char_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )
        op.create_index("ix_api_usage_logs_user_id", "api_usage_logs", ["user_id"])
        op.create_index("ix_api_usage_logs_api_key_id", "api_usage_logs", ["api_key_id"])

    # 4. Bảng admin_audit_logs
    if "admin_audit_logs" not in existing_tables:
        op.create_table(
            "admin_audit_logs",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("admin_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("action", sa.String(100), nullable=False),
            sa.Column("target_type", sa.String(50), nullable=False),
            sa.Column("target_id", sa.String(100), nullable=True),
            sa.Column("details", sa.JSON(), nullable=True),
            sa.Column("ip_address", sa.String(50), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )
        op.create_index("ix_admin_audit_logs_admin_id", "admin_audit_logs", ["admin_id"])
        op.create_index("ix_admin_audit_logs_action", "admin_audit_logs", ["action"])

    # 5. Bảng system_voice_settings
    if "system_voice_settings" not in existing_tables:
        op.create_table(
            "system_voice_settings",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("voice_id", sa.String(100), nullable=False, unique=True),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default="1"),
            sa.Column("is_vip_only", sa.Boolean(), nullable=False, server_default="0"),
            sa.Column("cost_multiplier", sa.Float(), nullable=False, server_default="1.0"),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        )
        op.create_index("ix_system_voice_settings_voice_id", "system_voice_settings", ["voice_id"], unique=True)

    # 6. Bảng system_settings
    if "system_settings" not in existing_tables:
        op.create_table(
            "system_settings",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("key", sa.String(100), nullable=False, unique=True),
            sa.Column("value", sa.JSON(), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        )
        op.create_index("ix_system_settings_key", "system_settings", ["key"], unique=True)

    # 7. Bảng affiliate_withdrawals
    if "affiliate_withdrawals" not in existing_tables:
        op.create_table(
            "affiliate_withdrawals",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("amount", sa.Float(), nullable=False),
            sa.Column("bank_name", sa.String(100), nullable=False),
            sa.Column("account_number", sa.String(100), nullable=False),
            sa.Column("account_holder", sa.String(100), nullable=False),
            sa.Column("status", sa.String(50), nullable=False, server_default="pending"),
            sa.Column("admin_note", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        )
        op.create_index("ix_affiliate_withdrawals_user_id", "affiliate_withdrawals", ["user_id"])

    # 8. Bảng security_violation_logs
    if "security_violation_logs" not in existing_tables:
        op.create_table(
            "security_violation_logs",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=True),
            sa.Column("violation_type", sa.String(100), nullable=False),
            sa.Column("ip_address", sa.String(50), nullable=True),
            sa.Column("details", sa.JSON(), nullable=True),
            sa.Column("action_taken", sa.String(100), nullable=False, server_default="warn"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )
        op.create_index("ix_security_violation_logs_user_id", "security_violation_logs", ["user_id"])


def downgrade() -> None:
    op.drop_table("security_violation_logs")
    op.drop_table("affiliate_withdrawals")
    op.drop_table("system_settings")
    op.drop_table("system_voice_settings")
    op.drop_table("admin_audit_logs")
    op.drop_table("api_usage_logs")
    op.drop_table("api_keys")

    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_column("ban_reason")
        batch_op.drop_column("is_banned")
        batch_op.drop_column("violation_count")
        batch_op.drop_column("two_factor_enabled")
        batch_op.drop_column("two_factor_secret")
