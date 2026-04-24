"""add processing lifecycle statuses

Revision ID: 0006_processing_statuses
Revises: 0005_add_ingestion_metadata
Create Date: 2026-04-23
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0006_processing_statuses"
down_revision: str | None = "0005_add_ingestion_metadata"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    for value in ["queued", "ready", "needs_review"]:
        with op.get_context().autocommit_block():
            bind.exec_driver_sql(f"ALTER TYPE processing_status ADD VALUE IF NOT EXISTS '{value}'")


def downgrade() -> None:
    # PostgreSQL enum values cannot be dropped safely without recreating the type.
    pass
