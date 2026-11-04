"""Add auth fields to users and create refresh_tokens table

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-04
"""
from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.alter_column("hashed_password", existing_type=sa.String(255), nullable=True)
        batch_op.add_column(sa.Column("full_name", sa.String(150), nullable=True))
        batch_op.add_column(sa.Column("role", sa.String(20), nullable=False, server_default="user"))
        batch_op.add_column(sa.Column("is_verified", sa.Boolean(), nullable=False, server_default="0"))
        batch_op.add_column(sa.Column("google_id", sa.String(100), nullable=True))
        batch_op.create_index("ix_users_google_id", ["google_id"], unique=True)

    op.create_table(
        "refresh_tokens",
        sa.Column("id", sa.Integer(), nullable=False, autoincrement=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("is_revoked", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_refresh_tokens_user_id", "refresh_tokens", ["user_id"])
    op.create_index("ix_refresh_tokens_token_hash", "refresh_tokens", ["token_hash"], unique=True)


def downgrade() -> None:
    op.drop_table("refresh_tokens")
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.drop_index("ix_users_google_id")
        batch_op.drop_column("google_id")
        batch_op.drop_column("is_verified")
        batch_op.drop_column("role")
        batch_op.drop_column("full_name")
        batch_op.alter_column("hashed_password", existing_type=sa.String(255), nullable=False)
