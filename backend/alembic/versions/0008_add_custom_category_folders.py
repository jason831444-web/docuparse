"""add custom category folders

Revision ID: 0008_custom_category_folders
Revises: 0007_confirmed_favorites
Create Date: 2026-04-29
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "0008_custom_category_folders"
down_revision: str | None = "0007_confirmed_favorites"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.create_table(
        "category_folders",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("value", sa.String(length=120), nullable=False),
        sa.Column("label", sa.String(length=120), nullable=False),
        sa.Column("parent", sa.String(length=80), nullable=True),
        sa.Column("category", sa.String(length=80), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("value", name="uq_category_folders_value"),
    )
    op.create_index("ix_category_folders_value", "category_folders", ["value"])
    op.create_index("ix_category_folders_parent", "category_folders", ["parent"])
    op.create_index("ix_category_folders_category", "category_folders", ["category"])


def downgrade() -> None:
    op.drop_index("ix_category_folders_category", table_name="category_folders")
    op.drop_index("ix_category_folders_parent", table_name="category_folders")
    op.drop_index("ix_category_folders_value", table_name="category_folders")
    op.drop_table("category_folders")
