"""add ai extraction fields

Revision ID: 0002_add_ai_extraction_fields
Revises: 0001_create_documents
Create Date: 2026-04-22
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002_add_ai_extraction_fields"
down_revision: str | None = "0001_create_documents"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

document_type = postgresql.ENUM("receipt", "notice", "document", "memo", "other", name="document_type", create_type=False)


def upgrade() -> None:
    op.add_column("documents", sa.Column("subtotal", sa.Numeric(12, 2), nullable=True))
    op.add_column("documents", sa.Column("tax", sa.Numeric(12, 2), nullable=True))
    op.add_column("documents", sa.Column("ai_document_type", document_type, nullable=True))
    op.add_column("documents", sa.Column("ai_confidence_score", sa.Numeric(4, 3), nullable=True))
    op.add_column("documents", sa.Column("ai_extraction_notes", sa.Text(), nullable=True))
    op.add_column("documents", sa.Column("review_required", sa.Boolean(), server_default=sa.false(), nullable=False))
    op.add_column("documents", sa.Column("summary", sa.Text(), nullable=True))
    op.alter_column("documents", "review_required", server_default=None)


def downgrade() -> None:
    op.drop_column("documents", "summary")
    op.drop_column("documents", "review_required")
    op.drop_column("documents", "ai_extraction_notes")
    op.drop_column("documents", "ai_confidence_score")
    op.drop_column("documents", "ai_document_type")
    op.drop_column("documents", "tax")
    op.drop_column("documents", "subtotal")
