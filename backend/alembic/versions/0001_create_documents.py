"""create documents

Revision ID: 0001_create_documents
Revises:
Create Date: 2026-04-22
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001_create_documents"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


document_type = postgresql.ENUM("receipt", "notice", "document", "memo", "other", name="document_type", create_type=False)
processing_status = postgresql.ENUM("uploaded", "processing", "completed", "failed", name="processing_status", create_type=False)


def upgrade() -> None:
    document_type.create(op.get_bind(), checkfirst=True)
    processing_status.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("stored_file_path", sa.String(length=1024), nullable=False),
        sa.Column("mime_type", sa.String(length=100), nullable=False),
        sa.Column("document_type", document_type, nullable=False),
        sa.Column("title", sa.String(length=255), nullable=True),
        sa.Column("raw_text", sa.Text(), nullable=True),
        sa.Column("extracted_date", sa.Date(), nullable=True),
        sa.Column("extracted_amount", sa.Numeric(12, 2), nullable=True),
        sa.Column("currency", sa.String(length=8), nullable=True),
        sa.Column("merchant_name", sa.String(length=255), nullable=True),
        sa.Column("category", sa.String(length=80), nullable=True),
        sa.Column("tags", postgresql.ARRAY(sa.String()), server_default="{}", nullable=False),
        sa.Column("confidence_score", sa.Numeric(4, 3), nullable=True),
        sa.Column("processing_status", processing_status, nullable=False),
        sa.Column("preview_image_path", sa.String(length=1024), nullable=True),
        sa.Column("processing_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_documents_category", "documents", ["category"])
    op.create_index("ix_documents_processing_status", "documents", ["processing_status"])


def downgrade() -> None:
    op.drop_index("ix_documents_processing_status", table_name="documents")
    op.drop_index("ix_documents_category", table_name="documents")
    op.drop_table("documents")
    processing_status.drop(op.get_bind(), checkfirst=True)
    document_type.drop(op.get_bind(), checkfirst=True)
