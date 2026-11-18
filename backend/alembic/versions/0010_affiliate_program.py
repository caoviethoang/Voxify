"""Alembic migration: affiliate program tables and user referral columns (Issue #14)

Revision ID: 0010
Revises: 0009
Create Date: 2026-11-18
"""
from alembic import op
import sqlalchemy as sa

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = inspector.get_table_names()

    # 1. Thêm cột referral vào bảng users nếu chưa có
    user_columns = [c["name"] for c in inspector.get_columns("users")]
    with op.batch_alter_table("users") as batch_op:
        if "referral_code" not in user_columns:
            batch_op.add_column(sa.Column("referral_code", sa.String(32), nullable=True))
            batch_op.create_index("ix_users_referral_code", ["referral_code"], unique=True)
        if "referred_by_id" not in user_columns:
            batch_op.add_column(sa.Column("referred_by_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True))
            batch_op.create_index("ix_users_referred_by_id", ["referred_by_id"])
        if "registration_ip" not in user_columns:
            batch_op.add_column(sa.Column("registration_ip", sa.String(45), nullable=True))
        if "device_fingerprint" not in user_columns:
            batch_op.add_column(sa.Column("device_fingerprint", sa.String(100), nullable=True))

    # 2. Bảng affiliate_clicks
    if "affiliate_clicks" not in existing_tables:
        op.create_table(
            "affiliate_clicks",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("affiliate_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("referral_code", sa.String(32), nullable=False),
            sa.Column("ip_address", sa.String(45), nullable=True),
            sa.Column("user_agent", sa.String(255), nullable=True),
            sa.Column("device_fingerprint", sa.String(100), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )
        op.create_index("ix_affiliate_clicks_affiliate_user_id", "affiliate_clicks", ["affiliate_user_id"])
        op.create_index("ix_affiliate_clicks_referral_code", "affiliate_clicks", ["referral_code"])

    # 3. Bảng affiliate_commissions
    if "affiliate_commissions" not in existing_tables:
        op.create_table(
            "affiliate_commissions",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("affiliate_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("referred_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("order_id", sa.Integer(), sa.ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, unique=True),
            sa.Column("order_amount", sa.Integer(), nullable=False),
            sa.Column("commission_rate", sa.Float(), nullable=False),
            sa.Column("amount", sa.Integer(), nullable=False),
            sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
            sa.Column("hold_until", sa.DateTime(timezone=True), nullable=False),
            sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("cancel_reason", sa.String(255), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        )
        op.create_index("ix_affiliate_commissions_affiliate_user_id", "affiliate_commissions", ["affiliate_user_id"])
        op.create_index("ix_affiliate_commissions_referred_user_id", "affiliate_commissions", ["referred_user_id"])
        op.create_index("ix_affiliate_commissions_order_id", "affiliate_commissions", ["order_id"], unique=True)
        op.create_index("ix_affiliate_commissions_status", "affiliate_commissions", ["status"])
        op.create_index("ix_affiliate_commissions_hold_until", "affiliate_commissions", ["hold_until"])

    # 4. Kiểm tra và bổ sung bảng affiliate_withdrawals nếu chưa có
    if "affiliate_withdrawals" not in existing_tables:
        op.create_table(
            "affiliate_withdrawals",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("amount", sa.Integer(), nullable=False),
            sa.Column("bank_name", sa.String(100), nullable=False),
            sa.Column("bank_account_number", sa.String(50), nullable=False),
            sa.Column("bank_account_holder", sa.String(150), nullable=False),
            sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
            sa.Column("note", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        )
        op.create_index("ix_affiliate_withdrawals_user_id", "affiliate_withdrawals", ["user_id"])
        op.create_index("ix_affiliate_withdrawals_status", "affiliate_withdrawals", ["status"])


def downgrade() -> None:
    op.drop_table("affiliate_commissions")
    op.drop_table("affiliate_clicks")

    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_column("device_fingerprint")
        batch_op.drop_column("registration_ip")
        batch_op.drop_column("referred_by_id")
        batch_op.drop_column("referral_code")
