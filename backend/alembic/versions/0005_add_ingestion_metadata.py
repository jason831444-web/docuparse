"""add ingestion metadata

Revision ID: 0005_add_ingestion_metadata
Revises: 0004_add_workflow_enrichment
Create Date: 2026-04-22
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0005_add_ingestion_metadata"
down_revision: str | None = "0004_add_workflow_enrichment"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("documents", sa.Column("source_file_type", sa.String(length=40), nullable=True))
    op.add_column("documents", sa.Column("extraction_method", sa.String(length=80), nullable=True))
    op.add_column("documents", sa.Column("ingestion_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True))


def downgrade() -> None:
    op.drop_column("documents", "ingestion_metadata")
    op.drop_column("documents", "extraction_method")
    op.drop_column("documents", "source_file_type")
