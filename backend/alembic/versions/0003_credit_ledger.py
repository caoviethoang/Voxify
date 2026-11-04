"""Add credit_balance to users and update credit_transactions columns

Revision ID: 0003
Revises: 0002
Create Date: 2026-11-04
"""
from alembic import op
import sqlalchemy as sa

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Thêm credit_balance vào users nếu chưa có
    with op.batch_alter_table("users", schema=None) as batch_op:
        try:
            batch_op.add_column(sa.Column("credit_balance", sa.Integer(), nullable=False, server_default="10000"))
        except Exception:
            pass

    # 2. Cập nhật credit_transactions: thêm type và ref_id
    with op.batch_alter_table("credit_transactions", schema=None) as batch_op:
        try:
            batch_op.add_column(sa.Column("type", sa.String(30), nullable=False, server_default="usage"))
            batch_op.create_index("ix_credit_transactions_type", ["type"])
        except Exception:
            pass
        try:
            batch_op.add_column(sa.Column("ref_id", sa.String(100), nullable=True))
            batch_op.create_index("ix_credit_transactions_ref_id", ["ref_id"])
        except Exception:
            pass


def downgrade() -> None:
    with op.batch_alter_table("credit_transactions", schema=None) as batch_op:
        batch_op.drop_index("ix_credit_transactions_ref_id")
        batch_op.drop_column("ref_id")
        batch_op.drop_index("ix_credit_transactions_type")
        batch_op.drop_column("type")

    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.drop_column("credit_balance")
