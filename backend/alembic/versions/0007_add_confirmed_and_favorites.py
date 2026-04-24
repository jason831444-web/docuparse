"""add confirmed status and favorites

Revision ID: 0007_confirmed_favorites
Revises: 0006_processing_statuses
Create Date: 2026-04-24
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "0007_confirmed_favorites"
down_revision: str | None = "0006_processing_statuses"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    with op.get_context().autocommit_block():
        bind.exec_driver_sql("ALTER TYPE processing_status ADD VALUE IF NOT EXISTS 'confirmed'")

    op.add_column("documents", sa.Column("is_favorite", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.create_index("ix_documents_is_favorite", "documents", ["is_favorite"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_documents_is_favorite", table_name="documents")
    op.drop_column("documents", "is_favorite")
    # Enum value downgrade intentionally omitted.
