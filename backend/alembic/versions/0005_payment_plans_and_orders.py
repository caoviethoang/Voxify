"""Add payment plans, coupons, orders, and payment webhook logs

Revision ID: 0005
Revises: 0004
Create Date: 2026-11-05
"""
from alembic import op
import sqlalchemy as sa

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Bảng pricing_plans
    try:
        op.create_table(
            "pricing_plans",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("code", sa.String(50), nullable=False, unique=True),
            sa.Column("name", sa.String(100), nullable=False),
            sa.Column("type", sa.String(20), nullable=False, server_default="credit_pack"),
            sa.Column("price", sa.Integer(), nullable=False),
            sa.Column("currency", sa.String(10), nullable=False, server_default="VND"),
            sa.Column("credits", sa.Integer(), nullable=False),
            sa.Column("duration_days", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("storage_days", sa.Integer(), nullable=False, server_default="7"),
            sa.Column("has_premium_voices", sa.Boolean(), nullable=False, server_default="0"),
            sa.Column("has_api_access", sa.Boolean(), nullable=False, server_default="0"),
            sa.Column("queue_priority", sa.String(20), nullable=False, server_default="standard"),
            sa.Column("concurrency_limit", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("badge", sa.String(50), nullable=True),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("display_order", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default="1"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        )
        op.create_index("ix_pricing_plans_code", "pricing_plans", ["code"])
    except Exception:
        pass

    # 2. Bảng coupons
    try:
        op.create_table(
            "coupons",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("code", sa.String(50), nullable=False, unique=True),
            sa.Column("discount_type", sa.String(20), nullable=False, server_default="percent"),
            sa.Column("discount_value", sa.Integer(), nullable=False),
            sa.Column("min_order_amount", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("max_uses", sa.Integer(), nullable=False, server_default="100"),
            sa.Column("used_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default="1"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )
        op.create_index("ix_coupons_code", "coupons", ["code"])
    except Exception:
        pass

    # 3. Bảng orders
    try:
        op.create_table(
            "orders",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("order_code", sa.String(50), nullable=False, unique=True),
            sa.Column("order_number", sa.Integer(), nullable=False, unique=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("plan_id", sa.Integer(), sa.ForeignKey("pricing_plans.id", ondelete="SET NULL"), nullable=True),
            sa.Column("coupon_id", sa.Integer(), sa.ForeignKey("coupons.id", ondelete="SET NULL"), nullable=True),
            sa.Column("original_amount", sa.Integer(), nullable=False),
            sa.Column("discount_amount", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("final_amount", sa.Integer(), nullable=False),
            sa.Column("credits_to_add", sa.Integer(), nullable=False),
            sa.Column("payment_method", sa.String(20), nullable=False, server_default="vietqr"),
            sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
            sa.Column("qr_url", sa.String(500), nullable=True),
            sa.Column("checkout_url", sa.String(500), nullable=True),
            sa.Column("transfer_content", sa.String(50), nullable=True),
            sa.Column("bank_name", sa.String(50), nullable=True),
            sa.Column("bank_account_no", sa.String(50), nullable=True),
            sa.Column("bank_account_name", sa.String(100), nullable=True),
            sa.Column("payment_transaction_id", sa.String(100), nullable=True),
            sa.Column("metadata_json", sa.Text(), nullable=True),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        )
        op.create_index("ix_orders_order_code", "orders", ["order_code"])
        op.create_index("ix_orders_order_number", "orders", ["order_number"])
        op.create_index("ix_orders_user_id", "orders", ["user_id"])
        op.create_index("ix_orders_status", "orders", ["status"])
        op.create_index("ix_orders_transfer_content", "orders", ["transfer_content"])
    except Exception:
        pass

    # 4. Bảng payment_webhook_logs
    try:
        op.create_table(
            "payment_webhook_logs",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("gateway", sa.String(30), nullable=False),
            sa.Column("transaction_id", sa.String(100), nullable=False),
            sa.Column("order_code", sa.String(50), nullable=True),
            sa.Column("payload", sa.Text(), nullable=True),
            sa.Column("is_processed", sa.Boolean(), nullable=False, server_default="1"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )
        op.create_index("ix_payment_webhook_logs_gateway", "payment_webhook_logs", ["gateway"])
        op.create_index("ix_payment_webhook_logs_transaction_id", "payment_webhook_logs", ["transaction_id"])
    except Exception:
        pass


def downgrade() -> None:
    for tbl in ["payment_webhook_logs", "orders", "coupons", "pricing_plans"]:
        try:
            op.drop_table(tbl)
        except Exception:
            pass
