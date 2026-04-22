"""add provider tracking

Revision ID: 0003_add_provider_tracking
Revises: 0002_add_ai_extraction_fields
Create Date: 2026-04-22
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003_add_provider_tracking"
down_revision: str | None = "0002_add_ai_extraction_fields"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("documents", sa.Column("extraction_provider", sa.String(length=80), nullable=True))
    op.add_column("documents", sa.Column("refinement_provider", sa.String(length=80), nullable=True))
    op.add_column("documents", sa.Column("provider_chain", sa.String(length=255), nullable=True))
    op.add_column("documents", sa.Column("merge_strategy", sa.String(length=120), nullable=True))
    op.add_column("documents", sa.Column("field_sources", postgresql.JSONB(astext_type=sa.Text()), nullable=True))


def downgrade() -> None:
    op.drop_column("documents", "field_sources")
    op.drop_column("documents", "merge_strategy")
    op.drop_column("documents", "provider_chain")
    op.drop_column("documents", "refinement_provider")
    op.drop_column("documents", "extraction_provider")
