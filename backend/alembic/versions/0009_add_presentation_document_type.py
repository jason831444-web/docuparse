"""add presentation document type

Revision ID: 0009_presentation_document_type
Revises: 0008_custom_category_folders
Create Date: 2026-04-29
"""

from collections.abc import Sequence

from alembic import op


revision: str = "0009_presentation_document_type"
down_revision: str | None = "0008_custom_category_folders"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    with op.get_context().autocommit_block():
        bind.exec_driver_sql("ALTER TYPE document_type ADD VALUE IF NOT EXISTS 'presentation'")


def downgrade() -> None:
    # PostgreSQL enum values cannot be dropped safely without recreating the type.
    pass
